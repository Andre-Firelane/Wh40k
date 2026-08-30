"""The Chaos Spawn's own ability "Lethal Ichor".

RULE (printed): each time a melee attack is allocated to a model in this unit,
after the attacking unit has finished making its attacks, roll one D6 (to a
maximum of six D6 per attacking unit): on a 4+, the attacking unit suffers 1
mortal wound.

THREE THINGS MAKE THIS DIFFERENT from every other mortal-wound ability here:

  * IT COUNTS ALLOCATIONS, NOT DAMAGE. "Each time a melee attack is ALLOCATED
    to a model in this unit" fires for an attack that was saved, and for one
    that killed the model it was allocated to. So the tally is kept by the
    damage step, not derived afterwards from casualties - there is nothing on
    the board at the end from which the number could be recovered.
  * IT RESOLVES AFTER THE ATTACKER FINISHES, not at the moment of allocation.
    That instant already exists as FightController.on_unit_finished_fighting,
    the same seam Protocol of the Vengeful Stars uses.
  * THE CAP IS PER ATTACKING UNIT, not per phase and not per Spawn. Two
    different enemy units each pay their own six dice; one enemy unit attacking
    twice does not.

IT HURTS THE ATTACKER, which is the reverse of every other mortal-wound source
in this engine - so the MortalWoundAllocationSession is built against the
ATTACKING squad. Its pending_damage_choice therefore belongs to the attacking
player, which is exactly right: they choose which of their own models dies.

NOT OPTIONAL - the printed text has no "you can", so there is no prompt and no
auto_players fork, and it cannot cost an API call.
"""
from game.damage_resolution import MortalWoundAllocationSession

LETHAL_ICHOR_THRESHOLD = 4      # "on a 4+"
LETHAL_ICHOR_MAX_DICE = 6       # "to a maximum of six D6 per attacking unit"


def has_lethal_ichor(squad):
    if squad is None:
        return False
    return any(getattr(m.profile, "lethal_ichor", False) and not m.is_dead()
               for m in getattr(squad, "models", ()) or ())


class LethalIchorController:
    """Counts allocations during the Fight phase, resolves when the attacking
    unit is done."""

    def __init__(self, dice_manager=None, game_log=None):
        self.dice_manager = dice_manager
        self.game_log = game_log
        # (id(spawn squad), id(attacking squad)) -> allocations counted
        self._tally = {}
        self._pending = None            # {"attacker": squad, "dice": n}
        self.mortal_wound_session = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    @property
    def is_busy(self):
        return self._pending is not None or self.mortal_wound_session is not None

    # --- counting ---------------------------------------------------------

    def notify_melee_allocation(self, target_squad, attacking_squad):
        """Called once per melee attack allocated to a model of `target_squad`.

        Counting here rather than reconstructing later is the point: a saved
        attack was still allocated, and by the time the attacker has finished
        there is nothing left to count."""
        if not has_lethal_ichor(target_squad) or attacking_squad is None:
            return
        key = (id(target_squad), id(attacking_squad))
        self._tally[key] = min(LETHAL_ICHOR_MAX_DICE, self._tally.get(key, 0) + 1)

    def dice_owed_by(self, attacking_squad):
        """How many D6 this attacking unit currently owes, across every Spawn
        unit it hit. Capped PER Spawn unit, then summed - two Chaos Spawn units
        each get their own six."""
        if attacking_squad is None:
            return 0
        return sum(n for (_, attacker_id), n in self._tally.items()
                   if attacker_id == id(attacking_squad))

    # --- resolving --------------------------------------------------------

    def on_unit_finished_fighting(self, attacking_squad, *args):
        """FightController's hook: "after the attacking unit has finished
        making its attacks"."""
        dice = self.dice_owed_by(attacking_squad)
        if dice <= 0 or self.dice_manager is None:
            return False
        self._clear_tally_for(attacking_squad)
        self._pending = {"attacker": attacking_squad, "dice": dice}
        self.dice_manager.roll(
            dice, 6, label=f"Lethal Ichor ({dice}D6)",
            success_threshold=LETHAL_ICHOR_THRESHOLD,
            target_name=attacking_squad.name, target_squad=attacking_squad,
            subject_label="Splashed",
        )
        return True

    def _clear_tally_for(self, attacking_squad):
        for key in [k for k in self._tally if k[1] == id(attacking_squad)]:
            del self._tally[key]

    def on_dice_acknowledged(self):
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_session_done()
            return True
        if self._pending is None or self.dice_manager is None:
            return False
        attacker = self._pending["attacker"]
        self._pending = None
        rolls = self.dice_manager.last_values or []
        wounds = sum(1 for r in rolls if r >= LETHAL_ICHOR_THRESHOLD)
        if wounds <= 0:
            self._log(f"[lethal ichor] {attacker.name}: {rolls} - nothing got through.",
                      file_only=True)
            return True
        self._log(f"Lethal Ichor: {attacker.name} rolled {rolls} "
                  f"(needed {LETHAL_ICHOR_THRESHOLD}+) - it suffers {wounds} mortal wound(s).")
        self.mortal_wound_session = MortalWoundAllocationSession(
            attacker, wounds, dice_manager=self.dice_manager, log=self._log)
        self._check_session_done()
        return True

    def _check_session_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None

    @property
    def pending_damage_choice(self):
        """Spelled exactly as main.py's event chain and the AI's own
        _resolve_own_damage_choice() key on - see game/deadly_vectors.py's own
        note on why that name is load-bearing."""
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_session_done()

    def reset_phase(self):
        """The tally is per Fight phase - an attacking unit that never finished
        its attacks (the phase ended, it was destroyed) owes nothing next time."""
        self._tally.clear()
