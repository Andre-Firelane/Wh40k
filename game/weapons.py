from game.dice_notation import D3, D6

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
    name = "Missile Pod"
    weapon_type = RANGED
    range_in = 30
    attacks = 2
    ballistic_skill = "5+"
    strength = 7
    ap = -1
    damage = 2


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
    """Ranged half. [RAPID FIRE 2] (24.30) doubles down within half range;
    [PISTOL] (24.27) lets it fire out of Engagement Range."""
    name = "XV Pulse Pistol"
    weapon_type = RANGED
    range_in = 12
    attacks = 2
    strength = 6
    ap = -1
    damage = 2
    rapid_fire = 2
    pistol = True


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


class ExecutionerProfile(WeaponProfile):
    name = "Executioner"
    weapon_type = MELEE
    range_in = 2
    attacks = 3
    strength = 6
    ap = -3
    damage = 3


class MirrorswordsProfile(WeaponProfile):
    name = "Mirrorswords"
    weapon_type = MELEE
    range_in = 2
    attacks = 4
    strength = 4
    ap = -2
    damage = 2


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


class TriskeleMeleeProfile(WeaponProfile):
    name = "Triskele"
    weapon_type = MELEE
    range_in = 2
    attacks = 6
    strength = 3
    ap = -1
    damage = 1


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
    below, which is the entry the datasheet actually grants."""
    name = "Missile Launcher - Sunburst Blast"
    weapon_type = RANGED
    range_in = 48
    attacks = 3  # preview/grouping placeholder only - attacks_notation is what is rolled
    attacks_notation = D6()
    strength = 4
    ap = -1
    damage = 1


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
    ballistic_skill = "4+"
    strength = 14
    ap = -4
    damage = 4  # preview/grouping placeholder only - damage_notation is what is rolled
    damage_notation = D6(1)


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
    anti = ("INFANTRY", 3)


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
