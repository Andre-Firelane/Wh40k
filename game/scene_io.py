"""Saving and restoring a board position, so a reported failure becomes a
fixture instead of a reconstruction.

WHY THIS EXISTS. Every movement/placement bug in this project so far has been
reproduced by hand: read the `[move detail]` line out of the log, copy the
coordinates into a throwaway script, rebuild the units around them, and hope
the rest of the board did not matter. CLAUDE.md says "exakt reproduziert
(Positionen aus dem Log)" fifteen times over. It is slow, and worse, it is
lossy in exactly the direction that hides the bug: the reconstruction contains
the unit that misbehaved and leaves out the fourteen others that were in its
way. Measured, that omission is worth about twenty points of movement quality
(see measure_crowded_movement.py) - i.e. the reconstructions were routinely
missing the dominant factor.

WHAT IS AND IS NOT STORED. Only what varies. The map's terrain, objectives and
deployment zones are rebuilt from the map key, and the armies are rebuilt by
whoever builds the scene - a snapshot never carries datasheets, wargear or
points. It carries where everything IS: per model a position and its remaining
wounds, per unit whether it is on the board, in reserves or embarked, plus the
turn state and command points.

That is deliberate rather than lazy. Rebuilding a unit from a dump would mean
re-deriving its composition, wargear choices and attached-unit structure, all
of which already have exactly one correct source (game/army_lists.py), and a
second one would drift from it silently. The cost is that a snapshot is tied to
the roster that produced it - restore() says so plainly instead of quietly
placing half an army.

WHICH LISTS were on the table IS stored, though, and only since either player
could field any of them: without it a snapshot taken of an Aeldari-vs-Orks game
would restore into whatever config happened to say, and every single unit name
would then miss. It is one line - {player: army key} - and it is what --load
rebuilds the armies from (see armies_in() and main()). Optional on the way in:
a snapshot written before this existed simply has no such line, and is restored
against the configured lists exactly as it always was.

Not stored either: blood decals (cosmetic), the AI's turn plan (regenerated),
and anything derived from the above.
"""

import json
import os

FORMAT_VERSION = 1

BOARD = "board"
RESERVES = "reserves"
EMBARKED = "embarked"


def _squad_entries(state):
    """Every squad in the scene with where it currently is, keyed by name.

    Walks the three places a unit can be (rule 03.02 reserves, rule 18.02
    embarked, or on the board) rather than a single registry, because there
    isn't one - GameState keeps them in three separate lists on purpose."""
    entries = {}
    seen = set()
    for token in state.tokens:
        squad = getattr(token, "squad", None)
        if squad is None or id(squad) in seen:
            continue
        seen.add(id(squad))
        entries[squad.name] = (squad, BOARD, None)
    for squad in state.reserves:
        if id(squad) not in seen:
            seen.add(id(squad))
            entries[squad.name] = (squad, RESERVES, None)
    for squad in state.embarked_squads:
        if id(squad) in seen:
            continue
        seen.add(id(squad))
        transport = getattr(squad, "embarked_in", None)
        transport_squad = getattr(transport, "squad", None)
        entries[squad.name] = (squad, EMBARKED, getattr(transport_squad, "name", None))
    return entries


def capture(state, map_key, turn_tracker=None, command_points=None, armies=None):
    """The current board position as a plain dict, ready for write()."""
    squads = []
    for name, (squad, placement, transport_name) in _squad_entries(state).items():
        squads.append({
            "name": name,
            "owner": squad.owner,
            "placement": placement,
            "embarked_in": transport_name,
            "battle_shocked": bool(getattr(squad, "battle_shocked", False)),
            # Full precision, deliberately, at the cost of an uglier file.
            # Rounding to four decimals was tried and reproduced a live scene
            # to within 0.0001" - harmless for anything a rule looks at, but
            # the whole point of a fixture is to reproduce borderline geometry,
            # and the closest thing to a threshold in this engine is the 0.05"
            # overlap epsilon. A snapshot that is exact leaves no room to
            # wonder whether a case failed to reproduce because of the file.
            "models": [
                {"x_in": m.x_in, "y_in": m.y_in, "wounds": m.current_wounds}
                for m in squad.models
            ],
        })
    data = {
        "format": FORMAT_VERSION,
        "map": map_key,
        "squads": squads,
    }
    if armies:
        # Written next to the map key and read back the same way: both answer
        # "what has to be rebuilt before these positions mean anything".
        data["armies"] = dict(armies)
    if turn_tracker is not None:
        data["turn"] = {
            "battle_round": getattr(turn_tracker, "battle_round", None),
            "phase": getattr(turn_tracker, "phase", None),
            "turn_owner": getattr(turn_tracker, "turn_owner", None),
            "active_player": getattr(turn_tracker, "active_player", None),
        }
    if command_points is not None:
        data["command_points"] = dict(command_points.cp)
    return data


def write(data, path):
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1)
    return path


def read(path):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("format") != FORMAT_VERSION:
        raise ValueError(
            f"{path} is a format {data.get('format')} snapshot, this build reads "
            f"format {FORMAT_VERSION}"
        )
    return data


def armies_in(path):
    """{player -> army key} this snapshot was taken of, or None if it predates
    that being recorded.

    Read on its own, before anything is built, because the armies have to be
    known EARLIER than the positions do: main() rebuilds the units first and
    only then puts them back where they stood. Same shape as the map key, which
    --load already reads out of the file for the same reason."""
    armies = read(path).get("armies")
    return dict(armies) if armies else None


def restore(data, state, squads=None):
    """Move an already-built scene into the position `data` describes.

    The scene must already contain the same units - see the module docstring
    for why a snapshot does not rebuild them. Anything that does not line up is
    reported rather than patched over: a name in the snapshot that the scene
    does not have, a name the scene has that the snapshot does not, or a unit
    whose model count grew. Returns the list of those complaints, empty when
    the restore was exact.

    A unit with FEWER models in the snapshot than in the scene is not a
    mismatch - those are casualties, and the surplus models are removed.

    `squads` is every unit in the scene, for the case where none of them is in
    any of GameState's three lists yet - which is exactly how main() looks when
    the pre-game sequence (03.01) has not run, i.e. the case a snapshot exists
    to replace. Without it the units are found from the state.

    Turn state and command points are NOT touched here; see restore_turn(),
    which has to run after whatever starts the battle."""
    if squads is None:
        by_name = {name: squad for name, (squad, _p, _t) in _squad_entries(state).items()}
    else:
        by_name = {squad.name: squad for squad in squads}
    problems = []
    wanted = {entry["name"]: entry for entry in data.get("squads", [])}

    for name in by_name:
        if name not in wanted:
            problems.append(f"the scene has {name!r}, the snapshot does not")
    for name in wanted:
        if name not in by_name:
            problems.append(f"the snapshot has {name!r}, the scene does not")

    for name, entry in wanted.items():
        squad = by_name.get(name)
        if squad is None:
            continue
        models = entry["models"]
        if len(models) > len(squad.models):
            problems.append(
                f"{name!r} has {len(models)} models in the snapshot but only "
                f"{len(squad.models)} in the scene"
            )
            continue
        # Casualties: the snapshot is the shorter list, so the tail of the
        # scene's unit did not survive. Dropped straight out rather than left
        # at zero wounds - remove_dead_models() has already run by the time a
        # position is captured, so a restored scene should look the same.
        casualties = squad.models[len(models):]
        squad.models = squad.models[:len(models)]
        for model in casualties:
            if model in state.tokens:
                state.tokens.remove(model)
        for model, saved in zip(squad.models, models):
            model.x_in = saved["x_in"]
            model.y_in = saved["y_in"]
            if saved.get("wounds") is not None:
                model.current_wounds = saved["wounds"]
        squad.battle_shocked = entry.get("battle_shocked", False)

    _restore_placement(wanted, by_name, state, problems)
    return problems


def restore_turn(data, turn_tracker=None, command_points=None):
    """Battle round, phase, whose turn it is, and command points.

    Separate from restore() because of ordering: whatever begins the battle
    (main()'s begin_battle -> TurnTracker.start_battle) resets the round to 1
    and the phase to Command, so applying the snapshot's turn state before that
    would be silently undone. Returns the same kind of complaint list."""
    problems = []
    turn = data.get("turn")
    if turn and turn_tracker is not None:
        _restore_turn(turn, turn_tracker, problems)
    points = data.get("command_points")
    if points and command_points is not None:
        for player, value in points.items():
            if player in command_points.cp and value is not None:
                command_points.cp[player] = value
    return problems


def _restore_placement(wanted, by_name, state, problems):
    """Put each unit into the right one of the three lists. Done in one pass
    after every unit's models have been positioned, so an embarked unit can
    name a transport that is itself being restored."""
    transports = {}
    for name, squad in by_name.items():
        for model in squad.models:
            transports.setdefault(name, model)
            break

    for name, entry in wanted.items():
        squad = by_name.get(name)
        if squad is None:
            continue
        placement = entry.get("placement", BOARD)
        for model in squad.models:
            if model in state.tokens:
                state.tokens.remove(model)
        if squad in state.reserves:
            state.reserves.remove(squad)
        if squad in state.embarked_squads:
            state.embarked_squads.remove(squad)
        squad.embarked_in = None

        if placement == RESERVES:
            state.reserves.append(squad)
        elif placement == EMBARKED:
            carrier = transports.get(entry.get("embarked_in"))
            if carrier is None:
                problems.append(
                    f"{name!r} was embarked in {entry.get('embarked_in')!r}, "
                    "which is not in this scene - left on the board instead"
                )
                state.tokens.extend(squad.models)
                continue
            squad.embarked_in = carrier
            state.embarked_squads.append(squad)
        else:
            state.tokens.extend(squad.models)


def _restore_turn(turn, turn_tracker, problems):
    from game.turn import PHASES

    if turn.get("battle_round") is not None:
        turn_tracker.battle_round = turn["battle_round"]
    owner = turn.get("turn_owner")
    if owner is not None:
        turn_tracker.turn_owner = owner
        turn_tracker.set_active(turn.get("active_player") or owner)
    phase = turn.get("phase")
    if phase is not None:
        if phase in PHASES:
            turn_tracker.phase_index = PHASES.index(phase)
        else:
            problems.append(f"unknown phase {phase!r} in the snapshot")
