"""The Silent King: "Voice of the Triarch" and the three Triarch abilities.

RULES (verbatim, rules/necrons/The Silent King.md):

  "Voice of the Triarch: At the start of the battle round, select one Triarch
   ability (see left). Until the start of the next battle round, this unit has
   that ability."

  "Phaeron of the Stars (Aura): While a friendly NECRONS unit (excluding
   MONSTER units) is within 6" of this unit's Szarekh model, each time a model
   in that unit makes an attack, re-roll a Hit roll of 1 and re-roll a Wound
   roll of 1."

  "Phaeron of the Blades (Aura): While a friendly NECRONS unit (excluding
   MONSTER units) is within 6" of this unit's Szarekh model, you can re-roll
   Charge rolls made for that unit and each time a model in that unit makes a
   melee attack, add 1 to the Strength characteristic of that attack."

  "Relentless March (Aura): While a friendly NECRONS unit (excluding MONSTER
   units) is within 6" of this unit's Szarekh model, add 2" to the Move
   characteristic of models in that unit."

THE SELECTION LIVES ON THE SQUAD, NOT IN THIS CONTROLLER, and that is the whole
reason the folds below stay simple. Each aura is read from a seam that gets a
MODEL or a SQUAD and no controller at all - shooting.py's and fight.py's
hit/wound steps, coldstar.effective_movement_in(), and game/charge_reroll.py.
Threading a controller through any of them would be the "fade a turn_tracker
through eleven call sites" mistake this repo has written up twice. So the
controller owns WHEN the choice changes and `Squad.triarch_ability` carries
WHAT was chosen - the same split as Squad.montka_killing_blow, one stamp and
many readers.

IT IS SAVED. `triarch_ability` is in activation_state.SQUAD_FLAGS: the capture
filters on truthiness and restores with setattr, so a string key round-trips
through a scene snapshot unchanged. This is a CHOICE that lasts a battle round,
not derived state a later pass re-stamps, so losing it to an F9 would silently
change which aura an army is under.

MEASURED FROM THE SZAREKH MODEL, not from the unit. The printed words are
"within 6" of this unit's SZAREKH MODEL", and the unit also contains two
Menhirs that may be anywhere in coherency - measuring from the unit would hand
the aura out from up to a base-width further away, and from the wrong models.

THE SILENT KING'S OWN UNIT IS COVERED BY ITS OWN AURA. The text says "a
friendly NECRONS unit", not "another", and the unit is NECRONS, is within 6" of
its own Szarekh by construction, and is VEHICLE rather than MONSTER. The same
reading Carrier Wave took one stage earlier, and pinned here rather than left
to luck.

THE MONSTER EXCLUSION IS REAL ON THIS ARMY, which is why it is not folded away:
the C'tan Shards are NECRONS MONSTER units, so a C'tan standing beside Szarekh
gets none of the three. Note that the datasheet's FOURTH aura - "The Silent
King", the +1 Leadership one in game/silent_king_leadership.py - prints NO such
exclusion, and that difference is one printed word rather than an oversight.
"""

from game import ai_mode, awakened_dynasty
from game.squad import edge_distance

TRIARCH_AURA_RANGE_IN = 6.0
VOICE_OF_THE_TRIARCH_LABEL = "Voice of the Triarch"

#: "add 2 inches to the Move characteristic of models in that unit".
RELENTLESS_MARCH_BONUS_IN = 2.0

#: "add 1 to the Strength characteristic of that attack" - MELEE only.
PHAERON_OF_THE_BLADES_STRENGTH_BONUS = 1

PHAERON_OF_THE_STARS = "phaeron_of_the_stars"
PHAERON_OF_THE_BLADES = "phaeron_of_the_blades"
RELENTLESS_MARCH = "relentless_march"

#: key -> printed name. ORDERED, because the prompt lists them in the printed
#: order and the AI's deterministic fallback takes a named one from it.
TRIARCH_ABILITIES = (
    (PHAERON_OF_THE_STARS, "Phaeron of the Stars"),
    (PHAERON_OF_THE_BLADES, "Phaeron of the Blades"),
    (RELENTLESS_MARCH, "Relentless March"),
)
TRIARCH_ABILITY_NAMES = dict(TRIARCH_ABILITIES)


def _alive(squad):
    return [m for m in squad.models if not m.is_dead()] if squad else []


def szarekh_models(squad):
    """The living Szarekh model(s) of this unit - the aura's centre."""
    return [m for m in _alive(squad)
            if getattr(m.profile, "voice_of_the_triarch", False)]


def bearer_squads(all_tokens):
    seen, out = set(), []
    for token in all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is None or id(squad) in seen:
            continue
        if szarekh_models(squad):
            seen.add(id(squad))
            out.append(squad)
    return out


def selected_ability(squad):
    """Which Triarch ability this SILENT KING unit chose this battle round."""
    return getattr(squad, "triarch_ability", None)


def is_monster_unit(squad):
    """Rule 19.03's pooling: the exclusion is about the UNIT, so one MONSTER
    model in it excludes the whole unit - which is what "excluding MONSTER
    units" says."""
    return any(getattr(m.profile, "monster", False) for m in _alive(squad))


def aura_active(squad, all_tokens, key):
    """Whether `squad` is under the named Triarch ability right now."""
    if squad is None or not awakened_dynasty.is_necrons_unit(squad):
        return False
    if is_monster_unit(squad):
        return False
    mine = _alive(squad)
    if not mine:
        return False
    for bearer in bearer_squads(all_tokens):
        if bearer.owner != squad.owner:
            continue
        if selected_ability(bearer) != key:
            continue
        for szarekh in szarekh_models(bearer):
            if any(edge_distance(m, szarekh) <= TRIARCH_AURA_RANGE_IN for m in mine):
                return True
    return False


def refresh_active_auras(all_tokens):
    """Stamp `Squad.triarch_auras_active` on every unit on the board, once.

    WHY A FLAG AND NOT A LIVE CALL, and it is the same pair of reasons
    game/plagues.py's `afflicted` gives:

      * COST: aura_active() is a geometry sweep, and one of its four readers is
        coldstar.effective_movement_in(), which runs per MODEL on the movement
        path. Asking it live would re-derive the same distances dozens of times
        a frame.
      * REACH: two of the four readers get a MODEL or a SQUAD and no board at
        all - effective_movement_in() and game/charge_reroll.py. Threading
        all_tokens into either is the "fade a turn_tracker through eleven call
        sites" mistake, and a version that reached only the two readers that
        HAVE the board would be half a rule.

    A FROZENSET OF KEYS RATHER THAN ONE KEY. Two Silent King units cannot both
    be fielded today (EPIC HERO), so the set can hold at most one entry on any
    board this engine can build - but writing it as a set costs nothing and
    means the overlap case has an answer instead of a silent last-writer-wins.

    DERIVED STATE, so it belongs in activation_state.SQUAD_FLAGS_EXCLUDED and
    NOT in SQUAD_FLAGS: this pass re-stamps it every frame, while the CHOICE it
    is derived from (`triarch_ability`) is what a snapshot has to carry."""
    tokens = list(all_tokens or ())
    seen, squads = set(), []
    for token in tokens:
        squad = getattr(token, "squad", None)
        if squad is not None and id(squad) not in seen:
            seen.add(id(squad))
            squads.append(squad)
    for squad in squads:
        squad.triarch_auras_active = frozenset(
            key for key, _name in TRIARCH_ABILITIES
            if aura_active(squad, tokens, key))


def blades_adjusted_weapon(weapon, squad):
    """Phaeron of the Blades' second clause: "+1 to the Strength characteristic
    of that attack", MELEE only.

    A COPY, never a mutation of the class instance - every model carries its
    own WeaponProfile instances and the repo convention is that effects
    copy.copy() rather than write through, or one boosted swing raises the
    Strength of every other bearer of that weapon for the rest of the battle.

    A weapon whose Strength is a DICE NOTATION is left alone: none of the
    melee weapons this aura can reach prints one today, and "add 1 to the
    characteristic" has no defined meaning against a notation that is rolled
    per group. Named rather than silently handled."""
    import copy
    if weapon is None or not is_active(squad, PHAERON_OF_THE_BLADES):
        return weapon
    if getattr(weapon, "strength_notation", None) is not None:
        return weapon
    boosted = copy.copy(weapon)
    boosted.strength = weapon.strength + PHAERON_OF_THE_BLADES_STRENGTH_BONUS
    return boosted


def is_active(squad, key):
    """Whether `squad` is under the named Triarch ability, off the flag above.

    The one question all four seams ask, so none of them can answer it
    differently from the others."""
    return key in getattr(squad, "triarch_auras_active", frozenset())


class VoiceOfTheTriarchController:
    """Asks the choice ONCE per battle round, per SILENT KING unit.

    Shaped like BattleFocusPool.sync_battle_round(): idempotent and driven by
    the round NUMBER rather than by an event, because "the start of the battle
    round" is a moment main.py passes through from several places and a
    listener would fire a different number of times depending on which."""

    def __init__(self, decision_manager=None, game_log=None, game_state=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.auto_players = ai_mode.players(auto_players)
        self._chosen_round = {}      # id(squad) -> battle_round the choice was made for

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    def sync_battle_round(self, battle_round, all_tokens=None):
        """Offer the choice to every Silent King unit that has not made one for
        THIS round yet. Idempotent: safe to call every frame."""
        if not battle_round:
            return False
        tokens = self._tokens() if all_tokens is None else list(all_tokens)
        asked = False
        for squad in bearer_squads(tokens):
            if self._chosen_round.get(id(squad)) == battle_round:
                continue
            self._chosen_round[id(squad)] = battle_round
            asked = self._offer(squad, battle_round) or asked
        return asked

    def _offer(self, squad, battle_round):
        player = squad.owner
        if player in self.auto_players or self.decision_manager is None:
            # Deterministic and free for the AI. Phaeron of the Stars is the
            # pick: it is the only one of the three that pays on EVERY attack
            # the army makes in range, in both phases, without needing the unit
            # to charge or to want to move. The other two are situational, and
            # this engine has no planner input that could tell which turn is
            # which - the same reason the Repair Barge's AI branch takes the
            # unit with the most to recover rather than guessing intent.
            self._choose(squad, PHAERON_OF_THE_STARS, battle_round)
            # False, not the _choose() result: the return value of this and of
            # sync_battle_round() means "a human PROMPT is now open", which is
            # what main.py would have to wait on. The AI opened none.
            return False
        options = [
            (name, (lambda k=key: self._choose(squad, k, battle_round)))
            for key, name in TRIARCH_ABILITIES
        ]
        self.decision_manager.request(
            player,
            "%s (%s): select one Triarch ability for battle round %d."
            % (VOICE_OF_THE_TRIARCH_LABEL, squad.name, battle_round),
            options,
        )
        return True

    def _choose(self, squad, key, battle_round):
        squad.triarch_ability = key
        self._log("%s (%s): %s until the start of battle round %d."
                  % (VOICE_OF_THE_TRIARCH_LABEL, squad.name,
                     TRIARCH_ABILITY_NAMES[key], battle_round + 1))
        return True
