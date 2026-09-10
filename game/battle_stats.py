"""What every unit actually DID this battle - the numbers behind the
"Unit Statistics" overlay.

User: "Beim echten 40k macht man sich immer gedanken, wie jede einheit
performt hat als resumee." Nothing in this engine kept such a number before
this module: the only bookkeeping that existed was purpose-built and narrow
(MissionController.record_destroyed_squad() for VP, MovementController.
moved_distance_this_turn for rule 24.16's [HEAVY], overwritten every turn).

Three questions, and each is answered at a different seam:

  Best Killing   wounds this unit took OFF an enemy, plus what that is worth
                 in points
  Best Tanking   potential damage this unit turned aside
  Fastest        inches travelled, battle-long

KEYED BY squad.name, not by the Squad object. That is this repo's documented
identifier (game/army_roster.py's unit_name(): "the name is an IDENTIFIER,
not a label" - plan orders, partial rosters and saved scenes all address units
by it), it is unique by construction (owner digit + datasheet + copy number),
and it is the only key that survives the save/load rebuild - game/scene_io.py
and game/activation_state.py key on it for exactly that reason. A Squad object
would not: it hashes by identity and every --load builds new ones.

Rule 19.01: a unit merged into another by attach() has `absorbed_into` set and
its name stops being a thing on the table, so every recording resolves through
it. That merge happens in the pregame Declare Battle Formations step, before a
single wound is dealt, so today it never actually fires - it is here because
the alternative is a statistic quietly accruing to a squad nobody can see.

NOTHING HERE BLOCKS ANYTHING. This is a ledger, not a controller: no
is_busy, no pending_damage_choice, no on_dice_acknowledged. That keeps it out
of every gate in main.py and out of test_event_chain_wiring.py's SS 6/10/11/12/
17/20, all of which fire on those names. If a statistic ever needs to ask the
player something, it is the wrong statistic.
"""

from game import weapons

#: The battle's ledger, set once by main() and cleared when it ends.
#:
#: A MODULE attribute rather than a constructor argument threaded through the
#: engine, for exactly the reason MortalWoundAllocationSession.on_mortal_wounds
#: is one: the seams that report into it sit inside game/damage_resolution.py's
#: three sessions (25 call sites across 20 modules) and inside
#: game/feel_no_pain.py, and none of those should have to learn that statistics
#: exist. It lives HERE, next to the class it holds, so there is ONE answer to
#: "where do statistics go" rather than a copy of that question in every module
#: that reports - which is the drift this repo keeps consolidating away.
#:
#: None outside a real battle: every unit test and both non-interactive
#: resolve_* wrappers leave it alone and record nothing.
CURRENT = None


def report_damage(attacker_squad, model, amount):
    """`amount` wounds have just come off `model`. No-op without a ledger."""
    if CURRENT is not None:
        CURRENT.record_damage(attacker_squad, model, amount)


def report_prevented(model, amount):
    """`amount` damage was stopped after the attack had already got through -
    Feel No Pain, or a Damage-reducing ability. No-op without a ledger."""
    if CURRENT is not None:
        CURRENT.record_prevented(model, amount)


def report_group(group, weapon):
    """One weapon group has fully resolved. `group` is the attack controllers'
    own current_group dict, which carries the target and the two counts the
    tanking number is made of; `weapon` is the profile the DAMAGE used."""
    if CURRENT is None or group is None or weapon is None:
        return
    CURRENT.record_attack_group(group.get("target_squad"), weapon,
                                group.get("attacks", 0), group.get("landed", 0))


def report_move(squad, move_mode, distance_in):
    """A confirmed move of `distance_in` inches has just been committed."""
    if CURRENT is not None:
        CURRENT.notify_move(squad, move_mode, distance_in)


def _live_squad(squad):
    """The squad this one has become, following rule 19.01's merge."""
    seen = 0
    while squad is not None and getattr(squad, "absorbed_into", None) is not None:
        squad = squad.absorbed_into
        seen += 1
        if seen > 8:      # a cycle cannot happen; refusing to hang if one ever does
            break
    return squad


def starting_wounds(squad):
    """The wounds this unit had at full strength.

    `models` + `destroyed_models` is always the starting set: game/game_state.py's
    _remove_tokens() moves a casualty from the first list to the second, and the
    handful of abilities that bring a model back (game/model_return.py) move it
    the other way. Neither ever drops one, so the sum is stable all battle -
    which is what makes the points share below a fixed denominator rather than
    one that grows as the unit dies.

    Squad.starting_model_count is deliberately not used: it counts MODELS, and
    a unit's wounds are not its model count times anything once a Character is
    attached to it."""
    if squad is None:
        return 0
    total = 0
    for model in list(squad.models) + list(getattr(squad, "destroyed_models", ())):
        profile = getattr(model, "profile", None)
        if profile is not None:
            total += max(0, profile.wounds or 0)
    return total


class UnitRecord:
    """One unit's line in the resume."""

    __slots__ = ("name", "owner", "wounds_dealt", "points_dealt",
                 "prevented", "distance_in")

    def __init__(self, name, owner):
        self.name = name
        self.owner = owner
        self.wounds_dealt = 0          # wounds actually stripped off enemy models
        self.points_dealt = 0.0        # those wounds as a share of each target's points
        self.prevented = 0.0           # potential damage turned aside
        self.distance_in = 0.0         # inches travelled, every confirmed move

    def as_dict(self):
        return {"owner": self.owner, "wounds_dealt": self.wounds_dealt,
                "points_dealt": round(self.points_dealt, 3),
                "prevented": round(self.prevented, 3),
                "distance_in": round(self.distance_in, 3)}

    def load(self, data):
        self.wounds_dealt = int(data.get("wounds_dealt") or 0)
        self.points_dealt = float(data.get("points_dealt") or 0.0)
        self.prevented = float(data.get("prevented") or 0.0)
        self.distance_in = float(data.get("distance_in") or 0.0)


class BattleStats:
    """The battle-long ledger. One instance per battle, built in main()."""

    def __init__(self):
        self._records = {}             # squad name -> UnitRecord
        #: Wounds whose attacker could not be named - see record_damage().
        #: Reported by verify_unit_stats.py rather than hidden, because the
        #: size of this number is what decides whether stage two is worth it.
        self.unattributed_wounds = 0

    # ---------------------------------------------------------------- recording

    def _record_for(self, squad):
        squad = _live_squad(squad)
        if squad is None or not squad.name:
            return None
        record = self._records.get(squad.name)
        if record is None:
            record = self._records[squad.name] = UnitRecord(squad.name, squad.owner)
        return record

    def record_damage(self, attacker_squad, target_model, amount):
        """`amount` wounds have just come off `target_model`.

        Called from the three _finish_apply() methods in
        game/damage_resolution.py - the only places in the engine that reach
        Token.apply_damage(), which is itself the single funnel every wound
        goes through.

        `attacker_squad` may be None, and that is not an oversight: a
        MortalWoundAllocationSession is built at 22 sites across 21 modules and
        carries no attacker, so an ability's mortal wounds land here unnamed.
        They credit no killer and are counted in self.unattributed_wounds
        instead, which verify_unit_stats.py reports - the size of that number
        is what decides whether threading a source through all 21 is worth it,
        and doing it blind would be the "46 hand-edits, 46 chances to miss one"
        shape game/ui/unit_thumbs.py rejected by name.

        Note this only ever costs the KILLING table. Tanking does not read
        wounds at all - it counts attacks that never got through, plus what
        Feel No Pain and damage reduction stopped, and both of those are
        recorded on the defender where no attacker is needed. A mortal wound
        that lands was not prevented by anybody."""
        if amount <= 0:
            return
        target = _live_squad(getattr(target_model, "squad", None))
        attacker = _live_squad(attacker_squad)
        if attacker is None or target is None or attacker.owner == target.owner:
            # Self-inflicted wounds ([HAZARDOUS] 24.15, Deadly Demise on one's
            # own passengers) are nobody's kill - counting them would let a
            # unit climb the killing table by hurting its own army.
            if attacker is None:
                self.unattributed_wounds += amount
            return
        record = self._record_for(attacker)
        if record is None:
            return
        record.wounds_dealt += amount
        # "and additionally converted into points" - pro rata, the same
        # arithmetic ai/observation.py's damage_value() already uses (a share
        # of the target times the target's own cost). It needs no kill
        # attribution, which this engine does not have (see main.py's death
        # sweep: "there is no kill attribution here"), and it credits the unit
        # that softened a 300-point tank rather than only the one that
        # happened to land the last wound.
        points = getattr(target, "points", None)
        if points:
            total = starting_wounds(target)
            if total > 0:
                record.points_dealt += (min(amount, total) / total) * points

    def record_attack_group(self, target_squad, weapon, attacks, landed):
        """One weapon's attacks against `target_squad` have fully resolved:
        `attacks` were made and `landed` of them reached damage allocation.

        The difference is what the defender turned aside - by not being hit,
        not being wounded, or making its save, which is exactly the three the
        user named. Valued at what each of those attacks COULD have done
        (weapons.max_damage()), so a Bright Lance shot that misses is worth 8.

        WHY ATTACKS AND NOT DAMAGE POINTS: valuing this as "potential minus
        actual" would hand a unit credit for overkill - a D6+2 attack that
        kills a 1-wound Guardian wastes 7, and cheap chaff would top the
        tanking table for dying efficiently. Only attacks that never got
        through count."""
        target = _live_squad(target_squad)
        if target is None or weapon is None:
            return
        missed = max(0, attacks - landed)
        if not missed:
            return
        record = self._record_for(target)
        if record is not None:
            record.prevented += missed * weapons.max_damage(weapon)

    def record_prevented(self, target_model, amount):
        """`amount` damage was stopped AFTER the attack had already got
        through - Feel No Pain (24.12), or a Damage-reducing ability
        (game/molten_form.py, game/damage_reduction.py, Counterfire Defence
        Systems), all of which meet in DamageAllocationSession._reduced_damage().

        Counted explicitly rather than as the leftover between potential and
        actual, because that leftover also contains a Damage die simply
        rolling low - and a D6 coming up 3 is not something the defender did."""
        if amount <= 0:
            return
        record = self._record_for(getattr(target_model, "squad", None))
        if record is not None:
            record.prevented += amount

    def notify_move(self, squad, move_mode, distance_in):
        """A confirmed move of `distance_in`, measured as the FARTHEST any one
        model in the unit travelled.

        Every move type counts - Normal, Advance, Fall Back, Charge, Pile In,
        Consolidate, Scout, and the reactive ones - because the question is how
        far this unit got, not which rule moved it. `move_mode` is taken and
        deliberately unused: it is the fact the one universal call site in
        confirm_move() already hands out, and a statistic that later wants to
        split "advanced" from "walked" should not have to re-thread it.

        MovementController.moved_distance_this_turn is NOT reused: it is an
        assignment rather than a sum, it is wiped every player turn, and it is
        deliberately narrowed to Movement-phase moves for rule 24.16's sake."""
        if distance_in <= 0:
            return
        record = self._record_for(squad)
        if record is not None:
            record.distance_in += distance_in

    # ------------------------------------------------------------------ reading

    def record(self, name):
        return self._records.get(name)

    def _ranked(self, player, key, limit):
        rows = [r for r in self._records.values() if r.owner == player and key(r) > 0]
        # Name breaks ties so two units with identical numbers cannot swap
        # places between frames - the table is redrawn every frame it is open.
        rows.sort(key=lambda r: (-key(r), r.name))
        return rows[:limit]

    def top_killers(self, player, limit=3):
        return self._ranked(player, lambda r: r.wounds_dealt, limit)

    def top_tanks(self, player, limit=3):
        return self._ranked(player, lambda r: r.prevented, limit)

    def top_movers(self, player, limit=3):
        return self._ranked(player, lambda r: r.distance_in, limit)

    # -------------------------------------------------------------- save / load

    def save_state(self):
        """Same shape as MissionController.save_state() - a plain dict of
        primitives, keyed the way the rest of a snapshot is keyed."""
        return {"units": {name: record.as_dict()
                          for name, record in sorted(self._records.items())},
                "unattributed_wounds": self.unattributed_wounds}

    def load_state(self, data):
        problems = []
        for name, values in (data.get("units") or {}).items():
            record = self._records.get(name)
            if record is None:
                record = self._records[name] = UnitRecord(name, values.get("owner"))
            try:
                record.load(values)
            except (TypeError, ValueError):
                problems.append(f"unit statistics for {name!r} could not be read")
        self.unattributed_wounds = int(data.get("unattributed_wounds") or 0)
        return problems
