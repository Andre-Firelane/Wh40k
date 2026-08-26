"""Orks army rule: Waaagh!, as supplied by the user (not a rule from the
generic 40k core rulebook, so it lives in its own module - same reasoning as
game/greater_good.py for the T'au army rule).

RULE: if your Army Faction is Orks, once per battle, at the start of your
Command phase, you can call a Waaagh! If you do, until the start of your
next Command phase, it's active for your army and:
  - units with this ability are eligible to declare a charge in a turn they
    Advanced (NOT Fell Back - unlike Stormboyz' own Full Throttle, which
    covers both, this ability's text names only Advance).
  - add 1 to the Strength and Attacks characteristics of melee weapons
    equipped by models with this ability.
  - models with this ability have a 5+ invulnerable save.

No per-model Army Faction tracking exists in this engine (documented gap,
same as game/retaliation_cadre.py's own note on Bonded Heroes) - applies
unconditionally to any model with the `waaagh` UnitProfile flag, since only
Ork datasheets set it, rather than gating on "is this army's Faction
actually Orks".

Warboss's own datasheet ability "Da Biggest and da Best" (add 4 more to the
Attacks characteristic of this model's own melee weapons, same "while
active" gate) stacks on top of the above and is folded into the same
waaagh_extra_attacks() function via the `waaagh_biggest_and_best`
UnitProfile flag - see that function's own note.

Warboss in Mega Armour's own "Dead Brutal" (this model's melee weapon has a
Damage characteristic of 3 while active - an ABSOLUTE override, not a
bonus) is folded into waaagh_melee_adjusted_weapon() via the
`waaagh_dead_brutal_damage` UnitProfile flag, same gate again - see that
function's own note."""

import copy

from game.squad import unit_wide_ability
from game.thresholds import parse_threshold
from game.turn import PHASE_COMMAND
from game.weapons import MELEE

WAAAGH_INVULNERABLE_SAVE = "5+"
WAAAGH_MELEE_STRENGTH_BONUS = 1
WAAAGH_MELEE_ATTACKS_BONUS = 1
WAAAGH_BIGGEST_AND_BEST_ATTACKS_BONUS = 4  # Warboss's own "Da Biggest and da Best" (user-supplied, not a core rule): on top of the +1 above, while active
WAAAGH_KRUMPIN_TIME_FEEL_NO_PAIN = "5+"  # Meganobz's own "Krumpin' Time" (user-supplied, not a core rule)


def qualifying_players(squads):
    """Which players' armies count as ORKS for this rule.

    The same derivation game/battle_focus.py's own qualifying_players() uses,
    and for the same reason it gives: this engine has no army-faction
    declaration, so "your Army Faction is ORKS" is read as "this player's army
    contains units with the Waaagh! ability". Derived rather than configured,
    because a config constant is the thing someone forgets to update - and the
    failure mode of forgetting is a whole army rule quietly doing nothing, or
    (as reported) firing for an army that does not have it.

    Meant to be called ONCE, when the armies are complete: army faction is
    fixed at list-building and does not stop being ORKS when the last Boy
    dies."""
    return frozenset(
        squad.owner for squad in squads
        if squad.owner is not None
        and any(getattr(m.profile, "waaagh", False) for m in getattr(squad, "models", ()) or ())
    )


class WaaaghController:
    """Tracks, per player, whether a Waaagh! has been called yet this
    battle (`used_players` - permanent, once per battle) and whether one is
    currently active (`active_players` - toggles off again at the start of
    the caller's own next Command phase, see expire_for())."""

    def __init__(self, game_log=None):
        self.game_log = game_log
        self.used_players = set()
        self.active_players = set()
        # Whose army rule this actually IS. Set once by main.py from the built
        # armies (qualifying_players below).
        #
        # None means "nobody has told me", and only THAT lifts the restriction -
        # so every existing caller and test that never sets it behaves exactly
        # as before. An EMPTY set is a real answer meaning "no player fields
        # Orks", which is precisely the reported case (a Necron army against
        # Aeldari) and must therefore refuse. Writing this as a plain truthiness
        # test is the obvious mistake and it silently re-opens the bug: an empty
        # frozenset is falsy.
        #
        # Real bug, user report: "die necrons haben soeben einen waagh
        # ausgerufen. das koennen nur orks." can_call() checked once-per-battle
        # and the phase, and nothing else - which was safe only for as long as
        # Player 2 was ALWAYS Orks. The moment Player 2's army became
        # switchable, ai/agent_driver.py's _maybe_call_waaagh() (pure policy:
        # "call it in battle round 2") happily called one for a Necron army.
        #
        # Gated HERE rather than in the AI, so the human's button is covered by
        # the same answer: the engine must not offer what it does not want
        # chosen.
        self.orks_players = None
        self.on_called = None  # optional callable(player) - see main.py's WaaaghNoticeOverlay wiring, same pattern as StratagemController.on_stratagem_used

    def can_call(self, player, turn_tracker):
        if self.orks_players is not None and player not in self.orks_players:
            return False   # not an ORKS army - see orks_players
        if player in self.used_players:
            return False
        if turn_tracker is not None and (turn_tracker.phase != PHASE_COMMAND or turn_tracker.turn_owner != player):
            return False
        return True

    def call(self, player, turn_tracker=None):
        if not self.can_call(player, turn_tracker):
            return False
        self.used_players.add(player)
        self.active_players.add(player)
        if self.game_log is not None:
            self.game_log.add(f"{player} calls a WAAAGH!")
        if self.on_called is not None:
            self.on_called(player)
        return True

    def expire_for(self, player):
        """Called at the start of `player`'s own Command phase (see
        main.py's advance_turn_phase(), same hook as e.g.
        support_turret_controller.expire_for()) - "until the start of your
        next Command phase" is exactly this instant. A no-op if it wasn't
        active (the overwhelmingly common case: most Command phases aren't
        the start of a player's NEXT one after calling it)."""
        was_active = player in self.active_players
        self.active_players.discard(player)
        if was_active and self.game_log is not None:
            self.game_log.add(f"{player}'s WAAAGH! subsides.")

    def is_active(self, player):
        return player in self.active_players


def squad_waaagh_active(squad, waaagh):
    """Whether `squad` currently benefits from an active Waaagh! - both the
    unit's own ability and the controller's per-owner active state must hold.

    Read as a unit-wide ability (rule 19.04) rather than off a representative
    model: an attached unit (19.01) is no longer homogeneous, and a Warboss
    joining a Boyz mob must not decide the whole mob's Waaagh! eligibility by
    happening to be (or not be) models[0]."""
    if waaagh is None or not squad.models:
        return False
    if not unit_wide_ability(squad, "waaagh"):
        return False
    return waaagh.is_active(squad.owner)


def waaagh_melee_adjusted_weapon(weapon, pairs, waaagh):
    """"Add 1 to the Strength and Attacks characteristics of melee weapons
    equipped by models... with this ability" - modeled as an actual
    characteristic change (shallow copy, same reasoning as
    bonded_heroes_adjusted_weapon()/starscythe_adjusted_weapon() - the
    shared WeaponProfile instance is never mutated), only for MELEE weapons
    (the rule text says "melee weapons" explicitly - a ranged attack, even
    from a model with this ability, is untouched).

    Whether the group counts as a Waaagh! attack is decided from its
    representative fighter (pairs[0][0]), same simplification as the other
    two. The ATTACKS bonus is applied separately, at the point each weapon
    group's total attack DICE COUNT is computed (see
    waaagh_extra_attacks()) - by the time this function's caller has a
    rolled hit/wound count in hand, "how many attacks" has already been
    decided, so this only ever touches Strength here.

    Also folds in Warboss in Mega Armour's own "Dead Brutal" (while active,
    "this model's 'uge Choppa has a Damage characteristic of 3" - an
    ABSOLUTE override, not a bonus, unlike every other Waaagh!-related
    adjustment in this module) via the `waaagh_dead_brutal_damage`
    UnitProfile flag - same fighter_model/active check already computed
    above answers both, so one function covers both rather than a second
    near-duplicate one."""
    if weapon.weapon_type != MELEE:
        return weapon
    fighter_model = pairs[0][0] if pairs else None
    if fighter_model is None or not fighter_model.profile.waaagh:
        return weapon
    if waaagh is None or not waaagh.is_active(fighter_model.squad.owner):
        return weapon
    boosted = copy.copy(weapon)
    boosted.strength = weapon.strength + WAAAGH_MELEE_STRENGTH_BONUS
    if fighter_model.profile.waaagh_dead_brutal_damage is not None:
        boosted.damage = fighter_model.profile.waaagh_dead_brutal_damage
    return boosted


def waaagh_extra_attacks(pairs, waaagh):
    """The Attacks-characteristic half of the same melee boost (see
    waaagh_melee_adjusted_weapon()'s own note on why it's split out) - "add
    1 to the Attacks characteristic" per model, so this returns
    len(pairs) extra attack dice for the whole group, meant to be added the
    same way extra_attack_dice() already is at every total_attacks
    computation in game/fight.py. Melee-only, same as the Strength half -
    pairs here are always melee (weapon,model) tuples in fight.py's own
    callers, so no separate weapon_type check is needed like the Strength
    function has (that one is also reachable in principle from a shared
    helper, this one currently is not).

    Also folds in Warboss's own "Da Biggest and da Best" (add 4 more to the
    same characteristic, gated on the same "Waaagh! active for this model's
    owner" condition, just a per-model extra rather than an army-wide one) -
    a single fighter_model check already answers both, so one function
    covers both rather than a second near-duplicate one."""
    fighter_model = pairs[0][0] if pairs else None
    if fighter_model is None or not fighter_model.profile.waaagh:
        return 0
    if waaagh is None or not waaagh.is_active(fighter_model.squad.owner):
        return 0
    bonus = WAAAGH_MELEE_ATTACKS_BONUS
    if fighter_model.profile.waaagh_biggest_and_best:
        bonus += WAAAGH_BIGGEST_AND_BEST_ATTACKS_BONUS
    return len(pairs) * bonus


# effective_invulnerable_save() used to live here, while the Waaagh! was the
# only source that could grant one. It now folds two factions' grants together
# and lives in game/invulnerable_save.py - see that module's docstring.
# WAAAGH_INVULNERABLE_SAVE above stays here, next to the rest of this rule.


def effective_feel_no_pain(model, waaagh):
    """Meganobz's own "Krumpin' Time" ability (user-supplied, not a core
    rule): "While the Waaagh! is active for your army, models in this unit
    have the Feel No Pain 5+ ability" - same "better of what's already
    printed, never worse" principle as effective_invulnerable_save() above
    (a model that already prints a better FNP threshold, should one ever be
    paired with this ability, keeps it). Returns a threshold STRING ("5+",
    "-", or the model's own unchanged), matching UnitProfile.feel_no_pain's
    own convention, so game/feel_no_pain.py's FeelNoPainRoll keeps parsing
    it with parse_threshold() exactly as before.

    Threaded through DamageAllocationSession/MortalWoundAllocationSession/
    DevastatingWoundAllocationSession (game/damage_resolution.py), wherever
    their owning FightController/ShootingController already carries a
    `self.waaagh` for effective_invulnerable_save() above - i.e. normal
    shooting/fight damage, devastating wounds, and hazard mortal wounds.
    NOT threaded into game/crushing_impact.py, game/deadly_demise.py,
    game/explosives.py or game/hazard.py's own MortalWoundAllocationSession
    calls (none of those controllers are given a WaaaghController at all) -
    a documented, narrower version of the same "no per-model Army Faction
    tracking" style gap noted elsewhere in this module: a Meganobz unit
    taking mortal wounds from Crushing Impact/Deadly Demise/Explosives/a
    Hazardous weapon still gets its own model.profile.feel_no_pain
    unconditionally (i.e. none, since Krumpin' Time isn't a static value),
    not the Waaagh!-conditional 5+."""
    own = model.profile.feel_no_pain
    if waaagh is None or not model.profile.krumpin_time or not waaagh.is_active(model.squad.owner):
        return own
    own_threshold = parse_threshold(own)
    krumpin_threshold = parse_threshold(WAAAGH_KRUMPIN_TIME_FEEL_NO_PAIN)
    if own_threshold is not None and own_threshold <= krumpin_threshold:
        return own  # own FNP is already at least as good (lower threshold = better)
    return WAAAGH_KRUMPIN_TIME_FEEL_NO_PAIN
