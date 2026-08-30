"""All of a unit's melee attacks are made in ONE activation, so an earlier
weapon group's casualties cannot put a later one out of Engagement Range.

User report: "im nahkampf. alle nahkampfwaffen schlagen gleichzeitig zu. das
heisst waffen eines squads koennen in einer aktivierung nicht ausser reichweite
geraten, wenn models vom gegner entfernt werden. aehnlich wie beim schiessen."

The "aehnlich wie beim schiessen" is literal: game/shooting.py already carries
this exact fix as rule 10.02's _snapshot_target_state(), added after the same
report about the Shooting phase. The Fight phase never got it, so
weapon_eligibility() and choose_weapon() re-ran rule 12.02's per-model
Engagement Range check from scratch for every remaining group, against whatever
enemy models were still standing.

Reproduced before changing anything, with a Warp Spider squad and a target
whose only close model stood in front of the rest: the squad's three groups
offered 3/4, 1/1 and 1/1 eligible models, then 0/4, 0/1 and 0/1 the moment that
one model was removed as a casualty - and choose_weapon() built an empty pair
list, so the rest of the unit's melee weapons simply lost their attacks.

The fix is FightController._snapshot_engagement()/_engaged_with(), taken at the
same three points that constitute the target-selection step (choose_target_squad,
_start_fighting's single-target auto-pick, and Split Fire's assign_current).
"""
import testkit as tk
from game import fight as fight_module
from game.factions import aeldari as ae
from game.squad import model_engaged_with

c = tk.Checks("melee - all weapons strike in one activation")


def section(title):
    print(f"\n--- {title} ---")


ARRAY = {"Warp Spider Exarch": {ae.WARP_SPIDER_TO_POWERBLADE_ARRAY: 1}}

SQUAD_CCW = "Close Combat Weapon"
EXARCH_CCW = "Close Combat Weapon (Warp Spider Exarch)"
EXARCH_ARRAY = "Powerblade Array (Warp Spider Exarch)"


def scene(split_fire=False):
    """A Warp Spider squad in a line, and a target whose FRONT model is the
    only one any of them can reach - so removing it, and only it, is what
    breaks the live geometry. The Exarch carries the Powerblade Array, which
    is what gives the squad more than one weapon group to spend across the
    activation in the first place."""
    sc = tk.fight_scene(ae.WARP_SPIDERS, ae.DIRE_AVENGERS, attacker_owner="Player 1",
                        attacker_choices=ARRAY)
    if split_fire:
        sc["fight"].toggle_split_fire()
    tk.line_up(sc["attacker"], x=20.0, y=20.0)
    for i, model in enumerate(sc["target"].models):
        if i == 0:
            model.x_in, model.y_in = 22.0, 21.0     # in contact with the line
        else:
            model.x_in, model.y_in = 20.0 + i * 1.4, 30.0  # far behind it
    return sc


def started(split_fire=False):
    sc = scene(split_fire)
    sc["fight"].select_to_fight(sc["attacker"])
    if sc["fight"].state == fight_module.CHOOSING_TARGET and not split_fire:
        sc["fight"].choose_target_squad(sc["target"])
    return sc


def offers(sc):
    """{label: (eligible, total)} for the groups currently on offer."""
    return {label: (elig, total) for _key, label, elig, total in sc["fight"].weapon_eligibility()}


def kill_front(sc):
    """Remove the one close target model as a casualty, exactly as the damage
    pipeline plus main.py's once-per-frame sweep would."""
    sc["target"].models[0].current_wounds = 0
    return len(sc["state"].remove_dead_models())


def swing(sc, label):
    """Fight the group labelled EXACTLY `label` to a standstill. Returns how
    many model+weapon pairs actually SWUNG - the number the report is about,
    not the number the panel advertised."""
    option = next((o for o in sc["fight"].weapon_eligibility() if o[1] == label), None)
    if option is None:
        return None
    tk.script(*([6] * 240), default=6)
    sc["fight"].choose_weapon(option[0])
    swung = len(sc["fight"].current_group["pairs"]) if sc["fight"].current_group else 0
    for _ in range(240):
        if sc["dice"].is_pending:
            sc["dice"].acknowledge()
            sc["fight"].on_dice_acknowledged()
        elif sc["decision"].is_pending:
            tk.pick_option(sc["decision"], sc["decision"].options[0]["label"])
        else:
            break
    return swung


# --------------------------------------------------------------- 1. the report

section("1. the reported case - eligibility survives a casualty")

sc = started()
before = offers(sc)
c.eq("all three groups are offered at activation start", sorted(before), sorted([SQUAD_CCW, EXARCH_CCW, EXARCH_ARRAY]))
c.eq("squad's Close Combat Weapon starts 3/4 eligible", before[SQUAD_CCW], (3, 4))
c.eq("Exarch's Close Combat Weapon starts 1/1", before[EXARCH_CCW], (1, 1))
c.eq("Exarch's Powerblade Array starts 1/1", before[EXARCH_ARRAY], (1, 1))

c.eq("exactly one casualty is swept", kill_front(sc), 1)
c.eq("the target unit itself survives", len(sc["target"].models), 4)
# The premise of the whole report: LIVE geometry now says nobody is engaged.
c.eq("live Engagement Range says 0 attackers are engaged", sum(1 for m in sc["attacker"].models if model_engaged_with(m, sc["target"])), 0)

after = offers(sc)
c.eq("the same three groups are still offered", sorted(after), sorted(before))
c.eq("squad's Close Combat Weapon is still 3/4", after[SQUAD_CCW], (3, 4))
c.eq("Exarch's Close Combat Weapon is still 1/1", after[EXARCH_CCW], (1, 1))
c.eq("Exarch's Powerblade Array is still 1/1", after[EXARCH_ARRAY], (1, 1))


# ------------------------------------------------- 2. end to end, real pipeline

section("2. end to end - the later group really swings")

sc = started()
c.eq("group 1 swings with its 3 eligible models", swing(sc, SQUAD_CCW), 3)
c.eq("its casualty is swept between the groups", kill_front(sc), 1)
c.eq("the activation is still open", sc["fight"].state, fight_module.CHOOSING_WEAPON)
c.eq("group 1 is spent and no longer offered", SQUAD_CCW in offers(sc), False)
# The number that used to be 0. A count check alone would not have caught it:
# the panel and the swing read the same predicate, so both were wrong together.
c.eq("the Exarch's second group still swings with 1 model", swing(sc, EXARCH_CCW), 1)


# ------------------------------------------- 3. a target wiped out is different

section("3. a target destroyed ENTIRELY has nothing left to attack")

sc = started()
c.eq("frozen eligibility before the wipe", offers(sc)[SQUAD_CCW], (3, 4))
for model in list(sc["target"].models):
    model.current_wounds = 0
c.eq("every target model is dead but not yet swept", len(sc["target"].models), 5)
# `not squad.models` would still be False here - remove_dead_models() runs once
# per frame, so this moment exists in every real game (CLAUDE.md error class 12).
c.eq("a wiped-out target gives 0 eligible even before the sweep", offers(sc)[SQUAD_CCW], (0, 4))
c.eq("and swinging at it swings with nobody", swing(sc, SQUAD_CCW), 0)

sc = started()
for model in list(sc["target"].models):
    model.current_wounds = 0
sc["state"].remove_dead_models()
c.eq("same answer after the sweep", offers(sc)[SQUAD_CCW], (0, 4))


# ------------------------------------------------ 4. the snapshot is per-target

section("4. one activation, one snapshot - a later activation measures afresh")

sc = started()
c.eq("first activation sees the front model", offers(sc)[SQUAD_CCW], (3, 4))
kill_front(sc)
c.eq("still frozen mid-activation", offers(sc)[SQUAD_CCW], (3, 4))
sc["fight"].cancel()
# Compared by SIZE, not by value: the entries are keyed by Token, whose repr
# is a paragraph each, so a dict comparison prints an unreadable wall on the
# one thing this check exists to report.
c.eq("cancel() drops the snapshot", len(sc["fight"]._engagement_snapshot), 0)
sc["fight"].select_to_fight(sc["attacker"])
if sc["fight"].state == fight_module.CHOOSING_TARGET:
    sc["fight"].choose_target_squad(sc["target"])
# A NEW activation is a new target-selection step, so it must see the board as
# it stands now - freezing forever would be the opposite error. Here the squad
# is no longer engaged with anything at all, so _start_fighting() ends the
# activation outright rather than offering a target it cannot reach.
c.eq("a fresh activation re-measures: no target", sc["fight"].target_squad, None)
c.eq("...and offers no melee groups", offers(sc), {})

# The other boundary: an activation that runs to completion must leave nothing
# behind either, or the NEXT unit to fight inherits this one's frozen answers.
sc = started()
swing(sc, SQUAD_CCW)
swing(sc, EXARCH_CCW)
sc["fight"].stop_fighting()   # rule 04.01: "one or more" weapons, not all of them
c.eq("a completed activation ends in SELECTING", sc["fight"].state, fight_module.SELECTING)
c.eq("...and leaves no snapshot behind", len(sc["fight"]._engagement_snapshot), 0)


# -------------------------------------------------------- 5. Split Fire freezes

section("5. Split Fire freezes each assigned target independently")

sc = started(split_fire=True)
fc = sc["fight"]
c.eq("split fire starts in target selection", fc.state, fight_module.CHOOSING_TARGET)
fc.begin_assignment()
c.eq("assignment step reached", fc.state, fight_module.ASSIGNING)
assigned = 0
guard = 0
while fc.state == fight_module.ASSIGNING and guard < 40:
    guard += 1
    pair = fc.current_assignment()
    if pair is None:
        break
    before_len = len(fc.assignment_queue)
    fc.assign_current(sc["target"])
    if len(fc.assignment_queue) < before_len:
        assigned += 1
    else:
        fc.skip_current()
c.true("split fire assigned at least one model+weapon", assigned >= 1)
c.true("the assignment step snapshotted the target", any(
    key[1] is sc["target"] for key in fc._engagement_snapshot))


# ------------------------------------------ 6. live fallback for anything else

section("6. anything never snapshotted is still measured live")

sc = started()
fc, attacker, target = sc["fight"], sc["attacker"], sc["target"]
front = attacker.models[0]
c.eq("the snapshot answers for the selected target", fc._engaged_with(front, target), True)
kill_front(sc)
c.eq("...still, after the casualty", fc._engaged_with(front, target), True)
# A squad that was never a target of this activation has no snapshot entry, so
# _engaged_with() must fall back to live geometry rather than inventing a
# default - eligibility probes for other squads depend on that.
other = tk.build(ae.DIRE_AVENGERS, "Player 2", name="Dire Avengers C")
tk.line_up(other, x=20.0, y=60.0)
c.eq("an unsnapshotted far-off squad measures live (not engaged)", fc._engaged_with(front, other), False)
tk.line_up(other, x=20.0, y=20.9)
c.eq("an unsnapshotted adjacent squad measures live (engaged)", fc._engaged_with(front, other), True)


# ----------------------------------- 7. the AI reads the same frozen answer

section("7. the AI's group list agrees with the panel after a casualty")

from ai import agent_driver

sc = started()
kill_front(sc)
panel = {label: elig for label, (elig, _total) in offers(sc).items()}
ai_pairs = agent_driver._melee_group_pairs(sc["fight"], sc["attacker"])
ai_counts = {}
for key, pairs in ai_pairs.items():
    if not pairs:
        continue
    ai_counts[fight_module._melee_group_label(pairs)] = len(pairs)
# _melee_group_pairs()'s own docstring promises "exactly what
# weapon_eligibility() counts". A live check there made that promise false the
# moment a target's front models died, which is error class 10 in miniature.
c.eq("the AI sees the same non-empty groups as the panel", sorted(ai_counts), sorted(k for k, v in panel.items() if v))
c.eq("...with the same model counts", ai_counts, {k: v for k, v in panel.items() if v})


# ------------------------------------------------------------- 8. source guards

section("8. source guards - the snapshot is taken at every selection point")

src = open("game/fight.py", encoding="utf-8").read()
# Three call sites constitute the target-selection step: the explicit pick, the
# single-target auto-pick that most units actually take, and Split Fire's
# assignment. A snapshot at only some of them looks complete from each one.
c.eq("_snapshot_engagement is called three times", src.count("self._snapshot_engagement("), 3)
def ordered(label, first, second):
    """Both markers present, `first` ahead of `second`. Deliberately not
    src.index() twice: a MISSING marker is exactly what a regression looks
    like here, and it has to read as a failed check rather than a crash that
    takes the rest of the suite's report down with it."""
    a, b = src.find(first), src.find(second)
    c.true(label, a != -1 and b != -1 and a < b)


ordered("the auto-pick branch snapshots before offering reactions",
        "self._snapshot_engagement(targets[0])",
        "self._offer_target_reactions(targets[0])")
ordered("assign_current snapshots BEFORE its engagement check",
        "self._snapshot_engagement(target_squad)\n        model, weapon = self.assignment_queue.pop(0)",
        "if not self._engaged_with(model, target_squad):")
# The read sites the report is about must not go back to live geometry.
# Live geometry is reached from exactly two places: the snapshot builder, and
# _engaged_with()'s fallback for squads this activation never selected. Any
# third call site is a read that can drift back to re-measuring mid-activation.
# Counted rather than matched line-for-line: the guarantee is "exactly two call
# sites, and they are the snapshot builder and the fallback", not how either
# line happens to be wrapped. The literal form went red when the Dragon Knights'
# Agile Reach widened the snapshot expression across two lines - a real change
# that this check should NOT have objected to, and the same lesson the
# indentation pin in test_datasheet_rules.py already carries.
_engaged_calls = [line.strip() for line in src.splitlines()
                  if "model_engaged_with(model, target_squad)" in line]
c.eq("model_engaged_with has exactly two call sites", len(_engaged_calls), 2)
c.true("...the snapshot builder is one of them",
       any("_engagement_snapshot[key]" in line or "model_engaged_with(model, target_squad)" in line
           for line in _engaged_calls)
       and "self._engagement_snapshot[key] = (" in src)
c.true("...and _engaged_with()'s live fallback is the other",
       "return model_engaged_with(model, target_squad)" in _engaged_calls)
c.eq("the snapshot is cleared at all four activation boundaries",
     src.count("self._reset_engagement_snapshot()"), 4)

ai_src = open("ai/agent_driver.py", encoding="utf-8").read()
c.true("the AI reads the controller's snapshot",
       "fight_controller._engaged_with(m, target)" in ai_src)


c.finish()
