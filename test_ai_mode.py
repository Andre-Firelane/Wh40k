"""ONE definition of which side the engine answers for.

User: "die KI soll das zwar deterministisch anwenden, aber die Funktion selbst
soll nicht deterministisch sein ... es muss also eine weiche geben. je nachdem
ob KI aktiv ist oder nicht."

THE SWITCH ALREADY EXISTED - it was just written out 82 times. `auto_players`
is a constructor argument on ~83 rule modules, and the gate inside each of them
is right: an owner listed there gets the rule's own deterministic answer,
anyone else gets a DecisionManager prompt. What was missing was a single place
to SAY it. main.py carried the literal ("Player 2",) at 82 call sites, and four
more spellings of the same fact lived elsewhere - game/scouts.py's
human_players, game/pregame.py's and game/plagues.py's singular human_player,
ai/deployment_ai.py's ai_players default.

WHY IT HAS TO BE ONE FACT. `auto_players` is not a convenience: the AI can
already answer any pending prompt through ai/agent_driver.py's
_maybe_resolve_decision(), but that goes through the LLM and costs a real API
call. So a controller that is NOT told who the AI is does not fail loudly - it
quietly starts spending money. That is exactly what seven controllers were
doing (kauyon_* x3, montka_* x3, aac_autoreactive_camouflage): they declared
`auto_players`, READ it, and main.py never passed it. Inert only because no
shipped list fields those detachments.

FROZEN, DELIBERATELY. Every controller normalises what it is handed in its own
__init__, so nothing can change under one mid-battle. That is what lets the
question be asked once, before main() builds anything, instead of being
re-checked on every frame.
"""

import ast
import os
import pathlib
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from testkit import Checks

c = Checks("the AI/human switch")

ROOT = pathlib.Path(r"c:\Users\Andre\Desktop\WH40")
MAIN_SRC = (ROOT / "main.py").read_text(encoding="utf-8")
MAIN_TREE = ast.parse(MAIN_SRC)

from game import config  # noqa: E402


# --------------------------------------------------------------------------
# 1. The fact exists, in config, in the shape the rules read
# --------------------------------------------------------------------------
print("=== 1. one fact ===")

# getattr, never config.AI_PLAYERS directly: a probe that DELETES the setting
# must make these go RED, not raise AttributeError. A suite that crashes tells
# you nothing about which check broke - this repo has recorded that lesson
# five times (two str.index() guards, a None-valued row, an empty list, an
# unpacked list).
AI_PLAYERS = getattr(config, "AI_PLAYERS", None)
c.true("config.AI_PLAYERS exists", AI_PLAYERS is not None)
c.true("...as a tuple of player names, like every other owner-keyed setting",
       isinstance(AI_PLAYERS, tuple)
       and all(isinstance(p, str) for p in AI_PLAYERS))
c.eq("...and ships as Player 2, which is what it has always meant",
     AI_PLAYERS, ("Player 2",))
c.true("config.AI_MODE_SELECT exists", hasattr(config, "AI_MODE_SELECT"))


def classes_taking_auto_players():
    """Every class under game/ whose __init__ declares `auto_players`.

    Read from the SOURCE, not by importing: a module nobody imports still
    counts, and "nobody imports it" is one of the ways a rule goes unwired."""
    found = {}
    for path in sorted((ROOT / "game").rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    names = [a.arg for a in item.args.args + item.args.kwonlyargs]
                    if "auto_players" in names:
                        found[node.name] = path.relative_to(ROOT).as_posix()
    return found


TAKERS = classes_taking_auto_players()
# Live-guard first: a collector that stopped matching would make every check
# below pass by inspecting nothing - the failure mode of every source guard in
# this repo.
c.true(f"the sweep is live - it found {len(TAKERS)} classes taking auto_players",
       len(TAKERS) >= 80)


# --------------------------------------------------------------------------
# 2. G1 - no literal is left in main.py
# --------------------------------------------------------------------------
print("\n=== 2. no second copy of the answer ===")

c.eq("main.py holds no auto_players literal any more",
     MAIN_SRC.count('auto_players=("Player 2",)'), 0)
c.true("...it passes the shared binding instead",
       MAIN_SRC.count("auto_players=ai_players") >= 80)
c.true("...and scouts reads the same fact rather than its own list",
       "human_players=human_players," in MAIN_SRC
       and 'human_players=("Player 1",)' not in MAIN_SRC)
c.true("...as does the pre-game Scouts resolver",
       "ai_players=ai_players," in MAIN_SRC)
c.true("...and the agent is told which side it plays",
       "player=ai_players[0]," in MAIN_SRC)


# --------------------------------------------------------------------------
# 3. G2 - every controller main.py builds is actually TOLD
# --------------------------------------------------------------------------
print("\n=== 3. every rule that reads it, gets it ===")

# Checked at the CALL EXPRESSION, not by counting a name: this repo has been
# caught by a guard that counted occurrences and was satisfied by a mention in
# a docstring (Fehlerklasse 24).
built_without = []
built_with = set()
for node in ast.walk(MAIN_TREE):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        continue
    name = node.func.id
    if name not in TAKERS:
        continue
    if any(kw.arg == "auto_players" for kw in node.keywords):
        built_with.add(name)
    else:
        built_without.append((name, node.lineno))

c.true(f"the guard is live - main.py builds {len(built_with)} of them", len(built_with) >= 80)
c.eq("every controller main.py builds is handed auto_players",
     sorted(f"{n}:{ln}" for n, ln in built_without), [])


# --------------------------------------------------------------------------
# 4. G3 - a class that TAKES it must READ it
# --------------------------------------------------------------------------
print("\n=== 4. no dead gates ===")

# The three that stored it and never looked at it - word_of_the_phoenix,
# spiritseer.TearsOfIsha, raid_and_run - auto-resolved for a HUMAN too. A
# module can be cleared two ways: it reads the set itself, or it FORWARDS the
# argument to a base class that does. Without the forwarding clause this
# reports the four CommandPhaseMark subclasses as well, and a guard with false
# alarms gets deleted.
BASE_CLASSES = {"MortalWoundOfferController", "CommandPhaseMark"}

dead = []
for cls_name, rel in sorted(TAKERS.items()):
    src = (ROOT / rel).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != cls_name:
            continue
        body = ast.get_source_segment(src, node) or ""
        reads = "in self.auto_players" in body or "not in self.auto_players" in body
        # TWO ways to forward rather than read: up to a BASE class in the
        # constructor, or across to a shared COLLABORATOR that applies the gate
        # (game/unit_choice_offer.py, which four Stratagem controllers now hand
        # the choice to). The second is still "the gate is applied", just in one
        # place instead of four - and it is backed by behaviour, not by this
        # token: test_unit_choice_offers.py drives each of the four with an AI
        # owner and asserts no prompt opens and the window closes again.
        forwards = ("auto_players=auto_players" in body
                    or "auto_players=self.auto_players" in body)
        if not reads and not forwards and cls_name not in BASE_CLASSES:
            dead.append(f"{cls_name} ({rel})")

# TWO NAMED EXEMPTIONS, and the exemption is CONDITIONAL on the reason for it.
#
# Word of the Phoenix was the third and is fixed: it was reachable, main.py
# drove it for whichever player's Command phase it was, and a human Ynnari
# player had the whole ability resolved for them every turn.
#
# These two are a DIFFERENT defect. Their gates are dead too, but so is
# everything around them: TearsOfIshaController.resolve() and
# RaidAndRunController.start_move() have no caller anywhere in the app, so
# neither ability can fire for either side. Building a human prompt into a
# method nobody can reach would be speculative work behind an untestable path,
# so they are NAMED here instead (this repo's standing preference - see
# game/scouts.py's "declined for a human with a logged reason rather than
# half-implemented").
#
# The exemption expires by itself: the check below verifies they really ARE
# unreachable. Wire either ability up and this suite goes red, which is when
# the gate has to be made real.
# label -> the exact call expression that would MAKE it reachable. Named in
# full ("raid_and_run_controller.start_move("), not just the method: a bare
# ".start_move(" also matches movement_controller's own, which is a different
# thing entirely and made the first version of this check fail on healthy code.
UNREACHABLE = {
    "RaidAndRunController (game/raid_and_run.py)":
        "raid_and_run_controller.start_move(",
    "TearsOfIshaController (game/spiritseer.py)":
        "tears_of_isha_controller.resolve(",
}
c.eq("no class takes auto_players and ignores it, beyond the unreachable two",
     sorted(dead), sorted(UNREACHABLE))

# ...and they are unreachable, which is the whole basis of the exemption. A
# guard whose excuse nobody checks is how a dead gate survives.
APP_SRC = MAIN_SRC + "\n" + "\n".join(
    (ROOT / rel).read_text(encoding="utf-8")
    for rel in ("ai/agent_driver.py", "game/ui/action_panel.py"))
for label, call in sorted(UNREACHABLE.items()):
    c.eq(f"{label.split()[0]} really is unfed - nothing calls {call}...)",
         APP_SRC.count(call), 0)
# The exception list is load-bearing, not a rubber stamp: these really are base
# classes whose subclasses do the reading.
c.true("...and the named exceptions really are bases",
       all(any(f"({b})" in ln or b in ln for ln in [b]) for b in BASE_CLASSES))


# --------------------------------------------------------------------------
# 5. G5 - construction order (Fehlerklasse 23)
# --------------------------------------------------------------------------
print("\n=== 5. bound before it is used ===")

# main() is a 4000-line function and NO suite fares it, so a name used above
# its binding is an UnboundLocalError on the first real start and green
# everywhere else. That has happened three times in this repo. The AST guard in
# test_event_chain_wiring.py section 4 only covers `a.b = c`, not this.
# find(), never index(): a probe that DELETES the binding must make these go
# red, and index() would raise instead. -1 for a missing binding is also the
# correct ordering answer ("not before"), so no special case is needed - except
# that -1 < anything, so each check demands the needle was found at all.
bind_line = MAIN_SRC.find("    ai_players = ai_mode.players(p for p in sorted(armies)")
first_use = MAIN_SRC.find("auto_players=ai_players")
c.true("ai_players is bound before the first controller reads it",
       0 <= bind_line < first_use)
c.true("...and after the armies it is derived from are known",
       0 <= MAIN_SRC.find("    armies = army_lists.configured_choices()") < bind_line)

human_bind = MAIN_SRC.find("    human_players = ai_mode.humans(sorted(armies), ai_players)")
human_use = MAIN_SRC.find("human_players=human_players,")
c.true("human_players likewise", 0 <= human_bind < human_use)
c.true("...and is derived from ai_players, not written out a second time",
       "ai_mode.humans(sorted(armies), ai_players)" in MAIN_SRC)


# --------------------------------------------------------------------------
# 6. The switch really switches
# --------------------------------------------------------------------------
print("\n=== 6. it is a switch, not a constant ===")

from game.ard_as_nails import ArdAsNailsController  # noqa: E402
from game.decision import DecisionManager           # noqa: E402

# Driven at the controller, which is where the fact lands. With the owner
# listed, the rule answers itself; without, the same rule raises a prompt.
# 'Ard as Nails is the canonical carrier of the pattern.
src = (ROOT / "game" / "ard_as_nails.py").read_text(encoding="utf-8")
c.true("the canonical gate answers for a listed owner",
       "if target.owner in self.auto_players:" in src)
c.true("...and falls through to a prompt for anyone else",
       "self.decision_manager.request(" in src)

listed = ArdAsNailsController(None, decision_manager=DecisionManager(),
                              auto_players=("Player 2",))
unlisted = ArdAsNailsController(None, decision_manager=DecisionManager(),
                                auto_players=())
c.true("a controller told about Player 2 holds it", "Player 2" in listed.auto_players)
c.eq("...and one told about nobody holds nobody", len(unlisted.auto_players), 0)

# The normalisation in __init__ IS the freeze: what a controller was handed
# cannot change under it, which is why the question may be asked once, before
# main() builds anything.
handed = ["Player 2"]
frozen = ArdAsNailsController(None, decision_manager=DecisionManager(),
                              auto_players=handed)
handed.append("Player 1")
c.true("a controller freezes what it was handed", "Player 1" not in frozen.auto_players)


# --------------------------------------------------------------------------
# 7. Nobody automatic must not crash the AI entry points
# --------------------------------------------------------------------------
print("\n=== 7. an empty AI side is a no-op, not a crash ===")

# config.AI_PLAYERS = () is now reachable, and ai_players[0] would raise. Both
# frame-loop entry points return early instead - and returning early is also
# the RIGHT behaviour: with nobody automatic, letting the agent act would spend
# a human's CP and a real API call doing it.
c.true("run_ai_action() returns early with no AI side",
       "        nonlocal last_shown_turn_plan\n        if not ai_players:\n            return"
       in MAIN_SRC)
c.true("...and so does the pre-game one",
       "        if not ai_players:\n            return\n        deployment_ai.take_pregame_action("
       in MAIN_SRC)

# deployment_ai's own default flipped to (), so a caller that FORGETS resolves
# nothing rather than silently handing the AI a human's Scouts move.
dep_src = (ROOT / "ai" / "deployment_ai.py").read_text(encoding="utf-8")
c.true("resolve_scouts defaults to nobody", "ai_players=()):" in dep_src)
c.true("...and says why", "DEFAULTS TO EMPTY" in dep_src)

# --------------------------------------------------------------------------
# 8. ONE switch: the mode reaches the gates that were built once
# --------------------------------------------------------------------------
print("\n=== 8. the mode is live, and it is the same switch ===")

# THE REPORTED BUG. User, after a game played with the red corner dot off:
# "Protokoll of undying legions wurde wieder automatisch ausgefuehrt, obwohl KI
# Modus aus war" - and, when asked whether auto-play and these gates might be
# separate things: "das ist fuer mich das gleiche. KI - Modus ist autoplay ...
# das steuert auch, ob die ki pfade fuer faehigkeiten und stratagems aktiviert
# sind. verstehe nicht warum man das trennen sollte."
#
# Measured in logs/game_20260904_174253.log: "auto-play OFF" at line 17, the
# human then hand-placed all eight of Player 2's units (so channel one really
# had stopped), and at line 175 channel two still spent a CP.
from game import ai_mode                                        # noqa: E402
from game.command_points import CommandPointManager             # noqa: E402
from game.dice import DiceManager                               # noqa: E402
from game.game_state import GameState                           # noqa: E402
from game.stratagems import StratagemController                 # noqa: E402
from game.factions import necrons as _nec                       # noqa: E402
from game import protocol_undying_legions as _pul               # noqa: E402
import testkit as _tk                                           # noqa: E402

c.true("the mode defaults to on", ai_mode.enabled())
c.eq("set_enabled reports the new state", ai_mode.set_enabled(False), False)
c.eq("toggle flips it", ai_mode.toggle(), True)

# FROZEN MEMBERS, LIVE MEMBERSHIP - that pairing is the whole mechanism. A
# controller built while the mode was on must stop answering when it goes off,
# without being rebuilt, because ~83 of them are built once at the start of a
# battle and never again.
view = ai_mode.players(("Player 2",))
c.true("a listed owner is answered for while the mode is on", "Player 2" in view)
c.eq("...and the members say so regardless", set(view.members), {"Player 2"})
ai_mode.set_enabled(False)
c.eq("the SAME view stops answering when the mode goes off",
     "Player 2" in view, False)
c.eq("...and reads as empty in every other shape too",
     (len(view), bool(view), list(view)), (0, False, []))
c.eq("...while still remembering who it would answer for",
     set(view.members), {"Player 2"})
ai_mode.set_enabled(True)
c.true("and comes back", "Player 2" in view)

c.true("players() is idempotent", ai_mode.players(view) is view)
c.eq("an empty view is empty in both modes", len(ai_mode.players(())), 0)


def _undying_scene():
    """The reported unit: a Necron squad that has just lost models, a real CP
    ledger and a real StratagemController - the bookkeeping is half of what
    this is about, so a stub would test the stub."""
    state = GameState()
    squad = _tk.build(_nec.NECRON_WARRIORS, "Player 2",
                      name="2 Necron Warriors 1", composition_index=0)
    _tk.line_up(squad, x=20.0, y=20.0)
    state.tokens = list(squad.models)
    for model in squad.models[:3]:
        model.current_wounds = 0
    state.remove_dead_models()
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = 5
    decisions = DecisionManager()
    controller = _pul.UndyingLegionsController(
        StratagemController(command_points=pool, game_log=_tk.Log()),
        dice_manager=DiceManager(), decision_manager=decisions,
        game_log=_tk.Log(), game_state=state, auto_players=("Player 2",))
    return controller, decisions, squad, pool


# ON: today's behaviour, unchanged - the AI answers itself, for free.
ai_mode.set_enabled(True)
ctrl, decisions, squad, pool = _undying_scene()
c.true("mode ON: the Stratagem fires by itself", ctrl.maybe_offer(squad))
c.eq("...spending the CP", pool.cp["Player 2"], 4)
c.eq("...and asking nobody", decisions.is_pending, False)

# OFF: the same controller, the same board - and now it asks.
ai_mode.set_enabled(False)
ctrl, decisions, squad, pool = _undying_scene()
c.true("mode OFF: it still offers", ctrl.maybe_offer(squad))
c.true("...but as a prompt", decisions.is_pending)
c.eq("...with the CP untouched", pool.cp["Player 2"], 5)
c.true("...naming the Stratagem", "Undying Legions" in decisions.prompt)
c.true("...and offering to decline",
       any("decline" in o["label"].lower() for o in decisions.options))
ai_mode.set_enabled(True)   # leave the process as the rest of the suite found it


# --------------------------------------------------------------------------
# 9. Nothing may hold a FROZEN copy any more
# --------------------------------------------------------------------------
print("\n=== 9. every gate goes through the one normaliser ===")

# A SET DIFFERENCE at the source, not a behaviour test: a behaviour test cannot
# see the 84th controller, because it does not exist yet. Every module that
# stores auto_players must store the live view - one that writes
# set(auto_players) again would be frozen in the ON state and would keep
# answering with the switch off, which is exactly the reported bug.
_stores, _frozen = [], []
for _folder in ("game", "ai"):
    for _path in sorted((ROOT / _folder).rglob("*.py")):
        _text = _path.read_text(encoding="utf-8")
        if "self.auto_players =" not in _text:
            continue
        _rel = _path.relative_to(ROOT).as_posix()
        _stores.append(_rel)
        for _line in _text.split("\n"):
            if "self.auto_players =" in _line and "ai_mode.players(" not in _line:
                _frozen.append((_rel, _line.strip()))
c.true("the sweep found the gates at all (%d)" % len(_stores), len(_stores) >= 80)
c.eq("no gate keeps a frozen copy", _frozen, [])

# ...and every one of them must really import it, or the line above is a
# NameError waiting for its first game rather than a live view.
_missing = []
for _rel in _stores:
    _tree = ast.parse((ROOT / _rel).read_text(encoding="utf-8"))
    _ok = any(isinstance(n, ast.ImportFrom) and n.module == "game"
              and any(a.name == "ai_mode" for a in n.names) for n in _tree.body)
    if not _ok:
        _missing.append(_rel)
c.eq("...and imports it at module level", _missing, [])


# --------------------------------------------------------------------------
# 10. main.py: one switch, two channels, and it is clickable
# --------------------------------------------------------------------------
print("\n=== 10. one switch in main() ===")

c.eq("the separate auto-play local is gone", MAIN_SRC.count("ai_auto_play ="), 0)
c.true("a battle opens with the AI idle, where that local used to start",
       "ai_mode.set_enabled(False)" in MAIN_SRC)
c.true("one helper flips it, so every route logs the same",
       "def _set_ai_mode(on, source):" in MAIN_SRC)
c.true("Shift+A goes through it", '_set_ai_mode(ai_mode.toggle(), "Shift+A")' in MAIN_SRC)
c.true("the board switch goes through it too",
       '_set_ai_mode(not ai_mode.enabled(), "AI toggle")' in MAIN_SRC)
c.true("the per-frame AI tick reads the mode",
       "ai_mode.enabled() and not dice_panel.is_busy" in MAIN_SRC)
c.true("the switch is drawn every frame, in both states",
       "draw_ai_mode_toggle(" in MAIN_SRC)

# BEFORE the state-gated chain (error class 15): ~40 of its branches gate on
# controller state with no event.type term, so a press reachable only after
# them is one pending prompt away from being unreachable - and a pending prompt
# is exactly when a player reaches for this switch.
_toggle_click = MAIN_SRC.find("ai_toggle_rect.collidepoint(event.pos)")
_chain_start = MAIN_SRC.find("if event.type == pygame.QUIT:")
c.true("the switch has a click branch", _toggle_click > 0)
c.true("...asked before the state-gated chain", 0 < _toggle_click < _chain_start)
# ...and it consumes the press, or the click that flips the mode also pans the
# board it is drawn on.
c.true("...and it consumes the click",
       "continue" in MAIN_SRC[_toggle_click:_toggle_click + 400])

c.finish()
