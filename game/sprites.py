"""Rule-free rendering asset: static portrait art for units, dropped by the
user into the Sprites/ folder at the project root, drawn in place of the
plain colored disc + 2-letter label (see Renderer._draw_tokens) whenever one
is available for a given token.

Lookup logic (user-specified):
    - every squad (datasheet) can have a standard image.
    - a squad can ALSO have variant images for its squad leader model
      (UnitProfile.squad_leader) and/or for a model whose weapon loadout
      differs from the squad's own majority loadout (the same notion of
      "unusual" Squad.unusual_loadout_models() already uses for the tint
      highlight, e.g. a Boss Nob's Big Choppa or a Kroot Long-quill's extra
      pistol).
    - a variant with no image of its own falls back to the squad's standard
      image.
    - a squad with NO image at all (not even a standard one) falls back to
      the renderer's plain disc + letter label - nothing here requires every
      unit to have art before it's drawable.

Filename convention, all files living directly in Sprites/ (tries
.png/.jpg/.jpeg/.webp in that order, case-sensitive on the base name):
    <sprite key>.png                   - standard
    <sprite key> - Leader.png           - the squad leader model
    <sprite key> - <Weapon Name>.png    - a model armed with <Weapon Name>,
                                           where that weapon isn't part of
                                           the squad's majority loadout

`<sprite key>` comes from SQUAD_SPRITE_KEYS, keyed by the datasheet name
(e.g. "Strike Team") - matched as a SUBSTRING of the squad's own `.name`,
not an exact match, since a real Squad's name usually isn't the bare
datasheet name (main.py's demo scene names its squads e.g. "1 Strike Team
1" - owner + datasheet name + per-player instance count). The art's own
filename doesn't have to match the datasheet name 1:1 either (e.g. the
user's own test file is "Fire Warrior Strike Squad.png" for the "Strike
Team" datasheet), so add one entry here whenever a new sprite is dropped
into Sprites/. A squad whose name doesn't contain any mapped key simply has
no sprite (falls back to letters), same as any other unmapped squad.

Separately, GROUND_TEXTURE_NAME (a single "Sprites/Ground.<ext>" file, no
per-squad mapping needed - there's only ever one battlefield floor) is
tiled across the whole board as its background - see Renderer's static
layer, which falls back to the plain flat BACKGROUND_COLOR fill (as
before) if that file isn't present. DENSE_COVER_TEXTURE_NAME
("Sprites/Dense_Cover.<ext>") and NORMAL_COVER_TEXTURE_NAME
("Sprites/Normal_Cover.<ext>") are the same idea, tiled within each
non-Dense terrain footprint (a TerrainArea's Light/Exposed features - see
game/terrain.py) instead of the whole board - which one is picked depends
on whether that footprint's own TerrainArea also has a Dense feature (a
wall) standing on it (TerrainArea.has_dense_feature): Dense_Cover for a
ruin's floor with walls rising out of it, Normal_Cover for open terrain
with no walls (a standalone barricade/crater/rubble patch). Falls back to
the old translucent color tint for that terrain if the relevant file isn't
present.

Separately again, BLOOD_DECAL_NAME (a single "Sprites/Blood.<ext>" file) is
drawn at BLOOD_DECAL_ALPHA opacity, at the spot each model died - one decal per
death, accumulated in GameState.blood_decals and painted by
Renderer.draw_blood_decals(), unrelated to the per-squad sprite lookup
above. Missing art means no decals are drawn at all, same "missing art is
fine" convention as everything else in this module."""

import os
from collections import Counter

import pygame

from game import attached_units

SPRITES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Sprites")

_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

# Maps Squad.name -> base filename (without extension/variant suffix) in
# Sprites/. See this module's docstring for why this mapping exists instead
# of matching the datasheet name directly.
SQUAD_SPRITE_KEYS = {
    # --- Aeldari ---
    "Guardian Defenders": "Guardian Defender",  # the platform model has its own art, see MODEL_SPRITE_KEYS below
    # The user's file is named "Assault Guardian"; the datasheet is Storm
    # Guardians. No separate art for the Serpent's Scale Platform, so that
    # model falls through to this same image - fine, and the reason it is NOT
    # in MODEL_SPRITE_KEYS.
    "Storm Guardians": "Assault Guardian",
    "Striking Scorpions": "Striking Scorpion",  # the Exarch has no art of its own
    "Howling Banshees": "Howling Banshees",  # likewise - one image for the whole unit
    # The user's file is "Warpspider" (one word); the datasheet is Warp Spiders.
    "Warp Spiders": "Warpspider",  # one image for the whole unit, Exarch included
    "Dire Avengers": "Dire Avengers",
    "Fire Dragons": "Fire Dragons",
    "Falcon": "Falcon Tank",
    "Wraithguard": "Wraithguard",
    "Asurmen": "Asurmen",
    # The user's file is "JainZar" (one word); the datasheet is Jain Zar.
    "Jain Zar": "JainZar",
    # The user's file is "Warlock Conclaive" (their spelling).
    "Warlock Conclave": "Warlock Conclaive",
    "Farseer": "Farseer",
    # The user's file is "Eldrad Ultran.png" - spelled without the h. The
    # folder's filenames are the source of truth here, as everywhere in this
    # table (cf. "Ghostkheel", "Starsythe", "Pulse Carbon").
    "Eldrad Ulthran": "Eldrad Ultran",
    # Also the folder's spelling: "Lykhis.png", without the h.
    "Lhykhis": "Lykhis",
    "Avatar of Khaine": "Avatar",
    "Strike Team": "Fire Warrior Strike Squad",
    "Breacher Team": "Breacher",
    "Kroot Carnivores": "Kroot Carnivores",
    "Stealth Battlesuits": "Stealth Suites",
    # Filename typo ("Starsythe") is the actual file dropped in Sprites/ -
    # kept verbatim, since _resolve_path() matches the base filename exactly.
    "Crisis Starscythe Battlesuits": "Crisis_Starsythe_Battle_Suits",
    "Crisis Sunforge Battlesuits": "Crisis_Sunforge_Battle_Suits",
    # The two attached CHARACTERS. Their art was already in Sprites/ but had
    # no entry here, so they fell through to whatever their host unit's name
    # happened to match - a Commander drawn as a Crisis suit. Note these are
    # only reachable because sprite keys are resolved per MODEL now (see
    # _squad_key()): an attached unit has one name and two datasheets, so no
    # amount of mapping could have picked them out of the squad name alone.
    "Commander in Coldstar Battlesuit": "Tau Coldstar Commander",
    "Cadre Fireblade": "Tau Fireblade",
    "Commander Farsight": "Commander Farsight",
    "Devilfish": "Devilfish",
    # Filename typo ("Ghostkheel") is the actual file dropped in Sprites/.
    "Ghostkeel Battlesuit": "Ghostkheel",
    "Riptide Battlesuit": "Riptide",
    # "Pathfinder Pulse Carbon.png" (the file's own spelling) is the standard
    # image: every model on the supplied datasheet carries a Pulse carbine.
    #
    # "Pathfinder Rail Rifle.png" is also in Sprites/ and IS meant to be used
    # (user: "für pathfinder gibt es auch extra sprites für die rail rifle"),
    # but nothing can reach it yet - the supplied datasheet has no rail rifle
    # weapon, so no model ever counts as carrying one. Two things are needed
    # when that option arrives: the weapon + WargearOption, and the file
    # renamed to "Pathfinder Pulse Carbon - Rail Rifle.png" - _variant_
    # candidates() builds "<mapped key> - <weapon name>", and the mapped key
    # here is the standard image's own name, not the datasheet's.
    "Pathfinder Team": "Pathfinder Pulse Carbon",
    # No separate Boss Nob art dropped yet - falls back to this same
    # standard image for the whole squad, Boss Nob included (see this
    # module's docstring: "a variant with no image of its own falls back to
    # the squad's standard image").
    # "Beast Snagga Boyz" MUST be listed before the plain "Boyz" entry
    # below - keys are matched as SUBSTRINGS of the squad's name, and
    # "Beast Snagga Boyz" contains "Boyz", so the plain entry would
    # otherwise swallow it and draw the mob as ordinary Ork Boyz. Exactly
    # the hazard the "Warboss in Mega Armour"/"Warboss" pair above documents.
    #
    # This datasheet has TWO files - the mob and its Nob. The Nob is picked
    # out by MODEL_SPRITE_KEYS below (keyed on the model's own profile
    # name), not here: both models belong to the same datasheet, so no
    # squad-level mapping could tell them apart.
    "Beast Snagga Boyz": "Beast Boy",
    "Boyz": "Ork Boy",
    # Same fallback note as Boyz above - no separate Boss Nob on Warbike art.
    "Warbikers": "Ork Warbiker",
    # Same fallback note as Boyz above - no separate Boss Nob art.
    "Stormboyz": "Ork Stormboyz",
    "Trukk": "Ork Trukk",
    # Same fallback note as Boyz above - no separate Runtherd art.
    "Gretchin": "Gretchins",
    # "Warboss in Mega Armour" MUST be listed before the plain "Warboss"
    # entry below - its own datasheet name contains "Warboss" as a
    # substring, and _squad_key() returns on the first match, so the more
    # specific key has to come first or every Warboss-in-Mega-Armour squad
    # would resolve to the plain Warboss art instead of its own.
    "Warboss in Mega Armour": "Ork Warboss in Megaarmor",
    # No separate variant art dropped yet - falls back to this same
    # standard image regardless of loadout (this datasheet has none).
    "Warboss": "Ork Warboss",
    # Same fallback note as Boyz above - no separate variant art for either
    # model line (Boss Nob shares the rank-and-file's own stat line here).
    "Meganobz": "Ork Meganob",
    # Same fallback note as Boyz above - no separate Boss Nob art.
    "Tankbustas": "Ork Tankbusta",
    "Deffkoptas": "Ork Deffkopta",
    "Deff Dread": "Ork Deffdread",
    "Beastboss": "Ork Beast Boss",
    "Kill Rig": "Ork Kill Rig",
    # Filename capitalisation ("Flash GItz") is the actual file dropped in
    # Sprites/ - kept verbatim, since _resolve_path() matches exactly.
    "Flash Gitz": "Flash GItz",
    "Battlewagon": "Ork Battle Wagon",
}

# Maps a MODEL's own profile name -> base filename, for a unit whose
# individually named models each have their own art. Consulted BEFORE
# SQUAD_SPRITE_KEYS (see _squad_key()), because these models share one squad
# AND one datasheet, so no squad- or component-level mapping can separate
# them - and the weapon-variant mechanism cannot either, since with exactly
# two models that each differ from the other there is no "majority loadout"
# to differ FROM.
#
# The filenames are the user's own ("Twin Blade Fusion"/"Twin Blade Ion"),
# and they line up with which main gun each model carries: Ri'Lantar has the
# Fusion eliminator, Ri'Locai the Ion scattercannon.
MODEL_SPRITE_KEYS = {
    "Ri'Lantar": "Twin Blade Fusion",
    "Ri'Locai": "Twin Blade Ion",
    # Beast Snagga Boyz' leader model. Same "one datasheet, two model lines
    # with their own art" case as the two Twin Lance models above - the
    # squad-level table cannot express it, because both lines share the
    # datasheet name. The rank and file fall through to SQUAD_SPRITE_KEYS'
    # "Beast Boy".
    "Beast Snagga Nob": "Beast Boy Nob",
    # Guardian Defenders' weapon platform. Third instance of the same case: one
    # datasheet, two model lines, each with its own art - the rank and file
    # fall through to SQUAD_SPRITE_KEYS' "Guardian Defender". Mapped to the
    # model LINE rather than through WEAPON_SPRITE_KEYS because only the Bright
    # Lance loadout is built (see game/factions/aeldari.py); if the platform
    # ever gains its alternative guns, the variant mechanism below is where
    # their art belongs.
    "Heavy Weapon Platform": "Bright Lance Weapon Platform",
}

# Maps (squad sprite key, weapon name) -> base filename, for variant art whose
# file is NOT named to the "<key> - <weapon>" convention. Consulted before
# that convention in _variant_candidates(), so a mapped file wins and an
# unmapped one still works the conventional way.
#
# Rail rifle: the art is in Sprites/ under the user's own name, and the
# convention would otherwise demand "Pathfinder Pulse Carbon - Rail Rifle.png".
# Nothing reaches it YET - no Rail rifle weapon profile has been supplied, so
# no Pathfinder ever counts as carrying one - but the mapping is here so that
# adding the weapon is the only remaining step.
WEAPON_SPRITE_KEYS = {
    ("Pathfinder Pulse Carbon", "Rail Rifle"): "Pathfinder Rail Rifle",
}

# Where on a given image the token's own base center should line up, as a
# fraction of that image's native (width, height) - (0,0) is the image's
# top-left corner, (1,1) its bottom-right. A raw geometric center (the
# default for any image not listed here) usually lands on an outstretched
# arm/weapon rather than the body itself, since most poses aren't
# symmetric - this anchors it to a sensible point instead (per the user:
# "möglichst im Bauchbereich", roughly the belly/torso). Keyed by the same
# base filename (without extension) used to resolve the file, so a future
# per-variant sprite (a different pose) can get its own anchor too.
SPRITE_ANCHORS = {
    "Fire Warrior Strike Squad": (245 / 346, 130 / 330),
}

# A token's on-screen art box is this many times its base DIAMETER on a
# side. The base itself stays its real size (the owner-color ring is drawn
# at the token's actual radius, unchanged from before sprites existed) -
# this is just a little slack so the art can overhang the base slightly
# instead of being squeezed to fit exactly inside it (User feedback: an
# earlier, much larger SPRITE_SCALE blew the art up far past the base,
# burying neighboring models under each other).
SPRITE_SCALE = 1.6

# Per-image overrides of SPRITE_SCALE, keyed by the same base filename
# (without extension) used to resolve the file - i.e. the same convention as
# SPRITE_ANCHORS above, so a future per-variant sprite ("Breacher - Leader")
# needs its own entry rather than inheriting this one. These exist because
# the art itself doesn't fill its own frame consistently: how large a model
# READS on screen depends on how much empty margin its PNG carries around
# the miniature, which no single global factor can even out (User: "die
# breacher sprites sind etwas zu groß, mach sie ein bisschen kleiner" / "das
# fireblade sprite ist ein bisschen zu klein, bitte etwas größer"). The
# token's own base (the owner-color ring) is unaffected - only the art box.
SPRITE_SCALE_OVERRIDES = {
    "Breacher": 1.45,
    "Tau Fireblade": 1.8,
    "Ork Deffdread": 1.8,  # User: "ork deffdread etwas größer"
}


def sprite_scale(base_name):
    """The art-box factor for this image - its SPRITE_SCALE_OVERRIDES entry
    if it has one, otherwise the shared SPRITE_SCALE."""
    return SPRITE_SCALE_OVERRIDES.get(base_name, SPRITE_SCALE)

GROUND_TEXTURE_NAME = "Ground"  # Sprites/Ground.<ext> - the battlefield floor, tiled across the whole board (see Renderer)
DENSE_COVER_TEXTURE_NAME = "Dense_Cover"  # Sprites/Dense_Cover.<ext> - tiled within a non-Dense footprint whose TerrainArea also has a Dense (wall) feature, see Renderer
NORMAL_COVER_TEXTURE_NAME = "Normal_Cover"  # Sprites/Normal_Cover.<ext> - tiled within a non-Dense footprint whose TerrainArea has no Dense (wall) feature, see Renderer

BLOOD_DECAL_NAME = "Blood"  # Sprites/Blood.<ext> - a small stain left where a model died (see GameState.add_blood_decal / Renderer.draw_blood_decals), purely cosmetic, no rule attached
BLOOD_DECAL_SCALE = 1.15  # decal diameter relative to the dead model's own base DIAMETER - a little larger than the base (reads as a stain the model stood in), but deliberately not blown up (User: "subtil")
BLOOD_DECAL_ALPHA = 255  # full opacity (User: first asked for ~50%, then "können wieder etwas auffälliger sein... also 100% opacity") - baked into the cached surface below via BLEND_RGBA_MULT (a no-op multiply at 255, i.e. the PNG's own per-pixel alpha is used as-is), not re-applied every frame

_file_cache = {}  # base filename (no ext) -> resolved path or None, so a repeated miss doesn't re-stat the disk every frame
_surface_cache = {}  # (path, target_px) -> pygame.Surface, so scaling only happens once per size actually needed, not every frame
_blood_surface_cache = {}  # target_px -> pygame.Surface, alpha already baked in - separate from _surface_cache since that one's shared with full-opacity unit portraits


def _resolve_path(base_name):
    if base_name in _file_cache:
        return _file_cache[base_name]
    resolved = None
    for ext in _EXTENSIONS:
        candidate = os.path.join(SPRITES_DIR, base_name + ext)
        if os.path.isfile(candidate):
            resolved = candidate
            break
    _file_cache[base_name] = resolved
    return resolved


def ground_texture_path():
    """Resolved path to Sprites/Ground.<ext>, or None if it isn't there -
    caller falls back to a flat color fill in that case, same "missing art
    is fine" convention as sprite_for()."""
    return _resolve_path(GROUND_TEXTURE_NAME)


def dense_cover_texture_path():
    """Resolved path to Sprites/Dense_Cover.<ext>, or None if it isn't
    there - caller falls back to the old translucent color tint for that
    footprint in that case, same "missing art is fine" convention as
    sprite_for()/ground_texture_path()."""
    return _resolve_path(DENSE_COVER_TEXTURE_NAME)


def normal_cover_texture_path():
    """Resolved path to Sprites/Normal_Cover.<ext>, or None if it isn't
    there - same fallback convention as dense_cover_texture_path()."""
    return _resolve_path(NORMAL_COVER_TEXTURE_NAME)


def blood_decal_path():
    """Resolved path to Sprites/Blood.<ext>, or None if it isn't there -
    caller simply draws no decal in that case, same "missing art is fine"
    convention as the other sprite lookups in this module."""
    return _resolve_path(BLOOD_DECAL_NAME)


def blood_decal_surface(path, diameter_px):
    """A cached surface for the blood decal at BLOOD_DECAL_ALPHA opacity,
    scaled (preserving aspect ratio) to fit within a
    (diameter_px * BLOOD_DECAL_SCALE) square. Alpha is baked into the
    surface once here via BLEND_RGBA_MULT (multiplies the existing
    per-pixel alpha, so the splat's own transparent background stays
    transparent regardless of BLOOD_DECAL_ALPHA's value) rather than
    re-applied every frame - unlike scaled_surface(), this path is only
    ever used for decals, so there's no other-opacity use case to protect
    by keeping the cached surface itself untouched."""
    target_px = max(1, round(diameter_px * BLOOD_DECAL_SCALE))
    cached = _blood_surface_cache.get(target_px)
    if cached is not None:
        return cached
    raw = pygame.image.load(path).convert_alpha()
    w, h = raw.get_size()
    scale = target_px / max(w, h)
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    scaled = pygame.transform.smoothscale(raw, size)
    scaled.fill((255, 255, 255, BLOOD_DECAL_ALPHA), special_flags=pygame.BLEND_RGBA_MULT)
    _blood_surface_cache[target_px] = scaled
    return scaled


def _key_for_name(name):
    """Substring match, not exact - see this module's docstring for why."""
    if not name:
        return None
    for datasheet_name, sprite_key in SQUAD_SPRITE_KEYS.items():
        if datasheet_name in name:
            return sprite_key
    return None


def _component_of(token):
    """The AttachedComponent this model came from, or None if its unit is
    not an attached unit (19.01)."""
    squad = token.squad
    if squad is None:
        return None
    for component in attached_units.components(squad):
        if token in component.starting_models:
            return component
    return None


def _squad_key(token):
    """Which sprite this MODEL should use.

    Resolved per model, not per squad, because an attached unit (19.01) is
    one Squad holding two datasheets' models. The squad's name is matched as
    a substring, so a merged name like "1 Crisis Starscythe Battlesuits 1 +
    Commander in Coldstar Battlesuit" hits whichever mapped key appears
    first in SQUAD_SPRITE_KEYS and hands that art to EVERY model in the
    unit - the Commander was drawn as a Crisis suit, and a Warboss attached
    to a Boyz mob is drawn as a Boy for the same reason. Matching on the
    merged name can never be right: one name, two datasheets.

    So a model that came from a recorded component is keyed off THAT
    component's own datasheet name, and only a model with no component
    (every ordinary squad) falls back to the squad-name match, unchanged.

    MODEL_SPRITE_KEYS comes first of all, for the case neither of those can
    express: ONE unit whose individually named models have their own art
    (The Twin Lance's Ri'Lantar and Ri'Locai). They share a datasheet and a
    squad, so no squad- or component-level mapping can tell them apart, and
    the weapon-variant mechanism cannot either - with two models that each
    differ from the other, "the majority loadout" is whichever one
    Counter.most_common() happens to return first."""
    profile_name = getattr(token.profile, "name", None) if token.profile is not None else None
    if profile_name is not None and profile_name in MODEL_SPRITE_KEYS:
        return MODEL_SPRITE_KEYS[profile_name]
    component = _component_of(token)
    if component is not None:
        source = component.datasheet.name if component.datasheet is not None else component.name
        key = _key_for_name(source)
        if key is not None:
            return key
    return _key_for_name(token.squad.name) if token.squad is not None else None


def _unusual_weapon_names(model):
    """Which of this model's own weapon names aren't part of its squad's
    majority loadout - reuses the same "unusual loadout" notion as
    Squad.unusual_loadout_models(), so a variant sprite lines up with the
    same tint highlight, but returns the actual differing weapon name(s)
    instead of just a yes/no.

    "Majority" is taken within the model's own COMPONENT for an attached
    unit (19.01): the variant sprites this feeds are per datasheet ("Boyz -
    Power Klaw"), so the comparison has to be against the datasheet's own
    rank and file. Measured against the merged unit instead, an attached
    Character - whose loadout differs from the bodyguards by definition -
    would always look "unusual" and go looking for variant art of a squad it
    isn't part of."""
    squad = model.squad
    if squad is None:
        return []
    component = _component_of(model)
    peers = component.starting_models if component is not None else squad.models
    peers = [m for m in peers if not m.is_dead()] or list(peers)
    if len(peers) <= 1:
        return []
    loadouts = [tuple(sorted(w.name for w in m.weapons)) for m in peers]
    majority = Counter(loadouts).most_common(1)[0][0]
    own = tuple(sorted(w.name for w in model.weapons))
    if own == majority:
        return []
    return [w.name for w in model.weapons if w.name not in majority]


def _variant_candidates(token):
    """Base filenames to try for this one token, most specific first,
    always ending with the plain standard key so a missing variant falls
    back to it (see this module's docstring)."""
    key = _squad_key(token)
    if key is None:
        return []
    candidates = []
    if token.profile is not None and token.profile.squad_leader:
        candidates.append(f"{key} - Leader")
    for weapon_name in _unusual_weapon_names(token):
        # An explicitly mapped filename first, then the "<key> - <weapon>"
        # convention. The override exists so art can keep the name it was
        # dropped in under: the convention would demand "Pathfinder Pulse
        # Carbon - Rail Rifle.png", but the file the user actually supplied
        # is "Pathfinder Rail Rifle.png". Asking for a rename would be the
        # wrong way round - this module already bends to the folder's own
        # spelling everywhere else (see "Ghostkheel"/"Starsythe").
        override = WEAPON_SPRITE_KEYS.get((key, weapon_name))
        if override is not None:
            candidates.append(override)
        candidates.append(f"{key} - {weapon_name}")
    candidates.append(key)
    return candidates


def sprite_for(token):
    """Resolved image path for this token, or None if its squad has no art
    at all - the caller should fall back to the plain disc + label."""
    for base_name in _variant_candidates(token):
        path = _resolve_path(base_name)
        if path is not None:
            return path
    return None


def portrait_paths(squad, limit=2):
    """The distinct images that represent this UNIT, most representative
    first - for panel/card listings, where a unit has to be recognised
    rather than a single model drawn.

    Per model rather than per squad for the same reason _squad_key() is: an
    attached unit (19.01) is one Squad holding two datasheets' models, so
    "the squad's sprite" is not a thing - a Boyz mob led by a Warboss has
    two, and showing both is exactly what tells it apart from the plain mob
    next to it. Deduped in model order (so the datasheet's own rank-and-file
    -then-leader order is kept, matching game/loadout.py's line listing) and
    capped at `limit`, since a listing tile has room for a couple of
    thumbnails, not for one per model line.

    Empty list if the unit has no art at all - callers draw text only, the
    same "missing art is fine" convention as sprite_for()."""
    if squad is None:
        return []
    models = [m for m in squad.models if not m.is_dead()] or list(squad.models)
    paths = []
    for model in models:
        path = sprite_for(model)
        if path is not None and path not in paths:
            paths.append(path)
            if len(paths) >= limit:
                break
    return paths


def fitted_surface(path, box_px):
    """A cached, alpha-aware surface for this image, scaled (preserving
    aspect ratio) to fit within a box_px square - cached per (path, target
    size), since a given on-screen size only changes with the window/zoom,
    not every frame."""
    target_px = max(1, round(box_px))
    cache_key = (path, target_px)
    cached = _surface_cache.get(cache_key)
    if cached is not None:
        return cached
    raw = pygame.image.load(path).convert_alpha()
    w, h = raw.get_size()
    scale = target_px / max(w, h)
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    scaled = pygame.transform.smoothscale(raw, size)
    _surface_cache[cache_key] = scaled
    return scaled


def scaled_surface(path, diameter_px):
    """A token's on-board art: fitted to a (diameter_px * sprite_scale())
    square, i.e. its base diameter plus this image's own overhang factor.
    Panel thumbnails call fitted_surface() directly instead - the scale
    overrides exist to even out how large a model READS next to its
    neighbours on the board, which a listing tile has no equivalent of."""
    base_name = os.path.splitext(os.path.basename(path))[0]
    return fitted_surface(path, diameter_px * sprite_scale(base_name))


def anchor_offset(path, surface_size):
    """Pixel position within a scaled_surface() result (of the given size)
    that should line up with the token's own base center - see
    SPRITE_ANCHORS. Uniform scaling (scaled_surface never stretches width
    and height by different factors) means the same fraction applies
    directly to the already-scaled size, no native size needed here."""
    base_name = os.path.splitext(os.path.basename(path))[0]
    frac_x, frac_y = SPRITE_ANCHORS.get(base_name, (0.5, 0.5))
    w, h = surface_size
    return frac_x * w, frac_y * h
