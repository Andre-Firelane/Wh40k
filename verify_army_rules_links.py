"""Runtime proof through the REAL main() loop that both rules links work.

"Built but never FED" has shipped in this repo six times, and a source guard
only shows the call is written down. So this drives selfplay.py's real main()
loop, waits until the panel has actually drawn its links, then for EACH of
them synthesises a click at the coordinates the panel itself reported, and
checks what the reader opened on.

It also feeds the reader the event PAIR pygame really delivers for one wheel
notch (MOUSEWHEEL plus the legacy MOUSEBUTTONDOWN button 4/5) and checks the
reader survives it - that pair is the reported bug, and it is exactly what a
synthetic single-event test cannot reproduce.

Harness trap this walks into deliberately (documented in CLAUDE.md): importing
selfplay runs nothing because of its __main__ guard, so it goes through runpy.

Usage:  python verify_army_rules_links.py [map2]
        python verify_army_rules_links.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game.ui import army_rules_overlay, game_status_panel

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

state = {"links": [], "opened": [], "wheel_survived": None, "clicks": 0,
         "seen": None}

_real_panel_draw = game_status_panel.GameStatusPanel.draw
_real_show = army_rules_overlay.ArmyRulesOverlay.show
_real_handle = army_rules_overlay.ArmyRulesOverlay.handle_event


def panel_draw(self, surface, rect, *args, **kwargs):
    # selfplay REPLACES pygame.event.get wholesale at import time, so a
    # wrapper installed before runpy is simply overwritten. Installing it from
    # here - the first frame the panel draws, by which point selfplay's own
    # pump is in place - wraps the real one instead of racing it.
    _install_pump()
    out = _real_panel_draw(self, surface, rect, *args, **kwargs)
    if self._army_rules_rects and not state["links"]:
        state["links"] = [(p, r.copy()) for p, r in self._army_rules_rects]
        state["seen"] = _frames["n"]
    return out


def show(self, armies, player):
    opened = _real_show(self, armies, player)
    if opened:
        players = {b.text.split(" - ")[0] for b in self._blocks if b.kind == "player"}
        state["opened"].append((player, sorted(players), len(self._blocks)))
    return opened


def handle_event(self, event):
    if NEUTRALIZE and event.type == pygame.MOUSEBUTTONDOWN:
        # The pre-fix world: ANY button dismisses, wheel twins included.
        self.dismiss()
        return True
    return _real_handle(self, event)


game_status_panel.GameStatusPanel.draw = panel_draw
army_rules_overlay.ArmyRulesOverlay.show = show
army_rules_overlay.ArmyRulesOverlay.handle_event = handle_event

# The probe rides main()'s own event pump: selfplay posts events into the same
# queue main() reads, so a click posted here is indistinguishable from a real
# one by the time the chain sees it.
_frames = {"n": 0}
_pump = {"real": None}


def _install_pump():
    if _pump["real"] is None:
        _pump["real"] = pygame.event.get
        pygame.event.get = event_get


def event_get(*args, **kwargs):
    _frames["n"] += 1
    events = list(_pump["real"](*args, **kwargs))
    if state["seen"] is None:
        return events
    # Scheduled RELATIVE to the frame the links first appeared: the pre-game
    # runs first, so a fixed frame number fires before the panel exists - which
    # is exactly the silent zero this probe is built to avoid.
    n = _frames["n"] - state["seen"]
    # REPLACING selfplay's own events on the frames under test, not adding to
    # them: selfplay clicks the board with button 1 every frame to drive the
    # game, and one of those would close the reader and be mistaken for the
    # bug being measured.
    if n == 2:
        player, rect = state["links"][0]
        state["clicks"] += 1
        return [pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": rect.center, "button": 1})]
    if n == 3:
        state["opened_before_wheel"] = _overlay_open()
        # One physical wheel notch, as pygame really queues it.
        return [pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1, "x": 0}),
                pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                   {"pos": (400, 400), "button": 5})]
    if n == 4:
        state["wheel_survived"] = _overlay_open()
        state["scrolled"] = max((ov.scroll for ov in _overlays), default=0)
        return [pygame.event.Event(pygame.KEYDOWN,
                                   {"key": pygame.K_ESCAPE, "mod": 0})]
    if n == 5:
        state["closed_by_esc"] = not _overlay_open()
        return []
    if n == 6 and len(state["links"]) > 1:
        player, rect = state["links"][1]
        state["clicks"] += 1
        return [pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": rect.center, "button": 1})]
    return events


_overlays = []
_real_init = army_rules_overlay.ArmyRulesOverlay.__init__


def init(self):
    _real_init(self)
    _overlays.append(self)


army_rules_overlay.ArmyRulesOverlay.__init__ = init


def _overlay_open():
    return any(ov.is_pending for ov in _overlays)


sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- army rules links spy" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print(f"  links the panel drew   : {[p for p, _r in state['links']]}")
print(f"  clicks posted          : {state['clicks']}")
for player, shown, blocks in state["opened"]:
    print(f"  clicked {player} -> reader shows {shown} ({blocks} blocks)")
print(f"  open before the wheel  : {state.get('opened_before_wheel')}")
print(f"  OPEN AFTER A WHEEL NOTCH: {state['wheel_survived']}  (scrolled to "
      f"{state.get('scrolled')})")
print(f"  ESC closes it          : {state.get('closed_by_esc')}")
