"""Warhost Stratagem: Fire and Fade (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Warhost.md):
  WHEN:   Your Shooting phase, just after an ASURYANI INFANTRY unit from your
          army (excluding AIRCRAFT, ASURMEN and WRAITH CONSTRUCT units) has
          shot.
  TARGET: That ASURYANI unit.
  EFFECT: Your unit can make a Normal move of up to D6+1".
  RESTRICTIONS: Until the end of the turn, your unit is not eligible to declare
                a charge or embark within a TRANSPORT.

THE SECOND "FIRE AND FADE" IN THIS ENGINE, and the older one is a DATASHEET
ability: game/fire_and_fade.py is the Kroot Lone-Spear's, which this repo would
normally rename one of - except both are genuinely printed under that name, so
neither can be renamed without lying about a datasheet. The detachment prefix
every module in this batch carries does the separating instead, and the two are
pinned AGAINST each other in the test the way the Necron Staff of Light pairs
are. What actually differs, all of it printed:

    Kroot Lone-Spear             this Stratagem
    a flat 6"                    D6+1", rolled
    must be within Engagement    no engagement condition at all
      Range of an enemy
    charge lock only             charge lock AND an embark lock
    free, a datasheet ability    1CP

THE EMBARK LOCK IS THE PART THE ENGINE DID NOT HAVE. charge_locked_until_end_of
_turn has existed for five rules; there was no counterpart for "cannot embark",
so Squad.embark_locked_until_end_of_turn was added and TransportController.
can_embark() reads it. Without it the printed RESTRICTIONS line is half
enforced, and the half that is missing is the one that makes the move free.

D6+1" IS ROLLED, THROUGH THE DICE MANAGER, so the human sees the number that
decides how far they may go - the same treatment Battle Focus's own D6+1"
manoeuvres get. roll_kind stays unset: a granted move distance is not on rule
15.02's re-rollable list.

IT IS NOT A REACTIVE MOVE. Its WHEN is "YOUR Shooting phase", so the mover is
the turn owner and MovementController.select() will accept the unit - which is
what separates it from Overflight, whose Fight-phase half belongs to nobody and
therefore needs the active_player hand-off. It goes through
start_post_shooting_move() with its rolled distance, and needs its own
move_mode only so Confirm can apply the two locks "if it does" - the same
reason Tactical Acumen and the Kroot ability each have one.

THREE EXCLUSIONS, and two of them are measured no-ops on this roster: no
Aeldari datasheet carries AIRCRAFT (this engine has none at all), and ASURMEN
is one named model. WRAITH CONSTRUCT is real and excludes four datasheets - but
all four are also not INFANTRY-only in the way that matters, so the INFANTRY
clause carries most of the weight. All three are written out anyway, because
"already impossible" and "forgotten" look identical from the code.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, martial_grace
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

WARHOST_FIRE_AND_FADE_NAME = "Fire and Fade"
WARHOST_FIRE_AND_FADE_CP = 1

#: 'a Normal move of up to D6+1"'.
WARHOST_FIRE_AND_FADE_BONUS_IN = 1

#: Routes Confirm back to this controller so the two locks are applied only if
#: the move is actually made. Distinct from the Kroot ability's own mode.
WARHOST_FIRE_AND_FADE_MOVE_MODE = "warhost_fire_and_fade"

#: "excluding AIRCRAFT, ASURMEN and WRAITH CONSTRUCT units".
WARHOST_FIRE_AND_FADE_EXCLUDED_KEYWORDS = ("AIRCRAFT", "WRAITH CONSTRUCT")
WARHOST_FIRE_AND_FADE_EXCLUDED_DATASHEET = "Asurmen"


def eligible_unit(squad):
    """"One ASURYANI INFANTRY unit ... (excluding AIRCRAFT, ASURMEN and WRAITH
    CONSTRUCT units)"."""
    if squad is None or not martial_grace.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_asuryani_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    if not unit_has_datasheet_keyword(squad, "INFANTRY"):
        return False
    for keyword in WARHOST_FIRE_AND_FADE_EXCLUDED_KEYWORDS:
        if unit_has_datasheet_keyword(squad, keyword):
            return False
    # ASURMEN is a named model, not a keyword - rule 19.03's pooling means a
    # unit he is leading is excluded too, which is what "units" says.
    return not any(
        getattr(m.profile, "name", "") == WARHOST_FIRE_AND_FADE_EXCLUDED_DATASHEET
        for m in (getattr(squad, "models", ()) or ()))


class WarhostFireAndFadeController:
    """The just-after-it-has-shot offer, the D6+1" roll and the two locks."""

    def __init__(self, stratagem_controller, movement_controller=None,
                 turn_tracker=None, dice_manager=None, decision_manager=None,
                 game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.movement_controller = movement_controller
        self.turn_tracker = turn_tracker
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self._moving_squad = None
        self._stratagem = Stratagem(
            name=WARHOST_FIRE_AND_FADE_NAME, cp_cost=WARHOST_FIRE_AND_FADE_CP,
            effect=self._start,
        )

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False
            if squad.owner != self.turn_tracker.turn_owner:
                return False           # "YOUR Shooting phase"
        if not eligible_unit(squad):
            return False
        if not any(not m.is_dead() for m in (getattr(squad, "models", ()) or ())):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def offer_after_shooting(self, squad, hit_squads=None):
        """Fed from ShootingController.on_squad_finished_shooting.

        `hit_squads` is unused: the printed WHEN is "has SHOT", not "has hit
        anything" - the same distinction Tactical Acumen writes out on the same
        hook."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return False               # no AI path
        self.decision_manager.request(
            squad.owner,
            '%s (%d CP): %s has shot - make a Normal move of up to D6+%d"? It '
            "cannot charge or embark this turn if it does."
            % (WARHOST_FIRE_AND_FADE_NAME, WARHOST_FIRE_AND_FADE_CP, squad.name,
               WARHOST_FIRE_AND_FADE_BONUS_IN),
            [("Use (%d CP)" % WARHOST_FIRE_AND_FADE_CP, (lambda: self.use(squad))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _start(self, controller, player, targets):
        squad = (targets or [None])[0]
        if squad is None or self.movement_controller is None or not squad.models:
            return
        distance = WARHOST_FIRE_AND_FADE_BONUS_IN
        if self.dice_manager is not None:
            # roll_kind stays unset: a granted move distance is not on rule
            # 15.02's re-rollable list, the same reasoning Battle Focus's own
            # D6+1" manoeuvres record.
            values = self.dice_manager.roll(
                count=1, sides=6,
                label='%s: %s moves D6+%d"' % (WARHOST_FIRE_AND_FADE_NAME,
                                               squad.name,
                                               WARHOST_FIRE_AND_FADE_BONUS_IN),
            )
            distance += sum(values or [0])
        self.movement_controller.select(squad.models[0])
        if self.movement_controller.selected_squad is not squad:
            return
        self.movement_controller.start_post_shooting_move(
            squad, move_mode=WARHOST_FIRE_AND_FADE_MOVE_MODE, max_distance=distance)
        self._moving_squad = squad
        if self.game_log is not None:
            self.game_log.add(
                '%s: %s may make a Normal move of up to %g".'
                % (WARHOST_FIRE_AND_FADE_NAME, squad.name, distance))

    def confirm_move(self):
        """The two locks are applied ONLY once the move has actually been made
        - "if it does". confirm_move() clears move_mode on success and leaves
        it set on failure, which is how that is read."""
        if self.movement_controller is None or self._moving_squad is None:
            return
        squad = self._moving_squad
        self.movement_controller.confirm_move()
        if self.movement_controller.move_mode is None:
            squad.charge_locked_until_end_of_turn = True
            squad.embark_locked_until_end_of_turn = True
            self._moving_squad = None
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s moved and cannot declare a charge or embark this "
                    "turn." % (WARHOST_FIRE_AND_FADE_NAME, squad.name))

    def cancel_move(self):
        if self.movement_controller is not None:
            self.movement_controller.cancel_move()
        self._moving_squad = None
