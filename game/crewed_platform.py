"""Guardian Defenders' datasheet ability "Crewed Platform": when the last crew
model in a unit is destroyed, that unit's remaining platform models are
destroyed too.

TWO FLAGS, NOT ONE
------------------
A platform is marked with UnitProfile.crewed_platform and its crew with
UnitProfile.platform_crew, rather than treating "every model that is not a
platform" as crew. The rule names the crew model specifically, and under rule
19.01 a unit can contain a model that is neither - an attached CHARACTER. With
a single flag, such a character would keep an abandoned platform alive; with
two, it correctly does not.

WHY IT RUNS INSIDE remove_dead_models()
---------------------------------------
That sweep is the one place this engine discovers deaths, and it is where the
rest of the death bookkeeping already lives (Squad.destroyed_models for rule
19.02/19.04 and for Painboy's Grot Orderly, main.py's blood splats, the
"No Mercy" secondary). Marking the orphaned platforms there - and letting the
same sweep remove them - means they die on the same frame and are counted
exactly like any other casualty. The alternative, killing them a frame later,
would show a platform standing alone for one frame and risk the two paths
disagreeing about what counts as destroyed.
"""


def is_platform(model):
    return bool(getattr(model.profile, "crewed_platform", False))


def is_crew(model):
    return bool(getattr(model.profile, "platform_crew", False))


def mark_orphaned_platforms(squads):
    """Set the platforms of any crewless unit to 0 wounds, and return them.

    Marks rather than removes: the caller's own sweep does the removal, so
    there is exactly one piece of code that takes a model off the board."""
    killed = []
    for squad in squads:
        if squad is None or not squad.models:
            continue
        platforms = [m for m in squad.models if is_platform(m) and not m.is_dead()]
        if not platforms:
            continue
        if any(is_crew(m) and not m.is_dead() for m in squad.models):
            continue
        for model in platforms:
            model.current_wounds = 0
            killed.append(model)
    return killed
