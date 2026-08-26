"""Describing a unit's actual equipment in words.

Exists because two units off the same datasheet are otherwise
indistinguishable in the UI. The pre-game's Declare Battle Formations step
(rule 03.01) is the sharp case: it asks "which transport should this unit ride
in", and with two Trukks on the table both buttons used to read "Embark in
Trukk" - there was no way to tell which one, nor what either was carrying
(user: "was ist wenn ich mehrere transporter habe? ... und was ist wenn meine
transporter unterschiedliche ausruestungen haben? wie erkenne ich das dann").

Derived from the models' ACTUAL weapons and Gear rather than from the wargear
options that were chosen, because build_squad() does not keep the choices - it
applies them and throws them away, so `model.weapons` is the only surviving
record. (Gear was worse still: it is a callback that mutates the token, so its
identity was gone entirely. Token.gear_names now records it, for this.)

Grouped by MODEL LINE, i.e. by profile name, which is what a datasheet's
ModelLine is named after - so a Boyz mob reads as its nine Boyz plus its Boss
Nob rather than as one flat pile of weapons. That grouping is the whole point:
the difference between two units is almost always in one model's loadout, and a
flat list buries it."""

from collections import Counter

from game.weapons import MELEE


def _live_models(squad):
    """Prefer living models, but fall back to all of them: a wiped-out unit
    still has to be describable (e.g. in a log line written after it died)."""
    alive = [m for m in squad.models if not m.is_dead()]
    return alive or list(squad.models)


def weapon_names(model):
    """This model's weapons, deduped with counts - "2x Big Shoota" rather than
    "Big Shoota, Big Shoota". Counts matter for identification, which is why
    this is not ai/observation.py's weapon summary: that one dedupes by label
    and drops the count, because it answers "what can this unit do" for
    matchup arithmetic rather than "which unit is this"."""
    # Counted per (name, type) and then collapsed to the highest count for
    # the name. A single weapon can print BOTH a ranged and a melee profile
    # under one name (The Twin Lance's Fusion eliminator and XV pulse pistol
    # do, and the printed datasheet lists each in both tables) - a model
    # carries both entries, but it is ONE weapon and must not read as "2x".
    # The max, not the sum: a model with two Fusion eliminators and their
    # two melee halves genuinely has 2, not 4.
    per_type = Counter((w.name, w.weapon_type) for w in model.weapons)
    counts = {}
    for (name, _type), n in per_type.items():
        counts[name] = max(counts.get(name, 0), n)
    ordered = list(dict.fromkeys(w.name for w in model.weapons))
    return [name if counts[name] == 1 else f"{counts[name]}x {name}" for name in ordered]


def _model_signature(model):
    """What makes two models of the same line interchangeable for display."""
    return (
        getattr(model.profile, "name", "?"),
        tuple(sorted(w.name for w in model.weapons)),
        tuple(sorted(getattr(model, "gear_names", ()) or ())),
    )


def line_groups(squad):
    """[(count, profile_name, [weapon/gear labels]), ...] - one entry per
    distinct model line + loadout combination, in the order the models appear
    (so the datasheet's own rank-and-file-then-leader order is preserved
    rather than sorted alphabetically)."""
    return model_line_groups(_live_models(squad))


def model_line_groups(models):
    """The same grouping for an arbitrary set of models.

    Extracted when the army selection screen became the second consumer (repo
    convention: extract at the SECOND consumer): a tile there describes one
    AttachedComponent - a unit's leader apart from its bodyguards - and a
    component is a list of models, not a Squad. Takes the models as given
    rather than filtering the dead itself, because the caller is the one that
    knows whether it is describing a live unit or a historical roster."""
    order = []
    seen = {}
    for model in models:
        signature = _model_signature(model)
        if signature not in seen:
            seen[signature] = [0, model]
            order.append(signature)
        seen[signature][0] += 1

    groups = []
    for signature in order:
        count, model = seen[signature]
        labels = weapon_names(model)
        gear = list(getattr(model, "gear_names", ()) or [])
        if gear:
            gear_counts = Counter(gear)
            labels += [name if n == 1 else f"{n}x {name}" for name, n in gear_counts.items()]
        groups.append((count, signature[0], labels))
    return groups


def loadout_lines(squad, include_counts=True):
    """One human-readable line per model line, e.g.

        9x Ork Boy: Slugga, Choppa
        Boss Nob: Slugga, Power Klaw

    A single-model unit drops the count entirely (a Trukk is not "1x Trukk")."""
    return _lines_from(line_groups(squad), include_counts)


def model_loadout_lines(models, include_counts=True):
    """The same lines for an arbitrary set of models - see
    model_line_groups() for why that set is not always a whole unit."""
    return _lines_from(model_line_groups(models), include_counts)


def _lines_from(groups, include_counts):
    lines = []
    for count, profile_name, labels in groups:
        prefix = f"{count}x {profile_name}" if include_counts and count > 1 else profile_name
        lines.append(f"{prefix}: {', '.join(labels)}" if labels else prefix)
    return lines


def loadout_summary(squad, separator=" | "):
    """The same information on one line, for places too narrow for a block
    (a card, a log line)."""
    return separator.join(loadout_lines(squad)) or "no weapons"


def ranged_names(squad):
    """Just the ranged weapon names, deduped with counts across the whole unit -
    enough to identify a TRANSPORT, whose loadout is a short list of guns and
    whose model lines are not interesting (it has one model)."""
    counts = Counter(
        w.name for m in _live_models(squad) for w in m.weapons
        if getattr(w, "weapon_type", None) != MELEE
    )
    return [name if n == 1 else f"{n}x {name}" for name, n in counts.items()]


def transport_description(transport_token):
    """"<unit name> - <its guns>", the label a player needs to tell two
    identically-named transports apart. The UNIT name ("2 Trukk 1"), not the
    profile name ("Trukk"): the profile name is shared by every copy, which is
    exactly the ambiguity this exists to remove."""
    squad = transport_token.squad
    name = squad.name if squad is not None else getattr(transport_token.profile, "name", "Transport")
    guns = ranged_names(squad) if squad is not None else []
    return f"{name} - {', '.join(guns)}" if guns else name
