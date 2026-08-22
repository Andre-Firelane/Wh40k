"""Painboy's "Grot Orderly" wargear ability, as supplied by the user (not a
rule from the generic 40k core rulebook, so it lives in its own module - same
reasoning as game/ammo_runt.py for Flash Gitz' own wargear item).

RULE (Grot Orderly, wargear ability):
  Once per battle, in your Command phase, if the bearer is leading a unit that
  is below its Starting Strength, you can return up to D3 destroyed Bodyguard
  models to that unit.

  Designer's Note: Place a Grot Orderly token next to the unit, removing it
  once this ability has been used.

THE NEW CONCEPT: PUTTING MODELS BACK
------------------------------------
Everything in this engine so far only ever REMOVES models from a unit. Two
pieces had to exist before this ability could:

  * a record of what was destroyed. GameState.remove_dead_models() takes a
    dead Token out of Squad.models but keeps the object alive (rules 19.02 and
    19.04 already depend on that, via AttachedComponent.starting_models), so
    all that was missing was a list to find it in again - Squad.destroyed_models.
  * somewhere legal to stand it. Rule 09.02 does not care that a model just
    arrived: the unit still has to end up as one connected group. The survivors
    are already standing somewhere legal and must NOT move, so this is not the
    "pack a whole unit around a point" problem that game/formation_layout.py's
    pack_positions() solves - it is the same problem with the survivors seeded
    as already-placed. That is formation_layout.returning_positions(), which
    gives coherency BY CONSTRUCTION rather than hoping for it, exactly as the
    disembark clump does.

"UP TO D3" IS LOAD-BEARING
--------------------------
A returning model that finds nowhere legal to stand is simply not returned,
and the rest still are. That is not a fudge around a hard case: the rule says
"up to", so returning fewer is a legal outcome, and it is much better than
either forcing a model onto illegal ground or throwing the whole return away.
The D3 is rolled visibly first (one D3, as printed), and the count returned is
min(roll, destroyed bodyguard models available, models that fit).

BODYGUARD MODELS ONLY
---------------------
Read through rule 19.01's own component provenance (game/attached_units.py's
bodyguard_models()), so the Painboy himself - and any other leader/support
model attached to the same unit - can never be brought back by it. He also
cannot be dead in the first place while this triggers: "the bearer is leading
a unit" requires him alive and attached.

WHICH destroyed models come back is NOT offered as a choice. The rule does not
say the player picks, and this returns them in the order they were destroyed
(oldest first). Flagged as a simplification rather than a reading: if the
choice should be the player's, this is the one place to add it.

WHO DECIDES
-----------
`auto_players` - main.py passes the AI's side, per the user's explicit
instruction that the AI use it deterministically at the first opportunity. For
those players the ability fires the first Command phase its conditions hold;
anyone else gets the DecisionManager prompt and keeps the choice, the same
auto_players split game/ammo_runt.py and game/spirit_of_gork.py use. Holding
it back is a real option for a human - a bigger D3 is worth more when more
models are down - which is why the prompt is not simply skipped for everyone.
"""

from game import attached_units
from game.formation_layout import returning_positions
from game.squad import is_below_starting_strength
from game.turn import PHASE_COMMAND

GROT_ORDERLY_DICE_SIDES = 3  # "up to D3 destroyed Bodyguard models"


def unit_has_grot_orderly(squad):
    """True while at least one live model carrying the wargear is in the unit
    - the rule 19.04 reading every other datasheet ability here uses."""
    if squad is None:
        return False
    return any(getattr(m, "grot_orderly", False) for m in squad.models if not m.is_dead())


def bearer_models(squad):
    return [m for m in squad.models if not m.is_dead() and getattr(m, "grot_orderly", False)]


def returnable_models(squad):
    """The destroyed BODYGUARD models (19.01) of this unit, oldest destruction
    first. A model already back on the battlefield is never offered again."""
    if squad is None:
        return []
    bodyguard = {id(m) for m in attached_units.bodyguard_models(squad, alive_only=False)}
    return [
        m for m in getattr(squad, "destroyed_models", ())
        if id(m) in bodyguard and m not in squad.models
    ]


class GrotOrderlyController:
    """Resolves the ability in its owner's Command phase. main.py drives it
    from its own phase-change block, the same way Spirit of Gork is driven
    from the start of the Fight phase."""

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, position_valid=None, auto_players=()):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        # position_valid(model, x, y) -> bool. main.py passes SetupController's
        # own predicate, so "somewhere legal" means exactly what it means for
        # every other placement in the game (board edge, Dense terrain that
        # blocks this model, overlap with another unit's models).
        self.position_valid = position_valid
        self.auto_players = set(auto_players)
        self._used = set()     # id(bearer model) - once per battle, never cleared
        self._pending = None   # {"squad", "bearer"} while the D3 is on the table

    # ---------------------------------------------------------------- state

    @property
    def is_busy(self):
        return self._pending is not None

    def has_been_used(self, bearer):
        return id(bearer) in self._used

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    # ----------------------------------------------------------- conditions

    def can_use(self, squad, turn_tracker=None):
        """Every clause of the condition line, in the order it is printed.
        The two that need a rule to read them:

        "the bearer is LEADING a unit" - rule 19.01's real attached unit, not
        merely a squad containing the model. Same false positive
        game/attached_units.py's leader_ability() documents.

        "below its Starting Strength" - the Appendix's own definition, which
        game/squad.py already implements for rule 08.03's Battle-Shock test."""
        if self._pending is not None or squad is None:
            return False
        if turn_tracker is not None:
            if turn_tracker.phase != PHASE_COMMAND or turn_tracker.turn_owner != squad.owner:
                return False
        bearers = [b for b in bearer_models(squad) if not self.has_been_used(b)]
        if not bearers:
            return False
        if not attached_units.is_attached_unit(squad):
            return False
        if not is_below_starting_strength(squad):
            return False
        return bool(returnable_models(squad))

    def eligible_squads(self, squads, turn_tracker=None):
        return [s for s in squads if self.can_use(s, turn_tracker)]

    # ----------------------------------------------------------- the offer

    def offer_at_command_phase(self, squads, turn_tracker=None):
        """Offers the ability to the first eligible unit. Returns True if
        anything happened (used outright, or a prompt raised).

        One unit at a time on purpose: the D3 is a visible dice step, and two
        of them queued behind one another would need a queue for a case that
        needs a second Painboy in the same army to exist at all. A second
        eligible unit simply gets its chance next Command phase."""
        for squad in self.eligible_squads(squads, turn_tracker):
            return self.offer(squad)
        return False

    def offer(self, squad):
        if not self.can_use(squad):
            return False
        bearer = next(b for b in bearer_models(squad) if not self.has_been_used(b))
        available = len(returnable_models(squad))
        if squad.owner in self.auto_players:
            self._use(squad, bearer)
            return True
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: Grot Orderly (once per battle) - return up to D3 of its "
            f"{available} destroyed Bodyguard model(s)?",
            [
                ("Use the Grot Orderly", lambda: self._use(squad, bearer)),
                ("Save it for later", lambda: None),
            ],
        )
        return True

    def _use(self, squad, bearer):
        self._used.add(id(bearer))
        self._pending = {"squad": squad, "bearer": bearer}
        if self.dice_manager is None:
            # Non-interactive callers (tests, headless tools) still get the
            # effect; the maximum is what "up to D3" allows.
            self._resolve(GROT_ORDERLY_DICE_SIDES)
            return
        self.dice_manager.roll(
            count=1, sides=GROT_ORDERLY_DICE_SIDES,
            label=f"Grot Orderly: D3 models returned to {squad.name}",
            target_name=squad.name,
        )

    def on_dice_acknowledged(self):
        if self._pending is None:
            return False
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        self._resolve(values[0])
        return True

    # ------------------------------------------------------------- the work

    def _resolve(self, rolled):
        ctx, self._pending = self._pending, None
        squad = ctx["squad"]
        candidates = returnable_models(squad)[:max(0, rolled)]
        if not candidates:
            self._log(f"Grot Orderly ({squad.name}): rolled a {rolled}, but there is nothing to return.")
            return
        spots = returning_positions(squad, candidates, position_valid=self._valid_for)
        returned = []
        for model, spot in zip(candidates, spots):
            if spot is None:
                continue
            self._return_model(squad, model, spot)
            returned.append(model)
        if not returned:
            self._log(
                f"Grot Orderly ({squad.name}): rolled a {rolled}, but no returning model could be "
                f"placed in coherency (09.02) - none came back."
            )
            return
        short = "" if len(returned) == len(candidates) else (
            f" ({len(candidates) - len(returned)} had nowhere legal to stand)"
        )
        self._log(
            f"Grot Orderly ({squad.name}): rolled a {rolled} - {len(returned)} destroyed "
            f"Bodyguard model(s) return to the unit{short}."
        )

    def _valid_for(self, model, x_in, y_in):
        if self.position_valid is None:
            return True
        return self.position_valid(model, x_in, y_in)

    def _return_model(self, squad, model, spot):
        model.x_in, model.y_in = spot
        model.current_wounds = model.profile.wounds
        if model not in squad.models:
            squad.models.append(model)
        model.squad = squad
        if model in getattr(squad, "destroyed_models", ()):
            squad.destroyed_models.remove(model)
        if self.game_state is not None and model not in self.game_state.tokens:
            self.game_state.tokens.append(model)
