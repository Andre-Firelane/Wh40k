"""game/reroll_scope.py: WHICH dice a granted re-roll may be thrown over, and
what the seven mandatory-1s sources do and do not change about that.

The module had no suite of its own. Its assurances lived scattered over ten
faction suites as single membership lines, and the one thing none of them
checked was the OPTION LIST the player is actually shown - which is exactly
where the reported bug was:

    "Fireknife kann all failed hits rerollen, wenn Gegner noch volles Leben
     hat. das wurde mir nicht angeboten."

Reproduced from the reported game (logs/game_20260911_132318.log:284-285): the
player was offered the whole roll or the 1s, took the whole roll because it was
the only thing on the table that touched his misses, and went from 6 hits to 5.

Four call sites build that list - hit and wound, in game/shooting.py and
game/fight.py - and this file drives all four for EVERY label in the set, so a
fix that reaches only one twin is red. It is a SET DIFFERENCE rather than a
list of ability names: an eighth source cannot be added without this file
moving.
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk  # noqa: E402
from game import reroll_scope  # noqa: E402
from game import monster_hunters  # noqa: E402
from game.factions import tau_empire as tau  # noqa: E402

checks = tk.Checks("Re-roll scope")

# A roll where "failed" and "the 1s" are DIFFERENT sizes. The obvious fixture
# (every miss a 1) makes both options read the same count, and then nothing
# here can tell which option it is looking at - the trap the Windriders suite
# had been sitting in.
FREE_HITS, FREE_TOTAL, ONES = 3, 6, 2
FREE_MISSES = FREE_TOTAL - FREE_HITS          # 3
FREE_NO_EFFECT = 3


def hit_options(controller, target, label):
    """The option labels the hit step would offer for `label`."""
    controller._hit_reroll_reason = lambda _t, _l=label: _l
    controller._hit_reroll_used = False
    controller.decision_manager._queue.clear()
    weapon = target.models[0].weapons[0]
    controller._offer_hit_reroll_choice(
        FREE_HITS, 0, weapon, target, "W", 4,
        (FREE_HITS, 0, FREE_TOTAL), "Player 2", ones=ONES,
    )
    return tk.options_of(controller.decision_manager)


def wound_options(controller, target, label, profile):
    """The option labels the wound step would offer for `label`."""
    controller._wound_reroll_reason = lambda _w, _t, _l=label: _l
    controller._twin_linked_used = False
    controller.decision_manager._queue.clear()
    weapon = target.models[0].weapons[0]
    controller._offer_twin_linked_choice(
        FREE_NO_EFFECT, 3, 0, weapon, target, profile, "W", 4, "Player 2",
        rerollable=(3, 0, FREE_NO_EFFECT), ones=ONES,
    )
    return tk.options_of(controller.decision_manager)


def has(labels, needle):
    return any(needle in l for l in labels)


# --- 1. the set itself ------------------------------------------------------
print("--- 1. the set ---")

LABELS = sorted(reroll_scope.ONES_OR_WHOLE_LABELS)
checks.true("the sweep found the sources", len(LABELS) >= 7)
checks.eq("an unlisted source is not one of them",
          reroll_scope.is_ones_or_whole("[TWIN-LINKED]"), False)
checks.eq("...nor is a label nobody uses", reroll_scope.is_ones_or_whole(None), False)


# --- 2. the HIT step, for every label ---------------------------------------
print("--- 2. the hit step ---")

_shoot = tk.shooting_scene(tau.CRISIS_FIREKNIFE, tau.KROOT_CARNIVORES,
                           attacker_owner="Player 2")
_sc = _shoot["shooting"]
_sc.active_squad = _shoot["attacker"]
_target = _shoot["target"]

for label in LABELS:
    labels = hit_options(_sc, _target, label)
    # The reported one. "you can re-roll the Hit roll instead" is a permission
    # PER ATTACK, so throwing fewer dice than allowed is forbearance.
    checks.true(f"{label}: the failures are on offer",
                has(labels, f"Re-roll failed hit rolls ({FREE_MISSES} dice)"))
    checks.true(f"{label}: ...and the whole roll",
                has(labels, f"Re-roll the whole Hit roll ({FREE_TOTAL} dice)"))
    # ...and what membership DOES decide: the base clause is mandatory, so
    # declining outright is not among the answers.
    checks.true(f"{label}: ...and the 1s, in place of keeping the result",
                has(labels, f"Re-roll the 1s only ({ONES} dice)"))
    checks.eq(f"{label}: ...with no 'Keep result'",
              [l for l in labels if "Keep" in l], [])
    checks.eq(f"{label}: exactly three options", len(labels), 3)

# THE counter-check. Without it every line above is satisfied by a build in
# which the distinction was deleted outright and every source offers all three.
_ordinary = hit_options(_sc, _target, monster_hunters.MONSTER_HUNTERS_REROLL_LABEL)
checks.true("an ordinary source still offers the failures",
            has(_ordinary, "Re-roll failed hit rolls"))
checks.true("...and the whole roll", has(_ordinary, "Re-roll the whole Hit roll"))
checks.true("...but KEEPS 'Keep result' - its 1s are not mandatory",
            has(_ordinary, "Keep result"))
checks.eq("...and offers no '1s only'", [l for l in _ordinary if "1s only" in l], [])

# A roll with nothing to mend must not offer to mend it (error class 5).
_sc._hit_reroll_reason = lambda _t: LABELS[0]
_sc._hit_reroll_used = False
_sc.decision_manager._queue.clear()
_sc._offer_hit_reroll_choice(
    FREE_TOTAL, 0, _target.models[0].weapons[0], _target, "W", 4,
    (FREE_TOTAL, 0, FREE_TOTAL), "Player 2", ones=0)
_clean = tk.options_of(_sc.decision_manager)
checks.eq("with every die a hit, no failures option is offered",
          [l for l in _clean if "failed hit" in l], [])

# The failures are a SUPERSET of the 1s - a natural 1 always misses (05.02) -
# so taking them can never sidestep the mandatory clause.
checks.true("the failures always include the 1s", FREE_MISSES >= ONES)


# --- 3. the WOUND step, for every label -------------------------------------
print("--- 3. the wound step ---")

_profile = _target.models[0].profile
for label in LABELS:
    labels = wound_options(_sc, _target, label, _profile)
    checks.true(f"{label}: the failed wounds are on offer",
                has(labels, f"Re-roll failed wound rolls ({FREE_NO_EFFECT} dice)"))
    checks.true(f"{label}: ...and the whole roll",
                has(labels, "Re-roll the whole Wound roll"))
    checks.true(f"{label}: ...and the 1s", has(labels, f"Re-roll the 1s only ({ONES} dice)"))
    checks.eq(f"{label}: ...with no 'Keep result'",
              [l for l in labels if "Keep" in l], [])

_ordinary_w = wound_options(_sc, _target, "[TWIN-LINKED]", _profile)
checks.true("an ordinary wound source still offers the failures",
            has(_ordinary_w, "Re-roll failed wound rolls"))
checks.eq("...and offers no '1s only'",
          [l for l in _ordinary_w if "1s only" in l], [])


# --- 4. the melee twins -----------------------------------------------------
print("--- 4. the melee twins ---")
# The same four call sites, in the other attack step. A fix that reaches only
# game/shooting.py leaves half the engine reading the old way.

_fight = tk.fight_scene(tau.CRISIS_FIREKNIFE, tau.KROOT_CARNIVORES,
                        attacker_owner="Player 2")
_fc = _fight["fight"]
_fc.fighting_squad = _fight["attacker"]
_ftarget = _fight["target"]

for label in LABELS:
    labels = hit_options(_fc, _ftarget, label)
    checks.true(f"melee {label}: the failures are on offer",
                has(labels, f"Re-roll failed hit rolls ({FREE_MISSES} dice)"))
    checks.eq(f"melee {label}: ...with no 'Keep result'",
              [l for l in labels if "Keep" in l], [])

_fprofile = _ftarget.models[0].profile
for label in LABELS:
    labels = wound_options(_fc, _ftarget, label, _fprofile)
    checks.true(f"melee {label}: the failed wounds are on offer",
                has(labels, f"Re-roll failed wound rolls ({FREE_NO_EFFECT} dice)"))

# ...and the DICE the option throws have to name the ability that threw them.
# fight._reroll_wound() hard-coded "[TWIN-LINKED]" into that label, so an
# Implacable Eradication re-roll announced itself as a different ability
# entirely - a diagnostic line that sends the next investigation to the wrong
# datasheet. Checked on the melee side because that is where it was wrong;
# the shooting twin has always passed its reason through.
_melee_label = None
for label in LABELS:
    wound_options(_fc, _ftarget, label, _fprofile)
    tk.script(default=6)
    tk.pick_option(_fc.decision_manager, "failed wound rolls")
    _melee_label = _fc.dice_manager.label or ""
    checks.true(f"melee {label}: the dice name the source that threw them",
                label in _melee_label)
checks.eq("...and not some other ability",
          "[TWIN-LINKED]" in (_melee_label or ""), False)


# --- 5. the offer is spent by being MADE ------------------------------------
print("--- 5. spent on offering ---")
# game/fight.py has always marked the offer used before raising it;
# game/shooting.py did not, and only its "1s only" branch returns through
# _finish_hit_roll(). So that one path could re-open the gate and hand the
# ability a second use of its once-per-group offer.

_sc._hit_reroll_used = False
_sc.decision_manager._queue.clear()
_sc._hit_reroll_reason = lambda _t: LABELS[0]
_sc._offer_hit_reroll_choice(
    FREE_HITS, 0, _target.models[0].weapons[0], _target, "W", 4,
    (FREE_HITS, 0, FREE_TOTAL), "Player 2", ones=ONES)
checks.true("the shooting offer is marked spent as it is raised", _sc._hit_reroll_used)
checks.eq("...so the gate will not re-open on the same weapon group",
          _sc._hit_reroll_choice_needed(_target, FREE_TOTAL), False)

_fc._hit_reroll_used = False
_fc.decision_manager._queue.clear()
_fc._hit_reroll_reason = lambda _t: LABELS[0]
_fc._offer_hit_reroll_choice(
    FREE_HITS, 0, _ftarget.models[0].weapons[0], _ftarget, "W", 4,
    (FREE_HITS, 0, FREE_TOTAL), "Player 2", ones=ONES)
checks.true("the melee offer is too - it always was", _fc._hit_reroll_used)

# Deliberately NOT inside _begin_ones_reroll(): that is also Forward Observers'
# automatic path, and spending the flag there would eat a later Monster Hunters
# offer that has nothing to do with it.
_shoot_src = io.open(os.path.join("game", "shooting.py"), encoding="utf-8").read()
_ones_body = _shoot_src[_shoot_src.index("def _begin_ones_reroll"):]
_ones_body = _ones_body[:_ones_body.index("\n    def ", 10)]
checks.eq("the automatic 1s path does not spend the offer",
          "_hit_reroll_used" in _ones_body, False)


# --- 6. the source guard: no call site may suppress the failures ------------
print("--- 6. source guard ---")
# A behaviour test cannot see the EIGHTH source, because it does not exist yet.
# This can: in all four option builders, the failures entry must not sit under
# a condition that asks whether the source is a mandatory-1s one.

import ast  # noqa: E402

GUARDED = [(os.path.join("game", "shooting.py"), "_offer_hit_reroll_choice"),
           (os.path.join("game", "shooting.py"), "_offer_twin_linked_choice"),
           (os.path.join("game", "fight.py"), "_offer_hit_reroll_choice"),
           (os.path.join("game", "fight.py"), "_offer_twin_linked_choice")]


def failures_guarded_by_scope(path, method):
    """Whether `method`'s failures-only option is built under a test that asks
    the ones-or-whole question.

    The INNERMOST enclosing `if` is the one that decides. The wound step keeps
    two separate option lists, one per shape, so its failures entry does sit
    inside an `is_ones_or_whole` branch - and that is correct, because the
    other shape has its own. What must never come back is a condition whose
    whole job is to withhold the option from these sources.

    None means the option was not found at all, which is its own failure."""
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != method:
            continue
        innermost, best = None, None
        for sub in ast.walk(node):
            if not isinstance(sub, ast.If):
                continue
            body_src = ast.dump(ast.Module(body=sub.body, type_ignores=[]))
            if "Re-roll failed" not in body_src:
                continue
            size = len(body_src)
            if best is None or size < best:
                innermost, best = sub, size
        if innermost is None:
            return None
        test_src = ast.dump(innermost.test)
        return any(token in test_src
                   for token in ("is_ones_or_whole", "swift", "ones_or_whole"))
    return None


for path, method in GUARDED:
    checks.eq(f"{os.path.basename(path)}:{method} offers the failures unconditionally",
              failures_guarded_by_scope(path, method), False)

checks.finish()
