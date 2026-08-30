from game.dice import DAMAGE_ROLL
from game.dice_notation import DiceNotationRoll
from game import damage_reduction, molten_form
from game import plagues  # imports only game/modifiers.py, so this cannot cycle
from game.feel_no_pain import FeelNoPainRoll
from game.enforcer_commander import adjusted_ap as enforcer_commander_adjusted_ap
from game.ramshackle import adjusted_ap as ramshackle_adjusted_ap
from game.thresholds import parse_threshold
from game.invulnerable_save import effective_invulnerable_save
from game.weapons import MELEE  # imports only dice_notation, so this cannot cycle


def _resolve_save(roll, ap, sv_threshold, insv_threshold):
    """Rule 05.04: unmodified 1 always inflicts damage; an invulnerable save
    (unmodified by AP) or an armor save (modified by AP) can stop it;
    anything else inflicts damage."""
    if roll == 1:
        return "damage"
    if insv_threshold is not None and roll >= insv_threshold:
        return "no_damage"
    if sv_threshold is not None and (roll + ap) >= sv_threshold:
        return "no_damage"
    return "damage"


def save_thresholds(model, weapon, waaagh=None):
    """The three numbers rule 05.04's save actually turns on, for ONE model
    against ONE weapon: the printed armour save, the invulnerable save in
    force, and the AP actually applying.

    Pulled out so that the DISPLAY and the RESOLUTION cannot disagree. They
    did: the dice panel was handed only `armour + (-weapon.ap)`, so a die that
    passed on the INVULNERABLE save was shown red and counted among the
    failures - user report, "oft werden bestandene rettungswuerfe rot
    angezeigt". A Riptide (Sv3+/Inv4+) under AP-2 is the plain case: its
    armour is a 5+ there, so a rolled 4 saves on the invuln and looked failed.
    The Battlewagon's Ramshackle had the mirror problem (the panel did not
    know the AP had been worsened against it).

    The Death Guard Plague Rattlejoint Ague ("worsen the Save characteristic
    of models in this unit by 1") lands on `sv` and deliberately not on `insv`
    or `ap`: it names the Save CHARACTERISTIC, which is the printed armour
    save, so an invulnerable save is untouched and AP still applies on top.
    Here rather than at the two callers precisely because this function exists
    to stop the panel and the resolution disagreeing about a save."""
    sv = parse_threshold(model.profile.armor_save)
    if sv is not None:
        sv += plagues.save_penalty(getattr(model, "squad", None))
        # Advanced Acquisition Cadre's Autoreactive Camouflage: "+1 Sv" is a
        # BETTER save, so it SUBTRACTS from the threshold - the mirror of the
        # Plague penalty on the line above, and in the same place so the dice
        # panel and the resolution keep agreeing about a save.
        from game import aac_autoreactive_camouflage
        sv -= aac_autoreactive_camouflage.save_bonus_for(getattr(model, "squad", None))
    insv = parse_threshold(effective_invulnerable_save(
        model, waaagh, melee=getattr(weapon, "weapon_type", None) == MELEE,
    ))
    # Two AP adjustments, applied in turn rather than folded: Ramshackle but
    # Rugged belongs to the MODEL being allocated to, the Enforcer Commander's
    # aura belongs to its UNIT and only to ranged attacks. No model has both
    # today, but composing them is what the printed texts say, where a max()
    # would silently cap two independent effects at one.
    ap = ramshackle_adjusted_ap(weapon.ap, model)
    return sv, insv, enforcer_commander_adjusted_ap(ap, model, weapon)


def displayed_save_threshold(model, weapon, waaagh=None):
    """The single number a save die has to REACH to save - the best of the
    AP-modified armour save and the (AP-proof) invulnerable save, which is
    exactly what _resolve_save() above lets through.

    None when neither can ever save; the callers turn that into the 7 that
    marks "no passing roll exists". Note the unmodified-1 rule is NOT folded
    in here - DiceManager.is_success() applies that itself, for every kind of
    roll."""
    sv, insv, ap = save_thresholds(model, weapon, waaagh)
    reachable = [t for t in ((sv - ap) if sv is not None else None, insv) if t is not None]
    return min(reachable) if reachable else None


def _select_candidates(group):
    """Rule 05.04 step 1: models that have already lost wounds must be chosen
    from, if any exist in the group; otherwise every living model in the
    group is an eligible candidate. When more than one candidate qualifies,
    it's the defending player's choice which one takes the wound - that's
    what DamageAllocationSession.pending_choice surfaces."""
    damaged = [m for m in group if not m.is_dead() and m.current_wounds < m.profile.wounds]
    if damaged:
        return damaged
    return [m for m in group if not m.is_dead()]


def _reroll_label(offer):
    """The ability that owns this re-roll, for the dice label.

    It used to read "Sunforge" unconditionally, which was true while
    game/sunforge.py was the only source and a lying name the moment
    Assured Destruction became the second - the same rename this repo
    makes whenever a second carrier arrives."""
    return getattr(offer, "label", None) or "re-roll"


class DamageAllocationSession:
    """Rule 05.04: processes save-roll results from lowest to highest.
    Damage is allocated within the current allocation group (Squad.
    allocation_groups) until every model in it is destroyed, only then
    moving on to the next group. Stops early - excess attacks are lost -
    once every model in the target unit has been destroyed.

    Whenever a failed save's group has more than one valid candidate model,
    the session pauses (`pending_choice` holds the candidates) until the
    defending player calls choose_model(...) - the controlling player's own
    choice is real, not auto-resolved. Ghostkeel Battlesuit's "Stealth
    Drones" ability (user-supplied, not a core rule - see
    game/stealth_drones.py): right after a model has been determined as the
    recipient of an attack (i.e. right here, before the Damage roll and
    Feel No Pain), the session pauses (`pending_stealth_drones`) on a
    DecisionManager choice of whether to reduce that attack's Damage
    characteristic to 0. When the weapon's Damage is itself dice-notation
    (`weapon.damage_notation` - e.g. a printed "D6", see
    game/weapons.py's TwinFusionBlasterProfile) and Stealth Drones didn't
    already zero it out, the session pauses again (`pending_damage_roll`
    holds the in-progress DiceNotationRoll) to roll it for real, once per
    attack allocated to a model - a real, visible dice step (found missing
    via a user report: this used to just apply the die's max value as a
    silent, fixed placeholder, with nothing ever rolled or shown) - before
    Feel No Pain gets a chance to reduce whatever that rolled amount turns
    out to be. Rule 24.12 (Feel No Pain): whenever a model about to take
    damage (after any Stealth Drones reduction and Damage roll) has this
    ability, the session also pauses (`pending_fnp` holds the in-progress
    FeelNoPainRoll) until its dice roll is acknowledged via
    on_fnp_acknowledged() - a real extra dice step, not a silent reduction."""

    def __init__(
        self, rolls, weapon, target_squad, dice_manager=None, log=None, priority_group=None, stealth_drones=None,
        waaagh=None, damage_reroll=None,
    ):
        self.weapon = weapon
        self.target_squad = target_squad
        self.dice_manager = dice_manager
        self.log = log
        self.stealth_drones = stealth_drones
        self.waaagh = waaagh  # Orks army rule "Waaagh!" - optional, like stealth_drones; see game/waaagh.py
        # Optional collaborator offering a re-roll of a dice-notation Damage
        # roll, with maybe_offer(total, on_resolved) -> bool, same contract
        # stealth_drones satisfies. Crisis Sunforge Battlesuits' Sunforge
        # ability is the only source today (game/sunforge.py); the session
        # deliberately doesn't know which ability it is, only that something
        # may want to re-roll. Passed only by game/shooting.py - Sunforge is
        # ranged-only, so game/fight.py builds its session without one.
        self.damage_reroll = damage_reroll
        # Set by the OWNING controller right after construction (it needs the
        # session object to bind against). Called whenever one of the two
        # asynchronous collaborators above - Stealth Drones, or the Damage
        # re-roll - answers its DecisionManager prompt and resumes this
        # session from OUTSIDE the controller's own call chain.
        #
        # Real freeze, found via user report ("nach meinem letzten Beschuss
        # mit den Sunforge ist das Spiel eingefroren - kein Knopf hat mehr
        # reagiert"): every path that drives this session from a controller
        # (_begin_damage_allocation(), choose_damage_model(), the "allocate"
        # dice branch) follows it with that controller's own
        # _check_allocation_done(). A DecisionManager callback does not - it
        # returns into DecisionManager.choose(), which knows nothing about
        # shooting/fight. So when the answer to such a prompt is what
        # FINISHES the session (the last allocated attack, or the target
        # dying and the rest of the attacks being wasted), nothing ever ran
        # the "this weapon group is done" step: the controller stayed stuck
        # mid-group with no dice and no prompt left to click, which is a
        # hard soft-lock - the whole activation, and with it the phase, can
        # never be ended.
        self.on_resumed = None
        self._groups = [list(g) for g in target_squad.allocation_groups() if g]
        if priority_group:
            # Rule 24.28 ([PRECISION]): the chosen CHARACTER-containing group
            # becomes "the current allocation group" until these attacks are
            # resolved or that group is destroyed - a stable sort preserves
            # the normal rule 05.03 order among every other group, so this
            # is the only change: the matching group moves to the front.
            priority_models = set(priority_group)
            self._groups.sort(key=lambda g: 0 if priority_models & set(g) else 1)
        self._rolls = sorted(rolls)
        self.saved = 0
        self.failed = 0
        self.pending_choice = None
        self._pending_roll = None
        self.pending_stealth_drones = False
        self.pending_damage_roll = None
        # True while a Damage re-roll offer is on the table and unanswered.
        # Counts as "mid step" for exactly the same reason
        # pending_stealth_drones does: the attack it belongs to has not been
        # applied yet, so the session is NOT done - without this, a session
        # whose last save-roll die is the one being offered reported done ==
        # True while the prompt was still open, and the controller closed the
        # weapon group early, logged its summary and released the squad, only
        # for the damage to land afterwards on a session it no longer owned.
        self.pending_damage_reroll = False
        self._damage_roll_model = None
        self._damage_roll_value = None
        self.pending_fnp = None
        self._fnp_model = None
        self._fnp_roll_value = None
        self._advance()

    @property
    def done(self):
        return (
            not self._rolls and self.pending_choice is None
            and not self.pending_stealth_drones and self.pending_damage_roll is None
            and not self.pending_damage_reroll
            and self.pending_fnp is None
        )

    def _current_group(self):
        while self._groups and all(m.is_dead() for m in self._groups[0]):
            self._groups.pop(0)
        return self._groups[0] if self._groups else None

    def _mid_step(self):
        return (
            self.pending_stealth_drones or self.pending_damage_roll is not None
            or self.pending_damage_reroll or self.pending_fnp is not None
        )

    def _notify_resumed(self):
        """Hand control back to the owning controller after an asynchronous
        collaborator callback has carried this session forward - see
        on_resumed's own note above. Called at every exit of such a
        callback, not only when the session ended: the controller's check is
        a no-op while the session is still busy, and calling it
        unconditionally means no future exit path can be forgotten."""
        if self.on_resumed is not None:
            self.on_resumed()

    def _advance(self):
        if self._mid_step():
            return
        while self._rolls:
            group = self._current_group()
            if group is None:
                if self.log is not None:
                    self.log("The rest of the attacks are wasted (unit destroyed).")
                self._rolls = []
                return

            roll = self._rolls.pop(0)
            sv_threshold, insv_threshold, effective_ap = save_thresholds(
                group[0], self.weapon, self.waaagh,
            )
            # Waaagh!'s granted 5+ invulnerable, a printed invulnerable that
            # improves against melee (Howling Banshees), and the Battlewagon's
            # Ramshackle AP worsening all live in save_thresholds() above -
            # one definition, so the dice panel colours a die by the same
            # numbers this line resolves it with.
            outcome = _resolve_save(roll, effective_ap, sv_threshold, insv_threshold)

            if outcome == "no_damage":
                self.saved += 1
                continue

            self.failed += 1
            candidates = _select_candidates(group)
            if len(candidates) == 1:
                self._apply(candidates[0], roll)
                if self._mid_step():
                    return
                continue

            self.pending_choice = candidates
            self._pending_roll = roll
            return

    def choose_model(self, model):
        if self.pending_choice is None or model not in self.pending_choice:
            return
        roll = self._pending_roll
        self.pending_choice = None
        self._pending_roll = None
        self._apply(model, roll)
        if not self._mid_step():
            self._advance()

    def _apply(self, model, roll):
        # A dice-notation Damage characteristic (weapon.damage_notation,
        # e.g. a printed "D6") isn't known yet at this point - `weapon.
        # damage` is only the grouping/preview placeholder (see
        # WeaponProfile.damage_notation's own note) - so Stealth Drones is
        # offered against a stand-in "1" (always positive, same as any
        # fixed-damage weapon) instead of a real amount; the real roll only
        # happens in _after_stealth_drones() below, and only if Stealth
        # Drones didn't already zero this attack out.
        preview_amount = 1 if self.weapon.damage_notation is not None else self.weapon.damage
        if self.stealth_drones is not None and self.stealth_drones.maybe_offer(
            model, preview_amount, lambda amount: self._after_stealth_drones(model, roll, amount)
        ):
            self.pending_stealth_drones = True
            return
        self._after_stealth_drones(model, roll, preview_amount)

    def _after_stealth_drones(self, model, roll, amount):
        # Only reached synchronously (still inside the original _advance()/
        # choose_model() call) when Stealth Drones wasn't offered at all;
        # when it WAS offered, this runs later from its own DecisionManager
        # callback, after that frame's _advance()/choose_model() already
        # returned - so it must resume the queue itself once done (mirrors
        # on_fnp_acknowledged()'s own trailing self._advance() call below).
        was_pending = self.pending_stealth_drones
        self.pending_stealth_drones = False
        if self.weapon.damage_notation is not None and amount != 0:
            # Rule: this weapon's printed Damage characteristic is itself a
            # die roll - roll it now, once per attack allocated to this
            # model (real 40k timing: separately for each attack that
            # wounds and gets allocated), as a real, visible dice_manager
            # step (game/dice_notation.py's DiceNotationRoll, same shape as
            # Feel No Pain's own dice step below) rather than the earlier
            # "store the die's max value as a fixed placeholder, never
            # actually roll it" simplification. Skipped when Stealth Drones
            # already reduced this attack's Damage to 0 (amount == 0) -
            # nothing left to roll for.
            damage_roll = DiceNotationRoll(
                self.weapon.damage_notation, count=1, dice_manager=self.dice_manager,
                label=f"Damage: {self.weapon.name}", roll_kind=DAMAGE_ROLL, log=self.log,
                # No attacker to name here (the session only knows who is
                # being shot at), so DicePanel shows the target on its own -
                # a softer degradation than dropping the matchup line for
                # this one step in the middle of the sequence.
                target_name=self.target_squad.name if self.target_squad is not None else None,
                target_squad=self.target_squad,
            )
            if damage_roll.is_pending:
                self.pending_damage_roll = damage_roll
                self._damage_roll_model = model
                self._damage_roll_value = roll
                if was_pending:
                    self._notify_resumed()
                return
            amount = damage_roll.total
        self._apply_feel_no_pain(model, roll, amount, was_pending)
        if was_pending:
            self._notify_resumed()

    def on_damage_roll_acknowledged(self):
        # Always reached asynchronously (via the controller's
        # on_dice_acknowledged(), long after the original _advance()/
        # choose_model() call that started this attack's damage roll
        # already returned) - unlike _after_stealth_drones()'s `was_pending`
        # (which distinguishes "still inside that original call" from "a
        # later callback"), by the time this method runs the answer is
        # always "later callback": nothing else will resume the queue, so
        # this does so unconditionally once Feel No Pain (if any) is also
        # done - same as on_fnp_acknowledged()'s own unconditional
        # self._advance() below.
        if self.pending_damage_roll is None:
            return
        self.pending_damage_roll.on_dice_acknowledged()
        model, roll, amount = self._damage_roll_model, self._damage_roll_value, self.pending_damage_roll.total
        self.pending_damage_roll = None
        self._damage_roll_model = None
        self._damage_roll_value = None
        # Sunforge (game/sunforge.py): "you can re-roll the Damage roll" -
        # offered here, right after the roll is acknowledged and before Feel
        # No Pain gets to reduce it, which is the only point at which there
        # is a Damage roll to re-roll. Like Stealth Drones above, a True
        # return means the answer arrives later through the callback, so
        # this call must not carry on.
        #
        # The Farseer's Branching Fates used to have a second, parallel seam
        # right here ("it counts as 6 instead"). It is gone: that ability is
        # now spent from the left panel WHILE the Damage roll is still on the
        # table, by setting the die itself - so by the time this runs the roll
        # already says what it says, and there is nothing left to override.
        # See game/unmodified_six_controller.py.
        # A MANDATORY re-roll ("re-roll a Damage roll of 1") is not an offer:
        # nothing is asked, so it resolves on the synchronous path exactly as a
        # declined offer would. The D-cannon Platform's Structural Collapse is
        # the first source - see game/structural_collapse.py.
        if (self.damage_reroll is not None
                and self.damage_reroll.auto_reroll_for(amount)):
            if self.log is not None:
                self.log.add("%s: re-rolling %s's Damage roll of 1."
                             % (self.damage_reroll.label, self.weapon.name))
            self._after_damage_reroll(model, roll, amount, True)
            return
        if self.damage_reroll is not None and self.damage_reroll.maybe_offer(
            amount, lambda again: self._after_damage_reroll(model, roll, amount, again, resumed=True)
        ):
            # Marks the session busy until the prompt is answered - see
            # pending_damage_reroll's own note on the early-finish this
            # prevents.
            self.pending_damage_reroll = True
            return
        self._after_damage_reroll(model, roll, amount, False)

    def _after_damage_reroll(self, model, roll, amount, again, resumed=False):
        """Resumes on_damage_roll_acknowledged() once a Damage re-roll offer
        has been answered (or immediately, when none was made).

        `again` True means throw the die once more. That is a brand new,
        visible dice_manager roll marked is_reroll=True - NOT a silent
        recomputation - so it lands back in pending_damage_roll and comes
        through this same method again after the player acknowledges it.
        The second time round the ability declines to offer (the ledger now
        records the die as spent), so this cannot loop.

        `resumed` is True when this call IS that answer arriving from the
        DecisionManager (as opposed to the synchronous "no offer was made"
        path, whose caller runs the controller's completion check itself) -
        every exit then has to hand control back via _notify_resumed()."""
        self.pending_damage_reroll = False
        if again:
            reroll = DiceNotationRoll(
                self.weapon.damage_notation, count=1, dice_manager=self.dice_manager,
                label=f"Damage ({_reroll_label(self.damage_reroll)} re-roll): {self.weapon.name}", roll_kind=DAMAGE_ROLL,
                log=self.log, is_reroll=True,
                target_name=self.target_squad.name if self.target_squad is not None else None,
                target_squad=self.target_squad,
            )
            if reroll.is_pending:
                self.pending_damage_roll = reroll
                self._damage_roll_model = model
                self._damage_roll_value = roll
                if resumed:
                    self._notify_resumed()
                return
            amount = reroll.total
        fnp = FeelNoPainRoll(model, self._reduced_damage(model, amount), self.dice_manager,
                             log=self.log, waaagh=self.waaagh)
        if fnp.is_pending:
            self.pending_fnp = fnp
            self._fnp_model = model
            self._fnp_roll_value = roll
            if resumed:
                self._notify_resumed()
            return
        self._finish_apply(model, roll, fnp.reduced_amount)
        self._advance()
        if resumed:
            self._notify_resumed()

    def _reduced_damage(self, model, amount):
        """Every "change the Damage characteristic of the attack allocated to
        this model" ability, applied in one place.

        Renamed from _molten() when the second carrier arrived: the Avatar's
        Molten Form was the only one while it was called that, and the Necron
        Overlord's Implacable Resilience / Void Dragon's Necrodermis would have
        made the name a lie (CLAUDE.md's own rule about renaming as soon as a
        second carrier exists).

        Called at BOTH places this session builds a FeelNoPainRoll - the
        synchronous fixed-damage path and the rolled-notation/Sunforge path -
        because those are the two points where the amount is finally settled and
        there is no single funnel below them. Before Feel No Pain deliberately:
        these change the Damage CHARACTERISTIC, and FNP (24.12) is then rolled
        per remaining wound.

        Halving runs before subtraction - the core rules' own order for
        characteristic modifiers. See game/molten_form.py and
        game/damage_reduction.py."""
        result = molten_form.adjusted_damage(model, amount)
        if result != amount and self.log is not None:
            self.log(f"Molten Form: {model.profile.name} halves this attack's Damage "
                     f"{amount} -> {result}.")
        reduced = damage_reduction.adjusted_damage(model, result)
        if reduced != result and self.log is not None:
            self.log(f"{damage_reduction.label_for(model)}: {model.profile.name} reduces "
                     f"this attack's Damage {result} -> {reduced}.")
        # Mont'ka's Counterfire Defence Systems: "subtract 1 from the Damage
        # characteristic of that attack" - the fourth source folded here.
        # Applied to `reduced`, the value actually returned, and floored at 1
        # like every other reduction in this method: a Damage characteristic
        # never drops below 1.
        # Imported inside the method: a module-level import here closes a
        # cycle (this module <- game/squad.py <- the Stratagem's own imports).
        from game import conclave_wraithbone_armour, montka_counterfire_defence
        counterfire = (
            montka_counterfire_defence.damage_reduction_for(
                getattr(model, "squad", None))
            # Spirit Conclave's Wraithbone Armour - the FIFTH source here, and
            # the first bought by the defender in reaction to being targeted.
            # Summed with the line above rather than max()'d: two "subtract 1
            # from the Damage characteristic" effects are two subtractions, and
            # the floor below still stops either from reaching 0.
            + conclave_wraithbone_armour.damage_reduction_for(
                getattr(model, "squad", None)))
        if counterfire:
            after = max(1, reduced - counterfire)
            if after != reduced and self.log is not None:
                self.log(f"{montka_counterfire_defence.COUNTERFIRE_NAME}: "
                         f"{model.profile.name} reduces this attack's Damage "
                         f"{reduced} -> {after}.")
            reduced = after
        return reduced

    def _apply_feel_no_pain(self, model, roll, amount, was_pending):
        """Only used by the fully-synchronous path (_after_stealth_drones(),
        when there's no dice-notation Damage to roll, or the roll resolved
        immediately because there's no dice_manager - see
        DiceNotationRoll's own non-interactive fallback) - `was_pending`
        still means what it always did there: whether THIS call itself is
        the asynchronous Stealth Drones callback (see that method's own
        comment).

        comment)."""
        fnp = FeelNoPainRoll(model, self._reduced_damage(model, amount), self.dice_manager,
                             log=self.log, waaagh=self.waaagh)
        if fnp.is_pending:
            self.pending_fnp = fnp
            self._fnp_model = model
            self._fnp_roll_value = roll
            return
        self._finish_apply(model, roll, fnp.reduced_amount)
        if was_pending:
            self._advance()

    def on_fnp_acknowledged(self):
        if self.pending_fnp is None:
            return
        self.pending_fnp.on_dice_acknowledged()
        model, roll, amount = self._fnp_model, self._fnp_roll_value, self.pending_fnp.reduced_amount
        self.pending_fnp = None
        self._fnp_model = None
        self._fnp_roll_value = None
        self._finish_apply(model, roll, amount)
        self._advance()

    def _finish_apply(self, model, roll, amount):
        model.apply_damage(amount)
        if self.log is not None:
            status = "destroyed" if model.is_dead() else f"{model.current_wounds}/{model.profile.wounds} wounds"
            self.log(f"Roll {roll}: {amount} damage to {model.profile.name} ({status}).")


def resolve_damage(rolls, weapon, target_squad, log=None):
    """Non-interactive convenience wrapper around DamageAllocationSession:
    auto-picks the first candidate whenever the defending player would
    otherwise have a real choice, and (no dice_manager) skips Feel No Pain
    - useful for tests and other non-interactive callers. The live game
    uses DamageAllocationSession directly so the defending player actually
    gets to pick and Feel No Pain gets its real dice step."""
    session = DamageAllocationSession(rolls, weapon, target_squad, log=log)
    while not session.done:
        session.choose_model(session.pending_choice[0])
    return session.saved, session.failed


def _mortal_wound_candidates(squad):
    """Rule 06.02 step 1: a damaged non-CHARACTER model, else any
    non-CHARACTER model, else a damaged CHARACTER model, else any CHARACTER
    model - re-evaluated fresh before every single mortal wound. When more
    than one model qualifies within that category, it's the defending
    player's choice which one takes it - same principle as normal damage
    allocation (05.04)."""
    alive = [m for m in squad.models if not m.is_dead()]
    non_characters = [m for m in alive if not m.profile.character]
    damaged_non_characters = [m for m in non_characters if m.current_wounds < m.profile.wounds]
    if damaged_non_characters:
        return damaged_non_characters
    if non_characters:
        return non_characters
    characters = [m for m in alive if m.profile.character]
    damaged_characters = [m for m in characters if m.current_wounds < m.profile.wounds]
    if damaged_characters:
        return damaged_characters
    if characters:
        return characters
    return []


class MortalWoundAllocationSession:
    """Rule 06.02: inflicts `count` mortal wounds on squad, one at a time -
    re-selecting eligible candidates before each one - until either all of
    them have been inflicted or the unit is destroyed. Whenever more than
    one candidate qualifies, the session pauses (`pending_choice` holds the
    candidates) until the defending player calls choose_model(...) - mirrors
    DamageAllocationSession's pending_choice for normal damage. Rule 24.12
    (Feel No Pain): see DamageAllocationSession's docstring - same
    pending_fnp/on_fnp_acknowledged() pattern."""

    #: A hook fired ONCE, before the first wound is resolved, for a rule whose
    #: WHEN is "when a unit suffers a mortal wound" - Armoured Warhost's
    #: Layered Wards is the first. Set by main.py; a plain module attribute
    #: rather than a constructor argument because this session is built at a
    #: dozen call sites, none of which should have to learn about a Stratagem.
    #:
    #: It returns True if it opened a decision, in which case the session does
    #: NOT resolve anything until resume() is called. That matters: the effect
    #: on offer is a Feel No Pain threshold, and _advance() rolls Feel No Pain
    #: for the FIRST wound immediately - so an offer that did not pause would
    #: arrive too late for the wound that triggered it.
    on_mortal_wounds = None

    def __init__(self, squad, count, dice_manager=None, log=None, waaagh=None):
        self.squad = squad
        self.dice_manager = dice_manager
        self.log = log
        self.waaagh = waaagh  # Orks army rule "Waaagh!" - optional, like DamageAllocationSession's own; see game/waaagh.py
        self.remaining = count
        self.inflicted = 0
        self.pending_choice = None
        self.pending_fnp = None
        self._fnp_model = None
        self.waiting_on_interrupt = False
        hook = MortalWoundAllocationSession.on_mortal_wounds
        if hook is not None and count > 0 and hook(squad):
            self.waiting_on_interrupt = True
            return
        self._advance()

    def resume(self):
        """Continue after an interrupt has been answered. Idempotent, so a
        caller that is unsure whether it paused may call it anyway."""
        if not self.waiting_on_interrupt:
            return
        self.waiting_on_interrupt = False
        self._advance()

    @property
    def done(self):
        # No `waiting_on_interrupt` term here, and that is deliberate rather
        # than an oversight: the pause only happens when count > 0, and it
        # happens before anything is resolved, so `remaining` is still the full
        # count and this already answers False. A guard was written here first
        # and removed once an A/B probe showed deleting it changed no answer -
        # the same call game/tau_detachments.py's battle_round_in() records, and
        # for the same reason: a branch no input can reach will eventually be
        # trusted wrongly.
        return self.remaining == 0 and self.pending_choice is None and self.pending_fnp is None

    def _advance(self):
        if self.pending_fnp is not None:
            return
        while self.remaining > 0:
            candidates = _mortal_wound_candidates(self.squad)
            if not candidates:
                if self.log is not None:
                    self.log("The rest of the mortal wounds are wasted (unit destroyed).")
                self.remaining = 0
                return
            if len(candidates) == 1:
                self._apply(candidates[0])
                if self.pending_fnp is not None:
                    return
                continue
            self.pending_choice = candidates
            return

    def choose_model(self, model):
        if self.pending_choice is None or model not in self.pending_choice:
            return
        self.pending_choice = None
        self._apply(model)
        if self.pending_fnp is None:
            self._advance()

    def _apply(self, model):
        # mortal=True: this session IS the mortal-wound path (06.02), so it
        # is the one place that can answer the question the Broadsides'
        # Advanced Armour asks - see game/advanced_armour.py.
        fnp = FeelNoPainRoll(model, 1, self.dice_manager, log=self.log,
                             waaagh=self.waaagh, mortal=True)
        if fnp.is_pending:
            self.pending_fnp = fnp
            self._fnp_model = model
            return
        self._finish_apply(model, fnp.reduced_amount)

    def on_fnp_acknowledged(self):
        if self.pending_fnp is None:
            return
        self.pending_fnp.on_dice_acknowledged()
        model, amount = self._fnp_model, self.pending_fnp.reduced_amount
        self.pending_fnp = None
        self._fnp_model = None
        self._finish_apply(model, amount)
        self._advance()

    def _finish_apply(self, model, amount):
        model.apply_damage(amount)
        self.remaining -= 1
        self.inflicted += 1
        if self.log is not None:
            status = "destroyed" if model.is_dead() else f"{model.current_wounds}/{model.profile.wounds} wounds"
            self.log(f"Mortal Wound: {amount} damage to {model.profile.name} ({status}).")


class DevastatingWoundAllocationSession:
    """Rule 24.10 ([DEVASTATING WOUNDS]): each critical wound scored by such
    a weapon inflicts `damage` mortal wounds capped at a single model - any
    excess from that one critical wound is lost, not spread to another
    model (unlike a normal batch of mortal wounds, which re-selects a
    candidate per wound). One allocation per critical wound; each is still
    the defending player's choice among tied candidates, using the same
    priority pool as regular mortal wounds (06.02). Rule 24.12 (Feel No
    Pain): see DamageAllocationSession's docstring - same pending_fnp/
    on_fnp_acknowledged() pattern."""

    def __init__(self, squad, damage, crit_count, dice_manager=None, log=None, waaagh=None):
        self.squad = squad
        self.damage = damage
        self.dice_manager = dice_manager
        self.log = log
        self.waaagh = waaagh  # Orks army rule "Waaagh!" - optional, like DamageAllocationSession's own; see game/waaagh.py
        self.remaining_crits = crit_count
        self.pending_choice = None
        self.pending_fnp = None
        self._fnp_model = None
        self._advance()

    @property
    def done(self):
        return self.remaining_crits == 0 and self.pending_choice is None and self.pending_fnp is None

    def _advance(self):
        if self.pending_fnp is not None:
            return
        while self.remaining_crits > 0:
            candidates = _mortal_wound_candidates(self.squad)
            if not candidates:
                if self.log is not None:
                    self.log("The rest of the Devastating Wounds mortal wounds are wasted (unit destroyed).")
                self.remaining_crits = 0
                return
            if len(candidates) == 1:
                self._apply(candidates[0])
                if self.pending_fnp is not None:
                    return
                continue
            self.pending_choice = candidates
            return

    def choose_model(self, model):
        if self.pending_choice is None or model not in self.pending_choice:
            return
        self.pending_choice = None
        self._apply(model)
        if self.pending_fnp is None:
            self._advance()

    def _apply(self, model):
        fnp = FeelNoPainRoll(model, self.damage, self.dice_manager, log=self.log, waaagh=self.waaagh)
        if fnp.is_pending:
            self.pending_fnp = fnp
            self._fnp_model = model
            return
        self._finish_apply(model, fnp.reduced_amount)

    def on_fnp_acknowledged(self):
        if self.pending_fnp is None:
            return
        self.pending_fnp.on_dice_acknowledged()
        model, amount = self._fnp_model, self.pending_fnp.reduced_amount
        self.pending_fnp = None
        self._fnp_model = None
        self._finish_apply(model, amount)
        self._advance()

    def _finish_apply(self, model, amount):
        model.apply_damage(amount)
        self.remaining_crits -= 1
        if self.log is not None:
            status = "destroyed" if model.is_dead() else f"{model.current_wounds}/{model.profile.wounds} wounds"
            self.log(f"Devastating Wounds: {amount} mortal wound(s) to {model.profile.name} ({status}).")


def resolve_mortal_wounds(squad, count, log=None):
    """Rule 06.02: inflict `count` mortal wounds on squad. Non-interactive
    convenience wrapper around MortalWoundAllocationSession: auto-picks the
    first candidate whenever the defending player would otherwise have a
    real choice, and (no dice_manager) skips Feel No Pain. Useful for tests
    and other non-interactive callers - the live game uses
    MortalWoundAllocationSession directly so the defending player actually
    gets to pick and Feel No Pain gets its real dice step.

    Per the "MORTAL WOUNDS AND NORMAL DAMAGE" sidebar, when a single attack
    sequence causes both, callers must resolve_damage() first and only then
    call resolve_mortal_wounds() for the same target."""
    session = MortalWoundAllocationSession(squad, count, log=log)
    while not session.done:
        session.choose_model(session.pending_choice[0])
    return session.inflicted
