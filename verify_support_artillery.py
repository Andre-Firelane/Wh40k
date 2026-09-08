"""Runtime proof through the REAL main() loop that Support Artillery is offered
at Declare Battle Formations, and that pressing it forms one unit.

WHAT WAS MISSING. The rule was transcribed on all three platforms, and the
MECHANISM had been in place since they were built - rule 19.01's SUPPORT role,
can_attach(), and the pairing table read off the printed "SUPPORT: GUARDIAN
DEFENDERS" line. What did not exist was the DECISION. The printed text puts the
join at the start of the Declare Battle Formations step, beside the transport
and Reserves declarations, and nothing ever asked. User: "im pre game muss man
sich entscheiden ob die Support weapons (d-cannons) an einen Guardian Trupp
angeschlossen werden sollen oder allein stehen. aehnlich wie man im pregame
Einheiten in Transporter steckt."

"Built but never FED" has shipped in this repo six times, and a source guard
only shows that a call is written down - so this drives selfplay.py's real
main() loop and reads back:

  1. the LABELS the real ActionPanel drew in the real formations step;
  2. what happened after a real click on the Join button - through the panel's
     own callback, the real PregameController, the real attach();
  3. whether the merged unit is what got deployed, with the platform gone from
     the army as a unit of its own.

THE ONE STAGED FACT, and it is a choice rather than a fabrication: selfplay
answers the formations panel by pressing buttons[0], which is always "Deploy on
the battlefield". This reorders the panel's own button list so the Join button
is the one that gets pressed - a real click on a real rect that the real panel
drew, exactly as a human choosing the other answer. Nothing else is stubbed.

The army is fixed to aeldari_guardian_battlehost because it is the shipped list
that fields both halves of the question: two D-cannon Platforms and two
Guardian Defenders blocks.

Harness trap this walks into deliberately (documented in CLAUDE.md): importing
selfplay runs nothing because of its __main__ guard, so it goes through runpy.

Usage:  python verify_support_artillery.py [map2] [frames]
        python verify_support_artillery.py map2 --neutralize
"""

import runpy
import sys

from game import config, formations
from game.ui.action_panel import ActionPanel

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

MAP_KEY = next((a for a in sys.argv[1:] if not a.isdigit()), "map2")
FRAMES = next((a for a in sys.argv[1:] if a.isdigit()), "900")

config.PLAYER1_ARMY = "aeldari_guardian_battlehost"
config.PLAYER2_ARMY = "necrons"

if NEUTRALIZE:
    # THE PRE-FIX WORLD: no unit is ever a legal host, so the panel draws no
    # Join button and the platform's only answers are Deploy and Reserves -
    # which is exactly where this feature stood before.
    formations.eligible_join_targets = lambda *a, **k: []

SEEN = []            # every button label the formations step drew
JOINED = []          # (platform name, host name) for each click that landed
LIVE = {}            # the real GameState, taken off the controller main() built

_real_formations = ActionPanel._draw_pregame_formations
_real_button = ActionPanel._draw_button


def _button(self, surface, rect, label, **kw):
    SEEN.append(label)
    return _real_button(self, surface, rect, label, **kw)


def _formations(self, surface, rect, pregame_controller, button_width, text_y):
    before = len(self._buttons)
    LIVE["state"] = pregame_controller.game_state
    out = _real_formations(self, surface, rect, pregame_controller, button_width, text_y)
    # Press the JOIN answer instead of the default DEPLOY one. selfplay clicks
    # buttons[0]; moving the Join button there is how a human choosing the
    # other option reaches the same callback.
    drawn = self._buttons[before:]
    labels = SEEN[-len(drawn):] if drawn else []
    for index, label in enumerate(labels):
        if label.startswith("Join "):
            squad = pregame_controller.current_formation_unit(
                pregame_controller.first_human())
            JOINED.append((getattr(squad, "name", "?"), label[len("Join "):]))
            self._buttons[before:] = [drawn[index]] + drawn[:index] + drawn[index + 1:]
            break
    return out


ActionPanel._draw_button = _button
ActionPanel._draw_pregame_formations = _formations

sys.argv = ["selfplay.py", MAP_KEY, FRAMES]
loc = runpy.run_module("selfplay", run_name="__main__")

print()
print("=== Support Artillery through the real main() loop ===")
print("  formations buttons offering a join : %d"
      % len([l for l in SEEN if l.startswith("Join ")]))
for platform, host in JOINED:
    print("  clicked                            : %s -> %s" % (platform, host))
if not JOINED:
    print("  clicked                            : NOTHING - no join was ever offered")

# The LIVE GameState, taken off the controller main() built rather than
# rebuilt here - the whole point is to read what the real run produced.
state = LIVE.get("state")
units = []
if state is not None and hasattr(state, "all_squads"):
    units = list(state.all_squads())
merged = [u for u in units if "+ D-cannon Platform" in u.name]
alone = [u for u in units if u.name.endswith("D-cannon Platform 1")
         or u.name.endswith("D-cannon Platform 2")]
print("  merged units on the table          : %s"
      % ([u.name + " (%d models)" % len(u.models) for u in merged] or "none"))
print("  platforms still standing alone     : %s"
      % ([u.name for u in alone] or "none"))
print()
print("VERDICT:", "a join was offered AND taken" if JOINED and merged
      else "no join reached the table")
