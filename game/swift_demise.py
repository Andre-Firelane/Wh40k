"""Windriders' "Swift Demise".

RULE (printed, word for word):
  "Each time a model in this unit makes a ranged attack, re-roll a Hit roll of
   1. If the target of that attack is the closest eligible target, you can
   re-roll the Hit roll instead."

TWO ENTITLEMENTS, AND THEY ARE MUTUALLY EXCLUSIVE. That is the whole shape of
this ability, and "instead" is the word that decides it:

  * against ANY target: re-roll the 1s. Not optional ("re-roll", not "you
    can"), so it is automatic - the same treatment, and literally the same
    dice step, that Forward Observers' identical clause already gets (see
    ShootingController._begin_ones_reroll()).
  * against the CLOSEST ELIGIBLE TARGET: "you can re-roll the Hit roll
    INSTEAD" - the whole roll, optional, and IN PLACE OF the 1s rather than on
    top of them.

So against the closest target the automatic throw is held back and the player
picks one of the two; against anything else the 1s simply go. Doing the 1s
first and then offering the rest would be strictly more generous than the
printed text, which is why the shooting step gates the automatic path rather
than chaining the two.

"CLOSEST ELIGIBLE TARGET" is rule 10.02's own term - "eligible" is what the
targeting step already answers (in range, visible, not engaged, ...), so this
module does not re-derive it: the caller passes the units that were actually
eligible for this shot, and the closest is measured edge to edge with
Squad.min_distance_to(), the same measurement rules 11.02/11.04 use. Ties count
as closest, since "the closest" cannot single one of two equals out.
"""

SWIFT_DEMISE_LABEL = "Swift Demise"


def applies(squad):
    """Whether this unit has the ability at all. Per rule 19.03 a merged unit
    (19.01) counts as having it if any component brought it, which is what
    reading it off the models gives for free."""
    if squad is None:
        return False
    return any(getattr(m.profile, "swift_demise", False)
               for m in squad.models if not m.is_dead())


def is_closest_target(squad, target_squad, candidates):
    """Whether `target_squad` is the closest of `candidates` to `squad`.

    `candidates` are the units that were eligible targets for this attack -
    supplied by the caller rather than recomputed here, so this stays a
    measurement and rule 10.02 keeps owning what "eligible" means. With no
    candidates to compare against, the target it was actually shot at is the
    closest by default."""
    if squad is None or target_squad is None:
        return False
    others = [c for c in candidates if c is not target_squad]
    if not others:
        return True
    gap = squad.min_distance_to(target_squad)
    return all(gap <= squad.min_distance_to(other) + 1e-9 for other in others)


def offers_full_reroll(squad, target_squad, candidates):
    """The optional half: the whole-roll re-roll, which is available only
    against the closest eligible target."""
    return applies(squad) and is_closest_target(squad, target_squad, candidates)
