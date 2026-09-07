"""Armoured Warhost Enhancement: Spirit Stone of Raelyth (20 pts).

RULE (verbatim, rules/aeldari/detachments/Armoured Warhost.md):
  "AELDARI PSYKER model only.
   - While this model is within 3" of a friendly AELDARI VEHICLE unit, this
     model has Lone Operative.
   - In your Movement phase, at the start or end of this unit's move, you can
     select one friendly AELDARI VEHICLE model within 3" of this model. That
     VEHICLE model heals D3 wounds."

TWO CLAUSES THAT SHARE ONLY A DISTANCE. They are wired at two unrelated seams
and are tested apart, because nothing about one implies the other.

CLAUSE 1 IS THE FOURTH CONDITIONAL LONE OPERATIVE. Illuminor Szeras, the
Spiritseer and the Death Guard Defenders all print "while this model is within
3" of <something friendly>, it has Lone Operative"; game/conditional_lone_
operative.py was extracted for exactly that shape, so this costs one tuple
entry and no new plumbing in game/status_effects.py.

CLAUSE 2 IS A HEAL, AND IT HAS TWO MOMENTS. "At the START or end of this
unit's move" - and only the end of a move had a seam. MovementController now
has on_move_started to mirror on_move_finished, hung on _begin_move(), which is
the ONE shared entry all ten move types pass through; a hook per move-starter
could have been wired to some of them and looked complete.

Offering only the end would have been the cheap version and it is a REAL loss:
the choice the two moments buy is precisely whether to heal a vehicle you are
about to drive away from, or one you are about to pull alongside. Losing that
takes an option away from the player who paid 20 points for it.

ONCE PER MOVE, NOT ONCE PER MOMENT. "At the start OR end" - one heal, and the
player picks when. So the offer is made at both, and a per-move ledger closes
it after the first acceptance; DECLINING at the start deliberately leaves the
end still open, because "or" is a choice of timing, not a use of the ability.

"MODEL", NOT "UNIT" - both halves. The Lone Operative clause measures from the
bearer MODEL to a friendly AELDARI VEHICLE UNIT; the heal targets one friendly
AELDARI VEHICLE MODEL. So the heal cannot be spread and cannot be aimed at the
unit as a whole, and a wounded vehicle in a squadron is chosen individually.

D3, CAPPED at the model's missing wounds - healing is bounded by what was
lost, so a roll that would overheal simply tops it up. See the controller for
why this one D3 is rolled in the module rather than through the DiceManager.
"""
from game import aeldari_detachments, ai_mode, attached_units, enhancements
from game.squad import edge_distance

SPIRIT_STONE_OF_RAELYTH = "Spirit Stone of Raelyth"

SPIRIT_STONE_LABEL = "Spirit Stone of Raelyth"

#: Both clauses print the same 3".
SPIRIT_STONE_RANGE_IN = 3.0

#: "heals D3 wounds".
SPIRIT_STONE_HEAL_DICE = "D3"


def bearer_models(squad):
    return enhancements.bearer_models(squad, SPIRIT_STONE_OF_RAELYTH)


def _is_aeldari_vehicle(squad):
    """"a friendly AELDARI VEHICLE unit/model" - two keywords, pooled per rule
    19.03, and asked in the two different ways this engine holds them: AELDARI
    off the DATASHEET, VEHICLE off the model profile."""
    if squad is None:
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    return attached_units.unit_has_keyword(
        squad, lambda m: getattr(m.profile, "vehicle", False))


def _friendly_vehicle_models(squad, all_tokens, range_in):
    """Living friendly AELDARI VEHICLE models within `range_in` of any bearer
    model in `squad`."""
    bearers = bearer_models(squad)
    if not bearers:
        return []
    out = []
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other is squad or other.owner != squad.owner:
            continue
        if not _is_aeldari_vehicle(other):
            continue
        if token.is_dead():
            continue
        if any(edge_distance(b, token) <= range_in for b in bearers):
            out.append(token)
    return out


# --- clause 1: the conditional Lone Operative -----------------------------

def grants_lone_operative(squad, all_tokens=()):
    """The shape game/conditional_lone_operative.py's SOURCES expects - the
    same signature Szeras', the Spiritseer's and the Death Guard Defenders'
    all have."""
    if not enhancements.is_active(squad, SPIRIT_STONE_OF_RAELYTH):
        return False
    return bool(_friendly_vehicle_models(squad, all_tokens, SPIRIT_STONE_RANGE_IN))


# --- clause 2: the heal ---------------------------------------------------

def heal_targets(squad, all_tokens=()):
    """The friendly AELDARI VEHICLE models this unit could heal right now.

    Only models that have actually LOST wounds - a full-strength vehicle would
    be offered a heal that does nothing, which is the "never offer what buys
    nothing" rule this repo keeps."""
    return [m for m in _friendly_vehicle_models(squad, all_tokens, SPIRIT_STONE_RANGE_IN)
            if m.current_wounds < m.profile.wounds]


class SpiritStoneOfRaelythController:
    """The heal, offered at both of its printed moments.

    The D3 is rolled in the module rather than through the DiceManager, the
    same deliberate exception game/spiritseer.py's Tears of Isha makes for its
    own D3: this fires inside the Movement phase's move hooks, where a visible
    roll would land in the middle of a drag. The LOG still names the amount, so
    the number is not hidden - only the die is.
    """

    HEAL_SIDES = 3

    def __init__(self, game_state=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        #: id(squad) -> True once this unit has used its heal for the move it
        #: is currently making. "At the start OR end" is ONE heal.
        self._used_this_move = {}

    def _tokens(self):
        return getattr(self.game_state, "tokens", ()) or ()

    def on_move_started(self, squad):
        """Both a fresh ledger for this move AND the first of its two moments -
        in that order, so a heal taken at the start is the one that closes it."""
        if squad is not None:
            self._used_this_move.pop(id(squad), None)
        self.offer(squad)

    def on_move_finished(self, squad):
        self.offer(squad)

    def offer(self, squad):
        """"you can select one friendly AELDARI VEHICLE model within 3"."""
        if squad is None or self._used_this_move.get(id(squad)):
            return False
        if not enhancements.is_active(squad, SPIRIT_STONE_OF_RAELYTH):
            return False
        targets = heal_targets(squad, self._tokens())
        if not targets:
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            # The most wounded model - a heal is capped by what was lost, so
            # this is the only choice that can never waste the roll.
            self._heal(squad, min(targets, key=lambda m: m.current_wounds))
            return True
        options = [("Heal %s (%d/%d wounds)"
                    % (m.profile.name, m.current_wounds, m.profile.wounds),
                    (lambda t=m: self._heal(squad, t)))
                   for m in targets]
        # DECLINING does not spend it: "at the start or end" is a choice of
        # timing, so saying no at the start must leave the end open.
        options.append(("Do not heal", lambda: False))
        self.decision_manager.request(
            squad.owner,
            "%s: heal a friendly AELDARI VEHICLE model?" % SPIRIT_STONE_LABEL,
            options,
        )
        return True

    def _heal(self, squad, model):
        from game.dice import random as dice_random
        healed = dice_random.randint(1, self.HEAL_SIDES)
        before = model.current_wounds
        model.current_wounds = min(model.profile.wounds, before + healed)
        self._used_this_move[id(squad)] = True
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s heals %d wound(s) (rolled %d)."
                % (SPIRIT_STONE_LABEL, model.profile.name,
                   model.current_wounds - before, healed))
        return True

    def reset_turn(self):
        self._used_this_move.clear()
