"""The Anhrathe abilities that are one predicate each - one module, not six.

Six small rules across four Corsair datasheets. Each is a few lines, each hangs
on a seam that already exists, and none of them shares state with the others.
Six modules would be six docstrings repeating "this is an Anhrathe ability";
one module keeps the reasoning where the rules are and costs nothing, which is
the same call game/mortal_wound_abilities.py records for its four.

The two that DO carry state - Kharseth's riven mark and Prince Yriel's
redeployment step - have their own modules, because state is what makes a rule
worth isolating.

RULES (printed, word for word):

  Piratical Raiders   "At the start of the battle, select one unit from your
      opponent's army. Weapons equipped by models in this unit have the
      [LETHAL HITS] and [PRECISION] abilities while targeting that unit."

  Piratical Hero      "While this model is leading a unit, each time a model in
      that unit makes an attack, that attack has the [SUSTAINED HITS 1] ability
      and add 1 to the Hit roll."

  Channeller Stones   "Once per turn, the first time a saving throw is failed
      for the bearer's unit, change the Damage characteristic of that attack
      to 0."

  Faolchu             "Ranged weapons equipped by models in the bearer's unit
      have the [IGNORES COVER] ability."

  Mistshield          "The bearer has a 4+ invulnerable save."

  Aethersense         "Enemy units that are set up on the battlefield from
      Reserves cannot be set up within 12" of this model."

MISTSHIELD is not here at all - it is a flat invulnerable save, so it is one
fold in game/invulnerable_save.py beside the Shimmershield, the Dispersion
Shield and the Forceshield, and a module would only forward to it.
"""
import copy

from game.attached_units import leader_ability

PIRATICAL_RAIDERS_LABEL = "Piratical Raiders"
PIRATICAL_HERO_LABEL = "Piratical Hero"
CHANNELLER_STONES_LABEL = "Channeller Stones"
FAOLCHU_LABEL = "Faolchu"
AETHERSENSE_LABEL = "Aethersense"

#: "cannot be set up within 12 inches of this model".
AETHERSENSE_RANGE_IN = 12.0


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def _unit_has(squad, flag):
    return any(getattr(m.profile, flag, False) for m in _living(squad))


# --- Piratical Hero ---------------------------------------------------------

def piratical_hero_applies(squad):
    """"While this model is LEADING a unit" - 24.22's question, so Prince Yriel
    standing alone grants nothing and a bodyguard never carries it."""
    return bool(squad is not None and leader_ability(squad, "piratical_hero"))


def piratical_hero_adjusted_weapon(weapon, squad):
    """The [SUSTAINED HITS 1] half. The +1 to Hit is a MODIFIER and lives in
    _hit_modifiers(); only a keyword grant belongs in the adjuster chain, where
    _crit_note() can read it at roll time.

    NEVER a downgrade, the standing guard for every grant of this keyword."""
    if weapon is None or not piratical_hero_applies(squad):
        return weapon
    if getattr(weapon, "sustained_hits", 0) >= 1:
        return weapon
    adjusted = copy.copy(weapon)
    adjusted.sustained_hits = 1
    return adjusted


# --- Faolchu ----------------------------------------------------------------

def faolchu_applies(squad):
    """"the BEARER'S UNIT", so 19.04's any() shape - one Corsair carrying it
    gives the whole unit [IGNORES COVER]."""
    return _unit_has(squad, "faolchu")


def faolchu_adjusted_weapon(weapon, squad):
    """RANGED weapons only - the printed text says so, and a melee weapon with
    [IGNORES COVER] would be meaningless anyway, which is exactly why the
    restriction is easy to drop by accident."""
    if weapon is None or not faolchu_applies(squad):
        return weapon
    if getattr(weapon, "ignores_cover", False):
        return weapon
    from game.weapons import RANGED
    if getattr(weapon, "weapon_type", None) != RANGED:
        return weapon
    adjusted = copy.copy(weapon)
    adjusted.ignores_cover = True
    return adjusted


# --- Channeller Stones ------------------------------------------------------

def channeller_stones_available(squad):
    """"Once per turn, the FIRST time a saving throw is failed for the bearer's
    unit" - so the resource is the turn, held on the squad like every other
    per-turn unit state here."""
    return (_unit_has(squad, "channeller_stones")
            and not getattr(squad, "channeller_stones_used_this_turn", False))


def spend_channeller_stones(squad):
    """Marks it spent and reports whether it was available. The caller applies
    the effect - "change the Damage characteristic of that attack to 0" - which
    is a damage amount, not a save, so it belongs at the damage step."""
    if not channeller_stones_available(squad):
        return False
    squad.channeller_stones_used_this_turn = True
    return True


def reset_channeller_stones(squads=()):
    for squad in squads or ():
        squad.channeller_stones_used_this_turn = False


# --- Aethersense ------------------------------------------------------------

def aethersense_blocks(point, all_tokens=(), arriving_player=None):
    """Whether a Reserves arrival at `point` is refused.

    "ENEMY units set up from Reserves" - so it blocks the opponent of whoever
    carries it, which is why the arriving player has to be passed in. Measured
    to the MODEL, as the printed text says ("within 12\" of this model"), not
    to its unit."""
    x, y = point
    for token in all_tokens or ():
        if token.is_dead() or not getattr(token.profile, "aethersense", False):
            continue
        squad = getattr(token, "squad", None)
        if squad is None or (arriving_player is not None
                             and squad.owner == arriving_player):
            continue
        if ((token.x_in - x) ** 2 + (token.y_in - y) ** 2) ** 0.5 <= AETHERSENSE_RANGE_IN:
            return True
    return False


# --- Piratical Raiders ------------------------------------------------------

class PiraticalRaidersController:
    """The Voidscarred's start-of-battle mark. State, but only one field, and
    it belongs with the ability that reads it."""

    def __init__(self, game_log=None, decision_manager=None, auto_players=()):
        self.game_log = game_log
        self.decision_manager = decision_manager
        self.auto_players = set(auto_players)
        self._marked = {}       # player -> the enemy squad chosen

    def applies(self, squad):
        return _unit_has(squad, "piratical_raiders")

    def mark(self, bearer_squad, target):
        if bearer_squad is None or target is None:
            return False
        self._marked[bearer_squad.owner] = target
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s marks %s - its weapons have [LETHAL HITS] and [PRECISION] "
                "against that unit for the battle."
                % (PIRATICAL_RAIDERS_LABEL, bearer_squad.name, target.name))
        return True

    def marked_by(self, player):
        return self._marked.get(player)

    def grants(self, attacking_squad, target_squad):
        """The grant is per (bearer unit, marked unit): only the Voidscarred
        get it, and only against the unit THEY chose."""
        if not self.applies(attacking_squad) or target_squad is None:
            return False
        return self._marked.get(attacking_squad.owner) is target_squad

    def adjusted_weapon(self, weapon, attacking_squad, target_squad):
        """[LETHAL HITS] and [PRECISION] together - one copy, both keywords, so
        neither can be granted without the other."""
        if weapon is None or not self.grants(attacking_squad, target_squad):
            return weapon
        if getattr(weapon, "lethal_hits", False) and getattr(weapon, "precision", False):
            return weapon
        adjusted = copy.copy(weapon)
        adjusted.lethal_hits = True
        adjusted.precision = True
        return adjusted

    def start(self, pregame_controller=None, on_done=None):
        """PregameController's pre-battle step protocol. "At the start of the
        battle" - so it runs in Resolve Pre-battle Abilities, like the
        Wraithlord's Fated Hero, and has no ordering constraint against it."""
        squads = []
        for token in (getattr(getattr(pregame_controller, "game_state", None),
                              "tokens", None) or ()):
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in squads:
                squads.append(squad)
        for bearer in [s for s in squads if self.applies(s)]:
            if self.marked_by(bearer.owner) is not None:
                continue
            enemies = [s for s in squads if s.owner != bearer.owner and _living(s)]
            if not enemies:
                continue
            if bearer.owner in self.auto_players or self.decision_manager is None:
                self.mark(bearer, self._pick(enemies))
                continue
            self.decision_manager.request(
                bearer.owner,
                "%s: %s - which enemy unit does it hunt this battle?"
                % (PIRATICAL_RAIDERS_LABEL, bearer.name),
                [(e.name, (lambda b=bearer, e=e: self._answer(b, e, on_done)))
                 for e in enemies])
            return True
        if on_done is not None:
            on_done()
        return False

    def _pick(self, enemies):
        """Deterministic for the AI: the biggest unit, ties broken by name -
        so there is no ai/ path and nothing can flicker between two equals."""
        return max(enemies, key=lambda s: (len(_living(s)), s.name))

    def _answer(self, bearer, target, on_done):
        self.mark(bearer, target)
        if on_done is not None:
            on_done()
        return True
