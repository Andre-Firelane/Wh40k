""""Nightmare Shroud" and "Harbinger of Despair" - the Psychomancer (Necrons).

RULES (printed, word for word):

  NIGHTMARE SHROUD (Aura): "In the Battle-Shock step of your opponent's
    Command phase, if an enemy unit that is below its Starting Strength is
    within 6" of this model, that enemy unit must take a Battle-Shock test,
    subtracting 1 from the test when it does so."

  HARBINGER OF DESPAIR: "Once per turn, at the start of your Command,
    Movement, Shooting, Charge or Fight phase, you can select one enemy unit
    within 18" of this model. That unit must take a Battle-Shock test,
    subtracting 1 from the test when it does so."

ONE MODULE, TWO ABILITIES, because they are the same sentence twice: a forced
Battle-Shock test at -1. Only the TRIGGER and the SELECTION differ, which is
the same reason game/battle_shock_after_shooting.py holds two abilities that
share everything but a target predicate.

NOTHING NEW IS BUILT HERE. BattleShockController.start_forced_roll() exists
for exactly "a Battle-Shock test some rule imposes out of turn" and ALREADY
TAKES A `penalty`, so the -1 needs no new arithmetic - Seer Council's
Presentiment of Dread opened that door and Neocapacitor Shields widened it.

THE TWO DIFFERENCES THAT DO REAL WORK
-------------------------------------
1. MANDATORY vs OPTIONAL. Nightmare Shroud says "must take"; there is no
   choice in it, so it is not offered, it fires. Harbinger says "you CAN
   select one enemy unit", so it is a decision - and the AI answers it through
   auto_players rather than paying for a prompt.

2. ONE UNIT vs EVERY UNIT. Harbinger picks exactly one ("select one enemy
   unit"). Nightmare Shroud is printed "(Aura)" and its condition is written
   about any qualifying unit, so every enemy unit below Starting Strength in
   range takes one. start_forced_roll() rolls for ONE squad at a time and
   refuses a second while one is open, so the aura keeps a QUEUE and drains it
   as each roll is acknowledged - the same arrangement Reanimation Protocols
   uses for the same reason.

"BELOW ITS STARTING STRENGTH" is Squad.starting_model_count, NOT the current
model count compared to some remembered number: it is what 01.02.03, Below
Half-strength and Reanimation Protocols all read, so asking it here keeps one
answer to "how big was this unit".

MEASURED FROM THE BEARER MODEL, not from the unit. Both clauses say "within
X inches of this MODEL", and the Psychomancer is a SUPPORT model whose whole
purpose is to be attached - once he is, his bodyguards are not sources, so
the distance has to be taken from him. Asked of the unit, an attached
Psychomancer would project his aura from wherever the squad happens to reach.
"""

from game import ai_mode
from game.attached_units import unit_has_keyword
from game.squad import edge_distance

#: "subtracting 1 from the test", both abilities.
BATTLE_SHOCK_PENALTY = 1

NIGHTMARE_SHROUD_RANGE_IN = 6.0
HARBINGER_RANGE_IN = 18.0

NIGHTMARE_SHROUD_LABEL = "Nightmare Shroud"
HARBINGER_LABEL = "Harbinger of Despair"


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def has_nightmare_shroud(squad):
    return squad is not None and unit_has_keyword(
        squad, lambda m: getattr(m.profile, "nightmare_shroud", False))


def has_harbinger(squad):
    return squad is not None and unit_has_keyword(
        squad, lambda m: getattr(m.profile, "harbinger_of_despair", False))


def below_starting_strength(squad):
    """"an enemy unit that is below its Starting Strength"."""
    start = getattr(squad, "starting_model_count", None)
    if not start:
        return False
    return len(_living(squad)) < start


def _bearers(squad, flag):
    """The MODELS an aura is measured from - see the module docstring."""
    return [m for m in _living(squad) if getattr(m.profile, flag, False)]


def units_in_range(squad, all_tokens, flag, range_in, extra=None):
    """Enemy units within `range_in` of a BEARER model, nearest first.

    `extra` is an optional predicate on the candidate unit - it is what
    separates the two abilities' target sets."""
    bearers = _bearers(squad, flag)
    if not bearers:
        return []
    seen, out = set(), []
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or id(other) in seen or other.owner == squad.owner:
            continue
        if not _living(other):
            continue
        if extra is not None and not extra(other):
            continue
        gap = min((edge_distance(a, b) for a in bearers for b in _living(other)),
                  default=None)
        if gap is None or gap > range_in:
            continue
        seen.add(id(other))
        out.append((gap, other))
    out.sort(key=lambda pair: (pair[0], pair[1].name))
    return [unit for _gap, unit in out]


class NightmareShroudController:
    """The mandatory aura, fired in the opponent's Battle-Shock step."""

    def __init__(self, battle_shock_controller=None, all_tokens=None, game_log=None):
        self.battle_shock_controller = battle_shock_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self._queue = []

    def candidates(self, squad):
        return units_in_range(squad, self.all_tokens, "nightmare_shroud",
                              NIGHTMARE_SHROUD_RANGE_IN, extra=below_starting_strength)

    def begin_battle_shock_step(self, squads, command_phase_player):
        """"In the Battle-Shock step of your OPPONENT's Command phase" - so the
        bearer's owner must NOT be the player whose Command phase it is."""
        self._queue = []
        for squad in sorted(squads, key=lambda s: s.name):
            if not has_nightmare_shroud(squad) or squad.owner == command_phase_player:
                continue
            for target in self.candidates(squad):
                if target not in self._queue:
                    self._queue.append(target)
        return self._drain()

    def _drain(self):
        while self._queue:
            target = self._queue[0]
            if self.battle_shock_controller is None:
                self._queue.pop(0)
                continue
            started = self.battle_shock_controller.start_forced_roll(
                target, NIGHTMARE_SHROUD_LABEL, penalty=BATTLE_SHOCK_PENALTY)
            if not started:
                return True          # a roll is already open; come back for it
            self._queue.pop(0)
            if self.game_log:
                self.game_log.add(
                    "%s is caught in the Nightmare Shroud and must take a "
                    "Battle-Shock test at -%d." % (target.name, BATTLE_SHOCK_PENALTY))
            return True
        return False

    def on_dice_acknowledged(self):
        """The queue's re-entry point - one more test per acknowledged roll."""
        return self._drain()

    @property
    def is_busy(self):
        return bool(self._queue)


class HarbingerOfDespairController:
    """Once per turn, one enemy unit within 18", at the start of any of the
    bearer's own five phases."""

    def __init__(self, battle_shock_controller=None, decision_manager=None,
                 all_tokens=None, game_log=None, auto_players=()):
        self.battle_shock_controller = battle_shock_controller
        self.decision_manager = decision_manager
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._used_this_turn = set()

    def reset_turn(self):
        """"Once per turn" - per BEARER unit, so the ledger is keyed on it."""
        self._used_this_turn = set()

    def candidates(self, squad):
        return units_in_range(squad, self.all_tokens, "harbinger_of_despair",
                              HARBINGER_RANGE_IN)

    def can_use(self, squad):
        return (has_harbinger(squad) and id(squad) not in self._used_this_turn
                and bool(self.candidates(squad)))

    def offer_at_start_of_phase(self, squads, phase_owner):
        """"at the start of YOUR Command, Movement, Shooting, Charge or Fight
        phase" - all five of them, so the only gate is that the phase belongs
        to the bearer's owner."""
        for squad in sorted(squads, key=lambda s: s.name):
            if squad.owner != phase_owner or not self.can_use(squad):
                continue
            targets = self.candidates(squad)
            if squad.owner in self.auto_players or self.decision_manager is None:
                # Deterministic for the AI: a free -1 Battle-Shock test costs
                # nothing and can only help, so it takes the nearest candidate
                # rather than paying the LLM to rank them.
                self._use(squad, targets[0])
                return True
            self.decision_manager.request(
                squad.owner,
                "%s: Harbinger of Despair - which enemy unit takes a "
                "Battle-Shock test at -%d?" % (squad.name, BATTLE_SHOCK_PENALTY),
                [(t.name, (lambda s=squad, t=t: self._use(s, t)), t) for t in targets]
                + [("Decline", lambda: None)],
            )
            return True
        return False

    def _use(self, squad, target):
        self._used_this_turn.add(id(squad))
        started = False
        if self.battle_shock_controller is not None:
            started = self.battle_shock_controller.start_forced_roll(
                target, HARBINGER_LABEL, penalty=BATTLE_SHOCK_PENALTY)
        if self.game_log:
            self.game_log.add(
                "%s uses Harbinger of Despair on %s: a Battle-Shock test at -%d."
                % (squad.name, target.name, BATTLE_SHOCK_PENALTY))
        return started
