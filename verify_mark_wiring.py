"""Do the three Aeldari marks actually reach BOTH attack controllers in main()?

Not a unit test - a wiring probe against the real main(), because this is a
mistake a suite cannot see. Guide's melee half was dead for a whole datasheet's
worth of work: it was wired into game/fight.py's _hit_modifiers() and every
test passed it in explicitly, while main.py's FightController(...) call simply
never mentioned it. Found only when Doom needed the same seam. Same shape as
the earlier patch that hit take_one_action() instead of action_panel.draw().

So this spies on both constructors during a few frames of a real game and
asserts that each mark arrives, and that both controllers got the SAME object -
one mark drifting between phases would be just as silent.

Run it after touching main.py's controller construction:
    python verify_mark_wiring.py
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, r"C:\Users\Andre\Desktop\WH40")

import pygame  # noqa: E402

from game import fight as fight_mod  # noqa: E402
from game import shooting as shooting_mod  # noqa: E402

seen = []

for mod, cls_name in ((shooting_mod, "ShootingController"), (fight_mod, "FightController")):
    cls = getattr(mod, cls_name)
    original = cls.__init__

    def make(cls_name=cls_name, original=original):
        def spy(self, *a, **kw):
            seen.append((cls_name, kw.get("guide"), kw.get("doom"), kw.get("whispering_web")))
            return original(self, *a, **kw)
        return spy

    cls.__init__ = make()

# Stop the loop almost immediately - construction is all we need.
frames = [0]
real_flip = pygame.display.flip


def flip():
    frames[0] += 1
    if frames[0] > 3:
        raise SystemExit(0)
    return real_flip()


pygame.display.flip = flip
pygame.event.get = lambda *a, **k: []

import main  # noqa: E402

try:
    main.main()
except SystemExit:
    pass

ok = True
for cls_name, guide, doom, web in seen:
    good = guide is not None and doom is not None and web is not None
    ok = ok and good
    print(f"{'ok ' if good else 'FAIL'} {cls_name}: guide={type(guide).__name__} "
          f"doom={type(doom).__name__} web={type(web).__name__}")
if len(seen) < 2:
    ok = False
    print(f"FAIL only {len(seen)} controller(s) constructed - expected both")
# Same object in both, so one mark cannot drift between phases.
if any(len({id(m) for m in col}) != 1 for col in zip(*[row[1:] for row in seen])):
    ok = False
    print("FAIL the two controllers got DIFFERENT mark objects")
else:
    print("ok  both controllers share the same mark objects")
print("PASS" if ok else "FAILED")
raise SystemExit(0 if ok else 1)
