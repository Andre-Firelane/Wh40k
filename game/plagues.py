"""The three Plagues of the DEATH GUARD army rule (game/nurgles_gift.py).

RULES (printed, word for word):

  "During the Declare Battle Formations step, select one of the Plagues below.
  Until the end of the battle, while an enemy unit is Afflicted, subtract 1
  from the Toughness characteristic of models in that unit, and that unit has
  the effect of your chosen Plague."

  Skullsquirm Blight: "Each time a model in this unit makes an attack, subtract
  1 from the Hit roll."

  Rattlejoint Ague: "Worsen the Save characteristic of models in this unit
  by 1."

  Scabrous Soulrot: "Worsen the Move, Leadership, and Objective Control
  characteristics of models in this unit by 1 (this rule can only worsen a
  model's Objective Control characteristic to a minimum of 1)."

"THIS UNIT" IS THE AFFLICTED ENEMY, not the Death Guard unit - every one of
these is a debuff written from the victim's point of view. Skullsquirm Blight
in particular reads backwards on a first pass: it is the afflicted unit's OWN
attacks that are worsened, not attacks against it.

"AN ATTACK", not "a ranged attack" - so it applies in BOTH phases, and the
modifier therefore sits in game/shooting.py's AND game/fight.py's
_hit_modifiers(). Recorded because this was built wrong first: a summarised
source gave it as "ranged attacks grant the target cover, melee attacks are -1
to hit", which is two effects in two places and neither of them what the card
says. The printed text is one effect in one place, twice over.

THE SIX EFFECTS SIT AT SIX EXISTING FUNNELS, none of them new:
  hit (ranged)  -> game/shooting.py's _hit_modifiers()
  hit (melee)   -> game/fight.py's _hit_modifiers()
  save          -> game/damage_resolution.py's save_thresholds()
  Move          -> game/coldstar.py's effective_movement_in()
  Leadership    -> game/leadership.py's leadership_threshold()
  Objective Ctl -> game/objectives.py's level_of_control()

EVERY READER TAKES ONLY THE SQUAD (or the model), and that is the whole design
decision in this module. The obvious alternative - hold the per-player choice
in one object and pass it to each funnel - would have grown a parameter on
effective_movement_in(), leadership_threshold() and level_of_control(), which
between them have well over a dozen call sites across the AI movement code.
game/coldstar.py's own docstring names that exact hazard ("eight call sites
across five files, including the AI movement code, which is the single most
regression-prone area in this repo").

Instead NurglesGiftController.refresh() - which already walks every unit once
a frame to set Squad.afflicted - writes Squad.afflicted_plague in the same
pass. The Plague is then read off the unit, like Squad.ard_as_nails_active and
Squad.psychic_shield_range, and a funnel needs one call and no new dependency.
This module therefore imports only game/modifiers.py and game/nurgles_gift.py,
both of which are leaves (nurgles_gift.py imports nothing at all, by design -
game/squad.py depends on it). That is what lets game/objectives.py,
game/leadership.py and game/coldstar.py all depend on this module without any
risk of an import cycle.

WHICH Plague lands on a unit is decided by PlagueChoice.plague_against(): the
one its OPPONENT chose. The Plague belongs to the Death Guard player and
afflicts their enemies, so a unit suffers the choice of the player who is not
its owner. In a two-player game that is exact, it needs no record of who
applied the affliction, and it makes a Death Guard mirror match work with no
extra code - each side suffers the other's Plague.
"""
from game import nurgles_gift
from game.modifiers import Modifier

SKULLSQUIRM_BLIGHT = "skullsquirm_blight"
RATTLEJOINT_AGUE = "rattlejoint_ague"
SCABROUS_SOULROT = "scabrous_soulrot"

PLAGUES = (SKULLSQUIRM_BLIGHT, RATTLEJOINT_AGUE, SCABROUS_SOULROT)

PLAGUE_NAMES = {
    SKULLSQUIRM_BLIGHT: "Skullsquirm Blight",
    RATTLEJOINT_AGUE: "Rattlejoint Ague",
    SCABROUS_SOULROT: "Scabrous Soulrot",
}

PLAGUE_DESCRIPTIONS = {
    SKULLSQUIRM_BLIGHT: "its ranged attacks grant cover, its melee attacks are -1 to hit",
    RATTLEJOINT_AGUE: "worsen its Save by 1",
    SCABROUS_SOULROT: "worsen its Move, Leadership and Objective Control by 1",
}

SKULLSQUIRM_HIT_PENALTY = 1  # positive worsens, see game/modifiers.py
RATTLEJOINT_SAVE_PENALTY = 1
SCABROUS_MOVE_PENALTY_IN = 1.0
SCABROUS_LEADERSHIP_PENALTY = 1
SCABROUS_OC_PENALTY = 1
SCABROUS_OC_FLOOR = 1  # "to a minimum of 1"

# The AI's pick, and the order the human is offered them in. Deterministic by
# construction - a fixed order, no board reading, so no API call and no way for
# two runs of the same scene to diverge.
#
# Rattlejoint Ague first because it is the only one of the three that pays
# against EVERY enemy unit: a worse Save applies to every attack this army
# makes, while Skullsquirm Blight only pays against a unit that is still
# attacking at all, and Scabrous Soulrot only against one that is
# still trying to move or hold ground. Recorded as a DECISION rather than a
# measurement - it is a once-per-battle choice made during Declare Battle
# Formations, before an enemy is on the table, so there is nothing yet to
# measure against.
AI_PLAGUE_PREFERENCE = (RATTLEJOINT_AGUE, SKULLSQUIRM_BLIGHT, SCABROUS_SOULROT)
DEFAULT_PLAGUE = AI_PLAGUE_PREFERENCE[0]


class PlagueChoice:
    """Which Plague each Death Guard player selected.

    One instance per battle, owned by main.py, handed to
    NurglesGiftController - which is the only thing that reads it, once a
    frame, when it stamps Squad.afflicted_plague."""

    def __init__(self, game_log=None):
        self._by_player = {}
        self.game_log = game_log

    def choose(self, player, plague):
        if plague not in PLAGUES:
            raise ValueError(f"unknown Plague: {plague!r}")
        self._by_player[player] = plague
        if self.game_log is not None:
            self.game_log.add(
                f"{player} selects the Plague {PLAGUE_NAMES[plague]} "
                f"({PLAGUE_DESCRIPTIONS[plague]}) - rule: Nurgle's Gift."
            )
        return plague

    def chosen_by(self, player):
        return self._by_player.get(player)

    def players(self):
        return sorted(self._by_player)

    def plague_against(self, squad):
        """The Plague affecting `squad` - i.e. the one its OPPONENT chose.

        None when no opponent has chosen one, which is every non-Death-Guard
        game and is why all six readers below degrade to "no effect"."""
        if squad is None:
            return None
        for player, plague in self._by_player.items():
            if player != squad.owner:
                return plague
        return None


def active_plague(squad):
    """The Plague this unit is suffering right now, or None.

    Both halves have to hold: the unit is Afflicted (Squad.afflicted) AND an
    opponent chose a Plague (Squad.afflicted_plague). Both flags are stamped
    by the same per-frame pass, so they cannot disagree."""
    if squad is None or not getattr(squad, "afflicted", False):
        return None
    return getattr(squad, "afflicted_plague", None)


def _suffers(squad, plague):
    return active_plague(squad) == plague


# --- Skullsquirm Blight -----------------------------------------------------

def hit_modifiers(attacking_squad):
    """"Each time a model in this unit makes an attack, subtract 1 from the
    Hit roll."

    Asked of the ATTACKING unit - it is the afflicted unit's own attacks that
    are blunted, not attacks against it. "An attack" with no qualifier, so BOTH
    _hit_modifiers() sites read this one function; there is no ranged/melee
    split and no cover clause (see the module docstring on how that was got
    wrong once)."""
    if _suffers(attacking_squad, SKULLSQUIRM_BLIGHT):
        return [Modifier(SKULLSQUIRM_HIT_PENALTY, "Skullsquirm Blight")]
    return []


# --- Rattlejoint Ague -------------------------------------------------------

def save_penalty(squad):
    """"Worsen the Save characteristic of models in this unit by 1."

    The Save CHARACTERISTIC, not the roll and not the AP: it lands on the
    printed armour save before AP is subtracted, and leaves the invulnerable
    save untouched (an invulnerable save is a different characteristic - and
    a unit with a 4+ invulnerable is exactly where the two readings visibly
    differ). Applied in game/damage_resolution.py's save_thresholds(), the one
    definition both the resolution and the dice panel read - so a die that
    Rattlejoint Ague turned into a failure cannot be shown as a pass, which is
    the bug that function was extracted to prevent."""
    return RATTLEJOINT_SAVE_PENALTY if _suffers(squad, RATTLEJOINT_AGUE) else 0


# --- Scabrous Soulrot -------------------------------------------------------

def movement_penalty_in(squad):
    """"Worsen the Move ... by 1". Inches, applied in game/coldstar.py's
    effective_movement_in() - the one place this engine asks "how far does
    this model actually move", after every override and every bonus."""
    return SCABROUS_MOVE_PENALTY_IN if _suffers(squad, SCABROUS_SOULROT) else 0.0


def leadership_penalty(squad):
    """"Worsen the ... Leadership ... by 1". Ld is a threshold, so worsening
    it means a HIGHER number - added to the threshold in
    game/leadership.py's leadership_threshold()."""
    return SCABROUS_LEADERSHIP_PENALTY if _suffers(squad, SCABROUS_SOULROT) else 0


def worsen_oc(model, printed=None):
    """Scabrous Soulrot's own contribution to this model's Objective Control.

    RENAMED from effective_oc(): it was the whole answer while this Plague was
    the only thing that could change an OC, and a name that says "effective"
    became a lie the moment the Kroot Hounds' Hunting Hounds arrived. The whole
    answer now lives in game/objective_control.py, which folds this together
    with that one - see its docstring for why the order is set-then-worsen.

    `printed` lets the caller pass a value another source has already set;
    None means read the model's printed characteristic, which is what every
    caller before the extraction meant.

    "(this rule can only worsen a model's Objective Control characteristic to
    a minimum of 1)" - so OC 3 becomes 2, OC 2 becomes 1, and OC 1 stays 1.

    A model with a PRINTED OC of 0 (every weapon platform and drone in this
    engine) is left alone rather than clamped up to the floor: the clause is a
    floor on how far the rule may WORSEN a value, not a value the rule may
    raise something to, and reading it the other way would have Scabrous
    Soulrot hand an objective-blind model an Objective Control of 1. Hence the
    `<= SCABROUS_OC_FLOOR` short-circuit, which covers the 1 and the 0 case
    for one reason."""
    if printed is None:
        printed = getattr(model.profile, "oc", 0)
    if printed <= SCABROUS_OC_FLOOR:
        return printed
    if not _suffers(getattr(model, "squad", None), SCABROUS_SOULROT):
        return printed
    return printed - SCABROUS_OC_PENALTY


# --- the Declare Battle Formations choice -----------------------------------

def ai_choice():
    """The AI's Plague, deterministically. No board reading, no API call."""
    return AI_PLAGUE_PREFERENCE[0]


def offer_labels():
    """The human's options, in AI_PLAGUE_PREFERENCE order so both players see
    the same ranking. [(plague key, button label), ...]"""
    return [(plague, f"{PLAGUE_NAMES[plague]} - {PLAGUE_DESCRIPTIONS[plague]}")
            for plague in AI_PLAGUE_PREFERENCE]


class PlagueSelectionStep:
    """"During the Declare Battle Formations step, select one of the Plagues."

    Driven from PregameController.on_formations_started. Only players who
    actually field Death Guard are asked - derived from the units by
    nurgles_gift.qualifying_players(), so a game with no Death Guard in it
    never sees this at all, and a mirror match asks both players.

    The AI answers itself from ai_choice(); no `agent` reaches this class, so
    the choice cannot cost an API call however the driver is wired."""

    def __init__(self, plague_choice, decision_manager=None,
                 human_players=("Player 1",), game_log=None):
        self.plague_choice = plague_choice
        self.decision_manager = decision_manager
        # A SET for the same reason PregameController holds one: with the AI
        # mode off both armies are played by hand, so a DEATH GUARD player
        # who is not "Player 1" must still be asked for their Plague.
        self.human_players = human_players
        self.game_log = game_log

    def begin(self, squads):
        """Ask every Death Guard player for their Plague. Returns the players
        asked, so main.py and the tests can see it happened."""
        asked = []
        for player in nurgles_gift.qualifying_players(squads):
            if self.plague_choice.chosen_by(player) is not None:
                continue  # idempotent: start() can be reached more than once
            asked.append(player)
            if player in self.human_players and self.decision_manager is not None:
                self._request(player)
            else:
                self.plague_choice.choose(player, ai_choice())
        return asked

    def _request(self, player):
        options = [(label, (lambda p=player, k=plague: self.plague_choice.choose(p, k)))
                   for plague, label in offer_labels()]
        self.decision_manager.request(
            player,
            "Nurgle's Gift: select one Plague for the battle "
            "(rule: Declare Battle Formations)",
            options,
        )
