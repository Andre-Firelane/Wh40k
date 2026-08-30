"""Mont'ka Enhancement: Strategic Conqueror (15 pts).

RULE (verbatim, rules/tau_empire/detachments/Mont'ka.md):
  T'AU EMPIRE model only. At the start of the first battle round, before the
  first turn begins, select one objective marker on the battlefield. While a
  friendly T'AU EMPIRE model is within range of that objective marker and the
  bearer is on the battlefield, add 1 to that friendly model's Objective
  Control characteristic.

THE MARK LIVES ON THE OBJECTIVE, NOT IN A CONTROLLER
------------------------------------------------------
Every other mark in this engine is held per player in a controller, because it
belongs to the marked unit's OPPONENT and has to be reset on a phase or turn
boundary. This one is neither: it is chosen once, before the first turn, and
lasts the whole battle.

More importantly, it is READ from inside Objective.level_of_control(), which
has no controller in scope and never will - it is called from
update_control(), which main.py runs for every objective at every phase and
turn boundary. Threading a controller down to it would mean a new argument on
a method with several callers, for one Enhancement.

So the choice is stored the same way rule 14.03's Secured status already is: an
attribute on the Objective itself (`strategic_conqueror_player`), set once by
the pre-battle step. The Objective is exactly the thing the rule names.

WHERE THE BONUS LANDS
---------------------
game/objective_control.py's effective_oc(), the sixteenth extraction and the
one place that answers "what is this model's OC right now". Not at
level_of_control()'s own summation: that would be a second source of OC outside
the fold, which is the drift objective_control.py exists to prevent. effective_oc()
grows an optional `objective` argument instead - absent for every caller that
is not asking about a particular objective, which keeps them all meaning
exactly what they did.

ORDER AMONG THE OC SOURCES. Hunting Hounds SETS the characteristic, Scabrous
Soulrot WORSENS it, and this ADDS to it. It is applied LAST, after both, so:
  * a Hound set to 1 and then given this becomes 2 - the set is a floor the
    Enhancement builds on, not a value that overwrites it;
  * Soulrot's "to a minimum of 1" is applied to the printed characteristic and
    this bonus lands on top, so an Afflicted T'au model on the Conqueror
    objective is 1 + 1 rather than being clamped away.
Both orderings are legal readings of three rules that never mention each other;
this one is chosen because it is the only one in which paying 15 points always
buys the +1, and it is written down rather than left to be inferred.

"AND THE BEARER IS ON THE BATTLEFIELD" is a live condition, not a one-time one:
a bearer that walks into Strategic Reserves, boards a TRANSPORT (18.02) or dies
switches the whole bonus off. Checked against the token list, which is this
engine's own definition of "on the battlefield" (GameState.add_reserve_squad's
docstring).

"THAT FRIENDLY MODEL" is any T'AU EMPIRE model of the bearer's army, not the
bearer's own unit - so a Strike Team sitting on the chosen objective gets it
while the Commander who paid for it stands somewhere else entirely.
"""

from game import enhancements

STRATEGIC_CONQUEROR = "Strategic Conqueror"
STRATEGIC_CONQUEROR_OC_BONUS = 1
MARK_ATTR = "strategic_conqueror_player"


def chosen_objective(objectives, player):
    """The objective this player's bearer named, or None."""
    for objective in objectives or ():
        if getattr(objective, MARK_ATTR, None) == player:
            return objective
    return None


def choose(objective, player, game_log=None):
    """The "at the start of the first battle round" selection.

    One objective per player: choosing again moves the mark rather than adding
    a second, because the printed text is "select ONE objective marker"."""
    if objective is None or player is None:
        return False
    setattr(objective, MARK_ATTR, player)
    if game_log is not None:
        game_log.add(f"{player}: {STRATEGIC_CONQUEROR} names {objective.name} "
                     f"(+{STRATEGIC_CONQUEROR_OC_BONUS} OC to friendly T'AU EMPIRE models "
                     f"in range of it).")
    return True


def clear(objectives, player=None):
    """Forget the mark - for a new battle, and for the test that has to build
    two of them on the same Objective objects."""
    for objective in objectives or ():
        if player is None or getattr(objective, MARK_ATTR, None) == player:
            if hasattr(objective, MARK_ATTR):
                delattr(objective, MARK_ATTR)


def offer(squads, objectives, decision_manager=None, game_log=None, auto_players=()):
    """The "at the start of the first battle round, before the first turn
    begins" selection, for every player with a bearer.

    Called from main.py's begin_battle(), which is that instant - the same one
    Kroot Farstalkers' Bounty Hunters already uses, and the first moment both
    armies are fully on the table.

    NOT optional: the printed text says "select one objective marker", with no
    "you can", so a player with a bearer always names one and the only question
    is which. An owner in `auto_players` takes the objective its own army has
    the most Objective Control on right now - the one this +1 is most likely to
    actually decide - with ties broken by name so a self-play run is
    reproducible. That is a rule answering its own prompt, not an AI path.
    """
    players = []
    for squad in squads or ():
        owner = getattr(squad, "owner", None)
        if owner is not None and owner not in players and is_active(squad):
            players.append(owner)
    asked = False
    for player in players:
        candidates = [o for o in objectives or ()]
        if not candidates:
            continue
        if player in auto_players or decision_manager is None:
            choose(_auto_pick(candidates, player, squads), player, game_log=game_log)
            asked = True
            continue
        decision_manager.request(
            player,
            f"{STRATEGIC_CONQUEROR}: which objective marker?",
            [(f"{STRATEGIC_CONQUEROR}: {o.name}",
              (lambda objective=o, p=player: choose(objective, p, game_log=game_log)))
             for o in candidates])
        asked = True
    return asked


def is_active(squad):
    """A living bearer, with Mont'ka checked."""
    return enhancements.is_active(squad, STRATEGIC_CONQUEROR)


def _auto_pick(objectives, player, squads):
    def held(objective):
        area = getattr(objective, "terrain_area", None)
        if area is None:
            return 0
        return sum(1 for s in squads or () if s.owner == player
                   for m in s.models if not m.is_dead() and area.overlaps_model(m))
    return sorted(objectives, key=lambda o: (-held(o), o.name))[0]


def bearer_on_battlefield(player, all_tokens):
    """"while ... the bearer is on the battlefield".

    A model in game_state.tokens is on the battlefield; one in Strategic
    Reserves or embarked in a TRANSPORT is not, because neither is in that
    list. That is this engine's own convention, not a new one."""
    flag = enhancements.get(STRATEGIC_CONQUEROR).flag
    for token in all_tokens or ():
        if token.is_dead() or token.profile is None:
            continue
        squad = getattr(token, "squad", None)
        if squad is None or squad.owner != player:
            continue
        if getattr(token.profile, flag, False):
            # The detachment gate, asked once the bearer is actually found.
            return enhancements.player_has_detachment(
                player, enhancements.get(STRATEGIC_CONQUEROR).setting)
    return False


def oc_bonus(model, objective, all_tokens=None):
    """+1 while all three printed conditions hold, else 0.

    Returns a NUMBER because that is what game/objective_control.py's fold
    deals in."""
    if model is None or objective is None:
        return 0
    squad = getattr(model, "squad", None)
    if squad is None:
        return 0
    if getattr(objective, MARK_ATTR, None) != squad.owner:
        return 0
    # "a friendly T'AU EMPIRE model" - answered at the unit level, because this
    # engine has no per-model faction keyword (the documented gap
    # game/retaliation_cadre.py's Bonded Heroes note records).
    from game import tau_detachments
    if not tau_detachments.is_tau_unit(squad):
        return 0
    # "within range of that objective marker" - the same overlap test rule
    # 14.02's own level_of_control() uses to decide who is counted at all, so
    # the bonus can never apply to a model that is not being counted.
    area = getattr(objective, "terrain_area", None)
    if area is None or not area.overlaps_model(model):
        return 0
    if not bearer_on_battlefield(squad.owner, all_tokens):
        return 0
    return STRATEGIC_CONQUEROR_OC_BONUS
