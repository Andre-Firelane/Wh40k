"""Rule 10.06 (Close-Quarters shooting): who an ENGAGED unit may shoot at.

Reported from a real game: "monster und fahrzeuge koennen aus dem nahkampf
rausschiessen auf eine andere einheit. im letzten spiel konnte ich das mit dem
voiddragon nicht." Reproduced before anything was changed - an engaged C'tan
Shard of the Void Dragon was offered exactly one target, the unit it had
charged (logs/game_20260904_214656.log line 585 shows it firing the Spear into
that melee with the Close-Quarters malus, which is the only shot it could take).

There was NO test for rule 10.06 anywhere in this repo before this file -
"Close-Quarters"/CLOSE_QUARTERS_SHOOTING appeared in zero test files - which is
why a targeting rule that touches 19 units across all five army lists could sit
wrong. This suite owns the rule now.

What it pins, and why each line is a boundary rather than a happy path:
  * a MONSTER/VEHICLE unit engaged in melee can pick EITHER the unit it is
    locked with OR another enemy unit;
  * an INFANTRY unit with a [PISTOL]/[CLOSE-QUARTERS] weapon deliberately
    cannot - the report names monsters and vehicles, and this is the half that
    was NOT widened;
  * rule 03.04 still applies to that other enemy unit: a unit locked in
    somebody else's melee stays off the list;
  * the hit malus, which had a half nothing could reach until now.

Run: python test_close_quarters_shooting.py
"""
import testkit as tk
from game import shooting
from game.factions import aeldari, necrons, orks
from game.modifiers import describe_modifiers
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance, is_monster_or_vehicle_unit

c = tk.Checks("rule 10.06 - close-quarters targeting")


def _place(anchor_squad, squad, edge_in, y0=20.0):
    """Put `squad` directly north of `anchor_squad` at `edge_in` inches of
    BASE-TO-BASE clearance.

    Spacing has to be computed from the actual base radii, not written down as
    a centre-to-centre gap: this file stages a Void Dragon (80 mm), Deffkoptas
    and Ork Boyz against the same two foes, and one fixed gap puts some of them
    inside Engagement Range and others outside it. The first draft did exactly
    that and six checks failed for the wrong reason."""
    dy = anchor_squad.models[0].radius_in + squad.models[0].radius_in + edge_in
    tk.line_up(squad, x=20.0, y=y0 + dy)
    return squad


def scene(shooter_sheet, near_edge_in=1.5, far_edge_in=9.0, shooter_owner="Player 2"):
    """Shooter locked in melee with `near`, with a second enemy unit `far`
    standing clear of every melee on the board.

    The stage checks its own two constraints in section 1 rather than trusting
    the numbers: `near` must be inside Engagement Range (03.04) and `far`
    outside it, or every assertion in this file would pass or fail for the
    wrong reason."""
    state = tk.GameState()
    foe_owner = "Player 1" if shooter_owner == "Player 2" else "Player 2"
    shooter = tk.build(shooter_sheet, shooter_owner, name="2 Shooter 1")
    near = tk.build(aeldari.GUARDIAN_DEFENDERS, foe_owner, name="1 Near 1")
    far = tk.build(aeldari.DIRE_AVENGERS, foe_owner, name="1 Far 1")
    tk.line_up(shooter, x=20.0, y=20.0)
    _place(shooter, near, near_edge_in)
    _place(shooter, far, far_edge_in)
    for sq in (shooter, near, far):
        for m in sq.models:
            state.add_token(m)

    tt = tk._tracker(tk.PHASE_SHOOTING, shooter_owner)
    sc = shooting.ShootingController(
        dice_manager=tk.RecordingDice(), turn_tracker=tt, all_tokens=state.tokens,
        decision_manager=tk.DecisionManager(), game_log=tk.Log(), obstacles=[],
    )
    return dict(state=state, shooter=shooter, near=near, far=far, shooting=sc)


def close_quarters(s):
    """Start the shooter's activation and land it in Close-Quarters shooting."""
    sc = s["shooting"]
    sc.start_shooting(s["shooter"])
    if sc.state == shooting.CHOOSING_SHOOTING_TYPE:
        sc.choose_shooting_type(shooting.CLOSE_QUARTERS_SHOOTING)
    return sc


def weapon_named(squad, needle):
    for m in squad.models:
        for w in m.weapons:
            if needle.lower() in w.name.lower():
                return m, w
    raise AssertionError("no weapon matching %r" % (needle,))


# ------------------------------------------------------------------ 1) report
print("\n1) The reported case: the Void Dragon shoots out of the melee")
s = scene(necrons.CTAN_SHARD_OF_THE_VOID_DRAGON)
sh, near, far = s["shooter"], s["near"], s["far"]
c.true("the shooter is a MONSTER/VEHICLE unit", is_monster_or_vehicle_unit(sh))
c.true("stage: it is locked with the near unit",
       min(edge_distance(a, b) for a in sh.models for b in near.models) <= ENGAGEMENT_RANGE_IN)
c.true("stage: the far unit stands clear of it",
       min(edge_distance(a, b) for a in sh.models for b in far.models) > ENGAGEMENT_RANGE_IN)
c.true("stage: nothing on the board is engaged with the far unit",
       not far.is_engaged(s["state"].tokens))

c.eq("engaged, it may only shoot Close-Quarters",
     shooting.available_shooting_types(sh, s["state"].tokens), [shooting.CLOSE_QUARTERS_SHOOTING])
sc = close_quarters(s)
c.eq("shooting type", sc.shooting_type, shooting.CLOSE_QUARTERS_SHOOTING)
c.true("it can still shoot the unit it is locked with",
       sc._is_valid_target_squad(near, s["state"].tokens))
c.true("REPORT: it can now shoot the OTHER enemy unit",
       sc._is_valid_target_squad(far, s["state"].tokens))

# Not just the predicate: the board highlight and the target click both come
# from valid_target_models(), so a fix the highlight never hears about would
# leave the unit unclickable - the "built but never fed" failure this repo has
# hit six times.
highlighted = set()
for t in sc.valid_target_models(s["state"].tokens):
    highlighted.add(t.squad)
c.true("the board highlight offers the far unit too", far in highlighted)
c.true("...and still offers the engaged one", near in highlighted)

# And the choice actually takes, rather than being silently dropped by
# choose_target_squad()'s own re-validation.
sc.choose_target_squad(far)
c.eq("choosing the far unit takes", sc.target_squad, far)
c.eq("...and moves on to the weapon step", sc.state, shooting.CHOOSING_WEAPON)
fired = [label for _, label, eligible, _, _ in sc.weapon_eligibility() if eligible]
c.true("at least one weapon can actually reach it", bool(fired))

# ------------------------------------------------------- 2) the half NOT widened
print("\n2) INFANTRY with a [PISTOL] stays locked on its own melee")
s = scene(orks.BOYZ)
sh, near, far = s["shooter"], s["near"], s["far"]
c.true("stage: the Boyz are not a MONSTER/VEHICLE unit", not is_monster_or_vehicle_unit(sh))
# is_close_quarters() takes the SQUAD now, because [PISTOL] can be granted as
# well as printed (Blades of Asuryan) - see its docstring. Passing the real
# squad is what the production gates do; passing None asks the printed-only
# question, and both agree here because no Ork unit can hold that grant.
c.true("stage: they carry a [CLOSE-QUARTERS]/[PISTOL] weapon",
       shooting.is_close_quarters(weapon_named(sh, "Slugga")[1], sh))
c.true("...printed, not granted",
       shooting.is_close_quarters(weapon_named(sh, "Slugga")[1], None))
c.eq("engaged, they may only shoot Close-Quarters",
     shooting.available_shooting_types(sh, s["state"].tokens), [shooting.CLOSE_QUARTERS_SHOOTING])
sc = close_quarters(s)
c.true("they can shoot the unit they are locked with",
       sc._is_valid_target_squad(near, s["state"].tokens))
c.true("they CANNOT shoot the other enemy unit",
       not sc._is_valid_target_squad(far, s["state"].tokens))

# ------------------------------------------------------------------ 3) 03.04
print("\n3) Rule 03.04 still keeps somebody else's melee off the list")
s = scene(necrons.CTAN_SHARD_OF_THE_VOID_DRAGON)
sh, near, far = s["shooter"], s["near"], s["far"]
# A second friendly unit locks the far one. Nothing else moves.
blocker = tk.build(necrons.NECRON_WARRIORS, "Player 2", name="2 Blocker 1")
_place(far, blocker, 1.5, y0=far.models[0].y_in)
for m in blocker.models:
    s["state"].add_token(m)
sc = close_quarters(s)
c.true("stage: the far unit is now locked in a melee of its own",
       far.is_engaged(s["state"].tokens))
c.true("a MONSTER may not fire into that melee either",
       not sc._is_valid_target_squad(far, s["state"].tokens))
c.true("...while the unit it is itself locked with stays legal",
       sc._is_valid_target_squad(near, s["state"].tokens))

# ------------------------------------------------------------------ 4) malus
print("\n4) The hit malus, both halves - one of them was unreachable until now")
s = scene(orks.DEFFKOPTAS, far_edge_in=8.0)
sh, near, far = s["shooter"], s["near"], s["far"]
c.true("stage: Deffkoptas are a MONSTER/VEHICLE unit", is_monster_or_vehicle_unit(sh))
sc = close_quarters(s)
cq_model, cq_weapon = weapon_named(sh, "Slugga")               # [CLOSE-QUARTERS]
other_model, other_weapon = weapon_named(sh, "Kopta Rokkits")  # not


def malus(model, weapon, target):
    mods = sc._hit_modifiers({"pairs": [(model, weapon)], "target_squad": target})
    return describe_modifiers(mods)


c.eq("[CLOSE-QUARTERS] weapon at the unit it is locked with: no malus",
     malus(cq_model, cq_weapon, near), "")
c.true("other weapon at the unit it is locked with: malus",
       "non-[CLOSE-QUARTERS] weapon" in malus(other_model, other_weapon, near))
c.true("other weapon out at the far unit: malus",
       "non-[CLOSE-QUARTERS] weapon" in malus(other_model, other_weapon, far))
# The branch that had nothing to reach it before: a [CLOSE-QUARTERS] weapon
# fired OUT of the melee. The old label would have called a Slugga a
# "non-[CLOSE-QUARTERS] weapon" on the dice panel.
out = malus(cq_model, cq_weapon, far)
c.true("[CLOSE-QUARTERS] weapon out at the far unit: malus", "Close-Quarters" in out)
c.true("...and the label names the reason it earned it, not the wrong one",
       "target not engaged" in out and "non-[CLOSE-QUARTERS]" not in out)

# ------------------------------------------------------------ 5) nothing else
print("\n5) Nothing outside rule 10.06 moved")
s = scene(necrons.CTAN_SHARD_OF_THE_VOID_DRAGON, near_edge_in=12.0, far_edge_in=20.0)
sh, near, far = s["shooter"], s["near"], s["far"]
c.true("stage: this shooter is not engaged at all", not sh.is_engaged(s["state"].tokens))
c.true("unengaged, it shoots normally",
       shooting.NORMAL_SHOOTING in shooting.available_shooting_types(sh, s["state"].tokens))
sc = s["shooting"]
sc.start_shooting(sh)
if sc.state == shooting.CHOOSING_SHOOTING_TYPE:
    sc.choose_shooting_type(shooting.NORMAL_SHOOTING)
c.eq("stage: normal shooting", sc.shooting_type, shooting.NORMAL_SHOOTING)
c.true("normal shooting can still pick an unengaged enemy",
       sc._is_valid_target_squad(near, s["state"].tokens))

# The same relaxation must NOT leak into normal shooting: an engaged enemy unit
# is off limits there, whoever is firing (03.04).
s = scene(necrons.CTAN_SHARD_OF_THE_VOID_DRAGON)
sh, near = s["shooter"], s["near"]
sc = s["shooting"]
sc.active_squad, sc.shooting_type = sh, shooting.NORMAL_SHOOTING
c.true("a MONSTER may not pick an engaged enemy under NORMAL shooting",
       not sc._is_valid_target_squad(near, s["state"].tokens))

# --------------------------------------------- 6) [PISTOL] can be GRANTED too
print("\n6) A GRANTED [PISTOL] counts everywhere a printed one does")

# This suite owns 10.06 and 24.07, and until now it only ever staged PRINTED
# [PISTOL]/[CLOSE-QUARTERS] weapons - so the gate's other input was invisible
# to it. Blades of Asuryan (Guardian Battlehost) grants [PISTOL] to a whole
# unit for a phase, and it reached the adjuster chain and not this gate:
# reported as "ich konnte zwar mit asurmen schiessen, aber nicht mit dem rest
# meines avengers squads". A change to is_close_quarters() would be run against
# THIS file, so the grant path belongs here as well as in the Aeldari suite.
from game import config as _config  # noqa: E402
from game.factions import aeldari as _ae  # noqa: E402

_D6 = _ae.AELDARI.datasheets
_saved_gb = getattr(_config, "GUARDIAN_BATTLEHOST_PLAYERS", ())
_config.GUARDIAN_BATTLEHOST_PLAYERS = ("Player 2",)
try:
    s = scene(_D6["Dire Avengers"], near_edge_in=1.5)
    sh, near = s["shooter"], s["near"]
    _ranged = [(m, w) for m in sh.models for w in m.weapons
               if getattr(w, "weapon_type", None) == "ranged"]
    c.true("stage: the Avengers are engaged", sh.is_engaged(s["state"].tokens))
    c.true("stage: not a MONSTER/VEHICLE unit", not is_monster_or_vehicle_unit(sh))
    c.true("stage: no printed [PISTOL] on any of its ranged weapons",
           not any(shooting.is_close_quarters(w, None) for _m, w in _ranged))

    c.eq("engaged with no [PISTOL] at all, it cannot shoot",
         shooting.available_shooting_types(sh, s["state"].tokens), [])

    sh.blades_of_asuryan_active = True
    c.eq("...and a GRANTED [PISTOL] opens Close-Quarters",
         shooting.available_shooting_types(sh, s["state"].tokens),
         [shooting.CLOSE_QUARTERS_SHOOTING])
    c.true("...for every ranged weapon in the unit",
           all(shooting._weapon_eligible_for_type(
               w, shooting.CLOSE_QUARTERS_SHOOTING, sh) for _m, w in _ranged))
    c.true("...and is_close_quarters() says so when asked with the squad",
           all(shooting.is_close_quarters(w, sh) for _m, w in _ranged))
    c.true("...while the printed-only question still says no",
           not any(shooting.is_close_quarters(w, None) for _m, w in _ranged))

    # RULE 24.07's two sides. A granted [PISTOL] really does move the weapon
    # onto the pistol side - claimed in _weapon_side()'s docstring, measured
    # here, because a claim about a rule that nothing measures is how the gate
    # got out of step in the first place.
    _model, _weapon = _ranged[0]
    c.eq("24.07: a granted weapon is on the [PISTOL] side",
         shooting._weapon_side(_weapon, sh), "close_quarters")
    c.eq("...and on the other side without the grant",
         shooting._weapon_side(_weapon, None), "other")
    # ...so a unit whose weapons are ALL granted has one side, and the lock
    # cannot split it.
    c.eq("...so the whole unit is on one side, and the lock cannot split it",
         {shooting._weapon_side(w, sh) for _m, w in _ranged}, {"close_quarters"})

    # The counter-check, without which this section would pass against a gate
    # that simply said yes to everything.
    _melee = [w for m in sh.models for w in m.weapons
              if getattr(w, "weapon_type", None) != "ranged"]
    c.true("stage: the unit has melee weapons to check", len(_melee) > 0)
    c.true("a melee weapon gains nothing - the text says 'ranged weapons'",
           not any(shooting.is_close_quarters(w, sh) for w in _melee))

    sh.blades_of_asuryan_active = False
    c.eq("and the grant expiring closes the gate again",
         shooting.available_shooting_types(sh, s["state"].tokens), [])
finally:
    _config.GUARDIAN_BATTLEHOST_PLAYERS = _saved_gb

c.finish()
