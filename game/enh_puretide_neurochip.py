"""Retaliation Cadre Enhancement: Puretide Engram Neurochip (15 pts).

RULE (the ERRATA'd text, which is what rules/tau_empire/detachments/
Retaliation Cadre.md prints under the original):
  T'AU EMPIRE BATTLESUIT model only. Each time you target the bearer's unit
  with a Stratagem, roll one D6: on a 4+, you gain 1CP.

NOT COMMANDER FARSIGHT'S "PURETIDE'S TEACHINGS"
-----------------------------------------------
game/puretide.py is a DIFFERENT rule printed under a similar name: Farsight's
own ability, which REDUCES the CP cost of a Stratagem targeting his unit by 1,
once per battle round. This one refunds a CP on a 4+ and has no per-round
limit of its own. Two rules, two modules, each named after what it is - the
same treatment `ere_we_go.py`/`melee_crit.py` got when a second carrier turned
a convenient name into a lying one. They can even be live at once (Farsight and
a Neurochip-bearing Commander in the same Retaliation Cadre army), and then
they do different things at different moments: the discount is applied to the
price, this fires after it has been paid.

WHERE IT LANDS
--------------
StratagemController.on_targets_chosen, a listener list added for it. The
existing on_stratagem_used callback was not usable: it carries the player and
the stratagem but NOT the targets, and "targeted the bearer's UNIT" is entirely
a question about the targets. Widening that callback would have changed a
signature main.py wires to an overlay with no use for them.

Fired after stratagem.effect() has run and the CP have been spent, so a CP
gained here can never be spent by the use that granted it.

"EACH TIME" - NO LIMIT OF ITS OWN, BUT ONE THAT ALREADY EXISTS
---------------------------------------------------------------
The printed text has no once-per-phase or once-per-round clause, so none is
invented. What DOES bound it is CommandPointManager's own house-rule cap
(BONUS_CP_PER_ROUND_CAP, shared across every bonus source), and this rolls only
while bonus_cp_remaining() says a CP would actually arrive - the same "never
roll a die that cannot pay out" rule game/coordinated_leadership.py follows,
and for the same reason: a die that visibly succeeds and grants nothing reads
as a bug.

TARGETS ARE UNITS, USUALLY - AND SOMETIMES NOT
-----------------------------------------------
StratagemController.use() takes `targets` as an opaque list: most Stratagems
pass Squads, but the ledger only ever hashes them, so a Stratagem is free to
pass something else. The bearer test therefore asks each target whether it is a
squad holding a live bearer, and ignores anything that is not, rather than
assuming. A Stratagem targeting a MODEL of the bearer's unit is not counted -
"target the bearer's UNIT" is what is printed.
"""

from game import enhancements

PURETIDE_ENGRAM_NEUROCHIP = "Puretide Engram Neurochip"
NEUROCHIP_THRESHOLD = 4
NEUROCHIP_DICE_SIDES = 6
NEUROCHIP_CP = 1


def is_bearer_unit(squad):
    """A live bearer, with Retaliation Cadre checked."""
    return enhancements.is_active(squad, PURETIDE_ENGRAM_NEUROCHIP)


class PuretideNeurochipController:
    """Registered in StratagemController.on_targets_chosen by main.py."""

    def __init__(self, dice_manager=None, command_points=None, turn_tracker=None,
                 game_log=None):
        self.dice_manager = dice_manager
        self.command_points = command_points
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._queue = []
        self._rolling = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    @property
    def is_busy(self):
        return self._rolling is not None or bool(self._queue)

    def _round(self):
        return getattr(self.turn_tracker, "battle_round", 1)

    def _has_headroom(self, player):
        if self.command_points is None:
            return True
        remaining = self.command_points.bonus_cp_remaining(player, self._round())
        return remaining is None or remaining > 0

    def bearer_targets(self, player, targets):
        """Which of `targets` are units of `player` carrying the Enhancement.

        Deduplicated: a Stratagem naming the same unit twice is one trigger,
        because the printed trigger is "you target the bearer's unit"."""
        found = []
        for target in targets or ():
            if getattr(target, "owner", None) != player:
                continue
            if not is_bearer_unit(target):
                continue
            if target not in found:
                found.append(target)
        return found

    def on_targets_chosen(self, player, stratagem, targets):
        """The listener. Returns True if a roll was queued."""
        if self._rolling is not None:
            # A Stratagem used while this controller's own die is still on the
            # table (Command Re-roll during a Neurochip roll is not reachable -
            # the die is not a re-rollable kind - but a reactive Stratagem in
            # another player's window is). Queue rather than drop, so no
            # trigger is silently lost.
            pass
        units = self.bearer_targets(player, targets)
        if not units or not self._has_headroom(player):
            return False
        name = getattr(stratagem, "name", "a Stratagem")
        for squad in units:
            self._queue.append((squad, player, name))
        if self._rolling is not None:
            return True
        return self._roll_next()

    def _roll_next(self):
        if not self._queue:
            self._rolling = None
            return False
        squad, player, stratagem_name = self._queue.pop(0)
        self._rolling = (squad, player, stratagem_name)
        if self.dice_manager is None:
            self._resolve(NEUROCHIP_THRESHOLD)
            return True
        self.dice_manager.roll(
            1, NEUROCHIP_DICE_SIDES,
            label=f"{PURETIDE_ENGRAM_NEUROCHIP} ({stratagem_name})",
            success_threshold=NEUROCHIP_THRESHOLD,
            target_name=squad.name, target_squad=squad, subject_label="Rolling")
        return True

    def on_dice_acknowledged(self):
        """Called from main.py's dice-acknowledgement chain. Returns True if
        this controller owned the roll."""
        if self._rolling is None:
            return False
        values = getattr(self.dice_manager, "last_values", None) or [1]
        self._resolve(values[0])
        return True

    def _resolve(self, value):
        squad, player, stratagem_name = self._rolling
        self._rolling = None
        if value >= NEUROCHIP_THRESHOLD:
            if self.command_points is not None:
                self.command_points.gain_cp(
                    player, self._round(), NEUROCHIP_CP,
                    reason=f"{PURETIDE_ENGRAM_NEUROCHIP}, {squad.name} targeted by {stratagem_name}")
            else:
                self._log(f"{player}: {PURETIDE_ENGRAM_NEUROCHIP} rolls {value} - "
                          f"{NEUROCHIP_CP} CP.")
        else:
            self._log(f"{player}: {PURETIDE_ENGRAM_NEUROCHIP} rolls {value} - no CP "
                      f"({stratagem_name} targeted {squad.name}).")
        self._roll_next()
