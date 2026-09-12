"""game/roll_choice.py: the re-roll offers as BUTTONS on the dice panel.

User: "Momentan akzeptiert man das Würfelergebnis durch ein Klick irgendwo hin.
Besser wäre: Unten im Panel Buttons je nach Situation: Wurf akzeptieren / 1en
wiederholen (wenns geht) / alles wiederholen (wenns geht) / Fehlschläge
wiederholen (wenns geht). Dann poppen nicht so viele Overlays hintereinander
auf."

The tragende claim is PREVIEW == OFFER: what pending_roll_choice() shows as
buttons BEFORE the roll is accepted is exactly what the controller would have
prompted for AFTER it. Both are read here independently - the preview's keys
and counts off the RollChoice, the prompt's off its human-facing LABELS - so a
preview that drifted from the offer is red, not re-derived by the same code.

1. shooting, hit step - ordinary source, mandatory-1s source, no source
2. shooting, the answer rides on the roll - no prompt, the re-roll is thrown
3. shooting, wound step - all three option shapes
4. the melee twins
5. the view - human only, cached per roll, recomputed when the dice change
6. the in-place offers - Advance and Charge
7. the offers asked after acceptance - Damage/Attacks and Reanimation
"""

import os
import re
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk  # noqa: E402
from testkit import Checks  # noqa: E402

from game import roll_choice as rc  # noqa: E402
from game import implacable_eradication, monster_hunters, reroll_scope  # noqa: E402
from game.dice import DiceManager, ADVANCE_ROLL, CHARGE_ROLL  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.factions.orks import BOYZ, FLASH_GITZ  # noqa: E402
from game.factions.tau_empire import STRIKE_TEAM  # noqa: E402

c = Checks("roll choices on the dice panel")

ORDINARY = monster_hunters.MONSTER_HUNTERS_REROLL_LABEL
MANDATORY_ONES = sorted(reroll_scope.ONES_OR_WHOLE_LABELS)[0]

# Read off the LABELS a player is shown - an independent reading of the prompt.
_LABEL_KEYS = (("Keep", rc.ACCEPT), ("1s only", rc.ONES), ("whole", rc.WHOLE), ("failed", rc.FAILURES))


def prompt_keys(decision):
    out = {}
    for label in tk.options_of(decision):
        key = next((k for needle, k in _LABEL_KEYS if needle in label), label)
        m = re.search(r"\((\d+) dice\)", label) or re.search(r"only the (\d+) failed", label)
        out[key] = int(m.group(1)) if m else None
    return out


def choice_keys(choice):
    if choice is None:
        return {}
    return {o.key: (None if o.key == rc.ACCEPT else o.count) for o in choice.options}


def same_offer(label, choice, decision):
    """Keys equal; counts equal wherever the prompt prints one."""
    shown, asked = choice_keys(choice), prompt_keys(decision)
    c.eq(f"{label}: the buttons are the prompt's options", sorted(shown), sorted(asked))
    for key, count in asked.items():
        if count is not None:
            c.eq(f"{label}: '{key}' counts the same dice", shown.get(key), count)


def accept(dm, controller):
    dm.acknowledge()
    controller.on_dice_acknowledged()


# ---------------------------------------------------------------------------
print("--- 1. shooting, hit step ---")


def hit_scene(hit_dice, reason):
    tk.script(*hit_dice, default=6)
    scene = tk.shooting_scene(FLASH_GITZ, STRIKE_TEAM, gap=10.0)
    sc = scene["shooting"]
    sc._hit_reroll_reason = lambda _t, _r=reason: _r
    sc.start_shooting(scene["attacker"])
    sc.choose_target_squad(scene["target"])
    key = next(k for k, *rest in sc.weapon_eligibility() if "Snazzgun" in str(rest[0]))
    sc.choose_weapon(key)
    return scene, sc, scene["dice"], scene["decision"]


scene, sc, dm, dec = hit_scene((1, 1, 2), ORDINARY)
dice_count = len(dm.pending_values)
c.eq("the hit roll is on the table", sc.pending_step, "hit")
c.true("...with more dice than the three misses", dice_count > 3)
preview = sc.pending_roll_choice()
c.eq("an ordinary source shows Accept, failures and the whole roll",
     choice_keys(preview), {rc.ACCEPT: None, rc.FAILURES: 3, rc.WHOLE: dice_count})
c.eq("...and belongs to the shooting player", preview.player, scene["attacker"].owner)
rolled_before = len(dm.rolled)
again = sc.pending_roll_choice()
c.eq("a preview is repeatable", choice_keys(again), choice_keys(preview))
c.eq("...throws no dice", len(dm.rolled), rolled_before)
c.eq("...opens no prompt", dec.is_pending, False)
c.eq("...and spends nothing", sc._hit_reroll_used, False)
c.eq("...and leaves the step where it was", sc.pending_step, "hit")
accept(dm, sc)
same_offer("ordinary hit", preview, dec)

scene, sc, dm, dec = hit_scene((1, 1, 2), MANDATORY_ONES)
preview = sc.pending_roll_choice()
c.eq("a mandatory-1s source with 1s shows failures, whole and the 1s",
     sorted(choice_keys(preview)), sorted([rc.FAILURES, rc.WHOLE, rc.ONES]))
c.eq("...and no Accept", preview.accept_allowed, False)
c.eq("...counting the two 1s", choice_keys(preview).get(rc.ONES), 2)
accept(dm, sc)
same_offer("mandatory 1s hit", preview, dec)

scene, sc, dm, dec = hit_scene((1, 1, 2), None)
c.eq("no re-roll source, no buttons", sc.pending_roll_choice(), None)
accept(dm, sc)
c.eq("...and no prompt either", dec.is_pending, False)


# ---------------------------------------------------------------------------
print("--- 2. the answer rides on the roll ---")

scene, sc, dm, dec = hit_scene((1, 1, 2), ORDINARY)
dm.choose_reroll(rc.FAILURES)
accept(dm, sc)
c.eq("a pressed button opens no prompt", dec.is_pending, False)
c.eq("...throws the failures again", len(dm.pending_values or []), 3)
c.eq("...as spent dice", dm.already_rerolled, {0, 1, 2})
c.eq("...on the re-roll step", sc.pending_step, "hit_monster_hunters_reroll")
c.eq("...spending the once-per-group offer", sc._hit_reroll_used, True)
c.true("...under a heading that says so", (dm.title or "").startswith("Re-roll failures"))

scene, sc, dm, dec = hit_scene((1, 1, 2), ORDINARY)
dm.choose_reroll(rc.ACCEPT)
accept(dm, sc)
c.eq("Accept keeps the result without a prompt", dec.is_pending, False)
c.true("...and the attack moves on past the hit step", sc.pending_step != "hit")
c.eq("...with no hit re-roll thrown", sc._pending_hit_reroll, None)

scene, sc, dm, dec = hit_scene((1, 1, 2), MANDATORY_ONES)
dm.choose_reroll(rc.ONES)
accept(dm, sc)
c.eq("the 1s button throws only the 1s", len(dm.pending_values or []), 2)
c.eq("...on the 1s step", sc.pending_step, "hit_reroll_ones")
c.eq("that roll offers nothing more - the offer was spent", sc.pending_roll_choice(), None)
accept(dm, sc)
c.eq("...and accepting it prompts nothing either", dec.is_pending, False)

scene, sc, dm, dec = hit_scene((1, 1, 2), ORDINARY)
dm.choose_reroll(rc.ONES)
accept(dm, sc)
c.eq("a recorded key the offer does not have falls back to the prompt", dec.is_pending, True)

stale = DiceManager()
stale.roll(count=2)
stale.choose_reroll(rc.WHOLE)
stale.roll(count=2)
c.eq("a new roll clears an old answer", stale.take_chosen_reroll(), None)
stale.choose_reroll(rc.WHOLE)
stale.acknowledge()
c.eq("...but accepting does not - the offer reads it afterwards", stale.take_chosen_reroll(), rc.WHOLE)
c.eq("...once", stale.take_chosen_reroll(), None)


# ---------------------------------------------------------------------------
print("--- 3. shooting, wound step ---")


def wound_scene(wound_dice, reason, full=False):
    scene, sc, dm, dec = hit_scene((), None)
    tk.script(*wound_dice, default=6)
    sc._wound_reroll_reason = lambda _w, _t, _r=reason: _r
    if full:
        sc._wound_reroll_is_full = lambda _w, _t: True
    for _ in range(6):
        if sc.pending_step == "wound" or not dm.is_pending:
            break
        accept(dm, sc)
    return scene, sc, dm, dec


for label, reason, full, want in (
    ("[TWIN-LINKED] (failures only)", "[TWIN-LINKED]", False, {rc.FAILURES, rc.ACCEPT}),
    ("a whole-roll source", "[TWIN-LINKED]", True, {rc.WHOLE, rc.FAILURES, rc.ACCEPT}),
    ("a mandatory-1s wound source", implacable_eradication.IMPLACABLE_ERADICATION_LABEL, False,
     {rc.FAILURES, rc.WHOLE, rc.ONES}),
):
    scene, sc, dm, dec = wound_scene((1, 1, 1), reason, full=full)
    c.eq(f"{label}: the wound roll is on the table", sc.pending_step, "wound")
    preview = sc.pending_roll_choice()
    c.eq(f"{label}: the buttons", set(choice_keys(preview)), want)
    accept(dm, sc)
    same_offer(label, preview, dec)

scene, sc, dm, dec = wound_scene((1, 1, 1), "[TWIN-LINKED]")
dm.choose_reroll(rc.FAILURES)
accept(dm, sc)
c.eq("a pressed wound button opens no prompt", dec.is_pending, False)
c.eq("...and re-rolls the three failures", len(dm.pending_values or []), 3)
c.eq("...on the wound re-roll step", sc.pending_step, "wound_twin_linked_reroll")


# ---------------------------------------------------------------------------
print("--- 4. the melee twins ---")


def swing(hit_dice, reason):
    tk.script(*hit_dice, default=6)
    scene = tk.fight_scene(BOYZ, STRIKE_TEAM)
    fc = scene["fight"]
    fc._hit_reroll_reason = lambda _t, _r=reason: _r
    fc.select_to_fight(scene["attacker"])
    if fc.state == "choosing_target":
        fc.choose_target_squad(scene["target"])
    fc.choose_weapon(fc.weapon_eligibility()[0][0])
    return scene, fc, scene["dice"], scene["decision"]


scene, fc, dm, dec = swing((1, 1, 2), ORDINARY)
c.eq("the melee hit roll is on the table", fc.pending_step, "hit")
preview = fc.pending_roll_choice()
c.eq("melee: an ordinary source shows Accept, failures and the whole roll",
     set(choice_keys(preview)), {rc.ACCEPT, rc.FAILURES, rc.WHOLE})
accept(dm, fc)
same_offer("melee hit", preview, dec)

scene, fc, dm, dec = swing((1, 1, 2), MANDATORY_ONES)
preview = fc.pending_roll_choice()
c.eq("melee: a mandatory-1s source keeps its 1s option and loses Accept",
     set(choice_keys(preview)), {rc.FAILURES, rc.WHOLE, rc.ONES})
accept(dm, fc)
same_offer("melee mandatory 1s", preview, dec)

scene, fc, dm, dec = swing((), None)
tk.script(1, 1, 1, default=6)
fc._wound_reroll_reason = lambda _w, _t: "[TWIN-LINKED]"
for _ in range(6):
    if fc.pending_step == "wound" or not dm.is_pending:
        break
    accept(dm, fc)
c.eq("the melee wound roll is on the table", fc.pending_step, "wound")
preview = fc.pending_roll_choice()
c.eq("melee [TWIN-LINKED]: failures and Accept", set(choice_keys(preview)), {rc.FAILURES, rc.ACCEPT})
accept(dm, fc)
same_offer("melee wound", preview, dec)

scene, fc, dm, dec = swing((1, 1, 2), ORDINARY)
dm.choose_reroll(rc.WHOLE)
accept(dm, fc)
c.eq("melee: a pressed button opens no prompt", dec.is_pending, False)
c.eq("...and re-rolls the whole roll", fc.pending_step, "hit_monster_hunters_reroll")


# ---------------------------------------------------------------------------
print("--- 5. the view ---")

scene, sc, dm, dec = hit_scene((1, 1, 2), ORDINARY)
view = rc.RollChoiceView([sc])
owner = scene["attacker"].owner
other = "Player 1" if owner == "Player 2" else "Player 2"
first = view.pending(dm, {owner})
c.eq("the owner gets the buttons", choice_keys(first).get(rc.FAILURES), 3)
c.eq("the other side gets none - its offer stays a prompt for its own player",
     view.pending(dm, {other}), None)
calls = []
sc.pending_roll_choice = (lambda real=sc.pending_roll_choice: calls.append(1) or real())
view.invalidate()
view.pending(dm, {owner})
view.pending(dm, {owner})
c.eq("one preview per roll, however many frames ask", len(calls), 1)
dm.set_die(0, 6)
changed = view.pending(dm, {owner})
c.eq("changing a die on the table (Command Re-roll, a 6 set by hand) re-asks",
     choice_keys(changed).get(rc.FAILURES), 2)
dm.acknowledge()
c.eq("nothing on offer once the roll is gone", view.pending(dm, {owner}), None)
c.eq("a provider may be a plain callable",
     rc.RollChoiceView([lambda: None]).pending(DiceManager(), {owner}), None)


# ---------------------------------------------------------------------------
print("--- 6. the in-place offers ---")

from game import superlative_strategist as ss  # noqa: E402
from game import charge_reroll  # noqa: E402


class Squad:
    def __init__(self, owner):
        self.owner = owner
        self.name = "Autarch unit"


adv_dm, adv_dec = DiceManager(), DecisionManager()
ctrl = ss.SuperlativeStrategistController(dice_manager=adv_dm, decision_manager=adv_dec)
unit = Squad("Player 1")
original_applies = ss.applies
ss.applies = lambda squad: True
try:
    tk.script(2)
    adv_dm.roll(count=1, label="Advance", roll_kind=ADVANCE_ROLL)
    advance = ctrl.pending_roll_choice(unit)
    c.eq("an Advance re-roll is a button beside Accept",
         set(choice_keys(advance)), {rc.ACCEPT, rc.WHOLE})
    reroll = advance.option(rc.WHOLE)
    c.eq("...that does NOT accept the roll", reroll.acknowledges, False)
    tk.script(5)
    reroll.apply()
    c.eq("pressing it throws the die in place", adv_dm.pending_values, [5])
    c.eq("...the roll stays on the table", adv_dm.is_pending, True)
    c.eq("...and the button is gone", ctrl.pending_roll_choice(unit), None)
    c.eq("...so accepting opens no prompt afterwards",
         ctrl.maybe_offer_advance_reroll(unit), False)

    tk.script(2)
    adv_dm.roll(count=1, label="Advance", roll_kind=ADVANCE_ROLL)
    accepted = ctrl.pending_roll_choice(unit)
    for source in accepted.claims:
        adv_dm.claim_reroll_offer(source)
    c.eq("Accept claims the offer, so the click that accepts opens no prompt",
         ctrl.maybe_offer_advance_reroll(unit), False)
    c.eq("...and nothing was queued", adv_dec.is_pending, False)

    tk.script(2)
    adv_dm.roll(count=2, label="Charge Roll", roll_kind=CHARGE_ROLL)
    c.eq("the Advance offer ignores a roll that is not an Advance", ctrl.pending_roll_choice(unit), None)
    tk.script(2)
    adv_dm.roll(count=1, label="Advance", roll_kind=ADVANCE_ROLL)
    ai_ctrl = ss.SuperlativeStrategistController(dice_manager=adv_dm, decision_manager=adv_dec,
                                                 auto_players=("Player 1",))
    c.eq("an AI-owned Advance gets no button - the AI decides in the controller",
         ai_ctrl.pending_roll_choice(unit), None)
finally:
    ss.applies = original_applies


class Charger:
    def __init__(self, squad, reach):
        self.active_squad = squad
        self._reach = reach

    def targets_reachable_with(self, total):
        return total >= self._reach


class TestCharge(charge_reroll.ChargeRerollController):
    LABEL = "Test Charge Re-roll"

    def applies(self, squad):
        return True


ch_dm, ch_dec = DiceManager(), DecisionManager()
offer = TestCharge(dice_manager=ch_dm, decision_manager=ch_dec,
                   charge_controller=Charger(Squad("Player 1"), reach=7))
tk.script(1, 2)
ch_dm.roll(count=2, label="Charge Roll", roll_kind=CHARGE_ROLL)
charge = offer.pending_roll_choice()
c.eq("a Charge re-roll that could still reach is a button", set(choice_keys(charge)), {rc.ACCEPT, rc.WHOLE})
tk.script(4, 4)
charge.option(rc.WHOLE).apply()
c.eq("...pressed, the charge is re-rolled in full, in place", ch_dm.pending_values, [4, 4])
c.eq("...and offered no more", offer.pending_roll_choice(), None)

far = TestCharge(dice_manager=ch_dm, decision_manager=ch_dec,
                 charge_controller=Charger(Squad("Player 1"), reach=13))
tk.script(1, 2)
ch_dm.roll(count=2, label="Charge Roll", roll_kind=CHARGE_ROLL)
c.eq("no button when not even a 12 would reach - the prompt would not open either",
     far.pending_roll_choice(), None)


# ---------------------------------------------------------------------------
print("--- 7. the offers asked AFTER acceptance: dice notation and reanimation ---")

import ast  # noqa: E402
import io  # noqa: E402

from game import reanimation_protocols as rp  # noqa: E402
from game.factions import necrons as nec  # noqa: E402
from game.notation_reroll import DamageRerollOffer  # noqa: E402
from testkit import GameState  # noqa: E402

# The Damage / Attacks re-roll ("you can re-roll the Damage roll"): one object
# answers the panel's preview AND the prompt, and the panel's answer is taken
# on its SYNCHRONOUS path.
n_dm, n_dec = DiceManager(), DecisionManager()
offer = DamageRerollOffer("Sunforge", decision_manager=n_dec, dice_manager=n_dm,
                          owner="Player 1", weapon_name="Fusion Blaster")
tk.script(3)
n_dm.roll(count=1, label="Damage")
notation_choice = offer.pending_choice(3)
c.eq("a Damage re-roll is Accept plus the whole roll", choice_keys(notation_choice),
     {rc.ACCEPT: None, rc.WHOLE: 1})
c.eq("...for the attacking player", notation_choice.player, "Player 1")
c.eq("no panel answer yet reads as 'not answered'", offer.panel_answer(), None)
n_dm.choose_reroll(rc.WHOLE)
n_dm.acknowledge()
c.eq("a pressed re-roll is read after acceptance as True", offer.panel_answer(), True)
c.eq("...and only once", offer.panel_answer(), None)
tk.script(3)
n_dm.roll(count=1, label="Damage")
n_dm.choose_reroll(rc.ACCEPT)
n_dm.acknowledge()
c.eq("a pressed Accept is read as False - keep it", offer.panel_answer(), False)
c.eq("without an answer the prompt still opens", offer.maybe_offer(3, lambda again: None), True)
c.eq("...as a real decision", n_dec.is_pending, True)
c.eq("a mandatory-only source (not offerable) shows no buttons",
     DamageRerollOffer("Structural Collapse", decision_manager=DecisionManager(), dice_manager=DiceManager(),
                       owner="Player 1", offerable=False).pending_choice(3), None)
c.eq("nobody to ask, no buttons",
     DamageRerollOffer("Sunforge", dice_manager=DiceManager(), owner="Player 1").pending_choice(3), None)


def _asks_panel_first(path, expect_at_least):
    """Every function that raises a notation offer's prompt asks the panel's
    answer first - maybe_offer() returning True means 'the answer comes later',
    which an answer already in hand must never claim."""
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    seen, wrong = 0, []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        offers = [n.lineno for n in calls if n.func.attr == "maybe_offer"]
        answers = [n.lineno for n in calls if n.func.attr == "panel_answer"]
        if not offers or not answers:
            continue
        seen += 1
        if min(answers) > min(offers):
            wrong.append(fn.name)
    c.true(f"{path}: the panel-answer sweep found its offer sites ({seen})", seen >= expect_at_least)
    c.eq(f"{path}: no notation offer is raised before the panel's answer is asked", wrong, [])


_asks_panel_first(os.path.join("game", "damage_resolution.py"), 1)
_asks_panel_first(os.path.join("game", "shooting.py"), 1)
_preview_src = ast.get_source_segment(
    io.open(os.path.join("game", "shooting.py"), encoding="utf-8").read(),
    next(n for n in ast.walk(ast.parse(io.open(os.path.join("game", "shooting.py"), encoding="utf-8").read()))
         if isinstance(n, ast.FunctionDef) and n.name == "pending_roll_choice"))
c.true("the shooting preview asks the Attacks and the Damage offer objects themselves",
       _preview_src.count(".pending_choice(") >= 2)

# Reanimation Protocols' Necron Warriors re-roll: offered as a button while the
# die is on the table, taken after acceptance instead of a prompt.
r_state = GameState()
warriors = tk.build(nec.NECRON_WARRIORS, "Player 2", name="2 Necron Warriors 1")
tk.line_up(warriors, x=20.0, y=20.0)
r_state.tokens = list(warriors.models)
# Three dead: the re-roll is only offered when the unit can use more than one
# wound (reanimation_protocols.REANIMATION_REROLL_FLOOR) - one dead 1-wound
# Warrior would make the offer inert, and the section would measure nothing.
for _model in warriors.models[:3]:
    _model.current_wounds = 0
r_state.remove_dead_models()
c.true("the Warriors really can re-roll a 1 here", rp.can_reroll(warriors, 1))


def reanimation(answer):
    r_dm, r_dec = DiceManager(), DecisionManager()
    ctrl = rp.ReanimationProtocolsController(dice_manager=r_dm, decision_manager=r_dec, game_log=tk.Log(),
                                             game_state=r_state, auto_players=())
    tk.script(1, default=3)
    ctrl.begin_command_phase({warriors}, "Player 2")
    shown = ctrl.pending_roll_choice()
    if answer is not None:
        r_dm.choose_reroll(answer)
    r_dm.acknowledge()
    ctrl.on_dice_acknowledged()
    return ctrl, r_dm, r_dec, shown


ctrl, r_dm, r_dec, shown = reanimation(None)
c.eq("a reanimation die a human may re-roll is Accept plus Re-roll", choice_keys(shown),
     {rc.ACCEPT: None, rc.WHOLE: 1})
c.eq("...and without a panel answer the prompt still opens", r_dec.is_pending, True)
ctrl, r_dm, r_dec, shown = reanimation(rc.WHOLE)
c.eq("pressed Re-roll: no prompt", r_dec.is_pending, False)
c.true("...the die is thrown again as a re-roll", r_dm.is_pending and bool(r_dm.already_rerolled))
c.eq("...and that re-roll offers nothing more", ctrl.pending_roll_choice(), None)
ctrl, r_dm, r_dec, shown = reanimation(rc.ACCEPT)
c.eq("pressed Accept: no prompt either", r_dec.is_pending, False)
c.eq("...and nothing is thrown again", bool(r_dm.already_rerolled), False)


# ---------------------------------------------------------------------------
print("--- 8. a re-roll never offers a re-roll ---")
# User, with a screenshot of "RE-ROLL 1S TO WOUND" carrying "RE-ROLL FAILURES
# (6)": "bei rerolls, sollte es keine reroll option geben. man darf rerolls
# nicht rerollen." The button meant the OTHER failures of the roll before -
# shooting.py threw a source's automatic 1s first and asked about the optional
# re-roll afterwards, so the question sat on the 1s re-roll. It is now asked on
# the roll as thrown, and declining it is what throws the 1s.

scene, sc, dm, dec = hit_scene((1, 1, 2), ORDINARY)
sc._forward_observers_applies = lambda _t: True
dice_count = len(dm.pending_values)
preview = sc.pending_roll_choice()
c.eq("hit, automatic 1s + an optional re-roll: the choice is on the roll as thrown",
     choice_keys(preview), {rc.ACCEPT: None, rc.FAILURES: 3, rc.WHOLE: dice_count})
accept(dm, sc)
same_offer("automatic 1s + ordinary hit", preview, dec)
c.true("...and its decline says the 1s still go",
       any(label.startswith("Keep result") and "1s" in label for label in tk.options_of(dec)))

scene, sc, dm, dec = hit_scene((1, 1, 2), ORDINARY)
sc._forward_observers_applies = lambda _t: True
dm.choose_reroll(rc.ACCEPT)
accept(dm, sc)
c.eq("hit: Accept throws the automatic 1s", sc.pending_step, "hit_reroll_ones")
c.eq("...only the two of them", len(dm.pending_values or []), 2)
c.eq("...without a prompt", dec.is_pending, False)
c.eq("THE REPORT: the 1s re-roll carries no buttons", sc.pending_roll_choice(), None)
tk.script(1, 1)
accept(dm, sc)
c.eq("...and accepting it asks nothing", dec.is_pending, False)
c.true("...the attack moves on", sc.pending_step not in ("hit", "hit_reroll_ones"))

scene, sc, dm, dec = hit_scene((1, 1, 2), ORDINARY)
sc._forward_observers_applies = lambda _t: True
dm.choose_reroll(rc.FAILURES)
accept(dm, sc)
c.eq("hit: 're-roll failures' throws all three - the 1s included", len(dm.pending_values or []), 3)
c.eq("...as spent dice", dm.already_rerolled, {0, 1, 2})
c.eq("...and that re-roll carries no buttons either", sc.pending_roll_choice(), None)
tk.script(1, 1, 1)
accept(dm, sc)
c.eq("...accepting it asks nothing", dec.is_pending, False)
c.true("...and no 1 is thrown a second time", sc.pending_step != "hit_reroll_ones")

scene, sc, dm, dec = wound_scene((1, 1, 1), "[TWIN-LINKED]")
sc._forward_observers_applies = lambda _t: True
preview = sc.pending_roll_choice()
c.eq("wound, automatic 1s + [TWIN-LINKED]: asked on the Wound roll",
     set(choice_keys(preview)), {rc.ACCEPT, rc.FAILURES})
c.eq("...its failures count the 1s (all three dice are 1s - the old order threw them first and offered nothing)",
     choice_keys(preview).get(rc.FAILURES), 3)
accept(dm, sc)
same_offer("automatic 1s + [TWIN-LINKED]", preview, dec)

scene, sc, dm, dec = wound_scene((1, 1, 1), "[TWIN-LINKED]")
sc._forward_observers_applies = lambda _t: True
dm.choose_reroll(rc.ACCEPT)
accept(dm, sc)
c.eq("wound: Accept throws the automatic 1s", sc.pending_step, "wound_reroll_ones")
c.eq("...all three of them", len(dm.pending_values or []), 3)
c.eq("THE REPORT, wound side: no buttons on it", sc.pending_roll_choice(), None)
tk.script(1, 1, 1)
accept(dm, sc)
c.eq("...and accepting it asks nothing", dec.is_pending, False)

scene, sc, dm, dec = wound_scene((1, 1, 1), "[TWIN-LINKED]")
sc._forward_observers_applies = lambda _t: True
dm.choose_reroll(rc.FAILURES)
accept(dm, sc)
c.eq("wound: 're-roll failures' throws all three failures", len(dm.pending_values or []), 3)
c.eq("...and that re-roll carries no buttons", sc.pending_roll_choice(), None)
tk.script(1, 1, 1)
accept(dm, sc)
c.eq("...accepting it asks nothing", dec.is_pending, False)
c.true("...and the 1s do not go again", sc.pending_step != "wound_reroll_ones")


class _Warrior:
    """Path of the Warrior's automatic 1s, on the roll this section asks about."""

    def __init__(self, hit=False, wound=False):
        self._hit, self._wound = hit, wound

    def hit_ones_apply(self, _squad):
        return self._hit

    def wound_ones_apply(self, _squad):
        return self._wound

    def offer(self, _squad):
        return None


# The melee side always asked first - but keeping the result skipped straight
# to the resolution and DROPPED a source's mandatory 1s.
scene, fc, dm, dec = swing((1, 1, 2), ORDINARY)
fc.path_of_the_warrior = _Warrior(hit=True)
c.eq("melee: an optional re-roll is asked on the roll as thrown",
     set(choice_keys(fc.pending_roll_choice())), {rc.ACCEPT, rc.FAILURES, rc.WHOLE})
dm.choose_reroll(rc.ACCEPT)
accept(dm, fc)
c.eq("melee: keeping the result still throws the mandatory 1s", fc.pending_step, "hit_reroll_ones")
c.eq("...the two of them", len(dm.pending_values or []), 2)
c.eq("...and that re-roll carries no buttons", fc.pending_roll_choice(), None)
accept(dm, fc)
c.eq("...nor asks anything", dec.is_pending, False)

scene, fc, dm, dec = swing((), None)
fc.path_of_the_warrior = _Warrior(wound=True)
tk.script(1, 1, 2, default=6)
fc._wound_reroll_reason = lambda _w, _t: "[TWIN-LINKED]"
for _ in range(6):
    if fc.pending_step == "wound" or not dm.is_pending:
        break
    accept(dm, fc)
dm.choose_reroll(rc.ACCEPT)
accept(dm, fc)
c.eq("melee wound: keeping the result still throws the mandatory 1s", fc.pending_step, "wound_reroll_ones")
c.eq("...and that re-roll carries no buttons", fc.pending_roll_choice(), None)

# The structural half: neither controller previews a re-roll step at all.
for path in (os.path.join("game", "shooting.py"), os.path.join("game", "fight.py")):
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "pending_roll_choice"), None)
    steps = set()
    for node in ast.walk(fn) if fn is not None else ():
        if isinstance(node, ast.Compare) and any(isinstance(op, ast.NotIn) for op in node.ops):
            for comp in node.comparators:
                if isinstance(comp, ast.Tuple):
                    steps |= {e.value for e in comp.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    c.true(f"{path}: the preview names the first-throw steps ({sorted(steps)})", {"hit", "wound"} <= steps)
    c.eq(f"{path}: ...and no re-roll step", sorted(s for s in steps if "reroll" in s), [])


# ---------------------------------------------------------------------------
print("--- 9. the Stratagem and ability buttons (ability_actions) ---")
# User: "buttons für fähigkeiten und stratagems sollen doch mit in das würfel
# panel rein, statt links in die spalte."


class _Ctrl:
    def __init__(self, usable=True, label="Crystal Matrix"):
        self.selecting_die = False
        self.usable = usable
        self.label = label
        self.calls = []

    def can_use(self):
        return self.usable

    def start(self):
        self.calls.append("start")

    def cancel_selection(self):
        self.calls.append("cancel")
        self.selecting_die = False

    def panel_label(self):
        return self.label


class _Six:
    def __init__(self, sources=("shrine", "fates")):
        self.selecting_die = False
        self._sources = sources
        self.started = []

    def available_sources(self):
        return [(s, None, None) for s in self._sources]

    def label_for(self, source):
        return f"{source} button"

    def start(self, source):
        self.started.append(source)

    def cancel_selection(self):
        self.selecting_die = False


command, array, six = _Ctrl(), _Ctrl(), _Six()
hint, actions = rc.ability_actions(command, array, six)
c.eq("nothing is being picked, so no hint", hint, None)
c.eq("Command Re-roll, the activation re-roll, then one button per unmodified-6 source",
     [o.key for o in actions],
     [rc.COMMAND_REROLL, rc.ACTIVATION_REROLL, rc.UNMODIFIED_SIX, rc.UNMODIFIED_SIX])
c.eq("...with their own labels",
     [o.label for o in actions], ["Command Re-roll (1 CP)", "Crystal Matrix", "shrine button", "fates button"])
c.eq("...none of them accepts the roll", [o.acknowledges for o in actions], [False] * 4)
c.eq("...and only the CP spend wears the Stratagem accent",
     [o.accent for o in actions], ["stratagem", None, None, None])
for option in actions:
    option.apply()
c.eq("each button starts its own controller", (command.calls, array.calls, six.started),
     (["start"], ["start"], ["shrine", "fates"]))

c.eq("a label-less activation re-roll falls back to Targeting Array",
     [o.label for o in rc.ability_actions(None, _Ctrl(label=""), None)[1]], ["Targeting Array"])
c.eq("a controller that cannot be used draws no button",
     rc.ability_actions(_Ctrl(usable=False), _Ctrl(usable=False), _Six(sources=()))[1], [])

for which, want_hint in (("command", rc.REROLL_PICK_HINT), ("array", rc.REROLL_PICK_HINT),
                         ("six", rc.UNMODIFIED_SIX_PICK_HINT)):
    command, array, six = _Ctrl(), _Ctrl(), _Six()
    picking = {"command": command, "array": array, "six": six}[which]
    picking.selecting_die = True
    hint, actions = rc.ability_actions(command, array, six)
    c.eq(f"picking a die for {which}: only its Cancel", [(o.key, o.accent) for o in actions],
         [(rc.CANCEL, "danger")])
    c.eq(f"...with the hint for that pick", hint, want_hint)
    if actions:
        actions[0].apply()
    c.eq(f"...and Cancel closes THAT pick", picking.selecting_die, False)

c.finish()
