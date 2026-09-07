"""AI MODE: is the AI playing, or is a human doing both sides?

ONE SWITCH, and that is the whole point of this module. User, after a game
spent with the red corner dot off: "Protokoll of undying legions wurde wieder
automatisch ausgefuehrt, obwohl KI Modus aus war" - and then, when asked why
the two might be separate things: "das ist fuer mich das gleiche. KI - Modus
ist autoplay, erkennbar am roten punkt. das steuert auch, ob die ki pfade fuer
faehigkeiten und stratagems aktiviert sind. verstehe nicht warum man das
trennen sollte."

Before this, the AI acted through TWO ungated channels and only one of them
listened to that dot:

  1. ai/agent_driver.py's take_one_action(), stepped once per frame while
     auto-play was on - gated by the dot.
  2. the ~83 `auto_players` gates inside the ability and Stratagem
     controllers, which answer the AI's own prompts for free and
     deterministically - NOT gated by anything.

Measured on the reported game (logs/game_20260904_174253.log): the dot went off
at line 17, the human hand-placed all eight of Player 2's units - so channel 1
really had stopped - and at line 175 channel 2 still spent a CP on Protocol of
the Undying Legions with nobody having clicked anything.

WHO vs WHETHER. config.AI_PLAYERS still says WHICH side is the AI's; this
module says whether that side is currently being played by the engine at all.
Keeping them apart is what lets the answer to "who" stay frozen for a whole
battle (every controller snapshots it in __init__) while "whether" stays live.

HOW A LIVE ANSWER REACHES 81 FROZEN GATES. Every controller normalises its
argument once, in its own __init__, and then only ever asks `player in
self.auto_players`. So the members stay frozen and the MEMBERSHIP TEST is what
became live: players() hands back a view whose __contains__ is "the mode is on
AND this player is one of them". Not one of the ~90 read sites had to change,
and none of them can drift out of step, because there is nothing left to keep
in step.

THE DEFAULT IS ON, AND A BATTLE STARTS OFF - which is not a contradiction but
the same "who vs whether" split again. With nobody driving a UI, the frozen
members already say everything there is to say ("Player 2 is the AI"), so a
caller that hands a controller `auto_players=("Player 2",)` and expects it to
be answered for is right - that is what ~18 suites assert, and they should not
each have to opt in to a mode that only exists inside a running game. main()
then sets it explicitly at the start of every battle, exactly where it used to
write `ai_auto_play = False`: the AI does nothing until the dot is switched on,
which is how this game has always started, and which is why the ten headless
harnesses - all of which send Shift+A themselves - are unaffected.

Per battle rather than per session, again matching the local it replaces. A
mode that survived into the next battle would be the kind of setting you have
to remember you left on.
"""

_enabled = True


def enabled():
    """Is the AI playing itself right now?"""
    return _enabled


def set_enabled(value):
    """Turn the mode on or off. Returns the new state."""
    global _enabled
    _enabled = bool(value)
    return _enabled


def toggle():
    """Flip it. Returns the new state."""
    return set_enabled(not _enabled)


class AutoAnswerPlayers:
    """The set of players the engine answers for - but only while the mode is
    on.

    Behaves like the frozen set every controller used to build, except that
    every question about membership is asked of the LIVE mode as well. That is
    what makes one switch reach gates that were built once, at the start of the
    battle, and never rebuilt.

    __iter__ and __len__ follow the same rule rather than reporting the frozen
    members: a caller writing `if self.auto_players:` or iterating it is asking
    the same question in another shape, and two shapes of one question that can
    disagree is the drift this repo keeps consolidating away."""

    __slots__ = ("_members",)

    def __init__(self, members=()):
        self._members = frozenset(members or ())

    @property
    def members(self):
        """Who WOULD be answered for, mode aside - for tests and diagnostics."""
        return self._members

    def __contains__(self, player):
        return _enabled and player in self._members

    def __iter__(self):
        return iter(self._members if _enabled else ())

    def __len__(self):
        return len(self._members) if _enabled else 0

    def __bool__(self):
        return bool(_enabled and self._members)

    def __getitem__(self, index):
        """Positional access, for the two `ai_players[0]` call sites in main().

        Both sit behind `if not ai_players: return`, and __bool__ above is
        already False while the mode is off - so this cannot be reached in a
        state where it would have to invent a player."""
        return sorted(self._members if _enabled else ())[index]

    def __eq__(self, other):
        if isinstance(other, AutoAnswerPlayers):
            return self._members == other._members
        if isinstance(other, (set, frozenset)):
            return set(self) == set(other)
        return NotImplemented

    def __hash__(self):
        return hash(self._members)

    def __repr__(self):
        state = "on" if _enabled else "off"
        return f"AutoAnswerPlayers({sorted(self._members)}, mode {state})"


class HumanPlayers:
    """The complement: everyone in this battle the engine does NOT answer for.

    A separate class rather than a second frozen tuple, for the reason the
    module docstring gives: with the mode off there is no AI side at all, so
    EVERY player is a human one - and the one consumer of this
    (game/scouts.py's Scouts offer) then asks about both armies instead of
    quietly taking one side's pre-battle move. It reads the live view rather
    than a copy of its members, so the two can never disagree."""

    __slots__ = ("_all", "_ai")

    def __init__(self, all_players, ai_players):
        self._all = frozenset(all_players or ())
        self._ai = players(ai_players)

    def __contains__(self, player):
        return player in self._all and player not in self._ai

    def __iter__(self):
        return iter(sorted(p for p in self._all if p not in self._ai))

    def __len__(self):
        return sum(1 for _ in self)

    def __bool__(self):
        return any(True for _ in self)

    def __repr__(self):
        return f"HumanPlayers({list(self)})"


def humans(all_players, ai_players):
    """The live complement of `ai_players` within this battle's players."""
    return HumanPlayers(all_players, ai_players)


def players(auto_players):
    """The one normaliser every controller's __init__ calls.

    Replaces the `set(auto_players)` / `tuple(auto_players)` each of them used
    to write. Idempotent, so a controller handed another controller's view (the
    CommandPhaseMark subclasses pass theirs down to their base) does not wrap it
    twice."""
    if isinstance(auto_players, AutoAnswerPlayers):
        return auto_players
    return AutoAnswerPlayers(auto_players)
