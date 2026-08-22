from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT
from game.weapons import MELEE

EPIC_CHALLENGE_CP_COST = 1

IDLE = "idle"
CHOOSING_MODEL = "choosing_model"  # the unit has more than one CHARACTER model - pick which one


class EpicChallengeController:
    """Rule 15.03 (Epic Challenge, Core Stratagem, 1CP): WHEN a friendly
    CHARACTER unit is selected to fight, TARGET that unit, EFFECT: select
    one CHARACTER model in it - until the end of the phase, that model's
    melee weapons have the [PRECISION] ability (rule 24.28).

    WHEN is read as "any time during that unit's own fight activation, up
    until it actually starts resolving an attack" rather than the single
    literal instant right after selection - a small, deliberate widening
    (same kind of reading Command Re-roll, rule 15.02, already gets) so a
    mis-click into split fire etc. doesn't lock the player out of a
    stratagem window that's conceptually still open. Gated to
    `fight_controller.fighting_squad is squad` and `current_group is None`
    (no attack currently resolving) via can_use().

    Melee weapons are per-model instances (see main.py's Token
    construction - a fresh WeaponProfile() is built for every model, never
    shared), so granting [PRECISION] is a plain, safe mutation of that one
    model's own weapon.precision - reverted at the end of the Fight phase
    via reset_fight_phase(), called from the same main.py spot that resets
    FightController for a new phase."""

    def __init__(self, stratagem_controller, fight_controller, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.fight_controller = fight_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log

        self.state = IDLE
        self.acting_squad = None
        self.acting_model = None
        self._granted_weapons = []  # weapon instances currently holding a granted [PRECISION]

        self._stratagem = Stratagem(
            name="Epic Challenge", cp_cost=EPIC_CHALLENGE_CP_COST, effect=self._apply_precision, when=self._when,
        )

    def _when(self, controller, player):
        return self.turn_tracker is None or self.turn_tracker.phase == PHASE_FIGHT

    def _qualifying_models(self, squad):
        return [m for m in squad.models if m.profile.character]

    def can_use(self, squad):
        if squad is None or self.state != IDLE:
            return False
        if self.fight_controller.fighting_squad is not squad or self.fight_controller.current_group is not None:
            return False
        if not self._qualifying_models(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def start(self, squad):
        if not self.can_use(squad):
            return
        self.acting_squad = squad
        qualifying = self._qualifying_models(squad)
        if len(qualifying) == 1:
            self.choose_model(qualifying[0])
        else:
            self.state = CHOOSING_MODEL

    def choosable_models(self):
        if self.state != CHOOSING_MODEL or self.acting_squad is None:
            return []
        return self._qualifying_models(self.acting_squad)

    def choose_model(self, model):
        if self.acting_squad is None or model not in self._qualifying_models(self.acting_squad):
            return
        self.acting_model = model
        if not self.stratagem_controller.use(self.acting_squad.owner, self._stratagem, [self.acting_squad]):
            self.acting_model = None
            return
        self.state = IDLE
        self.acting_squad = None
        self.acting_model = None

    def cancel(self):
        """Back out of choosing which CHARACTER model, before CP is spent."""
        self.state = IDLE
        self.acting_squad = None
        self.acting_model = None

    def _apply_precision(self, controller, player, targets):
        model = self.acting_model
        granted = [
            weapon for weapon in model.weapons
            if weapon.weapon_type == MELEE and not weapon.precision
        ]
        for weapon in granted:
            weapon.precision = True
        self._granted_weapons.extend(granted)
        self._log(f"{player}: Epic Challenge - {model.profile.name}'s melee weapons gain [PRECISION] until the end of the phase.")

    def reset_fight_phase(self):
        """"Until the end of the phase" - revert every grant the moment the
        Fight phase itself ends."""
        for weapon in self._granted_weapons:
            weapon.precision = False
        self._granted_weapons = []
        self.state = IDLE
        self.acting_squad = None
        self.acting_model = None

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
