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
points. It carries where everything IS: per model a position, its remaining
wounds and WHICH model it is, per unit whether it is on the board, in reserves or
embarked, plus the turn state, command points, and what everybody has already
done this turn (game/activation_state.py).

The per-model identity is not decoration. A snapshot holds a unit's SURVIVORS;
the scene it is restored into holds the unit as BUILT. Pairing them off in
order therefore handed a character's remaining wounds to whichever trooper
happened to sit at that index and deleted the character instead - reported as
"Schaden auf Einheiten wurde nicht gespeichert", and true in the worst way:
the survivor came back above its own maximum wounds, i.e. undamaged. See
_match_models().

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
import time

from game import activation_state

FORMAT_VERSION = 1

# Where snapshots live. Named here rather than spelled out at each call site
# because three things now agree on it: F9's manual save, the per-round
# autosave, and newest(), which is what the menu's Resume entry offers.
SCENES_DIR = "scenes"
AUTOSAVE_NAME = "autosave.json"

BOARD = "board"
RESERVES = "reserves"
EMBARKED = "embarked"


def _profile_name(model):
    return getattr(getattr(model, "profile", None), "name", None)


def _weapon_names(model):
    return sorted(getattr(weapon, "name", "") or ""
                  for weapon in (getattr(model, "weapons", None) or ()))


def _match_models(saved, models):
    """Pair each saved model with the model in the rebuilt unit that it IS.

    WHY THIS IS NOT A ZIP. A snapshot stores the SURVIVORS of a unit, in the
    order the live unit had them; the scene it is restored into has the unit
    as it was BUILT, casualties included. Matching them by position was wrong
    in exactly the way that looks like "the damage was not saved":

        1 Skorpekh Destroyers 1 + Skorpekh Lord, one model left on 5 wounds

    is the Lord (7W) on 5 - and positionally the one surviving model is the
    FIRST built one, a plain Destroyer with 3 wounds, which then came back at
    5/3, i.e. undamaged and with the Lord deleted instead of the Destroyers.
    The same shape hits every attached unit (19.01), because the character is
    always at the tail: an Immortal was routinely handed the Plasmancer's
    wounds while the Plasmancer itself was the model dropped.

    THREE PASSES, narrowing. Each saved model takes the first still-unclaimed
    scene model that answers:

      1. the same datasheet line AND the same weapons - which is what tells a
         Storm Guardian with a fusion gun from the one next to it,
      2. the same datasheet line - the fallback for a model whose weapon list
         was in flux when the save was taken (game/firing_deck.py and
         game/support_turret.py both lend weapons across models for the length
         of an activation),
      3. anything left, in order - which is exactly the old behaviour, and so
         is also what a snapshot written before models carried an identity
         still gets.

    Returns (matched, casualties, unidentified): the scene models in SAVED
    order, the scene models nothing claimed, and how many entries had to fall
    through to pass 3 despite naming a datasheet line (the honest complaint -
    a roster that no longer matches, rather than a model that simply died)."""
    remaining = list(models)
    matched = [None] * len(saved)
    unidentified = 0

    def _take(index, predicate):
        for model in remaining:
            if predicate(model):
                remaining.remove(model)
                matched[index] = model
                return True
        return False

    for index, entry in enumerate(saved):
        line, weapons = entry.get("model"), entry.get("weapons")
        if line is None or weapons is None:
            continue
        _take(index, lambda m, l=line, w=list(weapons):
              _profile_name(m) == l and _weapon_names(m) == w)
    for index, entry in enumerate(saved):
        line = entry.get("model")
        if matched[index] is not None or line is None:
            continue
        _take(index, lambda m, l=line: _profile_name(m) == l)
    for index, entry in enumerate(saved):
        if matched[index] is not None:
            continue
        if entry.get("model") is not None:
            unidentified += 1
        _take(index, lambda m: True)
    return matched, remaining, unidentified


def _make_casualty(model, squad, state):
    """Put a model the snapshot does not list where a dead one belongs.

    Not merely dropped, which is what this used to do. Zero wounds is how this
    engine spells "destroyed" (Token.is_dead), and Squad.destroyed_models is
    where a casualty's last position is read from by everything that can bring
    one back or measure from it - Reanimation Protocols, Undying Legions,
    Grot Orderly, Vengeful Stars. A restored battle that had lost three Necron
    Warriors should have three Warriors to reanimate, the way the battle it
    was saved from did. Same treatment _evict() gives a wiped-out unit, and
    for the same reason; no kill is recorded here either, because that VP is
    already in the restored ledger."""
    if model in state.tokens:
        state.tokens.remove(model)
    model.current_wounds = 0
    destroyed = getattr(squad, "destroyed_models", None)
    if destroyed is None:
        squad.destroyed_models = [model]
    elif model not in destroyed:
        destroyed.append(model)


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


def capture(state, map_key, turn_tracker=None, command_points=None, armies=None,
            missions=None, activation=None):
    """The current board position as a plain dict, ready for write().

    `missions` is {slot: controller} for anything carrying mission state - see
    capture_missions() next door, which is what builds it. `activation` is the
    same shape for anything holding "this unit has already acted this turn"
    (see game/activation_state.py). Keyword-only in spirit and optional like
    every argument before it: a caller that has neither to hand writes exactly
    the file it always did."""
    squads = []
    entries = _squad_entries(state)
    for name, (squad, placement, transport_name) in entries.items():
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
            # WHICH model, not just how many. Positions and wounds are put
            # back onto the rebuilt unit by _match_models(), and without an
            # identity to match on it could only pair them off in order -
            # which quietly moved a character's remaining wounds onto a
            # trooper and deleted the character instead. The datasheet line
            # plus the weapon list is enough to tell every model of every
            # shipped roster apart, and it costs nothing to derive.
            "models": [
                {"x_in": m.x_in, "y_in": m.y_in, "wounds": m.current_wounds,
                 "model": _profile_name(m), "weapons": _weapon_names(m)}
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
    if missions:
        # Each controller writes its own slot: what is battle-scoped and what
        # is scoped to one turn is a fact about that controller's rules, not
        # about the file format, so the knowledge stays where the state lives.
        saved = {slot: ctrl.save_state()
                 for slot, ctrl in missions.items() if ctrl is not None}
        if saved:
            data["missions"] = saved
    # WHO HAS ALREADY ACTED. Written unconditionally, because the per-unit half
    # of it (the flags on Squad itself) needs no collaborator - only the
    # controller ledgers do. An untouched board still writes nothing: every
    # field in there is left out when it holds its default.
    acted = activation_state.capture(
        [squad for squad, _p, _t in entries.values()], activation)
    if acted:
        data["activation"] = acted
    return data


def restore_missions(data, missions):
    """Put the VP ledger, the Secondary deck and the Primary's latches back.

    Separate from restore() for the same ordering reason restore_turn() is:
    whatever begins the battle draws battle round 1's cards and zeroes the
    score, so applying this before that would be quietly thrown away. Returns
    the same kind of complaint list.

    A snapshot written before this existed simply has no "missions" section
    and restores exactly as it always did - the same way `armies` was added,
    and the reason FORMAT_VERSION does not move for it."""
    problems = []
    saved = data.get("missions") or {}
    if not saved:
        return problems
    for slot, controller in (missions or {}).items():
        if controller is None or slot not in saved:
            continue
        result = controller.load_state(saved[slot])
        if result:
            problems.extend(result)
    return problems


def restore_activation(data, squads, controllers=None):
    """Put "who has already acted this turn" back - see restore_missions()
    just above for why this is its own function and not part of restore().

    Same ordering rule, and here it has TEETH: begin_battle() clears
    set_up_this_turn on every unit it can find, so this has to run after it or
    rule 18.02's lock is wiped straight back off again."""
    return activation_state.restore(data.get("activation"), squads, controllers)


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


def map_key_in(path):
    """The battlefield this snapshot was taken on.

    Its own function because TWO callers need it before anything is built -
    `--load` on the command line and the main menu's Resume entry - and the
    map has to be known earlier than everything else, since the whole engine
    reads the board dimensions out of config (see maps.apply_to_config)."""
    return read(path).get("map")


def newest(directory=None):
    """The most recently written snapshot in `directory`, or None.

    By MTIME, tie-broken on name. Not by the timestamp in the default
    `scene_YYYYMMDD_HHMMSS` filename: the autosave is not named that way, and
    a file dropped in by hand is newest by having arrived. The name tie-break
    only exists so the answer is deterministic when two files share a second.

    Returns None for a missing directory rather than raising - "there is
    nothing to resume" is an ordinary answer here, and the menu greys its
    Resume entry on it.

    `directory` defaults to SCENES_DIR read AT CALL TIME, not baked into the
    signature: as a default argument it would be bound once at import, and
    then pointing this module somewhere else - which is exactly what a test
    with a throwaway folder does - would silently keep listing the real one."""
    directory = directory if directory is not None else SCENES_DIR
    try:
        names = os.listdir(directory)
    except OSError:
        return None
    paths = [os.path.join(directory, name) for name in names if name.endswith(".json")]
    # The newest one that can actually be READ. A .json in this folder is not
    # necessarily a snapshot - a half-written file, one from a newer format, or
    # something dropped in by hand - and returning it would offer the menu a
    # Resume it then has to grey out, hiding the perfectly good save sitting
    # behind it. Reading each candidate costs one small parse and stops at the
    # first hit, so in the normal case it is exactly one file.
    for path in sorted(paths, key=lambda p: (os.path.getmtime(p), os.path.basename(p)),
                       reverse=True):
        try:
            read(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        return path
    return None


def summary(path):
    """One line describing a snapshot, or None when it cannot be read.

    None is the honest-eligibility half (CLAUDE.md error class 5): a corrupt
    file, or one from a newer format, greys the Resume entry out instead of
    being offered and then failing on the click. That is why this swallows
    the error rather than letting the menu wrap every press in a try."""
    try:
        data = read(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    turn = data.get("turn") or {}
    parts = [str(data.get("map") or "?")]
    if turn.get("battle_round") is not None:
        parts.append(f"battle round {turn['battle_round']}")
    if turn.get("turn_owner"):
        parts.append(str(turn["turn_owner"]))
    try:
        stamp = time.strftime("%d %b %H:%M", time.localtime(os.path.getmtime(path)))
        parts.append(stamp)
    except OSError:
        pass
    return "   -   ".join(parts)


def restore(data, state, squads=None, evict_missing=True):
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

    missing = [name for name in by_name if name not in wanted]
    for name in missing:
        problems.append(f"the scene has {name!r}, the snapshot does not "
                        "- destroyed before the save")
    # A unit the snapshot does not mention was WIPED OUT before it was taken:
    # capture() walks the same three lists GameState.all_squads() does, and a
    # squad with no models is in none of them. Reporting that and leaving the
    # rebuilt squad alone is not enough - on the legacy already-deployed path
    # (--no-deployment) register_unit() has already put it on the board, so it
    # comes back at FULL STRENGTH. Measured, and it is the one way a restore
    # can silently hand somebody an extra unit.
    #
    # Zero models is how this engine spells "destroyed" everywhere else, so
    # that is what eviction produces; the Tokens move to destroyed_models,
    # which is where the rest of the engine looks for a casualty's last
    # position (19.02/19.04, Reanimation Protocols, Vengeful Stars).
    #
    # NOT recorded as kills. Those deaths were scored in the battle this
    # snapshot came from, and their VP is restored with the rest of the
    # mission state - counting them again would pay for every casualty twice.
    #
    # The valve: if the snapshot matched NOTHING, it belongs to another roster
    # entirely, and evicting on that basis would quietly delete both armies.
    # Say so instead and change nothing.
    if evict_missing and len(by_name) > len(missing):
        for name in missing:
            _evict(by_name[name], state)
    elif missing:
        problems.append(
            f"the snapshot names none of this scene's {len(by_name)} units "
            "- wrong roster or wrong build; nothing was removed"
        )
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
        # Casualties are whatever the snapshot does not name - NOT the tail of
        # the built unit. See _match_models() for the failure that distinction
        # exists to stop.
        matched, casualties, unidentified = _match_models(models, squad.models)
        if unidentified:
            problems.append(
                f"{name!r}: {unidentified} model(s) in the snapshot name a "
                "datasheet line this unit does not have - matched by position "
                "instead"
            )
        squad.models = matched
        for model in casualties:
            _make_casualty(model, squad, state)
        for model, saved in zip(matched, models):
            model.x_in = saved["x_in"]
            model.y_in = saved["y_in"]
            if saved.get("wounds") is not None:
                # Clamped, because a snapshot written before models carried an
                # identity can only be matched by position - and that put a
                # 7-wound character's 5 remaining wounds onto a 3-wound
                # trooper, i.e. restored it ABOVE its own maximum and so
                # healthier than it went in. Nothing in this engine ever
                # stands above its profile (a Shield Drone raises both), so
                # the clamp cannot cost a legitimate value.
                maximum = getattr(getattr(model, "profile", None), "wounds", None)
                wounds = saved["wounds"]
                model.current_wounds = (wounds if maximum is None
                                        else min(wounds, maximum))
        squad.battle_shocked = entry.get("battle_shocked", False)

    _restore_placement(wanted, by_name, state, problems)
    return problems


def _evict(squad, state):
    """Take a unit off the board the way a casualty leaves it.

    Mirrors what GameState does when the last model of a squad dies: out of
    every list it could be in, models moved to destroyed_models (their
    coordinates are what several rules read a casualty's last position from),
    and models emptied - which is the test the whole engine uses for
    "destroyed"."""
    for model in list(squad.models):
        if model in state.tokens:
            state.tokens.remove(model)
    if squad in state.reserves:
        state.reserves.remove(squad)
    if squad in state.embarked_squads:
        state.embarked_squads.remove(squad)
    squad.embarked_in = None
    destroyed = getattr(squad, "destroyed_models", None)
    if destroyed is None:
        squad.destroyed_models = list(squad.models)
    else:
        destroyed.extend(m for m in squad.models if m not in destroyed)
    squad.models = []


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
