"""A rule offers; only the ANSWER is deterministic.

User: "die KI soll das zwar deterministisch anwenden, aber die Funktion selbst
soll nicht deterministisch sein. wenn ein Mensch zb. necrons spielt, muss er
die stratagems, Faehigkeiten und Platzierung der Modelle manuell ganz normal
steuern koennen."

The pattern was already right in ~83 modules; these are the places it was not.
Three shapes, and the middle one is the one that hides best:

  1. A DEAD GATE - `auto_players` stored and never read, so the rule resolved
     itself for a human too. Word of the Phoenix ran out of main.py for
     WHICHEVER player's Command phase it was, Player 1 included, and its own
     docstring described the gate it did not have.

  2. A PRE-FILTER - the gate is there and correct, but an "is this worth it"
     verdict runs ABOVE it, so a human is only ever shown the option when the
     engine already agreed with it. The human is asked to ratify a decision
     that was made for them. 'Ard as Nails and Sickening Impact both did this.

  3. NO CHANNEL AT ALL - Pestilent Fallout had `auto_players` and no
     `decision_manager`, so its gate was literally dead code (both branches
     byte-identical) and the enfeeble target was picked by the AI's damage
     ranking for both sides. Bounty Hunters had neither.

THE LINE THAT DECIDES WHAT STAYS AUTOMATIC. Eligibility and inertness are
suppressed for everyone - the rule does not permit it, or the option provably
buys nothing (Fehlerklasse 5). Desirability is AI policy only: whether a CP, a
token or a risk is worth it is the player's call, however the estimator would
have answered.
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import testkit as tk
from testkit import Checks, GameState
from game.decision import DecisionManager

c = Checks("deterministic gates")

HUMAN, AI = "Player 1", "Player 2"


def offered(dm):
    """The labels currently on offer, or [] when nothing is pending.

    Never dm.options directly: that is None with no prompt open, and every
    probe that removes a prompt would then CRASH this suite instead of
    reddening it. A suite that crashes does not say which check broke - this
    repo has recorded that lesson six times now."""
    return [o["label"] for o in (dm.options or ())]


# --------------------------------------------------------------------------
# 1. The Necron Warriors re-roll: offered on the RULE, decided on POLICY
# --------------------------------------------------------------------------
print("=== 1. the re-roll a human never saw ===")

from game import reanimation_protocols as rp          # noqa: E402
from game.factions.necrons import NECRON_WARRIORS     # noqa: E402


def warriors(owner=HUMAN, dead=3):
    squad = tk.build(NECRON_WARRIORS, owner, name=f"{owner[-1]} Necron Warriors 1")
    tk.line_up(squad)
    for model in squad.models[:dead]:
        squad.models.remove(model)
        squad.destroyed_models.append(model)
    return squad


hurt = warriors()
c.true("the premise: these Warriors can recover more than one wound",
       rp.recoverable_wounds(hurt) >= rp.REANIMATION_REROLL_FLOOR)

# THE REPORTED SHAPE. A 2 or a 3 was never offered, because should_reroll()
# said it was not worth it - an AI judgement gating a human's prompt.
c.true("a rolled 1 may be re-rolled", rp.can_reroll(hurt, 1))
c.true("...and so may a 2, which used to be refused", rp.can_reroll(hurt, 2))
c.eq("the AI still only re-rolls a 1", rp.should_reroll(hurt, 1), True)
c.eq("...and keeps a 2, which is its policy and nobody else's",
     rp.should_reroll(hurt, 2), False)

# INERTNESS still suppressed for everyone, which is the other half of the line.
c.eq("a 3 on a D3 cannot be improved, so nobody is asked", rp.can_reroll(hurt, 3), False)
barely = warriors(dead=0)
barely.models[0].current_wounds = barely.models[0].profile.wounds - 1
c.eq("a unit one wound short gains nothing from a better roll either",
     rp.can_reroll(barely, 1), False)
c.true("...and that really is the inert case",
       rp.recoverable_wounds(barely) < rp.REANIMATION_REROLL_FLOOR)


def reanimation_scene(owner, rolled):
    """Drive the REAL controller to the point where the re-roll is decided."""
    squad = warriors(owner)
    dice, dm = tk.RecordingDice(), DecisionManager()
    ctrl = rp.ReanimationProtocolsController(
        dice_manager=dice, decision_manager=dm, game_state=GameState(),
        auto_players=(AI,),
    )
    ctrl._current = squad
    ctrl._reroll_offered = False
    dice.last_values = [rolled]
    ctrl.on_dice_acknowledged()
    return squad, dm


for rolled in (1, 2):
    _sq, dm = reanimation_scene(HUMAN, rolled)
    c.eq(f"a human who rolls a {rolled} is asked", dm.is_pending, True)
_sq, dm = reanimation_scene(AI, 2)
c.eq("the AI is never asked - it answers itself, free", dm.is_pending, False)


# --------------------------------------------------------------------------
# 2. The Resurrection Orb: the human picks the unit, not the alphabet
# --------------------------------------------------------------------------
print("\n=== 2. the orb's candidate list ===")

from game.resurrection_orb import ResurrectionOrbController  # noqa: E402
from game.factions.necrons import OVERLORD                   # noqa: E402
from game.factions import necrons as nec                     # noqa: E402
from game import attached_units                              # noqa: E402
from game import reanimation_protocols                       # noqa: E402


def orb_scene(owner):
    """Two orb-bearing units of the same owner, hurt by different amounts.

    Built the way test_necron_abilities.py builds its own orb scene, and the
    two details it encodes are both traps: the orb is a TOKEN flag set by a
    Gear item that is CONDITIONAL on having traded the Tachyon Arrow away
    (hence `choices`), and models have to die through remove_dead_models() -
    moving them onto destroyed_models by hand leaves recoverable_wounds() at
    zero and the whole scene silently un-offerable."""
    dm = DecisionManager()
    state = GameState()
    ctrl = ResurrectionOrbController(decision_manager=dm, game_state=state,
                                     dice_manager=tk.RecordingDice(),
                                     auto_players=(AI,))
    squads = []
    for tag, dead in (("Alpha", 2), ("Beta", 5)):
        lord = tk.build(OVERLORD, owner, name=f"{owner[-1]} {tag} Overlord",
                        choices={"Overlord": {nec.OVERLORD_TO_VOIDSCYTHE: 1}},
                        gear={"Overlord": [nec.OVERLORD_RESURRECTION_ORB]})
        body = tk.build(NECRON_WARRIORS, owner, name=f"{owner[-1]} {tag} 1")
        led = attached_units.attach(lord, body, game_state=state)
        tk.line_up(led, x=10.0 + 20.0 * len(squads), y=20.0)
        state.tokens.extend(led.models)
        for m in led.models[:dead]:
            m.current_wounds = 0
        state.remove_dead_models()
        squads.append(led)
    return ctrl, dm, squads


ctrl, dm, squads = orb_scene(HUMAN)
usable = [s for s in squads if ctrl.can_use(s)]
c.true(f"the premise: more than one unit could use the orb ({len(usable)})", len(usable) > 1)
ctrl.offer_at_end_of_phase(squads, HUMAN)
orb_labels = [lbl for lbl in offered(dm) if lbl != "Decline"]
c.eq("a human is offered EVERY candidate, not just the first by name",
     len(orb_labels), len(usable))
c.true("...with the wound count in each label, which is what the choice turns on",
       bool(orb_labels) and all("wound(s) to recover" in lbl for lbl in orb_labels))
c.true("...and may decline", "Decline" in offered(dm))

ctrl2, dm2, squads2 = orb_scene(AI)
ctrl2.offer_at_end_of_phase(squads2, AI)
c.eq("the AI is not asked at all", dm2.is_pending, False)

# A DECLINE IS REMEMBERED. Its printed WHEN is "at the end of any phase", so
# main.py offers it at all five phase boundaries of every turn - and with no
# memory of a refusal that is a board-pick prompt taking over the whole left
# panel after very nearly every action. Reported: "ich werde nach jeder aktion
# wiederholt nach ressurrection orb gefragt".
ctrl3, dm3, squads3 = orb_scene(HUMAN)
_asks = 0
for _boundary in range(10):
    if ctrl3.offer_at_end_of_phase(squads3, HUMAN):
        _asks += 1
        if dm3.is_pending:
            dm3.choose(len(dm3.options) - 1)      # "Decline"
c.eq("ten phase boundaries on an unchanged board ask exactly once", _asks, 1)

# ...but the number the choice turns on going UP brings it back, because that
# is the only thing that can change the answer.
_hurt = squads3[0]
_before = reanimation_protocols.recoverable_wounds(_hurt)
for _m in [m for m in _hurt.models if not m.is_dead()][:1]:
    _m.current_wounds = 0
ctrl3.game_state.remove_dead_models()
c.true("the premise: there is more to recover than when it was declined",
       reanimation_protocols.recoverable_wounds(_hurt) > _before)
c.true("a further casualty re-opens the offer",
       ctrl3.offer_at_end_of_phase(squads3, HUMAN))
if dm3.is_pending:
    dm3.choose(len(dm3.options) - 1)
c.true("...and declining that quietens it again",
       not ctrl3.offer_at_end_of_phase(squads3, HUMAN))
c.true("a unit that was never declined is unaffected",
       not ctrl3.declined_unchanged(tk.build(NECRON_WARRIORS, HUMAN, name="fresh")))


# --------------------------------------------------------------------------
# 3. The pre-filters: the verdict is the AI's, not a gate on the prompt
# --------------------------------------------------------------------------
print("\n=== 3. no AI verdict gates a human's prompt ===")

import pathlib  # noqa: E402

from game.factions.death_guard import POXWALKERS as POXWALKERS_FOR_SICKENING  # noqa: E402

ROOT = pathlib.Path(r"c:\Users\Andre\Desktop\WH40")


def body_of(path, marker):
    """The source of one method, docstring included - but callers below cut it
    where it matters. Reading the FILE rather than importing, because what is
    being checked is the ORDER of two statements."""
    src = (ROOT / path).read_text(encoding="utf-8")
    return src.split(marker, 1)[1]


# 'Ard as Nails: is_worth_using() must come AFTER the auto_players branch
# opens, never before it.
ard = body_of("game/ard_as_nails.py", "    def maybe_offer(")
split_at = ard.find("if target.owner in self.auto_players:")
verdict_at = ard.find("if not is_worth_using(")
c.true("'Ard as Nails: the verdict is inside the AI branch",
       0 <= split_at < verdict_at)

# Sickening Impact: the second module that had it above the split.
sick = body_of("game/dlc_sickening_impact.py", "    def maybe_offer(")
sick_split = sick.find("if squad.owner in self.auto_players")
sick_verdict = sick.find("if not self.is_worth_using(")
c.true("Sickening Impact: likewise", 0 <= sick_split < sick_verdict)

# ...and the same thing as BEHAVIOUR, because the source check above only
# catches one spelling of the pre-filter: an A/B that moved the verdict onto
# the can_use() line instead of its own `if` sailed straight past it (36/36),
# which is a finding about this suite rather than about the code.
from game.dlc_sickening_impact import SickeningImpactController  # noqa: E402


def sickening_scene(owner, worth):
    dm = DecisionManager()
    ctrl = SickeningImpactController(None, decision_manager=dm, auto_players=(AI,))
    ctrl.can_use = lambda squad: True
    ctrl.is_worth_using = lambda squad: worth
    ctrl._tokens = lambda: []
    a = tk.build(POXWALKERS_FOR_SICKENING, owner, name=f"{owner[-1]} Impactor 1")
    b1 = tk.build(POXWALKERS_FOR_SICKENING, AI if owner == HUMAN else HUMAN, name="x 1")
    b2 = tk.build(POXWALKERS_FOR_SICKENING, AI if owner == HUMAN else HUMAN, name="x 2")
    ctrl_targets = [b1, b2]
    import game.dlc_sickening_impact as si
    real = si.engaged_targets
    si.engaged_targets = lambda squad, tokens: ctrl_targets
    try:
        ctrl.maybe_offer(a)
    finally:
        si.engaged_targets = real
    return dm


c.eq("a human is asked even when the verdict says it is not worth it",
     sickening_scene(HUMAN, worth=False).is_pending, True)
c.eq("...and the AI still declines on that same verdict",
     sickening_scene(AI, worth=False).is_pending, False)

# The two that always did it correctly, pinned so the pair cannot drift back.
for label, path, marker, gate in (
        ("Undying Spite", "game/dlc_undying_spite.py", "    def maybe_offer(",
         "if target_squad.owner in self.auto_players and not self.is_worth_using("),
        ("Undying Legions", "game/protocol_undying_legions.py", "    def maybe_offer(",
         "if target_squad.owner in self.auto_players:")):
    c.true(f"{label} keeps its verdict on the AI's side", gate in body_of(path, marker))


# --------------------------------------------------------------------------
# 4. Pestilent Fallout: a gate that was dead code, and had nothing to fall to
# --------------------------------------------------------------------------
print("\n=== 4. the dead gate with no channel ===")

from game.pestilent_fallout import PestilentFalloutController, PLAGUE_WIND_NAMES  # noqa: E402
from game.factions.death_guard import PLAGUE_MARINES, POXWALKERS                  # noqa: E402

caster = tk.build(PLAGUE_MARINES, HUMAN, name="1 Plague Marines 1")
for m in caster.models:
    m.profile = type(m.profile)()
    m.profile.pestilent_fallout = True
targets = [tk.build(POXWALKERS, AI, name=f"2 Poxwalkers {i}") for i in (1, 2)]

dm = DecisionManager()
fallout = PestilentFalloutController(
    decision_manager=dm, auto_players=(AI,),
    target_pick=lambda squad, cands: sorted(cands, key=lambda s: s.name)[-1])
weapon = sorted(PLAGUE_WIND_NAMES)[0]
fallout.on_squad_finished_shooting(caster, targets, [weapon])
c.eq("a human with two INFANTRY targets is asked which to enfeeble",
     dm.is_pending, True)
c.eq("...and offered both", len(offered(dm)), 2)
c.true("...with no Decline, because 'select' is not optional",
       "Decline" not in offered(dm))

# The AI keeps its own ranking, and pays nothing for it.
ai_caster = tk.build(PLAGUE_MARINES, AI, name="2 Plague Marines 1")
for m in ai_caster.models:
    m.profile = type(m.profile)()
    m.profile.pestilent_fallout = True
ai_targets = [tk.build(POXWALKERS, HUMAN, name=f"1 Poxwalkers {i}") for i in (1, 2)]
dm2 = DecisionManager()
fallout2 = PestilentFalloutController(
    decision_manager=dm2, auto_players=(AI,),
    target_pick=lambda squad, cands: sorted(cands, key=lambda s: s.name)[-1])
fallout2.on_squad_finished_shooting(ai_caster, ai_targets, [weapon])
c.eq("the AI is not asked", dm2.is_pending, False)
c.true("...and used its own ranking rather than name order",
       fallout2.is_enfeebled(ai_targets[-1]))

# One candidate is still nobody's decision.
dm3 = DecisionManager()
fallout3 = PestilentFalloutController(decision_manager=dm3, auto_players=(AI,))
fallout3.on_squad_finished_shooting(caster, targets[:1], [weapon])
c.eq("with a single candidate there is nothing to ask", dm3.is_pending, False)


# --------------------------------------------------------------------------
# 5. Word of the Phoenix: the gate its own docstring claimed
# --------------------------------------------------------------------------
print("\n=== 5. the dead gate that really fired ===")

wotp = (ROOT / "game" / "word_of_the_phoenix.py").read_text(encoding="utf-8")
c.true("it now reads auto_players", "squad.owner not in self.auto_players" in wotp)
c.true("...and has a prompt to fall through to", "self.decision_manager.request(" in wotp)
c.true("...with the roll behind its own entry point",
       "def _begin_roll(self, squad):" in wotp)

main_src = (ROOT / "main.py").read_text(encoding="utf-8")
c.true("main.py still drives it for whichever player's Command phase it is - "
       "which is exactly why the gate had to be real",
       "word_of_the_phoenix_controller.start(_sq)" in main_src)


# --------------------------------------------------------------------------
# 6. Bounty Hunters: the human names their own bounty
# --------------------------------------------------------------------------
print("\n=== 6. a mark chosen for the human ===")

from game.bounty_hunters import BountyHuntersController  # noqa: E402
from game.factions.tau_empire import KROOT_FARSTALKERS   # noqa: E402


def bounty_scene(owner):
    dm = DecisionManager()
    ctrl = BountyHuntersController(
        decision_manager=dm, auto_players=(AI,),
        target_pick=lambda h, enemies: sorted(enemies, key=lambda s: s.name)[-1])
    hunter = tk.build(KROOT_FARSTALKERS, owner, name=f"{owner[-1]} Kroot Farstalkers 1")
    foe = AI if owner == HUMAN else HUMAN
    enemies = [tk.build(POXWALKERS, foe, name=f"{foe[-1]} Poxwalkers {i}") for i in (1, 2)]
    return ctrl, dm, [hunter] + enemies, hunter, enemies


ctrl, dm, squads, hunter, enemies = bounty_scene(HUMAN)
picked = ctrl.select_at_start_of_battle(squads)
c.eq("a human is asked which unit to hunt", dm.is_pending, True)
c.eq("...and offered every enemy unit", len(offered(dm)), len(enemies))
c.eq("...with nothing decided yet", ctrl.bounty_for(hunter), None)
if dm.is_pending:          # guarded, so a probe that removes the prompt makes
    dm.choose(0)           # the line above go red instead of raising here
c.true("...until they answer", ctrl.bounty_for(hunter) is not None)

ctrl2, dm2, squads2, hunter2, enemies2 = bounty_scene(AI)
ctrl2.select_at_start_of_battle(squads2)
c.eq("the AI is not asked", dm2.is_pending, False)
c.true("...and keeps its own ranking",
       ctrl2.bounty_for(hunter2) is sorted(enemies2, key=lambda s: s.name)[-1])

c.finish()
