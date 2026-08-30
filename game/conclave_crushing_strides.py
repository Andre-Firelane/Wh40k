"""Spirit Conclave Stratagem: Crushing Strides (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Spirit Conclave.md):
  WHEN:   Your Charge phase, just after a WRAITHBLADES, WRAITHLORD or
          WRAITHKNIGHT unit from your army ends a Charge move.
  TARGET: That WRAITHBLADES, WRAITHLORD or WRAITHKNIGHT unit.
  EFFECT: Select one enemy unit within Engagement Range of your unit and roll
          one D6 for each WRAITHBLADES model in your unit, or roll four D6 if
          your unit has the WRAITHLORD keyword, or roll six D6 if your unit has
          the WRAITHKNIGHT keyword: for each 3+, that enemy unit suffers 1
          mortal wound.
  RESTRICTIONS: none printed.

THE SIXTH CARRIER OF game/mortal_wound_abilities.py's machinery, and the first
that is a STRATAGEM rather than a datasheet ability. That is why the shared base
lost its leading underscore: it was private to that module while all five users
lived in it, and a name that says "private" with a consumer outside is the kind
this repo renames.

THE DICE COUNT IS THREE DIFFERENT RULES, not one formula, and the printed text
is explicit about each:

    WRAITHBLADES   one D6 per MODEL in the unit
    WRAITHLORD     a flat four D6
    WRAITHKNIGHT   a flat six D6

So it is NOT Kroot Linebreakers' "one per model that is itself in Engagement
Range" - that clause is not printed here, and reading it in would quietly halve
a Wraithblades charge that only reached with half its models. Nor is it "count
the models" for the two monsters, which are single-model units and would roll
one die instead of four or six. Each branch is measured on its own.

WRAITHKNIGHT IS A MEASURED NO-OP: the datasheet exists in the corpus but is not
built here (TITANIC, deliberately out of scope). Its branch is written and
tested against a hand-built unit anyway, because the alternative is discovering
at build time that the biggest number was never exercised.

"JUST AFTER ... ENDS A CHARGE MOVE" is ChargeController.on_charge_move_finished,
the hook Guardian Battlehost's stage added and Crimson Harvest and Kroot
Linebreakers already use. A charge that fell short simply finds no enemy within
Engagement Range and the offer never appears - the same reasoning both of those
write out, and the reason no separate "did the charge succeed" test is needed.

ONE ROLL, NOT TWO. Kroot Linebreakers rolls a gate and then a D3 per hit; this
counts 3+ and each is exactly one mortal wound, so there is a single stage.

THE AI DECLINES (standing Aeldari instruction) - unlike the datasheet abilities
in that module, which resolve deterministically because they cost nothing. A CP
is a whole-army resource and this engine has no measure for spending one.
"""

from game import aeldari_detachments, shepherds_of_the_dead
from game.mortal_wound_abilities import MortalWoundOfferController
from game.squad import ENGAGEMENT_RANGE_IN, edge_distance
from game.stratagems import Stratagem
from game.turn import PHASE_CHARGE

CRUSHING_STRIDES_NAME = "Crushing Strides"
CRUSHING_STRIDES_CP = 1

#: "for each 3+, that enemy unit suffers 1 mortal wound".
CRUSHING_STRIDES_THRESHOLD = 3

#: The three printed dice rules, in the order the card reads them. The first
#: is per MODEL, the other two are flat.
CRUSHING_STRIDES_WRAITHLORD_DICE = 4
CRUSHING_STRIDES_WRAITHKNIGHT_DICE = 6

CRUSHING_STRIDES_KEYWORDS = ("WRAITHBLADES", "WRAITHLORD", "WRAITHKNIGHT")

SETTING = shepherds_of_the_dead.SETTING


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def eligible_unit(squad):
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k)
               for k in CRUSHING_STRIDES_KEYWORDS)


def dice_for(squad):
    """Three printed rules, checked in the card's own order.

    WRAITHKNIGHT and WRAITHLORD are FLAT counts - both are single-model units,
    so counting models would roll one die where the card says six or four."""
    if squad is None:
        return 0
    from game.attached_units import unit_has_datasheet_keyword
    if unit_has_datasheet_keyword(squad, "WRAITHKNIGHT"):
        return CRUSHING_STRIDES_WRAITHKNIGHT_DICE
    if unit_has_datasheet_keyword(squad, "WRAITHLORD"):
        return CRUSHING_STRIDES_WRAITHLORD_DICE
    if unit_has_datasheet_keyword(squad, "WRAITHBLADES"):
        # "one D6 for each WRAITHBLADES model in your unit" - every model,
        # NOT only those in Engagement Range. That clause belongs to Kroot
        # Linebreakers and is not printed here.
        return sum(1 for m in (getattr(squad, "models", ()) or ())
                   if not m.is_dead())
    return 0


def targets_for(squad, all_tokens=()):
    """"one enemy unit within Engagement Range of your unit"."""
    if squad is None:
        return []
    mine = [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]
    out = []
    for token in all_tokens or ():
        enemy = getattr(token, "squad", None)
        if enemy is None or enemy.owner == squad.owner or token.is_dead():
            continue
        if enemy in out:
            continue
        if any(edge_distance(m, token) <= ENGAGEMENT_RANGE_IN for m in mine):
            out.append(enemy)
    return out


class CrushingStridesController(MortalWoundOfferController):
    """Fired by ChargeController, like Crimson Harvest and Kroot Linebreakers -
    but with a CP cost and a 15.01 ledger those two do not have."""

    label = CRUSHING_STRIDES_NAME

    def __init__(self, *args, stratagem_controller=None, turn_tracker=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self._stratagem = Stratagem(
            name=CRUSHING_STRIDES_NAME, cp_cost=CRUSHING_STRIDES_CP,
            effect=self._noop_effect,
            # Two wraith units can each end a charge in one phase, and each is
            # its own printed trigger.
            allow_repeat_target=True,
        )

    def _noop_effect(self, controller, player, targets):
        """The CP is what rule 15.01 tracks; the dice are rolled by _use()
        below, which is where the target is known."""
        return None

    def can_use(self, squad):
        if squad is None or self._pending is not None:
            return False
        if self.stratagem_controller is None:
            return False
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_CHARGE:
            return False
        if not eligible_unit(squad):
            return False
        if dice_for(squad) <= 0:
            return False
        if not targets_for(squad, self._tokens()):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def on_charge_move_finished(self, squad):
        """A charge that fell short leaves nothing in Engagement Range, so the
        ability simply finds no target - the same reasoning Crimson Harvest's
        own hook gives."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return False               # no AI path
        targets = targets_for(squad, self._tokens())
        self.decision_manager.request(
            squad.owner,
            "%s (%d CP): %s ended a charge - crush an enemy unit with %d D6?"
            % (CRUSHING_STRIDES_NAME, CRUSHING_STRIDES_CP, squad.name,
               dice_for(squad)),
            [("Use (%d CP)" % CRUSHING_STRIDES_CP,
              (lambda s=squad: self._choose(s)))] +
            [("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def _choose(self, squad):
        """"Select one enemy unit" - not optional once bought, so the only
        decision left is WHICH, and one candidate needs no question."""
        if not self.can_use(squad):
            return False
        targets = targets_for(squad, self._tokens())
        if len(targets) == 1 or squad.owner in self.auto_players \
                or self.decision_manager is None:
            return self._use(squad, self._pick(squad, targets))
        self.decision_manager.request(
            squad.owner,
            "%s: %s crushes which unit?" % (CRUSHING_STRIDES_NAME, squad.name),
            [("%s: %s" % (CRUSHING_STRIDES_NAME, t.name),
              (lambda target=t: self._use(squad, target))) for t in targets],
        )
        return True

    def _use(self, squad, target):
        if target is None or not self.can_use(squad):
            return False
        dice = dice_for(squad)
        if dice <= 0:
            return False
        if not self.stratagem_controller.use(squad.owner, self._stratagem, [squad]):
            return False
        self._pending = {"squad": squad, "target": target, "dice": dice}
        self.dice_manager.roll(
            dice, 6, label=self.label, success_threshold=CRUSHING_STRIDES_THRESHOLD,
            target_name=target.name, attacker_squad=squad, target_squad=target)
        return True

    def on_dice_acknowledged(self):
        """ONE stage: each 3+ is exactly one mortal wound, where Kroot
        Linebreakers rolls a gate and then a D3 per hit."""
        if self._pending is None:
            return False
        values = (self.dice_manager.last_values if self.dice_manager is not None
                  else None) or []
        ctx = self._pending
        self._pending = None
        wounds = sum(1 for v in values if v >= CRUSHING_STRIDES_THRESHOLD)
        self._log("%s (%s): %d of %d dice at %d+ - %d mortal wound(s) on %s."
                  % (CRUSHING_STRIDES_NAME, ctx["squad"].name, wounds, ctx["dice"],
                     CRUSHING_STRIDES_THRESHOLD, wounds, ctx["target"].name))
        self._inflict(ctx["target"], wounds)
        return True
