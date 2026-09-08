"""Does firing a D-cannon survive - and land - in the REAL main() loop?

User: "absturz im letzten spiel / feuern der d-cannon"
      AttributeError: 'function' object has no attribute 'add'
      (main.py -> shooting_controller.on_dice_acknowledged()
       -> damage_resolution.py:423)

TWO defects on one weapon, and this measures both against the LIVE objects
main() built, with the one shipped list that actually fields the gun:

  1. THE CRASH. The automatic Damage re-roll branch called .add() on a field
     that holds a CALLABLE. The only ability that can reach that branch is the
     D-cannon's Structural Collapse ("re-roll a Damage roll of 1"), so the line
     had never executed until the user fired one.

  2. THE UNEARNED RE-ROLL. "if that attack targets a TITANIC unit, you can
     re-roll the Damage roll INSTEAD" is gated on the target. The offer was
     built with a decision_manager unconditionally, so every roll that was NOT
     a 1 opened a free-re-roll prompt - and the session parked on it, so the
     damage never landed at all.

WHY THE SHOT IS STAGED, AND WHAT IS NOT. A MockAgent run does not reach "a
D-cannon fires AND a save fails AND the Damage die shows a 1" inside any sane
frame budget - this repo's documented harness limit - and a passive counter
would report 0 and read exactly like a pass. So the shot is staged on the board
main() built, through the controller main() built, using the controller's OWN
_begin_resolution()/_begin_damage_allocation() entry points. Everything after
that - the offer, the session, the dice, on_dice_acknowledged(), the wounds -
is the real thing.

REACHABILITY IS MEASURED, NOT ASSUMED: exactly one shipped list fields the
D-cannon Platform (aeldari_guardian_battlehost), and it is fielded here as
PLAYER 1, the human. config ships necrons as player 2, so a question about the
human's weapon asked of the default armies measures the AI's and reports a
truthful-looking nothing.

Usage:  python verify_dcannon_damage_reroll.py [map2] [--neutralize]
        --neutralize restores BOTH halves of the pre-fix world and MUST report
        the reported traceback and the free re-roll.
"""

import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import runpy

MAP = "map2"
NEUTRALIZE = "--neutralize" in sys.argv
for arg in sys.argv[1:]:
    if arg.startswith("map"):
        MAP = arg

from game import config                           # noqa: E402
from game import damage_reduction, molten_form    # noqa: E402
from game import damage_resolution as dr          # noqa: E402
from game import structural_collapse              # noqa: E402
from game.damage_reroll import DamageRerollOffer   # noqa: E402
from game.weapons import DCannonProfile           # noqa: E402

config.PLAYER1_ARMY = "aeldari_guardian_battlehost"   # the only list with D-cannons
config.PLAYER2_ARMY = "necrons"
config.ARMY_SELECT = False
config.MAP_SELECT = False
config.MAP = MAP

RESULTS = {}

FIXED_LINE = 'self.log("%s: re-rolling %s\'s Damage roll of 1."'
BROKEN_LINE = 'self.log.add("%s: re-rolling %s\'s Damage roll of 1."'
FIXED_CONT = "                         % (self.damage_reroll.label, self.weapon.name))"
BROKEN_CONT = "                             % (self.damage_reroll.label, self.weapon.name))"


def _human(locals_):
    ai = set(locals_["ai_players"])
    for player in sorted(locals_["armies"]):
        if player not in ai:
            return player
    return None


def _neutralize_crash():
    """The pre-fix line, restored byte for byte on the live class.

    Derived from the SHIPPED source rather than re-implemented: a probe that
    re-derives the branch's own condition can bite for the wrong reason."""
    import inspect
    src = textwrap.dedent(
        inspect.getsource(dr.DamageAllocationSession.on_damage_roll_acknowledged))
    if src.count(FIXED_LINE) != 1:
        # NOT SystemExit: drive() swallows that, and a probe that fails
        # silently reports a truthful-looking nothing - which is what happened
        # on this script's own first neutralized run.
        RESULTS["error"] = "could not restore the pre-fix log line (anchor moved)"
        return False
    src = src.replace(FIXED_LINE, BROKEN_LINE)
    namespace = dict(vars(dr))
    exec(compile(src, "<pre-fix>", "exec"), namespace)
    dr.DamageAllocationSession.on_damage_roll_acknowledged = (
        namespace["on_damage_roll_acknowledged"])
    return True


def _neutralize_gate(sc):
    """The pre-fix offer: the mandatory half AND the offer half, on any
    target - which is what handed out the free re-roll."""
    original = sc._begin_damage_allocation

    def ungated(rolls, weapon, target_squad, priority_group):
        original(rolls, weapon, target_squad, priority_group)
        session = sc.damage_session
        if session is not None and structural_collapse.applies(sc.active_squad, weapon):
            session.damage_reroll = DamageRerollOffer(
                structural_collapse.STRUCTURAL_COLLAPSE_LABEL,
                automatic_faces=structural_collapse.STRUCTURAL_COLLAPSE_AUTOMATIC_FACES,
                notation=weapon.damage_notation,
                decision_manager=sc.decision_manager, dice_manager=sc.dice_manager,
                game_log=sc.game_log, owner=sc.active_squad.owner,
                weapon_name=weapon.name,
            )

    sc._begin_damage_allocation = ungated


def _fire(sc, shooter, target, first_die, second_die=None):
    """One failed save from the D-cannon, through the LIVE controller."""
    model = next((m for m in shooter.models
                  if any(isinstance(w, DCannonProfile) for w in m.weapons)), None)
    if model is None:
        return None
    gun = next(w for w in model.weapons if isinstance(w, DCannonProfile))
    sc.cancel()
    sc.active_squad = shooter
    # Through _begin_resolution() so current_group is the real thing:
    # on_dice_acknowledged() returns early without one.
    sc._begin_resolution("dcannon", gun.name, [(model, gun)], target)
    before = sum(m.current_wounds for m in target.models)
    sc._begin_damage_allocation([1], gun, target, None)
    session = sc.damage_session
    if session is None:
        return None
    offer = session.damage_reroll
    if session.pending_choice:
        sc.choose_damage_model(session.pending_choice[0])
    sc.dice_manager.last_values = [first_die]
    sc.dice_manager.acknowledge()
    crash, again = None, False
    try:
        sc.on_dice_acknowledged()
        again = (sc.damage_session is not None
                 and sc.damage_session.pending_damage_roll is not None)
        # Whatever the session still owes gets answered, not just the re-roll:
        # rule 24.12's Feel No Pain is its own dice step, and a probe that
        # stops before it reports 0 damage and reads like a failure of the
        # thing being measured. Every FNP die is a 1, so nothing is saved and
        # the number below is the Damage roll itself.
        for _ in range(6):
            session = sc.damage_session
            if session is None:
                break
            if session.pending_damage_roll is not None:
                if second_die is None:
                    break
                sc.dice_manager.last_values = [second_die]
            elif getattr(session, "pending_fnp", None) is not None:
                sc.dice_manager.last_values = [1] * max(
                    1, len(getattr(sc.dice_manager, "last_values", [1]) or [1]))
            else:
                break
            sc.dice_manager.acknowledge()
            sc.on_dice_acknowledged()
    except Exception as exc:                        # noqa: BLE001 - the report itself
        crash = "%s: %s" % (type(exc).__name__, exc)
    return dict(offer=offer, crash=crash, rerolled=again,
                damage=before - sum(m.current_wounds for m in target.models),
                asked=sc.decision_manager.is_pending)


def inspect_frame(locals_):
    human = _human(locals_)
    RESULTS["human"] = human
    state, sc = locals_["state"], locals_["shooting_controller"]

    shooters = [s for s in state.all_squads()
                if s.owner == human
                and any(isinstance(w, DCannonProfile) for m in s.models for w in m.weapons)]
    RESULTS["dcannon_units"] = sorted(s.name for s in shooters)
    foes = [s for s in state.all_squads() if s.owner != human and s.models]
    if not shooters or not foes:
        RESULTS["error"] = "no D-cannon on the board, or no enemy"
        return
    shooter = sorted(shooters, key=lambda s: s.name)[0]

    def _unmitigated(squad):
        """No halving and no flat reduction on any of its models.

        The C'tan Shard is the fattest thing the Necrons field and it carries
        Necrodermis, which quietly turns 8 into 7 - the probe would then be
        measuring that ability instead of this one. Asked of the two modules
        that own the question, so a new source of mitigation excludes its
        carrier here automatically."""
        return all(molten_form.adjusted_damage(m, 8) == 8
                   and damage_reduction.adjusted_damage(m, 8) == 8
                   for m in squad.models)

    # The fattest UNMITIGATED enemy unit: excess damage does not spill over, so
    # against a 1-wound model a re-rolled 8 and a kept 3 both read as 1.
    clean = [s for s in foes if _unmitigated(s)]
    if not clean:
        RESULTS["error"] = "no enemy unit without damage mitigation to measure against"
        return
    target = max(clean, key=lambda s: (max(m.current_wounds for m in s.models), s.name))
    RESULTS["shooter"] = shooter.name
    RESULTS["target"] = "%s (%d wounds on its toughest model)" % (
        target.name, max(m.current_wounds for m in target.models))
    RESULTS["target_titanic"] = structural_collapse.targets_titanic(target)

    locals_["turn_tracker"].turn_owner = human
    locals_["turn_tracker"].set_active(human)

    if NEUTRALIZE:
        if not _neutralize_crash():
            return
        _neutralize_gate(sc)

    def _drain():
        """is_pending is the whole QUEUE, not this shot's own question.

        The live battle can have a prompt of its own standing at this frame, and
        one left over from the first shot would swallow the second - so the
        queue is emptied before each measurement and 'a prompt was raised' then
        means what it says. Without this the reading was intermittently wrong."""
        for _ in range(20):
            if not sc.decision_manager.is_pending:
                return
            sc.decision_manager.choose(len(sc.decision_manager.options) - 1)

    _drain()
    one = _fire(sc, shooter, target, 1, 6)
    RESULTS["one"] = one
    if one is not None:
        RESULTS["offer_built"] = getattr(one["offer"], "label", None)
    _drain()
    RESULTS["four"] = _fire(sc, shooter, target, 4)


def drive(frames=260, at=200):
    import pygame
    fired = []
    count = {"n": 0}
    real_flip = pygame.display.flip

    def flip(*args, **kwargs):
        count["n"] += 1
        if count["n"] == at and not fired:
            fired.append(True)
            frame = sys._getframe(1)
            while frame is not None and frame.f_code.co_name != "main":
                frame = frame.f_back
            if frame is None:
                raise SystemExit("could not reach main()'s frame")
            inspect_frame(frame.f_locals)
        return real_flip(*args, **kwargs)

    pygame.display.flip = flip
    sys.argv = ["selfplay.py", MAP, str(frames)]
    try:
        runpy.run_module("selfplay", run_name="__main__")
    except SystemExit:
        pass
    finally:
        pygame.display.flip = real_flip
    return bool(fired)


if not drive():
    print("FAILED: never reached main()'s frame")
    raise SystemExit(1)

print("\n" + "=" * 74)
print("mode:", "NEUTRALIZED (pre-fix world)" if NEUTRALIZE else "fixed")
print("=" * 74)
if "error" in RESULTS:
    print("FAILED:", RESULTS["error"])
    raise SystemExit(1)

one, four = RESULTS.get("one"), RESULTS.get("four")
print("human player                  : %s" % RESULTS["human"])
print("D-cannon units on the board   : %s" % ", ".join(RESULTS["dcannon_units"]))
print("firing                        : %s" % RESULTS["shooter"])
print("at                            : %s" % RESULTS["target"])
print("target is TITANIC             : %s" % RESULTS["target_titanic"])
print("re-roll offer built           : %s" % RESULTS.get("offer_built"))
print("-" * 74)
if one:
    print("DIE OF 1  crash               : %s" % one["crash"])
    print("          thrown again        : %s" % one["rerolled"])
    print("          prompt raised       : %s" % one["asked"])
    print("          damage landed       : %s   (D6+2 on a re-rolled 6 = 8)" % one["damage"])
if four:
    print("DIE OF 4  crash               : %s" % four["crash"])
    print("          thrown again        : %s" % four["rerolled"])
    print("          PROMPT RAISED       : %s" % four["asked"])
    print("          damage landed       : %s   (D6+2 on a 4 = 6)" % four["damage"])

if one is None or four is None:
    print("\nFAIL - the shot could not be staged, nothing was measured")
    sys.exit(1)

if NEUTRALIZE:
    ok = (one["crash"] is not None and "has no attribute 'add'" in one["crash"]
          and four["asked"] and four["damage"] == 0)
    print("\n" + ("PASS - reproduced: the reported traceback, and a free re-roll "
                  "prompt that swallows the damage"
                  if ok else "FAIL - the pre-fix world was not restored"))
else:
    ok = (one["crash"] is None and one["rerolled"] and not one["asked"]
          and one["damage"] == 8
          and four["crash"] is None and not four["rerolled"] and not four["asked"]
          and four["damage"] == 6)
    print("\n" + ("PASS - the D-cannon fires, re-rolls its 1 without asking, and "
                  "lands its damage" if ok else "FAIL"))
sys.exit(0 if ok else 1)
