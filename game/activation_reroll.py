"""One free die re-roll per shooting activation - the machinery, not a rule.

NINETEENTH EXTRACTION, at the second consumer.

The Hammerhead and Sky Ray Gunships' TARGETING ARRAY was the first ability of
this shape; the Fire Prism's CRYSTAL MATRIX is the second, and it prints
almost the same sentence:

  TARGETING ARRAY  "Each time this model is selected to shoot, you can re-roll
                   one Hit roll OR you can re-roll one Wound roll when
                   resolving those attacks."

  CRYSTAL MATRIX   "Each time this model is selected to shoot, you can re-roll
                   one Hit roll AND you can re-roll one Wound roll when
                   resolving those attacks."

ONE WORD APART, and that word is the whole difference: Targeting Array is ONE
use per activation, spendable on either roll; Crystal Matrix is one use of
EACH. So the ledger is keyed per (squad, roll kind) and an ability declares
whether its two kinds share a single use.

Everything else - the panel button, the click-a-die selection, the "a die is
never re-rolled twice" gate, the once-per-activation window opened by
ShootingController.start_shooting() - is identical, and duplicating it would
have meant a second copy of the interaction that game/command_reroll.py
already shaped once.

ONE CONTROLLER FOR BOTH ABILITIES, NOT ONE EACH, and that is deliberate: the
panel asks "does the active unit have a free re-roll available right now",
which is one question with one answer. A second controller would need a second
ActionPanel parameter and a second entry in main.py's click routing - and
ActionPanel.draw() is the three-stage, partly POSITIONAL chain this repo has
already been bitten by once. `panel_label()` names whichever ability the active
unit actually has, so the button says the right thing without the panel knowing
there are two.

A DIE CAN NEVER BE RE-ROLLED TWICE (core rule), which
DiceManager.rerollable_indices() already enforces - so a roll whose dice are
all spent offers nothing and the button does not appear. That is this repo's
standing rule about never offering what buys nothing, and here it also stops a
once-per-activation use being burned on a roll it could not change.
"""
from game.dice import DAMAGE_ROLL, HIT_ROLL, WOUND_ROLL

#: The widest set any ability here reaches. Each ability names its OWN kinds
#: below; this is only the union, used to reject a roll no ability could touch
#: before asking which one the unit has.
#:
#: It grew from {HIT, WOUND} when Armoured Warhost's Soulsight arrived - the
#: first of these to name a Damage roll. Command Re-roll already reached
#: DAMAGE_ROLL, so the die-selection UI needed nothing.
REROLLABLE_KINDS = {HIT_ROLL, WOUND_ROLL, DAMAGE_ROLL}

#: What the first two abilities print, and the default.
HIT_AND_WOUND = (HIT_ROLL, WOUND_ROLL)


class RerollAbility:
    """One printed ability of this shape.

    `shared_use` is the OR/AND distinction: True spends a single use on either
    roll kind (Targeting Array), False gives one use of each (Crystal Matrix).
    """

    def __init__(self, flag, label, shared_use, kinds=HIT_AND_WOUND,
                 on_squad=False):
        self.flag = flag
        self.label = label
        self.shared_use = shared_use
        #: Which roll kinds this ability may be spent on. Per ability rather
        #: than one module constant, because Soulsight names three where the
        #: other two name two - a single shared set would have quietly let
        #: Targeting Array re-roll a Damage roll it never mentions.
        self.kinds = tuple(kinds)
        #: Where the flag lives. The two datasheet abilities are printed on a
        #: model, so they are UnitProfile fields; a STRATAGEM is bought for a
        #: unit and latches on the Squad. Same ledger, different shelf.
        self.on_squad = on_squad


#: Every ability that grants a free re-roll for the duration of a shooting
#: activation. A third one is an entry here and nothing else.
ABILITIES = (
    RerollAbility("targeting_array", "Targeting Array", shared_use=True),
    RerollAbility("crystal_matrix", "Crystal Matrix", shared_use=False),
    # Armoured Warhost's Soulsight (1CP). The third of this shape and the
    # first that is a STRATAGEM rather than a datasheet ability: it is bought
    # for one activation, so its flag sits on the Squad, and it prints THREE
    # kinds where the other two print two.
    RerollAbility("soulsight_active", "Soulsight", shared_use=False,
                  kinds=(HIT_ROLL, WOUND_ROLL, DAMAGE_ROLL), on_squad=True),
)


def ability_of(squad):
    """The ability this unit prints, read LIVE off its living models so it ends
    with the model that carries it. None when the unit has none."""
    if squad is None:
        return None
    models = [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]
    for ability in ABILITIES:
        if ability.on_squad:
            if getattr(squad, ability.flag, False):
                return ability
            continue
        if any(getattr(m.profile, ability.flag, False) for m in models):
            return ability
    return None


class ActivationRerollController:
    """The panel button, the die selection, and the per-activation ledger.

    Structurally CommandRerollController (game/command_reroll.py) minus the
    Stratagem: no cost, no 15.01 bookkeeping, and its resource is the
    ACTIVATION rather than a CP pool."""

    def __init__(self, dice_manager=None, shooting_controller=None, game_log=None):
        self.dice_manager = dice_manager
        self.shooting_controller = shooting_controller
        self.game_log = game_log
        self.selecting_die = False
        # (id(squad), roll_kind) already spent this activation. Keyed by kind
        # even for a shared_use ability - `_ledger_key()` collapses those onto
        # one key, so one ledger serves both readings.
        self._used_this_activation = set()

    # -- the activation ledger --------------------------------------------

    def _ledger_key(self, squad, roll_kind, ability):
        """A shared-use ability spends one slot whichever roll it is used on,
        so its two kinds map onto the SAME key."""
        return (id(squad), None if ability.shared_use else roll_kind)

    def begin_activation(self, squad):
        """Called from ShootingController.start_shooting(): a NEW activation,
        so this unit's use is available again."""
        self._forget(squad)

    def end_activation(self, squad):
        """Called when the activation finishes. Spending is recorded at USE,
        so this only tidies up; keeping it explicit means the ledger cannot
        leak into the next unit's activation."""
        self._forget(squad)
        self.selecting_die = False

    def _forget(self, squad):
        if squad is None:
            return
        for key in [k for k in self._used_this_activation if k[0] == id(squad)]:
            self._used_this_activation.discard(key)

    def available(self, squad, roll_kind=None):
        ability = ability_of(squad)
        if ability is None:
            return False
        if roll_kind is None:
            roll_kind = getattr(self.dice_manager, "roll_kind", None)
        if roll_kind is not None and roll_kind not in ability.kinds:
            return False   # this ability does not name this roll
        return self._ledger_key(squad, roll_kind, ability) not in self._used_this_activation

    # -- eligibility -------------------------------------------------------

    def _active_squad(self):
        return getattr(self.shooting_controller, "active_squad", None)

    def panel_label(self):
        """What the button says - the name of the ability the ACTIVE unit
        actually prints, so one button serves both."""
        ability = ability_of(self._active_squad())
        return ability.label if ability is not None else ""

    def can_use(self):
        if self.dice_manager is None or not self.dice_manager.is_pending:
            return False
        if self.dice_manager.roll_kind not in REROLLABLE_KINDS:
            return False
        if not self.dice_manager.rerollable_indices():
            return False
        return self.available(self._active_squad(), self.dice_manager.roll_kind)

    # -- the interaction ---------------------------------------------------

    def start(self):
        """The player clicked the ability's button."""
        if not self.can_use():
            return
        rerollable = self.dice_manager.rerollable_indices()
        if len(rerollable) == 1:
            self._reroll(rerollable[0])   # only one die to choose from
        else:
            self.selecting_die = True

    def choose_die(self, index):
        """The player clicked a die in the DicePanel while selecting_die.

        A die already re-rolled once cannot be picked - the click is ignored,
        leaving the selection open, rather than spending the use on nothing."""
        if not self.selecting_die:
            return
        if index not in self.dice_manager.rerollable_indices():
            return
        self.selecting_die = False
        self._reroll(index)

    def cancel_selection(self):
        self.selecting_die = False

    def _reroll(self, index):
        squad = self._active_squad()
        ability = ability_of(squad)
        if squad is None or ability is None:
            return
        roll_kind = self.dice_manager.roll_kind
        self._used_this_activation.add(self._ledger_key(squad, roll_kind, ability))
        self.dice_manager.reroll_die(index)
        if self.game_log:
            kind = "Hit" if roll_kind == HIT_ROLL else "Wound"
            self.game_log.add(
                "%s uses its %s to re-roll one %s die." % (squad.name, ability.label, kind))
