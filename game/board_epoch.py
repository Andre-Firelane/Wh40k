"""ONE answer to "has anything a geometric question depends on moved since I
last looked" - the cache key shared by the per-frame sweeps that are too
expensive to re-run every frame and too correctness-critical to key on a proxy.

WHY NOT len(state.tokens). That is what main.py's four caches
(visibility_cache, shoot_targets_cache, greater_good_targets_cache,
fire_overwatch_targets_cache) use as their "the board changed" term, and it is
a deliberate trade-off there: those sets are only ever computed while nothing is
driving. It is NOT good enough for a cache that answers a BUTTON in the Shooting
phase, because models really do move mid-phase - the opponent's reactive moves
(MovementController.REACTIVE_MOVE_MODES) and the active player's own extras
(OUT_OF_PHASE_MOVE_MODES: Torchstar, Fire and Fade, Tactical Acumen, ...). A
stale button is not a slow button; it offers a rule the board no longer allows.

WHAT IT COSTS, measured: 0.099 ms per frame over the 179 tokens of a T'au vs
Orks map2 board - against the 4732 ms sweep it guards. There is no reason to
approximate here.

WHAT IS IN IT.
  * position, because that is what line of sight and every range test read;
  * current_wounds, because a model that died THIS frame is still in the list
    (remove_dead_models() runs once a frame, error class 12) and because
    Arro'kon's tier threshold is literally a living-model count;
  * the tuple's LENGTH, which covers models actually leaving the board.

Read by game/greater_good.py and game/arrokon_protocol.py."""


def fingerprint(all_tokens):
    return tuple((t.x_in, t.y_in, t.current_wounds) for t in all_tokens)
