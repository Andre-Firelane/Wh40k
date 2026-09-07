"""Retaliation Cadre Enhancement: Internal Grenade Racks (20 pts).

RULE (verbatim, rules/tau_empire/detachments/Retaliation Cadre.md):
  T'AU EMPIRE BATTLESUIT model only. The bearer has the GRENADES keyword, and
  each time the bearer ends a Normal move, you can select one enemy unit that
  it moved over during that move. If you do, roll six D6: for each 4+, that
  enemy unit suffers 1 mortal wound.

TWO EFFECTS, AND THE FIRST ONE IS A KEYWORD
--------------------------------------------
"The bearer has the GRENADES keyword" is not decoration: rule 15.05
(Explosives) targets "one EXPLOSIVES/GRENADES unit", and game/explosives.py
reads exactly `profile.explosives or profile.grenades` to find its qualifying
models. So the keyword is answered through has_grenades_keyword() below, which
that one call site now asks - rather than by having grant() quietly write a
SECOND profile flag. One Enhancement, one flag, and the keyword derived from
it: two flags meaning the same thing is how a later "clean-up" ends up removing
the wrong one.

"MOVED OVER" IS ALREADY DECIDED, AND NOT BY THIS MODULE
--------------------------------------------------------
game/wraith_form.py settled it for the Canoptek Wraiths' identically worded
ability, and wrote out why: this engine records where each model started and
where it ended, not the drag in between, so "moved over" is the straight
segment from start to end passing within touching distance of an enemy base.
That is exact for an ordinary move to a destination, and it is the only reading
the recorded data supports. Reused here rather than re-derived - two answers to
"did this model pass over that one" is exactly the drift this repo consolidates.

THE START POINTS come from MovementController.last_move_start, which survives
_clear_move_state() specifically so on_move_finished listeners can still read
them.

PER MODEL, WHERE WRAITH FORM IS PER UNIT - the one real difference in the
trigger. "each time THE BEARER ends a Normal move" and "one enemy unit that IT
moved over": after a rule 19.01 merge the bearer is one Commander inside a
Crisis unit, and only HIS path counts. A unit-level reading would let three
bodyguards' paths find a target the Commander never went near. Its own test
line, because the two abilities are otherwise word for word.

SIX D6 FLAT, not one per model - the other difference, and the reason
dice_count is a constant here and a function there.

NORMAL MOVES ONLY. MovementController.on_move_finished passes the move KIND,
and the printed text names "a Normal move": an Advance, a Fall Back, a charge
or a pile-in does not trigger it.

OPTIONAL ("you can"), so a human is asked which enemy unit - or none. An owner
in `auto_players` answers deterministically by the shared
game/damage_estimate.py measure, exactly as Wraith Form does, so the engine
never stalls on a prompt nobody will answer. That is a rule answering its own
prompt, not an AI path (the standing T'au rule).
"""

from game import ai_mode, enhancements, wraith_form

INTERNAL_GRENADE_RACKS = "Internal Grenade Racks"
MORTAL_WOUND_THRESHOLD = 4          # "for each 4+"
GRENADE_RACK_DICE = 6               # "roll six D6"
GRENADE_RACK_MOVE_KIND = wraith_form.WRAITH_FORM_MOVE_KIND   # "a Normal move"


def bearer_models(squad):
    """Every live bearer in `squad`, with Retaliation Cadre checked."""
    if not enhancements.is_active(squad, INTERNAL_GRENADE_RACKS):
        return []
    return enhancements.bearer_models(squad, INTERNAL_GRENADE_RACKS)


def has_grenades_keyword(model):
    """"The bearer has the GRENADES keyword" - rule 15.05's own question,
    asked of the model rather than of a second profile flag.

    The detachment is checked here too: an Enhancement a player did not bring
    grants no keyword, which is the same gate every other half of every one of
    these rules goes through."""
    if model is None:
        return False
    return enhancements.model_is_active(model, INTERNAL_GRENADE_RACKS)


def units_moved_over(model, starts, all_tokens):
    """Every enemy unit THIS MODEL passed over, using game/wraith_form.py's
    settled geometry. A one-model wrapper around the unit-level function there,
    so the two cannot answer differently."""
    if model is None or model.is_dead():
        return []
    squad = getattr(model, "squad", None)
    if squad is None:
        return []

    class _JustThisModel:
        owner = squad.owner
        models = (model,)

    return wraith_form.units_moved_over(_JustThisModel, starts, all_tokens)


class InternalGrenadeRacksController:
    """Wired to MovementController.on_move_finished in main.py - the same
    listener list Isha's Fury, Path of the Outcast, Grenade Pack Flyover and
    Wraith Form already share."""

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, movement_controller=None, auto_players=(),
                 target_pick=None):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.movement_controller = movement_controller
        self.auto_players = ai_mode.players(auto_players)
        # target_pick(attacker, candidates) -> chosen squad; main.py passes the
        # shared damage-value ranking, so a non-human owner answers by the same
        # measure every other deterministic target choice here uses.
        self.target_pick = target_pick
        self._pending = None
        self.mortal_wound_session = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    @property
    def is_busy(self):
        return self._pending is not None

    def candidates(self, model):
        starts = getattr(self.movement_controller, "last_move_start", {}) if self.movement_controller else {}
        return units_moved_over(model, starts, self._tokens())

    def on_move_finished(self, squad, kind):
        """The listener. Returns True if anything was offered or used."""
        if kind != GRENADE_RACK_MOVE_KIND or self._pending is not None:
            return False
        bearers = bearer_models(squad)
        if not bearers:
            return False
        # One bearer per unit is the only build this engine can produce
        # (game/enhancements.py's grant() refuses a second), but the loop keeps
        # that a fact about grant() rather than an assumption here.
        for model in bearers:
            targets = self.candidates(model)
            if not targets:
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                return self._use(squad, model, self._pick(squad, targets))
            options = [
                (f"{INTERNAL_GRENADE_RACKS}: {t.name} ({GRENADE_RACK_DICE} D6, "
                 f"1 mortal wound per {MORTAL_WOUND_THRESHOLD}+)",
                 (lambda target=t, m=model: self._use(squad, m, target)), t)
                for t in targets
            ]
            options.append(("Decline", None))
            self.decision_manager.request(
                squad.owner,
                f"{model.profile.name} moved over an enemy unit - use {INTERNAL_GRENADE_RACKS}?",
                options)
            return True
        return False

    def _pick(self, squad, targets):
        if self.target_pick is not None:
            chosen = self.target_pick(squad, targets)
            if chosen is not None:
                return chosen
        return sorted(targets, key=lambda s: s.name)[0]

    def _use(self, squad, model, target):
        if target is None:
            return False
        self._pending = {"squad": squad, "model": model, "target": target}
        self.dice_manager.roll(
            GRENADE_RACK_DICE, 6, label=INTERNAL_GRENADE_RACKS,
            success_threshold=MORTAL_WOUND_THRESHOLD,
            target_name=target.name, attacker_squad=squad, target_squad=target)
        return True

    def on_dice_acknowledged(self):
        # A Feel No Pain roll inside the allocation is acknowledged here too -
        # the same branch CrushingImpactController opens with, and the reason
        # this method cannot simply return False whenever _pending is empty.
        if (self._pending is None and self.mortal_wound_session is not None
                and self.mortal_wound_session.pending_fnp is not None):
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_allocation_done()
            return True
        if self._pending is None:
            return False
        ctx, self._pending = self._pending, None
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or []
        wounds = sum(1 for v in values if v >= MORTAL_WOUND_THRESHOLD)
        target = ctx["target"]
        who = ctx["model"].profile.name
        if not wounds:
            self._log(f"{INTERNAL_GRENADE_RACKS} ({who}): {values} - no mortal wounds.")
            return True
        self._log(f"{INTERNAL_GRENADE_RACKS} ({who}): {values} - {target.name} suffers "
                  f"{wounds} mortal wound(s).")
        from game.damage_resolution import MortalWoundAllocationSession
        self.mortal_wound_session = MortalWoundAllocationSession(
            target, wounds, dice_manager=self.dice_manager,
            log=(lambda m: self._log(m)) if self.game_log is not None else None)
        return True

    @property
    def pending_damage_choice(self):
        """Rule 06.02: the DEFENDER allocates. Shaped exactly like
        CrushingImpactController's, so main.py's damage-choice lists can hold
        this controller beside the others without a special case."""
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_allocation_done()

    def _check_allocation_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
