from game.dice_notation import D3, D6, describe

#: A sentinel keyword for the NEGATED form of [ANTI-X], which no ordinary
#: keyword entry can express: the Stonesinger prints "ANTI-non-MONSTER/VEHICLE
#: 3+" and "...2+". Written as a keyword so it flows through the existing
#: (keyword, threshold) machinery and the "best threshold wins" fold unchanged;
#: game/shooting.py's _unit_has_keyword() is the one place that knows it means
#: "the complement of is_monster_or_vehicle_unit()".
NON_MONSTER_VEHICLE = "NON-MONSTER/VEHICLE"

RANGED = "ranged"
MELEE = "melee"


class WeaponProfile:
    """Base weapon profile. WS/BS come from the wielding model's own
    UnitProfile (weapon_skill/ballistic_skill) - real datasheets show them
    redundantly on every weapon row, but they're not weapon-specific stats,
    so we don't duplicate them here."""

    name = "Weapon"
    weapon_type = RANGED
    range_in = 24
    attacks = 1
    attacks_notation = None  # game/dice_notation.py's DiceNotation, e.g. D6() for a printed "D6" Attacks characteristic - None means `attacks` above is a real fixed value, used as-is. When set, `attacks` is only a preview/leftover value - the ACTUAL attack count is rolled for real, once per attacking model, before the Hit roll can even start (see ShootingController._begin_resolution()'s attacks_notation branch)
    ballistic_skill = None  # optional per-weapon BS override (rare - e.g. Strike Team's Support Turret/Twin Pulse Carbine/Missile Pod each print their own, worse BS than their wielder's) - None means "use the shooting model's own BS", true of every weapon so far except those; see shooting.py's effective_ballistic_skill()
    weapon_skill = None  # optional per-weapon WS override (rare, melee-only - e.g. Power Klaw prints its own, worse WS than its wielder's) - None means "use the fighting model's own WS", true of every melee weapon so far except those; see fight.py's effective_weapon_skill()
    overcharge_profile = None  # optional WeaponProfile CLASS: this weapon's alternate high-power firing mode, chosen at the point of shooting rather than a wargear swap (real 40k examples: an Ion weapon's Overcharge, a Plasma weapon's Supercharge) - e.g. CyclicIonRakerStandardProfile.overcharge_profile = CyclicIonRakerOverchargeProfile. None means this weapon has only one mode. See shooting.py's ShootingController.weapon_eligibility()/choose_weapon(overcharge=...).
    overcharge_of_id = None  # set on an INSTANCE (never a class) when shooting.py builds an alternate-firing-mode copy: id() of the real weapon in model.weapons that copy stands for. Only rule 24.26's [ONE SHOT] ledger needs it - that ledger is keyed by weapon instance, and a freshly built mode copy would otherwise mark an id() nothing ever looks up again
    strength = 4
    ap = 0
    damage = 1
    strength_notation = None  # game/dice_notation.py's DiceNotation, e.g. D6(6) for a printed "D6+6" Strength characteristic (Battlewagon's Zzap gun) - None means `strength` above is a real fixed value, used as-is. When set, `strength` is only a grouping/preview placeholder (shooting.py's _attack_key), and the ACTUAL value is rolled for real, once per weapon group, before the Wound roll - see ShootingController's "strength" pending step. RANGED only so far: game/fight.py has no such weapon and does not roll one
    damage_notation = None  # game/dice_notation.py's DiceNotation, e.g. D6() for a printed "D6" Damage characteristic - None means `damage` above is a real fixed value, used as-is. When set, `damage` is only a grouping/preview placeholder (shooting.py's _attack_key, the Save-roll's damage_per_failure preview) - the ACTUAL amount applied is rolled for real once per attack allocated to a model, see DamageAllocationSession's pending_damage_roll
    assault = False        # the [ASSAULT] keyword - rule 10.05
    close_quarters = False  # the [CLOSE-QUARTERS] keyword - rule 10.06
    indirect_fire = False   # the [INDIRECT FIRE] keyword - rule 10.07
    rapid_fire = 0          # the [RAPID FIRE X] keyword value (X) - rule 24.30, see extra_attack_dice()
    anti = None             # the [ANTI-X Y+] keyword - a (keyword, threshold) tuple, e.g. ("VEHICLE", 4), OR a tuple of such tuples for a weapon printing several at once (e.g. Anti-Monster 4+ AND Anti-Vehicle 4+, the Beastboss's weapons); rule 24.03. Where several match the same target, the BEST (lowest) threshold applies - see game/shooting.py's _wound_crit_threshold()
    blast = 0               # the [BLAST]/[BLAST X] keyword value (X; plain [BLAST] is X=1) - rule 24.05
    cleave = 0              # the [CLEAVE X] keyword value (X) - rule 24.06
    devastating_wounds = False  # the [DEVASTATING WOUNDS] keyword - rule 24.10
    devastating_wounds_vs_non_monster_vehicle = False  # the CONDITIONAL form, printed as "DEVASTATING WOUNDS: non-MONSTER/VEHICLE" on the Leystalker's Long Rifle - granted against the real target in game/conditional_devastating_wounds.py, never as the flat flag above
    extra_attacks = False   # the [EXTRA ATTACKS] keyword - rule 24.11 (melee only)
    hazardous = False       # the [HAZARDOUS] keyword - rule 24.15
    heavy = False           # the [HEAVY] keyword - rule 24.16 (ranged only, Shooting phase)
    ignores_cover = False   # the [IGNORES COVER] keyword - rule 24.18
    lance = False           # the [LANCE] keyword - rule 24.21 (melee only, see FightController._wound_modifiers)
    lethal_hits = False     # the [LETHAL HITS] keyword - rule 24.23
    melta = 0                # the [MELTA X] keyword value (X) - rule 24.25, see melta_adjusted_weapon() in shooting.py
    one_shot = False         # the [ONE SHOT] keyword - rule 24.26, see ShootingController/FightController.one_shot_used
    pistol = False           # the [PISTOL] keyword - rule 24.27, a pure alias for close_quarters, see is_close_quarters()
    precision = False        # the [PRECISION] keyword - rule 24.28, see _offer_precision_choice()/DamageAllocationSession's priority_group
    psychic = False          # the [PSYCHIC] keyword - rule 24.29, see _hit_modifiers()
    sustained_hits = 0       # the [SUSTAINED HITS X] keyword value (X) - rule 24.36, see _handle_hit_results()'s caller. When sustained_hits_notation below is set this is only a grouping/preview placeholder, never what an attack uses
    sustained_hits_notation = None  # game/dice_notation.py's DiceNotation for a printed dice X, e.g. D3() for the Avatar of Khaine's "[SUSTAINED HITS D3]". None means `sustained_hits` above is a real fixed value. When set, one die per CRITICAL hit is rolled for real as a visible dice_manager step - see shooting.py/fight.py's _begin_sustained_hits_roll(), the same arrangement attacks_notation/damage_notation/strength_notation already have
    torrent = False          # the [TORRENT] keyword - rule 24.37, see _begin_resolution()'s auto-hit skip
    twin_linked = False      # the [TWIN-LINKED] keyword - rule 24.38, see _offer_twin_linked_choice()

    # --- datasheet-specific abilities that hang off one named weapon ---
    # Not core-rule keywords: these are printed as a UNIT ability whose
    # condition is entirely "the attack was made with THIS weapon", so the
    # weapon is where the flag actually belongs (same shape as
    # devastating_wounds above, which is the closest core-rule analogue).
    hold_still = False       # Painboy's "Hold Still and Say 'Aargh!'" - each critical WOUND this weapon scores against a non-VEHICLE unit inflicts D6 mortal wounds on it, on top of the attack itself; see game/hold_still.py


def anti_entries(weapon):
    """WeaponProfile.anti as a uniform sequence of (keyword, threshold).

    It may be written either as a single tuple - ("VEHICLE", 4) - or as a
    tuple of those, for a weapon that prints more than one [ANTI-X] at once
    (the Beastboss's Beast Snagga klaw and Beastchoppa each carry
    Anti-Monster 4+ AND Anti-Vehicle 4+). The single form is detected by its
    second element being an int, which no nested form can be.

    Lives here, beside the field it reads, because two consumers now ask the
    same question: game/shooting.py's _wound_crit_threshold() (which one
    applies against THIS target) and printed_keywords() below (how the whole
    set is spelled on the card). shooting.py re-exports it, so there is one
    definition rather than two that can drift apart."""
    anti = weapon.anti
    if anti is None:
        return ()
    if len(anti) == 2 and isinstance(anti[1], int):
        return (anti,)
    return tuple(anti)


def max_damage(weapon):
    """The most Damage one attack with this weapon could ever do.

    Lives here, beside the two fields it reads, because the answer is a fact
    about the weapon and nothing else - the same reason anti_entries() above
    sits here rather than in shooting.py, which first needed it.

    READS THE NOTATION, NEVER THE PLAIN INT. Where damage_notation is set the
    `damage` beside it is only a grouping/preview placeholder (its own comment
    in WeaponProfile says so), and it is MEASURABLY inconsistent about what it
    holds - counted over every weapon in this file that carries one, 38 of 56
    store something that is NOT the maximum: the Bright Lance stores 8 for a
    printed D6+2 (the maximum), the Starshot missile 3 for a plain D6 (the
    mean), the Blaster 4 for D6+1, and the Wurrtower 1 for a D6. Reading it
    would make "what could that shot have done" come out anywhere from 1 to 8
    for the same printed characteristic, depending on which datasheet asked.

    So: sides x dice + bonus for a notation - D6+2 is 8, 2D6 is 12 - and the
    fixed int only where there is no notation at all.

    game/battle_stats.py's "Best Tanking Units" is the caller: it values every
    attack a unit turned aside at what that attack could have done, which is
    exactly this number."""
    notation = weapon.damage_notation
    if notation is not None:
        return notation.sides * notation.dice + notation.bonus
    return weapon.damage


#: (attribute, printed spelling) for every keyword that is a plain on/off flag.
#: The ones carrying a VALUE (anti/blast/cleave/melta/rapid_fire/
#: sustained_hits) are spelled in printed_keywords() below, because their
#: printed form is not a constant.
_FLAG_KEYWORDS = (
    ("assault", "ASSAULT"),
    ("close_quarters", "CLOSE-QUARTERS"),
    ("devastating_wounds", "DEVASTATING WOUNDS"),
    ("devastating_wounds_vs_non_monster_vehicle", "DEVASTATING WOUNDS: non-MONSTER/VEHICLE"),
    ("extra_attacks", "EXTRA ATTACKS"),
    ("hazardous", "HAZARDOUS"),
    ("heavy", "HEAVY"),
    ("ignores_cover", "IGNORES COVER"),
    ("indirect_fire", "INDIRECT FIRE"),
    ("lance", "LANCE"),
    ("lethal_hits", "LETHAL HITS"),
    ("one_shot", "ONE SHOT"),
    ("pistol", "PISTOL"),
    ("precision", "PRECISION"),
    ("psychic", "PSYCHIC"),
    ("torrent", "TORRENT"),
    ("twin_linked", "TWIN-LINKED"),
)


def printed_keywords(weapon):
    """This weapon's keywords, spelled and ordered the way its datasheet
    prints them: ["ASSAULT", "RAPID FIRE 1", "TWIN-LINKED"].

    Reported: "in den weapon info tabellen im overlay fehlen die keywords (zb
    twin linked oder sustained hits)". The hover datacard's weapon tables drew
    Range/A/BS/S/AP/D and stopped there, so the half of a weapon row that
    decides how it actually behaves - [TORRENT] means no Hit roll at all,
    [TWIN-LINKED] a re-roll, [DEVASTATING WOUNDS] wounds that skip the save -
    was on no screen anywhere in the game.

    THE ONE DEFINITION of "how is this weapon's keyword column printed",
    living beside the flags it reads rather than in the card that first needed
    it: a second consumer (a tooltip, the loadout list, a future weapon
    picker) asks the same question and must get the same answer.

    ALPHABETICAL, because that is the printed order - measured, not assumed:
    of the 35 distinct multi-keyword rows in rules/*.md, all 35 are sorted.
    Sorting the spelled-out strings reproduces it (BLAST < DEVASTATING WOUNDS
    < INDIRECT FIRE), so the card matches the sheet a player is holding.

    Read off the object it is given, exactly as printed_characteristic() in
    game/ui/unit_datacard.py does: on a model's own weapon instance that is
    the printed row, and a caller that hands it a runtime-adjusted copy gets
    that copy's answer, which is what such a caller is asking for.

    NOT included: `hold_still`. Its own comment in WeaponProfile says why -
    it is printed as a UNIT ability whose condition happens to name one
    weapon, not as a keyword in that weapon's keyword column. Painboy's
    printed row is empty there, and inventing an entry would be the card
    claiming something the datasheet does not say. The same holds for the
    three datasheet-specific weapon abilities this engine deliberately does
    not model (Dead Choppy, Snagged, Linked Fire) - each is documented as
    unmodeled where its weapon is defined, and printing them would promise a
    rule that no code enforces.
    """
    printed = []
    for keyword, threshold in anti_entries(weapon):
        printed.append("ANTI-%s %d+" % (keyword, threshold))
    for attribute, spelling in _FLAG_KEYWORDS:
        if getattr(weapon, attribute, False):
            printed.append(spelling)
    # Plain [BLAST] carries no X on the printed sheet; this engine stores it
    # as X=1 (see WeaponProfile.blast), so 1 prints bare. Nothing sets a
    # higher value today, but a printed "[BLAST 2]" would still be honest.
    if weapon.blast:
        printed.append("BLAST" if weapon.blast == 1 else "BLAST %d" % weapon.blast)
    for attribute, spelling in (("cleave", "CLEAVE"), ("melta", "MELTA"),
                                ("rapid_fire", "RAPID FIRE")):
        value = getattr(weapon, attribute, 0)
        if value:
            printed.append("%s %d" % (spelling, value))
    # [SUSTAINED HITS X] is the one valued keyword whose X can itself be a
    # die (the Avatar of Khaine prints "[SUSTAINED HITS D3]"), in which case
    # the int beside the notation is only a grouping placeholder - the same
    # trap printed_characteristic() exists for in the A/S/D columns.
    if weapon.sustained_hits_notation is not None:
        printed.append("SUSTAINED HITS %s" % describe(weapon.sustained_hits_notation))
    elif weapon.sustained_hits:
        printed.append("SUSTAINED HITS %d" % weapon.sustained_hits)
    return sorted(printed)


class BolterProfile(WeaponProfile):
    name = "Bolter"
    weapon_type = RANGED
    range_in = 24
    attacks = 2
    strength = 4
    ap = 0
    damage = 2
    assault = True  # for testing rule 10.05 (Assault shooting) in the live demo scene


class CloseCombatWeaponProfile(WeaponProfile):
    """Generic fallback melee weapon for the demo squads that don't have a
    real datasheet's named close-combat weapon pasted yet - every 40k unit
    can still fight in melee even without one. Stats are a placeholder (not
    from any specific datasheet), only so the Fight phase has something to
    roll for units other than the Boyz."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 1
    strength = 4
    ap = 0
    damage = 1


# --- Boyz (Orks) datasheet, see game/factions/orks.py ---

class ShootaProfile(WeaponProfile):
    """Unselected Profiles alternate for the rank-and-file Boy (not part of
    the datasheet's own default loadout, see BOYZ's Slugga+Choppa build in
    game/factions/orks.py)."""
    name = "Shoota"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 4
    ap = 0
    damage = 1
    rapid_fire = 1


class KombiWeaponProfile(WeaponProfile):
    """Unselected Profiles alternate, real stat line (user-supplied,
    corrects two earlier guesses here - KombiShootaProfile/KombiRokkitProfile
    - that didn't match any actual printed Boyz datasheet stat line and are
    now removed)."""
    name = "Kombi-weapon"
    weapon_type = RANGED
    range_in = 24
    attacks = 1
    strength = 4
    ap = 0
    damage = 1
    anti = ("INFANTRY", 4)
    devastating_wounds = True
    rapid_fire = 1


class SluggaProfile(WeaponProfile):
    name = "Slugga"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 4
    ap = 0
    damage = 1
    pistol = True  # the [PISTOL] keyword, rule 24.27 - printed keyword is "Pistol", not "Close-Quarters" (is_close_quarters() treats both the same, see WeaponProfile's own note)


class BigChoppaProfile(WeaponProfile):
    name = "Big Choppa"
    weapon_type = MELEE
    range_in = 2  # melee "range" is engagement range, not a distinct weapon stat
    attacks = 3
    strength = 7
    ap = -1
    damage = 2


class ChoppaProfile(WeaponProfile):
    name = "Choppa"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 4
    ap = -1
    damage = 1


class OrkCloseCombatWeaponProfile(WeaponProfile):
    """Boyz's own "Close combat weapon (x2)" Unselected Profiles alternate
    (A2 WS3+ S4 AP0 D1) - not wired as a Boyz wargear option yet (no
    swap-rule text given, same documented gap as every other Unselected
    Profiles entry), but the IDENTICAL stat line is Warbikers' own actual
    default loadout weapon (see WARBIKERS in game/factions/orks.py) - named
    generically (not "Boyz..."/"Warbikers...") since it's reused as-is
    across datasheets, same convention as TauCloseCombatWeaponProfile/
    KrootCloseCombatWeaponProfile. Not the same class as the plain
    CloseCombatWeaponProfile placeholder at the top of this file (A1, no
    specific datasheet) - this one has a real, datasheet-sourced A2."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 4
    ap = 0
    damage = 1


class PowerKlawProfile(WeaponProfile):
    """Boyz's own "Power klaw" Unselected Profiles alternate (A3 WS4+ S9
    AP-2 D2) - was deliberately left unbuilt for a while (WeaponProfile had
    a per-weapon `ballistic_skill` override but no equivalent WS one, and
    Power klaw's WS4+ is worse than a Boss Nob's own WS3+) until an actual
    army list selected it for real (Boyz/Stormboyz/Warbikers Boss Nobs),
    which is when the missing weapon_skill override field/fight.py's
    effective_weapon_skill() were added. Named generically (not
    "Boyz..."/"Stormboyz..."/"Warbikers...") since it's the same printed
    wargear item reused as-is across all three of those datasheets'
    Boss Nob upgrade options."""
    name = "Power Klaw"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    weapon_skill = "4+"
    strength = 9
    ap = -2
    damage = 2


# --- Warbikers (Orks) datasheet, see game/factions/orks.py ---

class TwinDakkagunProfile(WeaponProfile):
    name = "Twin Dakkagun"
    weapon_type = RANGED
    range_in = 18
    attacks = 3
    strength = 5
    ap = 0
    damage = 1
    assault = True
    rapid_fire = 2
    twin_linked = True


# --- Trukk (Orks) datasheet, see game/factions/orks.py ---

class BigShootaProfile(WeaponProfile):
    name = "Big Shoota"
    weapon_type = RANGED
    range_in = 36
    attacks = 3
    strength = 5
    ap = 0
    damage = 1
    rapid_fire = 2


class SpikedWheelProfile(WeaponProfile):
    name = "Spiked Wheel"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = 0
    damage = 1


class WreckinBallProfile(WeaponProfile):
    """Trukk's own "Unselected Profiles" alternate (D6 Damage - WS4+ here
    matches the Trukk's own weapon_skill, so no weapon_skill override was
    ever needed for this one, unlike PowerKlawProfile above)."""
    name = "Wreckin' Ball"
    weapon_type = MELEE
    range_in = 2
    attacks = 1
    strength = 10
    ap = 0
    damage = 6
    damage_notation = D6()
    extra_attacks = True


# --- Gretchin (Orks) datasheet, see game/factions/orks.py ---

class GrotBlastaProfile(WeaponProfile):
    name = "Grot Blasta"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 3
    ap = 0
    damage = 1
    pistol = True


class GretchinCloseCombatWeaponProfile(WeaponProfile):
    """Gretchin's own "Close combat weapon" (A1 WS5+ S2 AP0 D1) - a
    distinct, much weaker class from both the generic CloseCombatWeaponProfile
    (A1 S4) and OrkCloseCombatWeaponProfile (A2 S4), same "same printed
    name, different stats, needs its own class" reasoning as
    TauCloseCombatWeaponProfile."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 1
    strength = 2
    ap = 0
    damage = 1


class GrotSmackaProfile(WeaponProfile):
    name = "Grot-Smacka"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 5
    ap = 0
    damage = 1


# --- Warboss (Orks) datasheet, see game/factions/orks.py ---
# "Kombi-weapon" is NOT a new class - the Warboss's printed stat line (range
# 24", A1, S4, AP0, D1, Anti-Infantry 4+, Devastating Wounds, Rapid Fire 1)
# is word-for-word identical to KombiWeaponProfile above (Boyz's own
# Unselected Profiles entry), so it's reused as-is.

class TwinSluggaProfile(WeaponProfile):
    """Warboss's own "Twin slugga" (A2 S4 AP0 D1, Pistol/Twin-linked) - a
    distinct, stronger class from the rank-and-file SluggaProfile (A1, no
    Twin-linked), same "same weapon family, different stat line for this
    datasheet" pattern as OrkCloseCombatWeaponProfile vs the plain
    CloseCombatWeaponProfile."""
    name = "Twin Slugga"
    weapon_type = RANGED
    range_in = 12
    attacks = 2
    strength = 4
    ap = 0
    damage = 1
    pistol = True
    twin_linked = True


class AttackSquigProfile(WeaponProfile):
    """The Warboss's own "Attack squig" (Melee, A2, WS4+, S4, AP0, D1,
    [EXTRA ATTACKS]) - a wargear item rather than a weapon swap, so
    [EXTRA ATTACKS] (24.11) is what lets it bite alongside whatever the
    Warboss himself swings under rule 04.01. Its WS4+ is worse than the
    Warboss's own 2+, hence the per-weapon override."""
    name = "Attack Squig"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    weapon_skill = "4+"  # printed on the weapon, worse than the Warboss's own 2+
    strength = 4
    ap = 0
    damage = 1
    extra_attacks = True


class WarbossBigChoppaProfile(WeaponProfile):
    """Warboss's own "Big choppa" (A5 S8 AP-1 D2) - a distinct, stronger
    stat line from Boyz' own Big Choppa (BigChoppaProfile: A3 S7 AP-1 D2),
    same "same printed name, different numbers per datasheet" pattern as
    GretchinCloseCombatWeaponProfile vs CloseCombatWeaponProfile. Named
    distinctly (not reusing BigChoppaProfile) for that reason."""
    name = "Big Choppa"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 8
    ap = -1
    damage = 2


class WarbossPowerKlawProfile(WeaponProfile):
    """Warboss's own "Unselected Profiles" alternate Power klaw (A4 WS3+
    S10 AP-2 D2) - a distinct, stronger stat line from Boyz/Stormboyz/
    Warbikers' shared PowerKlawProfile (A3 WS4+ S9 AP-2 D2). Not wired as a
    Warboss wargear option (no swap-rule text given), same documented gap as
    every other datasheet's own Unselected Profiles entries."""
    name = "Power Klaw"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    weapon_skill = "3+"
    strength = 10
    ap = -2
    damage = 2


# --- Meganobz (Orks) datasheet, see game/factions/orks.py ---
# "Kombi-weapon" (Unselected Profiles) is NOT a new class - identical stat
# line to KombiWeaponProfile above (Boyz' own Unselected Profiles entry,
# already reused as-is by Warboss). "Power klaw" (both the actual default
# loadout AND the Unselected Profiles reference) is NOT a new class either
# - identical stat line (A3 WS4+ S9 AP-2 D2) to the existing PowerKlawProfile
# (Boyz/Stormboyz/Warbikers' shared Boss Nob upgrade), reused as-is.

class KustomShootaProfile(WeaponProfile):
    name = "Kustom Shoota"
    weapon_type = RANGED
    range_in = 18
    attacks = 4
    strength = 4
    ap = 0
    damage = 1
    rapid_fire = 2


class KillsawProfile(WeaponProfile):
    """Meganobz's own "Unselected Profiles" alternate (A2 WS4+ S12 AP-3 D2)
    - not wired as a wargear option yet (no swap-rule text given), same
    documented gap as every other datasheet's own Unselected Profiles."""
    name = "Killsaw"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    weapon_skill = "4+"
    strength = 12
    ap = -3
    damage = 2


class TwinKillsawProfile(WeaponProfile):
    """Meganobz's own "Unselected Profiles" alternate - identical stat line
    to KillsawProfile above but [TWIN-LINKED], same "same weapon, one more
    keyword" relationship as e.g. TwinDakkagunProfile has to a plain dakka
    weapon elsewhere in this file."""
    name = "Twin Killsaw"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    weapon_skill = "4+"
    strength = 12
    ap = -3
    damage = 2
    twin_linked = True


# --- Warboss in Mega Armour (Orks) datasheet, see game/factions/orks.py ---
# "Big shoota" is NOT a new class - the printed stat line (range 36", A3,
# S5, AP0, D1, Rapid Fire 2) is word-for-word identical to BigShootaProfile
# above (Trukk's own weapon), so it's reused as-is.

class UgeChoppaProfile(WeaponProfile):
    name = "'Uge Choppa"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 12
    ap = -2
    damage = 2


# --- Tankbustas (Orks) datasheet, see game/factions/orks.py ---

class RokkitPistolProfile(WeaponProfile):
    name = "Rokkit Pistol"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 9
    ap = -2
    damage = 3
    pistol = True


class RokkitLunchaProfile(WeaponProfile):
    """Tankbustas' own "Rokkit launcha" - a dice-notation Attacks
    characteristic (a printed "D3"), same real-dice-roll treatment as
    TauFlamerProfile's own D6 Attacks (see attacks_notation's own note) -
    `attacks` below is only the preview/leftover placeholder value."""
    name = "Rokkit Launcha"
    weapon_type = RANGED
    range_in = 24
    attacks = 1
    attacks_notation = D3()
    strength = 9
    ap = -2
    damage = 3
    blast = 1  # plain [BLAST] keyword (X=1), see WeaponProfile.blast's own note


class TankbustaChoppaProfile(WeaponProfile):
    """Tankbustas' own Boss Nob's "Choppa" (A4 S5 AP-1 D1) - a distinct,
    stronger stat line from Boyz' own ChoppaProfile (A3 S4 AP-1 D1), same
    "same printed name, different numbers per datasheet" pattern as
    GretchinCloseCombatWeaponProfile vs CloseCombatWeaponProfile."""
    name = "Choppa"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = -1
    damage = 1


class TankbustaCloseCombatWeaponProfile(WeaponProfile):
    """Tankbustas' own "Close combat weapon" (A3 S5 AP0 D1) - a distinct
    stat line from both the generic CloseCombatWeaponProfile (A1 S4) and
    OrkCloseCombatWeaponProfile (A2 S4), same "same printed name, needs its
    own class" reasoning as GretchinCloseCombatWeaponProfile."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 5
    ap = 0
    damage = 1


class SmashHammerProfile(WeaponProfile):
    """Tankbustas' own "Unselected Profiles" alternate (A2 S6 AP-2 D3,
    Anti-Monster 4+ AND Anti-Vehicle 4+) - not wired as a wargear option
    (no swap-rule text given), same documented gap as every other
    datasheet's own Unselected Profiles. Both of its [ANTI-X] keywords are
    now modeled: `anti` used to hold a single (keyword, threshold) tuple,
    so Anti-Monster 4+ was dropped and only Anti-Vehicle 4+ survived. The
    Beastboss's weapons print the same pair on a real, fielded loadout,
    which is what finally generalized the field (see WeaponProfile.anti's
    own note) - this weapon just gets its missing half back for free."""
    name = "Smash Hammer"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 6
    ap = -2
    damage = 3
    anti = (("MONSTER", 4), ("VEHICLE", 4))


# --- Deffkoptas (Orks) datasheet, see game/factions/orks.py ---
# "Slugga" is NOT a new class - identical stat line (range 12", A1, S4, AP0,
# D1, Pistol) to the existing SluggaProfile (Boyz' own weapon), reused as-is.

class KoptaRokkitsProfile(WeaponProfile):
    """Deffkoptas' own "Kopta rokkits" - same dice-notation Attacks
    treatment as Tankbustas' own Rokkit Launcha (RokkitLunchaProfile,
    identical S/AP/D/Blast), but also [TWIN-LINKED] - a distinct class
    for that reason, not a reuse."""
    name = "Kopta Rokkits"
    weapon_type = RANGED
    range_in = 24
    attacks = 1
    attacks_notation = D3()
    strength = 9
    ap = -2
    damage = 3
    blast = 1
    twin_linked = True


class SpinninBladesProfile(WeaponProfile):
    name = "Spinnin' Blades"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 5
    ap = 0
    damage = 1


class KustomMegaBlastaProfile(WeaponProfile):
    """Deffkoptas' own "Unselected Profiles" alternate (A3 S9 AP-2, D6
    Damage, [HAZARDOUS]) - not wired as a wargear option (no swap-rule text
    given), same documented gap as every other datasheet's own Unselected
    Profiles."""
    name = "Kustom Mega-Blasta"
    weapon_type = RANGED
    range_in = 24
    attacks = 3
    strength = 9
    ap = -2
    damage = 6
    damage_notation = D6()
    hazardous = True


# --- Deff Dread (Orks) datasheet, see game/factions/orks.py ---
# "Big shoota" is NOT a new class - identical stat line to BigShootaProfile
# above (Trukk's own weapon), reused as-is. "Kustom mega-blasta" (Unselected
# Profiles) is likewise NOT a new class - identical stat line to
# KustomMegaBlastaProfile above (Deffkoptas' own Unselected Profiles entry),
# reused as-is. "Rokkit launcha" (Unselected Profiles) is also NOT a new
# class - identical stat line to RokkitLunchaProfile above (Tankbustas' own
# weapon), reused as-is.

class StompyFeetProfile(WeaponProfile):
    name = "Stompy Feet"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = 0
    damage = 1


class DreadKlawProfile(WeaponProfile):
    """Deff Dread's own "Dread klaw" - printed A4 already reflects this
    model's actual loadout (2x Dread klaw): the datasheet's own "Dead
    Choppy" ability adds +1 Attacks per ADDITIONAL Dread klaw equipped
    (base A3, +1 for the 2nd), and since this datasheet only has one
    modeled composition (always exactly 2x Dread klaw, no wargear option to
    change that count), the bonus is simply baked into this class's fixed
    `attacks` value rather than computed at runtime - there's no other
    loadout for it to differ against yet. Dead Choppy itself is therefore
    NOT engine-wired as a live per-count calculation (abilities_text only)
    - see game/factions/orks.py's own note."""
    name = "Dread Klaw"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 12
    ap = -2
    damage = 3


class SkorchaProfile(WeaponProfile):
    """Deff Dread's own "Unselected Profiles" alternate (D6 Attacks, S5
    AP-1 D1, [IGNORES COVER]/[TORRENT]) - not wired as a wargear option (no
    swap-rule text given), same documented gap as every other datasheet's
    own Unselected Profiles. Printed BS is "N/A" - [TORRENT] attacks
    auto-hit (rule 24.37) and never roll a Hit roll at all, so no
    ballistic_skill override is needed for that "N/A" to already be
    correct."""
    name = "Skorcha"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    attacks_notation = D6()
    strength = 5
    ap = -1
    damage = 1
    ignores_cover = True
    torrent = True


# --- Beast Snagga Boyz (Orks) datasheet, see game/factions/orks.py ---
# "Slugga" is NOT a new class - the printed stat line (range 12", A1, BS5+,
# S4, AP0, D1, Pistol) is word-for-word identical to SluggaProfile above
# (Boyz' own weapon), reused as-is. The other three all LOOK like weapons
# this file already has and are not: this datasheet's Choppa is S5 where
# Boyz' ChoppaProfile is S4, its Close combat weapon is S5 where
# OrkCloseCombatWeaponProfile is S4, and Power snappa is A4 where the
# otherwise identical BigChoppaProfile is A3. Same "same printed name,
# different numbers, needs its own class" reasoning as
# GretchinCloseCombatWeaponProfile/TankbustaCloseCombatWeaponProfile.

class PowerSnappaProfile(WeaponProfile):
    """Beast Snagga Boyz' Nob weapon (A4 WS3+ S7 AP-1 D2). One Attack more
    than BigChoppaProfile (A3), which is otherwise the same line - hence a
    class of its own rather than a reuse."""
    name = "Power Snappa"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 7
    ap = -1
    damage = 2


class BeastSnaggaChoppaProfile(WeaponProfile):
    """Beast Snagga Boyz' rank-and-file melee weapon (A3 WS3+ S5 AP-1 D1) -
    a Choppa with S5, where Boyz' own ChoppaProfile is S4."""
    name = "Choppa"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 5
    ap = -1
    damage = 1


class ThumpGunProfile(WeaponProfile):
    """Beast Snagga Boyz' one ranged alternate (18", A D3, BS5+, S6, AP0,
    D2, [BLAST]) - carried by the one Beast Snagga Boy who swaps away his
    Slugga and Choppa for it. `attacks_notation` makes the printed "D3"
    Attacks a real, visible dice roll (see WeaponProfile.attacks_notation's
    own note), same as TauFlamerProfile's/Kopta Rokkits' own."""
    name = "Thump Gun"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    attacks_notation = D3()
    strength = 6
    ap = 0
    damage = 2
    blast = 1  # plain [BLAST] (no explicit X) is X=1, see WeaponProfile.blast


class BeastSnaggaCloseCombatWeaponProfile(WeaponProfile):
    """The melee weapon the thump gun's carrier keeps instead of a Choppa
    (A2 WS3+ S5 AP0 D1) - S5, where the otherwise identical
    OrkCloseCombatWeaponProfile is S4, and A2 where
    TankbustaCloseCombatWeaponProfile is A3."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 5
    ap = 0
    damage = 1


# --- Beastboss (Orks) datasheet, see game/factions/orks.py ---
# "Shoota" is NOT a new class - the printed stat line (18", A2, S4, AP0, D1,
# Rapid Fire 1) is word-for-word identical to ShootaProfile above (Boyz'
# own Unselected Profiles entry), and it deliberately has no
# ballistic_skill of its own, so it correctly picks up the Beastboss's own
# BS4+ rather than the BS5+ a Boy would shoot it at.
#
# Both melee weapons below carry Anti-Monster 4+ AND Anti-Vehicle 4+ - the
# first REAL, fielded loadout to print two [ANTI-X] keywords at once, which
# is what generalized WeaponProfile.anti from a single tuple to a sequence
# (see its own note; Smash Hammer had the same pair but only as an
# Unselected Profile, and lost half of it until now).

class BeastSnaggaKlawProfile(WeaponProfile):
    """Beastboss's heavy melee weapon (A4 WS3+ S10 AP-2 D2). Its WS3+ does
    NOT match this model's own printed WS - see BeastchoppaProfile below
    and BeastbossProfile's own note on why the profile carries 2+ and this
    weapon overrides."""
    name = "Beast Snagga Klaw"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    weapon_skill = "3+"  # printed on the weapon, worse than the Beastboss's own 2+
    strength = 10
    ap = -2
    damage = 2
    anti = (("MONSTER", 4), ("VEHICLE", 4))


class BeastchoppaProfile(WeaponProfile):
    """Beastboss's fast melee weapon (A6 WS2+ S6 AP-1 D2) - more attacks and
    a better hit roll than the klaw, but less Strength and AP, so the two
    are a genuine per-activation choice under rule 04.01 (only one melee
    weapon per model per fight), not one strictly better profile."""
    name = "Beastchoppa"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 6
    ap = -1
    damage = 2
    anti = (("MONSTER", 4), ("VEHICLE", 4))


# --- Kill Rig (Orks) datasheet, see game/factions/orks.py ---
# Every weapon below is new - none of the six matches an existing stat line.
# One printed keyword is NOT modeled: Stikka kannon's "Snagged". No rule
# text was supplied for it and it is not one of the core 24.xx keywords this
# engine knows, so there is nothing to implement against; flagged on the
# class itself rather than silently dropped.

class EavyLobbaProfile(WeaponProfile):
    """Kill Rig's artillery piece (48", A D6, BS5+, S6, AP0, D2, [BLAST],
    [INDIRECT FIRE]). `attacks_notation` makes the printed "D6" a real,
    visible roll (see WeaponProfile.attacks_notation's own note)."""
    name = "'Eavy Lobba"
    weapon_type = RANGED
    range_in = 48
    attacks = 1
    attacks_notation = D6()
    strength = 6
    ap = 0
    damage = 2
    blast = 1  # plain [BLAST] (no explicit X) is X=1, see WeaponProfile.blast
    indirect_fire = True  # [INDIRECT FIRE], rule 10.07


class StikkaKannonProfile(WeaponProfile):
    """Kill Rig's anti-armour shot (12", A1, BS5+, S12, AP-2, D3,
    Anti-Monster 2+, Anti-Vehicle 2+, Snagged).

    "Snagged" is NOT modeled: no rule text for it was supplied, and it is
    not a core 24.xx keyword this engine knows - same documented status as
    Tankbustas' Pulsa Rokkit. The two [ANTI-X] keywords ARE both modeled
    (see WeaponProfile.anti), and at 2+ they are the lowest crit threshold
    on any weapon here."""
    name = "Stikka Kannon"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 12
    ap = -2
    damage = 3
    anti = (("MONSTER", 2), ("VEHICLE", 2))


class WurrtowerProfile(WeaponProfile):
    """Kill Rig's psychic weapon (24", A D3, BS N/A, S12, AP-3, D D6,
    [HAZARDOUS], [PSYCHIC], [TORRENT]).

    The printed BS "N/A" needs no override: [TORRENT] attacks auto-hit
    (rule 24.37) and never make a Hit roll at all, exactly as
    SkorchaProfile already documents. Both its Attacks and its Damage are
    real dice rolls (attacks_notation/damage_notation)."""
    name = "Wurrtower"
    weapon_type = RANGED
    range_in = 24
    attacks = 1
    attacks_notation = D3()
    strength = 12
    ap = -3
    damage = 1
    damage_notation = D6()
    hazardous = True  # [HAZARDOUS], rule 24.15
    psychic = True  # [PSYCHIC], rule 24.29
    torrent = True  # [TORRENT], rule 24.37


class ButchaBoyzProfile(WeaponProfile):
    """Kill Rig's crew swinging over the side (A4 WS3+ S5 AP-1 D1,
    Anti-Monster 4+, Anti-Vehicle 4+, [EXTRA ATTACKS]). [EXTRA ATTACKS]
    (24.11) is what lets it swing alongside the model's chosen melee weapon
    instead of competing with it under rule 04.01."""
    name = "Butcha Boyz"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = -1
    damage = 1
    anti = (("MONSTER", 4), ("VEHICLE", 4))
    extra_attacks = True


class SawBladesProfile(WeaponProfile):
    """Kill Rig's main melee weapon (A6 WS3+ S10 AP-2 D2)."""
    name = "Saw Blades"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 10
    ap = -2
    damage = 2


class SavageHornsAndHoovesProfile(WeaponProfile):
    """The squigosaur underneath (A4 WS4+ S8 AP-1 D3, [EXTRA ATTACKS],
    [LANCE]). Its WS4+ is worse than the Kill Rig's own 3+, hence the
    per-weapon override."""
    name = "Savage Horns and Hooves"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    weapon_skill = "4+"  # printed on the weapon, worse than the Kill Rig's own 3+
    strength = 8
    ap = -1
    damage = 3
    extra_attacks = True
    lance = True  # [LANCE], rule 24.21


# --- Flash Gitz (Orks) datasheet, see game/factions/orks.py ---
# Both weapons are new classes. The Choppa in particular LOOKS like one this
# file already has and is not: A4 where Boyz' ChoppaProfile and Beast Snagga
# Boyz' own BeastSnaggaChoppaProfile are both A3 (it shares the latter's S5).
# Third same-named, different-numbered Choppa in this file - see
# BeastSnaggaChoppaProfile's own note for the convention.

class SnazzgunProfile(WeaponProfile):
    """Flash Gitz' looted shoota (24", A3, BS5+, S6, AP-1, D2, [HEAVY],
    [SUSTAINED HITS 1]).

    Its printed Attacks is 3; Gun-crazy Show-offs raises it to 4 against the
    closest eligible target, which is applied as a real characteristic
    change on a copy at resolution time rather than baked in here - see
    game/gun_crazy_showoffs.py."""
    name = "Snazzgun"
    weapon_type = RANGED
    range_in = 24
    attacks = 3
    strength = 6
    ap = -1
    damage = 2
    heavy = True  # [HEAVY], rule 24.16
    sustained_hits = 1  # [SUSTAINED HITS 1], rule 24.36


class FlashGitzChoppaProfile(WeaponProfile):
    """Flash Gitz' melee weapon (A4 WS3+ S5 AP-1 D1) - one Attack more than
    BeastSnaggaChoppaProfile, which is otherwise the same line."""
    name = "Choppa"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = -1
    damage = 1


# --- Battlewagon (Orks) datasheet, see game/factions/orks.py ---
# Two of its Unselected Profiles are NOT new classes: "Big shoota" (36", A3,
# S5, AP0, D1, Rapid Fire 2) is word-for-word BigShootaProfile above (Trukk's
# own weapon), and "Wreckin' ball" (A1, WS4+, S10, AP0, D D6, [EXTRA ATTACKS])
# is word-for-word WreckinBallProfile above (Trukk's own Unselected Profile) -
# including its WS4+, which matches the Battlewagon's own weapon_skill just as
# it matched the Trukk's. Both reused as-is.

class TracksAndWheelsProfile(WeaponProfile):
    """Battlewagon's only default weapon - it simply runs things over
    (A6 WS4+ S8 AP0 D1). WS4+ matches this model's own, so no override."""
    name = "Tracks and Wheels"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 8
    ap = 0
    damage = 1


class LobbaProfile(WeaponProfile):
    """Battlewagon's own "Unselected Profiles" artillery alternate (48",
    A D6, BS5+, S5, AP0, D1, [BLAST], [INDIRECT FIRE]).

    NOT the same class as the Kill Rig's EavyLobbaProfile above, despite the
    related name: that one is S6/D2, this is S5/D1."""
    name = "Lobba"
    weapon_type = RANGED
    range_in = 48
    attacks = 1
    attacks_notation = D6()
    strength = 5
    ap = 0
    damage = 1
    blast = 1  # plain [BLAST] (no explicit X) is X=1, see WeaponProfile.blast
    indirect_fire = True  # [INDIRECT FIRE], rule 10.07


class GrabbinKlawProfile(WeaponProfile):
    """Battlewagon's own "Unselected Profiles" alternate (A2 WS3+ S8 AP-2 D2,
    [EXTRA ATTACKS]). Its WS3+ is BETTER than the Battlewagon's own 4+, hence
    the per-weapon override - the first weapon in this file whose override
    improves on its wielder rather than worsening it."""
    name = "Grabbin' Klaw"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    weapon_skill = "3+"  # printed on the weapon, BETTER than the Battlewagon's own 4+
    strength = 8
    ap = -2
    damage = 2
    extra_attacks = True


class ZzapGunProfile(WeaponProfile):
    """Battlewagon's own "Unselected Profiles" alternate, and part of the
    supplied army list's actual build (36", A1, BS5+, S D6+6, AP-3, D5,
    Anti-Vehicle 4+).

    The first weapon in this file with a DICE-ROLLED Strength characteristic
    (`strength_notation`) - a real, visible roll before the Wound roll, the
    same treatment attacks_notation/damage_notation already get. The printed
    `strength` below is only the preview/grouping placeholder the two of them
    use; 9 is D6+6's average rounded, never the value an attack resolves
    with."""
    name = "Zzap Gun"
    weapon_type = RANGED
    range_in = 36
    attacks = 1
    strength = 9  # preview/grouping placeholder only - see strength_notation
    strength_notation = D6(6)  # "S D6+6"
    ap = -3
    damage = 5
    anti = (("VEHICLE", 4),)  # [ANTI-VEHICLE 4+], rule 24.03


class DeffRollaProfile(WeaponProfile):
    """Battlewagon's own "Unselected Profiles" alternate (A6 WS3+ S9 AP-1
    D2). Same better-than-its-wielder WS3+ override as Grabbin' Klaw above."""
    name = "Deff Rolla"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    weapon_skill = "3+"  # printed on the weapon, BETTER than the Battlewagon's own 4+
    strength = 9
    ap = -1
    damage = 2


# --- Painboy (Orks) datasheet, see game/factions/orks.py ---

class UrtySyringeProfile(WeaponProfile):
    """Painboy's "'Urty syringe" (Melee, A1, WS3+, S2, AP0, D1,
    [ANTI-INFANTRY 4+], [EXTRA ATTACKS], [PRECISION]).

    No `weapon_skill` override even though the datasheet prints WS3+ on the
    weapon: that IS PainboyProfile's own Weapon Skill, so the printed value
    is not an override at all (see WeaponProfile.weapon_skill's own note -
    None means "use the wielder's"). Its Power klaw is the one that really
    deviates, and that profile already carries its own 4+.

    [EXTRA ATTACKS] (24.11) is what makes this datasheet's two melee weapons
    both swing in the same activation despite rule 04.01 - same shape as the
    Warboss's Attack Squig - and it is what makes the combination with
    [ANTI-INFANTRY 4+] the point of the model: against INFANTRY a wound roll
    of 4+ is a CRITICAL wound (24.03), and each critical wound is what "Hold
    Still and Say 'Aargh!'" turns into D6 mortal wounds. `hold_still` below
    is that ability's hook - see game/hold_still.py."""
    name = "'Urty Syringe"
    weapon_type = MELEE
    range_in = 2
    attacks = 1
    strength = 2
    ap = 0
    damage = 1
    anti = ("INFANTRY", 4)  # [ANTI-INFANTRY 4+], rule 24.03
    extra_attacks = True    # [EXTRA ATTACKS], rule 24.11
    precision = True        # [PRECISION], rule 24.28
    hold_still = True       # Painboy's "Hold Still and Say 'Aargh!'" - see game/hold_still.py


# --- Strike Team (T'au Empire) datasheet ---

class PulsePistolProfile(WeaponProfile):
    name = "Pulse Pistol"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 5
    ap = 0
    damage = 1
    pistol = True


class PulsePistolBs3Profile(PulsePistolProfile):
    """The same printed row with its own BS. Strike/Breacher/Pathfinder Teams
    print the pulse pistol at 4+ - their models' own skill, so those inherit
    it from the profile as usual - but the Firesight Team (a BS4+ model) and
    Commander Shadowsun (a BS2+ model) both print it at 3+, which their
    wielders' skill cannot produce in either direction. Hence a per-weapon
    override rather than a change to the shared class, which would have made
    the other three wrong."""
    ballistic_skill = "3+"


class PulseRifleProfile(WeaponProfile):
    name = "Pulse Rifle"
    weapon_type = RANGED
    range_in = 30
    attacks = 1
    strength = 5
    ap = 0
    damage = 1
    rapid_fire = 1


class FirebladePulseRifleProfile(WeaponProfile):
    """Same printed name pattern/stats as the plain PulseRifleProfile above,
    EXCEPT its Damage - Cadre Fireblade's own copy prints D2, not D1 - needs
    its own class since two classes can't share a name/stats, same
    reasoning as the multiple "Close Combat Weapon"/"Battlesuit Fists"
    classes elsewhere in this file."""
    name = "Fireblade Pulse Rifle"
    weapon_type = RANGED
    range_in = 30
    attacks = 1
    strength = 5
    ap = 0
    damage = 2
    rapid_fire = 1


class PulseBlasterProfile(WeaponProfile):
    """Datasheet: Breacher Team. Its own BS3+ is BETTER than the Breacher
    Fire Warrior's own BS4+ - the same per-weapon override mechanism as
    Support Turret's (worse) BS5+, just in the other direction."""
    name = "Pulse Blaster"
    weapon_type = RANGED
    range_in = 10
    attacks = 2
    ballistic_skill = "3+"
    strength = 6
    ap = -1
    damage = 1
    assault = True


class SupportTurretProfile(WeaponProfile):
    """DS8 Support Turret - not part of the Fire Warrior Shas'ui's baseline
    loadout, only ever carried while game/support_turret.py's ability grants
    it. Its own BS5+ (printed on the datasheet, worse than the Shas'ui's own
    BS4+) is why WeaponProfile needed a ballistic_skill override at all."""
    name = "Support Turret"
    weapon_type = RANGED
    range_in = 30
    attacks = 2
    ballistic_skill = "5+"
    strength = 5
    ap = 0
    damage = 1
    indirect_fire = True
    twin_linked = True


class TauCloseCombatWeaponProfile(WeaponProfile):
    """Same printed name as the generic CloseCombatWeaponProfile ("Close
    Combat Weapon"), but Fire Warriors' own version is S3, not S4 - needs
    its own class since two classes can't share a name/stats."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 1
    strength = 3
    ap = 0
    damage = 1


class CadreFirebladeCloseCombatWeaponProfile(WeaponProfile):
    """Same printed name/Strength as TauCloseCombatWeaponProfile above, but
    Cadre Fireblade's own version is A3, not A1 - needs its own class since
    two classes can't share a name/stats, same reasoning as the multiple
    other "Close Combat Weapon" classes in this file."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 3
    ap = 0
    damage = 1


# Strike Team's "Unselected Profiles" - alternate weapons this datasheet has
# in the real game. Twin Pulse Carbine/Missile Pod still have no wargear-swap
# rule text (see CLAUDE.md's Später-Liste), but Pulse Carbine itself is now
# genuinely live - real wargear text (official app, screenshot): "Any number
# of Fire Warrior models can each have their pulse rifle replaced with 1
# pulse carbine", see game/factions/tau_empire.py's STRIKE_TEAM_RIFLE_TO_CARBINE.

class PulseCarbineProfile(WeaponProfile):
    name = "Pulse Carbine"
    weapon_type = RANGED
    range_in = 20
    attacks = 2
    strength = 5
    ap = 0
    damage = 1


class TwinPulseCarbineProfile(WeaponProfile):
    name = "Twin Pulse Carbine"
    weapon_type = RANGED
    range_in = 20
    attacks = 2
    ballistic_skill = "5+"
    strength = 5
    ap = 0
    damage = 1
    assault = True
    twin_linked = True


class MissilePodProfile(WeaponProfile):
    """The printed missile pod row as a MODEL carries it - no ballistic_skill
    override, so the firing model's own BS applies.

    THAT ABSENCE IS THE POINT, and it was found the hard way. This class used
    to hard-code "5+", which is the DRONE's printed value; that was invisible
    while the Missile Drone and the Riptide's drone-carried pair were the only
    users, and became wrong the moment a battlesuit carried one - the Commander
    in Enforcer Battlesuit prints BS3+ and Crisis Fireknife Battlesuits print
    BS4+, and both were silently firing at 5+. The drone's value now lives on
    DroneMissilePodProfile below, where it does real work."""
    name = "Missile Pod"
    weapon_type = RANGED
    range_in = 30
    attacks = 2
    strength = 7
    ap = -1
    damage = 2


class DroneMissilePodProfile(MissilePodProfile):
    """The Missile Drone's own copy: identical except that the drone prints
    BS5+ where the model carrying it prints better. Inherits so the shared
    numbers cannot drift; the test pins the two against each other."""
    ballistic_skill = "5+"


# --- Kroot Carnivores (T'au Empire) datasheet ---

class KrootPistolProfile(WeaponProfile):
    name = "Kroot Pistol"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 4
    ap = 0
    damage = 1
    pistol = True


class KrootRifleProfile(WeaponProfile):
    name = "Kroot Rifle"
    weapon_type = RANGED
    range_in = 24
    attacks = 1
    strength = 4
    ap = 0
    damage = 1
    rapid_fire = 1


class KrootCloseCombatWeaponProfile(WeaponProfile):
    """Same printed name as the other Close Combat Weapon classes, but
    Kroot Carnivores' own version is A2/S4 - needs its own class since two
    classes can't share a name/stats."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 4
    ap = 0
    damage = 1


# Kroot Carnivores' "Unselected Profiles" - same documented gap as Strike/
# Breacher Team (see CLAUDE.md): the actual wargear-swap rule text hasn't
# been given, only these reference profiles - kept here as data, not yet
# wired into any Datasheet's wargear_options.

class TanglebombLauncherProfile(WeaponProfile):
    """Printed Attacks is "D3" - this engine has no dice-notation attacks
    count yet (every WeaponProfile.attacks so far has been a fixed int);
    stored as a placeholder fixed value since this profile is unused
    (no wargear option wires it in yet) rather than left inaccurate AND live."""
    name = "Tanglebomb Launcher"
    weapon_type = RANGED
    range_in = 24
    attacks = 3  # placeholder for "D3" - see class docstring
    strength = 5
    ap = 0
    damage = 1
    blast = 1  # plain [BLAST] (no explicit X) is X=1, see WeaponProfile.blast


class KrootCarbineProfile(WeaponProfile):
    name = "Kroot Carbine"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 4
    ap = 0
    damage = 2


# --- Stealth Battlesuits (T'au Empire) datasheet ---

class BurstCannonProfile(WeaponProfile):
    name = "Burst Cannon"
    weapon_type = RANGED
    range_in = 18
    attacks = 4
    strength = 5
    ap = 0
    damage = 1


class BattlesuitFistsProfile(WeaponProfile):
    name = "Battlesuit Fists"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 4
    ap = 0
    damage = 1


# Stealth Battlesuits' "Unselected Profiles" - same documented gap as every
# other datasheet's alternates (see CLAUDE.md): the actual wargear-swap/
# alternate-composition rule text hasn't been given, only these reference
# profiles (Pulse Pistol/Twin Pulse Carbine/Missile Pod are the exact same
# classes already defined for Strike/Breacher Team above - reused, not
# redefined, since their stats are identical on this datasheet too).

class FusionBlasterProfile(WeaponProfile):
    """Printed Damage is "D6" - genuinely live: Stealth Battlesuits' real
    wargear text ("2 models can each have their burst cannon replaced with
    1 fusion blaster", official app screenshot) wires this in, see
    game/factions/tau_empire.py's STEALTH_BURST_TO_FUSION. `damage_notation`
    (game/dice_notation.py's D6()) makes it fire with a real, visible dice
    roll rather than reintroducing the "fixed placeholder int" bug found
    (and fixed, see TwinFusionBlasterProfile) on Ghostkeel's own D6 weapon;
    `damage` stays as the same placeholder value for grouping/preview
    purposes (see WeaponProfile.damage_notation's own note)."""
    name = "Fusion Blaster"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 9
    ap = -4
    damage = 6  # preview/grouping placeholder only - see class docstring
    damage_notation = D6()
    melta = 2


# --- Crisis Starscythe Battlesuits (T'au Empire) datasheet ---
# Burst Cannon isn't redefined here - Stealth Battlesuits' BurstCannonProfile
# above (18"/A4/BS4+/S5/AP0/D1) has identical stats on this datasheet too.

class TauFlamerProfile(WeaponProfile):
    """Printed Attacks is "D6" - genuinely live: part of Crisis Starscythe
    Battlesuits' actual baseline loadout (1 Burst Cannon + 1 T'au Flamer per
    model, per the real datasheet - see game/factions/tau_empire.py's
    _STARSCYTHE_LOADOUT) AND reachable the other way via its own wargear
    swap (STARSCYTHE_BURST_TO_FLAMER, replacing the Burst Cannon instead).
    First live use of dice-notation Attacks in this engine -
    `attacks_notation` makes it a real, visible D6 roll (game/dice_notation.
    py's DiceNotationRoll, wired into ShootingController/FightController's
    _begin_resolution()), once per attacking model, before the Hit roll even
    starts - the same fix already applied to dice-notation Damage (see
    WeaponProfile.damage_notation), just on the other side of "how many dice
    do I roll" instead of "how much does each one do". `attacks` itself
    stays at the old placeholder value purely as a leftover/preview, same
    role damage_notation's own note describes for `damage`.
    Printed BS is "N/A" - needs no ballistic_skill override (unlike Support
    Turret's worse BS5+ or Pulse Blaster's better BS3+): [TORRENT] (rule
    24.37) skips the hit roll entirely, so no BS value is ever read for it."""
    name = "T'au Flamer"
    weapon_type = RANGED
    range_in = 12
    attacks = 6  # preview/leftover placeholder only - see class docstring
    attacks_notation = D6()
    strength = 4
    ap = 0
    damage = 1
    ignores_cover = True
    torrent = True


class CrisisBattlesuitFistsProfile(WeaponProfile):
    """Same printed name as Stealth Battlesuits' own BattlesuitFistsProfile
    ("Battlesuit Fists"), but Crisis Starscythe's own version is A3/S5,
    not A2/S4 - needs its own class since two classes can't share a name/
    stats, same reasoning as the multiple "Close Combat Weapon" classes."""
    name = "Battlesuit Fists"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 5
    ap = 0
    damage = 1


# --- Devilfish (T'au Empire) datasheet ---

class AcceleratorBurstCannonProfile(WeaponProfile):
    name = "Accelerator Burst Cannon"
    weapon_type = RANGED
    range_in = 18
    attacks = 4
    strength = 6
    ap = -1
    damage = 1


class ArmouredHullProfile(WeaponProfile):
    name = "Armoured Hull"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = 0
    damage = 1


class DevilfishTwinPulseCarbineProfile(WeaponProfile):
    """Same printed name/stats as the existing TwinPulseCarbineProfile
    (Strike Team's Unselected Profiles / Gun Drone), EXCEPT its BS: that
    class hardcodes a "5+" ballistic_skill override, correct there because
    it's worse than its usual (BS4+) Fire Warrior/Stealth Suit wielder.
    Devilfish's own printed BS for this weapon is 4+ - matching the
    Devilfish's own BS4+ exactly - so it needs NO override here (None means
    "use the model's own BS", per WeaponProfile's own docstring); reusing
    the other class as-is would have silently forced the wrong (worse) BS
    onto this datasheet. Needs its own class rather than just omitting the
    override on the existing one, since Gun Drone/Strike Team's own copy of
    this weapon genuinely does need that override to stay correct."""
    name = "Twin Pulse Carbine"
    weapon_type = RANGED
    range_in = 20
    attacks = 2
    strength = 5
    ap = 0
    damage = 1
    assault = True
    twin_linked = True


# Devilfish's "Unselected Profiles" - same documented gap as every other
# T'au datasheet's alternates (see CLAUDE.md): the actual wargear-swap rule
# text hasn't been given, only these reference profiles (its own Twin Pulse
# Carbine is the same DevilfishTwinPulseCarbineProfile above, not redefined
# here - identical stats on both listings).

class SeekerMissileProfile(WeaponProfile):
    """Printed Damage is "D6+1" - unused (no wargear option wires it in
    yet), same as every other Unselected Profile in this file.
    `damage_notation` set to D6(bonus=1) for the same forward-looking reason
    as FusionBlasterProfile's own note; `damage` stays the same placeholder
    (6+1=7) for grouping/preview purposes only."""
    name = "Seeker Missile"
    weapon_type = RANGED
    range_in = 48
    attacks = 1
    strength = 14
    ap = -3
    damage = 7  # preview/grouping placeholder only - see class docstring
    damage_notation = D6(bonus=1)
    one_shot = True


class SmartMissileSystemProfile(WeaponProfile):
    """Genuinely live: Devilfish's real wargear text ("This model's 2 twin
    pulse carbines can be replaced with 2 smart missile systems", official
    app screenshot) wires this in, see game/factions/tau_empire.py's
    DEVILFISH_CARBINES_TO_SMS."""
    name = "Smart Missile System"
    weapon_type = RANGED
    range_in = 30
    attacks = 3
    strength = 5
    ap = 0
    damage = 1
    indirect_fire = True


# --- Ghostkeel Battlesuit (T'au Empire) datasheet ---

class FusionColliderProfile(WeaponProfile):
    """Printed Damage is "D6". Docstring correction: this previously claimed
    to be unused/superseded by TwinFusionBlasterProfile - that was itself
    stale/wrong. The real datasheet (official app, screenshot) confirms
    Fusion Collider actually IS this model's own baseline weapon
    (_GHOSTKEEL_LOADOUT, game/factions/tau_empire.py); the Cyclic Ion Raker
    is the alternative, reachable via GHOSTKEEL_FUSION_TO_ION_RAKER's
    wargear swap - the previous belief had the two roles backwards."""
    name = "Fusion Collider"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 12
    ap = -4
    damage = 6  # preview/grouping placeholder only - see class docstring
    damage_notation = D6()
    melta = 2


class TwinTauFlamerProfile(WeaponProfile):
    """Same stats as the plain T'au Flamer (TauFlamerProfile above) plus
    [TWIN-LINKED] and a different printed name ("Twin T'au Flamer") - needs
    its own class since two classes can't share a name/stats. Genuinely
    live: this is Ghostkeel Battlesuit's own baseline weapon (per the real
    datasheet, official app screenshot - see _GHOSTKEEL_LOADOUT,
    game/factions/tau_empire.py), not a Crisis Starscythe wargear result as
    an earlier, pre-screenshot guess here assumed (Crisis Starscythe's own
    wargear swaps use the plain, non-twin-linked TauFlamerProfile instead -
    see STARSCYTHE_BURST_TO_FLAMER). Reachable the other way on Ghostkeel
    too, via its own wargear swaps (GHOSTKEEL_FLAMER_TO_FUSION_BLASTER/
    GHOSTKEEL_FLAMER_TO_BURST_CANNON). Dice-notation Attacks
    (attacks_notation) works exactly like TauFlamerProfile's own - see its
    docstring and ShootingController/FightController's
    _begin_resolution()/_continue_resolution_with_attacks()."""
    name = "Twin T'au Flamer"
    weapon_type = RANGED
    range_in = 12
    attacks = 6  # preview/leftover placeholder only - see class docstring
    attacks_notation = D6()
    strength = 4
    ap = 0
    damage = 1
    ignores_cover = True
    torrent = True
    twin_linked = True


class GhostkeelFistsProfile(WeaponProfile):
    name = "Ghostkeel Fists"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = 0
    damage = 2


# Ghostkeel's "Unselected Profiles" - same documented gap as every other
# T'au datasheet's alternates (see CLAUDE.md): the actual wargear-swap rule
# text hasn't been given, only these reference profiles (all alternates to
# the Fusion Collider primary weapon slot). Cyclic Ion Raker below is the
# one EXCEPTION - it's not a wargear swap at all (see its own docstring).

class CyclicIonRakerStandardProfile(WeaponProfile):
    """The Cyclic Ion Raker's default firing mode - this is the instance
    actually carried by the Ghostkeel Battlesuit (_GHOSTKEEL_LOADOUT,
    game/factions/tau_empire.py). Its overcharge_profile links to the
    Overcharge mode below: real 40k treats these as ONE weapon with two
    selectable firing modes (chosen at the point of shooting, like a
    Plasma weapon's Supercharge), not a wargear swap - giving the model
    both as separate weapon instances would incorrectly let it fire twice
    in one Shooting activation. ShootingController.weapon_eligibility()/
    choose_weapon(overcharge=True) offer Overcharge as a second button next
    to this weapon's normal one instead."""
    name = "Cyclic Ion Raker - Standard"
    weapon_type = RANGED
    range_in = 36
    attacks = 6
    strength = 7
    ap = -1
    damage = 2


class CyclicIonRakerOverchargeProfile(WeaponProfile):
    """Not a standalone loadout choice - only ever instantiated on demand by
    ShootingController.choose_weapon(overcharge=True), never placed directly
    in a model's weapons list. See CyclicIonRakerStandardProfile's own
    docstring."""
    name = "Cyclic Ion Raker - Overcharge"
    weapon_type = RANGED
    range_in = 36
    attacks = 6
    strength = 8
    ap = -2
    damage = 3
    hazardous = True


CyclicIonRakerStandardProfile.overcharge_profile = CyclicIonRakerOverchargeProfile


class TwinBurstCannonProfile(WeaponProfile):
    name = "Twin Burst Cannon"
    weapon_type = RANGED
    range_in = 18
    attacks = 4
    strength = 5
    ap = 0
    damage = 1
    twin_linked = True


class TwinFusionBlasterProfile(WeaponProfile):
    """Printed Damage is "D6" - genuinely live (part of Ghostkeel
    Battlesuit's actual baseline loadout, game/factions/tau_empire.py's
    _GHOSTKEEL_LOADOUT - the docstring here previously claimed it was an
    unused reference profile like FusionBlasterProfile's own plain "D6";
    that was stale/wrong, found via a user report that Ghostkeel's damage
    was being silently resolved with no visible roll). `damage_notation`
    makes this a real, visible D6 roll (game/dice_notation.py's
    DiceNotationRoll, wired into DamageAllocationSession) once per attack
    actually allocated to a model, instead of the earlier "store the die's
    max value as a fixed int, never roll it" placeholder; `damage` itself
    stays at that same placeholder value purely for grouping (_attack_key)
    and the Save-roll's damage_per_failure preview (suppressed to None
    whenever damage_notation is set - see shooting.py/fight.py's
    _resolve_wounds())."""
    name = "Twin Fusion Blaster"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 9
    ap = -4
    damage = 6  # preview/grouping placeholder only - see class docstring
    damage_notation = D6()
    melta = 2
    twin_linked = True


# --- Commander in Coldstar Battlesuit (T'au Empire) datasheet ---
# Battlesuit fists isn't redefined here - Crisis Starscythe's own
# CrisisBattlesuitFistsProfile above (A3/S5/AP0/D1) has identical stats on
# this datasheet too (WS4+ needs no override, deferring to this model's own
# weapon_skill - see ColdstarCommanderProfile's own docstring, game/units.py).

class HighOutputBurstCannonProfile(WeaponProfile):
    """Genuinely live: this model's own baseline weapon (see
    game/factions/tau_empire.py's _COLDSTAR_COMMANDER_LOADOUT)."""
    name = "High-output Burst Cannon"
    weapon_type = RANGED
    range_in = 18
    attacks = 8
    strength = 5
    ap = 0
    damage = 1


# Coldstar Commander's "Unselected Profiles" - same documented gap as every
# other T'au datasheet's alternates (see CLAUDE.md): no "Wargear Options"
# swap-rule text was given for this datasheet (only these reference
# profiles, plus a separate "Abilities" list of named Support Systems -
# Battlesuit Support System/Shield Generator/Weapon Support System - with no
# "can be equipped with" text tying them to a slot), so none of these are
# wired into any WargearOption yet. Burst cannon/Fusion blaster/T'au flamer
# reuse the existing BurstCannonProfile/FusionBlasterProfile/TauFlamerProfile
# classes as-is (each already defers BS to the wielder, or already matches
# this model's own BS3+); Twin pulse carbine/the second Missile pod entry
# reuse the existing TwinPulseCarbineProfile/MissilePodProfile classes as-is
# (both already hardcode the BS5+ this datasheet's own copies print).

class AirburstingFragmentationProjectorProfile(WeaponProfile):
    """Printed Attacks is "D6" - unused (no wargear option wires it in yet),
    same as every other Unselected Profile in this file. `attacks_notation`
    set to D6() for the same forward-looking reason as TauFlamerProfile's
    own note; `attacks` stays at the same placeholder (6) for grouping/
    preview purposes only."""
    name = "Airbursting Fragmentation Projector"
    weapon_type = RANGED
    range_in = 24
    attacks = 6  # preview/grouping placeholder only - see class docstring
    attacks_notation = D6()
    strength = 3
    ap = 0
    damage = 1
    blast = 1  # plain [BLAST] (no explicit X) is X=1, see WeaponProfile.blast
    indirect_fire = True


class CyclicIonBlasterStandardProfile(WeaponProfile):
    """Unused reference profile (see class-group note above) - not the same
    weapon as Ghostkeel's own Cyclic Ion Raker (different name, different
    stats), so it needs its own class rather than reusing
    CyclicIonRakerStandardProfile. Its own overcharge_profile links to the
    Overcharge mode below, same one-weapon-two-firing-modes relationship as
    the Ion Raker's (see CyclicIonRakerStandardProfile's own docstring) -
    kept even though unused, so the pairing is correct the moment a wargear
    option ever wires this in."""
    name = "Cyclic Ion Blaster - Standard"
    weapon_type = RANGED
    range_in = 18
    attacks = 3
    strength = 7
    ap = -1
    damage = 1


class CyclicIonBlasterOverchargeProfile(WeaponProfile):
    """Not a standalone loadout choice - see CyclicIonBlasterStandardProfile
    above and CyclicIonRakerStandardProfile's own docstring for why."""
    name = "Cyclic Ion Blaster - Overcharge"
    weapon_type = RANGED
    range_in = 18
    attacks = 3
    strength = 8
    ap = -2
    damage = 2
    hazardous = True


CyclicIonBlasterStandardProfile.overcharge_profile = CyclicIonBlasterOverchargeProfile


class PlasmaRifleProfile(WeaponProfile):
    """Unused reference profile (see class-group note above)."""
    name = "Plasma Rifle"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 8
    ap = -3
    damage = 3


class ColdstarMissilePodProfile(WeaponProfile):
    """Same printed name/stats as the existing MissilePodProfile (Strike/
    Breacher Team's Unselected Profile), EXCEPT its BS: that class hardcodes
    a "5+" ballistic_skill override, correct there for a BS4+ Fire Warrior
    wielder. This datasheet's own first "Missile pod" listing prints BS3+ -
    matching this model's own ballistic_skill exactly - so it needs no
    override (None means "use the model's own BS"); reusing the other class
    as-is would have silently forced the wrong (worse) BS onto this
    datasheet, same reasoning as DevilfishTwinPulseCarbineProfile's own note.
    Unused reference profile (see class-group note above)."""
    name = "Missile Pod"
    weapon_type = RANGED
    range_in = 30
    attacks = 2
    strength = 7
    ap = -1
    damage = 2


# --- Riptide Battlesuit (T'au Empire) datasheet ---
# Twin fusion blaster / Missile pod aren't redefined here - both already
# exist with stats identical to this datasheet's own printed copies, and
# both already resolve their BS correctly for this wielder:
# TwinFusionBlasterProfile (12"/A1/S9/AP-4/D D6, [MELTA 2], [TWIN-LINKED])
# defers BS to the model, whose own BS4+ is exactly what this datasheet
# prints for it; MissilePodProfile hardcodes a "5+" ballistic_skill
# override, which here is CORRECT rather than wrong - this datasheet's
# Missile pod prints BS5+ while the model's own BS is 4+, so the override
# is doing real work (the exact inverse of the ColdstarMissilePodProfile
# case, where the printed BS matched the model's own and the override had
# to be dropped).

class HeavyBurstCannonProfile(WeaponProfile):
    """Genuinely live: half of this model's own baseline loadout (see
    game/factions/tau_empire.py's _RIPTIDE_LOADOUT). BS4+ matches this
    model's own ballistic_skill, so no per-weapon override is needed."""
    name = "Heavy Burst Cannon"
    weapon_type = RANGED
    range_in = 36
    attacks = 12
    strength = 6
    ap = -1
    damage = 2


class TwinPlasmaRifleProfile(WeaponProfile):
    """Genuinely live: the other half of this model's baseline loadout.
    A distinct class from the existing PlasmaRifleProfile (18"/A1/S8/AP-3/D3,
    an unused Crisis reference profile with identical numbers) because this
    one carries [TWIN-LINKED] - same "identical stat line but a different
    keyword/BS makes it a different weapon" reasoning as
    DevilfishTwinPulseCarbineProfile's own note."""
    name = "Twin Plasma Rifle"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 8
    ap = -3
    damage = 3
    twin_linked = True


class RiptideFistsProfile(WeaponProfile):
    """Genuinely live: this model's own melee weapon. WS5+ matches this
    model's own weapon_skill (fight.py always reads model.profile.
    weapon_skill directly - there is no per-weapon WS override mechanism, so
    it only ever needs to line up; see CrisisStarscytheShasUiProfile's own
    docstring)."""
    name = "Riptide Fists"
    weapon_type = MELEE
    range_in = 2  # melee: the same nominal value every other melee profile here uses (WeaponProfile's own default is the RANGED 24")
    attacks = 6
    strength = 6
    ap = 0
    damage = 2


class IonAcceleratorStandardProfile(WeaponProfile):
    """The Ion accelerator's default firing mode - a real wargear swap
    option on this datasheet (it replaces the Heavy burst cannon, see
    RIPTIDE_BURST_TO_ION_ACCELERATOR), unlike most other T'au "Unselected
    Profiles" which stay unwired. Its overcharge_profile links to the
    Overcharge mode below: real 40k treats these as ONE weapon with two
    selectable firing modes rather than two weapons, exactly like the
    Cyclic Ion Raker - see CyclicIonRakerStandardProfile's own docstring for
    why giving the model both as separate instances would be wrong."""
    name = "Ion Accelerator - Standard"
    weapon_type = RANGED
    range_in = 72
    attacks = 6
    strength = 9
    ap = -2
    damage = 3


class IonAcceleratorOverchargeProfile(WeaponProfile):
    """Not a standalone loadout choice - only ever instantiated on demand by
    ShootingController.choose_weapon(overcharge=True), never placed directly
    in a model's weapons list. See IonAcceleratorStandardProfile's own
    docstring."""
    name = "Ion Accelerator - Overcharge"
    weapon_type = RANGED
    range_in = 72
    attacks = 6
    strength = 10
    ap = -3
    damage = 4
    hazardous = True


IonAcceleratorStandardProfile.overcharge_profile = IonAcceleratorOverchargeProfile


class TwinSmartMissileSystemProfile(WeaponProfile):
    """Unused reference profile: this datasheet lists it under "Unselected
    Profiles" with no "can be equipped with" text tying it to a slot, so it
    is not wired into any WargearOption (same documented gap as every other
    T'au datasheet's alternates, see CLAUDE.md).

    A distinct class from the existing SmartMissileSystemProfile (30"/A3/S5/
    AP0/D1, [INDIRECT FIRE], genuinely live on the Devilfish) because this
    one also carries [TWIN-LINKED]."""
    name = "Twin Smart Missile System"
    weapon_type = RANGED
    range_in = 30
    attacks = 3
    strength = 5
    ap = 0
    damage = 1
    indirect_fire = True
    twin_linked = True


# --- Pathfinder Team (T'au Empire) datasheet ---
# Pulse carbine / Pulse pistol / Close combat weapon / Twin pulse carbine /
# Missile pod aren't redefined here - all five already exist with stats
# identical to this datasheet's own printed copies, and all five already
# resolve BS/WS correctly for these wielders: PulseCarbineProfile,
# PulsePistolProfile and TauCloseCombatWeaponProfile defer to the model
# (BS4+/WS5+, exactly what this datasheet prints), while
# TwinPulseCarbineProfile and MissilePodProfile hardcode the "5+" this
# datasheet also prints for them (a BS5+ drone weapon on a BS4+ wielder -
# the same case the Riptide's own Missile Drones are).

class SemiAutomaticGrenadeLauncherEmpProfile(WeaponProfile):
    """The Semi-automatic grenade launcher's EMP firing mode. Its
    overcharge_profile links to the fusion mode below: the datasheet prints
    them as two "➤" sub-profiles of ONE weapon entry, i.e. one weapon with
    two selectable firing modes, exactly like the Cyclic Ion Raker and the
    Riptide's Ion Accelerator - see CyclicIonRakerStandardProfile's own
    docstring for why giving a model both as separate instances would be
    wrong (it would let one weapon fire twice in a single activation).

    NOTE on the field name: `overcharge_profile` is this engine's generic
    "alternate firing mode" hook, not specifically a hazardous overcharge
    (its own comment on WeaponProfile says so). The two modes here are
    peers - EMP is the anti-vehicle mode, fusion the high-damage one -
    with neither being a drawback-carrying upgrade of the other, so which
    of the two is the "standard" instance is arbitrary; EMP is used because
    the datasheet lists it first."""
    name = "Semi-automatic Grenade Launcher - EMP"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 3
    ap = 0
    damage = 1
    anti = ("VEHICLE", 4)  # [ANTI-VEHICLE 4+] - rule 24.03
    devastating_wounds = True  # rule 24.10


class SemiAutomaticGrenadeLauncherFusionProfile(WeaponProfile):
    """Not a standalone loadout choice - only ever instantiated on demand by
    ShootingController.choose_weapon(overcharge=True), never placed directly
    in a model's weapons list. See
    SemiAutomaticGrenadeLauncherEmpProfile's own docstring."""
    name = "Semi-automatic Grenade Launcher - Fusion"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 6
    ap = -1
    damage = 3


SemiAutomaticGrenadeLauncherEmpProfile.overcharge_profile = SemiAutomaticGrenadeLauncherFusionProfile


class DroneBurstCannonProfile(WeaponProfile):
    """Genuinely live: the weapon a Recon Drone grants its bearer (see
    game/drones.py's recon_drone_gear()). A distinct class from the existing
    BurstCannonProfile (18"/A4/S5/AP0/D1, same numbers) because this one
    prints BS5+ - a drone's own worse BS, which must NOT defer to the
    BS4+ Pathfinder carrying it. Same reasoning as
    DevilfishTwinPulseCarbineProfile's own note, in the opposite direction."""
    name = "Drone Burst Cannon"
    weapon_type = RANGED
    range_in = 18
    attacks = 4
    ballistic_skill = "5+"
    strength = 5
    ap = 0
    damage = 1


# --- The Twin Lance (T'au Empire) datasheet -------------------------------
# Three of this datasheet's weapons print BOTH a ranged and a melee profile
# under the same name (Fusion eliminator, XV pulse pistol, Ion scattercannon).
# They are separate WeaponProfile classes here because this engine keys a
# weapon's type off `weapon_type`, and a model carries both entries at once -
# the printed datasheet does the same thing, listing each in both tables.
#
# This is also the first datasheet whose melee weapons DISAGREE about WS
# (4+/3+/4+ on one stat line), so each melee class carries its own
# `weapon_skill` override - the per-weapon mechanism added for the Ork Power
# Klaw, used here for the first time on more than one weapon of a unit. The
# model's own WS is set to the most common of them; the overrides make that
# choice irrelevant to results, only to which entries need one.

class FusionEliminatorProfile(WeaponProfile):
    """Ranged half. Printed Damage "D6" - a real, visible roll via
    damage_notation, same as every other dice-notation Damage in this file;
    `damage` stays the grouping/preview placeholder."""
    name = "Fusion Eliminator"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 10
    ap = -4
    damage = 6  # preview/grouping placeholder only - see damage_notation
    damage_notation = D6()
    melta = 2


class FusionEliminatorMeleeProfile(WeaponProfile):
    """Melee half: printed Damage "D6+2" - DiceNotation carries the flat
    bonus, so this is D6 plus 2, not a separate addition the caller has to
    remember. [EXTRA ATTACKS] (24.11) means it is made IN ADDITION to the
    model's other melee weapon, not instead of it."""
    name = "Fusion Eliminator"
    weapon_type = MELEE
    range_in = 2  # melee: the same nominal value every other melee profile here uses (WeaponProfile's own default is the RANGED 24")
    attacks = 1
    weapon_skill = "4+"
    strength = 10
    ap = -4
    damage = 8  # preview/grouping placeholder only (D6+2's maximum) - see damage_notation
    damage_notation = D6(bonus=2)
    extra_attacks = True


class TwinPulseBlasterProfile(WeaponProfile):
    """The weapon an MV15 Gun Drone brings. Its printed BS5+ is the drone's
    own, worse than the BS2+ wielder's, so the override is doing real work -
    same case as the Riptide's Missile Drone."""
    name = "Twin Pulse Blaster"
    weapon_type = RANGED
    range_in = 10
    attacks = 2
    ballistic_skill = "5+"
    strength = 6
    ap = -1
    damage = 1
    assault = True
    twin_linked = True


class ShardstormBurstSystemProfile(WeaponProfile):
    """Printed Attacks "D6" - a real roll per attacking model before the Hit
    roll (attacks_notation), not a fixed number; `attacks` is only the
    preview/grouping leftover. [PISTOL] (24.27) lets it fire while the unit
    is within Engagement Range."""
    name = "Shardstorm Burst System"
    weapon_type = RANGED
    range_in = 18
    attacks = 6  # preview/grouping placeholder only - see attacks_notation
    attacks_notation = D6()
    strength = 5
    ap = 0
    damage = 1
    pistol = True


class XvPulsePistolProfile(WeaponProfile):
    """Ranged half. [RAPID FIRE 2] (24.30) doubles down within half range.

    NOT [PISTOL], despite the name - the printed keyword column of
    rules/tau_empire/The Twin Lance.md reads "rapid fire 2" and nothing else,
    while the Shardstorm burst system one row above does print "pistol". The
    flag sat here (with a docstring reasoning from the weapon's name that it
    "lets it fire out of Engagement Range") until the keyword sweep put the
    two columns side by side."""
    name = "XV Pulse Pistol"
    weapon_type = RANGED
    range_in = 12
    attacks = 2
    strength = 6
    ap = -1
    damage = 2
    rapid_fire = 2


class XvPulsePistolMeleeProfile(WeaponProfile):
    """Melee half - the only weapon on this datasheet whose WS (3+) is
    better than the other two melee entries', hence its own override. NOT
    [EXTRA ATTACKS]: unlike the Fusion eliminator and Ion scattercannon
    melee profiles, this one is a normal melee weapon and competes with them
    for the model's single non-EXTRA-ATTACKS selection (rule 04.01)."""
    name = "XV Pulse Pistol"
    weapon_type = MELEE
    range_in = 2  # melee: the same nominal value every other melee profile here uses (WeaponProfile's own default is the RANGED 24")
    attacks = 4
    weapon_skill = "3+"
    strength = 6
    ap = -1
    damage = 2


class IonScattercannonStandardProfile(WeaponProfile):
    """The Ion scattercannon's default firing mode; its overcharge_profile
    links to the Hazardous mode below. One weapon with two selectable modes,
    exactly like the Cyclic Ion Raker and the Riptide's Ion Accelerator -
    see CyclicIonRakerStandardProfile's own docstring for why both must not
    be handed to the model as separate instances.

    The datasheet prints overcharge FIRST and standard second; standard is
    the base instance here because it is the mode with no drawback, matching
    every other ion weapon in this file."""
    name = "Ion Scattercannon - Standard"
    weapon_type = RANGED
    range_in = 18
    attacks = 4
    strength = 7
    ap = -2
    damage = 2
    rapid_fire = 2


class IonScattercannonOverchargeProfile(WeaponProfile):
    """Not a standalone loadout choice - only ever instantiated on demand by
    ShootingController.choose_weapon(overcharge=True). See
    IonScattercannonStandardProfile's own docstring."""
    name = "Ion Scattercannon - Overcharge"
    weapon_type = RANGED
    range_in = 18
    attacks = 4
    strength = 8
    ap = -3
    damage = 3
    rapid_fire = 2
    hazardous = True


IonScattercannonStandardProfile.overcharge_profile = IonScattercannonOverchargeProfile


class IonScattercannonMeleeProfile(WeaponProfile):
    """Melee half - [EXTRA ATTACKS] (24.11), so it is swung in addition to
    whichever normal melee weapon the model selects."""
    name = "Ion Scattercannon"
    weapon_type = MELEE
    range_in = 2  # melee: the same nominal value every other melee profile here uses (WeaponProfile's own default is the RANGED 24")
    attacks = 3
    weapon_skill = "4+"
    strength = 7
    ap = -2
    damage = 2
    extra_attacks = True


# --- Commander Farsight (T'au Empire) datasheet ---------------------------

class HighIntensityPlasmaRifleProfile(WeaponProfile):
    """Genuinely live: this model's own ranged weapon. Its printed BS2+
    matches the model's own, so no per-weapon override is needed - unlike
    the plain PlasmaRifleProfile above (a Crisis reference profile with a
    different stat line entirely: 18"/S8/AP-3/D3 vs this one's 24"/A2)."""
    name = "High-intensity Plasma Rifle"
    weapon_type = RANGED
    range_in = 24
    attacks = 2
    strength = 8
    ap = -3
    damage = 3


# The Dawn Blade's two "➤" sub-profiles are modeled as two separate melee
# WeaponProfiles rather than through the overcharge_profile mechanism the
# two-mode RANGED weapons use (Ion Accelerator, Cyclic Ion Raker, Ion
# Scattercannon). That is not a shortcut - it is what rule 04.01 already
# does for free.
#
# choose_weapon(overcharge=True) only exists in game/shooting.py, because a
# ranged weapon has no other rule stopping a model firing every gun it
# carries: without a mode mechanism, two instances of one weapon would let
# it shoot twice. Melee is the opposite. 04.01 lets a model attack with only
# ONE of its melee weapons per fight (game/fight.py's _lock_other_melee_
# weapon()/_melee_locked_out(), [EXTRA ATTACKS] excepted), so two melee
# profiles under one name already behave exactly as "pick a mode": the
# player is offered both, picking either locks out the other for that
# activation. Adding a parallel melee mode mechanism would duplicate a
# restriction the rules already impose.

class DawnBladeStrikeProfile(WeaponProfile):
    """The Dawn Blade's Strike mode - few, heavy blows. WS2+ matches this
    model's own, so no per-weapon override."""
    name = "Dawn Blade - Strike"
    weapon_type = MELEE
    range_in = 2  # melee: the same nominal value every other melee profile here uses (WeaponProfile's own default is the RANGED 24")
    attacks = 4
    strength = 10
    ap = -2
    damage = 3


class DawnBladeSweepProfile(WeaponProfile):
    """The Dawn Blade's Sweep mode - many light blows. See the note above
    on why this is a sibling weapon rather than a firing mode."""
    name = "Dawn Blade - Sweep"
    weapon_type = MELEE
    range_in = 2  # melee: the same nominal value every other melee profile here uses (WeaponProfile's own default is the RANGED 24")
    attacks = 8
    strength = 6
    ap = -1
    damage = 1


# --- Pathfinder Team special weapons (T'au Empire) ------------------------
# Both print BS5+ while a Pathfinder's own BS is 4+, so both carry the
# override - and here it is the WEAPON that is less accurate than its
# wielder, not a drone's own worse skill (the Riptide's Missile Drone case).
# Reading the printed value as-is either way, same discipline as everywhere
# else in this file.

class RailRifleProfile(WeaponProfile):
    """Genuinely live: up to 3 Pathfinders can carry one in place of their
    Pulse carbine (see game/factions/tau_empire.py's
    PATHFINDER_CARBINE_TO_RAIL_RIFLE)."""
    name = "Rail Rifle"
    weapon_type = RANGED
    range_in = 30
    attacks = 1
    ballistic_skill = "5+"
    strength = 10
    ap = -4
    damage = 3
    devastating_wounds = True  # rule 24.10
    heavy = True               # rule 24.16


class IonRifleStandardProfile(WeaponProfile):
    """The Ion rifle's default firing mode; its overcharge_profile links to
    the Hazardous mode below. One weapon with two selectable modes, like
    every other ion weapon here - see CyclicIonRakerStandardProfile's own
    docstring for why both must not be handed to a model at once.

    The only item the official points list prices for this datasheet
    ("per Ion rifle 5 pts"), which is what corroborates it as a real
    wargear option rather than a guess."""
    name = "Ion Rifle - Standard"
    weapon_type = RANGED
    range_in = 30
    attacks = 3
    ballistic_skill = "5+"
    strength = 7
    ap = -1
    damage = 1
    heavy = True


class IonRifleOverchargeProfile(WeaponProfile):
    """Not a standalone loadout choice - only ever instantiated on demand by
    ShootingController.choose_weapon(overcharge=True). See
    IonRifleStandardProfile's own docstring."""
    name = "Ion Rifle - Overcharge"
    weapon_type = RANGED
    range_in = 30
    attacks = 3
    ballistic_skill = "5+"
    strength = 8
    ap = -2
    damage = 2
    hazardous = True
    heavy = True


IonRifleStandardProfile.overcharge_profile = IonRifleOverchargeProfile


# --- Kroot Shapers (T'au Empire): Flesh / Trail / War Shaper datasheets ---
#
# All three print WS 2+ and BS 4+ on every one of their own weapon rows, so
# those live on the UnitProfile (game/units.py) rather than as per-weapon
# overrides - the per-weapon `weapon_skill`/`ballistic_skill` hooks are for a
# model whose rows DISAGREE with each other, which is The Twin Lance, not
# these. The Kroot rifle and Kroot pistol they also carry already exist above
# with exactly the printed numbers and are reused rather than re-declared.

class KrootScattergunProfile(WeaponProfile):
    name = "Kroot Scattergun"
    weapon_type = RANGED
    range_in = 12
    attacks = 2
    strength = 4
    ap = 0
    damage = 1
    assault = True


class TwinRitualisticBladesProfile(WeaponProfile):
    """[TWIN-LINKED] despite "twin" also being in the printed name - the
    keyword is printed on the row as well, so this is not the Wave Serpent
    case where the name alone carries it."""
    name = "Twin Ritualistic Blades"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = -1
    damage = 1
    twin_linked = True


class ShapersBladeProfile(WeaponProfile):
    """Printed identically on the Trail Shaper and the War Shaper, so it is
    ONE class shared by both datasheets rather than a copy each."""
    name = "Shaper's Blade"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = 0
    damage = 1


class DartBowAndTriBladeProfile(WeaponProfile):
    """Printed Attacks is "D3+1", hence attacks_notation - `attacks` below is
    only the grouping/preview value, the real count is rolled per attacking
    model (see WeaponProfile.attacks_notation's own note).

    It prints [ASSAULT] and [HEAVY] together, which is not a contradiction:
    24.16 is a bonus for not moving, 24.04 permits shooting after Advancing,
    and this engine already evaluates them independently."""
    name = "Dart-bow and Tri-blade"
    weapon_type = RANGED
    range_in = 24
    attacks = 3  # preview only - see attacks_notation
    attacks_notation = D3(bonus=1)
    strength = 4
    ap = 0
    damage = 2
    anti = ("INFANTRY", 3)
    assault = True
    heavy = True


class BladestaveAndPreyHookProfile(WeaponProfile):
    name = "Bladestave and Prey-hook"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = -1
    damage = 2
    lethal_hits = True


# --- Ethereal (T'au Empire) datasheet ---

class HonourStaveProfile(WeaponProfile):
    name = "Honour Stave"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 5
    ap = 0
    damage = 1


# --- Darkstrider (T'au Empire) datasheet ---

class ShadeProfile(WeaponProfile):
    """His BS 2+ is better than the profile's own, so unlike the Kroot Shapers
    this one DOES need the per-weapon override - his close combat weapon is
    WS 4+ and the two rows disagree."""
    name = "Shade"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    ballistic_skill = "2+"
    strength = 5
    ap = 0
    damage = 2
    assault = True


class DarkstriderCloseCombatWeaponProfile(WeaponProfile):
    """Same printed name as the other Close Combat Weapon classes but A3/S3 -
    needs its own class, same reasoning as every other one in this file."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 3
    ap = 0
    damage = 1


# --- Firesight Team (T'au Empire) datasheet ---

class LongshotPulseRiflesProfile(WeaponProfile):
    """Plural on the printed datasheet: the sniper drones' rifles and the
    Marksman's are ONE weapon row, because the Designer's Note makes the drones
    part of the single Marksman model rather than models of their own."""
    name = "Longshot Pulse Rifles"
    weapon_type = RANGED
    range_in = 36
    attacks = 3
    strength = 5
    ap = -1
    damage = 2
    heavy = True
    precision = True


class FiresightCloseCombatWeaponsProfile(WeaponProfile):
    """Printed name is plural ("Close combat weapons"), for the same reason the
    rifles are - so it is kept as printed rather than normalised to the
    singular the other classes use."""
    name = "Close Combat Weapons"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    weapon_skill = "5+"
    strength = 3
    ap = 0
    damage = 1


# --- Kroot Lone-Spear (T'au Empire) datasheet ---

class KrootLongGunProfile(WeaponProfile):
    name = "Kroot Long Gun"
    weapon_type = RANGED
    range_in = 36
    attacks = 1
    ballistic_skill = "3+"
    strength = 6
    ap = -2
    damage = 3
    heavy = True
    precision = True


class BlastJavelinProfile(WeaponProfile):
    """Printed Attacks "D6" - see attacks_notation. Its BS 4+ differs from the
    Kroot long gun's 3+ on the same model, so both carry an override."""
    name = "Blast Javelin"
    weapon_type = RANGED
    range_in = 18
    attacks = 6  # preview only - see attacks_notation
    attacks_notation = D6()
    ballistic_skill = "4+"
    strength = 10
    ap = -2
    damage = 2
    assault = True
    blast = 1  # plain [BLAST] (no explicit X) is X=1


class HuntingJavelinProfile(WeaponProfile):
    name = "Hunting Javelin"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 4
    ap = -1
    damage = 1
    lance = True


class KalamandrasBiteProfile(WeaponProfile):
    """The mount's own bite: [EXTRA ATTACKS] (24.11), so it is swung IN
    ADDITION to whichever other melee weapon the rider chooses, and 04.01's
    one-melee-weapon lock does not apply to it."""
    name = "Kalamandra's Bite"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    weapon_skill = "4+"
    strength = 5
    ap = -1
    damage = 1
    extra_attacks = True


class LoneSpearCloseCombatWeaponProfile(WeaponProfile):
    """Same printed name as the other Close Combat Weapon classes, A3/S4/WS3+
    on this datasheet - its own class, same reasoning as the rest."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 4
    ap = 0
    damage = 1


# --- Commander Shadowsun (T'au Empire) datasheet ---
#
# Her pulse pistol and battlesuit fists rows print the numbers the existing
# PulsePistolProfile and CrisisBattlesuitFistsProfile already carry, so those
# are reused; only the three weapons nothing else in the army prints are new.

class FlechetteLauncherProfile(WeaponProfile):
    name = "Flechette Launcher"
    weapon_type = RANGED
    range_in = 18
    attacks = 5
    strength = 3
    ap = 0
    damage = 1


class HighEnergyFusionBlasterProfile(WeaponProfile):
    """Printed Damage "D6" - hence damage_notation; `damage` below is the
    preview value, same arrangement as every other dice-damage weapon here."""
    name = "High-energy Fusion Blaster"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 10
    ap = -4
    damage = 6  # preview only - see damage_notation
    damage_notation = D6()
    melta = 2


class LightMissilePodProfile(WeaponProfile):
    """A THIRD weapon printed as some flavour of "missile pod" (after the
    Crisis suits' 30"/S7/AP-1 one and the Riptide's drone-carried copy), with
    its own range and AP - so its own class, and the printed name is kept
    exactly rather than folded into the others."""
    name = "Light Missile Pod"
    weapon_type = RANGED
    range_in = 24
    attacks = 2
    strength = 7
    ap = 0
    damage = 2


# --- Kroot Hounds / Kroot Farstalkers (T'au Empire) ---

class RippingFangsProfile(WeaponProfile):
    """Printed identically on the Kroot Hounds datasheet and on the two Kroot
    Hounds inside a Kroot Farstalkers unit, so it is ONE class shared by both -
    unlike their MODEL profiles, whose Leadership differs (8+ alone, 7+ inside
    the Farstalkers)."""
    name = "Ripping Fangs"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 3
    ap = 0
    damage = 1


class FarstalkerFirearmProfile(KrootRifleProfile):
    """Every number is the Kroot rifle's; only the printed NAME differs. So it
    INHERITS rather than repeating them - the same arrangement the Wave
    Serpent's twin weapons and the Lokhust Lord's blade use, and the reason the
    test pins the two against EACH OTHER instead of against literals."""
    name = "Farstalker Firearm"


class TauTechRifleProfile(PulseRifleProfile):
    """Likewise the Pulse rifle's numbers under another name - 30"/A1/S5/AP0/
    D1/[RAPID FIRE 1], which is what a Kroot carrying T'au-issue kit should
    print."""
    name = "T'au-tech Rifle"


class DvorgiteSkinnerProfile(WeaponProfile):
    """BS "N/A" on the printed row, which per this repo's own recipe means
    [TORRENT] - and the row prints that keyword too, so the two agree."""
    name = "Dvorgite Skinner"
    weapon_type = RANGED
    range_in = 12
    attacks = 6  # preview only - see attacks_notation
    attacks_notation = D6()
    strength = 4
    ap = -1
    damage = 1
    ignores_cover = True
    torrent = True


class LondaxiTribalestProfile(WeaponProfile):
    name = "Londaxi Tribalest"
    weapon_type = RANGED
    range_in = 18
    attacks = 3
    ballistic_skill = "5+"
    strength = 7
    ap = -1
    damage = 1
    anti = ("VEHICLE", 4)
    devastating_wounds = True
    heavy = True


class RitualBladeProfile(WeaponProfile):
    """The Kill-broker's own blade. Same printed S/AP/D as the Shapers' blade
    but A3/WS3+ rather than A4/WS2+, so it needs its own class - the standing
    rule for a shared name with different numbers."""
    name = "Ritual Blade"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 5
    ap = 0
    damage = 1


# --- Vespid Stingwings (T'au Empire) datasheet ---

class NeutronBlasterProfile(WeaponProfile):
    name = "Neutron Blaster"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 5
    ap = -2
    damage = 2
    assault = True


class NeutronGrenadeLauncherProfile(WeaponProfile):
    name = "Neutron Grenade Launcher"
    weapon_type = RANGED
    range_in = 18
    attacks = 6  # preview only - see attacks_notation
    attacks_notation = D6()
    strength = 4
    ap = -1
    damage = 2
    anti = ("INFANTRY", 3)
    blast = 1  # plain [BLAST] (no explicit X) is X=1


class NeutronRailRifleProfile(WeaponProfile):
    """Not the Pathfinders' Rail rifle: 30" and S10/AP-4/D3 against that one's
    30"/S10/AP-4/D3 at BS5+ with [HEAVY]. The printed rows differ in skill and
    keywords, so this is its own class rather than a rename."""
    name = "Neutron Rail Rifle"
    weapon_type = RANGED
    range_in = 30
    attacks = 1
    strength = 10
    ap = -4
    damage = 3
    devastating_wounds = True


class StingwingClawsProfile(WeaponProfile):
    name = "Stingwing Claws"
    weapon_type = MELEE
    range_in = 2
    attacks = 1
    weapon_skill = "4+"
    strength = 4
    ap = -1
    damage = 1


# --- Krootox Riders / Krootox Rampagers (T'au Empire) ---

class RepeaterCannonProfile(WeaponProfile):
    name = "Repeater Cannon"
    weapon_type = RANGED
    range_in = 36
    attacks = 2
    strength = 7
    ap = -1
    damage = 2
    rapid_fire = 2


class TanglecannonProfile(WeaponProfile):
    """Printed Attacks "D6+1" - hence attacks_notation."""
    name = "Tanglecannon"
    weapon_type = RANGED
    range_in = 36
    attacks = 4  # preview only - see attacks_notation
    attacks_notation = D6(bonus=1)
    strength = 6
    ap = 0
    damage = 1
    blast = 1
    heavy = True


class KrootoxFistsProfile(WeaponProfile):
    """The Krootox Riders' version: [EXTRA ATTACKS] only."""
    name = "Krootox Fists"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 6
    ap = -1
    damage = 2
    extra_attacks = True


class RampagerKrootoxFistsProfile(KrootoxFistsProfile):
    """The RAMPAGERS' version. Identical numbers to the Riders' fists above
    and the same printed name, but it also prints [SUSTAINED HITS 1] - so it
    inherits and adds only the keyword, which is what keeps the shared numbers
    from drifting apart. The test pins the two against each other.

    Keeping the printed name means two classes share it; that is the same
    situation the several "Close Combat Weapon" classes are in, and it is
    exactly why each needs its own class rather than a shared instance."""
    sustained_hits = 1


class KrootPistolAndHuntingJavelinsProfile(WeaponProfile):
    """One printed weapon ROW combining two named weapons, so one class - the
    same reading the Kill-broker's "dart-bow and tri-blade" gets."""
    name = "Kroot Pistol and Hunting Javelins"
    weapon_type = RANGED
    range_in = 12
    attacks = 2
    strength = 4
    ap = 0
    damage = 1
    assault = True
    pistol = True


class RampagerCloseCombatWeaponProfile(WeaponProfile):
    """Printed as "Close combat weapon" on the weapon table, and as "hunting
    blades" on the Unit Composition line - the table is what carries the
    numbers, so the table's name is used. A3/S4/AP-1/[LANCE], which is neither
    of the other Kroot "Close Combat Weapon" classes."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 4
    ap = -1
    damage = 1
    lance = True


# --- Broadside Battlesuits (T'au Empire) datasheet ---

class HeavyRailRifleProfile(WeaponProfile):
    """The heaviest gun in the T'au list: S12/AP-4/D6+1 at 60".

    Not a bigger Rail rifle - the Pathfinders' (30"/A1/BS5+/S10/AP-4/D3,
    [DEVASTATING WOUNDS] [HEAVY]) and the Vespid's Neutron rail rifle share
    only the family name. Three printed rows, three classes."""
    name = "Heavy Rail Rifle"
    weapon_type = RANGED
    range_in = 60
    attacks = 2
    strength = 12
    ap = -4
    damage = 7  # preview only - see damage_notation
    damage_notation = D6(bonus=1)
    devastating_wounds = True
    heavy = True


class HighYieldMissilePodsProfile(WeaponProfile):
    """Printed PLURAL, and it is one weapon row rather than two missile pods -
    the same reading the Firesight Team's "longshot pulse rifles" gets. A6 and
    [TWIN-LINKED] is what distinguishes it from the ordinary missile pod, which
    is A2 and neither."""
    name = "High-yield Missile Pods"
    weapon_type = RANGED
    range_in = 30
    attacks = 6
    strength = 7
    ap = -1
    damage = 2
    twin_linked = True


class BroadsideTwinSmartMissileSystemProfile(WeaponProfile):
    """A4 where the Riptide's copy of the same printed name is A3 - so its own
    class, the standing rule for a shared name with different numbers, and the
    third weapon in this file called some flavour of "smart missile system"."""
    name = "Twin Smart Missile System"
    weapon_type = RANGED
    range_in = 30
    attacks = 4
    strength = 5
    ap = 0
    damage = 1
    indirect_fire = True
    twin_linked = True


class CrushingBulkProfile(WeaponProfile):
    name = "Crushing Bulk"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = 0
    damage = 1


# --- Hammerhead Gunship / Sky Ray Gunship / Piranhas (T'au Empire) ---
#
# The Accelerator burst cannon, Seeker missile, Smart missile system and
# Armoured hull rows on these three datasheets print exactly the numbers the
# Devilfish's classes already carry, so those are reused. Only what genuinely
# differs is new - and on this batch that includes one weapon whose difference
# is a single missing keyword.

class HammerheadTwinPulseCarbineProfile(WeaponProfile):
    """The Hammerhead's twin pulse carbine prints [TWIN-LINKED] and NOTHING
    ELSE, where the Devilfish's, the Piranha's and the Sky Ray's all print
    [ASSAULT] as well.

    One keyword, one class - and it is worth the class rather than a shrug:
    [ASSAULT] is what lets a weapon fire after Advancing (24.04), so sharing
    the Devilfish's copy would quietly let a Hammerhead Advance and still
    shoot its carbines."""
    name = "Twin Pulse Carbine"
    weapon_type = RANGED
    range_in = 20
    attacks = 2
    strength = 5
    ap = 0
    damage = 1
    twin_linked = True


class IonCannonStandardProfile(WeaponProfile):
    """The Hammerhead's alternative main gun. Its overcharge_profile links to
    the Hazardous mode below - one weapon with two selectable modes, like every
    other ion weapon in this file."""
    name = "Ion Cannon - Standard"
    weapon_type = RANGED
    range_in = 60
    attacks = 6  # preview only - see attacks_notation
    attacks_notation = D6(bonus=3)
    strength = 7
    ap = -1
    damage = 2
    blast = 1


class IonCannonOverchargeProfile(WeaponProfile):
    """Not a standalone loadout choice - only ever instantiated on demand by
    ShootingController.choose_weapon(overcharge=True)."""
    name = "Ion Cannon - Overcharge"
    weapon_type = RANGED
    range_in = 60
    attacks = 6  # preview only - see attacks_notation
    attacks_notation = D6(bonus=3)
    strength = 8
    ap = -2
    damage = 3
    blast = 1
    hazardous = True


IonCannonStandardProfile.overcharge_profile = IonCannonOverchargeProfile


class RailgunProfile(WeaponProfile):
    """The biggest gun in this engine by a wide margin: S20/AP-5/D6+6 at 72".

    Not the Broadside's heavy rail rifle (60"/S12/AP-4/D6+1) and not the
    Pathfinders' rail rifle - three printed rows, three classes, and this one
    is the reason a Hammerhead is worth its points."""
    name = "Railgun"
    weapon_type = RANGED
    range_in = 72
    attacks = 1
    strength = 20
    ap = -5
    damage = 12  # preview only - see damage_notation
    damage_notation = D6(bonus=6)
    devastating_wounds = True
    heavy = True


class SeekerMissileRackProfile(WeaponProfile):
    """The Sky Ray's main armament: the Seeker missile's S/AP/D three times
    over and [TWIN-LINKED] instead of [ONE SHOT] - so it fires every turn where
    a Seeker missile fires once per battle. That contrast is the datasheet."""
    name = "Seeker Missile Rack"
    weapon_type = RANGED
    range_in = 48
    attacks = 3
    strength = 14
    ap = -3
    damage = 7  # preview only - see damage_notation
    damage_notation = D6(bonus=1)
    twin_linked = True


class PiranhaBurstCannonProfile(AcceleratorBurstCannonProfile):
    """Every number is the Accelerator burst cannon's; only the printed NAME
    differs, so it inherits rather than repeating them - and the test pins the
    two against EACH OTHER rather than against literals."""
    name = "Piranha Burst Cannon"


class PiranhaFusionBlasterProfile(WeaponProfile):
    """[MELTA 4], where every other fusion weapon in this file is [MELTA 2] -
    the highest melta value in the engine, and the reason this is its own class
    rather than the plain Fusion blaster under another name."""
    name = "Piranha Fusion Blaster"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 9
    ap = -4
    damage = 6  # preview only - see damage_notation
    damage_notation = D6()
    melta = 4


class PiranhaArmouredHullProfile(WeaponProfile):
    """A2/S4 where the Devilfish's and the two gunships' armoured hull is
    A3/S6 - a lighter skimmer, so its own class."""
    name = "Armoured Hull"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    weapon_skill = "5+"
    strength = 4
    ap = 0
    damage = 1


# --- Guardian Defenders (Aeldari), see game/factions/aeldari.py ---

class ShurikenCatapultProfile(WeaponProfile):
    name = "Shuriken Catapult"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 4
    ap = -1
    damage = 1
    assault = True


class BrightLanceProfile(WeaponProfile):
    """The Heavy Weapon Platform's gun in the loadout this project fields.

    No weapon keywords - confirmed from the datasheet, not assumed: an S12
    AP-3 D6+2 gun with nothing attached looks like a transcription gap, and
    that suspicion was raised and then settled here rather than guessed at."""
    name = "Bright Lance"
    weapon_type = RANGED
    range_in = 36
    attacks = 1
    strength = 12
    ap = -3
    damage = 8            # grouping/preview placeholder only - damage_notation below is what is rolled
    damage_notation = D6(2)


class AeldariCloseCombatWeaponProfile(WeaponProfile):
    """Its own class rather than reusing CloseCombatWeaponProfile: that one is
    an explicit placeholder at S4, and this is a real printed S3 profile.
    Exactly the "same name, different numbers" case that needs a separate
    class - and see AeldariCloseCombatWeaponA2Profile below, which is a
    THIRD one, because Aeldari print two different Close Combat Weapon rows."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 1
    strength = 3
    ap = 0
    damage = 1


# --- Storm Guardians (Aeldari), see game/factions/aeldari.py ---

class AeldariCloseCombatWeaponA2Profile(WeaponProfile):
    """The A2 Aeldari Close Combat Weapon, where AeldariCloseCombatWeaponProfile
    above is the A1 one - same name, same faction, different number, which is
    why both exist.

    Named after the numbers rather than a datasheet because three datasheets
    print this exact row now (Storm Guardians including their Serpent's Scale
    Platform, Warp Spiders, Dire Avengers); it was called
    AeldariCloseCombatWeaponA2Profile while Storm Guardians were its only
    carrier."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 3
    ap = 0
    damage = 1


class ShurikenPistolProfile(WeaponProfile):
    name = "Shuriken Pistol"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 4
    ap = -1
    damage = 1
    assault = True
    pistol = True


class AeldariFlamerProfile(WeaponProfile):
    """Printed BS is "N/A" - no ballistic_skill override needed, since
    [TORRENT] skips the Hit roll entirely (same as Skorcha above)."""
    name = "Flamer"
    weapon_type = RANGED
    range_in = 12
    attacks = 3  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6()
    strength = 4
    ap = 0
    damage = 1
    assault = True
    ignores_cover = True
    torrent = True


class FusionGunProfile(WeaponProfile):
    name = "Fusion Gun"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 8
    ap = -4
    damage = 3  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6()
    assault = True
    melta = 2


class PowerSwordProfile(WeaponProfile):
    name = "Power Sword"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 4
    ap = -2
    damage = 1


class VoidscarredPowerSwordProfile(PowerSwordProfile):
    """Same printed NAME and same S/AP/D, one more Attack: Corsair Voidscarred
    print this row at A3 where Storm Guardians and Corsair Voidreavers print
    it at A2. The recipe's "same name, different numbers" case, so it inherits
    and overrides only the number that differs - which is also what keeps the
    two pinned against each other instead of against literals."""
    attacks = 3


# --- Striking Scorpions (Aeldari), see game/factions/aeldari.py ---
# The Shuriken Pistol is shared with Storm Guardians above - same printed row,
# so it is reused rather than duplicated.

class ScorpionChainswordProfile(WeaponProfile):
    name = "Scorpion Chainsword"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 4
    ap = -1
    damage = 1
    sustained_hits = 1


class ScorpionsClawProfile(WeaponProfile):
    name = "Scorpion's Claw"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 8
    ap = -2
    damage = 2


class BitingBladeProfile(WeaponProfile):
    name = "Biting Blade"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 6
    ap = -3
    damage = 1
    sustained_hits = 1


class ChainsabresRangedProfile(WeaponProfile):
    """Chainsabres appear in BOTH weapon tables - a ranged row and a melee row
    under one name, like the Twin Lance's own dual-profile weapons. Two classes
    because this engine keys a profile by weapon_type, and the model carries
    both entries at once, exactly as the datasheet prints them."""
    name = "Chainsabres"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 4
    ap = -1
    damage = 1
    assault = True
    pistol = True
    twin_linked = True


class ChainsabresMeleeProfile(WeaponProfile):
    name = "Chainsabres"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 4
    ap = -1
    damage = 1
    sustained_hits = 1
    twin_linked = True


# --- Howling Banshees (Aeldari), see game/factions/aeldari.py ---
# Every melee row here prints WS2+, which is the model's own Weapon Skill, so
# none of them needs a per-weapon override. The Shuriken Pistol is shared with
# the other Aeldari datasheets.

class BansheeBladeProfile(WeaponProfile):
    name = "Banshee Blade"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 4
    ap = -2
    damage = 2
    # [ANTI-INFANTRY 3+] (rule 24.03). User report: "anti-infanterie bei den
    # banshees greift nicht" - it was missing from every one of this
    # datasheet's five weapon rows. Re-checked against the printed Keywords
    # column, which carries it on the Banshee blade, Executioner,
    # Mirrorswords AND both Triskele rows.
    anti = ("INFANTRY", 3)


class ExecutionerProfile(WeaponProfile):
    name = "Executioner"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = -3
    damage = 3
    # [ANTI-INFANTRY 3+] (rule 24.03). User report: "anti-infanterie bei den
    # banshees greift nicht" - it was missing from every one of this
    # datasheet's five weapon rows. Re-checked against the printed Keywords
    # column, which carries it on the Banshee blade, Executioner,
    # Mirrorswords AND both Triskele rows.
    anti = ("INFANTRY", 3)


class MirrorswordsProfile(WeaponProfile):
    name = "Mirrorswords"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 4
    ap = -2
    damage = 2
    # [ANTI-INFANTRY 3+] (rule 24.03). User report: "anti-infanterie bei den
    # banshees greift nicht" - it was missing from every one of this
    # datasheet's five weapon rows. Re-checked against the printed Keywords
    # column, which carries it on the Banshee blade, Executioner,
    # Mirrorswords AND both Triskele rows.
    anti = ("INFANTRY", 3)


class TriskeleRangedProfile(WeaponProfile):
    """Triskele has a ranged and a melee row under one name, like Chainsabres
    above - two classes, because this engine keys a profile by weapon_type and
    the model carries both entries at once."""
    name = "Triskele"
    weapon_type = RANGED
    range_in = 12
    attacks = 3
    strength = 3
    ap = -1
    damage = 1
    assault = True
    # [ANTI-INFANTRY 3+] (rule 24.03). User report: "anti-infanterie bei den
    # banshees greift nicht" - it was missing from every one of this
    # datasheet's five weapon rows. Re-checked against the printed Keywords
    # column, which carries it on the Banshee blade, Executioner,
    # Mirrorswords AND both Triskele rows.
    anti = ("INFANTRY", 3)


class TriskeleMeleeProfile(WeaponProfile):
    name = "Triskele"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 3
    ap = -1
    damage = 1
    # [ANTI-INFANTRY 3+] (rule 24.03). User report: "anti-infanterie bei den
    # banshees greift nicht" - it was missing from every one of this
    # datasheet's five weapon rows. Re-checked against the printed Keywords
    # column, which carries it on the Banshee blade, Executioner,
    # Mirrorswords AND both Triskele rows.
    anti = ("INFANTRY", 3)


# --- Warp Spiders -----------------------------------------------------------
# Every ranged weapon on this datasheet prints BS "N/A", which is what a
# [TORRENT] weapon prints - rule 24.37 skips the Hit roll entirely, so there is
# no ballistic skill to print. No ballistic_skill override is needed here for
# the same reason: nothing ever reads one.


class DeathSpinnerProfile(WeaponProfile):
    name = "Death Spinner"
    weapon_type = RANGED
    range_in = 12
    attacks = 3            # grouping/preview only - attacks_notation below is what is actually rolled
    attacks_notation = D6()
    strength = 4
    ap = -1
    damage = 1
    ignores_cover = True
    torrent = True


class ExarchsDeathSpinnerProfile(WeaponProfile):
    """The Exarch's own row: same name-shape as the Death Spinner above but
    S6/AP-2 where that one is S4/AP-1, so its own class."""
    name = "Exarch's Death Spinner"
    weapon_type = RANGED
    range_in = 12
    attacks = 3
    attacks_notation = D6()
    strength = 6
    ap = -2
    damage = 1
    ignores_cover = True
    torrent = True


class DeathWeaversProfile(WeaponProfile):
    name = "Death Weavers"
    weapon_type = RANGED
    range_in = 6
    attacks = 3
    attacks_notation = D6()
    strength = 4
    ap = -1
    damage = 1
    ignores_cover = True
    torrent = True
    twin_linked = True


class SpinneretRifleProfile(WeaponProfile):
    name = "Spinneret Rifle"
    weapon_type = RANGED
    range_in = 18
    attacks = 3
    attacks_notation = D6()
    strength = 5
    ap = -1
    damage = 1
    ignores_cover = True
    torrent = True


class PowerbladesProfile(WeaponProfile):
    name = "Powerblades"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 4
    ap = -2
    damage = 1
    lethal_hits = True
    twin_linked = True


class PowerbladeArrayProfile(WeaponProfile):
    """Twice the Powerblades' attacks (10 vs 5), otherwise the same row."""
    name = "Powerblade Array"
    weapon_type = MELEE
    range_in = 2
    attacks = 10
    strength = 4
    ap = -2
    damage = 1
    lethal_hits = True
    twin_linked = True


# --- Dire Avengers ----------------------------------------------------------


class AvengerShurikenCatapultProfile(WeaponProfile):
    """Distinct from ShurikenCatapultProfile (the Guardian Defenders' one)
    only in its Attacks: 18"/A4 where that row is 18"/A2. Everything else,
    [ASSAULT] included, matches."""
    name = "Avenger Shuriken Catapult"
    weapon_type = RANGED
    range_in = 18
    attacks = 4
    strength = 4
    ap = -1
    damage = 1
    assault = True


class DireswordProfile(WeaponProfile):
    name = "Diresword"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 4
    ap = -2
    damage = 1


class PowerGlaiveProfile(WeaponProfile):
    name = "Power Glaive"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 5
    ap = -3
    damage = 1


# --- Fire Dragons -----------------------------------------------------------


class DragonFusionGunProfile(WeaponProfile):
    """Distinct from FusionGunProfile (Storm Guardians'): S9 where that is S8,
    and [MELTA 3] where that is [MELTA 2]."""
    name = "Dragon Fusion Gun"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 9
    ap = -4
    damage = 3  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6()
    assault = True
    melta = 3


class ExarchsDragonFusionGunProfile(DragonFusionGunProfile):
    """The Exarch's own row: the same gun at [MELTA 6] instead of [MELTA 3]."""
    name = "Exarch's Dragon Fusion Gun"
    melta = 6


class DragonFusionPistolProfile(WeaponProfile):
    name = "Dragon Fusion Pistol"
    weapon_type = RANGED
    range_in = 6
    attacks = 1
    strength = 9
    ap = -4
    damage = 3
    damage_notation = D6()
    assault = True
    melta = 3
    pistol = True


class DragonsBreathFlamerProfile(WeaponProfile):
    """Prints BS "N/A" because [TORRENT] skips the Hit roll (rule 24.37), so
    no ballistic_skill override is wanted here."""
    name = "Dragon's Breath Flamer"
    weapon_type = RANGED
    range_in = 12
    attacks = 5  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(2)
    strength = 6
    ap = -2
    damage = 1
    assault = True
    ignores_cover = True
    torrent = True


class FirepikeProfile(WeaponProfile):
    name = "Firepike"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 12
    ap = -4
    damage = 3
    damage_notation = D6()
    assault = True
    melta = 3


class DragonAxeProfile(WeaponProfile):
    name = "Dragon Axe"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = -4
    damage = 3
    damage_notation = D6()


# --- Aeldari grav-tank guns -------------------------------------------------
# The four options a Falcon can mount in place of its scatter laser, plus the
# two weapons it carries as standard. Guardian Defenders' Heavy Weapon Platform
# lists the same four alternatives and has them unmodelled to this day for want
# of a confirmed keyword column - these rows now supply one, so closing that
# gap is four WargearOptions once the platform's own stats are checked against
# these.


class PulseLaserProfile(WeaponProfile):
    """The Falcon's main gun. Unrelated to the T'au "Pulse" weapon family
    despite the shared word - no name collision, and none of their stats."""
    name = "Pulse Laser"
    weapon_type = RANGED
    range_in = 48
    attacks = 3
    strength = 9
    ap = -2
    damage = 3  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6()


class ScatterLaserProfile(WeaponProfile):
    name = "Scatter Laser"
    weapon_type = RANGED
    range_in = 36
    attacks = 6
    strength = 5
    ap = 0
    damage = 1
    sustained_hits = 1


class ShurikenCannonProfile(WeaponProfile):
    name = "Shuriken Cannon"
    weapon_type = RANGED
    range_in = 24
    attacks = 3
    strength = 6
    ap = -1
    damage = 2
    lethal_hits = True


class StarcannonProfile(WeaponProfile):
    name = "Starcannon"
    weapon_type = RANGED
    range_in = 36
    attacks = 2
    strength = 8
    ap = -3
    damage = 2


class MissileLauncherSunburstProfile(WeaponProfile):
    """The blast profile of the missile launcher's two - see the starshot one
    below, which is the entry the datasheet actually grants.

    [BLAST] was missing here until the War Walker and Wave Serpent arrived and
    made this row live on three datasheets: the printed NAME is "Missile
    launcher - sunburst BLAST", and the name column is the reliable half of
    Wahapedia's rendering (the keyword cell comes back empty for this row on
    every datasheet that has it). The Dark Reapers' own copy already set it, so
    the two would otherwise have disagreed."""
    name = "Missile Launcher - Sunburst Blast"
    weapon_type = RANGED
    range_in = 48
    attacks = 3  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6()
    strength = 4
    ap = -1
    damage = 1
    blast = 1  # plain [BLAST] is X=1, see WeaponProfile.blast


class MissileLauncherStarshotProfile(WeaponProfile):
    """One datasheet entry, two printed firing profiles - so the second is an
    alternate FIRING MODE rather than a second weapon, the same shape
    Pathfinder Team's Ion rifle and the Ghostkeel's Cyclic Ion Raker use.
    Which of the two counts as the "standard" instance is arbitrary here (they
    are not an upgrade of one another); starshot is the row printed first."""
    name = "Missile Launcher - Starshot"
    weapon_type = RANGED
    range_in = 48
    attacks = 1
    strength = 10
    ap = -2
    damage = 3  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6()
    overcharge_profile = MissileLauncherSunburstProfile


class TwinShurikenCatapultProfile(WeaponProfile):
    """ShurikenCatapultProfile's twin mount: same 18"/S4/AP-1 row, [TWIN-LINKED]
    on top, and A2 where the single is also A2 - the keyword is the difference."""
    name = "Twin Shuriken Catapult"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 4
    ap = -1
    damage = 1
    assault = True
    twin_linked = True


class WraithboneHullProfile(WeaponProfile):
    """The grav-tank's own melee row. WS4+ is printed here where the vehicle
    itself has no other melee weapon to compare against, so it is a real
    per-weapon override rather than the model's own skill."""
    name = "Wraithbone Hull"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    weapon_skill = "4+"
    strength = 6
    ap = 0
    damage = 1


# --- Wraith constructs ------------------------------------------------------


class WraithcannonProfile(WeaponProfile):
    """S14 is the highest Strength in this engine. No weapon keywords -
    confirmed against the printed row rather than assumed, the same check the
    Bright Lance needed for the same reason (a gun this size with nothing
    attached reads like a transcription gap)."""
    name = "Wraithcannon"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    ballistic_skill = "4+"  # the WRAITHGUARD row; Corsair Voidreavers print 3+, see VoidreaverWraithcannonProfile
    strength = 14
    ap = -4
    damage = 4  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6(1)


class VoidreaverWraithcannonProfile(WraithcannonProfile):
    """Same printed row, its own BS: Corsair Voidreavers print the wraithcannon
    at 3+, the Wraithguard at 4+. Inherits everything and overrides only the
    number that differs, so the two stay pinned to each other."""
    ballistic_skill = "3+"



class DScytheProfile(WeaponProfile):
    """[TORRENT] is not read off the keywords column, which prints "none"
    here - it is read off the BS, which prints "N/A". A weapon that rolls to
    hit must print a ballistic skill, so "N/A" can only mean the Hit roll is
    skipped (rule 24.37). The name column carries "torrent" too."""
    name = "D-scythe"
    weapon_type = RANGED
    range_in = 12
    attacks = 3  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6()
    strength = 7
    ap = -3
    damage = 1
    torrent = True


class WraithCloseCombatWeaponProfile(WeaponProfile):
    """The THIRD Aeldari Close Combat Weapon row: A3/S5, where
    AeldariCloseCombatWeaponProfile is A1/S3 and
    AeldariCloseCombatWeaponA2Profile is A2/S3. Same name, different numbers,
    so its own class - and named after the construct rather than the count,
    because A3/S5 differs in two characteristics rather than one."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    weapon_skill = "4+"
    strength = 5
    ap = 0
    damage = 1


# --- Asurmen ----------------------------------------------------------------
# Both rows print their keywords appended to the NAME with an empty keywords
# column - the rendering artefact this project has now seen on seven weapons
# (Avenger shuriken catapult "assault", Shuriken pistol "assault pistol",
# Scatter laser "sustained hits 1", Shuriken cannon "lethal hits", Twin
# shuriken catapult "assault twin-linked", D-scythe "torrent", and these two),
# and in every earlier case the appended words were confirmed real keywords.
# Here there is also internal evidence: Hand of Asuryan's own printed text
# calls the gun "its Bloody Twins weapon", without the suffix - so "assault
# pistol" is not part of the name.


class BloodyTwinsProfile(WeaponProfile):
    name = "Bloody Twins"
    weapon_type = RANGED
    range_in = 24
    attacks = 6
    strength = 5
    ap = -1
    damage = 2
    assault = True
    pistol = True


class SwordOfAsurProfile(WeaponProfile):
    name = "Sword of Asur"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 6
    ap = -3
    damage = 3
    devastating_wounds = True


# --- Jain Zar ---------------------------------------------------------------
# Same rendering artefact as Asurmen's two rows: the keywords land in the NAME
# column. Here they landed in BOTH columns and looked swapped, which is why it
# was queried rather than guessed - the answer is that each row carries its own
# and Silent Death carries two.


class SilentDeathProfile(WeaponProfile):
    name = "Silent Death"
    weapon_type = RANGED
    range_in = 12
    attacks = 6
    strength = 6
    ap = -2
    damage = 1
    assault = True
    # NO [ANTI-INFANTRY 3+]: that keyword is the BLADE of Destruction's alone.
    # It sat here too until the keyword sweep put both rows beside their
    # printed ones - the two rows' keywords really do look swapped on the
    # page, which is what put it here in the first place (see the note in
    # test_jain_zar.py), but the scraped keyword column of
    # rules/aeldari/Jain Zar.md prints "assault" on this row and
    # "anti-infantry 3+" on the melee one.


class BladeOfDestructionProfile(WeaponProfile):
    name = "Blade of Destruction"
    weapon_type = MELEE
    range_in = 2
    attacks = 8
    strength = 6
    ap = -3
    damage = 2
    anti = ("INFANTRY", 3)


# --- Warlock Conclave -------------------------------------------------------
# Keywords read off the NAME column again (eighth datasheet with the same
# rendering artefact). Worth recording: on this one a targeted follow-up
# CONTRADICTED that column - it claimed [ASSAULT] on the Destructor, which the
# name does not carry - so the name column is the channel to trust and the
# summariser's prose about keywords is not. The Destructor also has
# independent confirmation: its BS prints "N/A", which only a [TORRENT] weapon
# does.


class DestructorProfile(WeaponProfile):
    name = "Destructor"
    weapon_type = RANGED
    range_in = 12
    attacks = 3  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6()
    strength = 5
    ap = -1
    damage = 1
    psychic = True
    torrent = True


class SingingSpearRangedProfile(WeaponProfile):
    """The thrown profile. One datasheet entry, two printed rows - so two
    classes under one name, the same shape as Chainsabres and the Twin Lance's
    Fusion eliminator (and NOT overcharge_profile, which is for two firing
    modes of one ranged weapon)."""
    name = "Singing Spear"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 9
    ap = 0
    damage = 3
    assault = True
    psychic = True


class SingingSpearMeleeProfile(WeaponProfile):
    name = "Singing Spear"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 3
    ap = 0
    damage = 3
    psychic = True


class WitchbladeProfile(WeaponProfile):
    name = "Witchblade"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 3
    ap = 0
    damage = 2
    psychic = True
    anti = ("INFANTRY", 2)


class EldritchStormProfile(WeaponProfile):
    """The Farseer's gun. First weapon here with BOTH a dice-notation Attacks
    and a dice-notation Damage."""
    name = "Eldritch Storm"
    weapon_type = RANGED
    range_in = 24
    # Printed BS 3+ on BOTH datasheets that carry it, while the Farseer and
    # the Farseer Skyrunner are 2+ with every other weapon they hold - so it
    # is a real per-weapon override, not the wielder's own skill. Without it
    # the gun hit on 2+.
    ballistic_skill = "3+"
    attacks = 3  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6()
    strength = 6
    ap = -2
    damage = 2   # likewise a placeholder - damage_notation is what is rolled
    damage_notation = D3()
    blast = 1
    psychic = True


class MindWarProfile(WeaponProfile):
    """Eldrad Ulthran's psychic duel. Nothing shareable: no other weapon here
    combines [ANTI-CHARACTER] with [PRECISION], and the pairing is the point -
    [PRECISION] (24.28) lets the wounds be put on a CHARACTER model that rule
    05.03 would otherwise protect, and [ANTI-CHARACTER 4+] is what makes those
    wounds land in the first place."""
    name = "Mind War"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 5
    ap = -2
    damage = 3   # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6()
    anti = ("CHARACTER", 4)
    precision = True
    psychic = True


class StaffOfUlthamarProfile(WeaponProfile):
    """"Staff of Ulthamar and witchblade" is ONE printed weapon row, not two -
    so one profile, under the printed name.

    Deliberately NOT WitchbladeProfile, which the Farseer and the Warlock
    Conclave share: that one is A2/S3/AP0, this is A3/S5/AP-1. Different name
    AND different numbers, i.e. the datasheet-recipe's "check whether a
    same-named weapon already exists with different values" step landing on
    the answer that a new class is needed. It keeps [PSYCHIC] and the
    [ANTI-INFANTRY] shape, but at a 2+ threshold rather than the Witchblade's
    own printed one."""
    name = "Staff of Ulthamar and Witchblade"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 5
    ap = -1
    damage = 2
    anti = ("INFANTRY", 2)
    psychic = True


class BroodTwainProfile(WeaponProfile):
    """Lhykhis' gun. Prints its Ballistic Skill as "N/A", which is the
    independent confirmation of [TORRENT] (24.37) - a weapon that rolled to hit
    would have to print a BS. Same corroboration the D-scythe, the Death
    Spinner and the Warlock Destructor gave.

    Note the interaction that follows from that, and which the test pins: her
    own Whispering Web lowers the crit threshold of the HIT roll, and this
    weapon never makes one. The ability is army-wide, so it is for everyone
    else's benefit, not hers."""
    name = "Brood Twain"
    weapon_type = RANGED
    range_in = 12
    attacks = 6   # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(3)
    strength = 6
    ap = -2
    damage = 1
    ignores_cover = True
    torrent = True
    twin_linked = True


class SpidersFangsProfile(WeaponProfile):
    """[EXTRA ATTACKS] (24.11), so it swings alongside Weaverender rather than
    competing with it under rule 04.01 - both of her melee rows land every
    activation, which is the point of the pair."""
    name = "Spider's Fangs"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 4
    ap = -2
    damage = 1
    extra_attacks = True
    lethal_hits = True


class WeaverenderProfile(WeaponProfile):
    """Her main melee row: the same A5/AP-2 as Spider's Fangs above but S6/D2,
    and without [EXTRA ATTACKS] - so this is the one rule 04.01 would make her
    choose, and the Fangs come free on top."""
    name = "Weaverender"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 6
    ap = -2
    damage = 2
    lethal_hits = True


class WailingDoomProfile(WeaponProfile):
    """The Avatar of Khaine's ranged row, and the first weapon here whose
    [SUSTAINED HITS] value is itself a DIE - printed "sustained hits d3".

    Eleventh instance of the Wahapedia rendering artefact where a weapon's
    keywords land appended to the NAME with the keywords column left empty, and
    the least ambiguous one yet: a narrower follow-up fetch confirmed all three
    of this datasheet's keyword cells are empty while "sustained hits d3" sits
    in the ranged row's name.

    `sustained_hits` below is a preview/grouping placeholder, the same
    arrangement `attacks`/`damage` have when their notation field is set - the
    ACTUAL number of extra hits is rolled per critical hit, see
    sustained_hits_notation and _begin_sustained_hits_roll()."""
    name = "The Wailing Doom"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 16
    ap = -4
    damage = 5    # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6(2)
    sustained_hits = 2          # preview/grouping placeholder only (D3's rough average) - sustained_hits_notation is what is rolled
    sustained_hits_notation = D3()


class WailingDoomStrikeProfile(WeaponProfile):
    """"The Wailing Doom - strike": the heavy melee row.

    Two melee rows under one weapon, and rule 04.01 already makes that a
    choice: whichever one swings locks the other out for the activation
    (_melee_locked_out()), so "strike or sweep" needs no mode machinery of its
    own. Same reasoning as Commander Farsight's Dawn Blade - and unlike a
    RANGED two-mode weapon, which does need overcharge_profile, because nothing
    otherwise stops one model firing both."""
    name = "The Wailing Doom - Strike"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 16
    ap = -4
    damage = 5    # placeholder, as above
    damage_notation = D6(2)


class WailingDoomSweepProfile(WeaponProfile):
    """"The Wailing Doom - sweep": twice the attacks at half the Strength and a
    flat 2 Damage - the horde-clearing half of the same choice."""
    name = "The Wailing Doom - Sweep"
    weapon_type = MELEE
    range_in = 2
    attacks = 12
    strength = 8
    ap = -2
    damage = 2


# --- Dark Reapers ----------------------------------------------------------
#
# EVERY BALLISTIC SKILL HERE IS AN EXPLICIT OVERRIDE, and that is a decision
# rather than an oversight. The printed rows give the Reaper launcher BS3+ and
# the Missile launcher BS2+, while the statlines give a Dark Reaper BS3+ and
# the Exarch BS2+. The Exarch carries a Reaper launcher by default, so the two
# sources disagree for exactly one combination: deferring to the model would
# fire his default weapon at 2+, which is not what the row prints. The printed
# row wins, which is also the engine's existing precedent for a weapon whose
# BS differs from its bearer's (the Riptide's Missile Drones, the Pathfinder
# Rail Rifle). The visible consequence is that the Exarch's own 2+ only shows
# through the Missile launcher - the one option printed at 2+.


class ReaperLauncherStarshotProfile(WeaponProfile):
    """The unit's default gun, printed as ONE datasheet entry with two firing
    modes (starshot/starswarm) - so the second is an overcharge_profile rather
    than a second weapon, the same shape as Pathfinder Team's Ion Rifle. The
    two are peers here (neither is an upgrade of the other, and neither is
    [HAZARDOUS]); which one is the "standard" instance is arbitrary."""
    name = "Reaper Launcher - Starshot"
    weapon_type = RANGED
    range_in = 48
    attacks = 1
    ballistic_skill = "3+"
    strength = 10
    ap = -2
    damage = 3
    ignores_cover = True


class ReaperLauncherStarswarmProfile(WeaponProfile):
    name = "Reaper Launcher - Starswarm"
    weapon_type = RANGED
    range_in = 48
    attacks = 2
    ballistic_skill = "3+"
    strength = 5
    ap = -2
    damage = 1
    ignores_cover = True


ReaperLauncherStarshotProfile.overcharge_profile = ReaperLauncherStarswarmProfile


class DarkReaperMissileLauncherStarshotProfile(WeaponProfile):
    """Same printed name as the Falcon's Missile Launcher and genuinely its own
    row - but NOT for the reason this docstring used to give. It claimed "D6
    where that one is D3"; both are printed D6, and the flat `damage = 6` that
    sat here (the old "keep the die's max value" convention) was what made the
    two look different. What actually separates them is the Dark Reapers'
    printed [IGNORES COVER] - and the Exarch's own 2+ against the Falcon's 3+.
    Corrected when rules/aeldari/*.md was put side by side with the engine;
    until then the Exarch's launcher dealt a guaranteed 6 for a printed D6."""
    name = "Missile Launcher - Starshot"
    weapon_type = RANGED
    range_in = 48
    attacks = 1
    ballistic_skill = "2+"
    strength = 10
    ap = -2
    damage = 3  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6()
    ignores_cover = True


class DarkReaperMissileLauncherSunburstProfile(WeaponProfile):
    name = "Missile Launcher - Sunburst"
    weapon_type = RANGED
    range_in = 48
    attacks = 3            # grouping/preview only - attacks_notation is what is rolled
    attacks_notation = D6()
    ballistic_skill = "2+"
    strength = 4
    ap = -1
    damage = 1
    blast = 1              # plain [BLAST] is X=1, see WeaponProfile.blast
    ignores_cover = True


DarkReaperMissileLauncherStarshotProfile.overcharge_profile = (
    DarkReaperMissileLauncherSunburstProfile)


class DarkReaperShurikenCannonProfile(ShurikenCannonProfile):
    """Identical numbers to the shared Shuriken Cannon, one keyword more: this
    datasheet prints it with [IGNORES COVER] as well as [LETHAL HITS], which
    the Falcon's and the Shining Spears' rows do not. Same-name-different-
    PRINTING rather than different numbers, so it subclasses rather than
    repeating the statline - a change to the shared numbers reaches it."""
    ballistic_skill = "3+"
    ignores_cover = True


class TempestLauncherProfile(WeaponProfile):
    name = "Tempest Launcher"
    weapon_type = RANGED
    range_in = 36
    attacks = 7            # grouping/preview only - attacks_notation is what is rolled
    attacks_notation = D6(dice=2)   # printed "2D6" - the first multi-die characteristic here
    ballistic_skill = "3+"
    strength = 4
    ap = -1
    damage = 1
    blast = 1
    indirect_fire = True   # [INDIRECT FIRE], rule 10.07


# --- Shining Spears --------------------------------------------------------
#
# The laser lance and the star lance each print a RANGED row and a MELEE row
# under one name, so each is two classes - the shape Chainsabres, the Singing
# Spear and the Fusion Eliminator already use, and deliberately NOT
# overcharge_profile (that is for two firing modes of one ranged weapon, where
# something has to stop a model firing both).


class LaserLanceRangedProfile(WeaponProfile):
    name = "Laser Lance"
    weapon_type = RANGED
    range_in = 6
    attacks = 1
    strength = 6
    ap = -2
    damage = 3
    assault = True


class LaserLanceMeleeProfile(WeaponProfile):
    name = "Laser Lance"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 5
    ap = -2
    damage = 3
    anti = (("MONSTER", 3), ("VEHICLE", 3))
    lance = True           # [LANCE], rule 24.21


class StarLanceRangedProfile(WeaponProfile):
    name = "Star Lance"
    weapon_type = RANGED
    range_in = 6
    attacks = 1
    strength = 9
    ap = -3
    damage = 3
    assault = True


class StarLanceMeleeProfile(WeaponProfile):
    name = "Star Lance"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = -3
    damage = 3
    anti = (("MONSTER", 3), ("VEHICLE", 3))
    lance = True


class ParagonSabreProfile(WeaponProfile):
    name = "Paragon Sabre"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 5
    ap = -2
    damage = 2


class AeldariCloseCombatWeaponA3Profile(WeaponProfile):
    """Windriders' row: A3/S3, where the three Aeldari "Close combat weapon"
    rows already here are A1/S3 (Guardian Defenders), A2/S3 (Storm Guardians,
    Fire Dragons, Dark Reapers) and A3/S5 (Wraithguard). Named after the
    numbers that distinguish it, like its siblings, rather than after one
    datasheet."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 3
    ap = 0
    damage = 1


# --- Rangers / Shroud Runners ----------------------------------------------
#
# TWO "Long rifle" rows that are NOT the same weapon: the Rangers' prints
# [HEAVY] and [PRECISION] at BS3+, the Shroud Runners' prints [PRECISION] alone
# at BS2+. Same printed name, different printing - so two classes, the same
# call the Dark Reapers' Shuriken Cannon needed.
#
# The keyword cells of both rows came back EMPTY while the name cells carried
# the keywords ("Long rifle heavy precision"). That is the rendering artefact
# this file has hit a dozen times now, and the name column is the reliable
# half - confirmed here by a second, targeted lookup.


class RangerLongRifleProfile(WeaponProfile):
    """Rangers' row. BS printed explicitly because this datasheet's two guns
    disagree with each other: the rifle is 3+ (the model's own) and the pistol
    is 2+ (better than the model), which was confirmed twice before being
    written down - a sniper rifle less accurate than a pistol reads like a
    transcription error and is not one."""
    name = "Long Rifle"
    weapon_type = RANGED
    range_in = 36
    attacks = 1
    ballistic_skill = "3+"
    strength = 4
    ap = -1
    damage = 2
    heavy = True            # [HEAVY], rule 24.16
    precision = True        # [PRECISION], rule 24.28


class RangerShurikenPistolProfile(ShurikenPistolProfile):
    """Same numbers as the shared Shuriken Pistol, one difference that matters:
    this datasheet prints it at BS2+ while the model is BS3+, so it cannot
    defer. Subclasses rather than repeating the statline, so a change to the
    shared numbers reaches it."""
    ballistic_skill = "2+"


class ShroudRunnerLongRifleProfile(WeaponProfile):
    """Shroud Runners' row: [PRECISION] only - no [HEAVY], which the Rangers'
    row does print. Pinned as an explicit comparison in the suites, because two
    weapons sharing a name is exactly where a keyword gets copied across."""
    name = "Long Rifle"
    weapon_type = RANGED
    range_in = 36
    attacks = 1
    ballistic_skill = "2+"
    strength = 4
    ap = -1
    damage = 2
    precision = True


class ShroudRunnerScatterLaserProfile(ScatterLaserProfile):
    """The shared Scatter Laser with an explicit BS3+: this datasheet's models
    are BS2+, so deferring would fire it more accurately than the row prints."""
    ballistic_skill = "3+"


# --- Swooping Hawks / Baharroth --------------------------------------------


class LasblasterProfile(WeaponProfile):
    name = "Lasblaster"
    weapon_type = RANGED
    range_in = 24
    attacks = 4
    strength = 4
    ap = 0
    damage = 1
    assault = True
    lethal_hits = True


class ExarchsLasblasterProfile(WeaponProfile):
    """The Exarch's own row: same name-shape as the Lasblaster above but
    S5/AP-1 where that one is S4/AP0, so its own class - the same call the
    Exarch's Death Spinner needed."""
    name = "Exarch's Lasblaster"
    weapon_type = RANGED
    range_in = 24
    attacks = 4
    strength = 5
    ap = -1
    damage = 1
    assault = True
    lethal_hits = True


class HawksTalonProfile(WeaponProfile):
    """The Exarch's printed default. NOT [ASSAULT] - the two lasblaster rows
    are, this one is not, which is the difference the wargear swap trades
    away."""
    name = "Hawk's Talon"
    weapon_type = RANGED
    range_in = 24
    attacks = 2
    strength = 6
    ap = -2
    damage = 2
    lethal_hits = True


class SunpistolProfile(WeaponProfile):
    name = "Sunpistol"
    weapon_type = RANGED
    range_in = 12
    attacks = 2
    strength = 4
    ap = 0
    damage = 1
    assault = True
    pistol = True
    lethal_hits = True


class SwoopingHawkPowerSwordProfile(WeaponProfile):
    """Same printed name as the Power Sword the Storm Guardians carry, and
    A5 where that one is A2 - so its own class, the recipe's "check whether a
    same-named weapon already exists with DIFFERENT numbers" step."""
    name = "Power Sword"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 4
    ap = -2
    damage = 1


class FuryOfTheTempestProfile(WeaponProfile):
    name = "Fury of the Tempest"
    weapon_type = RANGED
    range_in = 24
    attacks = 4
    strength = 6
    ap = -1
    damage = 2
    assault = True
    lethal_hits = True


class ShiningBladeProfile(WeaponProfile):
    name = "Shining Blade"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 5
    ap = -2
    damage = 2
    sustained_hits = 1


# --- War Walkers / Wave Serpent --------------------------------------------
#
# EVERY Wave Serpent gun is one of the guns already here plus [TWIN-LINKED],
# so they SUBCLASS rather than repeat the statline: a change to the shared
# numbers reaches the twin version, which is the point. That is also why the
# War Walker needed no new ranged weapon at all - its six rows are the shared
# ones, unchanged.


class WarWalkerFeetProfile(WeaponProfile):
    """Not the Wraithbone Hull: that is A3/WS4+/S6, this is A3/WS3+/S5."""
    name = "War Walker Feet"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    weapon_skill = "3+"
    strength = 5
    ap = 0
    damage = 1


class TwinBrightLanceProfile(BrightLanceProfile):
    name = "Twin Bright Lance"
    twin_linked = True


class TwinScatterLaserProfile(ScatterLaserProfile):
    name = "Twin Scatter Laser"
    twin_linked = True


class TwinShurikenCannonProfile(ShurikenCannonProfile):
    name = "Twin Shuriken Cannon"
    twin_linked = True


class TwinStarcannonProfile(StarcannonProfile):
    name = "Twin Starcannon"
    twin_linked = True


class TwinMissileLauncherSunburstProfile(MissileLauncherSunburstProfile):
    name = "Twin Missile Launcher - Sunburst Blast"
    twin_linked = True


class TwinMissileLauncherStarshotProfile(MissileLauncherStarshotProfile):
    """One datasheet entry with two firing profiles, so the second is an
    overcharge_profile - the same shape the single-barrelled version uses."""
    name = "Twin Missile Launcher - Starshot"
    twin_linked = True
    overcharge_profile = TwinMissileLauncherSunburstProfile


# --- Fuegan -----------------------------------------------------------------
#
# Searsong is ONE datasheet entry with two firing profiles, named "beam" and
# "lance" - the word after the dash, exactly where "sunburst" and "starshot" sit
# on the missile launcher. "lance" is therefore the PROFILE NAME and not the
# [LANCE] weapon ability: it stands in the same position as "beam", which is
# unambiguously a name, and the ability does not appear on the datasheet. Pinned
# in test_fuegan.py so that correcting it, if it is ever confirmed the other way,
# is a one-line change with a test that says why.


class SearsongLanceProfile(WeaponProfile):
    """The long profile: fewer, far heavier shots. Reached as the alternate
    firing mode of the beam below."""
    name = "Searsong - Lance"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    ballistic_skill = "2+"
    strength = 14
    ap = -4
    damage = 3            # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6()
    assault = True
    melta = 6


class SearsongBeamProfile(WeaponProfile):
    """The short profile, and the granted entry - the datasheet prints it
    first, and its alternate mode is the lance above."""
    name = "Searsong - Beam"
    weapon_type = RANGED
    range_in = 12
    attacks = 3
    ballistic_skill = "2+"
    strength = 8
    ap = -3
    damage = 2
    assault = True
    melta = 1
    sustained_hits = 2
    overcharge_profile = SearsongLanceProfile


class FireAxeProfile(WeaponProfile):
    """Six attacks at WS2+/S5/AP-4/D3, and no keywords at all - checked rather
    than assumed, the same doubt BrightLanceProfile records."""
    name = "Fire Axe"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    weapon_skill = "2+"
    strength = 5
    ap = -4
    damage = 3


# ---------------------------------------------------------------------------
# Necrons - see game/factions/necrons.py
#
# TRANSCRIPTION NOTE, the ~15th instance of the artefact CLAUDE.md records:
# every Necron weapon row came back from Wahapedia with an EMPTY keyword
# column and its keywords hanging off the NAME instead ("Gauss destructor
# heavy lethal hits", "Doomsday cannon blast heavy", "Tachyon arrow one shot").
# The name column is the reliable half, so that is what these classes follow.
#
# WS/BS are deliberately absent here wherever they match the wielder's own
# UnitProfile - see WeaponProfile's docstring. The one exception is the
# Voidscythe, which really does print a worse WS than the Overlord carrying it.
# ---------------------------------------------------------------------------


class NecronCloseCombatWeaponA1Profile(WeaponProfile):
    """Necron Warriors' Close Combat Weapon: A1/S4.

    Its own class for the reason this file keeps re-learning - "Close Combat
    Weapon" is a name Necron datasheets print with DIFFERENT numbers. This is
    the A1/S4 one; NecronCloseCombatWeaponA2Profile below is the A2/S4 one that
    Immortals and both Lokhust datasheets carry. Named after the numbers rather
    than a datasheet because more than one carrier already exists - the same
    choice AeldariCloseCombatWeaponA2Profile records."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 1
    strength = 4
    ap = 0
    damage = 1


class NecronCloseCombatWeaponA2Profile(WeaponProfile):
    """The A2/S4 Necron Close Combat Weapon (Immortals, Lokhust Destroyers,
    Lokhust Heavy Destroyers), where NecronCloseCombatWeaponA1Profile above is
    the A1 one."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 4
    ap = 0
    damage = 1


# --- Necron Warriors ---

class GaussFlayerProfile(WeaponProfile):
    name = "Gauss Flayer"
    weapon_type = RANGED
    range_in = 24
    attacks = 1
    strength = 4
    ap = 0
    damage = 1
    lethal_hits = True
    rapid_fire = 1


class GaussReaperProfile(WeaponProfile):
    name = "Gauss Reaper"
    weapon_type = RANGED
    range_in = 12
    attacks = 2
    strength = 4
    ap = -1
    damage = 1
    lethal_hits = True


# --- Immortals ---

class GaussBlasterProfile(WeaponProfile):
    name = "Gauss Blaster"
    weapon_type = RANGED
    range_in = 24
    attacks = 2
    strength = 5
    ap = -1
    damage = 1
    lethal_hits = True


class TeslaCarbineProfile(WeaponProfile):
    name = "Tesla Carbine"
    weapon_type = RANGED
    range_in = 24
    attacks = 2
    strength = 5
    ap = 0
    damage = 1
    assault = True
    sustained_hits = 2


# --- Overlord / Lokhust Lord ---

class LordStaffOfLightRangedProfile(WeaponProfile):
    """The A4 Staff of Light, NOT the Technomancer's.

    Exactly the "same name, different numbers" case the datasheet recipe warns
    about: three datasheets print a weapon called "Staff of light", and the
    Technomancer's differs in both BS/WS (4+ against 2+) and melee Attacks
    (2 against 4). Two class pairs, therefore - see
    TechnomancerStaffOfLightRangedProfile.

    NAMED FOR THE LORDS AND NOT FOR THE OVERLORD, which it was until the
    Lokhust Lord arrived carrying the identical row. A class named after the
    first datasheet to field it is precisely the lying name this repo renames
    rather than copies (game/ere_we_go.py, game/melee_crit.py and
    weapon_support_system are the three recorded precedents)."""
    name = "Staff of Light"
    weapon_type = RANGED
    range_in = 18
    attacks = 3
    strength = 5
    ap = -2
    damage = 1


class LordStaffOfLightMeleeProfile(WeaponProfile):
    name = "Staff of Light"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = -2
    damage = 1


class TachyonArrowProfile(WeaponProfile):
    name = "Tachyon Arrow"
    weapon_type = RANGED
    range_in = 72
    attacks = 1
    strength = 16
    ap = -5
    damage = 8            # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6(2)
    one_shot = True


class OverlordsBladeProfile(WeaponProfile):
    name = "Overlord's Blade"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 8
    ap = -3
    damage = 2
    devastating_wounds = True


class VoidscytheProfile(WeaponProfile):
    """The one Necron weapon that prints a worse Weapon Skill than the model
    swinging it (WS3+ on a WS2+ Overlord) - the same shape as the Power Klaw,
    and the reason WeaponProfile carries a weapon_skill override at all."""
    name = "Voidscythe"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    weapon_skill = "3+"
    strength = 12
    ap = -3
    damage = 3
    devastating_wounds = True


# --- Plasmancer ---

class PlasmicLanceRangedProfile(WeaponProfile):
    name = "Plasmic Lance"
    weapon_type = RANGED
    range_in = 18
    attacks = 3
    strength = 7
    ap = -3
    damage = 2


class PlasmicLanceMeleeProfile(WeaponProfile):
    name = "Plasmic Lance"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 7
    ap = -3
    damage = 2


# --- Technomancer ---

class TechnomancerStaffOfLightRangedProfile(WeaponProfile):
    """The Technomancer's Staff of Light - see LordStaffOfLightRangedProfile
    for why these are two class pairs and not one shared one."""
    name = "Staff of Light"
    weapon_type = RANGED
    range_in = 18
    attacks = 3
    strength = 5
    ap = -2
    damage = 1


class TechnomancerStaffOfLightMeleeProfile(WeaponProfile):
    name = "Staff of Light"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 5
    ap = -2
    damage = 1


# --- Illuminor Szeras ---

class EldritchLanceRangedProfile(WeaponProfile):
    name = "Eldritch Lance"
    weapon_type = RANGED
    range_in = 36
    attacks = 3
    strength = 9
    ap = -3
    damage = 3


class EldritchLanceMeleeProfile(WeaponProfile):
    name = "Eldritch Lance"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 9
    ap = -3
    damage = 3


class ImpalingLegsProfile(WeaponProfile):
    name = "Impaling Legs"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 6
    ap = -1
    damage = 1
    extra_attacks = True


# --- Canoptek Wraiths ---

class ParticleCasterProfile(WeaponProfile):
    name = "Particle Caster"
    weapon_type = RANGED
    range_in = 12
    attacks = 3
    strength = 5
    ap = 0
    damage = 1
    devastating_wounds = True
    pistol = True


class TransdimensionalBeamerProfile(WeaponProfile):
    name = "Transdimensional Beamer"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 4
    ap = -2
    damage = 3


class ViciousClawsProfile(WeaponProfile):
    name = "Vicious Claws"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 6
    ap = -1
    damage = 2


class WhipCoilsProfile(WeaponProfile):
    name = "Whip Coils"
    weapon_type = MELEE
    range_in = 2
    attacks = 8
    strength = 5
    ap = 0
    damage = 1


# --- Lychguard ---

class HyperphaseSwordProfile(WeaponProfile):
    name = "Hyperphase Sword"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = -2
    damage = 1


class WarscytheProfile(WeaponProfile):
    name = "Warscythe"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 8
    ap = -3
    damage = 2
    devastating_wounds = True


# --- Skorpekh Destroyers ---

class SkorpekhHyperphaseWeaponsProfile(WeaponProfile):
    """Printed with an empty keyword column AND no keywords in the name, which
    was checked rather than assumed - the same doubt FireAxeProfile records."""
    name = "Skorpekh Hyperphase Weapons"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 7
    ap = -2
    damage = 2


# --- Lokhust Destroyers ---

class GaussCannonProfile(WeaponProfile):
    name = "Gauss Cannon"
    weapon_type = RANGED
    range_in = 24
    attacks = 3
    strength = 5
    ap = -2
    damage = 2
    lethal_hits = True


# --- Lokhust Heavy Destroyers ---

class EnmiticExterminatorProfile(WeaponProfile):
    name = "Enmitic Exterminator"
    weapon_type = RANGED
    range_in = 36
    attacks = 6
    strength = 6
    ap = -1
    damage = 1
    heavy = True
    rapid_fire = 6
    sustained_hits = 1


class GaussDestructorProfile(WeaponProfile):
    name = "Gauss Destructor"
    weapon_type = RANGED
    range_in = 48
    attacks = 1
    strength = 14
    ap = -4
    damage = 6
    heavy = True
    lethal_hits = True


# --- Doomsday Ark ---

class DoomsdayCannonProfile(WeaponProfile):
    name = "Doomsday Cannon"
    weapon_type = RANGED
    range_in = 72
    attacks = 1           # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(1)
    strength = 18
    ap = -4
    damage = 4
    blast = 1
    heavy = True


class GaussFlayerArrayProfile(WeaponProfile):
    name = "Gauss Flayer Array"
    weapon_type = RANGED
    range_in = 24
    attacks = 5
    strength = 4
    ap = 0
    damage = 1
    lethal_hits = True
    rapid_fire = 5


class ArmouredBulkProfile(WeaponProfile):
    name = "Armoured Bulk"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = 0
    damage = 1


# --- C'tan Shard of the Void Dragon ---

class SpearOfTheVoidDragonSweepProfile(WeaponProfile):
    """The Spear's second MELEE profile. Defined before the strike profile
    below because that one names it as its alternate mode."""
    name = "Spear of the Void Dragon - Sweep"
    weapon_type = MELEE
    range_in = 2
    attacks = 10
    strength = 8
    ap = -1
    damage = 2


class SpearOfTheVoidDragonStrikeProfile(WeaponProfile):
    """One printed datasheet entry with two melee profiles, so they are a
    firing-mode PAIR (overcharge_profile) rather than two separate weapons -
    otherwise the Void Dragon would swing both in the same activation, which
    rule 04.01 forbids."""
    name = "Spear of the Void Dragon - Strike"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 12
    ap = -4
    damage = 8            # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6(2)
    anti = ("VEHICLE", 2)
    overcharge_profile = SpearOfTheVoidDragonSweepProfile


class SpearOfTheVoidDragonAntiVehicleProfile(WeaponProfile):
    """The Spear's RANGED row. A third profile of the same printed weapon, but
    a ranged one, so it is a separate weapon in the loadout rather than a mode
    of the melee pair - the arrangement the Star Lance and Singing Spear use."""
    name = "Spear of the Void Dragon"
    weapon_type = RANGED
    range_in = 12
    attacks = 1           # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D3()
    strength = 8
    ap = -3
    damage = 8            # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6(2)
    anti = ("VEHICLE", 2)


class VoltaicStormProfile(WeaponProfile):
    name = "Voltaic Storm"
    weapon_type = RANGED
    range_in = 18
    attacks = 1           # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(3)
    strength = 7
    ap = -1
    damage = 2
    blast = 1
    sustained_hits = 2


class CanoptekTailBladesProfile(WeaponProfile):
    name = "Canoptek Tail Blades"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 6
    ap = -1
    damage = 1
    extra_attacks = True



class LordsBladeProfile(OverlordsBladeProfile):
    """The Lokhust Lord's blade. Same numbers as the Overlord's Blade to the
    last characteristic, different printed NAME - the mirror image of the
    Staff of Light case above, and handled the mirror way: it INHERITS, so a
    correction to the shared numbers reaches both, and only the name is
    overridden. Same move as the Wave Serpent's five twin-linked subclasses.

    The test pins the two AGAINST EACH OTHER rather than against literals - a
    copied class would pass any check that only read one of them."""
    name = "Lord's Blade"


# --- Skorpekh Lord ---

class EnmiticAnnihilatorProfile(WeaponProfile):
    """NOT the Lokhust Heavy Destroyers' Enmitic Exterminator: same family of
    name, different numbers (18"/A2 against 36"/A6, and [RAPID FIRE 2] against
    [HEAVY] [RAPID FIRE 6] [SUSTAINED HITS 1]). Its own class, which is the
    trap the datasheet recipe warns about and this faction has now hit three
    times (Staff of Light, Close Combat Weapon, and this)."""
    name = "Enmitic Annihilator"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 6
    ap = -1
    damage = 1
    rapid_fire = 2


class FlensingClawProfile(WeaponProfile):
    """A8 at S6, and NO keywords - checked rather than assumed, because a
    many-attacks claw alongside a heavier weapon usually IS [EXTRA ATTACKS]
    and here it is not. That makes the Lord's two melee weapons a real rule
    04.01 CHOICE (see SkorpekhLordProfile), not a claw that comes free with
    the harvester."""
    name = "Flensing Claw"
    weapon_type = MELEE
    range_in = 2
    attacks = 8
    strength = 6
    ap = -1
    damage = 1


class HyperphaseHarvesterProfile(WeaponProfile):
    """The heavy half of the Lord's 04.01 choice - a quarter of the claw's
    attacks at S10/AP-3/D3 instead of S6/AP-1/D1. Distinct from both the
    Lychguard's Hyperphase Sword and the Skorpekh Destroyers' Skorpekh
    Hyperphase Weapons; all three print different numbers."""
    name = "Hyperphase Harvester"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 10
    ap = -3
    damage = 3


# --- Deathmarks / Flayed Ones / Cryptothralls / Tomb Blades ----------------
#
# FOUR SHARES AND TWO INHERITANCES, measured before a class was written:
#   * the Deathmarks' "Close combat weapon" IS NecronCloseCombatWeaponA2Profile
#     (A2 S4 AP0 D1) and the Tomb Blades' IS NecronCloseCombatWeaponA1Profile
#     (A1 S4). Cloning either would have been the inverse of the "same name,
#     other numbers" trap - the numbers are the same, so the class is.
#   * the two twin guns are their single-barrelled siblings plus [TWIN-LINKED]
#     and nothing else, so they INHERIT and override only `name` and that one
#     keyword - the shape the five Wave Serpent twins already use, and the one
#     that keeps them pinned against each other instead of against literals.


class SynapticDisintegratorProfile(WeaponProfile):
    """Deathmarks. [PRECISION] is what the datasheet is for: a 36" sniper that
    can pick a CHARACTER out of an attached unit (rule 24.28)."""
    name = "Synaptic disintegrator"
    weapon_type = RANGED
    range_in = 36
    attacks = 1
    strength = 5
    ap = -2
    damage = 2
    heavy = True
    precision = True


class FlayerClawsProfile(WeaponProfile):
    """Flayed Ones."""
    name = "Flayer claws"
    weapon_type = MELEE
    attacks = 4
    strength = 4
    ap = -1
    damage = 1
    sustained_hits = 1
    twin_linked = True


class ScouringEyeProfile(WeaponProfile):
    """Cryptothralls. Six inches of range, which is the whole character of the
    datasheet - it is a bodyguard, not a gun."""
    name = "Scouring eye"
    weapon_type = RANGED
    range_in = 6
    attacks = 2
    strength = 5
    ap = -1
    damage = 1


class ScythedLimbsProfile(WeaponProfile):
    """Cryptothralls."""
    name = "Scythed limbs"
    weapon_type = MELEE
    attacks = 4
    strength = 5
    ap = -1
    damage = 1


class ParticleBeamerS5Profile(WeaponProfile):
    """Tomb Blades, one of the two twin-gauss-blaster replacements."""
    name = "Particle beamer"
    weapon_type = RANGED
    range_in = 18
    attacks = 3  # preview/grouping placeholder only - attacks_notation is rolled
    attacks_notation = D6()
    strength = 5
    ap = 0
    damage = 1
    blast = 1
    devastating_wounds = True


class TwinGaussBlasterProfile(GaussBlasterProfile):
    """Tomb Blades' default gun: the Immortals' Gauss Blaster with
    [TWIN-LINKED] added and nothing else changed. Inherited rather than
    copied, so the two stay pinned to each other."""
    name = "Twin gauss blaster"
    twin_linked = True


class TwinTeslaCarbineProfile(TeslaCarbineProfile):
    """The other replacement, and the same relationship to the Immortals'
    Tesla Carbine."""
    name = "Twin tesla carbine"
    twin_linked = True


# --- Crypteks: Chronomancer / Psychomancer / Orikan The Diviner -------------
#
# The two staves each print ONE name across a ranged and a melee row, which is
# this repo's Staff-of-Light shape: two classes, one printed name, and the
# datasheet lists both. WS/BS live on the PROFILE (all three Crypteks agree
# with their own weapons), so none of these carries an override.


class AeonstaveRangedProfile(WeaponProfile):
    """Chronomancer, ranged row."""
    name = "Aeonstave"
    weapon_type = RANGED
    range_in = 18
    attacks = 3  # preview/grouping placeholder only - attacks_notation is rolled
    attacks_notation = D6()
    strength = 5
    ap = -1
    damage = 1
    blast = 1


class AeonstaveMeleeProfile(WeaponProfile):
    """Chronomancer, melee row. Same printed name, no [BLAST] - 24.05 is a
    ranged-only keyword and the melee row does not print it."""
    name = "Aeonstave"
    weapon_type = MELEE
    attacks = 3
    strength = 5
    ap = -1
    damage = 1


class AbyssalLanceRangedProfile(WeaponProfile):
    """Psychomancer, ranged row."""
    name = "Abyssal lance"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 6
    ap = -3
    damage = 3


class AbyssalLanceMeleeProfile(WeaponProfile):
    """Psychomancer, melee row - identical numbers to the ranged one, which is
    what the sheet prints."""
    name = "Abyssal lance"
    weapon_type = MELEE
    attacks = 1
    strength = 6
    ap = -3
    damage = 3


class StaffOfTomorrowProfile(WeaponProfile):
    """Orikan The Diviner. His only weapon, and the reason his profile carries
    WS 3+ rather than the 4+ the other two Crypteks print."""
    name = "Staff of Tomorrow"
    weapon_type = MELEE
    attacks = 2
    strength = 4
    ap = -3
    damage = 2  # preview/grouping placeholder only - damage_notation is rolled
    damage_notation = D3()
    devastating_wounds = True


# --- Destroyer Cult: Hexmark / Ophydian / Nekrosor Ammentar ----------------
#
# THE COLLISION SWEEP FOR THIS BATCH, run before a class was written, because
# the Necron block has now been burned in both directions:
#   * "Close combat weapon" is printed a THIRD time here (Hexmark Destroyer,
#     A4 WS3+ S5) and the numbers match NEITHER of the two that exist, so it
#     is a new class - the "same printed name, other numbers" trap.
#     Deliberately named after the NUMBERS rather than the datasheet, like its
#     two neighbours, because the Royal Warden prints this exact row too and
#     will share it.
#   * "Blade tail and whip coils" LOOKS like the Canoptek Wraiths' "Whip
#     Coils" and is not: different printed name, and different numbers
#     (A6 S6 AP-1 with [EXTRA ATTACKS] against A8 S5 AP0). Two classes, and
#     the resemblance is written down so neither is folded into the other.
#   * everything else in this batch is a name no datasheet has printed yet.
#
# WS/BS are on the PROFILES again - the Hexmark agrees with his own two rows
# (BS2+ ranged, WS3+ melee) and so does Nekrosor Ammentar (2+ throughout), so
# none of these carries an override.


class NecronCloseCombatWeaponA4S5Profile(WeaponProfile):
    """The A4/S5 Necron Close Combat Weapon (Hexmark Destroyer; the Royal
    Warden prints the identical row).

    The THIRD set of numbers this printed name carries in this faction, after
    NecronCloseCombatWeaponA1Profile (A1 S4) and
    NecronCloseCombatWeaponA2Profile (A2 S4)."""
    name = "Close Combat Weapon"
    weapon_type = MELEE
    attacks = 4
    strength = 5
    ap = 0
    damage = 1


class EnmiticDisintegratorPistolsProfile(WeaponProfile):
    """Hexmark Destroyer. Six [PISTOL] shots at BS2+ with [IGNORES COVER] -
    the whole datasheet is this row plus the two abilities that fire it out of
    turn."""
    name = "Enmitic disintegrator pistols"
    weapon_type = RANGED
    range_in = 18
    attacks = 6
    strength = 6
    ap = -2
    damage = 1
    pistol = True
    ignores_cover = True


class OphydianHyperphaseWeaponsProfile(WeaponProfile):
    """Ophydian Destroyers. A FOURTH hyperphase weapon, and a fourth set of
    numbers - the Lychguard's Hyperphase Sword (A3 S6 AP-2 D1), the Skorpekh
    Hyperphase Weapons (A4 S7 AP-2 D2) and the Skorpekh Lord's Hyperphase
    Harvester (A4 S10 AP-3 D3) are all different rows under similar names."""
    name = "Ophydian hyperphase weapons"
    weapon_type = MELEE
    attacks = 5
    strength = 4
    ap = -2
    damage = 2


class EnmiticDisintegratorsProfile(WeaponProfile):
    """Nekrosor Ammentar. NOT the Hexmark's "Enmitic disintegrator pistols"
    above (different printed name, different numbers), and not the Lokhust
    Heavy Destroyers' Enmitic Exterminator either - three enmitic guns, three
    classes."""
    name = "Enmitic disintegrators"
    weapon_type = RANGED
    range_in = 18
    attacks = 4
    strength = 6
    ap = -2
    damage = 1
    pistol = True
    ignores_cover = True
    sustained_hits = 2


class BladeTailAndWhipCoilsProfile(WeaponProfile):
    """Nekrosor Ammentar's [EXTRA ATTACKS] row - rule 24.11, so it is made IN
    ADDITION to the Unmaker Gauntlet rather than instead of it, which is why
    the two are not a firing-mode pair like the Void Dragon's spear."""
    name = "Blade tail and whip coils"
    weapon_type = MELEE
    attacks = 6
    strength = 6
    ap = -1
    damage = 1
    extra_attacks = True


class UnmakerGauntletProfile(WeaponProfile):
    """Nekrosor Ammentar's main melee row: S10 AP-3 D3 at WS2+."""
    name = "Unmaker Gauntlet"
    weapon_type = MELEE
    attacks = 6
    strength = 10
    ap = -3
    damage = 3


# --- Triarch: Praetorians / Stalker ----------------------------------------
#
# THE COLLISION SWEEP FOR THIS BATCH, run before a class was written - and it
# came out the OTHER way round from the Destroyer Cult's, which is the point of
# running it every time rather than assuming:
#
#   * "Particle caster" is printed on the Triarch Praetorians and is BYTE-FOR-
#     BYTE the Canoptek Wraiths' row already here (12" A3 S5 AP0 D1,
#     [DEVASTATING WOUNDS] [PISTOL]). It is SHARED, not forked. The only
#     column that differs is BS (4+ Wraiths, 3+ Praetorians) - and BS lives on
#     the model PROFILE in this engine, not on the weapon, so one class gives
#     each wielder its own printed skill for free. Cloning it would have been
#     the inverse of the Destroyer Cult's mistake and just as wrong.
#   * every other name in this batch is one no datasheet has printed yet.
#
# WS/BS ARE ON THE PROFILES, with ONE exception that is genuinely printed: the
# Triarch Stalker's rows say BS3+ for the focused heat ray and the heavy gauss
# cannon array, WS3+ for the forelimbs - and BS2+ for the particle shredder.
# A model whose own rows CONTRADICT each other is exactly what the per-weapon
# override is for, so the shredder carries one and nothing else does.


class RodOfCovenantRangedProfile(WeaponProfile):
    """Triarch Praetorians' default gun. One printed datasheet entry with a
    ranged AND a melee row, so it is two weapons in the loadout rather than a
    firing-mode pair - the arrangement the Aeonstave and the Eldritch Lance
    already use, and the opposite of the Void Dragon's melee strike/sweep pair
    (those are two profiles of ONE row, which rule 04.01 makes exclusive)."""
    name = "Rod of covenant"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 5
    ap = -2
    damage = 2


class RodOfCovenantMeleeProfile(WeaponProfile):
    """The melee half of the same printed entry - three attacks where the
    ranged row has one, everything else identical."""
    name = "Rod of covenant"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 5
    ap = -2
    damage = 2


class VoidbladeProfile(WeaponProfile):
    """Triarch Praetorians' melee alternative, taken together with the
    particle caster in place of the rod of covenant."""
    name = "Voidblade"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = -2
    damage = 1


class HeatRayFocusedProfile(WeaponProfile):
    """The heat ray's second mode. Defined before the dispersed profile below
    because that one names it as its alternate mode."""
    name = "Heat ray - focused"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 9
    ap = -4
    damage = 6            # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6()
    melta = 4


class HeatRayDispersedProfile(WeaponProfile):
    """Triarch Stalker's default gun, first of the two printed modes.

    [TORRENT] (24.37), so its printed BS column is "N/A" - no Hit roll is made
    and the skill is never read. The two modes are a firing-mode PAIR
    (overcharge_profile) because they are one datasheet entry: without that
    the Stalker would fire both in the same activation."""
    name = "Heat ray - dispersed"
    weapon_type = RANGED
    range_in = 12
    attacks = 2           # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(dice=2)   # printed "2D6"
    strength = 5
    ap = -1
    damage = 1
    ignores_cover = True
    torrent = True
    overcharge_profile = HeatRayFocusedProfile


class ParticleShredderProfile(WeaponProfile):
    """Triarch Stalker, first heat-ray replacement.

    The ONE per-weapon BS override in this batch, and it is printed: this row
    says 2+ while the Stalker's other two skill-carrying rows say 3+. Not the
    Canoptek Spyder's "particle beamer" and not the Praetorians' "particle
    caster" - three particle guns, three classes."""
    name = "Particle shredder"
    weapon_type = RANGED
    range_in = 18
    attacks = 6           # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(6)        # printed "D6+6"
    ballistic_skill = "2+"          # printed on the weapon, BETTER than the Stalker's own 3+
    strength = 7
    ap = 0
    damage = 1
    blast = True
    devastating_wounds = True


class HeavyGaussCannonArrayProfile(WeaponProfile):
    """Triarch Stalker, second heat-ray replacement. A separate class from the
    Lokhust Heavy Destroyers' "Gauss Destructor" and from the Doomsday Ark's
    "Gauss Flayer Array" - similar names, different rows."""
    name = "Heavy gauss cannon array"
    weapon_type = RANGED
    range_in = 24
    attacks = 6
    strength = 8
    ap = -2
    damage = 2
    lethal_hits = True


class StalkersForelimbsProfile(WeaponProfile):
    name = "Stalker's forelimbs"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 7
    ap = -1
    damage = 3


# --- Canoptek: Scarabs / Spyders / Doomstalker / Reanimator / Macrocytes /
# --- Tomb Crawlers / Geomancer ---------------------------------------------
#
# THE COLLISION SWEEP FOR THIS BATCH is the biggest one yet - fourteen printed
# names, and it came out THREE different ways:
#
#   * FORK, same name and other numbers. "Particle beamer" is printed on the
#     Tomb Blades at S5 and on the Canoptek Spyders at S6, everything else
#     identical - the classic trap. Both classes are now named after their
#     STRENGTH, the Necron block's own convention (see the three
#     NecronCloseCombatWeapon* classes): a bare ParticleBeamerProfile lies by
#     omission the moment the second carrier exists. Same for "Atomiser beam"
#     (Reanimator A3 AP-2 against Macrocytes A1 AP-1) and "Claws" (Macrocytes
#     A2 S4 against Tomb Crawlers A4 S6).
#   * INHERIT, same numbers plus one keyword. "Twin gauss flayer" IS the Necron
#     Warriors' Gauss Flayer with [TWIN-LINKED], and "Twin gauss reaper" IS the
#     Immortals' Gauss Reaper with it - so both subclass and override only the
#     name, the arrangement TwinGaussBlasterProfile already uses. Pinned
#     against their parents rather than against literals, so the two can never
#     drift apart silently.
#   * NEW, a name no datasheet has printed here before - the rest.
#
# WS/BS ARE ON THE PROFILES throughout: every one of these seven datasheets
# agrees with its own rows (the Spyder is BS3+/WS4+, the Doomstalker 4+/4+, the
# Geomancer 4+/4+, and so on), so not one weapon in this batch carries an
# override. The Triarch Stalker's particle shredder remains the only Necron
# weapon that needs one.


class FeederMandiblesProfile(WeaponProfile):
    """Canoptek Scarab Swarms' only weapon."""
    name = "Feeder mandibles"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 2
    ap = 0
    damage = 1
    lethal_hits = True


class ParticleBeamerS6Profile(WeaponProfile):
    """Canoptek Spyders. NOT the Tomb Blades' particle beamer: same printed
    name, same range, same D6 Attacks, same keywords - and S6 against their
    S5. See the collision sweep at the head of this block."""
    name = "Particle beamer"
    weapon_type = RANGED
    range_in = 18
    attacks = 3           # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D6()
    strength = 6
    ap = 0
    damage = 1
    blast = True
    devastating_wounds = True


class AutomatonClawsProfile(WeaponProfile):
    name = "Automaton claws"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 8
    ap = -2
    damage = 2


class DoomsdayBlasterProfile(WeaponProfile):
    """Canoptek Doomstalker. The hardest-hitting Necron gun in this engine
    (S14), and NOT the Doomsday Ark's "Doomsday cannon" - different printed
    name, different row."""
    name = "Doomsday blaster"
    weapon_type = RANGED
    range_in = 48
    attacks = 7           # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(1)        # printed "D6+1"
    strength = 14
    ap = -3
    damage = 3
    blast = True
    heavy = True


class TwinGaussFlayerProfile(GaussFlayerProfile):
    """Canoptek Doomstalker. The Necron Warriors' Gauss Flayer with
    [TWIN-LINKED] added and nothing else changed - so it INHERITS and
    overrides only the name, the arrangement TwinGaussBlasterProfile uses.
    Pinned against its parent in the suite rather than against literals: the
    assurance is that the two stay identical apart from the keyword."""
    name = "Twin gauss flayer"
    twin_linked = True


class DoomstalkerLimbsProfile(WeaponProfile):
    name = "Doomstalker limbs"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = 0
    damage = 1


class AtomiserBeamA3Profile(WeaponProfile):
    """Canoptek Reanimator, which carries TWO of them. Named after its numbers
    because the Canoptek Macrocytes print the same name at A1 AP-1."""
    name = "Atomiser beam"
    weapon_type = RANGED
    range_in = 12
    attacks = 3
    strength = 6
    ap = -2
    damage = 1


class ReanimatorsClawsProfile(WeaponProfile):
    name = "Reanimator's claws"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = 0
    damage = 1


class AtomiserBeamA1Profile(WeaponProfile):
    """Canoptek Macrocytes. The other half of the "Atomiser beam" fork -
    a weaker row under the same printed name."""
    name = "Atomiser beam"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 6
    ap = -1
    damage = 1


class GaussScalpelProfile(WeaponProfile):
    name = "Gauss scalpel"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 4
    ap = -1
    damage = 1
    lethal_hits = True


class TeslaCasterProfile(WeaponProfile):
    """Canoptek Macrocytes. Not the Immortals' "Tesla Carbine" - different
    printed name and a different row (that one is A2 S5 with [SUSTAINED HITS
    2]); three tesla guns would be three classes."""
    name = "Tesla caster"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 5
    ap = 0
    damage = 1
    assault = True
    sustained_hits = 1


class ClawsA2S4Profile(WeaponProfile):
    """Canoptek Macrocytes. Named after its numbers because the Canoptek Tomb
    Crawlers print "Claws" too, at A4 S6."""
    name = "Claws"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 4
    ap = -1
    damage = 1


class ClawsA4S6Profile(WeaponProfile):
    """Canoptek Tomb Crawlers - the other half of the "Claws" fork."""
    name = "Claws"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 6
    ap = -1
    damage = 1


class TransdimensionalIsolatorProfile(WeaponProfile):
    """Canoptek Tomb Crawlers. Not the Canoptek Wraiths' "Transdimensional
    Beamer" - similar name, different row."""
    name = "Transdimensional isolator"
    weapon_type = RANGED
    range_in = 12
    attacks = 2
    strength = 4
    ap = -2
    damage = 2


class TwinGaussReaperProfile(GaussReaperProfile):
    """Canoptek Tomb Crawlers: the Immortals' Gauss Reaper with [TWIN-LINKED],
    inherited for the same reason the Twin gauss flayer above is."""
    name = "Twin gauss reaper"
    twin_linked = True


class TremorglaiveShockWavePulseProfile(WeaponProfile):
    """The Tremorglaive's second ranged mode. Defined before the beam profile
    below because that one names it as its alternate mode.

    [TORRENT] (24.37), so its printed BS column is "N/A" - no Hit roll is made
    and the skill is never read."""
    name = "Tremorglaive - shock wave pulse"
    weapon_type = RANGED
    range_in = 18
    attacks = 5           # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(2)        # printed "D6+2"
    strength = 4
    ap = 0
    damage = 1
    ignores_cover = True
    torrent = True


class TremorglaiveReverberatingBeamProfile(WeaponProfile):
    """The Geomancer's default ranged mode, first of the two printed rows.
    A firing-mode PAIR, because the two are one datasheet entry - the same
    arrangement the Triarch Stalker's heat ray uses."""
    name = "Tremorglaive - reverberating beam"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 8
    ap = -2
    damage = 2
    melta = 2
    overcharge_profile = TremorglaiveShockWavePulseProfile


class TremorglaiveMeleeProfile(WeaponProfile):
    """The Tremorglaive's MELEE row - a third profile of the same printed
    weapon, but a melee one, so it is a separate weapon in the loadout rather
    than a mode of the ranged pair. The Void Dragon's spear and the Triarch
    Praetorians' rod of covenant use the same arrangement."""
    name = "Tremorglaive"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 8
    ap = -2
    damage = 2


# --- The other three C'tan - Deceiver, Nightbringer, Transcendent ----------
#
# COLLISION SWEEP, run over all thirteen remaining Necron datasheets before the
# first class below was written, and it came back EMPTY for these three: not
# one of their seven printed weapon names appears anywhere else in the corpus.
# They are the only batch in this backfill with nothing to share and nothing to
# fork - the Void Dragon's Spear, Voltaic Storm and Canoptek Tail Blades are
# its own, and no other datasheet prints a Gaze of Death or Golden Fists.
#
# NO PER-WEAPON SKILL OVERRIDE, and that is checked rather than assumed: all
# four C'tan print 2+ in every WS and BS cell they have, so the model profile
# answers for every row and nothing here contradicts its wielder. The single
# override in this faction remains the Triarch Stalker's particle shredder.

class GazeOfDeathProfile(WeaponProfile):
    name = "Gaze of Death"
    weapon_type = RANGED
    range_in = 18
    attacks = 1           # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D3()
    strength = 12
    ap = -3
    damage = 9            # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6(3)


class ScytheOfTheNightbringerSweepProfile(WeaponProfile):
    """The Scythe's second MELEE profile. Defined before the strike profile
    below because that one names it as its alternate mode - the arrangement
    the Void Dragon's Spear and the Triarch Stalker's heat ray both use."""
    name = "Scythe of the Nightbringer - Sweep"
    weapon_type = MELEE
    range_in = 2
    attacks = 14
    strength = 8
    ap = -2
    damage = 2


class ScytheOfTheNightbringerStrikeProfile(WeaponProfile):
    """One printed datasheet entry with two melee profiles, so they are a
    firing-mode PAIR (overcharge_profile) rather than two separate weapons -
    otherwise the Nightbringer would swing both in one activation, which rule
    04.01 forbids. Only this, the default mode, goes in the loadout."""
    name = "Scythe of the Nightbringer - Strike"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 14
    ap = -4
    damage = 8            # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6(2)
    devastating_wounds = True
    overcharge_profile = ScytheOfTheNightbringerSweepProfile


class CosmicInsanityProfile(WeaponProfile):
    """Three printed keywords at once, and [PRECISION] is the one that changes
    how it is resolved rather than how hard it hits (rule 24.28: the attacker
    picks which model in the target unit takes the wound)."""
    name = "Cosmic Insanity"
    weapon_type = RANGED
    range_in = 18
    attacks = 6
    strength = 6
    ap = -2
    damage = 2
    anti = ("CHARACTER", 4)
    devastating_wounds = True
    precision = True


class GoldenFistsProfile(WeaponProfile):
    name = "Golden Fists"
    weapon_type = MELEE
    range_in = 2
    attacks = 8
    strength = 10
    ap = -3
    damage = 3


class SeismicAssaultProfile(WeaponProfile):
    name = "Seismic Assault"
    weapon_type = RANGED
    range_in = 12
    attacks = 6
    strength = 8
    ap = -2
    damage = 2
    assault = True
    sustained_hits = 1


class CracklingTendrilsProfile(WeaponProfile):
    name = "Crackling Tendrils"
    weapon_type = MELEE
    range_in = 2
    attacks = 8
    strength = 10
    ap = -3
    damage = 6            # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D6()
    sustained_hits = 1


# --- The four Necron characters that lead ----------------------------------
#
# COLLISION SWEEP, run over the corpus before the first class below:
#   * "Close combat weapon" (Royal Warden, A4 WS3+ S5) is the THIRD printing of
#     that name in this faction and is BYTE-IDENTICAL to the Hexmark
#     Destroyer's, so NecronCloseCombatWeaponA4S5Profile is REUSED rather than
#     cloned - the fork this repo had to make three times in stage 3 has an
#     inverse, and cloning here would be it. Its own docstring named the Royal
#     Warden as the sharer that would arrive; both wielders resolve WS3+ off
#     their own profile, which is why one class can serve them.
#   * "Overlord's blade" is likewise identical to the Overlord's, so
#     OverlordsBladeProfile is reused. (The Catacomb Command Barge in stage 8
#     prints the same row again.)
#   * The other four names collide with NOTHING anywhere in the corpus.
#
# NO PER-WEAPON SKILL OVERRIDE: every row below agrees with its wielder's own
# profile. The Gauntlet of Fire prints BS "N/A", which is [TORRENT] (rule
# 24.37 - no Hit roll is made at all) and not a skill that disagrees.

class RelicGaussBlasterProfile(WeaponProfile):
    name = "Relic Gauss Blaster"
    weapon_type = RANGED
    range_in = 24
    attacks = 2
    strength = 5
    ap = -1
    damage = 2
    lethal_hits = True
    rapid_fire = 2


class GauntletOfFireProfile(WeaponProfile):
    """BS "N/A" on the printed row is [TORRENT]: rule 24.37 makes the attacks
    hit automatically, so there is no skill to disagree with."""
    name = "Gauntlet of Fire"
    weapon_type = RANGED
    range_in = 12
    attacks = 1           # grouping/preview placeholder only - attacks_notation is what is rolled
    attacks_notation = D6()
    strength = 5
    ap = -1
    damage = 1
    ignores_cover = True
    torrent = True


class StaffOfTheDestroyerRangedProfile(WeaponProfile):
    """One printed NAME, two rows - and unlike the Nightbringer's Scythe these
    are NOT a firing-mode pair. One is ranged and one is melee, so Imotekh
    carries both at once and rule 04.01 never has to choose between them; an
    overcharge_profile here would silently take one of his two weapons away.
    The Void Dragon's Spear and the Aeldari Star Lance are the same
    arrangement."""
    name = "Staff of the Destroyer"
    weapon_type = RANGED
    range_in = 18
    attacks = 3
    strength = 6
    ap = -3
    damage = 2


class StaffOfTheDestroyerMeleeProfile(WeaponProfile):
    """The melee half of the pair above. Same name, same S/AP/D, one more
    Attack and [DEVASTATING WOUNDS] - pinned against its ranged twin in the
    suite rather than against literals, since a copy would pass either read on
    its own."""
    name = "Staff of the Destroyer"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 6
    ap = -3
    damage = 2
    devastating_wounds = True


class EmpathicObliteratorProfile(WeaponProfile):
    """[SUSTAINED HITS D3] - the dice-notation form, so one die per critical
    hit is rolled for real rather than a fixed X being applied."""
    name = "Empathic Obliterator"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 7
    ap = 0
    damage = 3            # grouping/preview placeholder only - damage_notation is what is rolled
    damage_notation = D3()
    sustained_hits = 1    # grouping/preview placeholder only - sustained_hits_notation is what is rolled
    sustained_hits_notation = D3()


# ---------------------------------------------------------------------------
# Death Guard - see game/factions/death_guard.py
#
# Two naming notes, both of the kind CLAUDE.md's error class 11 is about:
#
#   * PLAIN NAMES ARE USED HERE (Boltgun, Meltagun, Power Fist, Multi-melta)
#     because Death Guard is currently the only faction in this engine that
#     prints them. A loyalist Space Marine faction prints several of the same
#     NAMES with DIFFERENT numbers - if one is ever added, these need renaming
#     for their datasheet or their numbers, not copying.
#   * "Plaguespitter" is printed on the Foetid Bloat-drone AND the Plagueburst
#     Crawler with IDENTICAL numbers, so both share one class. Plague Marines'
#     "plague spewer" is a different weapon (S5, Anti-Infantry 2+) with a
#     confusingly similar name, and the Deathshroud's "plaguespurt gauntlet"
#     is a third - all three are separate classes on purpose.
#
# The keyword column rendered EMPTY for every weapon row on every Death Guard
# datasheet, exactly as it did for all thirteen Necron sheets - the ~15th
# occurrence of that artefact. The NAME column is followed throughout, and the
# values here come from per-weapon follow-up queries rather than the bundled
# summary, which had merged several weapons' keywords into one list.
# ---------------------------------------------------------------------------


class BoltgunProfile(WeaponProfile):
    name = "Boltgun"
    weapon_type = RANGED
    range_in = 24
    attacks = 2
    strength = 4
    ap = 0
    damage = 1
    lethal_hits = True


class BoltPistolProfile(WeaponProfile):
    """Printed identically on Plague Marines and the Malignant Plaguecaster,
    so one class serves both - the same call the two Warlock Conclaves' shared
    weapons get."""
    name = "Bolt Pistol"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 4
    ap = 0
    damage = 1
    lethal_hits = True
    pistol = True


class BlightLauncherProfile(WeaponProfile):
    name = "Blight Launcher"
    weapon_type = RANGED
    range_in = 24
    attacks = 2  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D3()
    strength = 6
    ap = -1
    damage = 2
    blast = 1
    lethal_hits = True


class MeltagunProfile(WeaponProfile):
    name = "Meltagun"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 9
    ap = -4
    damage = 3  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6()
    melta = 2


class PlagueBelcherProfile(WeaponProfile):
    """Printed BS is "N/A" - no ballistic_skill override needed, since
    [TORRENT] skips the Hit roll entirely."""
    name = "Plague Belcher"
    weapon_type = RANGED
    range_in = 12
    attacks = 3  # preview/grouping placeholder only
    attacks_notation = D6()
    strength = 4
    ap = 0
    damage = 1
    anti = ("INFANTRY", 4)
    ignores_cover = True
    torrent = True


class PlagueSpewerProfile(WeaponProfile):
    """The bigger of the two Plague Marine flamers: S5/AP-1 and Anti-Infantry
    2+ where the belcher is S4/AP0 and 4+."""
    name = "Plague Spewer"
    weapon_type = RANGED
    range_in = 12
    attacks = 3  # preview/grouping placeholder only
    attacks_notation = D6()
    strength = 5
    ap = -1
    damage = 1
    anti = ("INFANTRY", 2)
    ignores_cover = True
    torrent = True


class PlasmaGunSuperchargeProfile(WeaponProfile):
    """Defined above the standard profile because overcharge_profile names the
    class object, so it has to already exist."""
    name = "Plasma Gun - supercharge"
    weapon_type = RANGED
    range_in = 24
    attacks = 1
    strength = 8
    ap = -3
    damage = 2
    hazardous = True
    rapid_fire = 1


class PlasmaGunProfile(WeaponProfile):
    name = "Plasma Gun"
    weapon_type = RANGED
    range_in = 24
    attacks = 1
    strength = 7
    ap = -2
    damage = 1
    rapid_fire = 1
    overcharge_profile = PlasmaGunSuperchargeProfile


class PlasmaPistolSuperchargeProfile(WeaponProfile):
    name = "Plasma Pistol - supercharge"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 8
    ap = -3
    damage = 2
    hazardous = True
    pistol = True


class PlasmaPistolProfile(WeaponProfile):
    name = "Plasma Pistol"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 7
    ap = -2
    damage = 1
    pistol = True
    overcharge_profile = PlasmaPistolSuperchargeProfile


class PlaguespurtGauntletProfile(WeaponProfile):
    """The Deathshroud Terminators' only ranged weapon. [PISTOL] as well as
    [TORRENT], so it can be fired while the unit is in Engagement Range."""
    name = "Plaguespurt Gauntlet"
    weapon_type = RANGED
    range_in = 12
    attacks = 3  # preview/grouping placeholder only
    attacks_notation = D6()
    strength = 3
    ap = 0
    damage = 1
    anti = ("INFANTRY", 4)
    ignores_cover = True
    pistol = True
    torrent = True


class PlaguespitterProfile(WeaponProfile):
    """Shared by the Foetid Bloat-drone and the Plagueburst Crawler - the same
    printed name with the same numbers on both, so one class. NOT the Plague
    Marines' plague spewer, which is S5/AP-1, nor the Deathshroud's
    plaguespurt gauntlet, which is S3/AP0 and a [PISTOL]."""
    name = "Plaguespitter"
    weapon_type = RANGED
    range_in = 12
    attacks = 3  # preview/grouping placeholder only
    attacks_notation = D6()
    strength = 6
    ap = -1
    damage = 1
    anti = ("INFANTRY", 2)
    ignores_cover = True
    torrent = True


class PlagueWindFocusedProfile(WeaponProfile):
    """The Malignant Plaguecaster's second fire mode - more shots and better
    S/AP, at the cost of [HAZARDOUS]."""
    name = "Plague Wind - focused witchfire"
    weapon_type = RANGED
    range_in = 12
    attacks = 6  # preview/grouping placeholder only
    attacks_notation = D6(3)
    strength = 6
    ap = -2
    damage = 2  # preview/grouping placeholder only
    damage_notation = D3()
    hazardous = True
    psychic = True
    torrent = True


class PlagueWindProfile(WeaponProfile):
    name = "Plague Wind - witchfire"
    weapon_type = RANGED
    range_in = 12
    attacks = 3  # preview/grouping placeholder only
    attacks_notation = D6()
    strength = 4
    ap = -1
    damage = 2  # preview/grouping placeholder only
    damage_notation = D3()
    psychic = True
    torrent = True
    overcharge_profile = PlagueWindFocusedProfile


class InfernalCannonProfile(WeaponProfile):
    name = "Infernal Cannon"
    weapon_type = RANGED
    range_in = 24
    attacks = 3
    ballistic_skill = "2+"
    strength = 5
    ap = -1
    damage = 2
    lethal_hits = True


class BileSpurtProfile(WeaponProfile):
    name = "Bile Spurt"
    weapon_type = RANGED
    range_in = 12
    attacks = 3
    strength = 5
    ap = 0
    damage = 1
    lethal_hits = True


class MissileLauncherFragProfile(WeaponProfile):
    """The Myphitic Blight-hauler's. Distinct from the Defiler's HEAVY
    missile launcher, which prints different numbers under a different name.

    This docstring used to claim the opposite of what the sheet prints ("its
    keyword column really is empty for this row ... only the krak carries
    [LETHAL HITS]"). The printed pair is the other way round: the FRAG row
    carries [BLAST] and the krak row carries nothing. Both halves are fixed;
    kept as a note because a comment asserting a checked fact is exactly what
    stops the next reader from checking it."""
    name = "Missile Launcher - frag"
    blast = 1  # plain [BLAST] is X=1, see WeaponProfile.blast
    weapon_type = RANGED
    range_in = 48
    attacks = 3  # preview/grouping placeholder only
    attacks_notation = D6()
    strength = 4
    ap = 0
    damage = 1


class MissileLauncherKrakProfile(WeaponProfile):
    name = "Missile Launcher - krak"
    weapon_type = RANGED
    range_in = 48
    attacks = 1
    strength = 9
    ap = -2
    damage = 3  # preview/grouping placeholder only
    damage_notation = D6()
    # NO [LETHAL HITS]: this row's keyword column is empty on the printed
    # sheet. The pair was transcribed the wrong way round - it is the FRAG
    # half that carries a keyword ([BLAST]), and the sibling profile's
    # docstring said the opposite in as many words until the keyword sweep
    # put both rows beside their printed ones.


class MultiMeltaProfile(WeaponProfile):
    name = "Multi-melta"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 9
    ap = -4
    damage = 3  # preview/grouping placeholder only
    damage_notation = D6()
    lethal_hits = True
    melta = 2


class EntropyCannonProfile(WeaponProfile):
    name = "Entropy Cannon"
    weapon_type = RANGED
    range_in = 36
    attacks = 1
    strength = 10
    ap = -3
    damage = 4  # preview/grouping placeholder only
    damage_notation = D6(1)
    lethal_hits = True


class HeavySluggerProfile(WeaponProfile):
    name = "Heavy Slugger"
    weapon_type = RANGED
    range_in = 36
    attacks = 4
    strength = 5
    ap = -1
    damage = 1
    lethal_hits = True


class PlagueburstMortarProfile(WeaponProfile):
    """The Plagueburst Crawler's main gun, and the trigger for its
    Spore-laced Shock Waves ability - see game/spore_laced_shock_waves.py,
    which identifies it by this class."""
    name = "Plagueburst Mortar"
    weapon_type = RANGED
    range_in = 48
    attacks = 6  # preview/grouping placeholder only
    attacks_notation = D6(3)
    strength = 8
    ap = -1
    damage = 2
    blast = 1
    indirect_fire = True
    lethal_hits = True


class RothailVolleyGunProfile(WeaponProfile):
    name = "Rothail Volley Gun"
    weapon_type = RANGED
    range_in = 36
    attacks = 3
    strength = 5
    ap = 0
    damage = 1
    lethal_hits = True
    rapid_fire = 3


class EctoplasmaDestructorProfile(WeaponProfile):
    name = "Ectoplasma Destructor"
    weapon_type = RANGED
    range_in = 36
    attacks = 3  # preview/grouping placeholder only
    attacks_notation = D6()
    strength = 12
    ap = -3
    damage = 3
    blast = 1  # plain [BLAST] is X=1, see WeaponProfile.blast - missing until the keyword sweep; the printed row is "blast, lethal hits" and the Defiler's other two D6-attack guns already carried it
    lethal_hits = True


class ExcruciatorCannonProfile(WeaponProfile):
    name = "Excruciator Cannon"
    weapon_type = RANGED
    range_in = 36
    attacks = 6
    strength = 6
    ap = -1
    damage = 2
    lethal_hits = True


class HadesBattleCannonProfile(WeaponProfile):
    name = "Hades Battle Cannon"
    weapon_type = RANGED
    range_in = 48
    attacks = 6  # preview/grouping placeholder only
    attacks_notation = D6(3)
    strength = 10
    ap = -1
    damage = 3
    blast = 1
    lethal_hits = True


class HadesLascannonProfile(WeaponProfile):
    name = "Hades Lascannon"
    weapon_type = RANGED
    range_in = 48
    attacks = 2
    strength = 12
    ap = -3
    damage = 4  # preview/grouping placeholder only
    damage_notation = D6(1)
    lethal_hits = True


class HeavyBaleflamerProfile(WeaponProfile):
    name = "Heavy Baleflamer"
    weapon_type = RANGED
    range_in = 12
    attacks = 6  # preview/grouping placeholder only
    attacks_notation = D6(3)
    strength = 7
    ap = -2
    damage = 2
    ignores_cover = True
    torrent = True


class DefilerHeavyMissileLauncherFragProfile(WeaponProfile):
    """Named for its datasheet because the Myphitic Blight-hauler prints a
    plain "missile launcher" with different numbers - the same reason the Dark
    Reapers' launcher carries its own prefix."""
    name = "Heavy Missile Launcher - frag"
    weapon_type = RANGED
    range_in = 48
    attacks = 7  # preview/grouping placeholder only
    attacks_notation = D6(0, 2)   # "2D6"
    strength = 5
    ap = -1
    damage = 1
    blast = 1
    lethal_hits = True


class DefilerHeavyMissileLauncherKrakProfile(WeaponProfile):
    name = "Heavy Missile Launcher - krak"
    weapon_type = RANGED
    range_in = 48
    attacks = 2
    strength = 10
    ap = -2
    damage = 4  # preview/grouping placeholder only
    damage_notation = D6(1)
    lethal_hits = True


class HeavyReaperAutocannonProfile(WeaponProfile):
    """Three offensive keywords at once - the only weapon in this faction with
    [DEVASTATING WOUNDS], and one of the two Defiler options that costs points."""
    name = "Heavy Reaper Autocannon"
    weapon_type = RANGED
    range_in = 48
    attacks = 4
    strength = 9
    ap = -1
    damage = 3
    devastating_wounds = True
    lethal_hits = True
    sustained_hits = 1


class MagmaCuttersProfile(WeaponProfile):
    name = "Magma Cutters"
    weapon_type = RANGED
    range_in = 12
    attacks = 2
    strength = 9
    ap = -4
    damage = 3  # preview/grouping placeholder only
    damage_notation = D6()
    lethal_hits = True
    melta = 2


# --- Death Guard melee ------------------------------------------------------

class PlagueKnivesProfile(WeaponProfile):
    name = "Plague Knives"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 4
    ap = 0
    damage = 1
    lethal_hits = True


class BuboticWeaponsProfile(WeaponProfile):
    name = "Bubotic Weapons"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 5
    ap = -2
    damage = 1
    lethal_hits = True


class HeavyPlagueWeaponProfile(WeaponProfile):
    """Fewer attacks at a WORSE WS than plague knives, in exchange for S8/AP-2 -
    so a Plague Marine carrying one is a real 04.01 choice, not an upgrade."""
    name = "Heavy Plague Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    weapon_skill = "4+"
    strength = 8
    ap = -2
    damage = 2
    lethal_hits = True


class PowerFistProfile(WeaponProfile):
    name = "Power Fist"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 8
    ap = -2
    damage = 2
    lethal_hits = True


class ImprovisedWeaponProfile(WeaponProfile):
    name = "Improvised Weapon"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    weapon_skill = "5+"
    strength = 3
    ap = 0
    damage = 1
    lethal_hits = True


class LakrimaeSweepProfile(WeaponProfile):
    name = "Lakrimae - sweep"
    weapon_type = MELEE
    range_in = 2
    attacks = 12
    weapon_skill = "2+"
    strength = 6
    ap = -1
    damage = 1
    lethal_hits = True


class LakrimaeStrikeProfile(WeaponProfile):
    """Typhus' manreaper. ONE printed datasheet entry with two profiles, so it
    is modelled as a fire mode rather than two weapons - otherwise rule 04.01
    would let him swing both."""
    name = "Lakrimae - strike"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    weapon_skill = "2+"
    strength = 9
    ap = -2
    damage = 3
    lethal_hits = True
    overcharge_profile = LakrimaeSweepProfile


class CorruptedStaffProfile(WeaponProfile):
    name = "Corrupted Staff"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 6
    ap = -1
    damage = 2  # preview/grouping placeholder only
    damage_notation = D3()
    lethal_hits = True
    psychic = True


class HellforgedWeaponsSweepProfile(WeaponProfile):
    name = "Hellforged Weapons - sweep"
    weapon_type = MELEE
    range_in = 2
    attacks = 14
    weapon_skill = "2+"
    strength = 6
    ap = -1
    damage = 1
    lethal_hits = True


class HellforgedWeaponsStrikeProfile(WeaponProfile):
    name = "Hellforged Weapons - strike"
    weapon_type = MELEE
    range_in = 2
    attacks = 7
    weapon_skill = "2+"
    strength = 8
    ap = -2
    damage = 3
    lethal_hits = True
    overcharge_profile = HellforgedWeaponsSweepProfile


class HideousMutationsProfile(WeaponProfile):
    """The Chaos Spawn's only weapon, and one of the few in this engine with a
    dice-notation Attacks characteristic AND no keywords at all."""
    name = "Hideous Mutations"
    weapon_type = MELEE
    range_in = 2
    attacks = 5  # preview/grouping placeholder only
    attacks_notation = D6(2)
    weapon_skill = "4+"
    strength = 5
    ap = -1
    damage = 2


class ManreaperSweepProfile(WeaponProfile):
    """Note the WORSE weapon skill on the sweep (3+ against the strike's 2+),
    which the Lakrimae and Hellforged pairs do not have - so the two halves of
    this weapon differ in three characteristics, not two."""
    name = "Manreaper - sweep"
    weapon_type = MELEE
    range_in = 2
    attacks = 8
    weapon_skill = "3+"
    strength = 4
    ap = -1
    damage = 1
    lethal_hits = True


class ManreaperStrikeProfile(WeaponProfile):
    name = "Manreaper - strike"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    weapon_skill = "2+"
    strength = 8
    ap = -2
    damage = 2
    lethal_hits = True
    overcharge_profile = ManreaperSweepProfile


class FleshmowerProfile(WeaponProfile):
    name = "Fleshmower"
    weapon_type = MELEE
    range_in = 2
    attacks = 10
    strength = 7
    ap = -1
    damage = 2
    lethal_hits = True


class PlagueProbeProfile(WeaponProfile):
    name = "Plague Probe"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = -1
    damage = 1
    lethal_hits = True


class GnashingMawProfile(WeaponProfile):
    name = "Gnashing Maw"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 6
    ap = -1
    damage = 1
    lethal_hits = True


class ArmouredTracksProfile(WeaponProfile):
    name = "Armoured Tracks"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    weapon_skill = "4+"
    strength = 6
    ap = 0
    damage = 1


class ElectroscourgeProfile(WeaponProfile):
    """[EXTRA ATTACKS] (24.11), so it never takes part in the Defiler's 04.01
    choice - it is swung in ADDITION to whatever else the model has."""
    name = "Electroscourge"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 12
    ap = -2
    damage = 2
    extra_attacks = True
    sustained_hits = 2


class ShearingClawsSweepProfile(WeaponProfile):
    name = "Shearing Claws - sweep"
    weapon_type = MELEE
    range_in = 2
    attacks = 10
    strength = 6
    ap = -2
    damage = 1
    lethal_hits = True


class ShearingClawsStrikeProfile(WeaponProfile):
    """S16 is the highest Strength characteristic in this engine - checked
    rather than assumed, because a number that far outside the usual band reads
    like a transcription slip."""
    name = "Shearing Claws - strike"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 16
    ap = -3
    damage = 4  # preview/grouping placeholder only
    damage_notation = D6(1)
    lethal_hits = True
    overcharge_profile = ShearingClawsSweepProfile


# --- Wraith Constructs: Wraithlord and Wraithblades -------------------------
#
# The Wraithlord's ranged rows are the shared Aeldari guns (bright lance,
# flamer, both missile launcher modes, scatter laser, shuriken cannon,
# shuriken catapult, starcannon) and are REUSED rather than re-declared: not
# one of them pins ballistic_skill, so each reads the firing model's own BS.
# That is what makes the reuse safe here - the Wraithlord prints BS4+ where
# the War Walker prints BS3+, and a hardcoded skill on a shared class is
# exactly the MissilePodProfile bug this repo already paid for once.


class GhostglaiveSweepProfile(WeaponProfile):
    """The wide profile of the Wraithlord's ghostglaive."""
    name = "Ghostglaive - Sweep"
    weapon_type = MELEE
    range_in = 2
    attacks = 8
    strength = 7
    ap = -2
    damage = 2


class GhostglaiveStrikeProfile(WeaponProfile):
    """One datasheet entry, two printed profiles, so the second is an alternate
    FIRING MODE and not a second weapon - the same shape the missile launcher's
    starshot/sunburst pair uses. Strike is the row printed first, so it is the
    granted instance; handing out both would give the model two glaives."""
    name = "Ghostglaive - Strike"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 10
    ap = -3
    damage = 4  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6(1)
    overcharge_profile = GhostglaiveSweepProfile


class WraithboneFistsProfile(WeaponProfile):
    """NOT the Wraithbone Hull, which is the grav-tank row at A3/WS4+/S6/AP0/D1.
    These are A4/S7/AP-2/D2 - three characteristics apart, so a separate class
    rather than a shared one. Pinned against the hull in the test."""
    name = "Wraithbone Fists"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 7
    ap = -2
    damage = 2


class GhostswordsProfile(WeaponProfile):
    """The Wraithblades' default: more attacks, less strength than the axe."""
    name = "Ghostswords"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 5
    ap = -2
    damage = 2


class GhostaxeProfile(WeaponProfile):
    """The traded-down profile: the axe costs two attacks and buys S7, and it
    comes bundled with the forceshield (a 4+ invulnerable save), which is why
    the wargear option is one swap and not two."""
    name = "Ghostaxe"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 7
    ap = -2
    damage = 2


# --- Support Weapon Platforms (D-cannon / Shadow Weaver / Vibro Cannon) ------
#
# Three datasheets, one chassis. The shuriken catapult and the A2 close combat
# weapon are the shared Aeldari rows and are reused; only the heavy gun differs,
# which is the whole difference between the three sheets. None of the three
# pins ballistic_skill - the platforms print BS3+ on every row, so the model's
# own skill is the right source and a per-weapon override would be the
# MissilePodProfile mistake again.


class DCannonProfile(WeaponProfile):
    """The heaviest gun in the engine by Strength: S16, and D6+2 damage on top
    of [DEVASTATING WOUNDS]. Attacks is a D3, so both characteristics are
    notations rather than fixed numbers."""
    name = "D-cannon"
    weapon_type = RANGED
    range_in = 24
    attacks = 2  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D3()
    strength = 16
    ap = -4
    damage = 5  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6(2)
    blast = 1
    devastating_wounds = True
    indirect_fire = True


class ShadowWeaverProfile(WeaponProfile):
    """Volume rather than weight: D6+2 shots at S6/AP-1/D1, indirect."""
    name = "Shadow Weaver"
    weapon_type = RANGED
    range_in = 48
    attacks = 5  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(2)
    strength = 6
    ap = -1
    damage = 1
    blast = 1
    indirect_fire = True


class VibroCannonProfile(WeaponProfile):
    """The only one of the three with NO weapon keywords at all - checked
    rather than assumed, the same doubt BrightLanceProfile records, because an
    S9 48" gun with nothing attached reads like a transcription gap. Its
    stacking is a datasheet ability (Sonic Destruction), not a keyword."""
    name = "Vibro Cannon"
    weapon_type = RANGED
    range_in = 48
    attacks = 3  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6()
    strength = 9
    ap = -1
    damage = 2


# --- Fire Prism / Night Spinner / Vypers ------------------------------------


class PrismCannonFocusedLancesProfile(WeaponProfile):
    """The heavy profile: two shots at S18/AP-4/D6, the highest Strength on any
    Aeldari gun here.

    Its printed [LINKED FIRE] keyword is NOT modelled - see the Fire Prism's
    abilities_text for what the keyword does and why re-basing a weapon's range
    and visibility onto a second model is a targeting-layer change rather than
    a weapon flag."""
    name = "Prism Cannon - Focused Lances"
    weapon_type = RANGED
    range_in = 60
    attacks = 2
    strength = 18
    ap = -4
    damage = 6


class PrismCannonDispersedPulseProfile(WeaponProfile):
    """One datasheet entry, two printed profiles, so the second is an alternate
    FIRING MODE rather than a second weapon - the shape the missile launcher's
    starshot/sunburst pair uses. Dispersed pulse is printed first, so it is the
    granted instance; handing out both would give the tank two cannons.

    2D6 attacks, not D6+3: same mean, different spread, and game/dice_notation.
    py grew its `dice` field precisely so a printed "2D6" is not quietly
    restated (Dark Reapers' Tempest Launcher was the first)."""
    name = "Prism Cannon - Dispersed Pulse"
    weapon_type = RANGED
    range_in = 60
    attacks = 7  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(dice=2)
    strength = 6
    ap = -2
    damage = 2
    blast = 1
    overcharge_profile = PrismCannonFocusedLancesProfile


class DoomweaverProfile(WeaponProfile):
    """The Night Spinner's gun: a lot of indirect, twin-linked shots."""
    name = "Doomweaver"
    weapon_type = RANGED
    range_in = 48
    attacks = 6  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(3)
    strength = 7
    ap = -1
    damage = 2
    blast = 1
    indirect_fire = True
    twin_linked = True


class VyperScatterLaserProfile(ScatterLaserProfile):
    """The Vyper prints [SUSTAINED HITS 2] where every other carrier of this
    row prints 1 - same name, same numbers otherwise, one keyword value
    different, which is exactly the case that needs its own class. Inherits so
    the shared characteristics cannot drift apart from the base row."""
    sustained_hits = 2


class VyperStarcannonProfile(StarcannonProfile):
    """Printed BS2+ on the Vyper's datasheet, where its five other weapon rows
    all print 3+ - so this is a genuine per-WEAPON override rather than the
    model's own skill, which is the one case WeaponProfile.ballistic_skill
    exists for (The Twin Lance and Darkstrider are the others).

    Transcribed as printed. It looks like a typo next to the rest of the sheet,
    which is exactly why it is pinned in the test with this note attached: a
    later correction should be a visible one-line change, not a silent one."""
    ballistic_skill = "2+"


# --- Spiritseer --------------------------------------------------------------


class WitchStaffProfile(WeaponProfile):
    """The Spiritseer's melee row. The Witchblade's twin in everything but
    Damage: A2/S3/AP0 with [ANTI-INFANTRY 2+] and [PSYCHIC] on both, but this
    one rolls a D3 where the Witchblade is a flat 2 - so a separate class, and
    pinned against the Witchblade in the test rather than against literals."""
    name = "Witch Staff"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 3
    ap = 0
    damage = 2  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D3()
    psychic = True
    anti = ("INFANTRY", 2)


# --- Autarchs and Maugan Ra --------------------------------------------------
#
# The Autarch's wargear is the Aspect Warriors' arsenal in a character's hands,
# and three of those rows print DIFFERENT numbers on his sheet than on the
# squad's. Each of those gets its own class rather than sharing - the recurring
# "same printed name, different numbers" case - and each INHERITS, so the
# characteristics they do share cannot drift apart.


class AutarchBansheeBladeProfile(BansheeBladeProfile):
    """A5 in an Autarch's hands, against the Howling Banshee Exarch's A2.
    Everything else - S4/AP-2/D2 and [ANTI-INFANTRY 3+] - is the same row."""
    attacks = 5


class AutarchScorpionChainswordProfile(ScorpionChainswordProfile):
    """A7 against the Striking Scorpion's A4. Same S4/AP-1/D1 and the same
    [SUSTAINED HITS 1]."""
    attacks = 7


class AutarchReaperLauncherStarswarmProfile(ReaperLauncherStarswarmProfile):
    """TWO differences from the Dark Reapers' row, both printed: it is [HEAVY],
    and it is S4 where theirs is S5. Checked against their datasheet rather
    than assumed, because a shared class would have been the obvious move."""
    strength = 4
    heavy = True


class AutarchReaperLauncherStarshotProfile(ReaperLauncherStarshotProfile):
    """Same numbers as the Dark Reapers' starshot, plus [HEAVY]."""
    heavy = True
    overcharge_profile = AutarchReaperLauncherStarswarmProfile


class StarGlaiveProfile(WeaponProfile):
    """The Autarch's default melee weapon. No keywords at all."""
    name = "Star Glaive"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 6
    ap = -3
    damage = 3


class MaugetarRangedProfile(WeaponProfile):
    """Maugan Ra's reaper launcher and scythe in one - the ranged half."""
    name = "Maugetar"
    weapon_type = RANGED
    range_in = 36
    attacks = 6
    strength = 7
    ap = -2
    damage = 2
    devastating_wounds = True
    ignores_cover = True


class MaugetarMeleeProfile(WeaponProfile):
    """...and the melee half. ONE printed weapon with a ranged row and a melee
    row, like the Star Lance and the Singing Spear - so both are granted, and
    that is not a duplicate."""
    name = "Maugetar"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    strength = 6
    ap = -2
    damage = 2


# --- Exodites ----------------------------------------------------------------
#
# Four datasheets on one drakesteed, and the Fangs and Talons plus the Solar
# Carbine are shared by every one of them that prints them.
#
# The Laser Lance's RANGED row is the Shining Spears' exactly, so it is reused.
# Its MELEE row is not: S6 against their S5, and no [ANTI-MONSTER/VEHICLE].


class SolarCarbineProfile(WeaponProfile):
    """The Exodite sidearm."""
    name = "Solar Carbine"
    weapon_type = RANGED
    range_in = 18
    attacks = 2
    strength = 4
    ap = 0
    damage = 1
    rapid_fire = 2


class DrakesteedFangsAndTalonsProfile(WeaponProfile):
    """The mount itself. [EXTRA ATTACKS] (24.11), so it never competes with
    the rider's weapon under 04.01."""
    name = "Drakesteed Fangs and Talons"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 5
    ap = -1
    damage = 1
    extra_attacks = True


class ExoditeLaserLanceMeleeProfile(WeaponProfile):
    """NOT the Shining Spears' melee row: S6 against their S5, and it prints no
    [ANTI-MONSTER/VEHICLE] where theirs does. Two differences, so its own class
    - and both are pinned against theirs rather than against literals."""
    name = "Laser Lance"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = -2
    damage = 3
    lance = True           # [LANCE], rule 24.21


class MoonbladesProfile(WeaponProfile):
    """The Clanblade's own blades."""
    name = "Moonblades"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    weapon_skill = "2+"    # its own row prints 2+ where the drakesteed's prints 3+
    strength = 4
    ap = -2
    damage = 2
    lethal_hits = True
    twin_linked = True


class ExoditeLongRifleProfile(WeaponProfile):
    """The Leystalker's rifle, and the first weapon here whose [DEVASTATING
    WOUNDS] is CONDITIONAL on the target: the printed keyword line reads
    "DEVASTATING WOUNDS: non-MONSTER/VEHICLE".

    So `devastating_wounds` itself stays False and the grant is applied in the
    adjuster chain against the actual target - see
    game/conditional_devastating_wounds.py. Setting the flat flag instead would
    hand it [DEVASTATING WOUNDS] against exactly the targets the printed line
    excludes."""
    name = "Long Rifle"
    weapon_type = RANGED
    range_in = 36
    attacks = 2
    ballistic_skill = "2+"
    strength = 6
    ap = -2
    damage = 3
    precision = True
    devastating_wounds_vs_non_monster_vehicle = True


class HuntingBladesProfile(WeaponProfile):
    name = "Hunting Blades"
    weapon_type = MELEE
    range_in = 2
    attacks = 2
    strength = 3
    ap = -1
    damage = 1


class SongOfWaningProfile(WeaponProfile):
    """[ANTI-MONSTER/VEHICLE 3+] written as the two entries this engine already
    uses for that printed pair, so the "best threshold wins" fold applies."""
    name = "Song of Waning"
    weapon_type = RANGED
    range_in = 24
    attacks = 3
    strength = 4
    ap = -2
    damage = 3
    anti = (("MONSTER", 3), ("VEHICLE", 3))
    psychic = True


class VenomcrestSpitProfile(WeaponProfile):
    """Printed BS is "-", which is [TORRENT] - no ballistic_skill override
    needed, the same call AeldariFlamerProfile records.

    [ANTI-non-MONSTER/VEHICLE 3+] is the NEGATED form, which no [ANTI-X] entry
    could express: see game/shooting.py's NON_MONSTER_VEHICLE sentinel."""
    name = "Venomcrest Spit"
    weapon_type = RANGED
    range_in = 12
    attacks = 3
    strength = 3
    ap = -2
    damage = 2
    anti = ((NON_MONSTER_VEHICLE, 3),)
    blast = 1
    torrent = True


class StoneStaveProfile(WeaponProfile):
    """The same negated [ANTI-X], one threshold better."""
    name = "Stone Stave"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 3
    ap = -1
    damage = 2
    anti = ((NON_MONSTER_VEHICLE, 2),)
    psychic = True


# --- Anhrathe (Corsairs) -----------------------------------------------------
#
# The Corsair arsenal. The power sword, fusion gun, shuriken pistol, shuriken
# cannon, wraithcannon and both Aeldari close combat rows are the shared ones
# and are reused; what follows is everything the Corsairs print that nothing
# else does, plus the three rows that share a NAME with an existing weapon and
# not its numbers.


class BlasterProfile(WeaponProfile):
    name = "Blaster"
    weapon_type = RANGED
    range_in = 18
    attacks = 1
    strength = 8
    ap = -4
    damage = 4  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6(1)
    assault = True


class NeuroDisruptorProfile(WeaponProfile):
    name = "Neuro Disruptor"
    weapon_type = RANGED
    range_in = 12
    attacks = 1
    strength = 4
    ap = -2
    damage = 1
    anti = ("INFANTRY", 2)
    assault = True
    pistol = True


class ShredderProfile(WeaponProfile):
    """Printed BS is "N/A", which is [TORRENT] - no override needed."""
    name = "Shredder"
    weapon_type = RANGED
    range_in = 18
    attacks = 3  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6()
    strength = 6
    ap = 0
    damage = 1
    assault = True
    torrent = True


class ShurikenRifleProfile(WeaponProfile):
    name = "Shuriken Rifle"
    weapon_type = RANGED
    range_in = 24
    attacks = 1
    strength = 4
    ap = -1
    damage = 1
    assault = True
    rapid_fire = 1


class BlastPistolProfile(WeaponProfile):
    name = "Blast Pistol"
    weapon_type = RANGED
    range_in = 6
    attacks = 1
    strength = 8
    ap = -3
    damage = 2  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D3()
    assault = True
    pistol = True


class CorsairBladeProfile(WeaponProfile):
    name = "Corsair Blade"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 4
    ap = -2
    damage = 1


class PairedHekatariiBladesProfile(WeaponProfile):
    """The Shade Runner's blades."""
    name = "Paired Hekatarii Blades"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    # [TWIN-LINKED] (24.38) - re-roll the Wound roll. Found by the keyword
    # sweep in test_weapon_characteristics.py section 5: the printed row
    # carries it and this profile did not, so the blades were re-rolling
    # nothing at all.
    twin_linked = True
    # Printed WS 2+, where the Shade Runner herself is 3+ - a real per-weapon
    # override, the same shape as the Power Klaw's own worse one.
    weapon_skill = "2+"
    strength = 3
    ap = -2
    damage = 1


class VoidscarredExecutionerProfile(WeaponProfile):
    """NOT the Aeldari Executioner already here, which is a MELEE row at
    A3/S6/AP-3/D3 with [ANTI-INFANTRY 3+]. This is a RANGED 18" gun with
    [ANTI-INFANTRY 2+] and [PSYCHIC]. Same printed name, nothing else in
    common - the clearest case of the "needs its own class" rule in this
    batch, and pinned against the melee one so the two cannot merge."""
    name = "Executioner"
    weapon_type = RANGED
    range_in = 18
    attacks = 3
    strength = 6
    ap = -2
    damage = 2  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D3()
    anti = ("INFANTRY", 2)
    psychic = True


class WaySeekerWitchStaffProfile(WitchStaffProfile):
    """The Spiritseer's row exactly, plus the WS2+ its own line prints - the
    Way Seeker stands in a WS3+ unit, so this is a genuine per-WEAPON override
    rather than the model's own skill."""
    weapon_skill = "2+"


class DreadOfTheDeepVoidProfile(WeaponProfile):
    """Kharseth's gun. Five keywords at once, [HAZARDOUS] among them - the
    price the datasheet charges for a D6+2 [BLAST] with [ANTI-INFANTRY 2+]."""
    name = "Dread of the Deep Void"
    weapon_type = RANGED
    range_in = 24
    attacks = 5  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(2)
    strength = 3
    ap = -2
    damage = 1
    anti = ("INFANTRY", 2)
    blast = 1
    hazardous = True
    ignores_cover = True
    psychic = True


class WaystaveProfile(WeaponProfile):
    name = "Waystave"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    weapon_skill = "2+"
    strength = 3
    ap = 0
    damage = 3
    anti = ("INFANTRY", 2)
    psychic = True


class EyeOfWrathProfile(WeaponProfile):
    name = "Eye of Wrath"
    weapon_type = RANGED
    range_in = 6
    attacks = 3
    ballistic_skill = "2+"
    strength = 6
    ap = -2
    damage = 2
    assault = True
    pistol = True


class SpearOfTwilightProfile(WeaponProfile):
    name = "Spear of Twilight"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    weapon_skill = "2+"
    strength = 7
    ap = -3
    damage = 3
    lance = True


class DisintegratorCannonProfile(WeaponProfile):
    name = "Disintegrator Cannon"
    weapon_type = RANGED
    range_in = 36
    attacks = 3
    strength = 6
    ap = -3
    damage = 2
    assault = True


class StarfangGrenadeLauncherProfile(WeaponProfile):
    name = "Starfang Grenade Launcher"
    weapon_type = RANGED
    range_in = 36
    attacks = 2  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D3()
    strength = 6
    ap = -3
    damage = 2
    assault = True
    blast = 1


# --- The Ynnari triumvirate --------------------------------------------------


class StormOfWhispersProfile(WeaponProfile):
    """Yvraine's gun: many weak shots that crit on 2+ against INFANTRY and turn
    every crit into mortal wounds."""
    name = "Storm of Whispers"
    weapon_type = RANGED
    range_in = 12
    attacks = 6  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(3)
    ballistic_skill = "2+"
    strength = 2
    ap = -2
    damage = 1
    anti = ("INFANTRY", 2)
    devastating_wounds = True
    psychic = True


class KhaVirProfile(WeaponProfile):
    name = "Kha-vir"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    weapon_skill = "2+"
    strength = 4
    ap = -3
    damage = 2
    devastating_wounds = True


# The Visarch's Asu-var prints THREE stances, where every other multi-profile
# weapon in this engine prints two. overcharge_profile is a single link, so the
# three are CHAINED: quicksilver -> duellist -> mythic. That is the shape the
# field already has, and it keeps "one datasheet entry, one granted weapon"
# true - only the first is handed out.


class AsuVarMythicStanceProfile(WeaponProfile):
    name = "Asu-var - Mythic Stance"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    weapon_skill = "2+"
    strength = 3
    ap = -4
    damage = 3
    anti = ("EPIC HERO", 2)
    precision = True


class AsuVarDuellistStanceProfile(WeaponProfile):
    name = "Asu-var - Duellist Stance"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    weapon_skill = "2+"
    strength = 5
    ap = -2
    damage = 2
    devastating_wounds = True
    precision = True
    overcharge_profile = AsuVarMythicStanceProfile


class AsuVarQuicksilverStanceProfile(WeaponProfile):
    """The row printed first, so the granted one."""
    name = "Asu-var - Quicksilver Stance"
    weapon_type = MELEE
    range_in = 2
    attacks = 8
    weapon_skill = "2+"
    strength = 4
    ap = -1
    damage = 1
    sustained_hits = 2
    overcharge_profile = AsuVarDuellistStanceProfile


class SwirlingSoulEnergyProfile(WeaponProfile):
    """Printed BS is "N/A", which is [TORRENT]."""
    name = "Swirling Soul Energy"
    weapon_type = RANGED
    range_in = 12
    attacks = 6  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6(3)
    strength = 7
    ap = -1
    damage = 2  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D3()
    ignores_cover = True
    psychic = True
    torrent = True


class VilithZharSweepProfile(WeaponProfile):
    name = "Vilith-zhar - Sweep"
    weapon_type = MELEE
    range_in = 2
    attacks = 10
    weapon_skill = "2+"
    strength = 6
    ap = -4
    damage = 1


class VilithZharStrikeProfile(WeaponProfile):
    name = "Vilith-zhar - Strike"
    weapon_type = MELEE
    range_in = 2
    attacks = 5
    weapon_skill = "2+"
    strength = 12
    ap = -4
    damage = 4  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6(1)
    overcharge_profile = VilithZharSweepProfile
