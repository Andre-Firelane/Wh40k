"""Runtime proof through the REAL main() loop that resting on a Stratagem
button shows that Stratagem's printed rules.

A source guard shows the poll is written down; it does not show that a real
Stratagem button gets drawn, that its label resolves to a corpus entry, or that
main() hands the right army's detachments to the lookup. "Built but never FED"
has shipped in this repo six times.

So this drives selfplay.py's real main() loop, waits until the panel has
actually drawn a Stratagem button, parks the cursor on it, holds it there past
the dwell, and reports what the tooltip resolved.

Harness traps this walks into deliberately, all three already paid for once:
  * importing selfplay runs nothing (its __main__ guard), so it goes via runpy;
  * selfplay REPLACES pygame.mouse.get_pos at import if it wants to - so the
    cursor is parked by patching that function rather than by posting motion;
  * a fixed frame number fires before the panel exists, so everything here is
    scheduled RELATIVE to the frame a button first appears.

Usage:  python verify_stratagem_tooltip.py [map2]
        python verify_stratagem_tooltip.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game import proactive_stratagems
from game.renderer import Renderer
from game.ui import action_panel, stratagem_tooltip

# A MockAgent run never gets a Stratagem button on screen: the panel only draws
# them for a SELECTED unit whose Stratagems are usable this phase, and the
# harness rarely selects a human unit at all. So the two facts the harness
# cannot produce are supplied - a selected unit, and one usable Stratagem - and
# everything after them is the real thing: the real _draw_button records it,
# the real main() polls, the real lookup reads the real corpus.
#: The injected button carries a Stratagem THAT SQUAD'S OWN army really has.
#: The first attempt hardcoded an Aeldari one and the probe reported it being
#: looked up under NECRONS with 0 blocks - correct behaviour, and a reminder
#: that "whose Stratagem is this" is answered by the selected unit, not by the
#: probe's assumptions.
BUTTON_BY_OWNER = {"Player 1": "Forewarned", "Player 2": "Sudden Storm"}
BUTTON_NAMES = set(BUTTON_BY_OWNER.values())
_real_buttons_for = proactive_stratagems.ProactiveStratagems.buttons_for


def buttons_for(self, squad):
    out = list(_real_buttons_for(self, squad))
    name = BUTTON_BY_OWNER.get(getattr(squad, "owner", None)) if squad is not None else None
    if name:
        out.append((f"{name} (1 CP)", lambda: None))
    return out


proactive_stratagems.ProactiveStratagems.buttons_for = buttons_for

_real_move_range = Renderer.draw_move_range


def draw_move_range(self, surface, board, movement_controller):
    # RE-SELECTED every frame, not once: the harness advances phases and turns,
    # and each of those clears the pick - so a single select() gives only a
    # handful of frames with a Stratagem button on screen, far short of the
    # 1400ms dwell this is here to exercise.
    if True:
        for token in movement_controller.all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is not None and squad.owner == "Player 1":
                movement_controller.select(squad.models[0])
                if movement_controller.selected_squad is not None:
                    break
    return _real_move_range(self, surface, board, movement_controller)


Renderer.draw_move_range = draw_move_range

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

state = {"seen": None, "buttons": [], "asked": [], "drawn": [], "frames": 0}

_real_panel_draw = action_panel.ActionPanel.draw
_real_update = action_panel.ActionPanel.update_tooltip
_real_tip_draw = stratagem_tooltip.StratagemTooltip.draw
_real_mouse = pygame.mouse.get_pos
_real_ticks = pygame.time.get_ticks


def ticks():
    """TIME COMPRESSED, not faked. The dwell is 1400ms of real clock, and this
    harness cannot hold an unmodal, cursor-on-the-button state that long - the
    AI keeps opening prompts, which correctly suppress the tooltip. Advancing
    the clock the loop itself reads makes two consecutive on-button frames
    enough, and leaves every other link in the chain untouched: the panel still
    records the button, main() still polls, the lookup still reads the corpus."""
    return _real_ticks() * 200


def panel_draw(self, surface, rect, *args, **kwargs):
    out = _real_panel_draw(self, surface, rect, *args, **kwargs)
    state["frames"] += 1
    if self._stratagem_buttons:
        state["with_buttons"] = state.get("with_buttons", 0) + 1
        # REFRESHED every frame, not captured once: the panel relays out as the
        # game state changes, so a rect grabbed on the first frame stops being
        # where the button is - the same staleness that made the aura probe
        # measure the wrong unit.
        if state["seen"] is None:
            state["seen"] = state["frames"]
        state["buttons"] = [(r.copy(), n) for r, n in self._stratagem_buttons]
    return out


def update_tooltip(self, mouse_pos, mouse_down, now_ms):
    state["polls"] = state.get("polls", 0) + 1
    if self.stratagem_at(mouse_pos):
        state["on_button"] = state.get("on_button", 0) + 1
    if mouse_down:
        state["mouse_down"] = state.get("mouse_down", 0) + 1
    if NEUTRALIZE:
        # The pre-fix world: no dwell tooltip at all.
        return None
    # THE DWELL IS PRE-AGED when the cursor is genuinely on a button, and that
    # is the third and last fact this harness cannot produce for itself: the
    # tooltip needs the cursor to rest on a Stratagem button, in the Movement
    # phase, with no prompt open, for 1400ms together - and the AI opens a
    # prompt every few frames, which correctly suppresses it. Everything after
    # this line is the real thing: the real dwell logic returns the name, main()
    # looks it up in the real corpus and draws the real box.
    if self.stratagem_at(mouse_pos) and self._tip_since is not None:
        self._tip_since = now_ms - action_panel.STRATAGEM_TIP_DELAY_MS
    out = _real_update(self, mouse_pos, mouse_down, now_ms)
    if out:
        state["opened"] = state.get("opened", 0) + 1
    return out


def tip_draw(self, surface, faction_keyword, detachments, name, mouse_pos,
             anchor_rect=None):
    rect = _real_tip_draw(self, surface, faction_keyword, detachments, name,
                          mouse_pos, anchor_rect=anchor_rect)
    blocks = self.blocks_for(faction_keyword, detachments, name)
    state["drawn"].append((name, faction_keyword, len(blocks), rect is not None))
    return rect


def mouse_pos():
    """Park the cursor on the injected button - BY NAME, not by position.
    The panel draws the engine's own Stratagems first and my one last, and the
    order shifts with the phase, so an index would wander onto a different
    button (and "Command Re-roll" is a CORE Stratagem with no detachment entry,
    which would correctly draw nothing and prove nothing)."""
    for rect, name in state["buttons"]:
        if name in BUTTON_NAMES:
            return rect.center
    return _real_mouse()


action_panel.ActionPanel.draw = panel_draw
action_panel.ActionPanel.update_tooltip = update_tooltip
stratagem_tooltip.StratagemTooltip.draw = tip_draw
pygame.mouse.get_pos = mouse_pos
pygame.time.get_ticks = ticks

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- stratagem tooltip spy" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
if not state["buttons"]:
    print("  no Stratagem button was ever drawn - INCONCLUSIVE")
    raise SystemExit(2)
print(f"  buttons drawn        : {[n for _r, n in state['buttons']]}")
print(f"  frames with a button : {state.get('with_buttons', 0)}")
print(f"  polls / on button    : {state.get('polls', 0)} / {state.get('on_button', 0)}"
      f"  (mouse held {state.get('mouse_down', 0)})")
print(f"  dwell completed      : {state.get('opened', 0)}")
if not state["drawn"]:
    print("  TOOLTIP              : never opened")
else:
    name, faction, blocks, drew = state["drawn"][-1]
    print(f"  TOOLTIP              : {name!r} ({faction}) -> "
          f"{blocks} printed blocks, drawn={drew}")
