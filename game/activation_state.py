"""What a unit has ALREADY DONE this turn, as plain data for a snapshot.

WHY THIS EXISTS. game/scene_io.py records where every model stands and how
hurt it is. It never recorded what anybody had already done - so a save taken
in the middle of a turn came back with every unit's activation refunded: units
that had shot could shoot again, units that had moved could move again, a
Charge already declared was forgotten, and a stratagem paid for "until the end
of the turn" was simply gone. Reported as "es wurde nicht gespeichert, wer
schon welche Aktion ausgefuehrt hat. zb wer schon geschossen hat und wer
nicht".

The per-round AUTOSAVE never showed it, and that is not luck: it is written at
a battle-round boundary, which is by construction the one moment every ledger
below is empty. F9 and the menu's Save Game are not, and those are the two a
player actually presses mid-turn.

WHY ONE MODULE RATHER THAN A save_state() ON EACH CONTROLLER. That is the
shape the MISSION controllers use, and it is right for them: each carries a
different and complicated kind of state, and "what here is scoped to one turn"
is genuinely a fact about that controller's own rules. Here it is ONE question
with eight identical answers - every ledger below is a set of units or a dict
keyed by unit. The thing that will actually go wrong is a NINTH ledger being
added and nobody remembering this file, and a declarative table plus a source
guard (test_scene_activation.py) catches that, where eight scattered methods
cannot.

WHAT IS DELIBERATELY NOT HERE - and it is one rule, not a list of excuses:
a snapshot restores a SETTLED board, never a half-finished activation. A move
with models part-way through their budget, a shooting sequence with a target
picked and dice on the table, an open damage allocation - none of that is
captured and none of it ever was, so nothing here tries to put it back either.
The named casualties of that rule are Squad.nova_charge_grants (keyed by
model.id and weapon instance id, neither of which survives a rebuild),
Squad.attached_ability_grace (rule 19.04's window, open only inside an attack
sequence), ShootingController.fired_weapon_types (which weapon groups of a
unit MID-ACTIVATION have already fired) and ActionController.states (rule
16.01, whose entries hold live callbacks). A save taken mid-activation
restores that unit as though its activation had not begun.
"""

# --- the shapes a ledger comes in ------------------------------------------
SQUADS = "squads"        # set of Squad
BY_SQUAD = "by_squad"    # {Squad: JSON scalar}
SQUAD_MAP = "squad_map"  # {Squad: Squad}
ONE_SHOT = "one_shot"    # set of (model.id, id(weapon)) - rule 24.26

# Every "this unit has already acted" ledger, by the slot main.py's
# _activation_slots() files its controller under. A controller that is not
# passed in is simply skipped, so a harness may hand over as few as it likes.
LEDGERS = {
    "movement": (
        # Rules 09.02/09.06/10.04-10.07. The last two are not "did it move"
        # but "how far" and "with which Advance roll" - read by [HEAVY]
        # (24.16) and by rule 09.06's "the Advance roll is final for the
        # phase", so losing them re-rolls an Advance a player already made.
        ("moved_squad_ids", SQUADS),
        ("stationary_squad_ids", SQUADS),
        ("advanced_squad_ids", SQUADS),
        ("moved_distance_this_turn", BY_SQUAD),
        ("advance_bonus_by_squad", BY_SQUAD),
    ),
    "shooting": (
        ("shot_squad_ids", SQUADS),
        # Rule 13.09: the turn a unit last fired is what ends Hidden, and it
        # is scoped to the whole BATTLE, not to the phase.
        ("last_ranged_attack_turn", BY_SQUAD),
        ("one_shot_used", ONE_SHOT),
    ),
    "charge": (("charged_squad_ids", SQUADS),),
    "fight": (
        ("fought_squad_ids", SQUADS),
        # The Fight step's own state (whose turn, which sub-step) is NOT here:
        # begin_fight_step() recomputes it from the board, and it only skips
        # units that are in fought_squad_ids - which is restored, so the step
        # resumes with the right units left to fight.
        ("one_shot_used", ONE_SHOT),
    ),
    "pile_in": (("piled_in_squad_ids", SQUADS),),
    "consolidate": (("consolidated_squad_ids", SQUADS),),
    "battle_shock": (("rolled_squad_ids", SQUADS),),
    "greater_good": (
        ("observer_squad_ids", SQUADS),
        ("spotted_by", SQUAD_MAP),
    ),
}

# --- the flags that live on the unit itself --------------------------------
# Squad fields recording something the unit has already done, had done to it,
# or paid for. Every one is a plain scalar, so they go straight into the file.
SQUAD_FLAGS = (
    # rules 11.04 / 09.07 / 18.02 / 20.04 - these GATE what the unit may still
    # do this turn, so losing them hands back an action the rules took away
    "charged_this_turn",
    "fell_back_this_turn",
    "set_up_this_turn",
    "ingress_locked",
    "charge_locked_until_end_of_turn",
    "explosives_locked_until_end_of_turn",
    "fights_first",
    # bought and paid for - a CP or a Battle Focus token was spent on each of
    # these, and a mid-turn save that drops them charges the player twice
    "stim_injectors_active",
    "arrokon_protocol_active",
    "ere_we_go_active",
    "ard_as_nails_active",
    "swift_as_the_wind_active",
    "star_engines_active",
    "flitting_shadows_active",
    "sudden_strike_active",
    "neocapacitor_shielded",
    "spirit_of_gork_strength",
    "spirit_of_gork_lethal",
    "ammo_runt_active",
    "unbridled_carnage_active",
    "flickerjump_active",
    # battle-scoped spend: once per battle each, so this only ever grows
    "aspect_shrine_tokens_used",
)

# Squad fields deliberately left out, each with the reason. Kept as data so
# the source guard can insist that EVERY field Squad.__init__ assigns is in
# one list or the other - a new flag then cannot appear without moving a line
# here, which is the only way this file stays complete.
SQUAD_FLAGS_EXCLUDED = {
    "name": "identity - the snapshot is keyed by it",
    "models": "restored by scene_io.restore() itself",
    "owner": "roster",
    "points": "roster",
    "datasheet": "roster",
    "attached_components": "roster (rule 19.01 provenance, rebuilt with the unit)",
    "starting_model_count": "roster (rule 19.01 re-derives it)",
    "aspect_shrine_tokens": "roster - build_squad() sets it from starting strength",
    "embarked_in": "restored by scene_io's placement pass (rule 18.02)",
    "destroyed_models": "restored by scene_io's casualty pass",
    "absorbed_into": "roster (a leader Squad attach() merged away)",
    "battle_shocked": "already in the snapshot's per-squad entry",
    "afflicted": "re-stamped every frame by NurglesGiftController.refresh()",
    "afflicted_plague": "re-stamped every frame by NurglesGiftController.refresh()",
    "nova_charge_grants": "keyed by model.id and weapon instance id - neither survives a rebuild",
    "attached_ability_grace": "rule 19.04's window, open only inside an attack sequence",
    # A Token, not a scalar, so it is captured by name below rather than
    # through SQUAD_FLAGS.
    "disembarked_from_this_turn": "a Token - saved as its transport's unit name instead",
}


def _name(thing):
    return getattr(thing, "name", None)


def _one_shot_entries(used, squads):
    """Rule 24.26's fired-once pairs as [unit name, model index, weapon name].

    (model.id, id(weapon)) is meaningless the moment the armies are rebuilt,
    so the model is named by WHERE IT STANDS in its unit - the same order
    scene_io.restore() puts back - and the weapon by its printed name.

    Only models still alive are recorded: a one-shot weapon on a dead model
    can never be fired again anyway, and a casualty has no index to name."""
    index_of, weapon_name = {}, {}
    for squad in squads:
        for index, model in enumerate(squad.models):
            index_of[model.id] = (squad.name, index)
            for weapon in getattr(model, "weapons", None) or ():
                weapon_name[id(weapon)] = getattr(weapon, "name", None)
    out = []
    for model_id, weapon_id in used or ():
        where = index_of.get(model_id)
        name = weapon_name.get(weapon_id)
        if where is not None and name is not None:
            out.append([where[0], where[1], name])
    return sorted(out)


def _one_shot_restore(entries, by_name):
    used = set()
    problems = []
    for entry in entries or ():
        try:
            unit_name, index, weapon_name = entry
        except (TypeError, ValueError):
            problems.append(f"the snapshot's one-shot record {entry!r} is malformed")
            continue
        squad = by_name.get(unit_name)
        if squad is None or index >= len(squad.models):
            problems.append(
                f"the snapshot says {unit_name!r}'s model {index} already fired "
                f"its {weapon_name!r}, but that model is not in this scene")
            continue
        model = squad.models[index]
        for weapon in getattr(model, "weapons", None) or ():
            if getattr(weapon, "name", None) == weapon_name:
                used.add((model.id, id(weapon)))
                break
        else:
            problems.append(
                f"the snapshot says {unit_name!r}'s model {index} already fired "
                f"a {weapon_name!r}, which it is not carrying")
    return used, problems


def capture(squads, controllers=None):
    """Everything above, as a plain dict. `controllers` is {slot: controller}."""
    squads = list(squads)
    flags = {}
    for squad in squads:
        entry = {field: getattr(squad, field)
                 for field in SQUAD_FLAGS
                 if getattr(squad, field, None)}
        transport = getattr(squad, "disembarked_from_this_turn", None)
        if transport is not None:
            entry["disembarked_from"] = _name(getattr(transport, "squad", None))
        if entry:
            # Only what is actually set. An untouched unit contributes nothing,
            # which keeps a start-of-round autosave the size it always was.
            flags[squad.name] = entry

    ledgers = {}
    for slot, fields in LEDGERS.items():
        controller = (controllers or {}).get(slot)
        if controller is None:
            continue
        saved = {}
        for field, kind in fields:
            value = getattr(controller, field, None)
            if not value:
                continue
            if kind == SQUADS:
                saved[field] = sorted(_name(s) for s in value if _name(s))
            elif kind == BY_SQUAD:
                saved[field] = {_name(s): v for s, v in value.items() if _name(s)}
            elif kind == SQUAD_MAP:
                saved[field] = {_name(k): _name(v) for k, v in value.items()
                                if _name(k) and _name(v)}
            elif kind == ONE_SHOT:
                entries = _one_shot_entries(value, squads)
                if entries:
                    saved[field] = entries
        if saved:
            ledgers[slot] = saved

    out = {}
    if flags:
        out["squads"] = flags
    if ledgers:
        out["controllers"] = ledgers
    return out


def restore(data, squads, controllers=None):
    """Put it all back. Returns the same kind of complaint list scene_io does.

    MUST run after whatever begins the battle: main()'s begin_battle() clears
    set_up_this_turn on every unit it finds (so a deployed army may embark in
    round 1), and would wipe the flag straight back off again. Same ordering
    trap restore_turn() and restore_missions() carry."""
    problems = []
    data = data or {}
    by_name = {squad.name: squad for squad in squads}
    transports = {squad.name: squad.models[0] for squad in squads if squad.models}

    for name, entry in (data.get("squads") or {}).items():
        squad = by_name.get(name)
        if squad is None:
            problems.append(f"the snapshot has activation state for {name!r}, "
                            "which is not in this scene")
            continue
        for field in SQUAD_FLAGS:
            if field in entry:
                setattr(squad, field, entry[field])
        transport_name = entry.get("disembarked_from")
        if transport_name is not None:
            # The UNIT is named, not the model: which model of a transport a
            # unit came out of is recorded nowhere and no rule reads it -
            # game/fire_support.py only asks WHICH TRANSPORT. Same
            # approximation scene_io's placement pass makes for embarked_in.
            squad.disembarked_from_this_turn = transports.get(transport_name)
            if squad.disembarked_from_this_turn is None:
                problems.append(
                    f"{name!r} disembarked from {transport_name!r}, which is "
                    "not in this scene")

    for slot, fields in LEDGERS.items():
        controller = (controllers or {}).get(slot)
        saved = (data.get("controllers") or {}).get(slot)
        if controller is None or not saved:
            continue
        for field, kind in fields:
            if field not in saved:
                continue
            value = saved[field]
            missing = []
            if kind == SQUADS:
                setattr(controller, field,
                        {by_name[n] for n in value if n in by_name})
                missing = [n for n in value if n not in by_name]
            elif kind == BY_SQUAD:
                setattr(controller, field,
                        {by_name[n]: v for n, v in value.items() if n in by_name})
                missing = [n for n in value if n not in by_name]
            elif kind == SQUAD_MAP:
                setattr(controller, field,
                        {by_name[k]: by_name[v] for k, v in value.items()
                         if k in by_name and v in by_name})
                missing = [n for pair in value.items() for n in pair
                           if n not in by_name]
            elif kind == ONE_SHOT:
                used, complaints = _one_shot_restore(value, by_name)
                setattr(controller, field, used)
                problems.extend(complaints)
            for name in missing:
                problems.append(f"the snapshot's {slot}.{field} names {name!r}, "
                                "which is not in this scene")
    return problems
