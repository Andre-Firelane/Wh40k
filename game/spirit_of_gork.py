"""Kill Rig's own "Spirit of Gork (Psychic)" ability, as supplied by the
user (not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/ferocious_rage.py for the Beastboss's and
game/monster_hunters.py for Beast Snagga Boyz').

RULE: At the start of the Fight phase, you can select one friendly ORKS unit
within 12" of this model and roll one D6:
  * on a 1, this model suffers D3 mortal wounds;
  * on a 2-5, until the end of the phase, add 1 to the Strength
    characteristic of melee weapons equipped by models in that unit;
  * on a 6, the same, and those weapons also have [LETHAL HITS].

TWO ROLLS, IN SEQUENCE
----------------------
The D6 decides the outcome, and only the 1 needs a second roll (D3 mortal
wounds onto the Kill Rig itself). Both are real, visible DiceManager rolls,
sequenced the same way game/grav_inhibitor_field.py sequences its own two -
DiceManager holds exactly one pending roll, so the second is started from
the first one's acknowledgement rather than alongside it.

WHO PICKS THE TARGET
--------------------
"you can select" is a choice, so it goes through DecisionManager - with one
exception, `auto_players`: for those the target is chosen deterministically
(the highest-points OTHER unit, falling back to the caster's own unit when
no other is eligible) and no prompt is raised at all. That is an explicit
user instruction for the AI, and it is the same auto_players shape
game/ard_as_nails.py already uses. Points are read from Squad.points, which
is None for a unit whose faction has no published list - those sort last
rather than crashing. See strongest() for why "other" is worth spelling out.

Declining stays available to a human: the rule says "can", and on a 1 the
Kill Rig hurts itself, so it is a real gamble rather than free value.

THE EFFECT IS A UNIT FLAG, NOT A WEAPON COPY
---------------------------------------------
The buff lands on the TARGET unit, which may be anywhere on the board and is
not the unit being resolved when a fight actually happens - so it is stored
on the Squad (spirit_of_gork_strength / spirit_of_gork_lethal) and read at
attack time by spirit_of_gork_adjusted_weapon(), chained into game/fight.py
next to War Horde's Get Stuck In. Same arrangement as
game/ard_as_nails.py's own defensive flag, and for the same reason.

"Until the end of the phase" is cleared by reset_phase(), called from
main.py's own phase-change block alongside every other per-phase grant.

MELEE ONLY, AND THE WHOLE UNIT
-------------------------------
"melee weapons equipped by models in that unit" - every model, not just
those with some ability, so unlike Ferocious Rage this one does NOT need a
per-model check. An attached unit (19.01) is one unit, so a Leader inside it
is buffed along with its bodyguards, which is what the rule says.
"""

import copy

from game.squad import edge_distance
from game.weapons import MELEE

SPIRIT_OF_GORK_RANGE_IN = 12.0
SPIRIT_OF_GORK_STRENGTH_BONUS = 1


def unit_has_spirit_of_gork(squad):
    """True while at least one live model with the ability is in the unit -
    rule 19.04's "while a model that has it is still alive" reading, used by
    every other datasheet ability here."""
    if squad is None:
        return False
    return any(m.profile.spirit_of_gork for m in squad.models if not m.is_dead())


def spirit_of_gork_adjusted_weapon(weapon, squad):
    """+1 Strength, and [LETHAL HITS] on a 6, for melee weapons of a unit
    currently under the effect.

    Modeled as a real characteristic change on a shallow copy - the shared
    WeaponProfile instance is never mutated, same reasoning as
    get_stuck_in_adjusted_weapon()/waaagh_melee_adjusted_weapon(). Granting
    [LETHAL HITS] never removes it from a weapon that already had it."""
    if weapon.weapon_type != MELEE or squad is None:
        return weapon
    strength = getattr(squad, "spirit_of_gork_strength", False)
    lethal = getattr(squad, "spirit_of_gork_lethal", False)
    if not strength and not lethal:
        return weapon
    boosted = copy.copy(weapon)
    if strength:
        boosted.strength += SPIRIT_OF_GORK_STRENGTH_BONUS
    if lethal:
        boosted.lethal_hits = True
    return boosted


class SpiritOfGorkController:
    """Resolves the ability once per Kill Rig at the start of each Fight
    phase. main.py drives it from its own phase-change block."""

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 all_tokens=None, auto_players=()):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.auto_players = set(auto_players)
        self._pending = None      # context while the D6 is on the table
        self._pending_mortal = None  # context while the D3 mortal-wound roll is
        self._resolved_this_phase = set()

    # ---------------------------------------------------------------- state

    @property
    def is_busy(self):
        return self._pending is not None or self._pending_mortal is not None

    def reset_phase(self, squads=()):
        """Clears both the "until the end of the phase" buff and the
        once-per-phase bookkeeping. Takes the squads explicitly so a caller
        that only tracks live tokens can still clear a unit that has since
        embarked."""
        for squad in squads:
            squad.spirit_of_gork_strength = False
            squad.spirit_of_gork_lethal = False
        self._resolved_this_phase = set()
        self._pending = None
        self._pending_mortal = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    # ------------------------------------------------------------ targeting

    def eligible_targets(self, rig_squad):
        """"one friendly ORKS unit within 12\" of this model" - friendly
        means same owner, and this engine reads ORKS off the `orks`
        UnitProfile flag (see UnitProfile.orks' own note). The Kill Rig's own
        unit is not excluded by the rule text, so it isn't excluded here."""
        if rig_squad is None or not unit_has_spirit_of_gork(rig_squad):
            return []
        alive = [m for m in rig_squad.models if not m.is_dead()]
        if not alive:
            return []
        seen, out = set(), []
        for token in self.all_tokens:
            squad = getattr(token, "squad", None)
            if squad is None or id(squad) in seen:
                continue
            if squad.owner != rig_squad.owner:
                continue
            if not any(m.profile.orks for m in squad.models if not m.is_dead()):
                continue
            if not any(
                edge_distance(rig, m) <= SPIRIT_OF_GORK_RANGE_IN
                for rig in alive for m in squad.models if not m.is_dead()
            ):
                continue
            seen.add(id(squad))
            out.append(squad)
        return out

    @staticmethod
    def _strength_key(squad):
        """"the strongest unit (points)" - a unit with no published cost
        sorts last rather than blocking the choice (Squad.points is None for
        a faction with no points list, see game/factions/points.py)."""
        return (squad.points is None, -(squad.points or 0), squad.name)

    def strongest(self, squads, caster=None):
        """The deterministic AI pick: the highest-points OTHER unit, falling
        back to the caster's own unit when there is no other eligible one.

        Explicit user instruction ("aendere auf staerkste andere einheit,
        wenn keine da ist, sich selbst"). The caster's own unit stays a legal
        target either way - the rule does not exclude it, and a human keeps
        it in the prompt - this only decides which one the AI reaches for.
        Worth being explicit about because the Kill Rig costs 145 points and
        so would otherwise win its own ranking most of the time."""
        if not squads:
            return None
        others = [s for s in squads if s is not caster]
        return sorted(others or squads, key=self._strength_key)[0]

    # ------------------------------------------------------------ resolving

    def start_of_fight_phase(self, rig_squads):
        """Offer/resolve for the first Kill Rig that still has one pending.
        Returns True if it took over the dice, so the caller knows to wait."""
        if self.is_busy or self.dice_manager is None:
            return self.is_busy
        for rig in rig_squads:
            if id(rig) in self._resolved_this_phase:
                continue
            targets = self.eligible_targets(rig)
            if not targets:
                self._resolved_this_phase.add(id(rig))
                continue
            self._resolved_this_phase.add(id(rig))
            if rig.owner in self.auto_players:
                self._begin_roll(rig, self.strongest(targets, caster=rig))
                return True
            if self.decision_manager is None:
                return False
            options = [
                (f"Spirit of Gork -> {t.name}", (lambda t=t: self._begin_roll(rig, t)))
                for t in sorted(targets, key=self._strength_key)
            ]
            options.append(("Decline", lambda: None))
            self.decision_manager.request(
                rig.owner,
                f"{rig.name}: Spirit of Gork (Psychic) - buff one friendly ORKS unit within 12\"? "
                f"(on a 1 this model suffers D3 mortal wounds)",
                options,
            )
            return True
        return False

    def _begin_roll(self, rig, target):
        self._pending = {"rig": rig, "target": target}
        self.dice_manager.roll(
            count=1, sides=6,
            label=f"Spirit of Gork: {rig.name} -> {target.name}",
            target_name=target.name,
        )

    def on_dice_acknowledged(self):
        """Drives both steps - the D6, then (only on a 1) the D3."""
        if self._pending_mortal is not None:
            self._finish_mortal()
            return True
        if self._pending is None:
            return False
        values = self.dice_manager.last_values or []
        roll = values[0] if values else 1
        ctx, self._pending = self._pending, None
        rig, target = ctx["rig"], ctx["target"]
        if roll == 1:
            self._log(f"Spirit of Gork ({rig.name}): rolled a 1 - the spirits turn on it.")
            self._pending_mortal = {"rig": rig}
            self.dice_manager.roll(
                count=1, sides=3,
                label=f"Spirit of Gork backlash: D3 mortal wounds to {rig.name}",
                target_name=rig.name,
            )
            return True
        target.spirit_of_gork_strength = True
        if roll == 6:
            target.spirit_of_gork_lethal = True
            self._log(
                f"Spirit of Gork ({rig.name}): rolled a 6 - {target.name}'s melee weapons get "
                f"+1 Strength and [LETHAL HITS] until the end of the phase."
            )
        else:
            self._log(
                f"Spirit of Gork ({rig.name}): rolled a {roll} - {target.name}'s melee weapons get "
                f"+1 Strength until the end of the phase."
            )
        return True

    def _finish_mortal(self):
        ctx, self._pending_mortal = self._pending_mortal, None
        rig = ctx["rig"]
        values = self.dice_manager.last_values or []
        wounds = values[0] if values else 1
        # A single-model unit, so there is nothing to allocate between -
        # the mortal wounds land on the Kill Rig itself (rule 06.02's choice
        # only exists where a unit has more than one model).
        model = next((m for m in rig.models if not m.is_dead()), None)
        if model is not None:
            model.current_wounds = max(0, model.current_wounds - wounds)
        self._log(
            f"Spirit of Gork backlash: {rig.name} suffers {wounds} mortal wound(s)"
            + (f" ({model.current_wounds}/{model.profile.wounds} wounds)." if model is not None else ".")
        )
