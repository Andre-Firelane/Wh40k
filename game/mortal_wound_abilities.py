"""Four abilities that inflict MORTAL WOUNDS by picking a unit and rolling.

Four abilities, one module, because they are the same machine: pick one enemy
unit in range, roll dice, inflict mortal wounds. Keeping them together means
the target-picking and the mortal-wound plumbing exist once.

Three are Necron; the fourth, Typhus' Eater Plague, is Death Guard and was
the one that paid the module back - its targeting is Living Lightning's and
its gate is Crimson Harvest's, so it needed no new plumbing at all. What it
DID add is the first case where a roll decides WHICH SIDE takes the wounds.

RULES (printed, word for word):

  Living Lightning: "In your Shooting phase, select one enemy unit within 18"
  of and visible to this model (excluding units with the Lone Operative ability
  that are not part of an Attached unit and are not within 12" of this model)
  and roll four D6: for each 4+, that enemy unit suffers 1 mortal wound."

  Matter Absorption: "At the start of your Shooting phase, select one enemy
  VEHICLE unit within 12" of this model and roll one D6: on a 2+, that enemy
  unit suffers D3 mortal wounds and this model regains up to that many lost
  wounds."

THE LONE OPERATIVE CLAUSE is transcribed rather than simplified: rule 24.24's
protection normally stops a unit being SELECTED as a target beyond 12", and
this ability restates it for itself because it is not an attack and so would
otherwise ignore targeting rules entirely. game/status_effects.py's
lone_operative_range() already answers "does this unit have it right now",
including Illuminor Szeras's conditional grant, so it is asked rather than
re-derived.

  Crimson Harvest: "Each time this model ends a Charge move, select one enemy
  unit within Engagement Range of this model and roll one D6: on a 2-5, that
  unit suffers D3 mortal wounds; on a 6, that unit suffers D3+3 mortal wounds."

CRIMSON HARVEST IS THE ONLY ONE NOT TRIGGERED BY A PHASE, which is the whole
reason it needed a new seam: "ends a Charge move" is a moment, and the only
place that moment exists is ChargeController.confirm_charge_move() after the
move is accepted. NOT _finish_charge() - that also runs for a DECLINED charge
and for a unit destroyed before it could move, neither of which ends a Charge
move. Its range is Engagement Range rather than inches, so a charge that fell
short simply finds no target and the ability does nothing, with no extra check.

ITS GATE HAS THREE OUTCOMES, not two: a 1 does nothing, 2-5 is D3, a 6 is
D3+3. So the second roll's SIZE depends on the first roll's value, not merely
whether it passed - which is why the stage context carries a bonus rather than
the threshold alone.

MATTER ABSORPTION HEALS THE BEARER, and "up to that many" is a cap, not a
grant: a Void Dragon missing one wound regains one from a roll of 3, not three.
Its two rolls are separate visible steps - the D6 that decides whether it
happens at all, then the D3 for how much - because a single combined roll could
not show which number did what.

Both AI answers are deterministic and use the same measure: the eligible target
with the highest game/damage_estimate.py value, which is the ranking every
other deterministic target choice in this engine already uses.
"""

from game.squad import ENGAGEMENT_RANGE_IN
from game.status_effects import lone_operative_range
from game import ai_mode

LIVING_LIGHTNING_RANGE_IN = 18.0
LIVING_LIGHTNING_LONE_OPERATIVE_RANGE_IN = 12.0
LIVING_LIGHTNING_DICE = 4
MORTAL_WOUND_THRESHOLD = 4

MATTER_ABSORPTION_RANGE_IN = 12.0
MATTER_ABSORPTION_THRESHOLD = 2      # "on a 2+"
MATTER_ABSORPTION_DICE_SIDES = 3     # "D3 mortal wounds"

CRIMSON_HARVEST_THRESHOLD = 2        # "on a 2-5" - a 1 does nothing at all
CRIMSON_HARVEST_BIG_ROLL = 6         # "on a 6"
CRIMSON_HARVEST_DICE_SIDES = 3       # "D3 mortal wounds"
CRIMSON_HARVEST_BIG_BONUS = 3        # "D3+3 mortal wounds"


def _bearers(squad, attribute):
    return [m for m in getattr(squad, "models", ()) or ()
            if getattr(m.profile, attribute, False) and not m.is_dead()]


def _enemy_squads(squad, all_tokens):
    seen = {}
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or token.is_dead() or other.owner == squad.owner:
            continue
        seen.setdefault(id(other), other)
    return list(seen.values())


def _gap(model, other_squad):
    """Edge-to-edge distance from one MODEL to the nearest model of a unit.

    Squad.min_distance_to() measures unit to unit; both abilities here measure
    from the bearer specifically ("within 12" of THIS MODEL"), which for a
    multi-model unit is not the same number."""
    live = [t for t in other_squad.models if not t.is_dead()]
    if not live:
        return float("inf")
    return min(((t.x_in - model.x_in) ** 2 + (t.y_in - model.y_in) ** 2) ** 0.5
               - t.radius_in - model.radius_in for t in live)


# --- Living Lightning -------------------------------------------------------

def has_living_lightning(squad):
    return bool(_bearers(squad, "living_lightning"))


def living_lightning_targets(squad, all_tokens, visible=None):
    """Every enemy unit this model may select.

    `visible(model, target_squad) -> bool` is supplied by the caller (main.py
    passes the real line-of-sight test), so this module never re-derives
    visibility. None means "do not filter", which is what a headless test
    wants."""
    out = []
    for bearer in _bearers(squad, "living_lightning"):
        for enemy in _enemy_squads(squad, all_tokens):
            if enemy in out:
                continue
            gap = _gap(bearer, enemy)
            if gap > LIVING_LIGHTNING_RANGE_IN:
                continue
            if visible is not None and not visible(bearer, enemy):
                continue
            # The printed Lone Operative carve-out.
            lone = lone_operative_range(enemy, all_tokens)
            if lone is not None and gap > LIVING_LIGHTNING_LONE_OPERATIVE_RANGE_IN:
                continue
            out.append(enemy)
    return out


# --- Matter Absorption ------------------------------------------------------

def has_matter_absorption(squad):
    return bool(_bearers(squad, "matter_absorption"))


def matter_absorption_targets(squad, all_tokens):
    """"one enemy VEHICLE unit within 12" of this model"."""
    out = []
    for bearer in _bearers(squad, "matter_absorption"):
        for enemy in _enemy_squads(squad, all_tokens):
            if enemy in out:
                continue
            if not any(getattr(m.profile, "vehicle", False) for m in enemy.models if not m.is_dead()):
                continue
            if _gap(bearer, enemy) <= MATTER_ABSORPTION_RANGE_IN:
                out.append(enemy)
    return out


# --- Crimson Harvest --------------------------------------------------------

def has_crimson_harvest(squad):
    return bool(_bearers(squad, "crimson_harvest"))


def crimson_harvest_targets(squad, all_tokens):
    """"one enemy unit within Engagement Range of this model".

    Measured from the BEARER, not the unit (_gap, same as the other two): the
    Skorpekh Lord is merged into his bodyguards under 19.01, so "within
    Engagement Range of this unit" would be a materially bigger circle than the
    printed text allows."""
    out = []
    for bearer in _bearers(squad, "crimson_harvest"):
        for enemy in _enemy_squads(squad, all_tokens):
            if enemy in out:
                continue
            if _gap(bearer, enemy) <= ENGAGEMENT_RANGE_IN:
                out.append(enemy)
    return out


class MortalWoundOfferController:
    """Shared plumbing for every one of them: pick a target, roll, allocate.

    PUBLIC since the sixth carrier arrived. The leading underscore said
    "private to this module", which was true while all five subclasses lived
    here; Spirit Conclave's Crushing Strides is a STRATAGEM and lives in its
    own file with its detachment prefix, so the name had become the kind of
    lie this repo renames rather than works around.

    Subclasses supply the eligibility test and the roll; everything else - the
    auto/prompt split, the pending slot, the mortal-wound session - is the same
    machine, which is why the two abilities share a module at all."""

    label = "Ability"

    def __init__(self, dice_manager=None, decision_manager=None, game_log=None,
                 game_state=None, auto_players=(), target_pick=None):
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.game_state = game_state
        self.auto_players = ai_mode.players(auto_players)
        # target_pick(attacker, candidates) -> squad. main.py passes the shared
        # damage-value ranking, so the AI uses the same measure as every other
        # deterministic target choice; None falls back to name order, which
        # keeps a headless test reproducible.
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

    def _pick(self, squad, targets):
        """Which enemy unit to hit. `squad` is passed so the ranking can use
        the shared damage estimate, which needs an attacker to mean anything -
        without it the measure collapses to "biggest unit", the exact bias
        game/damage_estimate.py exists to avoid."""
        if self.target_pick is not None:
            chosen = self.target_pick(squad, targets)
            if chosen is not None:
                return chosen
        return sorted(targets, key=lambda s: s.name)[0]

    def _inflict(self, target, wounds):
        if wounds <= 0:
            return
        from game.damage_resolution import MortalWoundAllocationSession
        self.mortal_wound_session = MortalWoundAllocationSession(
            target, wounds, dice_manager=self.dice_manager,
            log=(lambda m: self._log(m)) if self.game_log is not None else None)

    # ---------------------------------------------------------------- 06.02
    # THE SESSION'S OWN PLUMBING, WRITTEN ONCE FOR ALL SIX CARRIERS.
    #
    # It used to be written ZERO times. MortalWoundAllocationSession parks at
    # `pending_choice` the moment its target has more than one eligible model
    # (game/damage_resolution.py's _advance()), and nothing here ever drained
    # it - no pending_damage_choice, no choose_damage_model, no done check. So
    # against any multi-model unit the dice were rolled, the log said N mortal
    # wounds, and NOT ONE OF THEM WAS EVER APPLIED. Six abilities across four
    # factions: Living Lightning, Matter Absorption, Crimson Harvest, Eater
    # Plague, Kroot Linebreakers and Crushing Strides.
    #
    # Against a SINGLE-model target the session applies the wound itself and
    # never parks, which is why this survived: every one-model victim behaved
    # correctly, and the two suites that cover it measured how much was
    # ORDERED (`inflicted + remaining`, `remaining in (2, 1, 0)`) rather than
    # how much LANDED.
    #
    # Written in the base rather than on the one carrier that reported it:
    # game/crushing_impact.py and game/deadly_demise.py already spell these
    # same three methods out, so a seventh copy is the drift this repo
    # consolidates at the second consumer. With main.py asking each carrier
    # for pending_damage_choice, test_event_chain_wiring.py's section 6 then
    # enforces the click branch and the highlight by construction.

    @property
    def pending_damage_choice(self):
        """Rule 06.02: the TARGET's owner picks which of their models takes
        each mortal wound."""
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_session_done()

    def _ack_session(self):
        """The Feel No Pain leg of an OPEN session.

        Every subclass's on_dice_acknowledged() opens with `if self._pending
        is None: return False`, and by the time a session exists that slot is
        already cleared - so the FNP roll's acknowledgement never reached the
        session either. Called from exactly that guard instead of returning."""
        if self.mortal_wound_session is None:
            return False
        if self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_session_done()
            return True
        return False

    def _check_session_done(self):
        if self.mortal_wound_session is not None and self.mortal_wound_session.done:
            self.mortal_wound_session = None


class LivingLightningController(MortalWoundOfferController):
    """The Plasmancer's. Offered once per Shooting phase per bearer unit."""

    label = "Living Lightning"

    def __init__(self, *args, visible=None, **kwargs):
        super().__init__(*args, **kwargs)
        # visible(model, squad) -> bool. main.py passes the real line-of-sight
        # test; None means no filtering, which is what a headless test wants.
        self.visible = visible
        self._used_this_phase = set()

    def reset_phase(self):
        self._used_this_phase.clear()

    def can_use(self, squad):
        return (self._pending is None
                and has_living_lightning(squad)
                and id(squad) not in self._used_this_phase
                and bool(living_lightning_targets(squad, self._tokens(), self.visible)))

    def offer_at_shooting_phase(self, squads, player):
        for squad in sorted((s for s in squads if s.owner == player), key=lambda s: s.name):
            if self.can_use(squad):
                return self.offer(squad)
        return False

    def offer(self, squad):
        if not self.can_use(squad):
            return False
        targets = living_lightning_targets(squad, self._tokens(), self.visible)
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, self._pick(squad, targets))
        options = [(f"Living Lightning: {t.name}", (lambda target=t: self._use(squad, target)), t)
                   for t in targets]
        options.append(("Decline", None))
        self.decision_manager.request(
            squad.owner, f"{squad.name}: Living Lightning - strike which unit?", options)
        return True

    def _use(self, squad, target):
        if target is None:
            return False
        self._used_this_phase.add(id(squad))
        self._pending = {"squad": squad, "target": target}
        self.dice_manager.roll(
            LIVING_LIGHTNING_DICE, 6, label=self.label,
            success_threshold=MORTAL_WOUND_THRESHOLD,
            target_name=target.name, attacker_squad=squad, target_squad=target)
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            # No roll of our own outstanding - but an allocation session may
            # still owe a Feel No Pain acknowledgement. See _ack_session().
            return self._ack_session()
        ctx, self._pending = self._pending, None
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or []
        wounds = sum(1 for v in values if v >= MORTAL_WOUND_THRESHOLD)
        name = ctx["squad"].name
        self._log(f"Living Lightning ({name}): {values} - "
                  f"{ctx['target'].name} suffers {wounds} mortal wound(s).")
        self._inflict(ctx["target"], wounds)
        return True


class MatterAbsorptionController(MortalWoundOfferController):
    """The Void Dragon's. Two visible rolls, deliberately: the D6 that decides
    whether it happens at all, then the D3 for how much. One combined roll
    could not show which number did what."""

    label = "Matter Absorption"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._used_this_phase = set()
        self._stage = None

    def reset_phase(self):
        self._used_this_phase.clear()

    def can_use(self, squad):
        return (self._pending is None
                and has_matter_absorption(squad)
                and id(squad) not in self._used_this_phase
                and bool(matter_absorption_targets(squad, self._tokens())))

    def offer_at_shooting_phase(self, squads, player):
        for squad in sorted((s for s in squads if s.owner == player), key=lambda s: s.name):
            if self.can_use(squad):
                return self.offer(squad)
        return False

    def offer(self, squad):
        """Not optional - the printed text says "select", not "you can". So the
        only decision is WHICH vehicle, and with a single candidate there is
        nothing to ask at all."""
        if not self.can_use(squad):
            return False
        targets = matter_absorption_targets(squad, self._tokens())
        if len(targets) == 1 or squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, self._pick(squad, targets))
        options = [(f"Matter Absorption: {t.name}", (lambda target=t: self._use(squad, target)), t)
                   for t in targets]
        self.decision_manager.request(
            squad.owner, f"{squad.name}: Matter Absorption - drain which vehicle?", options)
        return True

    def _use(self, squad, target):
        if target is None:
            return False
        self._used_this_phase.add(id(squad))
        self._pending = {"squad": squad, "target": target}
        self._stage = "gate"
        self.dice_manager.roll(
            1, 6, label=self.label, success_threshold=MATTER_ABSORPTION_THRESHOLD,
            target_name=target.name, attacker_squad=squad, target_squad=target)
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            # No roll of our own outstanding - but an allocation session may
            # still owe a Feel No Pain acknowledgement. See _ack_session().
            return self._ack_session()
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        ctx = self._pending
        if self._stage == "gate":
            if values[0] < MATTER_ABSORPTION_THRESHOLD:
                self._pending = None
                self._stage = None
                self._log(f"Matter Absorption ({ctx['squad'].name}): rolled a {values[0]}, "
                          f"needed {MATTER_ABSORPTION_THRESHOLD}+ - nothing is drained.")
                return True
            self._stage = "amount"
            self.dice_manager.roll(
                1, MATTER_ABSORPTION_DICE_SIDES, label=f"{self.label} - mortal wounds",
                target_name=ctx["target"].name, attacker_squad=ctx["squad"],
                target_squad=ctx["target"])
            return True
        self._pending = None
        self._stage = None
        wounds = values[0]
        target, squad = ctx["target"], ctx["squad"]
        # "this model regains UP TO that many lost wounds" - a cap, not a grant:
        # a Void Dragon one wound short regains one from a roll of 3.
        healed = 0
        for bearer in _bearers(squad, "matter_absorption"):
            missing = bearer.profile.wounds - bearer.current_wounds
            healed = max(0, min(wounds, missing))
            bearer.current_wounds += healed
            break
        self._log(f"Matter Absorption ({squad.name}): {target.name} suffers {wounds} mortal "
                  f"wound(s); {squad.name} regains {healed}.")
        self._inflict(target, wounds)
        return True


class CrimsonHarvestController(MortalWoundOfferController):
    """The Skorpekh Lord's. Fired by ChargeController, not by a phase.

    Two visible rolls for the same reason Matter Absorption has two: the D6
    that decides IF and HOW HARD, then the D3 for how much. Here the first
    roll's value also sets the second one's bonus, so a combined roll could
    not show which number did what at all.

    NO once-per-phase ledger, deliberately, and it is not an oversight: the
    printed text is "each time this model ends a Charge move", and a unit gets
    at most one Charge move per Charge phase (ChargeController.
    charged_squad_ids) plus at most one reactive Heroic Intervention (15.11).
    The trigger IS the limit, and a ledger on top of it would silently cancel
    the Heroic Intervention case.
    """

    label = "Crimson Harvest"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stage = None

    def can_use(self, squad):
        return (self._pending is None
                and has_crimson_harvest(squad)
                and bool(crimson_harvest_targets(squad, self._tokens())))

    def on_charge_move_finished(self, squad):
        """ChargeController's hook. A charge that fell short leaves nothing in
        Engagement Range, so the ability simply finds no target - no separate
        "did the charge succeed" test is needed or wanted."""
        if not self.can_use(squad):
            return False
        return self.offer(squad)

    def offer(self, squad):
        """Not optional - the printed text says "select", not "you can". So
        the only decision is WHICH unit, and with a single candidate there is
        nothing to ask."""
        if not self.can_use(squad):
            return False
        targets = crimson_harvest_targets(squad, self._tokens())
        if len(targets) == 1 or squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, self._pick(squad, targets))
        options = [(f"Crimson Harvest: {t.name}", (lambda target=t: self._use(squad, target)), t)
                   for t in targets]
        self.decision_manager.request(
            squad.owner, f"{squad.name}: Crimson Harvest - reap which unit?", options)
        return True

    def _use(self, squad, target):
        if target is None:
            return False
        self._pending = {"squad": squad, "target": target}
        self._stage = "gate"
        self.dice_manager.roll(
            1, 6, label=self.label, success_threshold=CRIMSON_HARVEST_THRESHOLD,
            target_name=target.name, attacker_squad=squad, target_squad=target)
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            # No roll of our own outstanding - but an allocation session may
            # still owe a Feel No Pain acknowledgement. See _ack_session().
            return self._ack_session()
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        ctx = self._pending
        if self._stage == "gate":
            rolled = values[0]
            if rolled < CRIMSON_HARVEST_THRESHOLD:
                self._pending = None
                self._stage = None
                self._log(f"Crimson Harvest ({ctx['squad'].name}): rolled a {rolled} - "
                          f"{ctx['target'].name} is unharmed.")
                return True
            # "on a 2-5 ... D3; on a 6 ... D3+3". The bonus rides on the
            # context because the FIRST roll decides the SECOND roll's size,
            # not merely whether there is one.
            bonus = CRIMSON_HARVEST_BIG_BONUS if rolled >= CRIMSON_HARVEST_BIG_ROLL else 0
            ctx["bonus"] = bonus
            ctx["gate"] = rolled
            self._stage = "amount"
            suffix = f" (D3+{bonus})" if bonus else " (D3)"
            self.dice_manager.roll(
                1, CRIMSON_HARVEST_DICE_SIDES, label=f"{self.label} - mortal wounds{suffix}",
                target_name=ctx["target"].name, attacker_squad=ctx["squad"],
                target_squad=ctx["target"])
            return True
        self._pending = None
        self._stage = None
        bonus = int(ctx.get("bonus", 0))
        wounds = values[0] + bonus
        self._log(f"Crimson Harvest ({ctx['squad'].name}): rolled a {ctx.get('gate')}, "
                  f"then {values[0]}+{bonus} - {ctx['target'].name} suffers "
                  f"{wounds} mortal wound(s).")
        self._inflict(ctx["target"], wounds)
        return True


# --- Typhus' Eater Plague ---------------------------------------------------
#
# RULE (printed): "In your Shooting phase, you can select one enemy unit within
# 18" of and visible to this PSYKER ... and roll one D6: on a 1, this PSYKER's
# unit suffers D3 mortal wounds; on a 2-5, that enemy unit suffers D6 mortal
# wounds; on a 6, that enemy unit suffers D3+3 mortal wounds."
#
# THE FOURTH ABILITY IN THIS MODULE, and the one that justified the module's
# existence twice over: its TARGETING is Living Lightning's (18", visible, in
# your Shooting phase) and its GATE is Crimson Harvest's (three outcomes, and
# the first roll decides the second roll's SIZE, not merely whether there is
# one). Neither half is new; only the combination is.
#
# WHAT *IS* NEW - and it is the reason this could not simply reuse either - is
# that a roll of 1 turns the ability around and hurts TYPHUS' OWN UNIT. Every
# other mortal-wound source in this engine knows at the outset which side takes
# the damage. So the stage context carries the VICTIM as well as the amount,
# and it is not always the unit that was selected.
#
# "YOU CAN SELECT" - so unlike Living Lightning and Crimson Harvest this one IS
# optional, which is exactly what the 1-in-6 backfire makes it. The AI answers
# it deterministically all the same: it takes the shot whenever the expected
# damage to the target beats the expected damage to itself, which needs no
# agent and no judgement call.

EATER_PLAGUE_RANGE_IN = 18.0
EATER_PLAGUE_BACKFIRE = 1        # "on a 1" - the PSYKER's own unit
EATER_PLAGUE_BIG_ROLL = 6        # "on a 6"
EATER_PLAGUE_BACKFIRE_SIDES = 3  # "D3 mortal wounds" to its own unit
EATER_PLAGUE_SIDES = 6           # "D6 mortal wounds" on a 2-5
EATER_PLAGUE_BIG_SIDES = 3       # "D3+3" on a 6
EATER_PLAGUE_BIG_BONUS = 3


def has_eater_plague(squad):
    return bool(_bearers(squad, "eater_plague"))


def eater_plague_targets(squad, all_tokens, visible=None):
    """Every enemy unit Typhus may select.

    Measured from the BEARER ("within 18" of this PSYKER"), not from the unit -
    the same distinction Living Lightning and Crimson Harvest both make, and it
    matters more here than for either: rule 19.01 merges Typhus into a
    Deathshroud or Poxwalker unit, so "within 18" of this unit" would be a
    materially bigger circle than the printed text allows."""
    out = []
    for bearer in _bearers(squad, "eater_plague"):
        for enemy in _enemy_squads(squad, all_tokens):
            if enemy in out:
                continue
            if _gap(bearer, enemy) > EATER_PLAGUE_RANGE_IN:
                continue
            if visible is not None and not visible(bearer, enemy):
                continue
            out.append(enemy)
    return out


class EaterPlagueController(MortalWoundOfferController):
    """Typhus'. Offered once per Shooting phase per bearer unit.

    Feeds game/curse_of_the_walking_pox.py when Typhus is leading Poxwalkers:
    the printed text of THAT ability says models killed by this one "count as
    enemy models destroyed by an attack made by a POXWALKER model", which no
    ordinary reading of "mortal wounds" would give. main.py wires the two
    together; on_kills is the seam."""

    label = "Eater Plague"

    def __init__(self, *args, visible=None, on_kills=None, **kwargs):
        super().__init__(*args, **kwargs)
        # visible(model, squad) -> bool. main.py passes the real line-of-sight
        # test; None means no filtering, which is what a headless test wants.
        self.visible = visible
        # on_kills(poxwalker_squad, destroyed_models) - the Curse of the
        # Walking Pox clause. Optional, so a Typhus leading Deathshroud (or
        # standing alone) simply never calls it.
        self.on_kills = on_kills
        self._used_this_phase = set()
        self._stage = None

    def reset_phase(self):
        self._used_this_phase.clear()

    def can_use(self, squad):
        return (self._pending is None
                and has_eater_plague(squad)
                and id(squad) not in self._used_this_phase
                and bool(eater_plague_targets(squad, self._tokens(), self.visible)))

    def offer_at_shooting_phase(self, squads, player):
        for squad in sorted((s for s in squads if s.owner == player), key=lambda s: s.name):
            if self.can_use(squad):
                return self.offer(squad)
        return False

    def offer(self, squad):
        """"You CAN select" - so this one really is optional, unlike the three
        abilities above it. The 1-in-6 backfire is what makes that a real
        choice rather than a formality."""
        if not self.can_use(squad):
            return False
        targets = eater_plague_targets(squad, self._tokens(), self.visible)
        self._used_this_phase.add(id(squad))
        if squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, self._pick(squad, targets))
        options = [(f"Eater Plague: {t.name}", (lambda target=t: self._use(squad, target)), t)
                   for t in targets]
        options.append(("Decline", None))
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: Eater Plague - which unit? (on a 1 your own unit takes D3)",
            options)
        return True

    def _use(self, squad, target):
        if target is None:
            return False
        self._pending = {"squad": squad, "target": target}
        self._stage = "gate"
        self.dice_manager.roll(
            1, 6, label=self.label,
            target_name=target.name, attacker_squad=squad, target_squad=target)
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            # No roll of our own outstanding - but an allocation session may
            # still owe a Feel No Pain acknowledgement. See _ack_session().
            return self._ack_session()
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        ctx = self._pending
        if self._stage == "gate":
            rolled = values[0]
            ctx["gate"] = rolled
            self._stage = "amount"
            if rolled <= EATER_PLAGUE_BACKFIRE:
                # THE BACKFIRE. The victim is the PSYKER's own unit, so it is
                # recorded on the context - the amount step below reads it
                # rather than assuming the selected target.
                ctx["victim"] = ctx["squad"]
                ctx["bonus"] = 0
                sides = EATER_PLAGUE_BACKFIRE_SIDES
                suffix = " - backfire (D3)"
            elif rolled >= EATER_PLAGUE_BIG_ROLL:
                ctx["victim"] = ctx["target"]
                ctx["bonus"] = EATER_PLAGUE_BIG_BONUS
                sides = EATER_PLAGUE_BIG_SIDES
                suffix = f" (D3+{EATER_PLAGUE_BIG_BONUS})"
            else:
                ctx["victim"] = ctx["target"]
                ctx["bonus"] = 0
                sides = EATER_PLAGUE_SIDES
                suffix = " (D6)"
            self.dice_manager.roll(
                1, sides, label=f"{self.label} - mortal wounds{suffix}",
                target_name=ctx["victim"].name, attacker_squad=ctx["squad"],
                target_squad=ctx["victim"])
            return True

        self._pending = None
        self._stage = None
        victim = ctx["victim"]
        wounds = values[0] + int(ctx.get("bonus", 0))
        whose = "its own unit" if victim is ctx["squad"] else victim.name
        self._log(f"Eater Plague ({ctx['squad'].name}): rolled a {ctx.get('gate')}, "
                  f"then {values[0]} - {whose} suffers {wounds} mortal wound(s).")
        before = [m for m in victim.models if not m.is_dead()]
        self._inflict(victim, wounds)
        if self.on_kills is not None and victim is not ctx["squad"]:
            killed = [m for m in before if m.is_dead()]
            if killed:
                # The printed TYPHUS clause of Curse of the Walking Pox. Fed
                # with the squad TYPHUS IS IN, not with the victim - the models
                # that return are Poxwalkers from his own unit.
                self.on_kills(ctx["squad"], killed)
        return True


# --- Krootox Rampagers' Kroot Linebreakers ----------------------------------
#
# RULE (printed, word for word):
#   "Each time this unit ends a Charge move, select one enemy unit within
#    Engagement Range of it, then roll one D6 for each model in this unit that
#    is within Engagement Range of that enemy unit: for each 4+, that enemy
#    unit suffers D3 mortal wounds. If one or more enemy models are destroyed as
#    a result of these mortal wounds, that enemy unit must take a Battle-shock
#    test."
#
# THE FIFTH ABILITY IN THIS MODULE, and Crimson Harvest's sibling: same trigger
# (ChargeController.on_charge_move_finished), same "select one enemy unit within
# Engagement Range", same two-stage roll. Three things are genuinely new, and
# each is a way to get it wrong:
#
#   * THE FIRST ROLL IS A HANDFUL, NOT ONE DIE - one per model of THIS unit that
#     is itself within Engagement Range of the chosen target. So a six-Rampager
#     unit that only got three models into contact rolls three dice, and the
#     count has to be measured per MODEL rather than taken from the unit's size.
#   * EACH 4+ IS ITS OWN D3, so the second stage rolls that many dice and sums
#     them - where Crimson Harvest's second stage is a single die whose SIZE the
#     first roll set.
#   * THE BATTLE-SHOCK TEST is conditional on a MODEL DYING, not on wounds being
#     dealt - a unit that soaks every mortal wound takes no test. That is
#     checked by counting the target's living models across the allocation.
#
# "EACH TIME THIS UNIT ENDS A CHARGE MOVE" is the same limit Crimson Harvest
# relies on and for the same reason: a unit gets at most one Charge move per
# phase plus at most one Heroic Intervention, so the trigger IS the ledger.

KROOT_LINEBREAKERS_THRESHOLD = 4     # "for each 4+"
KROOT_LINEBREAKERS_DICE_SIDES = 3    # each success is D3 mortal wounds


def has_kroot_linebreakers(squad):
    return bool(_bearers(squad, "kroot_linebreakers"))


def linebreaker_targets(squad, all_tokens):
    """"one enemy unit within Engagement Range of it" - of the UNIT here, not
    of a single bearer, because every model in a Krootox Rampagers unit prints
    the ability. That is the difference from crimson_harvest_targets() above,
    whose bearer is one merged-in character."""
    out = []
    for bearer in _bearers(squad, "kroot_linebreakers"):
        for enemy in _enemy_squads(squad, all_tokens):
            if enemy not in out and _gap(bearer, enemy) <= ENGAGEMENT_RANGE_IN:
                out.append(enemy)
    return out


def linebreaker_dice(squad, target):
    """How many D6 to roll: one per model of this unit that is ITSELF within
    Engagement Range of `target`.

    Not the unit's model count - a charge that only reached with half its
    models rolls half the dice, which is the whole point of the clause."""
    if squad is None or target is None:
        return 0
    return sum(1 for m in _bearers(squad, "kroot_linebreakers")
               if _gap(m, target) <= ENGAGEMENT_RANGE_IN)


class KrootLinebreakersController(MortalWoundOfferController):
    """Fired by ChargeController, like Crimson Harvest."""

    label = "Kroot Linebreakers"

    def __init__(self, *args, battle_shock=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._stage = None
        # The Battle-shock test the printed text demands when a model dies.
        # Optional like every other collaborator here.
        self.battle_shock = battle_shock
        self._pending_battle_shock = None

    def can_use(self, squad):
        return (self._pending is None
                and has_kroot_linebreakers(squad)
                and bool(linebreaker_targets(squad, self._tokens())))

    def on_charge_move_finished(self, squad):
        """A charge that fell short leaves nothing in Engagement Range, so the
        ability simply finds no target - the same reasoning Crimson Harvest's
        own hook gives."""
        if not self.can_use(squad):
            return False
        return self.offer(squad)

    def offer(self, squad):
        """"select one enemy unit" - not optional, so the only decision is
        WHICH, and one candidate needs no question."""
        if not self.can_use(squad):
            return False
        targets = linebreaker_targets(squad, self._tokens())
        if len(targets) == 1 or squad.owner in self.auto_players or self.decision_manager is None:
            return self._use(squad, self._pick(squad, targets))
        options = [(f"Kroot Linebreakers: {t.name}", (lambda target=t: self._use(squad, target)), t)
                   for t in targets]
        self.decision_manager.request(
            squad.owner, f"{squad.name}: Kroot Linebreakers - trample which unit?", options)
        return True

    def _use(self, squad, target):
        if target is None:
            return False
        dice = linebreaker_dice(squad, target)
        if dice <= 0:
            return False
        self._pending = {"squad": squad, "target": target, "dice": dice}
        self._stage = "gate"
        self.dice_manager.roll(
            dice, 6, label=self.label, success_threshold=KROOT_LINEBREAKERS_THRESHOLD,
            target_name=target.name, attacker_squad=squad, target_squad=target)
        return True

    def on_dice_acknowledged(self):
        if self._pending is None:
            # No roll of our own outstanding - but an allocation session may
            # still owe a Feel No Pain acknowledgement. See _ack_session().
            return self._ack_session()
        values = (self.dice_manager.last_values if self.dice_manager is not None else None) or [1]
        ctx = self._pending
        if self._stage == "gate":
            hits = sum(1 for v in values if v >= KROOT_LINEBREAKERS_THRESHOLD)
            if hits <= 0:
                self._pending = None
                self._stage = None
                self._log(f"Kroot Linebreakers ({ctx['squad'].name}): no 4+ among "
                          f"{ctx['dice']} dice - {ctx['target'].name} is unharmed.")
                return True
            ctx["hits"] = hits
            self._stage = "amount"
            self.dice_manager.roll(
                hits, KROOT_LINEBREAKERS_DICE_SIDES,
                label=f"{self.label} - mortal wounds ({hits}D3)",
                target_name=ctx["target"].name, attacker_squad=ctx["squad"],
                target_squad=ctx["target"])
            return True
        self._pending = None
        self._stage = None
        target = ctx["target"]
        wounds = sum(values)
        # "if one or more enemy models are DESTROYED as a result" - counted
        # across the allocation, because a unit that soaks every mortal wound
        # takes no test however many it soaked.
        before = sum(1 for m in target.models if not m.is_dead())
        self._log(f"Kroot Linebreakers ({ctx['squad'].name}): {ctx['hits']} hit(s) - "
                  f"{target.name} suffers {wounds} mortal wound(s).")
        self._inflict(target, wounds)
        after = sum(1 for m in target.models if not m.is_dead())
        if after < before and self.battle_shock is not None:
            # start_forced_roll() is the "a rule orders a test out of turn"
            # entry point (game/battle_shock.py) - it deliberately skips
            # 08.03's Command-phase gate, and it returns whether a roll really
            # started, since a mortal-wound allocation may still owe dice.
            self._pending_battle_shock = target
        return True

    def resolve_pending_battle_shock(self):
        """Start the owed Battle-shock test once nothing else is using the
        dice. Called from main.py after the mortal-wound allocation settles -
        deferred rather than fired inline because _inflict() can leave an
        allocation pending, and DiceManager holds ONE roll at a time."""
        target = getattr(self, "_pending_battle_shock", None)
        if target is None or self.battle_shock is None:
            return False
        if self.mortal_wound_session is not None:
            return False
        if not self.battle_shock.start_forced_roll(target, self.label):
            return False
        self._pending_battle_shock = None
        return True
