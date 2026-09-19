"""Kill Rig's Warpath (2026-09 Ork codex, stage E3e).

RULE (verbatim, rules/orks/Kill Rig.md):
  "Warpath (psychic level 1): In the Fight phase, when this unit is selected to
   fight, if this unit is not battle-shocked, you can make a psychic roll for
   this unit by rolling one D6. If you do:
   - On a 1, this unit is battle-shocked.
   - This unit's melee attacks have [Lethal Hits] and [Psychic]."

WHERE IT HANGS: "when this unit is selected to fight" is
FightController._start_fighting(), the instant Rokkit Charge and the Plasmacyte
are offered at. "In the Fight phase" is bare, so both players' Fight phases.

THE ROLL is game/psychic_roll.py: the not-battle-shocked gate, the Unstable
Energies budget (psychic level 1 against the Kill Rig's psyker level 1, shared
with Beastscent for the battle round), and the shock on a 1. The effect lands on
every roll (the plan's reading), so use() sets the grant before the die is read.

THE GRANT is a Squad flag for the phase (warpath_active, reset in main.py's
per-phase block with Rokkit Charge's), read in the fight adjuster chain: a copy
of every melee weapon with [LETHAL HITS] and [PSYCHIC]. [PSYCHIC] on a MELEE
attack is rule 24.29's hit-modifier drop, which game/fight.py's _hit_modifiers()
did not read until this stage because no melee weapon printed the keyword - it
now reads the ADJUSTED weapon. A damaged Kill Rig swinging under Warpath ignores
its own Damaged -1.

ONE DICE SLOT. The D6 is on the table right after selection; a human cannot pick
a weapon before acknowledging it, and the AI stops after select_to_fight() while
it is pending (ai/agent_driver.py's _handle_fight) - otherwise its Hit roll would
replace this one.

"You can" - a human is asked; the AI answers through an injected verdict
(ai/agent_driver.py's warpath_verdict(), 0 API calls).
"""

import copy

from game import ai_mode
from game.squad import unit_wide_ability
from game.weapons import MELEE

WARPATH_NAME = "Warpath"
WARPATH_PSYCHIC_LEVEL = 1
ROLL_LABEL = "Make the psychic roll (Warpath)"
DECLINE_LABEL = "Decline"


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "warpath"))


def is_active(squad):
    return bool(getattr(squad, "warpath_active", False))


def adjusted_weapon(weapon, squad):
    """[LETHAL HITS] and [PSYCHIC] on a melee weapon while the grant is up. A
    copy - the shared WeaponProfile instance is never mutated."""
    if weapon is None or getattr(weapon, "weapon_type", None) != MELEE or not is_active(squad):
        return weapon
    granted = copy.copy(weapon)
    granted.lethal_hits = True
    granted.psychic = True
    return granted


def reset_phase(squads=()):
    for squad in squads or ():
        if getattr(squad, "warpath_active", False):
            squad.warpath_active = False


class WarpathController:
    """The offer, the roll and the grant. The Weirdboy prints the same frame under
    the same name with ANOTHER effect (game/weirdboy_warpath.py), so what differs
    between the two is these three class attributes and nothing else: which
    printed flag carries the ability, which Squad flag holds the grant, and the
    words that describe it."""
    ABILITY_FLAG = "warpath"
    ACTIVE_FLAG = "warpath_active"
    EFFECT_TEXT = "its melee attacks have [LETHAL HITS] and [PSYCHIC]"

    def __init__(self, psychic_roll, decision_manager=None, game_log=None, auto_players=(), verdict=None):
        self.psychic_roll = psychic_roll
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self.verdict = verdict  # callable(squad) -> bool, the AI's rule; injected (game/ must not import ai/)

    def has_ability(self, squad):
        return squad is not None and bool(unit_wide_ability(squad, self.ABILITY_FLAG))

    def can_use(self, squad):
        # No "not already active" term: a use spends the unit's whole psyker
        # level for the battle round, so can_roll() refuses first - a gate term
        # that can never be the one that holds is a dead branch.
        return (self.has_ability(squad) and self.psychic_roll is not None
                and self.psychic_roll.can_roll(squad, WARPATH_PSYCHIC_LEVEL))

    def offer(self, squad):
        """Called from FightController._start_fighting()."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players:
            if self.verdict is not None and not self.verdict(squad):
                if self.game_log is not None:
                    self.game_log.add("%s does not use %s." % (squad.name, WARPATH_NAME))
                return False
            return self.use(squad)
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            squad.owner,
            "%s: %s (psychic level %d) - %s; roll one D6, on a 1 it is battle-shocked?"
            % (squad.name, WARPATH_NAME, WARPATH_PSYCHIC_LEVEL, self.EFFECT_TEXT),
            [(ROLL_LABEL, lambda s=squad: self.use(s)), (DECLINE_LABEL, lambda: None)],
        )
        return True

    def use(self, squad):
        if not self.can_use(squad):
            return False
        setattr(squad, self.ACTIVE_FLAG, True)
        if self.game_log is not None:
            self.game_log.add("%s uses %s: %s." % (squad.name, WARPATH_NAME, self.EFFECT_TEXT))
        self.psychic_roll.roll(squad, WARPATH_NAME, WARPATH_PSYCHIC_LEVEL)
        return True

    def reset_phase(self, squads=()):
        reset_phase(squads)
