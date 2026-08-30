"""Approximate "how badly does this attack go" arithmetic, shared by the AI's
threat/trade numbers and by any engine-side rule that has to judge whether an
attack is worth reacting to.

This math used to live entirely in ai/observation.py, which was the right home
while the AI was its only consumer. It moved here when a *rule* needed it:
Stim Injectors (game/stim_injectors.py) is a reactive Stratagem whose WHEN
fires on every single enemy target selection, so the engine has to decide
whether an incoming attack is even worth interrupting the game over - and
`game/` cannot import `ai/` (ai/observation.py imports half of `game/`; the
dependency runs one way only). Rather than grow a second, quietly diverging
estimator, the arithmetic lives here and ai/observation.py imports it - the
same "one definition" reasoning already applied to _model_capacity_cost
(game/formations.py) and _ingress_pack_positions (game/formation_layout.py).

wound_threshold() came along for the ride from game/shooting.py, and this is
its natural home: it is a pure S-vs-T table with no dependencies, and leaving
it in shooting.py would have made this module import shooting.py, closing an
import cycle (feel_no_pain -> stim_injectors -> damage_estimate -> shooting ->
damage_resolution -> feel_no_pain). game/shooting.py re-exports it under its
old private name, so every existing `from game.shooting import _wound_threshold`
importer (game/fight.py, ai/agent_driver.py, ai/observation.py) is unaffected.

APPROXIMATE ON PURPOSE, and every consumer inherits the same caveats: no
re-rolls, no [SUSTAINED HITS]/[LETHAL HITS]/[DEVASTATING WOUNDS]/[BLAST], no
cover, no invulnerable-save edge cases beyond taking the better of the two
saves, and no per-weapon range filtering unless the caller passes a distance
(see expected_wounds_against()). It answers "roughly how badly does this
matchup go", which is what a positioning decision - or a "is this worth 1 CP"
decision - needs, not "what will this attack roll".
"""

from game.squad import (attached_unit_toughness, squad_has_guardian_drone,
                        tank_hunters_modifiers)


def wound_threshold(strength, toughness):
    """Rule 05.02's Strength-vs-Toughness table: the D6 result a Wound roll
    needs to succeed."""
    if strength >= 2 * toughness:
        return 2
    if strength > toughness:
        return 3
    if strength == toughness:
        return 4
    if 2 * strength <= toughness:
        return 6
    return 5


def _skill_value(raw, default=4):
    """Turn a printed characteristic like "4+" into the number 4."""
    try:
        return int(str(raw).rstrip("+"))
    except (TypeError, ValueError):
        return default


class DefenderStats:
    """The defensive statline one attack resolves against: rule 19.02's
    pooled Toughness for the unit, with save/wounds taken from the model
    that will actually be allocated the hit. A tiny shim so expected_wounds()
    can keep taking one "profile"-shaped object rather than growing three
    more parameters, and so the 19.02 substitution happens in exactly one
    place."""

    def __init__(self, toughness, model_profile):
        self.toughness = toughness
        self.armor_save = model_profile.armor_save
        self.invulnerable_save = getattr(model_profile, "invulnerable_save", None)
        self.wounds = model_profile.wounds


def defender_soak(defender):
    """(DefenderStats, wounds_per_model) for whichever models will actually
    absorb this attack.

    Rule 19.02 says an attack against an attached unit resolves against the
    BODYGUARD models' Toughness, so use that rather than any one model's.
    Saves and wounds-per-model are read off the models that will actually
    soak the hits - rule 05.03 allocates to the first allocation group, and
    CHARACTER groups are ordered last, so a character in a unit does not
    make the unit tougher to chew through until it is the last group
    standing."""
    toughness = attached_unit_toughness(defender)
    soak_group = next((g for g in defender.allocation_groups() if g), defender.models)
    return DefenderStats(toughness, soak_group[0].profile), max(1, soak_group[0].profile.wounds)


def models_destroyed_by(defender, total_wounds):
    """How many of `defender`'s models `total_wounds` is expected to destroy,
    counting the wounds those models ACTUALLY have left rather than their
    printed characteristic. Fractional on purpose - half a model killed is a
    meaningful ranking signal, and every caller either reports it as a rate or
    compares it against a fraction of the unit.

    This used to be a flat `total_wounds / wounds_per_model`, which reads a
    damaged unit as though it were fresh. User report: "die panzaknacker haben
    auf die feuerkrieger geschossen, obwohl da auch ein angeschlagener riptide
    stand. das macht keinen sinn. die haben doch anti tank waffen". Measured on
    those exact datasheets, a Riptide's value to a Tankbusta squad was 22.8
    points a turn whether it had 14 wounds left or 1 - so "finish it off",
    which is the whole reason to shoot the wounded thing, was invisible to
    every ranking built on this. At 1 wound left the same shot is now worth the
    Riptide's full 190 points, because that is what killing it removes from the
    board.

    Wounds are spent in the order the rules allocate them: rule 05.03's
    allocation groups in order (so an attached unit's bodyguards soak before
    its CHARACTER), and within a group the already-wounded models first, which
    is rule 05.04's first step. That ordering is what makes the estimate rise
    for a damaged unit instead of averaging the damage away.

    Note the deliberate asymmetry with expected_wounds()'s overkill cap, which
    still uses the PRINTED wounds: the cap asks "how much of a hit is wasted on
    a typical model of this unit", and the models queued up behind the wounded
    one are undamaged. Capping on the current wounds of the front model would
    understate every shot at a squad whose leader happens to be hurt."""
    if not total_wounds or total_wounds <= 0:
        return 0.0

    pools = []
    for group in defender.allocation_groups():
        alive = [m for m in group
                 if (m.current_wounds if m.current_wounds is not None
                     else m.profile.wounds) > 0]
        # Rule 05.04 step 1: a model that has already lost wounds must be
        # allocated the attack, so it is the one that dies first.
        alive.sort(key=lambda m: m.current_wounds if m.current_wounds is not None
                   else m.profile.wounds)
        pools.extend(m.current_wounds if m.current_wounds is not None
                     else m.profile.wounds for m in alive)
    if not pools:
        return 0.0

    destroyed, left = 0.0, total_wounds
    for pool in pools:
        if left >= pool:
            destroyed += 1.0
            left -= pool
        else:
            destroyed += left / pool
            break
    return destroyed


def _threshold_chance(need):
    """Chance a D6 meets `need`, with the floor both rules 05.01 and 05.02
    impose: an unmodified 1 always fails, so nothing is ever better than 5/6.
    That floor only starts mattering once modifiers are honoured - without
    them no printed characteristic reaches it."""
    return max(0.0, min(5.0 / 6.0, (7 - need) / 6.0))


def attack_modifiers(attacker_model, defender, melee=False):
    """The (hit, wound) threshold modifiers a shot from `attacker_model` at
    `defender` picks up, in this engine's Modifier sign convention (positive
    worsens the threshold).

    Read off the SAME shared helpers the real resolution uses
    (game/shooting.py's and game/fight.py's own _hit_modifiers()/
    _wound_modifiers()), never a second copy of the rule - the estimate and
    the dice must not be able to disagree about what an ability does.

    Deliberately only the abilities that depend on nothing but the attacking
    MODEL and the TARGET UNIT. Everything else the real resolution applies is
    left out on purpose, and for a reason rather than for effort:

      * Benefit of Cover, Guided/Target Uploaded, [HEAVY] all depend on where
        the models stand or on what happened earlier in the turn, and this
        estimate is called for hypothetical positions as much as for real
        ones (see expected_wounds_against() on `gap_in`).
      * 'Ard as Nails and the like are Stratagem states that last a phase; a
        planning number that swung with them would describe this instant
        rather than the matchup.

    Still missing and now cheap to add, in rough order of what they are
    worth: Might is Right (melee hit, Warboss-led units), Volley Fire (an
    extra Attack per ranged weapon), Waaagh! (+1 A and +1 S in melee). Each
    is one line here; each needs its own measurement, which is why they are
    named rather than swept in."""
    hit = wound = 0
    # `melee` is threaded through so the Myphitic Blight-hauler's ranged-only
    # Tank Hunters is not counted for its Gnashing Maw - see
    # game/squad.py's tank_hunters_modifiers() on why there are two flags.
    for modifier in tank_hunters_modifiers(attacker_model, defender, melee=melee):
        # Tankbustas' Tank Hunters is +1 to Hit AND +1 to Wound against a
        # MONSTER or VEHICLE unit - the whole reason an anti-tank unit is an
        # anti-tank unit, and it was worth exactly nothing here. User:
        # "noch dazu haben sie anti tank regeln, also die entscheidung war
        # auf allen ebenen falsch."
        hit += modifier.amount
        wound += modifier.amount
    if not melee and squad_has_guardian_drone(defender):
        # The defender's side of the same coin. Counting only the attacker's
        # buffs would trade one bias for another.
        wound += 1
    return hit, wound


def expected_wounds(weapon, shots, skill, defender_profile,
                    hit_modifier=0, wound_modifier=0):
    """Expected wounds one weapon inflicts with `shots` attacks at `skill`
    (the printed WS/BS of whoever is swinging it) against `defender_profile`.

    Factored out of expected_wounds_against() so a SINGLE melee weapon can be
    valued on its own - which is what rule 04.01's "select one melee weapon"
    forces the Fight phase to do: a model with a Power Klaw (A3 WS4+ S9 AP-2
    D2) and a Choppa (A3 WS3+ S4 AP-1 D1) has to commit to one of them, and
    the better choice depends entirely on what it is hitting. `weapon.attacks`
    is used as-is, so a weapon with a printed dice Attacks characteristic
    (attacks_notation) is valued off its preview number."""
    d_save = _skill_value(defender_profile.armor_save, 7)
    invuln = _skill_value(defender_profile.invulnerable_save, 7)
    hit = _threshold_chance(_skill_value(skill) + hit_modifier)
    wound_on = wound_threshold(weapon.strength, defender_profile.toughness)
    wound = _threshold_chance(wound_on + wound_modifier)
    # AP is printed as a negative modifier; a worse save is a higher number.
    save_needed = min(d_save - weapon.ap, invuln)
    fail_save = max(0.0, min(1.0, (save_needed - 1) / 6.0))
    # Damage in excess of a model's Wounds is WASTED - damage is allocated to
    # one model at a time and what is left over when it dies does not carry to
    # the next (only Mortal Wounds do). Counting it anyway valued a D3 rocket
    # against 1-wound Kroot as three kills per wound instead of one, which
    # inflated exactly the matchup an anti-tank weapon is worst at: measured on
    # the reported board, Tankbustas "expected" to erase 5.8 of 10 Kroot, so
    # every ranking built on this - target choice, threat numbers, and the
    # reserve landing score the user reported ("tankbustas und kopter sind
    # beides antitank einheiten... sie hätten die crisis zb beschießen können")
    # - preferred a cheap screen over the Battlesuits the unit exists to kill.
    effective_damage = min(weapon.damage, max(1, defender_profile.wounds))
    return shots * hit * wound * fail_save * effective_damage


def expected_wounds_against(attacker, defender, melee=False, gap_in=None):
    """Total wounds one round of `attacker`'s shooting (or fighting) is
    expected to strip off `defender`, before any Feel No Pain. None if either
    side has no models left.

    This is the raw number; ai/observation.py's expected_kills() divides it by
    wounds-per-model to express the same thing in models destroyed, and
    game/stim_injectors.py uses it directly, because a damage-reduction
    ability saves WOUNDS, not models.

    Both sides are evaluated MODEL BY MODEL rather than from a single
    representative statline. That used to be "models[0]'s weapons times the
    model count" against "models[0]'s T/Sv/W", which is exact for a
    homogeneous squad and badly wrong for an attached unit (19.01): a
    Warboss merged into a Boyz mob would have had its Power Klaw ignored
    entirely and its 6 wounds and 2+ save read as a Boy's 1 and 6+. Since
    an attached unit is precisely the case this most needs to judge
    correctly - it is the biggest threat and the biggest prize on the board
    - the arithmetic is done per model. For a homogeneous squad this is the
    same sum as before, just reached the long way.

    `gap_in` is the edge-to-edge distance to the target; give it and a ranged
    weapon whose own Range does not cover that distance is left out. OFF by
    default, and deliberately: the caller has to know whether the distance is
    a fact or a guess. It is a fact for a shot being taken right now, and a
    guess for a planning question, because shooting happens after moving - a
    gate on the gap as it stands would understate every mobile shooter on the
    board, which is a mistake _reaches_this_turn() had to have corrected once
    already. Measured on the reported activation: a Deffkopta squadron's
    12" Sluggas were being counted against Stealth Battlesuits 16" away,
    which is most of the reason shooting them looked as good as shooting the
    vehicle its 24" Rokkits were for (26.0 vs 28.6 points ungated, 22.2 vs
    29.0 with the guns that cannot reach left out)."""
    if not attacker.models or not defender.models:
        return None
    want = "melee" if melee else "ranged"
    d_profile, _ = defender_soak(defender)

    total_wounds = 0.0
    for model in attacker.models:
        skill = model.profile.weapon_skill if melee else model.profile.ballistic_skill
        hit_mod, wound_mod = attack_modifiers(model, defender, melee=melee)
        best_selectable = 0.0
        for weapon in model.weapons:
            if getattr(weapon, "weapon_type", None) != want:
                continue
            if not melee and gap_in is not None and getattr(weapon, "range_in", 0) < gap_in:
                continue
            value = expected_wounds(weapon, weapon.attacks, skill, d_profile,
                                    hit_modifier=hit_mod, wound_modifier=wound_mod)
            if melee and not weapon.extra_attacks:
                # Rule 04.01: a model making melee attacks uses ONE of its
                # melee weapons, not all of them - only [EXTRA ATTACKS]
                # weapons (24.11) swing "in addition to any others".
                best_selectable = max(best_selectable, value)
            else:
                total_wounds += value
        total_wounds += best_selectable
    return total_wounds
