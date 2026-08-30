"""Ending the turn while rule 12.04 still owes you melee attacks used to
happen silently.

User: "gib mal bitte ine warnung aus, die ich wegklicken muss, wenn ich auf
end turn klicke, obwohl ich noch mit einheiten im nahkampf kaempfen koennte."

Reproduced before anything was changed: a human unit eligible under 12.04
with an engaged enemy in front of it, and NOTHING in main.py's "End Turn"
gate stopped the click. _has_unresolved_declaration() covers
fight_controller's CHOOSING_TARGET/CHOOSING_WEAPON/ASSIGNING sub-states - a
half-finished activation - but deliberately not SELECTING, which is the
ordinary "it is your turn to fight, pick a unit" state. So the turn ended,
the attacks were gone, and a game_log line was the only trace.

Three parts, because the bug had three separable halves:

  1. the QUESTION (game/fight.py's squads_that_could_still_fight) - who
     actually still has attacks coming, which is stricter than bare 12.04
     eligibility;
  2. the WARNING (game/ui/fight_warning_overlay.py) - once per phase, spent
     by the click that raised it, and re-armed at the next phase;
  3. the WIRING (main.py) - the half no behaviour test can see. This repo
     has hit "a controller that is built but never fed" three times
     (VengefulStarsController, the mark wiring, Path of the Outcast), and
     main.py's event chain has swallowed an input five times (error class
     15), so section 3 reads main.py itself.
"""
import io
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from game import fight
from game.factions.aeldari import STORM_GUARDIANS, HOWLING_BANSHEES
from game.factions.orks import BOYZ
from game.ui.fight_warning_overlay import FightWarningOverlay

c = tk.Checks("End Turn warning - units that could still fight")

HUMAN = "Player 1"


def section(title):
    print(f"\n--- {title} ---")


pygame.init()
pygame.display.set_mode((1200, 800))


# ------------------------------------------- 1. who still has attacks coming

section("1. FightController.squads_that_could_still_fight()")

sc = tk.fight_scene(BOYZ, STORM_GUARDIANS, attacker_owner="Player 2")
fc, human_squad, ai_squad = sc["fight"], sc["target"], sc["attacker"]

# The reported case, exactly: the human's engaged unit has not fought yet.
c.eq("the engaged human unit is named", [s.name for s in fc.squads_that_could_still_fight(HUMAN)],
     [human_squad.name])
c.true("...and it really is rule 12.04 eligible", fc.is_eligible_to_fight(human_squad))
c.true("...with an engaged enemy to swing at", bool(fc.engaged_enemy_squads(human_squad)))

# Asked per player: the AI's own engaged unit is not the human's problem.
c.eq("the AI's unit is not reported for the human", ai_squad.name in
     [s.name for s in fc.squads_that_could_still_fight(HUMAN)], False)
c.eq("...but is reported for the AI", [s.name for s in fc.squads_that_could_still_fight("Player 2")],
     [ai_squad.name])

# Once it has fought it owes nothing - _is_eligible_to_fight()'s own first test.
fc.fought_squad_ids.add(human_squad)
c.eq("a unit that already fought is not reported",
     [s.name for s in fc.squads_that_could_still_fight(HUMAN)], [])
fc.fought_squad_ids.discard(human_squad)
c.eq("...and comes back once that is undone",
     [s.name for s in fc.squads_that_could_still_fight(HUMAN)], [human_squad.name])

# DONE means the Fight step is over for everyone, whatever the sticky
# engaged_at_start flags still say (both players passed, say).
state_before = fc.state
fc.state = fight.DONE
c.eq("DONE reports nothing at all",
     [s.name for s in fc.squads_that_could_still_fight(HUMAN)], [])
fc.state = state_before

# The STRICTER half, and the reason this is not just is_eligible_to_fight():
# 12.04's second condition keeps a unit eligible when its only nearby enemy
# has since died. It is still eligible - and it has nothing to attack, so
# naming it in a warning would be noise.
for model in ai_squad.models:
    model.current_wounds = 0
c.true("a unit whose only enemy died is still 12.04 eligible", fc.is_eligible_to_fight(human_squad))
c.eq("...but is NOT reported as still having attacks",
     [s.name for s in fc.squads_that_could_still_fight(HUMAN)], [])
for model in ai_squad.models:
    model.current_wounds = model.profile.wounds

# ...and that living-model filter matters within the frame a unit dies:
# main.py's remove_dead_models() runs once per frame, so the corpses are
# still on the board and still inside engagement range right now.
c.true("the dead enemy's models are still on the board",
       all(m in fc.all_tokens for m in ai_squad.models))

# A unit out of engagement range and never engaged owes nothing.
far = tk.build(HOWLING_BANSHEES, HUMAN, name="1 Howling Banshees far")
tk.line_up(far, y=40.0)
for model in far.models:
    fc.all_tokens.append(model)
c.eq("a unit nowhere near an enemy is not reported",
     [s.name for s in fc.squads_that_could_still_fight(HUMAN)], [human_squad.name])

# Several units at once, and in a stable order: _all_squads() is a SET, so
# without the sort the warning would list them differently frame to frame.
extra = []
for label in ("Aaa", "Mmm", "Zzz"):
    unit = tk.build(HOWLING_BANSHEES, HUMAN, name=f"1 {label} Banshees near")
    tk.line_up(unit, y=21.2)
    for model in unit.models:
        fc.all_tokens.append(model)
    extra.append(unit)
names = [s.name for s in fc.squads_that_could_still_fight(HUMAN)]
c.eq("every engaged human unit is reported", sorted(names),
     sorted([human_squad.name] + [u.name for u in extra]))
c.eq("...sorted by name, not by set iteration order", names, sorted(names))
# The behaviour check above is honest but cannot FAIL reliably: a set's
# iteration order sometimes comes out sorted by luck, and the A/B probe for
# this one duly passed on one run. The source is the deterministic half.
fight_src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "game", "fight.py"),
                    encoding="utf-8").read()
method = fight_src[fight_src.index("def squads_that_could_still_fight"):]
method = method[:method.index("\n    def ", 1)]
c.true("...and the sort is in the source, not left to the set", "key=lambda s: s.name" in method)


# --------------------------------------------------- 2. the warning itself

section("2. FightWarningOverlay - once per phase, spent by its own click")

ov = FightWarningOverlay()
c.eq("nothing pending to begin with", ov.is_pending, False)

c.true("the first End Turn click raises it", ov.warn_once(["1 Storm Guardians 1"]))
c.true("...and it is now pending", ov.is_pending)

# The whole point of "a warning, not a lock": clicking End Turn again means
# it, so the second call must NOT intercept.
c.eq("a second click is not intercepted", ov.warn_once(["1 Storm Guardians 1"]), False)

ov.dismiss()
c.eq("dismiss clears the overlay", ov.is_pending, False)
c.eq("...but does not re-arm it", ov.warn_once(["1 Storm Guardians 1"]), False)

ov.reset()
c.true("reset re-arms it for the next phase", ov.warn_once(["1 Storm Guardians 1"]))
ov.reset()

# Nothing to warn about is not a warning.
c.eq("an empty unit list never intercepts", ov.warn_once([]), False)
c.eq("...and leaves it un-armed for a real one later", ov.is_pending, False)
c.true("a real list still works afterwards", ov.warn_once(["1 Storm Guardians 1"]))

# It draws, on a real surface, and says which units it means - a warning
# that only says "you have units" sends you hunting the board for them.
ov.reset()
ov.warn_once(["1 Storm Guardians 1", "1 Howling Banshees 1"])
screen = pygame.display.get_surface()
screen.fill((0, 0, 0))
before = pygame.image.tobytes(screen, "RGB")
ov.draw(screen)
c.true("draw() actually puts something on screen", pygame.image.tobytes(screen, "RGB") != before)

# Measured, not assumed: the box is tall enough to hold a line per unit.
one, two = FightWarningOverlay(), FightWarningOverlay()
one.warn_once(["A"])
two.warn_once(["A", "B", "C"])


def drawn_height(overlay):
    surf = pygame.Surface((1200, 800), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 255))
    overlay.draw(surf)
    rows = [y for y in range(800)
            if any(surf.get_at((x, y))[:3] != (0, 0, 0) for x in range(0, 1200, 4))]
    return (max(rows) - min(rows)) if rows else 0


h1, h3 = drawn_height(one), drawn_height(two)
c.true(f"three units draw a taller box than one ({h1} -> {h3})", h3 > h1)

# A dismissed overlay draws nothing at all - otherwise it would linger over
# the board after the click that closed it.
one.dismiss()
c.eq("a dismissed overlay draws nothing", drawn_height(one), 0)


# --------------------------------------------------------- 3. the wiring

section("3. main.py wiring (the half no behaviour test can see)")

src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py"),
              encoding="utf-8").read()
lines = src.split("\n")


def line_of(needle, start=0):
    return next((i for i in range(start, len(lines)) if needle in lines[i]), None)


def block_of(def_line):
    """Source of one nested def, from its `def` line to the first non-blank
    line back at (or above) its own indent, plus that end index.

    Written this way rather than "up to the next line starting with def"
    because ai_advance_phase() is the LAST nested def inside main() - the
    naive version ran on to the module-level helpers far below and read the
    entire event chain as part of it, which is exactly how the check below
    first failed for the wrong reason."""
    indent = len(lines[def_line]) - len(lines[def_line].lstrip())
    end = next((i for i in range(def_line + 1, len(lines))
                if lines[i].strip() and (len(lines[i]) - len(lines[i].lstrip())) <= indent),
               len(lines))
    return "\n".join(lines[def_line:end]), end


c.eq("FightWarningOverlay is imported", src.count("from game.ui.fight_warning_overlay import"), 1)
c.eq("...and instantiated exactly once", src.count("FightWarningOverlay()"), 1)

# It has to be in _front_notice(), or it is never DRAWN: main.py draws only
# the front-most notice ("one modal at a time"), so an overlay missing from
# that tuple is pending, swallows clicks, and shows nothing.
#
# Read out of the whole function rather than off one line: that tuple grows
# (a parallel session added battle_end_overlay to it mid-run and re-wrapped
# the line), and a guard that only recognises one formatting of it reports a
# missing overlay every time somebody else adds theirs.
# Comments stripped first: _front_notice() carries a comment explaining why
# the warning is ordered where it is, and without this the guard would find
# the name THERE and pass with the overlay itself removed from the tuple -
# caught by the A/B probe, which is what those probes are for.
front_src, _ = block_of(line_of("    def _front_notice():"))
front_code = "\n".join(ln for ln in front_src.split("\n") if not ln.strip().startswith("#"))
c.true("the warning is in _front_notice()'s tuple", "fight_warning_overlay" in front_code)

# The click that dismisses it must be caught ABOVE the button that raised it -
# error class 15, five times over in this file. One click may not both
# dismiss the warning and end the turn it warned about.
dismiss_i = line_of("elif fight_warning_overlay.is_pending:")
button_i = line_of("and game_status_panel.handle_click(event.pos)")
c.true("there is a dismiss branch", dismiss_i is not None)
c.true("...and it sits ABOVE the End Turn button's branch",
       dismiss_i is not None and button_i is not None and dismiss_i < button_i)
c.eq("...and it dismisses exactly once", src.count("fight_warning_overlay.dismiss()"), 1)

# BOTH human routes into advance_turn_phase() are guarded. The coherency
# route is the same End Turn click resumed after 09.02's model removal - a
# warning one of the two routes walks past is not a warning.
guards = [i for i, ln in enumerate(lines) if "_fight_warning_intercepts_end_turn()" in ln
          and not ln.strip().startswith(("#", "def "))]
c.eq("both human End-Turn routes call the shared guard", len(guards), 2)
for i in guards:
    c.true(f"...guard at line {i + 1} gates an advance_turn_phase() call",
           any("advance_turn_phase()" in lines[j] for j in range(i, min(i + 6, len(lines)))))

# The AI must not keep playing behind an unread warning - same gate every
# other notice already has, in all three places.
c.eq("the AI/datacard gates all know about it",
     src.count("and not fight_warning_overlay.is_pending"), 3)

# Once per PHASE needs a point of re-offer at the phase change (this repo's
# own rule 14: a "deferred until X" note needs a point at X).
reset_i = line_of("fight_warning_overlay.reset()")
adv_i = line_of("    def advance_turn_phase():")
_, after_adv = block_of(adv_i)
c.true("reset() lives inside advance_turn_phase()",
       reset_i is not None and adv_i < reset_i < after_adv)
c.eq("...exactly once", src.count("fight_warning_overlay.reset()"), 1)

# The warning is asked only when this click would END THE TURN (07.02) - an
# intermediate phase change owes nobody a fight.
helper_i = line_of("    def _fight_warning_intercepts_end_turn():")
helper_src, _ = block_of(helper_i)
c.true("the guard checks is_last_phase", "turn_tracker.is_last_phase" in helper_src)
c.true("...and asks for the human's units",
       bool(re.search(r'squads_that_could_still_fight\(\s*"Player 1"\s*\)', helper_src)))

# The AI's own end-of-turn path is deliberately NOT guarded: an overlay there
# would stall the AI on a warning nobody is going to click away.
ai_adv_src, _ = block_of(line_of("    def ai_advance_phase():"))
c.eq("ai_advance_phase() is left alone",
     ai_adv_src.count("_fight_warning_intercepts_end_turn"), 0)
c.true("...and that block really is just that function (sanity, given it is "
       "the last nested def in main())",
       "advance_turn_phase()" in ai_adv_src and "elif fight_warning_overlay" not in ai_adv_src)


c.finish()
