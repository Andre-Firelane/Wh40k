"""Aspect Host Stratagem: Preternatural Precision (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Aspect Host.md):
  WHEN:   Your Shooting phase.
  TARGET: One ASPECT WARRIORS unit from your army that has not been selected to
          shoot this phase.
  EFFECT: Each time you use this Stratagem, you can remove one Aspect Shrine
          token your unit has (see datasheets). Then, select one of the
          following abilities, or select two of the following abilities if you
          removed an Aspect Shrine token during this usage of this Stratagem:
          [IGNORES COVER], [LETHAL HITS], [SUSTAINED HITS 1]. Until the end of
          the phase, ranged weapons equipped by models in your unit have the
          selected abilities.
  RESTRICTIONS: none printed.

THE FIRST RULE TO SPEND AN ASPECT SHRINE TOKEN ON SOMETHING OTHER THAN A DIE.
Those tokens existed for one purpose - game/unmodified_six_controller.py's
"change a die to an unmodified 6" - and the resource half is already separate
from that use (aspect_shrine.unspent_tokens()/spend()), so this needs no new
bookkeeping. What it does need is to NOT go through aspect_shrine.usable(),
which asks the per-MODEL question that rule cares about ("excluding CHARACTER
models"): this card spends a token the UNIT has, with no model involved.

ASPECT WARRIORS ONLY - NO AVATAR. Three of this detachment's six Stratagems say
"ASPECT WARRIORS or AVATAR OF KHAINE"; this one does not, and that is not an
oversight on the card: the Avatar has no Aspect Shrine tokens to spend, so half
this Stratagem could never apply to it. Its own test line, since the pairing
next door makes the omission look like a typo.

"YOU CAN REMOVE ONE TOKEN" IS OPTIONAL, and the choice is real in both
directions: spending buys a second ability now, at the cost of a die-change
later in the battle. So it is a genuine two-branch decision rather than
something to auto-resolve - the opposite call from "any or all modifiers" in
Warrior Focus next door, and for the opposite reason (there, no branch was ever
worse; here, both are live).

THE THREE ABILITIES ARE GRANTS, NEVER UPGRADES. A weapon that already prints
[SUSTAINED HITS 2] keeps its 2 - "have the [SUSTAINED HITS 1] ability" grants
the ability, it does not set the value. The same two guards
game/ritual_butchery.py and Kauyon's Patient Hunter both carry.

RANGED ONLY, as printed, and on a COPY: a WeaponProfile CLASS is shared by
every model in the game carrying that gun.

THE AI DECLINES (standing Aeldari instruction).
"""
import copy

from game import aeldari_detachments, ai_mode, aspect_shrine, detachment_gate
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING
from game.weapons import RANGED

PRETERNATURAL_PRECISION_NAME = "Preternatural Precision"
PRETERNATURAL_PRECISION_CP = 1

IGNORES_COVER = "ignores_cover"
LETHAL_HITS = "lethal_hits"
SUSTAINED_HITS = "sustained_hits"

#: The three the card offers, in its own order.
PRETERNATURAL_PRECISION_ABILITIES = (IGNORES_COVER, LETHAL_HITS, SUSTAINED_HITS)

#: "[SUSTAINED HITS 1]" - the value granted, never an upgrade of a higher one.
PRETERNATURAL_PRECISION_SUSTAINED = 1

#: ASPECT WARRIORS only - no AVATAR OF KHAINE, which has no tokens to spend.
PRETERNATURAL_PRECISION_KEYWORD = "ASPECT WARRIORS"

SETTING = "ASPECT_HOST_PLAYERS"

_LABELS = {
    IGNORES_COVER: "[IGNORES COVER]",
    LETHAL_HITS: "[LETHAL HITS]",
    SUSTAINED_HITS: "[SUSTAINED HITS 1]",
}


def has_detachment(player):
    return detachment_gate.has_detachment(player, SETTING)


def granted(squad):
    """The abilities this unit was given this phase, as a tuple."""
    return tuple(getattr(squad, "preternatural_precision_abilities", ()) or ())


def adjusted_weapon(weapon, squad):
    """The granted abilities on this unit's RANGED weapons. A COPY, and never
    a downgrade."""
    if weapon is None:
        return weapon
    names = granted(squad)
    if not names:
        return weapon
    if getattr(weapon, "weapon_type", None) != RANGED:
        return weapon              # "RANGED weapons", as printed
    out = None
    if IGNORES_COVER in names and not weapon.ignores_cover:
        out = out if out is not None else copy.copy(weapon)
        out.ignores_cover = True
    if LETHAL_HITS in names and not weapon.lethal_hits:
        out = out if out is not None else copy.copy(weapon)
        out.lethal_hits = True
    if SUSTAINED_HITS in names \
            and PRETERNATURAL_PRECISION_SUSTAINED > weapon.sustained_hits:
        out = out if out is not None else copy.copy(weapon)
        out.sustained_hits = PRETERNATURAL_PRECISION_SUSTAINED
    return out if out is not None else weapon


def eligible_unit(squad):
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return unit_has_datasheet_keyword(squad, PRETERNATURAL_PRECISION_KEYWORD)


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.preternatural_precision_abilities = ()


class PreternaturalPrecisionController:
    """A Shooting-phase panel button, with the token choice and then the
    ability choice."""

    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._pending = {}
        self._stratagem = Stratagem(
            name=PRETERNATURAL_PRECISION_NAME, cp_cost=PRETERNATURAL_PRECISION_CP,
            effect=self._grant,
        )

    def panel_label(self, squad):
        return ("%s (%d CP) - grant [IGNORES COVER], [LETHAL HITS] or "
                "[SUSTAINED HITS 1]"
                % (PRETERNATURAL_PRECISION_NAME, PRETERNATURAL_PRECISION_CP))

    def has_token(self, squad):
        """The UNIT's resource, not a model's - so aspect_shrine.usable() is
        deliberately not asked: that adds the per-model CHARACTER exclusion the
        die-changing rule needs and this one has no model at all."""
        return aspect_shrine.unspent_tokens(squad) > 0

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False               # "YOUR Shooting phase"
        if granted(squad):
            return False
        if not eligible_unit(squad):
            return False
        if self.shooting_controller is not None \
                and self.shooting_controller.active_squad is squad:
            return False               # "has not been selected to shoot"
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad, abilities=None, spend_token=None):
        """`spend_token` None means "ask"; the two-branch choice is real, so it
        is never auto-resolved for a human."""
        if not self.can_use(squad):
            return False
        if spend_token is None:
            if self.has_token(squad) and squad.owner not in self.auto_players \
                    and self.decision_manager is not None:
                self.decision_manager.request(
                    squad.owner,
                    "%s: spend an Aspect Shrine token for a SECOND ability? "
                    "(%d left)"
                    % (PRETERNATURAL_PRECISION_NAME,
                       aspect_shrine.unspent_tokens(squad)),
                    [("Spend a token - two abilities",
                      (lambda s=squad: self.use(s, spend_token=True))),
                     ("Keep the token - one ability",
                      (lambda s=squad: self.use(s, spend_token=False)))],
                    is_stratagem=True,
                )
                return True
            spend_token = False
        wanted = 2 if spend_token else 1
        if abilities is None:
            options = self._combinations(wanted)
            if len(options) > 1 and squad.owner not in self.auto_players \
                    and self.decision_manager is not None:
                self.decision_manager.request(
                    squad.owner,
                    "%s: which %s?" % (PRETERNATURAL_PRECISION_NAME,
                                       "two abilities" if wanted == 2 else "ability"),
                    [(" + ".join(_LABELS[a] for a in combo),
                      (lambda s=squad, combo=combo, t=spend_token:
                       self.use(s, abilities=combo, spend_token=t)))
                     for combo in options],
                    is_stratagem=True,
                )
                return True
            abilities = options[0]
        self._pending[squad.owner] = (squad, tuple(abilities), bool(spend_token))
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _combinations(self, wanted):
        import itertools
        return [tuple(c) for c in
                itertools.combinations(PRETERNATURAL_PRECISION_ABILITIES, wanted)]

    def _grant(self, controller, player, targets):
        squad, abilities, spend_token = self._pending.pop(player, (None, (), False))
        if squad is None:
            return
        if spend_token:
            aspect_shrine.spend(squad)
        squad.preternatural_precision_abilities = tuple(abilities)
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s's ranged weapons gain %s this phase%s."
                % (PRETERNATURAL_PRECISION_NAME, squad.name,
                   " and ".join(_LABELS[a] for a in abilities),
                   " (an Aspect Shrine token spent)" if spend_token else ""))
