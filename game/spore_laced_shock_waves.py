"""The Plagueburst Crawler's own ability "Spore-laced Shock Waves".

RULE (printed): in your Shooting phase, each time you select a target for this
model's Plagueburst mortar, roll one D6 for the target unit and for each other
enemy unit within 3" of it, adding 1 to the result if that unit is Afflicted.
On a 6+ that unit is struck by spores, and after this model has resolved all of
its attacks against the target unit, each struck unit suffers D3 mortal wounds.

THE SPLASH IS THE POINT: it is the only ability in this faction that reaches
units the Crawler did not shoot at, and the 3" is measured from the TARGET, not
from the Crawler - so a tightly packed enemy line takes it in several places.

TWO MOMENTS, AND THEY ARE DELIBERATELY DIFFERENT:
  * the D6s are rolled WHEN THE TARGET IS SELECTED, before any attack is made -
    so the set of units at risk is frozen at that instant, exactly as rule
    10.02's target snapshot freezes range and cover. Rolling afterwards would
    measure a board the Crawler's own shooting had already rearranged.
  * the mortal wounds land AFTER all of its attacks against that target have
    resolved. So a unit wiped out by the shooting itself never takes them,
    which is checked at resolution rather than assumed.

"+1 IF THAT UNIT IS AFFLICTED" is the second ability in the faction to READ
Nurgle's Gift rather than produce it (Gift of Contagion is the other), and it
is what makes the Crawler and the army rule work together rather than
independently.

NOT OPTIONAL and nothing to choose - no prompt, no auto_players, no API call.
"""
from game import nurgles_gift
from game.damage_resolution import MortalWoundAllocationSession
from game.weapons import RANGED

SPORE_THRESHOLD = 6            # "on a 6+"
SPORE_AFFLICTED_BONUS = 1      # "adding 1 to the result if that unit is Afflicted"
SPORE_SPLASH_RANGE_IN = 3.0
SPORE_DAMAGE_SIDES = 3         # "D3 mortal wounds"
PLAGUEBURST_MORTAR_NAME = "Plagueburst Mortar"


def has_ability(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "spore_laced_shock_waves", False) and not m.is_dead()
               for m in getattr(squad, "models", ()) or ())


def is_the_mortar(weapon):
    """Identified by the weapon's own class name rather than by a flag on the
    profile: the ability names ONE weapon, and a second Plagueburst Crawler
    weapon must not trigger it."""
    return getattr(weapon, "name", None) == PLAGUEBURST_MORTAR_NAME


def units_at_risk(target_squad, all_tokens):
    """The target unit, plus every OTHER enemy unit within 3" of it.

    "Enemy" is relative to the target's owner being the enemy - i.e. every unit
    on the target's own side. Sorted by name so the dice come out in a
    reproducible order."""
    if target_squad is None:
        return []
    out = {id(target_squad): target_squad}
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or token.is_dead() or id(other) in out:
            continue
        if other.owner != target_squad.owner:
            continue
        if target_squad.min_distance_to(other) <= SPORE_SPLASH_RANGE_IN:
            out[id(other)] = other
    return sorted(out.values(), key=lambda s: s.name)


def struck(rolled, squad):
    """Whether this unit's D6 struck it, Afflicted bonus included."""
    bonus = SPORE_AFFLICTED_BONUS if nurgles_gift.is_afflicted(squad) else 0
    return (rolled + bonus) >= SPORE_THRESHOLD


class SporeLacedShockWavesController:
    """Rolls when the mortar picks a target, resolves once it has finished."""

    def __init__(self, dice_manager=None, game_log=None, game_state=None):
        self.dice_manager = dice_manager
        self.game_log = game_log
        self.game_state = game_state
        self._struck = []            # units the spores caught, waiting to be resolved
        self._queue = []             # struck units still owed their D3
        self._current = None
        self.mortal_wound_session = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    @property
    def is_busy(self):
        return (self._current is not None or bool(self._queue)
                or self.mortal_wound_session is not None)

    def notify_target_selected(self, shooter_squad, weapon, target_squad):
        """"each time you select a target for this model's Plagueburst mortar".

        The D6s are rolled here, not shown as a dice-panel step: there is one
        per unit at risk and no decision attached to any of them, so they are
        resolved immediately and REPORTED, which is what keeps the visible dice
        flow to the one thing that matters - the D3 of mortal wounds."""
        if not has_ability(shooter_squad) or not is_the_mortar(weapon):
            return []
        from game.dice import random as dice_random
        caught = []
        for squad in units_at_risk(target_squad, self._tokens()):
            rolled = dice_random.randint(1, 6)
            bonus = SPORE_AFFLICTED_BONUS if nurgles_gift.is_afflicted(squad) else 0
            note = f" +{bonus} (Afflicted)" if bonus else ""
            if struck(rolled, squad):
                caught.append(squad)
                self._log(f"[spores] {squad.name}: rolled {rolled}{note} - struck "
                          f"(needed {SPORE_THRESHOLD}+).", file_only=True)
            else:
                self._log(f"[spores] {squad.name}: rolled {rolled}{note} - not struck.",
                          file_only=True)
        self._struck = caught
        return caught

    def resolve_after_attacks(self, shooter_squad):
        """"after this model has resolved all of its attacks against the target
        unit". A unit the shooting itself wiped out takes nothing."""
        queue = [s for s in self._struck
                 if any(not m.is_dead() for m in getattr(s, "models", ()) or ())]
        self._struck = []
        if not queue or self.dice_manager is None:
            return False
        self._queue = queue
        return self._roll_next()

    def _roll_next(self):
        while self._queue:
            squad = self._queue.pop(0)
            if not any(not m.is_dead() for m in getattr(squad, "models", ()) or ()):
                continue
            self._current = squad
            self.dice_manager.roll(
                1, SPORE_DAMAGE_SIDES, label="Spore-laced Shock Waves - mortal wounds (D3)",
                target_name=squad.name, target_squad=squad, subject_label="Struck")
            return True
        self._current = None
        return False

    def on_dice_acknowledged(self):
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_session_done()
            return True
        if self._current is None or self.dice_manager is None:
            return False
        squad = self._current
        self._current = None
        wounds = (self.dice_manager.last_values or [1])[0]
        self._log(f"Spore-laced Shock Waves: {squad.name} suffers {wounds} mortal wound(s).")
        self.mortal_wound_session = MortalWoundAllocationSession(
            squad, wounds, dice_manager=self.dice_manager, log=self._log)
        self._check_session_done()
        return True

    def _check_session_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
        self._roll_next()

    @property
    def pending_damage_choice(self):
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_session_done()
