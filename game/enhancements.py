"""Enhancements: who bears which one, and the single place that hands one out.

WHY THIS EXISTS
---------------
game/factions/detachment.py's Enhancement class is the DESCRIPTIVE half - a
name, a points cost, the printed text - and its own docstring says how the
engine-wired half is meant to work: "granting one means setting the matching
field on that specific model's own UnitProfile instance after build_squad()
created it". game/starflare_ignition.py was the one instance of that, and it
wrote ~80 lines of bearer-eligibility, uniqueness, points and logging around a
single attribute assignment.

Nineteen T'au Enhancements are now engine-wired. Nineteen copies of those
eighty lines is exactly the drift this repo consolidates at the SECOND
consumer, and the halves that would drift are the ones that are easy to get
subtly wrong and hard to see:

  * the 19.04 reading ("does this unit still HAVE the Enhancement" means "is
    the bearer model still alive"), including the fact that a model killed
    this frame is still sitting in Squad.models - the report that taught
    game/starflare_ignition.py that lesson;
  * the points, which must land on Squad.points and must not invent a total
    for an unpriced unit (the "None is contagious" convention);
  * refusing an ambiguous grant rather than guessing which model carries a
    20-point upgrade.

So the RULE of each Enhancement lives in its own module, exactly like a
datasheet ability, and everything all nineteen share lives here.

THE REGISTRY IS THE POINT
-------------------------
ENHANCEMENTS below is the one list of every engine-wired Enhancement: its
points, its detachment, the UnitProfile field its rule reads, and the printed
BEARER restriction as a predicate. A test can count it, and a twentieth cannot
appear without that count moving - the same guard game/proactive_stratagems.py
and the T'au stratagem suite already use.

GATED ON THE DETACHMENT - CLOSING A NAMED LIMITATION
----------------------------------------------------
game/starflare_ignition.py wrote out, at length, why it was NOT gated on its
detachment: an Enhancement is a list-building choice, this engine has no
army-building step, and the predefined T'au list handed it to its Coldstar
Commander unconditionally - so "picking a different T'au detachment leaves that
Commander holding a Retaliation Cadre Enhancement (and its 20 points)".

That limitation is closed here, and by the cheaper of the two fixes it named.
There is still no army-building step, but there IS now a detachment CHOICE, and
main() resolves it BEFORE the armies are built (detachments.apply_to_config()
at main.py:421, army_lists...build() at main.py:527). So the predefined list
can hand out the Enhancement that belongs to the detachment actually chosen -
see game/army_lists.py's tau_army() - and is_active() below refuses one that
does not, so a scene loaded from an older save or built by a test cannot
quietly run a Kauyon Enhancement in a Mont'ka army either.

`setting` is the same game/config.py constant game/detachments.py writes and
each detachment RULE reads. One question, one answer.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
No "apply(model)" that pretends to grant an arbitrary effect generically. What
field to set and what reads it is specific to each Enhancement, which is what
its own module is for. This module only knows: may this model bear it, is the
bearer still alive, whose detachment is it, and what does it cost.
"""

from game import config


class EnhancementSpec:
    """One engine-wired Enhancement's runtime record.

    `flag` is the UnitProfile attribute that marks the bearer. It is declared
    on UnitProfile (game/units.py) like every other ability flag, so a model
    that was never given it answers False rather than raising.

    `can_bear(model, squad)` is the printed BEARER line as a predicate. It
    takes the squad as well as the model because two of the nineteen restrict
    the UNIT rather than the model ("STEALTH BATTLESUITS unit only"), which is
    not a question any single model can answer.

    `unit_level` says the Enhancement is given to a UNIT rather than to one
    model, which is the same two. grant() then marks every model of the unit,
    and the 19.04 reading below ("a living model still has it") comes out
    right for free: the unit has it for as long as the unit exists.
    """

    def __init__(self, name, points, detachment, setting, flag,
                 can_bear, bearer_text="", unit_level=False):
        self.name = name
        self.points = points
        self.detachment = detachment
        self.setting = setting
        self.flag = flag
        self.can_bear = can_bear
        self.bearer_text = bearer_text
        self.unit_level = unit_level


# --- the printed BEARER restrictions, as predicates ----------------------
#
# Written as small named functions rather than inline lambdas so the printed
# line each one transcribes can sit next to it. The general Enhancement rule
# that a bearer is a CHARACTER model is folded into the ones whose printed text
# says "model only"; the two "unit only" ones deliberately do not require it,
# because neither of the datasheets they name has a CHARACTER at all.

def _is_tau(model):
    """"T'AU EMPIRE model". There is no per-model faction keyword in this
    engine (the same documented gap game/retaliation_cadre.py's Bonded Heroes
    note records), so this is answered at the UNIT level by the caller - see
    _tau_character() and grant()'s squad-side check."""
    return True


def _tau_character(model, squad):
    """"T'AU EMPIRE model only" + the general rule that a bearer is a
    CHARACTER."""
    return bool(model.profile.character)


def _tau_character_not_kroot_shaper(model, squad):
    """"T'AU EMPIRE model only (excluding KROOT SHAPER models)."

    A Kroot Shaper is the one CHARACTER in this faction that the two Exemplar
    Enhancements and the two Observer ones exclude by name. Read off the
    datasheet name rather than a new keyword flag: "Kroot Flesh/Trail/War
    Shaper" is what the three datasheets are called, and game/kroot_shapers.py
    already treats the shared KrootShaperProfile base class as their identity -
    so that is what is asked for."""
    if not model.profile.character:
        return False
    return not _is_kroot_shaper(model)


def _tau_character_not_kroot(model, squad):
    """"T'AU EMPIRE model only (excluding KROOT models)."""
    return bool(model.profile.character) and not model.profile.kroot


def _battlesuit_character(model, squad):
    """"T'AU EMPIRE BATTLESUIT model only", plus the CHARACTER rule."""
    return bool(model.profile.battlesuit and model.profile.character)


def _battlesuit(model, squad):
    """"BATTLESUIT model only" - printed without the T'AU EMPIRE qualifier on
    the three Experimental Prototype Cadre Enhancements, and without CHARACTER
    either. Kept as printed: their effect names one of the bearer's own weapons,
    so a non-character battlesuit bearing one is a legal build."""
    return bool(model.profile.battlesuit)


def _kroot_shaper(model, squad):
    """"Kroot Shaper model only"."""
    return _is_kroot_shaper(model)


def _is_kroot_shaper(model):
    name = getattr(model.profile, "name", "") or ""
    return "Shaper" in name and bool(model.profile.kroot)


def _stealth_battlesuits_unit(model, squad):
    """"STEALTH BATTLESUITS unit only"."""
    return _unit_is(squad, ("Stealth Battlesuits",))


def _ghostkeel_pathfinder_or_stealth_unit(model, squad):
    """"GHOSTKEEL BATTLESUIT/PATHFINDER TEAM/STEALTH BATTLESUITS unit only"."""
    return _unit_is(squad, ("Ghostkeel Battlesuit", "Pathfinder Team", "Stealth Battlesuits"))


def _unit_is(squad, datasheet_names):
    """Whether `squad` is one of the named datasheets.

    Asked of the DATASHEET rather than of a keyword flag because that is what
    the printed restriction names, and because rule 19.01 can merge a character
    in: attached_components keeps the provenance, so a merged unit still knows
    which datasheets it is made of. A hand-built Squad with no datasheet (every
    testkit.py scene) answers False, which is the safe direction - it withholds
    the Enhancement rather than inventing one."""
    if squad is None:
        return False
    names = []
    sheet = getattr(squad, "datasheet", None)
    if sheet is not None and getattr(sheet, "name", None):
        names.append(sheet.name)
    for component in getattr(squad, "attached_components", ()) or ():
        sheet = getattr(component, "datasheet", None)
        if sheet is not None and getattr(sheet, "name", None):
            names.append(sheet.name)
    return any(n in datasheet_names for n in names)


# --- the Aeldari printed BEARER restrictions -----------------------------
#
# MEASURED across all 28: the printed clauses fall into NINE shapes, not 28.
# Seven say "ASURYANI model only", five "ASURYANI PSYKER model only", four
# "SPIRITSEER model only", four "AUTARCH or AUTARCH WAYLEAPER model only",
# three "ASURYANI MOUNTED model only", two "AELDARI PSYKER model only", and one
# each of "ASURYANI MOUNTED PSYKER model only", "RANGERS unit only" and
# "RANGERS/SHROUD RUNNERS unit only". So nine named predicates, composed from
# helpers that already exist, rather than 28 near-copies.
#
# THE SAME GAP _is_tau() RECORDS, AND SHARPER HERE. Twelve of the 28 print a
# FACTION keyword on a MODEL ("ASURYANI model only"), and this engine has no
# per-model faction keyword. For T'au that was harmless - the faction has one.
# For Aeldari it is not: ASURYANI, AELDARI and YNNARI are genuinely different
# sets (Datasheet.faction_keywords, built for the detachment RULES), and the
# Ynnari triumvirate is AELDARI without being ASURYANI. So the question is
# answered at the UNIT, through attached_units.unit_has_faction_keyword(), and
# said out loud rather than papered over with a `return True`.

def _is_asuryani(squad):
    """"ASURYANI" - answered at the UNIT, see the note above."""
    from game import aeldari_detachments
    return aeldari_detachments.is_asuryani_unit(squad)


def _is_aeldari(squad):
    from game import aeldari_detachments
    return aeldari_detachments.is_aeldari_unit(squad)


def _model_is(model, datasheet_names):
    """Whether this MODEL is one of the named datasheets.

    _unit_is() below answers the same question for a UNIT; this is the
    per-model half, and it is what eight of the 28 need ("SPIRITSEER model
    only", "AUTARCH or AUTARCH WAYLEAPER model only"). Matched on the printed
    profile NAME, which is what those clauses name - _is_kroot_shaper() is the
    only earlier per-model version and it substring-matches, which is exactly
    the looseness this avoids."""
    if model is None:
        return False
    return (getattr(model.profile, "name", "") or "") in datasheet_names


def _asuryani_model(model, squad):
    """"ASURYANI model only"."""
    return _is_asuryani(squad)


def _asuryani_psyker(model, squad):
    """"ASURYANI PSYKER model only" - the faction half at the unit, the PSYKER
    half on the model, which is where that keyword really lives."""
    return _is_asuryani(squad) and bool(model.profile.psyker)


def _aeldari_psyker(model, squad):
    """"AELDARI PSYKER model only" - a WIDER faction set than the clause above,
    and the difference is real: the Ynnari triumvirate is AELDARI and not
    ASURYANI. Two printed clauses, two predicates."""
    return _is_aeldari(squad) and bool(model.profile.psyker)


def _is_mounted(squad):
    """MOUNTED, read off the DATASHEET keyword line and NOT UnitProfile.mounted.

    MEASURED, and the flag would have been a quiet disaster here: the profile
    flag is a strict SUBSET of the keyword. Five Aeldari datasheets set both,
    and FOUR carry the keyword with no flag - Shining Spears, Shroud Runners,
    Warlock Skyrunners and Windriders, i.e. exactly the units Windrider Host's
    four Enhancements exist for. game/fated_hero.py already records that MOUNTED
    is "a descriptive datasheet keyword rather than a profile flag in this
    engine" and reads the keyword line for the same reason."""
    from game.attached_units import unit_has_datasheet_keyword
    return unit_has_datasheet_keyword(squad, "MOUNTED")


def _asuryani_mounted(model, squad):
    """"ASURYANI MOUNTED model only"."""
    return _is_asuryani(squad) and _is_mounted(squad)


def _asuryani_mounted_psyker(model, squad):
    """"ASURYANI MOUNTED PSYKER model only" - all three. PSYKER stays on the
    MODEL, which is where that keyword really lives."""
    return (_is_asuryani(squad) and _is_mounted(squad)
            and bool(model.profile.psyker))


def _spiritseer(model, squad):
    """"SPIRITSEER model only"."""
    return _model_is(model, ("Spiritseer",))


def _autarch(model, squad):
    """"AUTARCH or AUTARCH WAYLEAPER model only" - two datasheets, named
    because the printed clause names them rather than a keyword they share."""
    return _model_is(model, ("Autarch", "Autarch Wayleaper"))


def _rangers_unit(model, squad):
    """"RANGERS unit only"."""
    return _unit_is(squad, ("Rangers",))


def _rangers_or_shroud_runners_unit(model, squad):
    """"RANGERS/SHROUD RUNNERS unit only"."""
    return _unit_is(squad, ("Rangers", "Shroud Runners"))


# --- the registry --------------------------------------------------------
#
# Every engine-wired Enhancement, keyed by its printed name. `flag` names the
# UnitProfile field the rule reads; the rule itself is the module named in the
# comment. Points and detachment match game/factions/tau_empire.py's descriptive
# records, which is pinned by a test rather than trusted.

_RETALIATION = ("Retaliation Cadre", "RETALIATION_CADRE_PLAYERS")
_KAUYON = ("Kauyon", "KAUYON_PLAYERS")
_MONTKA = ("Mont'ka", "MONTKA_PLAYERS")
_EPC = ("Experimental Prototype Cadre", "EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS")
_AAC = ("Advanced Acquisition Cadre", "ADVANCED_ACQUISITION_CADRE_PLAYERS")
_AUXILIARY = ("Auxiliary Cadre", "AUXILIARY_CADRE_PLAYERS")

# The eight Aeldari detachments. Every one of these config constants already
# existed and is already written by game/detachments.py - the detachment RULES
# stage put them there.
_ASPECT_HOST = ("Aspect Host", "ASPECT_HOST_PLAYERS")
_GUARDIAN_BATTLEHOST = ("Guardian Battlehost", "GUARDIAN_BATTLEHOST_PLAYERS")
_WARHOST = ("Warhost", "WARHOST_PLAYERS")
_WINDRIDER_HOST = ("Windrider Host", "WINDRIDER_HOST_PLAYERS")
_SPIRIT_CONCLAVE = ("Spirit Conclave", "SPIRIT_CONCLAVE_PLAYERS")
_ARMOURED_WARHOST = ("Armoured Warhost", "ARMOURED_WARHOST_PLAYERS")
_PATH_OF_THE_OUTCAST = ("Path of the Outcast", "PATH_OF_THE_OUTCAST_PLAYERS")
_SEER_COUNCIL = ("Seer Council", "SEER_COUNCIL_PLAYERS")

ENHANCEMENTS = {}


def register(spec):
    if spec.name in ENHANCEMENTS:
        raise ValueError(f"Enhancement {spec.name!r} is already registered.")
    ENHANCEMENTS[spec.name] = spec
    return spec


def _add(name, points, detachment_setting, flag, can_bear, bearer_text, unit_level=False):
    detachment, setting = detachment_setting
    return register(EnhancementSpec(
        name, points, detachment, setting, flag, can_bear,
        bearer_text=bearer_text, unit_level=unit_level))


# Retaliation Cadre - game/enh_internal_grenade_racks.py,
# game/enh_prototype_weapon_system.py, game/enh_puretide_neurochip.py and the
# original game/starflare_ignition.py.
_add("Internal Grenade Racks", 20, _RETALIATION, "internal_grenade_racks",
     _battlesuit_character, "T'AU EMPIRE BATTLESUIT model only")
_add("Prototype Weapon System", 15, _RETALIATION, "prototype_weapon_system",
     _battlesuit_character, "T'AU EMPIRE BATTLESUIT model only")
_add("Puretide Engram Neurochip", 15, _RETALIATION, "puretide_engram_neurochip",
     _battlesuit_character, "T'AU EMPIRE BATTLESUIT model only")
_add("Starflare Ignition System", 20, _RETALIATION, "starflare_ignition_system",
     _battlesuit_character, "T'AU EMPIRE BATTLESUIT model only")

# Kauyon - game/enh_exemplars.py, game/enh_precision_patient_hunter.py,
# game/enh_solid_image_projection.py, game/enh_guided_keyword_grants.py.
_add("Exemplar of the Kauyon", 20, _KAUYON, "exemplar_of_the_kauyon",
     _tau_character_not_kroot_shaper,
     "T'AU EMPIRE model only (excluding KROOT SHAPER models)")
_add("Precision of the Patient Hunter", 15, _KAUYON, "precision_of_the_patient_hunter",
     _tau_character, "T'AU EMPIRE model only")
_add("Solid-image Projection Unit", 20, _KAUYON, "solid_image_projection_unit",
     _tau_character, "T'AU EMPIRE model only")
_add("Through Unity, Devastation", 30, _KAUYON, "through_unity_devastation",
     _tau_character_not_kroot_shaper,
     "T'AU EMPIRE model only (excluding KROOT SHAPER models)")

# Mont'ka - game/enh_guided_keyword_grants.py, game/enh_exemplars.py,
# game/enh_strategic_conqueror.py, game/enh_strike_swiftly.py.
_add("Coordinated Exploitation", 30, _MONTKA, "coordinated_exploitation",
     _tau_character_not_kroot_shaper,
     "T'AU EMPIRE model only (excluding KROOT SHAPER models)")
_add("Exemplar of the Mont'ka", 10, _MONTKA, "exemplar_of_the_montka",
     _tau_character_not_kroot_shaper,
     "T'AU EMPIRE model only (excluding KROOT SHAPER models)")
_add("Strategic Conqueror", 15, _MONTKA, "strategic_conqueror",
     _tau_character, "T'AU EMPIRE model only")
_add("Strike Swiftly", 45, _MONTKA, "strike_swiftly",
     _tau_character, "T'AU EMPIRE model only")

# Experimental Prototype Cadre - game/enh_prototype_weapons.py, all three.
_add("Thermoneutronic Projector", 15, _EPC, "thermoneutronic_projector",
     _battlesuit, "BATTLESUIT model only")
_add("Plasma Accelerator Rifle", 20, _EPC, "plasma_accelerator_rifle",
     _battlesuit, "BATTLESUIT model only")
_add("Supernova Launcher", 15, _EPC, "supernova_launcher",
     _battlesuit, "BATTLESUIT model only")

# Advanced Acquisition Cadre - game/enh_negation_emitters.py,
# game/enh_unmasking_suite.py. Both are given to a UNIT, not to a model.
_add("Negation Emitters", 15, _AAC, "negation_emitters",
     _stealth_battlesuits_unit, "STEALTH BATTLESUITS unit only", unit_level=True)
_add("Unmasking Suite", 15, _AAC, "unmasking_suite",
     _ghostkeel_pathfinder_or_stealth_unit,
     "GHOSTKEEL BATTLESUIT/PATHFINDER TEAM/STEALTH BATTLESUITS unit only",
     unit_level=True)

# Auxiliary Cadre - game/enh_student_of_kauyon.py, game/enh_admired_leader.py.
_add("Student of Kauyon", 20, _AUXILIARY, "student_of_kauyon",
     _kroot_shaper, "KROOT SHAPER model only")
_add("Admired Leader", 20, _AUXILIARY, "admired_leader",
     _tau_character_not_kroot, "T'AU EMPIRE model only (excluding KROOT models)")


# --- Aeldari ---------------------------------------------------------
#
# 28: the 24 of the seven detachments whose rules and Stratagems are built,
# plus Seer Council's four. Seer Council is the one Aeldari detachment the
# army list actually fields, so without its four no Aeldari Enhancement
# could ever be live in a default game.


_add("Aspect of Murder", 15, _ASPECT_HOST, "aspect_of_murder",
     _autarch, "AUTARCH or AUTARCH WAYLEAPER model only")
_add("Mantle of Wisdom", 20, _ASPECT_HOST, "mantle_of_wisdom",
     _autarch, "AUTARCH or AUTARCH WAYLEAPER model only")
_add("Shimmerstone", 10, _ASPECT_HOST, "shimmerstone",
     _autarch, "AUTARCH or AUTARCH WAYLEAPER model only")
_add("Strategic Savant", 10, _ASPECT_HOST, "strategic_savant",
     _autarch, "AUTARCH or AUTARCH WAYLEAPER model only")

_add("Craftworld's Champion", 25, _GUARDIAN_BATTLEHOST, "craftworlds_champion",
     _asuryani_model, "ASURYANI model only")
_add("Ethereal Pathway", 30, _GUARDIAN_BATTLEHOST, "ethereal_pathway",
     _asuryani_model, "ASURYANI model only")
_add("Protector of the Paths", 20, _GUARDIAN_BATTLEHOST, "protector_of_the_paths",
     _asuryani_model, "ASURYANI model only")
_add("Breath of Vaul", 10, _GUARDIAN_BATTLEHOST, "breath_of_vaul",
     _asuryani_model, "ASURYANI model only")

_add("Phoenix Gem", 35, _WARHOST, "phoenix_gem",
     _asuryani_model, "ASURYANI model only")
_add("Timeless Strategist", 15, _WARHOST, "timeless_strategist",
     _asuryani_model, "ASURYANI model only")
_add("Gift of Foresight", 15, _WARHOST, "gift_of_foresight",
     _asuryani_model, "ASURYANI model only")
_add("Psychic Destroyer", 30, _WARHOST, "psychic_destroyer",
     _asuryani_psyker, "ASURYANI PSYKER model only")

_add("Firstdrawn Blade", 10, _WINDRIDER_HOST, "firstdrawn_blade",
     _asuryani_mounted, "ASURYANI MOUNTED model only")
_add("Mirage Field", 25, _WINDRIDER_HOST, "mirage_field",
     _asuryani_mounted, "ASURYANI MOUNTED model only")
_add("Seersight Strike", 15, _WINDRIDER_HOST, "seersight_strike",
     _asuryani_mounted_psyker, "ASURYANI MOUNTED PSYKER model only")
_add("Echoes of Ulthanesh", 20, _WINDRIDER_HOST, "echoes_of_ulthanesh",
     _asuryani_mounted, "ASURYANI MOUNTED model only")

_add("Light of Clarity", 30, _SPIRIT_CONCLAVE, "light_of_clarity",
     _spiritseer, "SPIRITSEER model only")
_add("Stave of Kurnous", 15, _SPIRIT_CONCLAVE, "stave_of_kurnous",
     _spiritseer, "SPIRITSEER model only")
_add("Rune of Mists", 10, _SPIRIT_CONCLAVE, "rune_of_mists",
     _spiritseer, "SPIRITSEER model only")
_add("Higher Duty", 25, _SPIRIT_CONCLAVE, "higher_duty",
     _spiritseer, "SPIRITSEER model only")

_add("Spirit Stone of Raelyth", 20, _ARMOURED_WARHOST, "spirit_stone_of_raelyth",
     _aeldari_psyker, "AELDARI PSYKER model only")
_add("Guiding Presence", 25, _ARMOURED_WARHOST, "guiding_presence",
     _aeldari_psyker, "AELDARI PSYKER model only")

_add("Camouflaged Snipers", 10, _PATH_OF_THE_OUTCAST, "camouflaged_snipers",
     _rangers_unit, "RANGERS unit only", unit_level=True)
_add("Assassins' Eye", 15, _PATH_OF_THE_OUTCAST, "assassins_eye",
     _rangers_or_shroud_runners_unit, "RANGERS/SHROUD RUNNERS unit only", unit_level=True)

_add("Lucid Eye", 30, _SEER_COUNCIL, "lucid_eye",
     _asuryani_psyker, "ASURYANI PSYKER model only")
_add("Runes of Warding", 25, _SEER_COUNCIL, "runes_of_warding",
     _asuryani_psyker, "ASURYANI PSYKER model only")
_add("Stone of Eldritch Fury", 15, _SEER_COUNCIL, "stone_of_eldritch_fury",
     _asuryani_psyker, "ASURYANI PSYKER model only")
_add("Torc of Morai-Heg", 20, _SEER_COUNCIL, "torc_of_morai_heg",
     _asuryani_psyker, "ASURYANI PSYKER model only")


def get(name):
    spec = ENHANCEMENTS.get(name)
    if spec is None:
        raise KeyError(f"No engine-wired Enhancement named {name!r}.")
    return spec


def for_detachment(detachment_name):
    """Every engine-wired Enhancement of one detachment, in registration
    order (which is the printed order on the detachment's own page)."""
    return [s for s in ENHANCEMENTS.values() if s.detachment == detachment_name]


# --- the 19.04 reading ---------------------------------------------------

def _living(models):
    return [m for m in models if not m.is_dead()]


def enhancement_models(squad, name):
    """Every model of `squad` that was GIVEN this Enhancement, alive or not.

    The distinction from bearer_models() matters for reporting: a unit whose
    bearer has just been killed no longer has the Enhancement, but it is still
    the unit a "not offered - because X" line is about."""
    if squad is None:
        return []
    flag = get(name).flag
    return [m for m in squad.models if getattr(m.profile, flag, False)]


def bearer_models(squad, name):
    """Every LIVING model of `squad` carrying this Enhancement.

    A list rather than a bool because rule 19.01 merges a bearer into a larger
    unit, so "does this unit still have the Enhancement" means "is the bearer
    model still alive".

    is_dead() is filtered here and not left to Squad.models, because a model
    killed this frame is still in that list: GameState.remove_dead_models()
    runs ONCE PER FRAME, strictly after the event loop and run_ai_action().
    Every end-of-turn and end-of-phase rule therefore sees corpses. That is the
    report game/starflare_ignition.py was fixed for (a unit whose bearer had
    just died was still offered the withdrawal, and the answer then did
    nothing), and it applies to all nineteen."""
    return _living(enhancement_models(squad, name))


def has(squad, name):
    """Whether this unit still has the Enhancement at all."""
    return bool(bearer_models(squad, name))


def player_has_detachment(player, setting):
    """Whether `player` fields the detachment whose config constant is
    `setting`. The same question every detachment rule asks of the same
    constant - imported rather than re-answered, so a rule and its Enhancements
    can never disagree about who brought it.

    Reached through game/detachment_gate.py rather than game/tau_detachments.py,
    which is where this used to point. That was harmless while every registered
    Enhancement was a T'au one and a lying import path the moment an Aeldari one
    arrived - the same rename detachment_gate.py itself was extracted for."""
    from game import detachment_gate
    return detachment_gate.has_detachment(player, setting)


def is_active(squad, name):
    """The condition every one of these rules opens with: a living bearer,
    AND an owner who actually fields the Enhancement's detachment.

    The second half is what closes game/starflare_ignition.py's named
    limitation - see the module docstring."""
    if squad is None:
        return False
    spec = get(name)
    if not has(squad, name):
        return False
    return player_has_detachment(getattr(squad, "owner", None), spec.setting)


def model_is_active(model, name):
    """is_active() for a single model - "each time the BEARER makes an attack"
    is per-model, and after a 19.01 merge the bearer is one model among many.

    Takes the owner from the model's own squad, which is how every other
    per-model rule here reaches the player."""
    if model is None or model.is_dead():
        return False
    spec = get(name)
    if not getattr(model.profile, spec.flag, False):
        return False
    squad = getattr(model, "squad", None)
    return player_has_detachment(getattr(squad, "owner", None), spec.setting)


def bearer_units(squads, name, player=None):
    """Every unit in `squads` with a living bearer (and the detachment), for
    the rules that have to find their own bearer rather than being handed one -
    the pre-battle and Command-phase ones."""
    out = []
    for squad in squads or ():
        if player is not None and getattr(squad, "owner", None) != player:
            continue
        if is_active(squad, name) and squad not in out:
            out.append(squad)
    return out


# --- army building -------------------------------------------------------

def grant(squad, name, model=None, game_log=None):
    """Give one Enhancement to `squad` during army building.

    This is the "apply" step game/factions/detachment.py's Enhancement
    docstring describes: set the matching field on the bearer's own UnitProfile
    instance, which build_squad() creates fresh per model, so it never leaks to
    another model built from the same datasheet.

    It is a function rather than a raw attribute poke because two things have
    to happen that a bare assignment silently skips - the printed BEARER
    restriction has to be enforced somewhere, and army building is the only
    moment it is ever decided; and the points have to land on Squad.points.

    `model` names the bearer explicitly. Omitted, the single eligible model is
    used, and an AMBIGUOUS squad is refused rather than guessed at: which model
    carries a 20-point upgrade is not something to pick arbitrarily.

    Raises ValueError on an illegal grant. This runs while the scene is being
    built, long before there is a UI to report into, and a silently dropped
    Enhancement shows up much later as "the rule never triggers".
    """
    spec = get(name)
    if squad is None:
        raise ValueError(f"{name}: no unit given.")
    if enhancement_models(squad, name):
        raise ValueError(f"{name}: {squad.name} already has this Enhancement.")

    candidates = [m for m in squad.models if spec.can_bear(m, squad)]
    if spec.unit_level:
        # "STEALTH BATTLESUITS unit only": the restriction is on the unit, so
        # either every model may bear it or none may. Marking all of them is
        # what makes bearer_models()'s "a living model still has it" mean "the
        # unit still exists", which is the right reading for a unit-level
        # Enhancement.
        if not candidates:
            raise ValueError(f"{name}: {squad.name} is not a legal unit for it ({spec.bearer_text}).")
        bearers = list(squad.models)
    elif model is not None:
        if model not in squad.models:
            raise ValueError(f"{name}: that model is not in {squad.name}.")
        if not spec.can_bear(model, squad):
            raise ValueError(f"{name}: {model.profile.name} does not satisfy '{spec.bearer_text}'.")
        bearers = [model]
    elif not candidates:
        raise ValueError(f"{name}: {squad.name} has no model satisfying '{spec.bearer_text}'.")
    elif len(candidates) > 1:
        raise ValueError(
            f"{name}: {squad.name} has {len(candidates)} eligible models - "
            f"name the bearer explicitly.")
    else:
        bearers = [candidates[0]]

    for bearer in bearers:
        setattr(bearer.profile, spec.flag, True)
    # An Enhancement's points are part of what the army costs. Squad.points is
    # None for a faction with no transcribed points list, and that "None is
    # contagious" convention (game/attached_units.py's attach() uses the same
    # one) has to hold here too - adding to an unpriced unit would invent a
    # total that isn't one.
    if squad.points is not None:
        squad.points += spec.points
    if game_log is not None:
        who = squad.name if spec.unit_level else bearers[0].profile.name
        game_log.add(f"{squad.owner}: {who} carries the {name} Enhancement ({spec.points} pts).")
    return bearers[0]


def granted_names(squad):
    """Every Enhancement this unit was given, in registry order - for the
    datacard and the army-building log line."""
    return [name for name in ENHANCEMENTS if enhancement_models(squad, name)]
