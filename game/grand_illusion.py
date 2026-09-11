"""Grand Illusion - the C'tan Shard of the Deceiver's own ability.

RULE (printed, word for word):

  "If your army includes this model, after both players have deployed their
   armies, select up to three NECRONS units from your army and redeploy them.
   When doing so, any of those units can be placed into Strategic Reserves,
   regardless of how many units are already in Strategic Reserves."

The machine is game/post_deployment_redeploy.py's - extracted at this, its
second carrier, from Kauyon's Solid-image Projection Unit, which prints the
same sentence with "T'AU EMPIRE" for "NECRONS". This file is the two words that
differ.

"IF YOUR ARMY INCLUDES THIS MODEL" - NOT "IF IT IS ON THE BATTLEFIELD"
-----------------------------------------------------------------------
That is the one clause a copy of the neighbouring carrier would get wrong, and
it is worth spelling out because the OTHER redeploy ability in this engine says
the opposite: game/prince_of_corsairs.py is gated on "if this unit is on the
battlefield (or any TRANSPORT it is embarked within is)", and its own docstring
records that the reserve case "is the one that would silently keep working".

Here the reserve case is CORRECT. A Deceiver that deep-struck into Strategic
Reserves still grants Grand Illusion, because the printed condition is about
the army list, not the board. So grants() reads GameState.all_squads() - board,
reserves and transports - where its sibling reads the token list.

NECRONS IS READ OFF THE DATASHEET, via game/awakened_dynasty.py's
is_necrons_unit(). That is the same arrangement the other two factions use
(game/tau_detachments.py's is_tau_unit, game/aeldari_detachments.py's
is_aeldari_unit): the faction question lives in the faction's detachment
module, and everyone else imports it rather than writing their own.

FOUND WHILE WIRING THIS, NOT FIXED HERE: there are FOUR definitions of "is this
a NECRONS unit" in game/, and they are two different readings.
is_necrons_unit() above reads the DATASHEET's faction keyword;
multi_threat_eliminator.py, reanimation_boost.py and spyder_wargear.py each
carry a byte-identical copy that reads the per-model `reanimation_protocols`
flag instead. On the built datasheets the two agree - every Necron datasheet
prints the army rule - so nothing is wrong today. Consolidating them means
editing three modules shipped in stages 3 and 5, which is its own measured
step; importing the datasheet reading here at least does not make it five.
"""

from game import awakened_dynasty
from game.post_deployment_redeploy import PostDeploymentRedeployStep

GRAND_ILLUSION_LABEL = "Grand Illusion"


def _living(squad):
    return [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]


def has_grand_illusion(squad):
    return any(getattr(m.profile, "grand_illusion", False) for m in _living(squad))


class GrandIllusionStep(PostDeploymentRedeployStep):
    """Registered as one arm of main.py's `_RedeployChain`."""

    label = GRAND_ILLUSION_LABEL

    def _army_squads(self):
        """Every unit this player owns, wherever it is - see the module
        docstring on why the board alone is the wrong list here."""
        state = self.game_state
        if state is None:
            return []
        getter = getattr(state, "all_squads", None)
        if callable(getter):
            return list(getter())
        return self._squads()

    def grants(self, player):
        return any(s.owner == player and has_grand_illusion(s)
                   for s in self._army_squads())

    def in_faction(self, squad):
        '''"up to three NECRONS units from your army".'''
        return awakened_dynasty.is_necrons_unit(squad)
