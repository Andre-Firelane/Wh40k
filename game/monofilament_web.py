"""The Night Spinner's "Monofilament Web" - a datasheet ability.

RULE (printed, word for word):
  "In your Shooting phase, after this model has shot, if one or more of those
  attacks made with its doomweaver scored a hit against an enemy unit, until
  the start of your next turn, that enemy unit is pinned. While a unit is
  pinned, subtract 2 from that unit's Move characteristic and subtract 2 from
  Charge rolls made for it."

PINNED IS NOT SHAKEN, AND THE DIFFERENCE IS ONE CLAUSE
------------------------------------------------------
Mont'ka's Pulse Onslaught (game/montka_pulse_onslaught.py) applies SHAKEN,
which is -2 Move, -2 ADVANCE and -2 Charge. Pinned is -2 Move and -2 Charge and
says nothing about Advance rolls. Two of the three seams are shared, and the
third is exactly the reason these are two statuses rather than one flag: a
single "slowed" status would silently hand the Night Spinner an Advance penalty
its datasheet does not print. Same call `tank_hunters_modifiers()` records for
the two abilities that share ITS name.

They STACK, and that is deliberate rather than accidental: a unit that is both
pinned and shaken has two separate printed effects on it, so the penalties add.
Each is read from its own module at each seam.

"UNTIL THE START OF YOUR NEXT TURN" is the marking player's next turn, so the
lifetime is stored as the applying player and cleared when that player's turn
begins - the same clock game/monofilament_snare.py uses, and one turn boundary
further out than a Guide/Doom mark.

"WITH ITS DOOMWEAVER" is a per-WEAPON condition, so a unit hit only by the
Night Spinner's twin shuriken catapult is not pinned. The per-weapon subset
comes from ShootingController.squads_hit_by_weapon(), the record Shroud
Runners' Target Acquisition already needed.

"IF ONE OR MORE ... SCORED A HIT" has no "select": unlike Monofilament Snare on
the Shadow Weaver, there is nothing to choose. Every unit the doomweaver hit is
pinned, so there is no prompt and nothing for `auto_players` to answer.
"""
from game import pinned as _pinned
from game.weapons import DoomweaverProfile

MONOFILAMENT_WEB_LABEL = "Monofilament Web"

# THE STATUS ITSELF NOW LIVES IN game/pinned.py, extracted at the second source
# (the Geomancer's Tectonic Reverberations prints the same two sentences).
# Re-exported here under the names this module has always had, so every caller
# - game/charge.py, game/coldstar.py and the Aeldari suite - is unchanged by
# construction. Only the CLOCK is this ability's own: "until the start of your
# next turn".
PINNED_MOVE_PENALTY = _pinned.PINNED_MOVE_PENALTY
PINNED_CHARGE_PENALTY = _pinned.PINNED_CHARGE_PENALTY
is_pinned = _pinned.is_pinned
move_penalty_for = _pinned.move_penalty_for
charge_penalty_for = _pinned.charge_penalty_for

#: Exported so main.py can ask for the per-weapon hit subset without importing
#: game/weapons.py - the shape target_acquisition.LONG_RIFLE_NAME has.
DOOMWEAVER_NAME = DoomweaverProfile.name


class MonofilamentWebController:
    """One per battle. Applies the pins and expires them."""

    def __init__(self, game_log=None, game_state=None):
        self.game_log = game_log
        self.game_state = game_state

    def is_pinned(self, squad):
        return is_pinned(squad)

    def applies(self, squad):
        return any(getattr(m.profile, "monofilament_web", False) and not m.is_dead()
                   for m in getattr(squad, "models", ()) or ())

    def pin(self, squad, by_player):
        """Delegates to game/pinned.py, naming THIS ability's clock ("until
        the start of your next turn"). The ensnared check and the log line
        live there, with the status."""
        return _pinned.pin(
            squad, by_player, until=_pinned.UNTIL_TURN,
            log=(self.game_log.add if self.game_log is not None else None),
            label=MONOFILAMENT_WEB_LABEL)

    def after_shooting(self, squad, hit_squads, doomweaver_hits=()):
        """No choice to make - every unit the doomweaver hit is pinned."""
        if not self.applies(squad):
            return 0
        pinned = 0
        for target in hit_squads:
            if target in doomweaver_hits and self.pin(target, squad.owner):
                pinned += 1
        return pinned

    def clear_for_turn_of(self, player, squads=()):
        """"Until the start of YOUR next turn" - a pin placed by `player`
        expires as that player's turn begins.

        Takes the squads explicitly (or reads the board) because the status
        lives on the squads themselves; there is no central registry to walk."""
        return _pinned.clear_at(player, _pinned.UNTIL_TURN,
                                squads or self._squads())

    def _squads(self):
        seen = []
        for token in (getattr(self.game_state, "tokens", None) or ()):
            squad = getattr(token, "squad", None)
            if squad is not None and squad not in seen:
                seen.append(squad)
        return seen
