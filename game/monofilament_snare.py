"""The Shadow Weaver Platform's "Monofilament Snare" - a datasheet ability.

RULE (printed, word for word):
  "In your Shooting phase, after this model has shot, select one enemy unit hit
  by one or more of those attacks made with its shadow weaver. Until the start
  of your next turn, that enemy unit is snared. While a unit is snared, each
  time that unit makes a Normal, Advance or Fall Back move, roll one D6 for
  each model in that unit: for each 1, that unit suffers 1 mortal wound."

A MARK ON THE ENEMY, AND THE SIXTH OF ITS KIND
----------------------------------------------
Guide, Doom, Whispering Web, Advanced Scouting and Harnessed Alien Instincts
are the others: an effect that belongs to the OPPONENT of the unit it sits on,
so it is held per player in this controller rather than as a flag on the marked
squad. Form follows game/whispering_web.py.

WHAT IS GENUINELY NEW is the trigger. Every existing mark is read at an ATTACK;
this one fires on a MOVE, and there was no "a unit finished a Normal/Advance/
Fall Back move" hook. There is now, and it is the SAME seam rule 16.01 already
uses - MovementController.confirm_move() reporting the move's own mode - which
matters for two reasons:

  * The move types that are NOT one of the three printed ones are recognised
    BY NAME rather than guessed at, so a Charge, Pile-In, Consolidate or Surge
    correctly triggers nothing. See UNSNARED_MOVE_MODES below for why the set
    is written as the exclusions - a granted "Normal move" (Scouts, Fade Back,
    Path of the Outcast) IS a Normal move and should trigger it.
  * confirm_move() is the ONE place every confirmed move passes through, so
    there is no second path a move could take without paying.

"UNTIL THE START OF YOUR NEXT TURN" is the marking player's next turn, so the
mark is cleared at the start of that player's turn and not at a phase boundary
- one turn boundary further out than a Guide/Doom mark, and the reason the
lifetime is a stored owner rather than a flat reset.

"ONE D6 FOR EACH MODEL IN THAT UNIT ... FOR EACH 1, THAT UNIT SUFFERS 1 MORTAL
WOUND" - the dice count is the unit's CURRENT model count, read at the moment
of the move, so a unit whittled down between marking and moving rolls fewer.

THE ROLL IS RESOLVED IMMEDIATELY rather than as a dice-panel step, for the
reason game/dlc_undying_spite.py gives for its own: there is no decision
attached to it, and a unit that moves every turn would otherwise stop the game
once per move. The result is REPORTED in the log instead, and the mortal wounds
themselves go through the ordinary MortalWoundAllocationSession, so Feel No
Pain and 06.02's allocation still apply.
"""
from game.weapons import ShadowWeaverProfile

MONOFILAMENT_SNARE_LABEL = "Monofilament Snare"

#: The printed weapon name, exported so main.py can ask the shooting
#: controller for the per-weapon hit subset without importing game/weapons.py -
#: the same shape target_acquisition.LONG_RIFLE_NAME already has.
SHADOW_WEAVER_NAME = ShadowWeaverProfile.name

#: "for each 1" - the die face that costs a mortal wound.
SNARE_MORTAL_WOUND_FACE = 1

#: "a Normal, Advance or Fall Back move" - written as the EXCLUSIONS, not as a
#: list of the included modes, and that is deliberate.
#:
#: The engine's `move_mode` is None for an ordinary Movement-phase move (which
#: covers both Normal AND Advance - an Advance has no mode of its own here, it
#: is a Normal move with a bonus, which is why MovementController.can_advance()
#: tests `move_mode is None`). Every other mode is a NAMED move, and most of
#: those named moves are still Normal moves as far as the rules are concerned:
#: Scouts (24.31), Battle Focus' Fade Back, Path of the Outcast, Tactical
#: Acumen and Retro-thrusters all print "a Normal move", so the snare should
#: bite on them too.
#:
#: What is genuinely NOT one of the three printed types is a short and stable
#: list - a Charge (11.04), a Pile-In (12.03), a Consolidate (12.07) and a
#: Surge (21.02). Naming those and admitting everything else means a future
#: granted Normal move is covered the day it is added instead of silently
#: escaping, which is the direction this repo's move-mode set has already been
#: caught getting wrong once (REACTIVE_MOVE_MODES, reported twice).
UNSNARED_MOVE_MODES = frozenset({"charge", "pile_in", "consolidate", "surge"})


def is_snaring_weapon(weapon):
    """"attacks made with its shadow weaver" - a per-WEAPON condition, so the
    platform's shuriken catapult snares nothing."""
    return isinstance(weapon, ShadowWeaverProfile)


class MonofilamentSnareController:
    """One per battle. Holds the marks and resolves the movement penalty."""

    def __init__(self, dice_manager=None, game_log=None, decision_manager=None,
                 game_state=None, turn_tracker=None):
        self.dice_manager = dice_manager
        self.game_log = game_log
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        #: id(squad) -> the player whose Shadow Weaver snared it. Held here
        #: rather than on the squad because the effect belongs to that player,
        #: exactly like the five other enemy marks in this engine.
        self._snared = {}
        self.mortal_wound_session = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    # ------------------------------------------------------------ the mark

    def is_snared(self, squad):
        return squad is not None and id(squad) in self._snared

    def snare(self, squad, by_player):
        if squad is None:
            return False
        self._snared[id(squad)] = by_player
        self._log("%s: %s is snared until the start of %s's next turn."
                  % (MONOFILAMENT_SNARE_LABEL, squad.name, by_player))
        return True

    def applies(self, squad):
        return any(getattr(m.profile, "monofilament_snare", False) and not m.is_dead()
                   for m in getattr(squad, "models", ()) or ())

    def offer_after_shooting(self, squad, hit_squads, shadow_weaver_hits=()):
        """"after this model has shot, select one enemy unit hit by one or more
        of those attacks made with ITS SHADOW WEAVER."

        `hit_squads` is what the hook hands every listener; `shadow_weaver_hits`
        is the per-WEAPON subset, supplied by main.py from the controller's own
        squads_hit_by_weapon() record - the same split Shroud Runners' Target
        Acquisition uses, and for the same reason: the plain hook cannot tell
        which weapon did the hitting, and a unit hit only by the platform's
        shuriken catapult is not a legal choice."""
        if not self.applies(squad):
            return
        candidates = [s for s in hit_squads
                      if s in shadow_weaver_hits and not self.is_snared(s)]
        if not candidates:
            return
        if len(candidates) == 1 or self.decision_manager is None:
            self.snare(candidates[0], squad.owner)
            return
        self.decision_manager.request(
            squad.owner,
            "%s: %s - which unit is snared?" % (squad.name, MONOFILAMENT_SNARE_LABEL),
            [(target.name, (lambda t=target: self.snare(t, squad.owner)), target)
             for target in candidates],
        )

    def clear_for_turn_of(self, player):
        """"Until the start of your next turn" - so a mark placed by `player`
        expires as that player's turn begins."""
        for key in [k for k, owner in self._snared.items() if owner == player]:
            del self._snared[key]

    # --------------------------------------------------------- the trigger

    def notify_move(self, squad, move_mode=None):
        """Fed from MovementController.confirm_move(), the one place every
        confirmed move passes through. Returns the number of mortal wounds
        inflicted, which is 0 for every move this ability does not name."""
        if not self.is_snared(squad) or move_mode in UNSNARED_MOVE_MODES:
            return 0
        living = [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]
        if not living:
            return 0
        rolled = [self._roll_one() for _ in living]
        wounds = sum(1 for r in rolled if r == SNARE_MORTAL_WOUND_FACE)
        self._log("[snare] %s moved while snared - %d dice, %d one(s): %d mortal wound(s)."
                  % (squad.name, len(rolled), wounds, wounds), file_only=True)
        if wounds:
            self._inflict(squad, wounds)
        return wounds

    def _roll_one(self):
        from game.dice import random as dice_random
        return dice_random.randint(1, 6)

    def _inflict(self, squad, count):
        from game.damage_resolution import MortalWoundAllocationSession
        self._log("%s: %s suffers %d mortal wound(s) for moving while snared."
                  % (MONOFILAMENT_SNARE_LABEL, squad.name, count))
        self.mortal_wound_session = MortalWoundAllocationSession(
            squad, count, dice_manager=self.dice_manager, log=self.game_log)

    @property
    def is_busy(self):
        session = self.mortal_wound_session
        return session is not None and not getattr(session, "done", True)
