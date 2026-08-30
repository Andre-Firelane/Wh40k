"""The DEATH GUARD army rule: "Nurgle's Gift (Aura)".

RULES (printed, word for word):

  Nurgle's Gift (Aura): "If your Army Faction is DEATH GUARD, while an enemy
  unit is within Contagion Range of one or more DEATH GUARD units from your
  army, it is Afflicted."

  Contagion Range: 3" during the 1st battle round, 6" during the 2nd, 9" from
  the 3rd onwards.

"ONE OR MORE DEATH GUARD UNITS", and the measurement here is per MODEL - which
is the same answer, because a unit is within X" of something exactly when one
of its models is. Measuring per model is what lets the aura be drawn as one
circle per base, and what makes an attached unit (19.01) with mixed base sizes
come out right without a special case.

  "During the Declare Battle Formations step, select one of the Plagues below.
  Until the end of the battle, while an enemy unit is Afflicted, subtract 1
  from the Toughness characteristic of models in that unit, and that unit has
  the effect of your chosen Plague."

This module owns the GEOMETRY and the -1 Toughness. The three Plagues - what
being Afflicted does BEYOND the Toughness penalty - live in game/plagues.py,
because they hang off five different calculation steps (save threshold, cover,
melee hit roll, Move, Leadership, Objective Control) and none of those is this
module's business.

AFFLICTED IS A FLAG ON THE SQUAD, REFRESHED ONCE PER FRAME - not a live
predicate asked at each use. Two independent reasons:

  * COST. attached_unit_toughness() (game/squad.py) has nine readers, and it
    is called once per weapon group per attack. Measuring an army-wide aura
    inside it would re-derive the same geometry dozens of times a frame, and
    would have to grow an all_tokens parameter at all nine call sites.
  * CORRECTNESS. "Afflicted" has TWO sources, and only one of them is
    geometric. The Death Lord's Chosen stratagem Signal Pox sets a unit
    Afflicted "until the start of your next turn" through an objective marker,
    with no DEATH GUARD model anywhere near it. A live distance test could
    never see that; a flag is the union of both.

This is the same arrangement game/status_effects.py's targeting_range_limit()
documents for Squad.psychic_shield_range / ard_as_nails_active /
stim_injectors_active: the effect is read off the unit, so a reader needs one
call and no new dependency, and a third source later needs no third site.

WHY THIS MODULE IMPORTS NOTHING FROM game/: game/squad.py has to depend on it
for the Toughness penalty, so it must not depend on game/squad.py. The
model-to-unit distance is therefore written out here, exactly as
game/mortal_wound_abilities.py's _gap() writes out the same measurement for
the same reason.

THE 12" CEILING IS INERT WITH THESE NUMBERS, and is kept anyway. The printed
progression tops out at 9", and the only modifier in the game adds 3" (Blooming
Pestilence), so the largest reachable range is exactly 12" - the ceiling never
actually clamps anything today. It stays because a second modifier would make
it bite, and because it is cheaper to keep a bound that is already right than
to add one later under pressure. NOTE it is not in the user-supplied card text;
it came from the same summarised source as the wrong table below, so treat it
as unconfirmed rather than printed.

RECORDED BECAUSE THE TABLE WAS GOT WRONG ONCE: these values were first built as
6"/9"/12", from a source that could not read them at all - Wahapedia prints the
progression as three IMAGES, and asked precisely, a text fetch returns the
filenames and no numbers. The summariser had inferred them. With those values
the ceiling would have applied from round 3 with no modifier, making Blooming
Pestilence provably worthless from round 3 on - a tempting "sharp decision
boundary" that was an artefact of the wrong table. The values here are the
user's, from the printed card.
"""

# Printed Contagion Range per battle round. Rounds 3+ are the default rather
# than three more table rows: the printed diagrams show one value from round 3
# on, and a game that somehow reaches round 6 should not fall off the table.
CONTAGION_RANGE_BY_ROUND = {1: 3.0, 2: 6.0}
CONTAGION_RANGE_DEFAULT_IN = 9.0
#: "Contagion Range cannot be greater than 12" AFTER modifiers" - unreachable
#: from the table above, so this only ever bounds a MODIFIER; see the docstring.
CONTAGION_RANGE_CAP_IN = 12.0

TOUGHNESS_PENALTY = 1
MINIMUM_TOUGHNESS = 1  # a characteristic cannot be reduced below 1


def contagion_range_in(battle_round, bonus_in=0.0):
    """How far this army's Contagion Range reaches during `battle_round`.

    `bonus_in` is any modifier a rule adds (today only Blooming Pestilence's
    3"), and the ceiling is applied AFTER it. With the printed table the two
    never meet short of 12", so the ceiling changes no result today - see the
    module docstring."""
    if battle_round is None:
        battle_round = 1
    base = CONTAGION_RANGE_BY_ROUND.get(int(battle_round), CONTAGION_RANGE_DEFAULT_IN)
    return min(CONTAGION_RANGE_CAP_IN, base + (bonus_in or 0.0))


def has_nurgles_gift(squad):
    """Whether this unit carries the army rule at all.

    Read live off SURVIVING models, like reanimation_protocols.py's own
    predicate: an attached unit (19.01) merges its components, so the answer
    has to come from whoever is still standing rather than from the
    datasheet."""
    if squad is None:
        return False
    return any(getattr(m.profile, "nurgles_gift", False) and not m.is_dead()
               for m in getattr(squad, "models", ()) or ())


def qualifying_players(squads):
    """Which players actually field Death Guard, derived from the units on the
    table rather than from a config setting.

    Same choice game/waaagh.py's and game/battle_focus.py's own
    qualifying_players() make, for the same reason: an ARMY rule is a property
    of the army, so the units are the honest source, and a mirror match needs
    no special case. (A DETACHMENT rule is the opposite - it is a list-building
    statement not derivable from the board, which is why Deadly Vectors reads
    a config tuple instead.)"""
    return sorted({s.owner for s in squads or () if has_nurgles_gift(s)})


def is_afflicted(squad):
    """Whether this unit is currently Afflicted.

    Reads the flag NurglesGiftController.refresh() maintains. A squad that has
    never been through a refresh reads False, which is the right degradation:
    no Death Guard on the table means nothing is Afflicted."""
    return bool(getattr(squad, "afflicted", False))


def toughness_penalty(squad):
    """The Toughness reduction Nurgle's Gift imposes on this unit right now:
    1 while Afflicted, 0 otherwise.

    Kept as its own function rather than inlined into
    game/squad.py's attached_unit_toughness() so the number and the condition
    stay in the module that owns the rule."""
    return TOUGHNESS_PENALTY if is_afflicted(squad) else 0


def _gap(model, other_squad):
    """Edge-to-edge distance from one MODEL to the nearest living model of a
    unit. Written out rather than imported for the reason in the module
    docstring; identical to game/mortal_wound_abilities.py's own _gap()."""
    live = [t for t in getattr(other_squad, "models", ()) or () if not t.is_dead()]
    if not live:
        return float("inf")
    return min(((t.x_in - model.x_in) ** 2 + (t.y_in - model.y_in) ** 2) ** 0.5
               - t.radius_in - model.radius_in for t in live)


def _bounds(squad):
    """The axis-aligned box enclosing this unit's living BASES, or None if it
    has none left. Base radii are folded in, so the box is what the models
    actually occupy rather than where their centres are."""
    live = [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]
    if not live:
        return None
    return (min(m.x_in - m.radius_in for m in live),
            min(m.y_in - m.radius_in for m in live),
            max(m.x_in + m.radius_in for m in live),
            max(m.y_in + m.radius_in for m in live))


def _box_gap(a, b):
    """Shortest distance between two axis-aligned boxes, 0 if they overlap.

    A LOWER BOUND on the true edge-to-edge distance between any model of one
    unit and any model of the other, which is what makes it safe as a reject:
    it can never claim a separation the models do not really have, so a pair it
    rejects genuinely has no model within reach."""
    dx = max(0.0, a[0] - b[2], b[0] - a[2])
    dy = max(0.0, a[1] - b[3], b[1] - a[3])
    return (dx * dx + dy * dy) ** 0.5


class NurglesGiftController:
    """Maintains Squad.afflicted for every unit on the battlefield.

    Fed once per frame from main.py, next to GameState.remove_dead_models() -
    positions change between frames, so the aura genuinely has to be
    re-derived that often, and the alternative (re-deriving it per attack) is
    strictly more work.
    """

    def __init__(self, turn_tracker=None, game_log=None, plague_choice=None):
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        # game/plagues.py's PlagueChoice, or None. Held rather than imported:
        # plagues.py has to be importable by game/objectives.py,
        # game/leadership.py and game/coldstar.py, and this module has to be
        # importable by game/squad.py, so an import either way round is a
        # cycle waiting to happen. Duck-typed on plague_against(squad).
        self.plague_choice = plague_choice
        # id(squad) -> the player whose next turn ends the marking. The
        # "sticky" half of Afflicted: Plague Marines' own ability and the
        # Signal Pox stratagem both read "until the start of your next turn".
        self._sticky = {}
        # Per-unit Contagion Range bonuses in inches, keyed by id(squad), for
        # Blooming Pestilence. Cleared by expire_phase().
        self._range_bonus = {}
        self._reported = set()  # id(squad) already logged as newly Afflicted

    # --- the geometric half ----------------------------------------------

    def battle_round(self):
        return getattr(self.turn_tracker, "battle_round", 1) or 1

    def range_bonus_in(self, squad):
        return self._range_bonus.get(id(squad), 0.0)

    def add_range_bonus(self, squad, bonus_in):
        """Blooming Pestilence: "add 3" to the Contagion Range of models in
        your unit". Additive so two sources could stack; the 12" cap in
        contagion_range_in() is what actually bounds it."""
        self._range_bonus[id(squad)] = self.range_bonus_in(squad) + float(bonus_in)

    def reach_of(self, squad):
        """This unit's Contagion Range right now, bonus and cap included."""
        return contagion_range_in(self.battle_round(), self.range_bonus_in(squad))

    # --- the sticky half --------------------------------------------------

    def mark_afflicted(self, squad, until_turn_of):
        """"Until the start of your next turn, that enemy unit is Afflicted."

        `until_turn_of` is the player whose next turn ends it - i.e. the
        Death Guard player who applied it, not the unit's owner."""
        if squad is None:
            return
        self._sticky[id(squad)] = until_turn_of

    def is_marked(self, squad):
        return squad is not None and id(squad) in self._sticky

    def expire_marks_for(self, player):
        """Called at the START of `player`'s turn: everything they marked
        stops being marked. Returns the ids cleared, for tests and logging."""
        cleared = [key for key, owner in self._sticky.items() if owner == player]
        for key in cleared:
            del self._sticky[key]
        return cleared

    # --- the per-frame refresh -------------------------------------------

    def refresh(self, all_tokens):
        """Recompute Squad.afflicted for every unit represented in
        `all_tokens`. Returns the set of squads that are Afflicted, for tests
        and callers that want to report it.

        A unit is Afflicted if EITHER an enemy Death Guard model is within
        that model's Contagion Range, OR something marked it stickily. Both
        halves are checked for every unit on the board, so the flag on a
        Death Guard unit's own enemy is correct no matter which player is
        playing the faction - and a mirror match works with no extra code.

        Squad.afflicted_plague is stamped in the SAME pass, for the reason
        game/plagues.py's docstring gives: it is what lets all six Plague
        funnels read the unit instead of growing a parameter."""
        squads = []
        seen = set()
        for token in all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is None or id(squad) in seen:
                continue
            seen.add(id(squad))
            squads.append(squad)

        # (squad, reach, bounding box) per carrier, computed once per refresh
        # rather than once per (carrier, target) pair. See _is_afflicted_now()
        # for why the box matters.
        carriers = []
        for squad in squads:
            if not has_nurgles_gift(squad):
                continue
            box = _bounds(squad)
            if box is None:
                continue  # every model dead - projects nothing
            carriers.append((squad, self.reach_of(squad), box))

        afflicted = set()
        for squad in squads:
            if self._is_afflicted_now(squad, carriers):
                afflicted.add(squad)
            was = bool(getattr(squad, "afflicted", False))
            squad.afflicted = squad in afflicted
            squad.afflicted_plague = self._plague_against(squad)
            self._report(squad, was)
        return afflicted

    def _plague_against(self, squad):
        if self.plague_choice is None:
            return None
        return self.plague_choice.plague_against(squad)

    def _is_afflicted_now(self, squad, carriers):
        if self.is_marked(squad):
            return True
        if not any(not m.is_dead() for m in getattr(squad, "models", ()) or ()):
            # A wiped unit is not Afflicted. The liveness test is
            # any(not is_dead()) and not `not squad.models`, because
            # remove_dead_models() runs once a frame and this refresh can see
            # corpses still in squad.models (the recurring ordering trap).
            return False
        box = _bounds(squad)
        if box is None:
            return False
        for carrier, reach, carrier_box in carriers:
            if carrier.owner == squad.owner:
                continue  # "an ENEMY unit"
            # Cheap conservative reject before the exact per-model measurement.
            # Two units whose bounding boxes are further apart than the reach
            # cannot possibly have a model pair within it, and on a real board
            # most pairs are exactly that. Measured on a 192-model board (16
            # Death Guard units against 14 enemy ones, i.e. the heaviest
            # realistic matchup): 3.56 ms per frame without this, 0.36 ms with
            # it, and 0.28 ms in the pathological case where every model is
            # piled into one blob and the reject never fires at all. That
            # matters because this runs once per frame, next to
            # GameState.remove_dead_models().
            if _box_gap(box, carrier_box) > reach:
                continue
            for model in carrier.models:
                if model.is_dead():
                    continue
                if _gap(model, squad) <= reach:
                    return True
        return False

    def _report(self, squad, was_afflicted):
        """One log line the first time a unit becomes Afflicted in a battle
        round, and one when it stops. Debounced through _reported so a unit
        standing in the aura does not print a line every frame - the same
        problem game/coherency's own logging solved the same way."""
        if self.game_log is None:
            return
        key = id(squad)
        now = bool(getattr(squad, "afflicted", False))
        if now and key not in self._reported:
            self._reported.add(key)
            self.game_log.add(
                f"[contagion] {squad.name} is Afflicted "
                f"(Contagion Range {contagion_range_in(self.battle_round()):g}\", "
                f"battle round {self.battle_round()}).",
                file_only=True,
            )
        elif not now and key in self._reported:
            self._reported.discard(key)
            self.game_log.add(f"[contagion] {squad.name} is no longer Afflicted.",
                              file_only=True)

    # --- lifetimes --------------------------------------------------------

    def expire_phase(self):
        """Blooming Pestilence is "until the end of the phase"; the sticky
        marks are NOT (they run to the start of a turn), so only the range
        bonuses are cleared here. Two clocks, cleared in two places, named
        after their lifetimes - the same care game/protocol_sudden_storm.py
        takes with its own pair."""
        self._range_bonus.clear()
