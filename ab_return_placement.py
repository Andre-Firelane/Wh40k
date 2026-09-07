"""A/B probes for the model-return placement.

Each restores ONE piece of the pre-change world AT THE SOURCE. A probe that
does not bite is a finding about the TEST (Fehlerklasse 24).

Probe 1 is the whole pre-change world: the ability applies its own spots for
everyone, which is what all eight did.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SUITE = os.path.join(ROOT, "test_return_placement.py")
BASE = 132

G = lambda *p: os.path.join(ROOT, "game", *p)


def clear_cache():
    for root, dirs, _f in os.walk(ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def run():
    out = subprocess.run([sys.executable, SUITE], capture_output=True, text=True,
                         cwd=ROOT).stdout
    for line in out.splitlines():
        if "checks passed" in line:
            got, total = line.strip().split()[0].split("/")
            return int(got), int(total)
    return -1, -1


def probe(label, path, old, new):
    src = open(path, encoding="utf-8").read()
    if src.count(old) != 1:
        print(f"  SKIP {label}: anchor found {src.count(old)}x")
        return
    open(path, "w", encoding="utf-8").write(src.replace(old, new, 1))
    try:
        clear_cache()
        got, total = run()
    finally:
        open(path, "w", encoding="utf-8").write(src)
    print(f"  {'BITES' if got < BASE else '*** DID NOT BITE ***':22} {got}/{total}  {label}")


clear_cache()
print(f"baseline: {run()[0]}/{BASE}")

# 1. THE WHOLE PRE-CHANGE WORLD: the ability applies its own spots for
#    everyone and nothing is ever opened.
probe(
    "the ability places for everyone, as all eight used to",
    G("reanimation_protocols.py"),
    "    if placer is not None:",
    "    if False:",
)

# 2. The placer opens a placement for the AI too - which would stall the loop
#    and, worse, is a decision the agent would have to be asked about.
probe(
    "a placement is opened for the AI as well",
    G("return_placement.py"),
    "        if (squad.owner in self.auto_players or self.setup_controller is None",
    "        if (False or self.setup_controller is None",
)

# 3. The subset collapses: SetupController picks up the WHOLE unit, so the
#    survivors get dragged along with the returning models.
probe(
    "the placement takes the whole unit again",
    G("setup.py"),
    "        if self._placing_models is None:\n            return list(self.setting_up_squad.models)",
    "        if True:\n            return list(self.setting_up_squad.models)",
)

# 4. The overlap exemption goes back to the whole squad - so a returning model
#    may be dropped on a survivor, and confirm rejects the lot (Fehlerklasse 8).
probe(
    "survivors are exempt from overlap again",
    G("setup.py"),
    """                exempt = (self.placing_models
                          if self.is_partial and squad is self.setting_up_squad
                          else (squad.models if squad is not None else ()))""",
    """                exempt = squad.models if squad is not None else ()""",
)

# 5. set_up_this_turn marked on a return - rule 18.02 then blocks the unit
#    from embarking for the rest of the turn. Invisible until a phase later.
probe(
    "a return counts as being set up this turn",
    G("setup.py"),
    "        if self._mark_set_up:\n            squad.set_up_this_turn = True",
    "        squad.set_up_this_turn = True",
)

# 6. Cancel stops putting the models back down, so an abandoned placement
#    leaves them alive on the board for free.
probe(
    "cancelling leaves the returned models standing",
    G("return_placement.py"),
    "        for model in models:\n            if model in squad.models:\n                squad.models.remove(model)",
    "        for model in []:\n            if model in squad.models:\n                squad.models.remove(model)",
)

# 7. A model with nowhere legal to stand is offered anyway - so a human is
#    asked to place something the rule did not return.
probe(
    "a model with no legal spot is placed anyway",
    G("return_placement.py"),
    "        pairs = [(m, s) for m, s in zip(models, spots) if s is not None]",
    "        pairs = [(m, s if s is not None else (0.0, 0.0)) for m, s in zip(models, spots)]",
)

# 8. The panel loses its Confirm route - the placement opens and nothing can
#    ever close it. Fehlerklasse 25 exactly.
probe(
    "the panel cannot resolve the placement",
    os.path.join(ROOT, "game", "ui", "action_panel.py"),
    "            confirm_callback = return_placement_controller.confirm\n"
    "            cancel_callback = return_placement_controller.cancel",
    "            confirm_callback = setup_controller.confirm_setup\n"
    "            cancel_callback = setup_controller.cancel_setup",
)

# 9. is_placeable stops honouring the subset, so a survivor can be dragged out
#    of formation during someone else's return.
probe(
    "a survivor becomes draggable",
    G("setup.py"),
    "            and token in self.placing_models",
    "            and token in self.setting_up_squad.models",
)

# --------------------------------------------------------------------------
# The reported bug: the OTHER doors into reanimate()
# --------------------------------------------------------------------------
# User: "Einheiten wurde automatisch platziert bei protocol of the undying
# legion, obwohl ich necrons spiele." The army rule's own controller was
# routed; the two modules that call the same reanimate() were not.

# 10. THE REPORTED WORLD, exactly: Undying Legions applies its own spots.
probe(
    "Undying Legions places for everyone (the reported bug)",
    G("protocol_undying_legions.py"),
    "            game_state=self.game_state,\n            placer=self.placer,",
    "            game_state=self.game_state,",
)

# 11. The same hole in the Resurrection Orb - found by counting the callers
#     rather than by a second report.
probe(
    "the Resurrection Orb places for everyone",
    G("resurrection_orb.py"),
    "            game_state=self.game_state,\n            placer=self.placer,",
    "            game_state=self.game_state,",
)

# 12. Wired in the module but never HANDED one by main.py - the "built but
#     never FED" class this repo has hit six times. Behaviour tests cannot see
#     it; only the source can.
probe(
    "main.py hands Undying Legions no placer",
    os.path.join(ROOT, "main.py"),
    "        placer=return_placement_controller,\n    )\n    eternal_revenant_controller",
    "    )\n    eternal_revenant_controller",
)

# 13. ...and the same for the orb, whose placer arrives by assignment because
#     it is built ~600 lines before the placer exists.
probe(
    "main.py hands the Resurrection Orb no placer",
    os.path.join(ROOT, "main.py"),
    "    resurrection_orb_controller.placer = return_placement_controller\n",
    "",
)

# --------------------------------------------------------------------------
# Coherency is part of a RETURN placement, and it is drawn that way
# --------------------------------------------------------------------------
# User: "immer wenn man Einheiten platzieren muss, zb durch Reanimation, muss
# man in coherency platzieren. dementsprechend muss auch das overlay sein. im
# Moment geht das ueber die ganze map?"

# 14. THE REPORTED WORLD: the placement predicate drops coherency again, so the
#     overlay paints 85.9% of the board and the drag stops anywhere.
probe(
    "a return placement ignores coherency (the reported bug)",
    G("setup.py"),
    "        if not self.is_partial:\n            return base",
    "        if True:\n            return base",
)

# 15. Coherency reduced to "has SOME neighbour within 2 inches" - the check
#     Squad.check_coherency() was rewritten to replace, because two
#     mutually-coherent clusters satisfy it while the unit has split in half.
probe(
    "connectivity weakened to a neighbour test",
    G("squad.py"),
    "        for group in components:\n"
    "            if not any(",
    "        for group in [[m for g in components for m in g]]:\n"
    "            if not any(",
)

# 16. The cached overlay mask stops following the squadmates, so it keeps
#     painting the ring from before the last model was dropped.
probe(
    "the overlay mask is cached across moves that invalidate it",
    G("setup.py"),
    "        if not self.is_partial:\n            return self.placement_generation",
    "        if True:\n            return self.placement_generation",
)

# 17. ...and main.py stops asking for it at all - "built but never FED", the
#     class this repo has hit six times. No behaviour test can see it.
probe(
    "main.py keys the overlay on the generation alone again",
    os.path.join(ROOT, "main.py"),
    "                session_key = (\"setup\", setup_controller.overlay_cache_key(None))",
    "                session_key = (\"setup\", setup_controller.placement_generation)",
)

# 18. The other direction: coherency leaking into a FULL Set Up, which the user
#     explicitly kept as it is - and which would also change what the
#     deployment AI is allowed to do if it ever came through here.
probe(
    "coherency also applies to a full Set Up",
    G("setup.py"),
    "        if not self.is_partial:\n            return base",
    "        if False:\n            return base",
)

# --------------------------------------------------------------------------
# The overlay is drawn as BASE EDGES, not centres
# --------------------------------------------------------------------------
# User: "momentan ist die Grenze des overlays so dass der Base Mittelpunkt bis
# zur Grenze gehen kann. intuitiver waere aber der Baserand."

# 19. THE PRE-CHANGE WORLD: the zones are evaluated at the model's real radius
#     again, so the line moves with the base size - one curve per model, and
#     no single picture is right for a unit with mixed bases.
probe(
    "the zones are measured from the centre again",
    G("setup.py"),
    "        def keep_out(x_in, y_in):\n"
    "            real = token.radius_in\n"
    "            token.radius_in = 0.0",
    "        def keep_out(x_in, y_in):\n"
    "            real = token.radius_in\n"
    "            token.radius_in = token.radius_in",
)

# 20. The coherency band is built at the real radius, so it grows with the base
#     - the exact asymmetry that made the old "draw the biggest model" fallback
#     unsafe.
probe(
    "the coherency band grows with the base size",
    G("setup.py"),
    "            token.radius_in = 0.0\n"
    "            try:\n"
    "                # Built here, inside the zero-radius window",
    "            token.radius_in = token.radius_in\n"
    "            try:\n"
    "                # Built here, inside the zero-radius window",
)

# 21. The band is never produced, so the one condition a player cannot work out
#     by eye is the one thing the picture does not show.
probe(
    "no coherency band is produced at all",
    G("setup.py"),
    "        if self.is_partial and unit is not None:",
    "        if False and unit is not None:",
)

# 22. The renderer draws only the keep-out layer - "built but never FED", the
#     class this repo has hit six times.
probe(
    "the renderer never draws the band layer",
    G("renderer.py"),
    "        if band_fn is not None:\n            self._coherency_overlay.draw(",
    "        if False:\n            self._coherency_overlay.draw(",
)

# 23. ...and main.py stops handing the zones over, falling back to nothing.
probe(
    "main.py stops asking for the zones",
    os.path.join(ROOT, "main.py"),
    "                keep_out_fn, band_fn = setup_controller.base_edge_zones(\n"
    "                    placement_squad, band_token)",
    "                keep_out_fn, band_fn = (lambda x, y: False), None",
)

# 24. The token's radius is left mangled after a call - the one real hazard of
#     reading the predicate at radius zero, since it mutates a live model.
probe(
    "the radius is not restored after a zone query",
    G("setup.py"),
    "            try:\n"
    "                return not base(token, x_in, y_in)\n"
    "            finally:\n"
    "                token.radius_in = real",
    "            try:\n"
    "                return not base(token, x_in, y_in)\n"
    "            finally:\n"
    "                pass",
)
