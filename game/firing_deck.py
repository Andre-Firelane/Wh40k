from game.weapons import RANGED

IDLE = "idle"
CHOOSING_MODELS = "choosing_models"  # step 1: pick up to X embarked models
CHOOSING_WEAPON = "choosing_weapon"  # step 2: for the current model, pick one of its ranged weapons


class FiringDeckController:
    """Rule 24.14 (Firing Deck X): "In your Shooting phase, each time this
    TRANSPORT is selected to shoot, if one or more units are embarked within
    it, resolve the following sequence": (1) select up to X embarked models
    (excluding models whose own unit has already been selected to shoot
    this phase - structurally always true here, embarked units aren't on
    the board at all, so they can never actually be selected to shoot;
    checked anyway for correctness/robustness), (2) for each selected
    model, pick ONE of its ranged, non-[ONE SHOT] weapons, (3) until the
    TRANSPORT has resolved all of its attacks, it has all of those selected
    weapons IN ADDITION to its own, (4) until the end of the turn, units
    embarked within this TRANSPORT are not eligible to shoot - a no-op
    here for the same reason as (1): an embarked unit already can't be
    selected to shoot (it's off the board), and our phase order never
    offers another Disembark opportunity later in the same turn once the
    Shooting phase is reached, so this consequence is already guaranteed
    by the embark mechanic itself without any extra flag.

    Sits IN FRONT of the normal "Shoot" button for a Firing-Deck-capable
    TRANSPORT (main.py/action_panel.py route the button through start()
    instead of calling shooting_controller.start_shooting() directly) -
    once the borrowed weapons (if any) are attached, it hands off to the
    perfectly normal ShootingController flow via start_shooting(squad,
    on_finished=...), so weapon/target selection, split fire, hit/wound/
    save/damage, hazards etc. all just work unmodified. `on_finished` (a
    generic completion callback ShootingController now supports for ANY
    activation, not just Fire Overwatch's reactive one, see shooting.py's
    _finish_activation()) is how this controller knows when to take the
    borrowed weapons back off the TRANSPORT's own model.

    Step 1 selects MODELS, step 2 asks for a weapon PER selected model -
    two separate stages, since which weapon a model contributes isn't
    decided until step 2. Candidates aren't board tokens (they're embarked,
    off the board), so - like Fire Overwatch's squad list or Rapid
    Ingress's reserves card - this is a panel-button list
    (game/ui/action_panel.py's _draw_firing_deck_choose_models/
    _draw_firing_deck_choose_weapon), not a board click."""

    def __init__(self, shooting_controller, transport_controller, game_log=None):
        self.shooting_controller = shooting_controller
        self.transport_controller = transport_controller
        self.game_log = game_log

        self.state = IDLE
        self.transport_squad = None
        self.transport_model = None
        self.max_models = 0
        self.selected_models = []        # step 1's picks, in selection order
        self._pending_weapon_models = []  # step 2's queue, drained one model at a time
        self.acting_model = None          # the model currently choosing its weapon
        self._borrowed_weapons = []       # weapon instances currently appended to transport_model.weapons

    def _firing_deck_x(self, transport_squad):
        return max((m.profile.firing_deck for m in transport_squad.models), default=0)

    def _embarked_models(self, transport_squad):
        models = []
        for embarked_squad in self.transport_controller.embarked_squads_in(transport_squad.models[0]):
            models.extend(embarked_squad.models)
        return models

    def _eligible_weapons(self, model):
        return [w for w in model.weapons if w.weapon_type == RANGED and not w.one_shot]

    def _candidate_models(self, transport_squad):
        already_shot = self.shooting_controller.shot_squad_ids
        return [
            model for model in self._embarked_models(transport_squad)
            if model.squad not in already_shot and self._eligible_weapons(model)
        ]

    def can_use(self, transport_squad):
        if transport_squad is None or not transport_squad.models or not transport_squad.models[0].profile.transport:
            return False
        if self._firing_deck_x(transport_squad) <= 0:
            return False
        if not self.shooting_controller.can_shoot(transport_squad):
            return False
        return bool(self._embarked_models(transport_squad))  # rule: triggers whenever 1+ units are embarked, regardless of weapon eligibility

    def start(self, transport_squad):
        if not self.can_use(transport_squad):
            return
        self.transport_squad = transport_squad
        self.transport_model = transport_squad.models[0]
        self.max_models = self._firing_deck_x(transport_squad)
        self.selected_models = []
        if not self._candidate_models(transport_squad):
            self._begin_shooting()
            return
        self.state = CHOOSING_MODELS

    def choosable_models(self):
        if self.state != CHOOSING_MODELS:
            return []
        return self._candidate_models(self.transport_squad)

    def toggle_model(self, model):
        if self.state != CHOOSING_MODELS or model not in self.choosable_models():
            return
        if model in self.selected_models:
            self.selected_models.remove(model)
        elif len(self.selected_models) < self.max_models:
            self.selected_models.append(model)

    def confirm_model_selection(self):
        """Rule 24.14 allows selecting "up to X" - zero is a valid choice
        (the TRANSPORT just shoots with its own weapons)."""
        if self.state != CHOOSING_MODELS:
            return
        self._pending_weapon_models = list(self.selected_models)
        self._advance_weapon_choice()

    def _advance_weapon_choice(self):
        if not self._pending_weapon_models:
            self._begin_shooting()
            return
        self.acting_model = self._pending_weapon_models.pop(0)
        weapons = self._eligible_weapons(self.acting_model)
        if len(weapons) == 1:
            self._apply_weapon(weapons[0])
        else:
            self.state = CHOOSING_WEAPON

    def choosable_weapons(self):
        if self.state != CHOOSING_WEAPON or self.acting_model is None:
            return []
        return self._eligible_weapons(self.acting_model)

    def choose_weapon(self, weapon):
        if self.state != CHOOSING_WEAPON or weapon not in self.choosable_weapons():
            return
        self._apply_weapon(weapon)

    def _apply_weapon(self, weapon):
        """Rule 24.14 step 3: append the actual weapon instance (not a copy
        - each model already owns its own WeaponProfile instance, see
        main.py's Token construction, so there's no shared-instance risk,
        and _attack_groups() pairing it with transport_model correctly uses
        the TRANSPORT's own characteristics (BS etc.) to resolve it, "it
        has... those weapons" per the rule text)."""
        self.transport_model.weapons.append(weapon)
        self._borrowed_weapons.append(weapon)
        self.acting_model = None
        self._advance_weapon_choice()

    def _begin_shooting(self):
        squad = self.transport_squad
        self.state = IDLE
        self.transport_squad = None
        if self.game_log is not None and self._borrowed_weapons:
            names = ", ".join(w.name for w in self._borrowed_weapons)
            self.game_log.add(
                f"{squad.owner}: Firing Deck - {squad.name} borrows {names} from embarked passengers (rule 24.14)."
            )
        self.shooting_controller.start_shooting(squad, on_finished=self._on_shooting_finished)

    def _on_shooting_finished(self):
        """Rule 24.14 step 3: "until this TRANSPORT has resolved all of its
        attacks" - take the borrowed weapons back the moment that
        activation ends, whether it actually fired them or not."""
        for weapon in self._borrowed_weapons:
            if weapon in self.transport_model.weapons:
                self.transport_model.weapons.remove(weapon)
        self._borrowed_weapons = []
        self.transport_model = None

    def cancel(self):
        """Back out entirely before shooting actually begins - safe to call
        from either step: in CHOOSING_MODELS nothing's been borrowed yet;
        in CHOOSING_WEAPON some earlier-processed models' weapons may
        already be attached, so those get returned too."""
        for weapon in self._borrowed_weapons:
            if self.transport_model is not None and weapon in self.transport_model.weapons:
                self.transport_model.weapons.remove(weapon)
        self._borrowed_weapons = []
        self.state = IDLE
        self.transport_squad = None
        self.transport_model = None
        self.selected_models = []
        self._pending_weapon_models = []
        self.acting_model = None
