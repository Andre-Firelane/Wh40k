import math
from game import config
from game import formation_layout
from game import line_of_sight
from game import reanimation_protocols
from game import status_effects
from game.ingress import INGRESS_MIN_BATTLE_ROUND
from game.missions import BATTLE_ROUNDS
from game.damage_estimate import (defender_soak, expected_wounds, models_destroyed_by,  # noqa: F401 - expected_wounds is re-exported: ai/agent_driver.py calls observation.expected_wounds()
                                  expected_wounds_against)
from game.coldstar import effective_movement_in
from game.ere_we_go import roll_bonus as charge_roll_bonus
from game.hazard import MORTAL_WOUNDS_ON_FAIL, MORTAL_WOUNDS_ON_FAIL_MONSTER_VEHICLE
from game.squad import (attached_unit_toughness, edge_distance, is_monster_or_vehicle_unit,
                        max_model_radius, min_model_movement)
from game.transport import TACTICAL_DISEMBARK_DISTANCE_IN
from game.waaagh import squad_waaagh_active
from game.weapons import MELEE, RANGED


def _all_weapons(squad):
    """Every weapon carried by every living model in the unit.

    Weapon reporting used to read squad.models[0].weapons, which is exact
    while a Squad is homogeneous. An attached unit (19.01) merges two
    datasheets into one unit, so a representative model no longer represents
    it - the leader's gun and melee weapon are simply absent from models[0].
    Callers dedupe by label, so listing them all costs nothing for a normal
    squad and is the difference between seeing and not seeing a Power Klaw
    for an attached one."""
    alive = [m for m in squad.models if not m.is_dead()] or squad.models
    return [w for m in alive for w in m.weapons]


def ranged_weapon_summary(squad):
    """Compact "what can this unit actually shoot with" line (S/AP/D per
    distinct ranged weapon on the squad's representative model) - the same
    summary the Shooting-phase options already carry, reused here so the
    strategic planner can judge which of its units is worth committing to a
    fight instead of inferring firepower from a squad name."""
    seen = []
    # Every model's weapons, not just a representative one: an attached unit
    # (19.01) is a single unit carrying two datasheets' loadouts, and listing
    # only models[0]'s would hide exactly the weapon that made the character
    # worth attaching - the same "described by a weapon nobody mentioned"
    # failure melee_weapon_summary() below was written to fix.
    for weapon in _all_weapons(squad):
        if getattr(weapon, "weapon_type", None) != "ranged":
            continue
        # Range included alongside S/AP/D: without it the planner could see
        # that a target is 30" away but had no way to tell whether any of its
        # own weapons actually reach that far.
        label = f"{weapon.name} (range {weapon.range_in:.0f}\", S{weapon.strength}/AP{weapon.ap}/D{weapon.damage})"
        if label not in seen:
            seen.append(label)
    return ", ".join(seen) if seen else "no ranged weapons"


def melee_weapon_summary(squad):
    """What this unit brings to CLOSE COMBAT.

    The observation reported ranged weapons only, which meant a melee unit was
    described to the planner purely by its sidearm - Ork Boyz appeared as "a
    Slugga (12", S4/AP0/D1)" with no hint of the Big Choppa (S7/AP-1/D2, 3
    attacks) that is the entire reason the unit exists. Asked to plan for that
    unit, the only capability on the sheet was a single weak pistol shot, so
    "get out of the transport and fire it" was a reasonable read of a
    description that was simply wrong. User, on exactly that move: "Die KI
    sollte schon grundlegendes taktisches Verstaendnis fuer das Spiel haben."
    It cannot, about a weapon nobody told it about."""
    seen = []
    for weapon in _all_weapons(squad):
        if getattr(weapon, "weapon_type", None) != "melee":
            continue
        label = (f"{weapon.name} (S{weapon.strength}/AP{weapon.ap}/D{weapon.damage}"
                 f", {getattr(weapon, 'attacks', '?')} attacks)")
        if label not in seen:
            seen.append(label)
    return ", ".join(seen) if seen else "no melee weapons"


def defensive_profile(squad):
    """How hard this unit is to kill: Toughness, Save, wounds per model.

    Both sides get it. A datasheet is open information in 40k - both players
    read each other's - and without it no threat assessment is possible at
    all: "which of my units does that enemy gun actually hurt" and "can I
    afford to stand here" are both S-vs-T and AP-vs-Sv questions."""
    if not squad.models:
        return None
    p = squad.models[0].profile
    profiles = [m.profile for m in squad.models]
    out = {
        # Rule 19.02: attacks against an attached unit resolve against the
        # bodyguard models' Toughness, which is what an opponent sizing up
        # the unit actually faces.
        "toughness": attached_unit_toughness(squad),
        "save": p.armor_save,
        "wounds_per_model": p.wounds,
        # Rule 19.03: "an attached unit has all of the keywords of all of its
        # component units" - any(), so a FLY character joining INFANTRY makes
        # the unit count as both for any rule keyed off either.
        "keywords": [k for k, attribute in (
            ("INFANTRY", "infantry"), ("VEHICLE", "vehicle"), ("MONSTER", "monster"),
            ("FLY", "fly"), ("BEASTS", "beasts"), ("SWARM", "swarm"),
        ) if any(getattr(pr, attribute) for pr in profiles)],
    }
    characters = [m for m in squad.models if m.profile.character]
    if characters and len(squad.models) > len(characters):
        # An attached unit (19.01). Spelled out rather than left implicit:
        # the character cannot be shot out of the unit, its own statline
        # differs from the line above, and rule 05.03 puts it LAST in the
        # allocation order - so an opponent has to chew through the
        # bodyguards first. All three change how the unit should be handled.
        out["attached_characters"] = [{
            "name": m.profile.name,
            "toughness": m.profile.toughness,
            "save": m.profile.armor_save,
            "wounds": m.profile.wounds,
        } for m in characters]
        out["note"] = (
            "attached unit (19.01) - the character is part of this unit and cannot be "
            "targeted separately; wounds are allocated to the bodyguard models first (05.03)"
        )
    return out


CHARGE_THREAT_RANGE_IN = 12.0  # rule 11.01: a charge is declared within 12"


def disembark_reach_in(transport_token):
    """How much closer to everything a passenger ends up simply by getting
    out: the disembark distance (18.04), measured from the HULL, so the
    transport's own radius counts too.

    This is game/transport.py's own placement radius for a tactical disembark
    (TACTICAL_DISEMBARK_DISTANCE_IN + transport_token.radius_in), named here
    so the places that reason about a passenger's reach cannot drift apart.
    ai/agent_driver.py's _reach_to_point() already allowed for it; the threat
    numbers in this file did not, and treated the transport as a dimensionless
    point that the unit had to move away from under its own power."""
    return TACTICAL_DISEMBARK_DISTANCE_IN + transport_token.radius_in


def _point_distance_to_squad(point, squad, own_spread_in=0.0):
    """Edge distance from a planned position to `squad`.

    `own_spread_in` matters more than it looks. A charge is measured between the
    two CLOSEST models, but a planned position is a single point - the centre of
    where a unit will stand. Ignoring the unit's own footprint therefore reports
    the gap from its middle instead of from its leading edge, understating every
    charge threat by roughly half the formation's depth. That is the second half
    of the error a user die roll exposed: "ich habe glaube ich eine 6 gewuerfelt.
    das sind mehr als 39%" - the reported 9+ was measured centre-to-edge with the
    reported 9+ was measured from the unit's centre instead of its leading
    edge."""
    return min(
        ((point[0] - m.x_in) ** 2 + (point[1] - m.y_in) ** 2) ** 0.5 - m.radius_in - own_spread_in
        for m in squad.models
    )


def _squad_spread_in(squad):
    """How far the outermost model sits from the unit's centre, plus its base -
    the radius of the disc a planned position actually occupies."""
    if not squad.models:
        return 0.0
    cx = sum(m.x_in for m in squad.models) / len(squad.models)
    cy = sum(m.y_in for m in squad.models) / len(squad.models)
    return max(math.hypot(m.x_in - cx, m.y_in - cy) + m.radius_in for m in squad.models)


def combined_charge_chance(threats):
    """One number: the chance that SOMETHING charges you.

    Reporting only the per-unit odds invited exactly the mistake it was meant to
    prevent. On the reported move the destination carried three threats - 28%,
    8% and 8% - and the plan justified itself with "only 8% chance to be charged
    first", quoting the smallest and dropping the one that mattered. Nothing was
    wrong with the individual figures; a list of three numbers simply lets you
    pick your favourite, so the aggregate has to be stated too."""
    survive = 1.0
    for threat in threats:
        raw = threat.get("chance_to_reach_you", "")
        if raw.startswith("certain"):
            return "certain - something will reach you"
        if raw.startswith("impossible"):
            continue
        try:
            survive *= 1.0 - float(raw.split("%")[0]) / 100.0
        except ValueError:
            continue
    return f"{100.0 * (1.0 - survive):.0f}% chance something charges you"


AVERAGE_ADVANCE_IN = 3.5  # the mean of a D6, rule 09.06's Advance roll


def advance_reach_in(squad):
    """How far this unit gets THIS turn if it Advances (rule 09.06): its Move
    characteristic plus the average Advance roll, plus any standing bonus to
    that roll (War Horde's 'Ere We Go, +2 - see game/ere_we_go.py).

    Reported as the AVERAGE rather than the guaranteed minimum (M+1) because
    the movement code degrades gracefully: a unit that rolls low simply ends
    up short of the point it was aiming at, still facing the right way, and
    under an active WAAAGH! it can still charge from wherever it stopped. A
    minimum-case radius would give up 2.5" of ground every turn to avoid a
    failure mode that costs nothing.

    Exists because every reach number this AI works with was the M
    characteristic alone, which quietly made Advance unreachable: the planner
    is told its position orders must lie inside a circle of radius M, the
    validator clamps anything outside it back in, and the tactical layer then
    offers an Advance only when the commanded point is FURTHER than M - a
    condition the first two rules had already made impossible. Measured over
    the reported WAAAGH! turn, the planner ordered six units to "Advance" and
    the tactical layer had an Advance option for exactly one of them (the only
    one whose plan named no position at all)."""
    return min_model_movement(squad) + AVERAGE_ADVANCE_IN + charge_roll_bonus(squad)


def charge_chance_after_advancing(squad, enemy, at_point=None):
    """Probability of completing a charge on `enemy` this turn if the unit
    ADVANCES first, as a percentage.

    The exact joint distribution over both rolls - each D6 Advance result
    weighted 1/6, and for each the 2D6 charge it then leaves - rather than
    "average advance, then charge". Averaging first is wrong in the direction
    that matters: charge probability is a step function of the remaining gap,
    so the mean of the outcomes is not the outcome of the mean, and near a
    threshold the difference is large.

    Only meaningful where Advancing does not itself forfeit the charge (rule
    09.06) - i.e. while an Ork WAAAGH! is active, which is the case the user
    raised: "gerade im waagh zug hat man dadurch ja kaum abzuege. man darf
    danach noch chargen." Callers gate on that; this function only does the
    arithmetic."""
    gap = (_point_distance_to_squad(at_point, enemy, _squad_spread_in(squad))
           if at_point is not None else _squad_distance(squad, enemy))
    move = min_model_movement(squad)
    bonus = charge_roll_bonus(squad)  # applies to the Advance roll AND the charge roll
    total = 0.0
    for die in range(1, 7):
        after = max(0.0, gap - move - die - bonus)
        total += charge_roll_chance(max(0.0, after - bonus))
    return total / 6.0


def charge_roll_chance(needed_in):
    """Probability that 2D6 covers `needed_in` inches, as a percentage."""
    if needed_in <= 2.0:
        return 100.0
    if needed_in > 12.0:
        return 0.0
    need = math.ceil(needed_in)
    hits = sum(1 for a in range(1, 7) for b in range(1, 7) if a + b >= need)
    return 100.0 * hits / 36.0


def charge_now(squad, enemy, at_point=None, advance_keeps_charge=False):
    """What a charge on `enemy` costs THIS turn if the unit moves flat out
    first - the roll it would then need and how likely that is.

    Reported so the planner does not have to derive it, which is the same
    reason distances carry `turns_to_reach` and matchups carry a wound
    threshold: every number this AI has to work out for itself, it works out
    badly. Without it, "advance and charge now" and "stage and charge next
    turn" look like two plans of equal standing, and the second one always
    reads as the safer.

    Straight from the reported turn (logs/game_20260819_222130.log): the mob
    was ordered to a staging spot worth 1" of ground with the reason "close
    distance under WAAAGH! for a charge next turn". Moving flat out instead
    would have left 4.2" to the Ghostkeel - a 5+ charge at 83%, and 97% with
    the 'Ere We Go the AI had already paid for that same turn. Nothing in the
    observation said so.

    Rule 11.04, BEFORE MOVING: the roll must cover the WHOLE remaining gap,
    with no engagement-range discount.

    `advance_keeps_charge` is for the one case where the unit has a SECOND,
    longer move available that does not cost it the charge - an active Ork
    WAAAGH! (rule 09.06 normally forfeits the charge for Advancing; the army
    rule suspends that). The extra D6 is then close to free for a melee unit,
    and the planner had no number saying so: it read one figure computed on
    the flat Move characteristic and ordered a stage-and-charge-next-turn
    where an Advance would have charged this turn. User: "gerade im waagh zug
    hat man dadurch ja kaum abzuege. man darf danach noch chargen." """
    gap = (_point_distance_to_squad(at_point, enemy, _squad_spread_in(squad))
           if at_point is not None else _squad_distance(squad, enemy))
    needed = max(0.0, gap - min_model_movement(squad))
    bonus = charge_roll_bonus(squad)
    entry = {
        "gap_after_moving_in": round(needed, 1),
        "charge_roll_needed": max(2, math.ceil(needed) - bonus),
        "chance_to_reach_it_this_turn": f"{charge_roll_chance(max(0.0, needed - bonus)):.0f}%",
    }
    if advance_keeps_charge:
        entry["chance_if_you_advance_first"] = (
            f"{charge_chance_after_advancing(squad, enemy, at_point=at_point):.0f}%"
            " - WAAAGH! is active, so Advancing costs only non-Assault shooting, not the charge"
        )
    return entry


def charge_threats(squad, enemy_squads, at_point=None):
    """Which enemy units could charge this one on their next turn, and how hard
    they hit in melee.

    User request, and the reason it matters most to a shooting army: "Welche
    der Gegner können mich chargen? Hat der Gegner gefährliche Nahkampftrupps,
    die mich leicht chargen können? Muss ich meine eigenen Einheiten vielleicht
    etwas weiter entfernt stellen, damit der Charge schwieriger wird?" A charge
    is declared within 12" AFTER moving, so the reach that matters is the
    enemy's own movement plus 12" - and that is a number the planner cannot
    work out from raw coordinates.

    Reported per threatening unit with the roll it would need, so "just out of
    comfortable reach" and "will certainly reach me" are distinguishable
    rather than both reading as "an enemy is nearby"."""
    threats = []
    for enemy in enemy_squads:
        if not enemy.models:
            continue
        melee = melee_weapon_summary(enemy)
        if melee == "no melee weapons":
            continue
        gap = (_point_distance_to_squad(at_point, enemy, _squad_spread_in(squad))
               if at_point is not None else _squad_distance(squad, enemy))
        reach = min_model_movement(enemy)
        # The roll must cover the WHOLE gap, with no engagement-range discount.
        # Rule 11.04, BEFORE MOVING: a unit may only be selected as a charge
        # target if it is "within 12\" of your unit AND within the maximum
        # distance of your unit" - the maximum distance being the charge roll.
        # Being engaged afterwards is an additional requirement on the finished
        # move, not a reduction of what the roll has to reach. (Briefly
        # subtracted 2" here; the user quoted 11.04 to correct it.)
        needed = gap - reach
        if needed > CHARGE_THREAT_RANGE_IN:
            continue
        chance = charge_roll_chance(needed)
        if chance >= 100.0:
            odds = "certain (needs 2+ on 2D6)"
        elif chance <= 0.0:
            odds = "impossible"
        else:
            odds = f"{chance:.0f}% chance"
        threats.append({
            "unit": enemy.name,
            "distance_in": round(gap, 1),
            "moves_in": reach,
            "charge_roll_needed": max(2, round(needed)),
            "chance_to_reach_you": odds,
            "melee": melee,
        })
    threats.sort(key=lambda t: t["charge_roll_needed"])
    return threats


def expected_kills(attacker, defender, melee=False, gap_in=None):
    """Expected models of `defender` destroyed by one round of `attacker`'s
    shooting (or fighting), as a count and as a fraction of the unit.

    This is the number every threat judgement actually needs, and the reason
    to compute it here rather than hand over raw statlines: the planner was
    given S/AP/D and T/Sv and asked to combine them, which it does
    unreliably - the same failure that made it fire anti-infantry guns at a
    Devilfish until the wound threshold was computed for it. Deliberately
    expressed in models-per-turn rather than an abstract 1-100 danger score:
    a number with units can be sanity-checked and debugged, an invented index
    cannot.

    Approximate on purpose - no re-rolls, no [SUSTAINED HITS]/[LETHAL HITS]/
    [DEVASTATING WOUNDS]/[BLAST], no cover, no invulnerable-save edge cases
    beyond taking the better of the two saves. It answers "roughly how badly
    does this matchup go", which is what a positioning decision needs, not
    "what will this attack roll".

    Both sides are evaluated MODEL BY MODEL rather than from a single
    representative statline. That used to be "models[0]'s weapons times the
    model count" against "models[0]'s T/Sv/W", which is exact for a
    homogeneous squad and badly wrong for an attached unit (19.01): a
    Warboss merged into a Boyz mob would have had its Power Klaw ignored
    entirely and its 6 wounds and 2+ save read as a Boy's 1 and 6+. Since
    an attached unit is precisely the case the AI most needs to judge
    correctly - it is the biggest threat and the biggest prize on the board
    - the arithmetic is done per model. For a homogeneous squad this is the
    same sum as before, just reached the long way.

    The arithmetic itself lives in game/damage_estimate.py - it moved there
    when game/stim_injectors.py needed the same estimate and `game/` cannot
    import `ai/`. This function is the "expressed in models" wrapper around
    it; expected_wounds_against() is the same number in wounds."""
    if not attacker.models or not defender.models:
        return None
    total_wounds = expected_wounds_against(attacker, defender, melee=melee, gap_in=gap_in)
    kills = min(len(defender.models), models_destroyed_by(defender, total_wounds))
    return {
        "models_killed_per_turn": round(kills, 1),
        "fraction_of_unit": round(kills / len(defender.models), 2),
    }


THREAT_LIST_LIMIT = 3  # incoming threats only - see threat_assessment()


def _reaches_this_turn(attacker, defender, melee, gap=None):
    """Can `attacker` bring this kind of attack to bear on `defender` next
    turn? Out of reach means zero danger, which is the whole point of gating:
    an anti-tank team on the far side of the board is not a threat to anything.

    Ranged: some weapon's range covers the gap as it stands. Melee: the gap
    minus the attacker's move is inside charge range (rule 11.01)."""
    if not attacker.models or not defender.models:
        return False
    if gap is None:
        gap = _squad_distance(attacker, defender)
    if melee:
        return gap - min_model_movement(attacker) <= CHARGE_THREAT_RANGE_IN
    ranges = [w.range_in for w in _all_weapons(attacker)
              if getattr(w, "weapon_type", None) == "ranged"]
    # The attacker's move counts here too. Shooting happens AFTER moving, so a
    # unit 24" away with an 18" gun and a 6" move is very much a threat - and
    # this used to compare the gap as it stands, understating every mobile
    # shooter on the board (user: "berücksichtigt die auch, dass ich meine
    # einheiten noch bewegen kann, bevor ich schieße, charge?" - for melee it
    # did, for shooting it did not).
    return bool(ranges) and gap - min_model_movement(attacker) <= max(ranges)


def _worst_case(attacker, defender, gap=None):
    """The more dangerous of this attacker's two attack modes that can
    actually reach, as (kills, fraction, how)."""
    best = None
    for melee, label in ((False, "shooting"), (True, "melee")):
        if not _reaches_this_turn(attacker, defender, melee, gap=gap):
            continue
        got = expected_kills(attacker, defender, melee)
        if got is None:
            continue
        if best is None or got["models_killed_per_turn"] > best[0]:
            best = (got["models_killed_per_turn"], got["fraction_of_unit"], label)
    return best


TARGET_LIST_LIMIT = 2  # per attack mode - see ranked_targets()


def _target_entry(squad, enemy, melee, with_position, charge_from=None, advance_keeps_charge=False):
    """One "what this unit does to that one" row, or None if it does nothing
    worth reporting.

    Ranked on `value_you_remove_per_turn` (see damage_value()) and NOT on the
    casualty count, which is the distinction this whole file turns on: a
    specialist erases a larger share of a cheap screen than of the expensive
    thing it was built to kill, so counting bodies aims it at the screen. The
    casualty count is kept alongside because it is what the number means
    physically, and a value with no units behind it cannot be sanity-checked.

    Dropped on the VALUE rather than on the casualty count, so the cutoff and
    the sort agree. Filtering on bodies while ranking on points quietly
    discarded 269 pairings across the two rosters that were worth up to 9.5
    points a turn - a fraction of a wound on something expensive. Measured: it
    changes none of the 32 top-two lists on these armies, so this is
    consistency rather than a behaviour change, but the two criteria had no
    business being different."""
    got = expected_kills(squad, enemy, melee=melee)
    value = damage_value(squad, enemy, melee=melee)
    if got is None or value <= 0.05:
        return None
    entry = {
        "unit": enemy.name,
        "value_you_remove_per_turn": round(value, 1),
        "kills_per_turn": got["models_killed_per_turn"],
        "fraction_of_their_unit": got["fraction_of_unit"],
    }
    if melee and charge_from is not False:
        # What it would take to be IN that fight this turn, not next one. See
        # charge_now().
        entry.update(charge_now(squad, enemy,
                                at_point=charge_from if charge_from is not True else None,
                                advance_keeps_charge=advance_keeps_charge))
    if with_position:
        entry["where_it_is"] = {
            "x": round(sum(m.x_in for m in enemy.models) / len(enemy.models), 1),
            "y": round(sum(m.y_in for m in enemy.models) / len(enemy.models), 1),
        }
    # The trade: points we would remove against points we would risk.
    mine, theirs = getattr(squad, "points", None), getattr(enemy, "points", None)
    if mine and theirs:
        entry["your_points"] = mine
        entry["their_points"] = theirs
        entry["trade"] = ("trading UP - they are worth more than you"
                          if theirs > mine else
                          "trading down - you are worth more than them")
    return entry


def ranked_targets(squad, enemy_squads, limit=TARGET_LIST_LIMIT, reaches=None,
                   with_position=False, charge_from=None, advance_keeps_charge=False):
    """What this unit is FOR: the enemy units it is actually good against,
    ranked by points removed per turn and reported SEPARATELY for shooting and
    for melee.

    The two modes are kept apart rather than merged into one "best" figure,
    because merging them describes the unit's role WRONGLY. Measured on the
    reported case: an Ork Tankbusta squad's merged list is Kroot Carnivores /
    Strike Team / Breachers, all in MELEE, and the Battlesuits its S9/AP-2/D3
    Rokkits exist for are nowhere on it - a mob of bodies is worth a lot of
    swings, so a single list buries the anti-tank role every time. Split, the
    same squad reads "best_to_shoot: The Twin Lance 33, Ghostkeel 28". Same
    shape, and the same reason, as the split between ranged_weapons and
    melee_weapons in squad_summary().

    Two user reports, one root cause ("die panzaknackas ... haben sehr gute
    anti tank waffen und haben sich hinter der mauer versteckt. konnten so ihr
    potential nicht abrufen" and "die deffkopter haben auch anti tank waffen.
    haben aber irgendwie immer auf die stealth suites geschossen. und die
    fahrzeuge ignoriert"). Both units were described to the planner by a list
    ranked in bodies, and across every log kept so far a vehicle appears in
    only 3.8% of the entries - 14 of 747 for the Tankbustas - while the enemy
    army has four of them. A unit told its best use is charging a Kroot mob
    behaves like a melee unit: it closes, and while closing it stages in cover.

    `reaches(enemy, melee)` gates each pairing on whether the attack can
    actually be brought to bear; pass None for a unit that has no position yet
    (a reserve unit), where the question is what it is for and not what it can
    hit from where it is standing."""
    out = {}
    for melee, key, kind in ((False, "best_to_shoot", RANGED),
                             (True, "best_to_charge", MELEE)):
        if not any(getattr(w, "weapon_type", None) == kind for w in _all_weapons(squad)):
            continue
        rows = []
        for enemy in enemy_squads:
            if not enemy.models:
                continue
            if reaches is not None and not reaches(enemy, melee):
                continue
            entry = _target_entry(squad, enemy, melee, with_position, charge_from=charge_from,
                                  advance_keeps_charge=advance_keeps_charge)
            if entry is not None:
                rows.append(entry)
        rows.sort(key=lambda e: -e["value_you_remove_per_turn"])
        out[key] = rows[:limit]
    return out


def threat_assessment(squad, enemy_squads, at_point=None, point_radius_in=0.0,
                      advance_keeps_charge=False):
    """Both halves of the risk question for one of our units: what can hurt it,
    and what it can hurt back.

    User's framing, and the reason both directions are needed: "manchmal ist
    eine einheit so effektiv gegen eine andere, dass sie nach oben traden. ein
    boytrupp kann einen crisis trupp töten, obwohl er günstiger ist. das ist
    ein guter handel. da sollte er aggressiv werden." A danger number on its
    own only ever argues for hiding; paired with what the unit gives back -
    and with the points on both sides - it becomes a trade.

    Deliberately reports only the worst few threats and best few targets
    rather than every pairing: a full matrix is 60+ entries per turn and would
    drown the plan in exactly the way the user warned about.

    The outgoing half is ranked_targets() - value-ranked and split by attack
    mode - rather than a second, differently-sorted opinion about the same
    question. It used to be a single list ranked by casualties, which is how a
    Rokkit team came to be told its best use was charging a Kroot mob; see
    ranked_targets() for the measurement. The reserve-only field that already
    stated a unit's role correctly is now simply the same function without the
    reach gate, so an on-board unit and an off-board one can no longer be
    described by two rankings that disagree."""
    # An embarked unit's own model coordinates are not maintained while it
    # rides (measured: one passenger squad still sat at its deployment spot
    # 30" from its transport), so distance is taken from the TRANSPORT - which
    # is also where the unit would actually get out. Without this the whole
    # block below was simply skipped for passengers, so the planner saw no
    # targets for them at all and had no number arguing for a disembark (user:
    # "die boyz sind nicht ausgestiegen").
    # `point_radius_in` is the slack around that point the unit gets for free -
    # for a passenger, the disembark distance measured from the hull (see
    # disembark_reach_in()). Without it the gap was taken from the transport's
    # centre as if the unit had to walk out of a dot, which overstated every
    # distance by the hull radius plus 3". That reads as a small error and is
    # not: it is subtracted from BOTH sides' reach, and the side with the least
    # slack loses entries first. A Boyz mob reaches 18" (6" move plus a 12"
    # charge); a Devilfish shooting at it reaches 30". So the same few inches
    # routinely emptied the target list while leaving the threat list
    # untouched - the field showed danger and no upside, and the plan kept the
    # unit aboard.
    def gap_to(enemy):
        if at_point is None:
            return None
        return max(0.0, _point_distance_to_squad(at_point, enemy) - point_radius_in)

    threats = []
    for enemy in enemy_squads:
        if not enemy.models:
            continue
        incoming = _worst_case(enemy, squad, gap=gap_to(enemy))
        if incoming is not None and incoming[0] > 0.05:
            threats.append({
                "unit": enemy.name,
                "kills_per_turn": incoming[0],
                "fraction_of_your_unit": incoming[1],
                "via": incoming[2],
            })

    threats.sort(key=lambda t: -t["kills_per_turn"])
    # NOT capped at 1.0 any more, and named for what it is: this sums EVERY
    # enemy unit in reach as though all of them fired at this one squad, which
    # is an upper bound rather than a forecast - an opponent with eight units
    # and five targets does not concentrate everything on one. Capping it threw
    # away the only thing that made the bound usable. Measured on the reported
    # board: four of nine units read exactly 1.0, so the number no longer told
    # "grazed" from "wiped three times over", and the planner kept a Boyz mob
    # in its transport during the WAAAGH turn - the same observation showed the
    # mob would destroy 10 models a turn in melee if it got out ("die boyz sind
    # im waagh zug wieder nicht ausgestiegen"). The raw ratio (1.32 there)
    # keeps that distinction.
    total = sum(t["fraction_of_your_unit"] for t in threats)
    return {
        "worst_case_losses_per_turn_if_everything_shoots_you": round(total, 2),
        "biggest_threats_to_you": threats[:THREAT_LIST_LIMIT],
        "best_targets_for_you": ranked_targets(
            squad, enemy_squads,
            reaches=lambda enemy, melee: _reaches_this_turn(
                squad, enemy, melee, gap=gap_to(enemy)),
            # A passenger charges from where its transport stands (18.04), so
            # its charge arithmetic has to start there too - the same origin
            # every other distance for it already uses.
            charge_from=at_point,
            advance_keeps_charge=advance_keeps_charge,
        ),
    }


def damage_value(attacker, defender, melee=False, gap_in=None):
    """What a turn of `attacker`'s attacks on `defender` is WORTH, in points.

    expected_kills() answers "what share of that unit do I erase", which is the
    wrong question for choosing between targets: a specialist erases a larger
    share of a cheap screen than of the expensive thing it was built to kill,
    so ranking by share aims it at the screen. Multiplying the share by the
    target's own points turns it into value removed - the same trade arithmetic
    threat_assessment() already reports.

    Falls back to the bare fraction for an unpriced unit (a faction whose list
    has not been transcribed), so such an army still ranks sensibly among
    itself rather than scoring zero everywhere.

    `gap_in` is passed straight through to expected_wounds_against(), which
    documents when a caller may use it: only where the distance is a fact
    rather than a planning guess."""
    got = expected_kills(attacker, defender, melee=melee, gap_in=gap_in)
    if not got:
        return 0.0
    points = getattr(defender, "points", None)
    return got["fraction_of_unit"] * points if points else got["fraction_of_unit"]


def matchup_targets(squad, enemy_squads, limit=TARGET_LIST_LIMIT):
    """ranked_targets() for a unit that has no position yet - the same "what
    is this unit FOR" question with the reach gate removed and the target's
    current position added.

    A reserve unit was described to the planner by its weapon profiles alone,
    leaving it to derive from S9/AP-2/D3 that Rokkits are for Battlesuits and
    not for Kroot - the same "here are the statlines, work it out"
    arrangement that had to be replaced with a computed wound threshold once
    already. User: "der planner sollte eigentlich die rollen der einheiten
    kennen und entsprechend gegen die korrekten ziele platzieren, wenn
    möglich." The position is carried here and not in the on-board case
    because an arriving unit is PLACED by coordinate and cannot move
    afterwards, so where the target stands is the whole decision;
    _auto_ingress_squad() already honours a planned position ahead of its own
    ranking."""
    # charge_from=False: a unit still in reserve or aboard a transport has no
    # position to charge FROM, so the roll it would need is not a fact yet.
    return ranked_targets(squad, enemy_squads, limit=limit, with_position=True,
                          charge_from=False)


HAZARD_FAIL_CHANCE = 2 / 6.0  # rule 06.03: a hazard roll of 1-2 is a failure


def staying_aboard_cost(squad, transport, enemy_squads):
    """What a turn spent inside the transport costs - the half of the
    disembark decision that was never reported at all.

    "if_you_disembark" handed the planner a danger figure and a trade figure
    for getting out and NOTHING for the alternative, so staying aboard read as
    the free, safe option by default. It is neither, and the engine knows both
    reasons already:

    - Rule 18.02 puts an embarked unit off the battlefield. It deals no damage,
      holds no objective and contributes nothing for the whole turn. That cost
      is certain, and it is paid again every turn the unit waits - which is
      what "disembark next turn once in range" actually buys.
    - Rules 18.03/18.05: the transport is itself a target, and when it dies the
      passengers are forced out in an Emergency Disembark - after a hazard roll
      per model (06.03), with the whole unit destroyed outright if it cannot be
      set up within 6". Riding a threatened transport is not shelter.

    Same deliberate approximations as expected_kills(), which supplies the
    transport's own risk number here."""
    models = len(squad.models)
    if not models:
        return None

    # Measured against the unit's AVERAGE wounds per model, not the first
    # allocation group's, which is what expected_kills() uses. Mortal wounds
    # spill from one model to the next instead of being lost with the model
    # they killed, so a whole batch does not stop at the first group - reading
    # a lone 2-wound Boss Nob as the whole mob's durability halved the figure.
    total_wounds = sum(max(1, m.profile.wounds) for m in squad.models)
    wounds_each = max(1.0, total_wounds / models)
    per_failure = (MORTAL_WOUNDS_ON_FAIL_MONSTER_VEHICLE if is_monster_or_vehicle_unit(squad)
                   else MORTAL_WOUNDS_ON_FAIL)
    hazard_losses = min(models, models * HAZARD_FAIL_CHANCE * per_failure / wounds_each)

    out = {
        "you_contribute_nothing_this_turn": (
            "rule 18.02 - an embarked unit is off the battlefield: no shooting, no charge, "
            "no Objective Control, no score. Waiting a turn costs this unit's entire output."
        ),
        "models_lost_if_the_transport_dies": round(hazard_losses, 1),
        "if_the_transport_dies": (
            "rules 18.03/18.05 - the unit is forced out in an Emergency Disembark, taking a "
            "hazard roll per model first (06.03), and is destroyed outright if it cannot be "
            "set up within 6\". Staying aboard a transport under fire is not the safe option."
        ),
    }

    carrier = getattr(transport, "squad", None)
    if carrier is not None and enemy_squads:
        risk = threat_assessment(carrier, enemy_squads)
        out["transport_losses_per_turn"] = risk["worst_case_losses_per_turn_if_everything_shoots_you"]
        out["biggest_threats_to_the_transport"] = risk["biggest_threats_to_you"]
    return out


LOS_SAMPLE_POINTS = 6
# Stand-in base size for "could a unit placed on this objective see X" - a
# typical infantry base, since that is what usually ends up garrisoning one.
OBJECTIVE_PROBE_RADIUS_IN = 0.63  # coarse on purpose - see visible_enemy_units()
LOS_MAX_PROBES_PER_PAIR = 3


def visible_enemy_units(squad, enemy_squads, obstacles, terrain_areas, all_tokens):
    """Which enemy units this squad can actually SEE right now (rule 06.01
    line of sight, plus rule 13.10 obscuring terrain).

    Real gap found via user report ("der planner befiehlt immer den einheiten
    auf irgendwas zu schießen, obwohl da eine dicke wand im weg ist. darum
    schätzt der planner situationen völlig falsch ein"): the planning
    observation carried positions and, since the last fix, distances - but
    nothing about visibility. A target 10" away behind a solid ruin wall
    looked exactly like one standing in the open, so the planner kept
    ordering shots that the Shooting phase could never carry out.

    Deliberately approximate, and cheaper than the real thing: the engine's
    own target validation checks every model pair at full precision, while
    this probes only the `LOS_MAX_PROBES_PER_PAIR` own models closest to the
    enemy, each against its own nearest enemy model, at the same reduced
    `LOS_SAMPLE_POINTS` precision the tactical heuristics already use. It
    answers "is this unit worth planning a shot against at all", not "is this
    specific shot legal" - the Shooting phase still decides that, unchanged."""
    visible = []
    for enemy in enemy_squads:
        if not enemy.models:
            continue
        probes = sorted(
            squad.models,
            key=lambda m: min((m.x_in - e.x_in) ** 2 + (m.y_in - e.y_in) ** 2 for e in enemy.models),
        )[:LOS_MAX_PROBES_PER_PAIR]
        for observer in probes:
            target = min(
                enemy.models,
                key=lambda e: (observer.x_in - e.x_in) ** 2 + (observer.y_in - e.y_in) ** 2,
            )
            if line_of_sight.has_line_of_sight(
                observer, target, obstacles, all_tokens, terrain_areas, sample_points=LOS_SAMPLE_POINTS,
            ):
                visible.append(enemy.name)
                break
    return visible


class _ProbeSquad:
    """The only thing line_of_sight reads off a model's squad is `owner` (to
    skip the observer's own army) and the squad's identity (to skip its own
    unit) - a throwaway instance satisfies both: it is never identical to any
    real squad, and it carries the probing player."""
    __slots__ = ("owner",)

    def __init__(self, owner):
        self.owner = owner


class _ProbePoint:
    """Duck-typed stand-in for a Token at an arbitrary spot on the table -
    line_of_sight only ever reads x_in/y_in/radius_in (and squad, to skip the
    observer's own unit and own army), so this is enough to ask "what would a
    model standing HERE be able to see".

    `owner` matters since friendly models stopped blocking line of sight: left
    unset, a probe has no army, so the probing player's OWN models would count
    as blockers and a sightline would look blocked when the real shot from
    there would be legal."""
    __slots__ = ("x_in", "y_in", "radius_in", "squad")

    def __init__(self, x_in, y_in, radius_in, owner=None):
        self.x_in = x_in
        self.y_in = y_in
        self.radius_in = radius_in
        self.squad = _ProbeSquad(owner) if owner is not None else None


# A stand-in base size for "some enemy model will be standing there" when
# probing ground nobody occupies yet. Between an infantry base (0.63") and a
# vehicle hull (1.4"), so the answer is neither systematically optimistic nor
# pessimistic about what a wall hides.
TYPICAL_PROBE_RADIUS_IN = 0.8


def zone_visibility_from_point(x_in, y_in, radius_in, owner, zone_probe_points,
                               obstacles, terrain_areas, all_tokens):
    """How many sample points across the ENEMY deployment zone can see a model
    standing at (x, y). Lower is more hidden.

    The deployment-time counterpart of visible_enemy_units_from_point(). During
    rule 03.01's alternating deployment most of the enemy army is not on the
    board yet - the first unit down would be scored against an empty table -
    so "is this spot exposed" has to be asked of the ground the enemy WILL
    occupy, not of the handful of models already placed. The zone is fully
    known from the first frame.

    Each probe carries the enemy's `owner` so the deploying player's own
    models are not mistaken for blockers, and so the probe's own army is
    skipped (see _ProbePoint)."""
    here = _ProbePoint(x_in, y_in, radius_in, owner)
    seen = 0
    for (px, py) in zone_probe_points:
        there = _ProbePoint(px, py, TYPICAL_PROBE_RADIUS_IN, _other_owner(owner))
        if line_of_sight.has_line_of_sight(
            there, here, obstacles, all_tokens, terrain_areas, sample_points=LOS_SAMPLE_POINTS,
        ):
            seen += 1
    return seen


def _other_owner(owner):
    return "Player 2" if owner == "Player 1" else "Player 1"


def visible_enemy_units_from_point(x_in, y_in, radius_in, enemy_squads, obstacles, terrain_areas, all_tokens,
                                   owner=None):
    """Which enemy units would be visible to a model standing at (x, y).

    Real gap found via user report ("planner weist ghostkeel an sich auf das
    NE objective zu bewegen und auf die stealth suites zu schiessen. von da
    aus gibt es aber gar keine sichtlinie... Das liegt wahrscheinlich daran,
    dass der Planner nur die Sichtlinie der aktuellen Position messen kann,
    aber nicht die Sichtlinie des Zielorts, oder?") - exactly right.
    visible_enemy_units() answers "what can this unit see from where it is
    standing", which is the wrong question for an order of the form "move
    there, then shoot that": the shot is taken from the DESTINATION, and a
    wall that does not block the current position may well block that one.
    Reported twice in the same turn, for the Ghostkeel and for the Kroot.

    Same deliberate approximation as visible_enemy_units(): one probe point
    against each enemy unit's nearest model, at the reduced LOS_SAMPLE_POINTS
    precision. It answers "is a shot from there worth planning at all".

    `owner` is the player who would be standing there - pass it whenever it is
    known, so that player's own models are correctly ignored as blockers (see
    _ProbePoint)."""
    probe = _ProbePoint(x_in, y_in, radius_in, owner)
    visible = []
    for enemy in enemy_squads:
        if not enemy.models:
            continue
        target = min(enemy.models, key=lambda e: (x_in - e.x_in) ** 2 + (y_in - e.y_in) ** 2)
        if line_of_sight.has_line_of_sight(
            probe, target, obstacles, all_tokens, terrain_areas, sample_points=LOS_SAMPLE_POINTS,
        ):
            visible.append(enemy.name)
    return visible


def squad_summary(squad, in_reserve=False, embarked_in=None, include_weapons=False,
                  terrain_areas=(), turn_tracker=None, last_ranged_attack_turn=None):
    summary = {
        "name": squad.name,
        "owner": squad.owner,
        "alive_models": len(squad.models),
        "total_wounds_remaining": sum(m.current_wounds for m in squad.models),
        # Rule 14.01 sums OC over every model in the unit, so the TOTAL is
        # what decides objective control - and in an attached unit (19.01)
        # the models no longer share one OC value, so a per-model figure
        # would be both ambiguous and wrong for the only question it feeds.
        "oc": sum(m.profile.oc for m in squad.models),
    }
    # Weapons and durability for BOTH sides - a datasheet is open information,
    # and the planner was previously shown enemy units as little more than a
    # name and a wound count, which makes "hide the tank from the anti-tank
    # guns" unanswerable in principle.
    summary["ranged_weapons"] = ranged_weapon_summary(squad)
    summary["melee_weapons"] = melee_weapon_summary(squad)
    # NECRONS only: how much this unit would actually get back if its
    # Reanimation Protocols activated right now, healing and revived models
    # together. A PRE-COMPUTED number rather than raw wounds, per this repo's
    # second recurring error class - anything the model has to derive itself,
    # it derives badly, and this one needs the CHARACTER exclusion and the
    # starting-strength cap to come out right.
    #
    # Deliberately NOT a meta-level "go turn" field like waaagh: reanimation is
    # a steady per-unit trickle rather than a moment to build a plan around, so
    # it belongs on the unit. Absent entirely for a non-Necron unit, so no
    # other army pays a key for it.
    if reanimation_protocols.has_reanimation_protocols(squad):
        recoverable = reanimation_protocols.recoverable_wounds(squad)
        returnable = len(reanimation_protocols.revivable_models(squad))
        summary["reanimation_protocols"] = {
            "wounds_you_could_recover": recoverable,
            "destroyed_models_that_could_return": returnable,
            "note": (
                "at the end of your Command phase this unit heals D3 wounds; surplus "
                "healing revives destroyed models (not CHARACTERS). 0 means a roll for "
                "this unit can achieve nothing."
            ),
        }
    defence = defensive_profile(squad)
    if defence is not None:
        summary["defensive_profile"] = defence
    # Rule 24.24 (LONE OPERATIVE): this unit cannot be selected as a ranged
    # target at all unless the shooter is within X". User report: "Der Planner
    # hat dem Stealth Suit angewiesen, auf die Ghostkeel zu schiessen, aber
    # der Ghostkeel hat Lone Operative. Aus der Entfernung kann gar nicht auf
    # den geschossen werden." The engine has enforced this the whole time
    # (game/shooting.py reads lone_operative_range()); the planner was simply
    # never told, so it kept writing orders the Shooting phase had to drop.
    lone_range = status_effects.lone_operative_range(squad)
    if lone_range is not None:
        summary["lone_operative"] = (
            f"cannot be shot at from further than {lone_range:.0f}\" away (rule 24.24)"
        )

    # Rule 13.09 (Hidden): a unit sitting IN Dense terrain that has held its
    # fire cannot be targeted from beyond 15" (12" with a wall on its own
    # footprint) at all. The engine has always enforced it; the planner was
    # never told, so it could not weigh "stay hidden while we close" against
    # "shoot now" - user: "oder alternativ, wenn der Gegner noch weit weg ist,
    # die 'Stay Hidden' Mechanik zu nutzen". Reported as a whole-unit fact:
    # is_hidden() is per model, and a unit is only meaningfully hidden while
    # all of it is.
    if squad.models and turn_tracker is not None and terrain_areas:
        seen = last_ranged_attack_turn if last_ranged_attack_turn is not None else {}
        if all(status_effects.is_hidden(m, terrain_areas, turn_tracker, seen) for m in squad.models):
            summary["hidden"] = (
                "currently Hidden (rule 13.09) - cannot be targeted from beyond its detection "
                "range; firing any ranged weapon gives this up for this turn and the next"
            )


    if in_reserve:
        # A reserve squad's models still exist as Token objects (see
        # GameState.reserves), but their x_in/y_in are inert leftovers from
        # scene setup, never a real board position (see CLAUDE.md) - showing
        # them would misrepresent an off-board unit as being somewhere on
        # the battlefield. Flag it instead.
        summary["in_reserve"] = True
        # Rule 20.03: Strategic Reserves cannot arrive on battle round 1.
        # User report: "Der Planner hat dem Crisis-Team angewiesen, jetzt
        # schon zu deployen, aber es ist Zug 1. Da kann man auch nicht
        # deployen." Same shape as the Lone Operative gap above - the engine
        # rejects it (IngressController's INGRESS_MIN_BATTLE_ROUND check),
        # the planner just never knew the rule.
        summary["can_arrive_from_battle_round"] = INGRESS_MIN_BATTLE_ROUND
    elif embarked_in is not None:
        # Rule 18.02: an embarked squad is off the battlefield too - its own
        # models' coordinates are just as inert as a reserve squad's, so the
        # TRANSPORT's position is the only meaningful "where is this unit".
        # User report ("ich glaube nicht, dass sie weiß, dass im devilfish
        # breacher stecken, mit denen man sehr viel schaden austeilen
        # könnte"): embarked squads were previously omitted from the
        # observation ENTIRELY - they live in GameState.embarked_squads, not
        # GameState.tokens, so nothing that iterates tokens could ever see
        # them, and the planner had no idea the transport was carrying
        # anything at all.
        summary["embarked_in"] = embarked_in.squad.name if embarked_in.squad is not None else "a transport"
        summary["transport_position"] = {"x": round(embarked_in.x_in, 1), "y": round(embarked_in.y_in, 1)}
        summary["note"] = "inside a transport - can disembark to fight, but is doing nothing while it stays aboard"
    else:
        summary["models"] = [{"x": round(m.x_in, 1), "y": round(m.y_in, 1)} for m in squad.models]
    return summary


GARRISON_THREAT_RANGE_IN = 12.0  # an enemy this close could reach an objective next turn


def garrison_reach_needed_in(objective, objectives):
    """How far a gun standing on `objective` has to reach before it is still
    taking part in the game, in inches.

    Measured off the board rather than set as a constant: it is the distance to
    the NEAREST other objective, which is the closest ground anybody actually
    fights over. On the three maps that comes out at 17.1" (map1), 14.8" (map2)
    and 17.6" (map3), symmetrically for both players - so a 24" gun counts
    everywhere, a 12" one nowhere, and an 18" one depends on the board. A fixed
    number would have been right on all three by luck and silently wrong on the
    fourth.

    Deliberately NOT the distance to No Man's Land, which is only 3.8-5.2" from
    a home objective on these maps: a weapon that can just barely put a shot
    over the line is not a weapon that is contributing, and using that number
    would have let every 12" gun through.

    Read by game/combat_focus.py's home_garrison_rank() through its callers -
    ai/deployment_ai.py (which unit is designated to hold home when deployment
    ends) and ai/agent_driver.py (which unit the turn plan leaves there). Those
    are two phases of one decision, so they take the number from here rather
    than each measuring it."""
    best = None
    ax, ay = _objective_centre_point(objective)
    for other in objectives or ():
        if other is objective:
            continue
        bx, by = _objective_centre_point(other)
        dist = math.dist((ax, ay), (bx, by))
        if best is None or dist < best:
            best = dist
    return best


def _objective_centre_point(objective):
    """An objective's terrain area's bounding-box centre - the same point
    objective_summary() reports to the planner as its position."""
    min_x, min_y, max_x, max_y = objective.terrain_area.bounding_box
    return ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)


def objective_threat_summary(objective, tokens, player):
    """How contested an objective actually is right now: how many of
    `player`'s own squads already stand on it, and how many enemy squads are
    close enough to threaten it (12" - roughly a move plus a charge).

    Real gap found via a repeated user report ("die ki gibt der verteidigung
    des homeobjectives zu viel relevanz. es stehen teilweise 3 einheiten
    hinten und verteidigen das objective. eine einheit reicht völlig") that
    came back UNCHANGED after a purely prompt-side "do not over-garrison"
    paragraph was added - the log then still showed three squads all given
    hold orders on the same uncontested objective. Prose alone clearly
    wasn't enough, so the planner now gets the two numbers the decision
    actually turns on and a hard rule stated in terms of them."""
    own_here = set()
    enemies_near = set()
    for token in tokens:
        if token.squad is None:
            continue
        if token.squad.owner == player:
            if objective.terrain_area.overlaps_model(token):
                own_here.add(token.squad.name)
        elif objective.terrain_area.distance_to_model(token) <= GARRISON_THREAT_RANGE_IN:
            enemies_near.add(token.squad.name)
    return sorted(own_here), sorted(enemies_near)


def objective_summary(objective, tokens):
    """Rule 14.01-14.02: name/position (its terrain area's bounding-box
    center) plus who currently controls it and each present player's raw OC
    total there - everything Claude needs to judge whether an objective is
    free for the taking, worth contesting, or already lost, without having
    to re-derive any of it from squad positions itself."""
    min_x, min_y, max_x, max_y = objective.terrain_area.bounding_box
    return {
        "name": objective.name,
        "position": {"x": round((min_x + max_x) / 2, 1), "y": round((min_y + max_y) / 2, 1)},
        "controlled_by": objective.controlled_by,
        "oc_present": objective.level_of_control(tokens),
    }


def build_observation(all_squads, turn_tracker, available_actions, player, objectives=None, plan_context=None):
    """Compact, JSON-ready summary handed to Agent.decide() - meta (round/
    phase/whose decision this is), every squad on the battlefield (both
    players), every mission objective (if given), and the enumerated legal
    actions for the ONE pending decision ai/agent_driver.py has identified.
    Terrain itself is still deliberately omitted (see CLAUDE.md) - the
    engine enforces terrain legality regardless of whether the agent
    reasons about it; objectives are a mission-scoring concept, not a
    terrain-legality one, which is why they're included here.

    plan_context (only ever passed by _handle_movement()'s own _choose()
    call, see its docstring - every other call site leaves this at the
    default None, so it's simply absent from their observations): the
    strategic planning phase's (ai/claude_agent.py's plan_turn()) result for
    THIS ONE squad - {"turn_intent": ..., "role": ..., "target": ...,
    "reason": ...} - surfaced as a "turn_plan" key. Advisory context only,
    see ai/claude_agent.py's SYSTEM_PROMPT."""
    all_squads = sorted(all_squads, key=lambda s: s.name)
    tokens = [m for s in all_squads for m in s.models]
    observation = {
        "meta": {
            "battle_round": turn_tracker.battle_round,
            "phase": turn_tracker.phase,
            "player": player,
        },
        "squads": [squad_summary(s) for s in all_squads],
        "objectives": [objective_summary(o, tokens) for o in objectives] if objectives else [],
        "available_actions": available_actions,
    }
    if plan_context is not None:
        observation["turn_plan"] = plan_context
    return observation


def _squad_distance(squad, other):
    return min(
        ((a.x_in - b.x_in) ** 2 + (a.y_in - b.y_in) ** 2) ** 0.5 - a.radius_in - b.radius_in
        for a in squad.models for b in other.models
    )


def _objective_distance(squad, objective):
    return min(objective.terrain_area.distance_to_model(m) for m in squad.models)


COVERED_SPOT_ANGLES = 12
COVERED_SPOT_FRACTIONS = (1.0, 0.6)
COVERED_SPOT_LIMIT = 4
# A staging spot has to GAIN ground. Offering the backwards ones and trusting the
# reader to notice the minus sign does not work: measured on the reported turn, the
# planner took (10,10) for the Stormboyz and (36,9) for the Warbikers - both behind
# their own deployment line - and described them as "move up now" and "Advance
# toward No Man's Land". A forward spot (+6.7") existed for the Warbikers in the
# same list and was passed over. The engine must therefore not offer what it does
# not want chosen; an empty list is the honest answer and means "advance in the
# open or hold", which the plan then has to decide and justify.
# A staging spot has to bank a real share of the unit's move, not a token inch.
# Reported (logs/game_20260819_222130.log) and reproduced exactly: the 20-strong
# mob was offered ONE spot, at (3.8,9.5), worth 1.00" of ground and 3.2"
# SIDEWAYS - 17% of its 6" move. The plan took it, described it as advancing,
# and the mob crabbed across the board. Worse, the spot was close enough that a
# Normal move reached it, which suppresses the Advance option entirely
# (_advance_is_worth_offering) - so the same token spot also cost the unit its
# run. A flat inch is not a threshold on a board where units move 5" to 12".
# The complaint was never "too few inches", it was DIRECTION: "anstatt nach
# vorne zu stürmen und zu chargen sind sie eher zur seite und teilweise
# zurückgegangen". So the test is on direction, with only a modest floor on
# size. Measured on the reported board, over every spot that genuinely hides
# the unit:
#
#   flat 1" (the original)   4 spots, and 3 of the 4 move further SIDEWAYS
#                            than forward - the reported failure
#   half the unit's move     0 spots - it also throws away the good ones
#                            (Meganobz +47% and Deff Dread +40% of their move
#                            both miss a 50% bar by a hair)
#   forward > sideways       1 spot, none of them sideways
#
# i.e. the direction rule keeps the good spot and drops exactly the bad ones,
# which neither magnitude threshold manages.
MIN_STAGING_ADVANCE_FRACTION = 0.25
MIN_STAGING_ADVANCE_IN = 1.0  # floor, for a unit slow enough that a quarter of its move is less
# Where a shooter might stand after its own move, as offsets from the straight
# line toward the spot it wants to see. A gunner walks AROUND a wall rather than
# into it, so testing only the direct approach misses most of the danger.
COVERED_SPOT_ENEMY_ARCS_DEG = (0.0, 60.0, -60.0, 120.0, -120.0, 180.0)


def _could_shoot_point(enemy, x_in, y_in):
    """Could this enemy unit put a shot on (x, y) at all this turn, move
    included? Pure arithmetic, run before any line-of-sight probe so that
    distant units cost nothing."""
    if not enemy.models:
        return False
    ranges = [w.range_in for w in _all_weapons(enemy)
              if getattr(w, "weapon_type", None) == "ranged"]
    if not ranges:
        return False
    gap = min(math.hypot(m.x_in - x_in, m.y_in - y_in) - m.radius_in for m in enemy.models)
    return gap - min_model_movement(enemy) <= max(ranges)


# How many points around the edge of a unit's footprint are probed in addition
# to its centre. A unit does not stand on the spot it was promised - it stands
# AROUND it - and the model that gets seen is always one on the enemy-facing
# edge, so the ring is what decides.
FOOTPRINT_PROBE_ARCS_DEG = (0.0, 60.0, -60.0, 120.0, -120.0, 180.0)


def _is_an_advance(progress_in, sideways_in):
    """Does this spot take the unit FORWARD, or just across the front?

    Named rather than inlined because it is the whole of the reported
    complaint - "anstatt nach vorne zu stürmen und zu chargen sind sie eher zur
    seite und teilweise zurückgegangen" - and because a magnitude threshold
    cannot express it: measured over every spot that genuinely hid a unit on
    the reported board, a flat inch let through 4 spots of which 3 moved
    further sideways than forward, while half-a-move let through none at all,
    including two that were 40-47% forward."""
    return progress_in > sideways_in


def _footprint_probes(x_in, y_in, radius_in, footprint_in, toward_x, toward_y):
    """The points to test for a unit that will occupy a disc of `footprint_in`
    around (x, y), enemy-facing first so a visible spot is rejected on the
    first call rather than the last.

    Probing only the centre is what made staging a false promise. Measured on
    map 2 after the unit actually walked to the spot its own staging list
    called hidden: Beast Snagga + Beastboss 10 of 11 models in line of sight,
    Gretchin 9 of 11, and only the single-model Deff Dread got what it was
    told - because a one-model unit IS the point that was tested."""
    if footprint_in <= 0.05:
        return [(x_in, y_in)]
    heading = math.atan2(toward_y - y_in, toward_x - x_in)
    points = [(x_in, y_in)]
    for arc in FOOTPRINT_PROBE_ARCS_DEG:
        angle = heading + math.radians(arc)
        points.append((x_in + footprint_in * math.cos(angle),
                       y_in + footprint_in * math.sin(angle)))
    return points


def _spot_stays_hidden(x_in, y_in, radius_in, enemy, obstacles, terrain_areas, all_tokens,
                       board_w_in, board_h_in, footprint_in=0.0):
    """Is a unit standing at (x, y) hidden from this enemy even after it moves?

    The distinction that makes this function necessary (user: "berücksichtigt
    die auch, dass ich meine einheiten noch bewegen kann, bevor ich schieße?"):
    cover measured against where the enemy stands RIGHT NOW is cover that lasts
    until they walk around the wall. Measured on the reported case, all four
    spots offered to the planner were hidden from current positions and visible
    after enemy movement - one of them to five separate units. Offering those as
    cover is worse than offering nothing, because it invites the plan to be
    confident about a spot that gets the unit shot to pieces."""
    origins = min(enemy.models, key=lambda m: (m.x_in - x_in) ** 2 + (m.y_in - y_in) ** 2)
    probes = [_ProbePoint(px, py, radius_in) for px, py in
              _footprint_probes(x_in, y_in, radius_in, footprint_in, origins.x_in, origins.y_in)]
    if any(line_of_sight.has_line_of_sight(
        origins, probe, obstacles, all_tokens, terrain_areas, sample_points=LOS_SAMPLE_POINTS,
    ) for probe in probes):
        return False
    move = effective_movement_in(origins)  # not the printed value - see game/coldstar.py
    if move <= 0:
        return True
    toward = math.atan2(y_in - origins.y_in, x_in - origins.x_in)
    for arc in COVERED_SPOT_ENEMY_ARCS_DEG:
        angle = toward + math.radians(arc)
        nx = origins.x_in + move * math.cos(angle)
        ny = origins.y_in + move * math.sin(angle)
        if not (0 < nx < board_w_in and 0 < ny < board_h_in):
            continue
        # owner=enemy.owner: this probe stands in for one of THEIR models, so
        # their own army must be ignored as blockers just like it would be for
        # the real model (see _ProbePoint).
        shooter = _ProbePoint(nx, ny, origins.radius_in, enemy.owner)
        if any(line_of_sight.has_line_of_sight(
            shooter, probe, obstacles, all_tokens, terrain_areas,
            sample_points=LOS_SAMPLE_POINTS,
        ) for probe in probes):
            return False
    return True


def staging_positions(squad, enemy_squads, obstacles, terrain_areas, all_tokens, goal=None,
                      board_w_in=None, board_h_in=None):
    """Where this unit can STAGE: spots inside its move that stay safe after the
    enemy moves too, ranked by how much ground they gain.

    Staging is the answer this observation was missing, and the user named it
    after the same unit walked into the open for the sixth time ("die echte
    lösung im spiel ist stagen. es muss doch möglich sein, der ki stagen
    beizubringen, wenn keine vernünftigen ziele in reichweite sind"). The first
    version of this function only reported spots that GAINED ground, on the
    reasoning that cover which costs ground is a retreat. That deleted the
    staging answer outright: when every safe spot lies level with or behind the
    unit, an empty list leaves the plan with nothing but "advance into the kill
    zone", which is exactly what kept happening. Progress is therefore reported
    rather than required - the plan can see the trade and justify it.

    The third instance of one failure shape, so worth stating plainly: every
    number the planner SELECTS from is pre-evaluated for it, and every number it
    INVENTS is not. Enemy units and objectives carry "turns_to_reach"; objectives
    carry "enemy_units_visible_from_here". A position_x/position_y the planner
    makes up carries neither, because it does not exist until the planner writes
    it - so "is that spot exposed?" was left to the model, with only a prompt
    paragraph telling it to prefer cover, and no way to check.

    Measured on the reported case (user: "und stormboyz wieder im freien"): the
    execution was correct - ordered to (15,25), arrived within 2.5" - but of 114
    reachable spots, 86 were hidden from EVERY enemy, several of them making
    +7-8" progress toward the same goal. Cover was abundant and free, and the
    plan could not see it.

    Approximate in the same way visible_enemy_units_from_point() is (one probe
    point per enemy unit, reduced sample precision): it answers "is this spot
    worth naming", not "is this spot legal" - the movement code still decides
    that. Ranked by progress toward `goal` so cover never means retreating."""
    if not squad.models:
        return []
    # Read from config rather than defaulted to a board size, because the
    # planner's own call does not pass them: with map 1's 44x60 hardcoded here,
    # map 2 (60x44) had its staging spots clipped in x and map 3 (30x30) was
    # offered spots off the board entirely.
    if board_w_in is None:
        board_w_in = config.BOARD_WIDTH_IN
    if board_h_in is None:
        board_h_in = config.BOARD_HEIGHT_IN
    cx = sum(m.x_in for m in squad.models) / len(squad.models)
    cy = sum(m.y_in for m in squad.models) / len(squad.models)
    reach = min_model_movement(squad)
    radius = max_model_radius(squad)
    # How much ground the unit covers at the spot - measured on the footprint
    # it can SQUEEZE INTO, not the one it is sprawled across right now, because
    # taking cover is exactly when a unit compresses. Judged on the live sprawl
    # instead, all fourteen units on map 2 were left with no cover at all. The
    # move that goes there has to actually pack it, or this is a promise again
    # rather than a measurement - see _stage_toward() in ai/agent_driver.py.
    footprint = formation_layout.packed_radius(squad)
    live_foes = [e for e in enemy_squads if e.models]
    if not live_foes:
        return []
    base = math.hypot(goal[0] - cx, goal[1] - cy) if goal else 0.0
    # Applied whether or not a goal was given. Without a goal `progress` is the
    # raw distance in ANY direction, so the old "only filter when there is a
    # goal" left a spot BEHIND the unit reporting positive progress.
    min_progress = max(MIN_STAGING_ADVANCE_IN, reach * MIN_STAGING_ADVANCE_FRACTION)

    found = []
    for i in range(COVERED_SPOT_ANGLES):
        angle = 2.0 * math.pi * i / COVERED_SPOT_ANGLES
        for fraction in COVERED_SPOT_FRACTIONS:
            distance = reach * fraction
            x = cx + distance * math.cos(angle)
            y = cy + distance * math.sin(angle)
            if not (radius < x < board_w_in - radius and radius < y < board_h_in - radius):
                continue
            # Only units that could actually land a shot there are worth a
            # line-of-sight probe; the arithmetic gate keeps the sweep affordable.
            shooters = [e for e in live_foes if _could_shoot_point(e, x, y)]
            if any(
                not _spot_stays_hidden(x, y, radius, e, obstacles, terrain_areas, all_tokens,
                                       board_w_in, board_h_in, footprint_in=footprint)
                for e in shooters
            ):
                continue
            progress = base - math.hypot(goal[0] - x, goal[1] - y) if goal else distance
            if progress < min_progress:
                continue
            # ...and it has to be an ADVANCE, not a shuffle across the front.
            if goal is not None and base > 1e-9:
                ux, uy = (goal[0] - cx) / base, (goal[1] - cy) / base
                if not _is_an_advance(progress, abs(-uy * (x - cx) + ux * (y - cy))):
                    continue
            found.append((-progress, {"x": round(x, 1), "y": round(y, 1),
                                      "progress_toward_your_goal_in": round(progress, 1),
                                      "stays_hidden_even_if_they_advance": True,
                                      "charge_risk_here": combined_charge_chance(
                                          charge_threats(squad, live_foes, at_point=(x, y)))}))
    found.sort(key=lambda item: item[0])
    return [spot for _rank, spot in found[:COVERED_SPOT_LIMIT]]


def _passenger_gap(from_point, reach_bonus_in, measure_to):
    """Distance from a passenger's real starting point to `measure_to`.

    A passenger's own model coordinates are not maintained while it rides, so
    every distance for it is taken from the TRANSPORT, less the distance it
    gets for free stepping out of the hull (rule 18.04 - see
    disembark_reach_in()). Same origin threat_assessment() already uses for
    passengers, on purpose: two fields answering "how far is that" from two
    different points is how a plan ends up arguing with itself."""
    return max(0.0, measure_to(from_point) - reach_bonus_in)


def add_planning_distances(summary, squad, enemy_squads, objectives, obstacles=(), terrain_areas=(), all_tokens=(),
                           from_point=None, reach_bonus_in=0.0, advance_keeps_charge=False):
    """Attach precomputed distances (and the unit's Move characteristic) to
    one of the planner's OWN squads.

    `from_point`/`reach_bonus_in` re-base every distance on a point that is
    not where the squad's models currently stand - passed for an EMBARKED
    squad, whose distances have to be measured from its transport plus the
    disembark reach.

    Real, severe bug found from the reported log: a passenger got NONE of
    this. It had `if_you_disembark.best_targets_for_you` listing three enemy
    units it would wipe entirely in melee, and no `move_inches_per_turn`, no
    `distance_to_enemy_units`, no `reachable_this_turn`, no
    `enemy_units_you_can_see` - because this function only ever ran for
    on-board squads. The planner is told throughout its prompt to check reach
    before ordering anything, so with the reach fields simply absent it
    concluded the unit could not reach anything, and wrote exactly that:
    "2 Boyz 2 + Warboss: stay_embarked (No target within charge/shoot range
    this turn from Trukk 2's position)" - three turns running, on a board
    where the same observation said the unit destroyed 100% of three separate
    enemy units if it got out. The user's verdict was blunt and correct
    ("totaler quatsch sie hatten viele ziele und hätten aktiv werden
    müssen"). Same failure shape as every other one in this file's history:
    the engine knew, the observation did not say.

    Real gap found via user report ("in zug 1 hat der thinking layer einen
    angriff der kroot auf mein stealth team angeordnet, obwohl es noch
    meilenweit entfernt war. kann der überhaupt entfernungen abschätzen?" -
    plus the follow-up suspicion that it confuses one objective for
    another): no, it could not. The observation gave raw (x, y) coordinates
    only, so judging "can this squad reach that unit this turn" meant doing
    Euclidean distance in its head for every pair - exactly the kind of
    arithmetic a language model is unreliable at, and the reason it ordered
    attacks on units that were nowhere near. Handing it the distances
    directly, next to the unit's own movement range, turns that from a
    calculation into a comparison."""
    summary["move_inches_per_turn"] = min_model_movement(squad) if squad.models else 0
    embarked = from_point is not None
    if squad.models:
        # Where this unit can actually get to this turn, as a circle it can be
        # compared against directly. Every other distance in this observation is
        # pre-computed with a "turns_to_reach" precisely because the planner is
        # unreliable at deriving reach from coordinates - but a position it
        # invents itself (position_x/position_y) cannot carry that, so it was
        # the one place still asking for the arithmetic. It answered wrong:
        # Stormboyz with a 12" move were ordered to a point 17" away and ended
        # the turn stranded halfway across open ground.
        if embarked:
            cx, cy = from_point
        else:
            cx = sum(m.x_in for m in squad.models) / len(squad.models)
            cy = sum(m.y_in for m in squad.models) / len(squad.models)
        summary["reachable_this_turn"] = {
            "from": {"x": round(cx, 1), "y": round(cy, 1)},
            "radius_in": round(summary["move_inches_per_turn"] + reach_bonus_in, 1),
            "note": (
                "a position_x/position_y you name must lie inside this circle to be reached this turn"
                + (" - measured from your transport, which is where you would step out" if embarked else "")
            ),
            # The SECOND legal distance this unit has, rule 09.06. Without it
            # stated here the Advance was unreachable by construction: this
            # circle is what the planner is told it may ask for, the plan
            # validator clamps anything outside it back in, and the tactical
            # layer only offers an Advance when the commanded point is further
            # than a plain move - so a plan that never asked for more than M
            # guaranteed the Advance option was never built. Measured on the
            # reported WAAAGH! turn: six units ordered to "advance", one
            # Advance option offered.
            "if_you_advance": {
                "radius_in": round(advance_reach_in(squad) + reach_bonus_in, 1),
                "note": (
                    "naming a position between the two radii means this unit Advances (rule 09.06) to reach it"
                    + (" - and WAAAGH! is active, so that costs it only non-Assault shooting, NOT its charge"
                       if advance_keeps_charge else
                       " - which costs it non-Assault shooting AND its charge this turn")
                ),
            },
        }
        # Concrete spots in that circle that no enemy can see, so "take cover"
        # is something to pick rather than something to estimate. Ranked toward
        # the nearest enemy, because a covered spot behind the unit is not an
        # improvement - the point is to advance under cover, not to hide.
        # Staging spots are computed from the squad's real model positions, so
        # they mean nothing for a passenger (whose models are not where they
        # appear to be) and are skipped for one - it is not choosing a spot to
        # advance to, it is choosing whether to get out at all.
        if not embarked:
            nearest_foe = min(
                (e for e in enemy_squads if e.models),
                key=lambda e: _squad_distance(squad, e), default=None,
            )
            goal = None
            if nearest_foe is not None:
                goal = (sum(m.x_in for m in nearest_foe.models) / len(nearest_foe.models),
                        sum(m.y_in for m in nearest_foe.models) / len(nearest_foe.models))
            spots = staging_positions(
                squad, enemy_squads, obstacles, terrain_areas, all_tokens, goal=goal,
            )
            if spots:
                summary["staging_positions_you_can_reach"] = spots
    if enemy_squads:
        summary["distance_to_enemy_units"] = {
            e.name: _reach_summary(
                _passenger_gap(from_point, reach_bonus_in, lambda p, s=e: _point_distance_to_squad(p, s))
                if embarked else _squad_distance(squad, e),
                summary["move_inches_per_turn"],
            )
            for e in enemy_squads if e.models
        }
    if objectives:
        # Distance AND how many of this unit's turns it costs. The planner
        # kept handing out goals three or four turns away as if they were this
        # turn's job (user: "der Planner hat dem Devilfish angewiesen, auf das
        # Objective NE zu fliegen, aber das ist doch am ganz anderen Ende der
        # Map... Der Devilfish braeuchte ungefaehr drei Runden, um dort
        # anzukommen"). Dividing distance by movement is exactly the kind of
        # arithmetic to do here rather than hope for - same reasoning as the
        # raw distances themselves, one step further.
        summary["distance_to_objectives"] = {
            o.name: _reach_summary(
                _passenger_gap(from_point, reach_bonus_in,
                               lambda p, ob=o: ob.terrain_area.distance_to_point(p[0], p[1]))
                if embarked else _objective_distance(squad, o),
                summary["move_inches_per_turn"],
            )
            for o in objectives
        }
    if enemy_squads:
        # Which of those enemies this unit can actually SEE - a distance
        # alone says nothing about whether a wall is in the way (see
        # visible_enemy_units()).
        summary["enemy_units_you_can_see"] = (
            visible_enemy_units_from_point(
                from_point[0], from_point[1], max_model_radius(squad), enemy_squads,
                obstacles, terrain_areas, all_tokens, owner=squad.owner,
            )
            if embarked else
            visible_enemy_units(squad, enemy_squads, obstacles, terrain_areas, all_tokens)
        )
        # The rest is measured at the squad's own models, which a passenger
        # does not have a meaningful position for - and for a passenger both
        # questions are already answered, from the transport, by the
        # if_you_disembark/if_you_stay_aboard pair its caller attaches.
        if not embarked:
            # Who can reach this unit in melee next turn (see charge_threats()) -
            # the number that decides whether standing here is affordable.
            threats = charge_threats(squad, enemy_squads)
            if threats:
                summary["can_be_charged_next_turn_by"] = threats
            # Both directions of the exchange, gated by what can actually reach -
            # see threat_assessment().
            summary["threat_assessment"] = threat_assessment(
                squad, enemy_squads, advance_keeps_charge=advance_keeps_charge)
    return summary


def _reach_summary(distance_in, move_in):
    """How far away something is, in inches AND in this unit's own turns."""
    turns = 1 if move_in <= 0 else max(1, math.ceil(distance_in / move_in))
    return {"inches": round(distance_in, 1), "turns_to_reach": turns}


def terrain_summary(terrain_areas):
    """The significant terrain, so the planner can point a squad AT a piece of
    it. Without this the plan could only ever name units and objectives -
    everything else on the table was invisible to it, which is why an order
    like "get behind that wall" was impossible to express (user: "es kann sehr
    schwer sein, genau zu beschreiben, wo sich diese Mauer denn befindet").

    Reported as one entry per terrain AREA rather than per obstacle: the demo
    board has ~85 individual features but only a dozen or so meaningful
    pieces, and a bounding box plus category is what a "move behind it"
    decision actually needs. Pair it with the position_x/position_y fields on
    each unit plan to turn "behind the ruin at (22, 30)" into a real order."""
    summary = []
    for area in terrain_areas:
        if not getattr(area, "features", None):
            continue
        min_x, min_y, max_x, max_y = area.bounding_box
        # The category lives on the individual features, not on the area, and
        # it is the whole point of the entry: DENSE blocks sight and movement
        # (so it is what you hide BEHIND), LIGHT only gives cover. Reporting a
        # flat "terrain" for everything would leave the planner unable to tell
        # a sight-blocking ruin from an open crater.
        summary.append({
            "category": "dense" if area.has_dense_feature else (
                "light" if area.is_obscuring else "exposed"
            ),
            "blocks_line_of_sight": bool(area.has_dense_feature),
            "center": {"x": round((min_x + max_x) / 2, 1), "y": round((min_y + max_y) / 2, 1)},
            "size": {"width": round(max_x - min_x, 1), "height": round(max_y - min_y, 1)},
        })
    return summary


def _score_summary(mission_controller, player, turn_tracker):
    """Who is winning, and by how much.

    User request: "er braucht zum Beispiel auch die Informationen, wie gerade
    der Punktestand ist". It changes the whole risk calculation - a lead worth
    protecting argues for holding what you have, a deficit argues for taking
    chances - and the planner had no idea of it.

    Includes how much game is left, which is the other half of the same
    judgement: a battle lasts BATTLE_ROUNDS (5) rounds, so "one scoring turn
    left and three VP behind" and "three turns left and level" call for
    completely different risks. TurnTracker keeps no limit of its own -
    missions define game length - so the constant lives in game/missions.py."""
    if mission_controller is None:
        return None
    opponent = next((p for p in mission_controller.primary_points if p != player), None)
    mine = mission_controller.total_points(player)
    theirs = mission_controller.total_points(opponent) if opponent else 0
    lead = mine - theirs
    if lead > 0:
        standing = f"you lead by {lead} VP"
    elif lead < 0:
        standing = f"you trail by {-lead} VP"
    else:
        standing = "level"
    left = max(0, BATTLE_ROUNDS - turn_tracker.battle_round) if turn_tracker else None
    return {
        "your_vp": mine,
        "enemy_vp": theirs,
        "standing": standing,
        "your_primary": mission_controller.primary_points.get(player, 0),
        "your_secondary": mission_controller.secondary_points.get(player, 0),
        "battle_rounds_total": BATTLE_ROUNDS,
        "your_scoring_turns_left": (left + 1) if left is not None else None,
        "note": (
            "Primary scores 3 VP per objective you control at the start of each of your own "
            "Command phases, so a lead compounds every round you keep ground - and ground given "
            "up now costs VP every round from here on."
        ),
    }


def waaagh_summary(player, waaagh_controller):
    """Is this the army's WAAAGH! turn - the one turn it is strongest?

    The single most consequential fact the planner was never told. WAAAGH! gives
    the whole army a 5+ invulnerable save, +1 melee Strength, +1 Attack, and lets
    units Advance and still charge - so it is the turn to commit everything. Only
    the TACTICAL layer knew, and only indirectly, because an Advance option's own
    description mentions it. The planner, which decides roles, disembarks and
    charge targets, wrote its plan as if it were an ordinary turn (user: "es ist
    ihr waagh zug. in diesem zug sind sie extrem stark. das war ihr go turn. und
    die boyz sind nicht ausgestiegen und die bikes haben nicht angegriffen").

    Same failure shape as every other gap this project has found: the engine knew,
    the observation did not report it."""
    if waaagh_controller is None:
        return None
    if player in getattr(waaagh_controller, "active_players", ()):
        return {
            "active_now": True,
            "effects": ("your whole army has a 5+ invulnerable save, +1 melee Strength, +1 Attack, "
                        "and may Advance and still charge this turn"),
            "note": "this is your strongest turn of the game - commit now rather than positioning for later",
        }
    if player in getattr(waaagh_controller, "used_players", ()):
        return {"active_now": False, "note": "your WAAAGH! is already spent and will not come again"}
    return {"active_now": False, "note": "your WAAAGH! is still available for a later turn"}


def build_planning_observation(on_board_squads, reserve_squads, turn_tracker, player, objectives=None,
                               embarked_squads=None, obstacles=(), terrain_areas=(),
                               last_ranged_attack_turn=None, mission_controller=None,
                               waaagh_controller=None):
    """JSON-ready summary handed to Agent.plan_turn() - same meta/squads/
    objectives shape as build_observation(), but no available_actions (this
    isn't a choose_action-style enumerated choice, see ai/base.py's
    plan_turn() docstring). Includes reserve squads (in_reserve=True, no
    position) alongside on-board ones, since the plan's "reserve_commit"
    role needs to be able to name them.

    `on_board_squads` is EVERY squad on the battlefield, both players' - the
    planner can only name an enemy unit as a target if it can see that the
    unit exists (each entry carries `owner`, so the two sides are
    distinguishable). `reserve_squads` stays the player's OWN reserves only:
    the opponent's off-board reserves are hidden information. See
    ai/agent_driver.py's _maybe_generate_turn_plan() for the bug this
    docstring line exists to prevent recurring."""
    on_board_squads = sorted(on_board_squads, key=lambda s: s.name)
    reserve_squads = sorted(reserve_squads, key=lambda s: s.name)
    embarked_squads = sorted(embarked_squads or [], key=lambda s: s.name)
    tokens = [m for s in on_board_squads for m in s.models]
    enemy_squads = [s for s in on_board_squads if s.owner != player and s.models]

    squads = []
    for s in on_board_squads:
        summary = squad_summary(
            s, include_weapons=s.owner == player, terrain_areas=terrain_areas,
            turn_tracker=turn_tracker, last_ranged_attack_turn=last_ranged_attack_turn,
        )
        if s.owner == player and s.models:
            add_planning_distances(
                summary, s, enemy_squads, objectives,
                obstacles=obstacles, terrain_areas=terrain_areas, all_tokens=tokens,
                advance_keeps_charge=squad_waaagh_active(s, waaagh_controller),
            )
        squads.append(summary)
    for s in reserve_squads:
        summary = squad_summary(s, in_reserve=True, include_weapons=True)
        # What this unit is FOR, as a number. A reserve unit has no position
        # yet, so threat_assessment()'s "can it reach this turn" gating has
        # nothing to gate on - but the matchup question is answerable without a
        # position, and it is the one that decides where the unit should drop.
        # See matchup_targets() for the report this closes.
        if s.models and enemy_squads:
            summary["best_targets_when_you_arrive"] = matchup_targets(s, enemy_squads)
        squads.append(summary)
    for s in embarked_squads:
        summary = squad_summary(s, embarked_in=s.embarked_in, include_weapons=True)
        # What getting out would be WORTH. Passengers used to be described only as
        # "embarked, can do nothing while aboard" - no threat numbers at all,
        # because add_planning_distances() (which attaches threat_assessment) only
        # runs for on-board squads. So the planner had nothing arguing for a
        # disembark and nothing arguing against one, and reliably left melee units
        # sitting in their transport with an exposed enemy in front of them (user:
        # "die boyz sind nicht ausgestiegen ... wenn man in dieser situation keinen
        # schaden anrichtet, dann verlieren sie zu 100%"). Measured from the
        # TRANSPORT, which is where they would step out - see threat_assessment()'s
        # at_point for why the passengers' own coordinates cannot be trusted.
        transport = s.embarked_in
        if s.models and transport is not None:
            # The same distance/reach block an on-board squad gets, re-based on
            # the transport plus the disembark reach. Without it a passenger had
            # no reach fields at all, and the planner - told everywhere to check
            # reach before ordering - read that absence as "cannot reach
            # anything" and left melee units aboard for whole turns while the
            # same observation said they would wipe three enemy units if they
            # got out. See add_planning_distances()'s own docstring.
            add_planning_distances(
                summary, s, enemy_squads, objectives,
                obstacles=obstacles, terrain_areas=terrain_areas, all_tokens=tokens,
                from_point=(transport.x_in, transport.y_in),
                reach_bonus_in=disembark_reach_in(transport),
                advance_keeps_charge=squad_waaagh_active(s, waaagh_controller),
            )
        if s.models and enemy_squads and transport is not None:
            assessment = threat_assessment(
                s, enemy_squads, at_point=(transport.x_in, transport.y_in),
                point_radius_in=disembark_reach_in(transport),
                advance_keeps_charge=squad_waaagh_active(s, waaagh_controller),
            )
            # "if you stay" means the OPPOSITE thing here. For a unit on the
            # board it reads "if you stand where you are"; nested under
            # "if_you_disembark" for a passenger, the decision being weighed is
            # whether to stay ABOARD - so a key literally saying "if you stay"
            # attached the cost of standing in the open to the choice of not
            # getting out at all. Renamed for this context only.
            assessment["worst_case_losses_per_turn_if_you_stand_there"] = assessment.pop(
                "worst_case_losses_per_turn_if_everything_shoots_you"
            )
            summary["if_you_disembark"] = assessment
            summary["if_you_stay_aboard"] = staying_aboard_cost(s, transport, enemy_squads)
        squads.append(summary)

    return {
        "meta": {
            "battle_round": turn_tracker.battle_round,
            "phase": turn_tracker.phase,
            "player": player,
            "score": _score_summary(mission_controller, player, turn_tracker),
            "waaagh": waaagh_summary(player, waaagh_controller),
            "note": (
                f"You are {player}. An objective's name is only a label for where it sits on the board - "
                "a name mentioning a player does NOT mean that player owns it. Read controlled_by for "
                "that. Every objective scores the same 3 VP for whoever controls it, and any of them can "
                "be held by either side."
            ),
        },
        "squads": squads,
        "terrain": terrain_summary(terrain_areas),
        "objectives": [
            _planning_objective_summary(o, tokens, player, enemy_squads, obstacles, terrain_areas)
            for o in objectives
        ] if objectives else [],
    }


def _planning_objective_summary(objective, tokens, player, enemy_squads=(), obstacles=(), terrain_areas=()):
    """objective_summary() plus the two garrison numbers the planner needs to
    avoid parking three squads on an uncontested objective (see
    objective_threat_summary()), plus what a unit standing HERE could shoot.

    That last field is what makes an order like "move onto this objective and
    shoot X" checkable before it is written: line of sight is a property of
    the firing position, so the planner needs the destination's view, not
    just the mover's current one (see visible_enemy_units_from_point())."""
    summary = objective_summary(objective, tokens)
    own_here, enemies_near = objective_threat_summary(objective, tokens, player)
    summary["your_units_here"] = own_here
    summary["enemy_units_within_12in"] = enemies_near
    if enemy_squads:
        # An objective is a terrain AREA, so probe from its centre - the same
        # point objective_summary() already reports as its "position".
        min_x, min_y, max_x, max_y = objective.terrain_area.bounding_box
        summary["enemy_units_visible_from_here"] = visible_enemy_units_from_point(
            (min_x + max_x) / 2.0, (min_y + max_y) / 2.0, OBJECTIVE_PROBE_RADIUS_IN,
            enemy_squads, obstacles, terrain_areas, tokens, owner=player,
        )
    return summary
