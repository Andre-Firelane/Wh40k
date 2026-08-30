"""Spirit Conclave Stratagem: Soul Bridge (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Spirit Conclave.md):
  WHEN:   Your Command phase.
  TARGET: One WRAITHBLADES, WRAITHGUARD or WRAITHLORD unit from your army and
          one ASURYANI PSYKER model from your army.
  EFFECT: Until the start of your next Command phase, your WRAITHBLADES,
          WRAITHGUARD or WRAITHLORD unit is considered to be within 12" of your
          PSYKER model for the purposes of the Psychic Guidance and Spirit
          Guides abilities.
  RESTRICTIONS: none printed.

NOTHING IN THIS ENGINE SPOOFS A DISTANCE, and this Stratagem deliberately does
not start. The printed text NAMES ITS OWN CONSUMERS - "for the purposes of the
Psychic Guidance and Spirit Guides abilities" - so what is granted is not a
position but an exemption that exactly those two predicates read. A general
"pretend this unit is 12" from that model" would also reach Leadership auras,
objective control, target selection and everything else that measures to a
model, none of which the printed text mentions.

So this module holds a MARK, and the two predicates ask it:

  * psychic_guidance._in_range() - the Wraithguard/Wraithblades hit-roll
    variant and the Wraithlord characteristic variant both go through it.
  * ShepherdsOfTheDeadController.spirit_guides_reaches().

Two readers, one mark, and a third ability wanting the same favour would have
to be named in a printed text before it got one.

THE MARK IS A (unit, psyker model) PAIR, not a flag on the unit. Both consumers
ask "is there a friendly PSYKER within 12"", and the answer has to be about the
SPECIFIC model this Stratagem named - a bridge to a dead Spiritseer is no
bridge, and the mark ends when that model dies rather than lingering as a bare
boolean.

THE TWO CONSUMERS WANT DIFFERENT PSYKERS, and the printed text is the reason
the mark stores the model rather than re-deriving it: Psychic Guidance says
AELDARI PSYKER, Spirit Guides says ASURYANI PSYKER, and this Stratagem's own
TARGET clause says ASURYANI PSYKER. The bridged model is checked against each
consumer's own keyword, so a bridge built to an AELDARI-but-not-ASURYANI psyker
could never satisfy Spirit Guides - which is what those three printed lines
say, however odd it reads.

"UNTIL THE START OF YOUR NEXT COMMAND PHASE" is the same clock Guide and Doom
run on, so it is cleared where they are and not on a phase or turn boundary.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, shepherds_of_the_dead
from game.stratagems import Stratagem
from game.turn import PHASE_COMMAND

SOUL_BRIDGE_NAME = "Soul Bridge"
SOUL_BRIDGE_CP = 1

#: "One WRAITHBLADES, WRAITHGUARD or WRAITHLORD unit from your army".
SOUL_BRIDGE_UNIT_KEYWORDS = ("WRAITHBLADES", "WRAITHGUARD", "WRAITHLORD")

SETTING = shepherds_of_the_dead.SETTING


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def bridged_psyker(squad):
    """The PSYKER model this unit is bridged to, or None.

    Ends by itself when that model dies - a bridge to a dead Spiritseer is no
    bridge, which a bare boolean could not express."""
    psyker = getattr(squad, "soul_bridge_psyker", None)
    if psyker is None or psyker.is_dead():
        return None
    return psyker


def is_bridged_to(squad, psyker_model):
    """Read by the two predicates the printed text names, and by nothing else."""
    return psyker_model is not None and bridged_psyker(squad) is psyker_model


def eligible_unit(squad):
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k)
               for k in SOUL_BRIDGE_UNIT_KEYWORDS)


def psyker_models_for(player, all_tokens=()):
    """"One ASURYANI PSYKER model from your army"."""
    out = []
    for token in all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is None or squad.owner != player or token.is_dead():
            continue
        if not getattr(token.profile, "psyker", False):
            continue
        if not aeldari_detachments.is_asuryani_unit(squad):
            continue
        out.append(token)
    return out


def clear_at_command_phase(squads=()):
    """"Until the start of your NEXT Command phase" - the clock Guide and Doom
    already run on."""
    for squad in squads or ():
        if squad is not None:
            squad.soul_bridge_psyker = None


class SoulBridgeController:
    """A Command-phase panel button. The psyker is chosen for the player when
    there is only one, and asked for otherwise."""

    def __init__(self, stratagem_controller, all_tokens=None, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self._pending = {}
        self._stratagem = Stratagem(
            name=SOUL_BRIDGE_NAME, cp_cost=SOUL_BRIDGE_CP, effect=self._bridge,
        )

    def panel_label(self, squad):
        return ('%s (%d CP) - count as within 12" of a psyker until your next '
                "Command phase" % (SOUL_BRIDGE_NAME, SOUL_BRIDGE_CP))

    def psykers_for(self, squad):
        return psyker_models_for(squad.owner, self.all_tokens)

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_COMMAND:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False               # "YOUR Command phase"
        if not eligible_unit(squad):
            return False
        if bridged_psyker(squad) is not None:
            return False
        if not self.psykers_for(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad, psyker_model=None):
        if not self.can_use(squad):
            return False
        candidates = self.psykers_for(squad)
        if psyker_model is None:
            # One candidate needs no question - the same shortcut every other
            # "select one" offer in this engine takes.
            if len(candidates) > 1 and squad.owner not in self.auto_players \
                    and self.decision_manager is not None:
                self.decision_manager.request(
                    squad.owner,
                    "%s: bridge %s to which psyker?" % (SOUL_BRIDGE_NAME, squad.name),
                    [("%s" % t.profile.name, (lambda s=squad, t=t: self.use(s, t)))
                     for t in candidates],
                    is_stratagem=True,
                )
                return True
            psyker_model = candidates[0]
        self._pending[squad.owner] = (squad, psyker_model)
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _bridge(self, controller, player, targets):
        squad, psyker = self._pending.pop(player, (None, None))
        if squad is None or psyker is None:
            return
        squad.soul_bridge_psyker = psyker
        if self.game_log is not None:
            self.game_log.add(
                '%s: %s counts as within 12" of %s for Psychic Guidance and '
                "Spirit Guides until your next Command phase."
                % (SOUL_BRIDGE_NAME, squad.name, psyker.profile.name))
