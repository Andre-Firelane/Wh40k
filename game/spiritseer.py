"""The Spiritseer's three abilities - one datasheet, so one module.

RULES (printed, word for word):

  Spiritseer:     "While this model is within 3" of one or more friendly WRAITH
                  CONSTRUCT units, this model has the Lone Operative ability."

  Spirit Mark:    "Once per turn, in your Movement phase, when this model
                  starts or ends a move, select one friendly WRAITH CONSTRUCT
                  unit within 6" of this model (excluding TITANIC units) and
                  one enemy unit visible to this model. Until the start of your
                  next Movement phase, weapons equipped by models in that
                  friendly unit have the [SUSTAINED HITS 1] ability while
                  targeting that enemy unit."

  Tears of Isha:  "In your Command phase, select one friendly WRAITH CONSTRUCT
                  unit within 6" of this model. If one or more models in that
                  unit are destroyed, you can return one destroyed model to
                  that unit. Otherwise, one model in that unit regains up to D3
                  lost wounds. Each unit can only be selected for this ability
                  once per turn."

All three point at WRAITH CONSTRUCT units, which is why they share a module and
one `_friendly_wraith_units()`.

SPIRITSEER IS ILLUMINOR SZERAS' CONDITIONAL LONE OPERATIVE
----------------------------------------------------------
Word for word the same shape - a range to a friendly unit of a named keyword,
granting 24.24 while it holds - so it plugs into the same place:
game/status_effects.py's lone_operative_range() already asks a module rather
than reading a printed value, precisely because Szeras made that necessary.
This is the second such grant and needed no new seam.

SPIRIT MARK IS A PAIR, NOT A MARK
---------------------------------
Every other mark in this engine names ONE unit. This names two - a friendly
unit and an enemy unit - and the grant only applies where they meet. So the
ledger stores PAIRS and the read takes both sides; storing it as "this friendly
unit has [SUSTAINED HITS 1]" would grant it against every target, which is a
strictly larger ability than the one printed.

The grant itself goes in the two _adjusted_weapon() chains rather than at the
wound step, because _crit_note() has to know at ROLL time whether a critical
die is a [SUSTAINED HITS] one - the same reason Ritual Butchery and both T'au
doctrines sit there.

"UNTIL THE START OF YOUR NEXT MOVEMENT PHASE" is its own clock: one phase
LATER than a Guide/Doom mark, which ends at the Command phase. Cleared at the
start of the owner's Movement phase for that reason.

TEARS OF ISHA HAS TWO BRANCHES AND THEY ARE NOT ALTERNATIVES THE PLAYER PICKS.
"If one or more models in that unit are destroyed, you CAN return one ...
Otherwise, one model regains up to D3 lost wounds." The return branch is
offered only when there is something to return; the heal is what happens when
there is not. Reading them as a free choice would let a full-strength unit
return a model it never lost.

The return itself is game/model_return.py - the shared four-halves helper
Grot Orderly, Fuegan and Protocol of the Eternal Revenant already use - so the
"back on the board" bookkeeping exists once.
"""
from game.formation_layout import returning_positions
from game.model_return import set_up_model
from game.squad import edge_distance

SPIRITSEER_LABEL = "Spiritseer"
SPIRIT_MARK_LABEL = "Spirit Mark"
TEARS_OF_ISHA_LABEL = "Tears of Isha"

WRAITH_CONSTRUCT_RANGE_IN = 3.0     # the Lone Operative grant
SPIRIT_MARK_RANGE_IN = 6.0
TEARS_OF_ISHA_RANGE_IN = 6.0
SPIRITSEER_LONE_OPERATIVE_RANGE_IN = 12.0   # rule 24.24's default X


from game import ai_mode, wraith_construct

def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def _has(squad, flag):
    return any(getattr(m.profile, flag, False) for m in _living(squad))


def has_spiritseer(squad):
    return _has(squad, "spiritseer_lone_operative")


def is_wraith_construct_unit(squad):
    """19.03's pooling, delegated to game/wraith_construct.py.

    That module exists because this question had TWO answers in the tree - this
    one read the UnitProfile FLAG while game/forewarned.py and
    game/shepherds_of_the_dead.py read the DATASHEET keyword. Measured, the two
    agree on every built datasheet; the keyword form won because that is what
    every printed clause names. Re-exported here so the Spiritseer's three
    abilities keep their own vocabulary."""
    return wraith_construct.is_wraith_construct_unit(squad)


def _friendly_wraith_units(squad, all_tokens, within_in):
    """Friendly WRAITH CONSTRUCT units with a model within `within_in` of one
    of this unit's models. Measured edge to edge, like every other datasheet
    range in this engine."""
    mine = _living(squad)
    seen, out = set(), []
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other is squad or id(other) in seen:
            continue
        if other.owner != squad.owner or not is_wraith_construct_unit(other):
            continue
        # Asked at the KEYWORD line. This used to read profile.titanic, a
        # field UnitProfile does not declare - so it was unconditionally
        # False, a silent no-op. Identical in behaviour today (nothing
        # built is TITANIC) and correct the day a Wraithknight is.
        if wraith_construct.is_titanic_unit(other):
            continue
        if any(edge_distance(m, t) <= within_in for m in mine for t in _living(other)):
            seen.add(id(other))
            out.append(other)
    return out


# --- 1. the conditional Lone Operative --------------------------------------

def grants_lone_operative(squad, all_tokens=()):
    """Whether the condition currently holds - asked by
    game/status_effects.py's lone_operative_range(), exactly as Szeras' is."""
    if not has_spiritseer(squad):
        return False
    return bool(_friendly_wraith_units(squad, all_tokens, WRAITH_CONSTRUCT_RANGE_IN))


# --- 2. Spirit Mark ---------------------------------------------------------

class SpiritMarkController:
    """The (friendly unit, enemy unit) pairs, and the [SUSTAINED HITS 1] grant.

    One per battle. Keyed by both sides, because the grant only applies where
    they meet - see the module docstring."""

    def __init__(self, decision_manager=None, game_log=None, all_tokens=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.auto_players = ai_mode.players(auto_players)
        self._pairs = {}            # player -> set of (id(friendly), id(enemy))
        self._used_this_turn = set()   # players who have already used it this turn

    def applies_to(self, attacking_squad, target_squad):
        """Does this attack get [SUSTAINED HITS 1] from a Spirit Mark?"""
        if attacking_squad is None or target_squad is None:
            return False
        key = (id(attacking_squad), id(target_squad))
        return key in self._pairs.get(attacking_squad.owner, ())

    def mark(self, bearer_squad, friendly_squad, enemy_squad):
        if bearer_squad is None or friendly_squad is None or enemy_squad is None:
            return False
        owner = bearer_squad.owner
        self._pairs.setdefault(owner, set()).add((id(friendly_squad), id(enemy_squad)))
        self._used_this_turn.add(owner)
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s's weapons gain [SUSTAINED HITS 1] against %s until the start "
                "of %s's next Movement phase."
                % (SPIRIT_MARK_LABEL, friendly_squad.name, enemy_squad.name, owner))
        return True

    def available(self, bearer_squad):
        """"Once per turn" - per ARMY, like the War Shaper's War Leader, since
        the printed text caps the ability rather than the model."""
        return (bearer_squad is not None
                and _has(bearer_squad, "spirit_mark")
                and bearer_squad.owner not in self._used_this_turn)

    def friendly_candidates(self, bearer_squad):
        return _friendly_wraith_units(bearer_squad, self.all_tokens, SPIRIT_MARK_RANGE_IN)

    def enemy_candidates(self, bearer_squad, visible_to=None):
        """Enemy units visible to this model. `visible_to(squad)` is injected so
        this module does not have to own a line-of-sight opinion; without it
        every enemy unit is offered, which is what a headless test wants."""
        seen, out = set(), []
        for token in self.all_tokens or ():
            other = getattr(token, "squad", None)
            if other is None or id(other) in seen or other.owner == bearer_squad.owner:
                continue
            if not _living(other):
                continue
            if visible_to is not None and not visible_to(other):
                continue
            seen.add(id(other))
            out.append(other)
        return out

    def start_of_movement_phase(self, player):
        """"Until the start of your next Movement phase" - one phase later than
        a Guide/Doom mark, which is why this is its own reset point."""
        self._pairs.pop(player, None)
        self._used_this_turn.discard(player)

    # --- the offer -------------------------------------------------------
    # THIS HALF WAS BUILT AND NEVER FED. mark(), available(), the two candidate
    # lists and start_of_movement_phase() all existed and were unit-tested, but
    # nothing in main.py ever called them - so in a real game the mark could
    # never be placed and the read half above was dead code. The eighth
    # instance of that class in this repo, and the reason the wiring is pinned
    # in the suite rather than merely the predicates.
    #
    # "WHEN THIS MODEL STARTS OR ENDS A MOVE" is the same pair of moments
    # Spirit Stone of Raelyth needs, which is what MovementController's
    # on_move_started/on_move_finished now provide.

    def on_move_started(self, squad):
        return self.offer(squad)

    def on_move_finished(self, squad):
        return self.offer(squad)

    def offer(self, bearer_squad, visible_to=None):
        """"select one friendly WRAITH CONSTRUCT unit ... and one enemy unit
        visible to this model" - two choices, chained."""
        if not self.available(bearer_squad):
            return False
        friends = self.friendly_candidates(bearer_squad)
        enemies = self.enemy_candidates(bearer_squad, visible_to=visible_to)
        if not friends or not enemies:
            return False
        if (bearer_squad.owner in self.auto_players
                or self.decision_manager is None):
            return False           # no AI path (standing Aeldari rule)
        self.decision_manager.request(
            bearer_squad.owner,
            "%s: which friendly WRAITH CONSTRUCT unit gains [SUSTAINED HITS 1]?"
            % SPIRIT_MARK_LABEL,
            [(f.name, (lambda x=f: self._pick_enemy(bearer_squad, x, enemies)), f)
             for f in friends]
            + [("Do not use it", lambda: False)],
        )
        return True

    def _pick_enemy(self, bearer_squad, friendly_squad, enemies):
        if len(enemies) == 1:
            return self.mark(bearer_squad, friendly_squad, enemies[0])
        self.decision_manager.request(
            bearer_squad.owner,
            "%s: against which enemy unit?" % SPIRIT_MARK_LABEL,
            [(e.name, (lambda x=e: self.mark(bearer_squad, friendly_squad, x)), e)
             for e in enemies],
        )
        return True


def spirit_mark_adjusted_weapon(weapon, controller, attacking_squad, target_squad):
    """A copy with [SUSTAINED HITS 1], or the weapon untouched.

    NEVER a downgrade: "have the [SUSTAINED HITS 1] ability" GRANTS it, it does
    not set the value - so a weapon that already prints a higher X keeps it.
    The same guard game/ritual_butchery.py and both T'au doctrines carry."""
    import copy
    if controller is None or weapon is None:
        return weapon
    if not controller.applies_to(attacking_squad, target_squad):
        return weapon
    if getattr(weapon, "sustained_hits", 0) and weapon.sustained_hits >= 1:
        return weapon
    adjusted = copy.copy(weapon)
    adjusted.sustained_hits = 1
    return adjusted


# --- 3. Tears of Isha -------------------------------------------------------

class TearsOfIshaController:
    """The Command-phase return-or-heal. One per battle."""

    #: "regains up to D3 lost wounds"
    HEAL_SIDES = 3

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, all_tokens=None, position_valid=None,
                 auto_players=()):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.all_tokens = all_tokens if all_tokens is not None else []
        # position_valid(model, x, y) - injected by main.py from the setup
        # controller, so this module owns no placement-legality opinion.
        self.position_valid = position_valid
        self.auto_players = ai_mode.players(auto_players)
        self._used_this_turn = set()    # id(squad) already selected this turn

    def candidates(self, bearer_squad):
        """"one friendly WRAITH CONSTRUCT unit within 6"", not already selected
        this turn, and with something to gain - a full-strength, undamaged unit
        is not offered, on this repo's standing rule against offering what buys
        nothing."""
        if bearer_squad is None or not _has(bearer_squad, "tears_of_isha"):
            return []
        return [s for s in _friendly_wraith_units(bearer_squad, self.all_tokens,
                                                  TEARS_OF_ISHA_RANGE_IN)
                if id(s) not in self._used_this_turn and self.would_do_something(s)]

    def would_do_something(self, squad):
        return bool(self.returnable(squad)) or self.missing_wounds(squad) > 0

    def returnable(self, squad):
        return list(getattr(squad, "destroyed_models", ()) or ())

    def missing_wounds(self, squad):
        total = 0
        for model in _living(squad):
            total += max(0, model.profile.wounds - model.current_wounds)
        return total

    def resolve(self, bearer_squad, squad):
        """The two branches, in the printed order.

        NOT a free choice: the heal is what happens when there is nothing to
        return ("Otherwise"), so a full-strength unit can never return a model
        it never lost."""
        if squad is None:
            return None
        self._used_this_turn.add(id(squad))
        destroyed = self.returnable(squad)
        if destroyed:
            return self._return_one(squad, destroyed[0])
        return self._heal(squad)

    def _return_one(self, squad, model):
        """Where it stands is formation_layout.returning_positions() - the same
        helper Grot Orderly uses, which seeds the collision set with the models
        already standing there so 09.02 coherency holds by construction. A model
        with nowhere legal to stand is NOT forced onto the board; the ability
        simply does nothing, which is how Grot Orderly reads its own failure."""
        spots = returning_positions(squad, [model], position_valid=self.position_valid)
        spot = spots[0] if spots else None
        if spot is None:
            if self.game_log is not None:
                self.game_log.add("%s: %s has nowhere legal to return a model."
                                  % (TEARS_OF_ISHA_LABEL, squad.name), file_only=True)
            return None
        set_up_model(model, spot, game_state=self.game_state)
        if self.game_log is not None:
            self.game_log.add("%s: one %s is returned to %s."
                              % (TEARS_OF_ISHA_LABEL, model.profile.name, squad.name))
        return "returned"

    def _heal(self, squad):
        hurt = [m for m in _living(squad) if m.current_wounds < m.profile.wounds]
        if not hurt:
            return None
        healed = self._roll_d3()
        model = hurt[0]
        before = model.current_wounds
        model.current_wounds = min(model.profile.wounds, before + healed)
        if self.game_log is not None:
            self.game_log.add("%s: %s regains %d wound(s)."
                              % (TEARS_OF_ISHA_LABEL, squad.name,
                                 model.current_wounds - before))
        return "healed"

    def _roll_d3(self):
        from game.dice import random as dice_random
        return dice_random.randint(1, self.HEAL_SIDES)

    def reset_turn(self):
        self._used_this_turn.clear()
