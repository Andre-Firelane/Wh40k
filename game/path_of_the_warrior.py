"""Aspect Host's "Path of the Warrior" - the detachment rule.

RULE (printed, word for word):
  "Each time an ASPECT WARRIORS or AVATAR OF KHAINE unit from your army is
  selected to shoot or fight, select one of the following abilities for it to
  gain until the end of the phase:
   - Each time a model in this unit makes an attack, re-roll a Hit roll of 1.
   - Each time a model in this unit makes an attack, re-roll a Wound roll of 1."

A REAL CHOICE, so a real prompt. This is the opposite call from Herald of
Ynnead, which was resolved automatically because its single option was pure
gain with no alternative to weigh. Here the two options are exclusive and
genuinely trade off - a unit that hits easily and wounds badly wants the second
- so offering it is the point of the rule rather than noise (error class 5 cuts
the other way).

PLAIN AUTOMATIC ONES, NOT A reroll_scope ENTRY. Each clause is "re-roll a Hit
roll of 1" with no "you can" and no "instead", so once the ability is chosen its
re-roll is mandatory and covers the 1s only. That means it belongs in the
`automatic_ones` disjunctions in the two attack steps, NOT in
_hit_reroll_reason()/_wound_reroll_reason(), which drive the failures-or-whole
OFFER. Listing it in game/reroll_scope.py would hand the player a second choice
the datasheet never gives, on top of the one it does. Pinned as an absence.

FOUR SITES, TWO PHASES. "selected to shoot OR fight" and "makes an attack", so
each clause is read in both files - hit in shooting.py and fight.py, wound in
shooting.py and fight.py. A wiring reaching three of the four looks complete
from any one of them, which is why the test counts per file.

UNTIL THE END OF THE PHASE, AND PER PHASE. A unit picks once when it is
selected to shoot and again when it is selected to fight, and the two are
independent - so the ledger is keyed by (unit, phase) and cleared on the phase
boundary. Keyed by id(squad) rather than held on the Squad, because a Squad
outlives the phase and this does not.

THE AI ANSWERS ITSELF. No path in ai/ (standing Aeldari instruction) - an owner
in auto_players takes the HIT re-roll, because the hit roll comes first and an
attack that misses never reaches the wound roll, so re-rolling 1s there is
never worth less. A prompt nobody answers would stall the loop, which is the
'Ard as Nails arrangement rather than an AI path.
"""

from game import aeldari_detachments
from game import enh_mantle_of_wisdom

PATH_OF_THE_WARRIOR_LABEL = "Path of the Warrior"

#: The two printed options, in printed order. The order is load-bearing only as
#: the AI's default.
HIT = "hit"
WOUND = "wound"
PATH_OF_THE_WARRIOR_OPTIONS = (HIT, WOUND)

OPTION_TEXT = {
    HIT: "re-roll a Hit roll of 1",
    WOUND: "re-roll a Wound roll of 1",
}

#: The two keyword lines the rule names.
PATH_OF_THE_WARRIOR_KEYWORDS = ("ASPECT WARRIORS", "AVATAR OF KHAINE")

#: The config constant game/detachments.py writes for Aspect Host.
SETTING = "ASPECT_HOST_PLAYERS"


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def eligible(squad):
    """"an ASPECT WARRIORS or AVATAR OF KHAINE unit from your army"."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, keyword)
               for keyword in PATH_OF_THE_WARRIOR_KEYWORDS)


class PathOfTheWarriorController:
    """The per-activation choice and the ledger that holds it for the phase."""

    def __init__(self, decision_manager=None, game_log=None, turn_tracker=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.turn_tracker = turn_tracker
        self.auto_players = set(auto_players)
        #: (id(squad), phase) -> HIT or WOUND.
        self._chosen = {}

    def _phase(self):
        return getattr(self.turn_tracker, "phase", None)

    def chosen_for(self, squad, phase=None):
        if squad is None:
            return None
        return self._chosen.get((id(squad), phase if phase is not None else self._phase()))

    def choose(self, squad, option, phase=None):
        if squad is None or option not in PATH_OF_THE_WARRIOR_OPTIONS:
            return False
        self._chosen[(id(squad), phase if phase is not None else self._phase())] = option
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s will %s until the end of the phase."
                % (PATH_OF_THE_WARRIOR_LABEL, squad.name, OPTION_TEXT[option]))
        return True

    def offer(self, squad):
        """"each time [it] is selected to shoot or fight" - both callers reach
        this, and the phase in the key is what keeps them independent."""
        if not eligible(squad) or self.chosen_for(squad) is not None:
            return False
        # Aspect Host's Mantle of Wisdom grants BOTH options, so there is
        # nothing to choose - asking anyway would present a limit that no
        # longer exists. See game/enh_mantle_of_wisdom.py.
        if enh_mantle_of_wisdom.applies(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            # The hit roll comes first and a miss never reaches the wound roll,
            # so re-rolling 1s there is never the worse half of the trade.
            return self.choose(squad, HIT)
        self.decision_manager.request(
            squad.owner,
            "%s: %s - which does it gain this phase?"
            % (PATH_OF_THE_WARRIOR_LABEL, squad.name),
            [(OPTION_TEXT[option].capitalize(),
              (lambda o=option: self.choose(squad, o)))
             for option in PATH_OF_THE_WARRIOR_OPTIONS])
        return True

    # --- what the two attack steps read ----------------------------------

    # Mantle of Wisdom is folded in HERE, at this rule's own answer, rather
    # than at the four places the answer is read - see that module's docstring
    # for why. "Both of the abilities", so both questions say yes.

    def hit_ones_apply(self, squad):
        if enh_mantle_of_wisdom.applies(squad):
            return True
        return self.chosen_for(squad) == HIT

    def wound_ones_apply(self, squad):
        if enh_mantle_of_wisdom.applies(squad):
            return True
        return self.chosen_for(squad) == WOUND

    def reset_phase(self):
        """"Until the end of the phase". Cleared wholesale rather than per
        player: the key carries the phase, and a phase ends for everyone."""
        self._chosen.clear()
