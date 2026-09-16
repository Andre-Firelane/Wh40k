"""The Warboss in Mega Armour's Krushin' Impetus (2026-09 Ork codex).

RULE (verbatim, rules/orks/Warboss in Mega Armour.md):
  "Krushin' Impetus: When this unit ends a charge move, you can select one
   enemy unit engaged with this unit. If you do, roll one D6 for each model in
   this unit engaged with that enemy unit:
   - For each 3+, that enemy unit suffers 1 mortal wound."

KROOT LINEBREAKERS WITH ONE STAGE LESS. The same charge-move seam, the same
handful ("one D6 for each model ... engaged with that enemy unit"), measured per
MODEL rather than taken from the unit's size - but every 3+ is ONE mortal wound
where the Krootox roll a second D3 stage, and there is no Battle-shock clause.
So it subclasses MortalWoundOfferController and inherits the 06.02 plumbing
(pending_damage_choice, choose_damage_model, the FNP leg) that every carrier
needs and five of them once shipped without.

"THIS UNIT" is the attached unit while the Warboss leads Meganobz - rule 19.04
confers the ability on every model until its source is destroyed, which is
unit_wide_ability()'s component-wise reading. So the Meganobz' models roll too,
and a mob that has lost its Warboss rolls nothing.

"YOU CAN SELECT" IS NOT OFFERED AS A DECLINE. Rolling costs nothing and can only
hurt the enemy, so a "don't" option would never be the better answer (the
reasoning Kauyon's "any or all" and rule 24.29 already use for automatic
resolution). The one real choice is WHICH enemy: one candidate is used outright,
several are a board pick for a human (game/unit_pick.py), and the AI takes the
shared damage-value ranking - 0 API calls.
"""

from game.mortal_wound_abilities import MortalWoundOfferController, enemy_squads, gap_to
from game.squad import ENGAGEMENT_RANGE_IN, unit_wide_ability

KRUSHIN_IMPETUS_NAME = "Krushin' Impetus"
#: "For each 3+".
KRUSHIN_IMPETUS_THRESHOLD = 3


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "krushin_impetus"))


def _alive(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def targets(squad, all_tokens):
    """The enemy units engaged with this unit - with ANY of its living models."""
    out = []
    for enemy in enemy_squads(squad, all_tokens):
        if enemy in out:
            continue
        if any(gap_to(m, enemy) <= ENGAGEMENT_RANGE_IN for m in _alive(squad)):
            out.append(enemy)
    return out


def dice_for(squad, target):
    """One D6 for each model of this unit that is ITSELF engaged with `target`."""
    if squad is None or target is None:
        return 0
    return sum(1 for m in _alive(squad) if gap_to(m, target) <= ENGAGEMENT_RANGE_IN)


class KrushinImpetusController(MortalWoundOfferController):
    """Fired by ChargeController.on_charge_move_finished, like Kroot Linebreakers."""

    label = KRUSHIN_IMPETUS_NAME

    def can_use(self, squad):
        return (self._pending is None and has_ability(squad)
                and bool(targets(squad, self._tokens())))

    def on_charge_move_finished(self, squad):
        if not self.can_use(squad):
            return False
        return self.offer(squad)

    def offer(self, squad):
        if not self.can_use(squad):
            return False
        candidates = targets(squad, self._tokens())
        if len(candidates) == 1 or squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, self._pick(squad, candidates))
        options = [("%s: %s" % (KRUSHIN_IMPETUS_NAME, t.name), (lambda target=t: self._use(squad, target)), t)
                   for t in candidates]
        self.decision_manager.request(
            squad.owner, "%s: %s - which engaged enemy unit?" % (squad.name, KRUSHIN_IMPETUS_NAME),
            options)
        return True

    def _use(self, squad, target):
        if target is None:
            return False
        dice = dice_for(squad, target)
        if dice <= 0 or self.dice_manager is None:
            return False
        self._pending = {"squad": squad, "target": target, "dice": dice}
        self.dice_manager.roll(
            dice, 6, label=self.label, success_threshold=KRUSHIN_IMPETUS_THRESHOLD,
            target_name=target.name, attacker_squad=squad, target_squad=target)
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            return self._ack_session()
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or []
        return self._resolve(values)

    def _resolve(self, values):
        ctx, self._pending = self._pending, None
        wounds = sum(1 for v in values if v >= KRUSHIN_IMPETUS_THRESHOLD)
        if wounds <= 0:
            self._log("%s (%s): no 3+ among %d dice - %s is unharmed."
                      % (KRUSHIN_IMPETUS_NAME, ctx["squad"].name, ctx["dice"], ctx["target"].name))
            return True
        self._log("%s (%s): %d of %d dice - %s suffers %d mortal wound(s)."
                  % (KRUSHIN_IMPETUS_NAME, ctx["squad"].name, wounds, ctx["dice"],
                     ctx["target"].name, wounds))
        self._inflict(ctx["target"], wounds)
        return True
