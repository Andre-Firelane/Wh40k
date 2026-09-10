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

Separately, the THREE MAP TEXTURES (a single file each, no per-squad
mapping needed - there is only ever one battlefield) come from the selected
BIOME rather than from fixed names here: see game/biomes.py and
_biome_texture_path() below. ground_texture_path() is the board's
background and is NOT a repeatable tile (User: "das sprite soll die gesamte
map ausfuellen") - Renderer's static layer scales that single copy to cover
the ENTIRE board. dense_cover_texture_path() and
normal_cover_texture_path() are the same idea, tiled within each non-Dense
terrain footprint (a TerrainArea's Light/Exposed features - see
game/terrain.py) instead of the whole board; which one is picked depends on
whether that footprint's own TerrainArea also has a Dense feature (a wall)
standing on it (TerrainArea.has_dense_feature). All three fall back to a
flat colour when the art is missing, same convention as the rest of this
module.

Separately again, BLOOD_DECAL_NAME (a single "Sprites/Blood.<ext>" file) is
drawn at BLOOD_DECAL_ALPHA opacity, at the spot each model died - one decal per
death, accumulated in GameState.blood_decals and painted by
Renderer.draw_blood_decals(), unrelated to the per-squad sprite lookup
above. Missing art means no decals are drawn at all, same "missing art is
fine" convention as everything else in this module."""

import os
from collections import Counter

import pygame

from game import attached_units, biomes

SPRITES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Sprites")

_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

# Maps Squad.name -> base filename (without extension/variant suffix) in
# Sprites/. See this module's docstring for why this mapping exists instead
# of matching the datasheet name directly.
SQUAD_SPRITE_KEYS = {
    # --- Aeldari ---
    "Guardian Defenders": "Guardian Defender",  # the platform model has its own art, see MODEL_SPRITE_KEYS below
    # The user's file is named "Assault Guardian"; the datasheet is Storm
    # Guardians. The Serpent's Scale Platform no longer falls through to this
    # image - it is in MODEL_SPRITE_KEYS below, borrowing the Guardian
    # Defenders' platform art.
    "Storm Guardians": "Assault Guardian",
    "Striking Scorpions": "Striking Scorpion",  # the Exarch has no art of its own
    "Howling Banshees": "Howling Banshees",  # likewise - one image for the whole unit
    # The user's file is "Warpspider" (one word); the datasheet is Warp Spiders.
    "Warp Spiders": "Warpspider",  # one image for the whole unit, Exarch included
    "Dire Avengers": "Dire Avengers",
    "Fire Dragons": "Fire Dragons",
    "Falcon": "Falcon Tank",
    "Wraithguard": "Wraithguard",
    "Wraithlord": "Wraithlord",
    # The user's file is "Wraith Blades" (two words); the datasheet is one.
    "Wraithblades": "Wraith Blades",
    # --- art the user added later, wired here. THE ORDER MATTERS in this
    # block: _key_for_name() takes the FIRST datasheet name that is a SUBSTRING
    # of the squad name, so "Autarch Wayleaper" has to come before "Autarch" or
    # every Wayleaper would draw the plain Autarch's picture. Longest first.
    "Autarch Wayleaper": "Autarch Wayleaper",
    "Autarch": "Autarch",
    # The file is "Spirit Seer" (two words); the datasheet is one.
    "Spiritseer": "Spirit Seer",
    # "Vyper" (singular) against the plural datasheet - the same call made for
    # Windriders, Rangers and the Necron singulars: the FOLDER wins.
    "Vypers": "Vyper",
    # "D-Cannon" with a capital C; the datasheet prints a lower-case c.
    "D-cannon Platform": "D-Cannon Platform",
    # ...and its two sisters BORROW it (user: "alle wie D-Cannon"). They are one
    # chassis with three different guns bolted on - which is exactly what
    # test_support_weapon_platforms.py exists to say - so sharing the art is
    # the same call the three Kroot Shapers already got.
    "Shadow Weaver Platform": "D-Cannon Platform",
    "Vibro Cannon Platform": "D-Cannon Platform",
    # Corsair Voidscarred take the Voidreavers' art (user: "nimm das Corsair
    # Sprite, das schon da ist"). TWO corsair files exist, and this is the foot
    # one: Skyreavers are the JETBIKES and keep "Corsair Skyrunner".
    "Corsair Voidscarred": "Corsair Voidreavers",
    "Fire Prism": "Fire Prism",
    "Night Spinner": "Night Spinner",
    "Maugan Ra": "Maugan Ra",
    "Corsair Voidreavers": "Corsair Voidreavers",
    # "Corsair Skyrunner" is the only file it can belong to: Skyreavers are the
    # corsair JETBIKES, and Skyrunner is this range's word for a jetbike (the
    # Warlock Skyrunners' own file is "Warlock Sky Runner"). No datasheet is
    # named Corsair Skyrunner. Named here because it is the one mapping in this
    # block inferred from the subject rather than read off a matching name.
    "Corsair Skyreavers": "Corsair Skyrunner",
    "Asurmen": "Asurmen",
    # The user's file is "JainZar" (one word); the datasheet is Jain Zar.
    "Jain Zar": "JainZar",
    # The user's file is "Warlock Conclaive" (their spelling).
    "Warlock Conclave": "Warlock Conclaive",
    # BEFORE the plain "Farseer" below, and that ordering is the whole point:
    # _key_for_name() matches a datasheet name as a SUBSTRING of the squad name
    # and returns the FIRST hit, so "1 Farseer Skyrunner 1" would otherwise land
    # on the foot Farseer's art by accident. It lands there on purpose instead -
    # there is no Farseer Skyrunner file, and the same character on a jetbike is
    # the closest thing in the folder. An explicit entry says so, and survives a
    # future rename of either file; the accident would not.
    "Farseer Skyrunner": "Farseer",
    "Farseer": "Farseer",
    # The user's file is "Eldrad Ultran.png" - spelled without the h. The
    # folder's filenames are the source of truth here, as everywhere in this
    # table (cf. "Ghostkheel", "Starsythe", "Pulse Carbon").
    "Eldrad Ulthran": "Eldrad Ultran",
    # Also the folder's spelling: "Lykhis.png", without the h.
    "Lhykhis": "Lykhis",
    "Avatar of Khaine": "Avatar",
    # Art arrived for these ten in one go, after the datasheets were built.
    # Where a file name and a datasheet name differ it is the FILE that wins -
    # _resolve_path() matches the base filename exactly, and this module bends
    # to what is in Sprites/ rather than asking for renames (the same call
    # "Warpspider", "JainZar" and "Eldrad Ultran" already record).
    "Dark Reapers": "Dark Reaper",        # one image for the unit, Exarch included
    "Shining Spears": "Shining Spears",   # likewise
    "Swooping Hawks": "Swooping Hawks",   # likewise
    "Windriders": "Windrider",
    "Warlock Skyrunners": "Warlock Sky Runner",  # the file spells it as three words
    # The lone Warlock borrows the Conclave's art (user: "gleiches wie warlock
    # conclaive") - same model, and the Conclave IS a unit of them.
    #
    # LAST OF THE THREE "Warlock..." KEYS ON PURPOSE. _key_for_name() takes the
    # first datasheet name that is a SUBSTRING of the squad name, and "Warlock"
    # is a substring of both "Warlock Conclave" and "Warlock Skyrunners" - put
    # first, it would hand the Conclave's picture to the Skyrunners as well.
    "Warlock": "Warlock Conclaive",
    "Rangers": "Ranger",
    "Shroud Runners": "Shroud Runners",
    "Baharroth": "Baharroth",
    "War Walkers": "War Walker",
    "Wave Serpent": "Wave Serpent",
    # Fuegan.png had been sitting in the folder unused since the last batch -
    # there was no datasheet for it until now.
    "Fuegan": "Fuegan",
    "Strike Team": "Fire Warrior Strike Squad",
    "Breacher Team": "Breacher",
    "Kroot Carnivores": "Kroot Carnivores",
    # The file has been sitting unused in Sprites/ since before this
    # datasheet existed - the folder wins on spelling, as everywhere in
    # this table ("Vespid", not "Vespid Stingwings").
    "Vespid Stingwings": "Vespid",
    # Also already in Sprites/ and unused until this datasheet existed;
    # the folder wins on spelling ("Skyray", not "Sky Ray Gunship").
    "Sky Ray Gunship": "Skyray",
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
    # The seventeen datasheets added by the T'au catch-up, all with art dropped
    # in Sprites/ afterwards. The FOLDER wins on spelling wherever the two
    # disagree - the same decision "Ghostkheel", "Skyray" and "Vespid" already
    # record: this module bends to the folder rather than asking for renames.
    # Four disagree here: "Battlesuites" (a typo kept verbatim), "Dark Strider"
    # as two words, "Piranha" singular where the datasheet is plural, and the
    # two files prefixed "Tau ".
    "Broadside Battlesuits": "Broadside Battlesuites",
    "Commander Shadowsun": "Commander Shadowsun",
    "Commander in Enforcer Battlesuit": "Commander in Enforcer Battlesuit",
    "Crisis Fireknife Battlesuits": "Tau Crisis Fireknife",
    "Darkstrider": "Dark Strider",
    "Ethereal": "Ethereal",
    "Firesight Team": "Tau Firesight Team",
    "Hammerhead Gunship": "Hammerhead Gunship",
    "Kroot Hounds": "Kroot Hounds",
    "Kroot Lone-Spear": "Kroot Lone-Spear",
    "Krootox Rampagers": "Krootox Rampagers",
    "Krootox Riders": "Krootox Riders",
    "Piranhas": "Piranha",
    # User instruction: "fuer Farstalkers die normalen Kroot Sprites". So the
    # Kill-broker and his nine Farstalkers borrow the Kroot Carnivores art;
    # the two Kroot Hounds inside the unit are handled per MODEL below, since
    # a squad-level key cannot reach one line of a three-line datasheet.
    "Kroot Farstalkers": "Kroot Carnivores",
    # User instruction: "fuer alle Kroot characters Kroot Flesh Shaper.png".
    # That is the three Shapers - the Kroot Lone-Spear is a CHARACTER too but
    # has art of its own, so it keeps it.
    "Kroot Flesh Shaper": "Kroot Flesh Shaper",
    "Kroot Trail Shaper": "Kroot Flesh Shaper",
    "Kroot War Shaper": "Kroot Flesh Shaper",
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

    # --- Necrons ---
    # The folder wins wherever it disagrees with the datasheet, the same
    # decision "Warpspider", "JainZar" and "Warlock Sky Runner" already
    # record: five of these files are SINGULAR where the datasheet is plural
    # ("Necron Warrior", "Necron Immortal", "Necron Wraith"), and three name
    # the model rather than the unit ("Necron Destroyer" for Lokhust
    # Destroyers, "Necron Heavy Destroyer" for Lokhust Heavy Destroyers,
    # "Necron Shard of the Void Dragon" for the C'tan Shard).
    #
    # No ordering hazard here even though _key_for_name() returns on the FIRST
    # substring match: "Lokhust Heavy Destroyers" does not contain the string
    # "Lokhust Destroyers" (the word "Heavy" sits between them), so the two
    # cannot shadow each other whichever way round they are listed.
    "Necron Warriors": "Necron Warrior",
    "Immortals": "Necron Immortal",
    "Lychguard": "Necron Lychguard",
    "Overlord": "Necron Overlord",
    "Plasmancer": "Necron Plasmancer",
    "Technomancer": "Necron Technomancer",
    "Illuminor Szeras": "Necron IlluminorSzeras",   # the file has no space
    "Canoptek Wraiths": "Necron Wraith",
    "Skorpekh Destroyers": "Necron Skorpekh Destroyers",
    # The only Necron file WITHOUT the "Necron " prefix the other twelve
    # carry. The folder wins, as everywhere else in this table. No ordering
    # hazard against its own bodyguards either: "Skorpekh Lord" does not
    # contain "Skorpekh Destroyers" nor the reverse, and "Overlord" is not a
    # substring of it (the pair that would actually be easy to get wrong).
    "Skorpekh Lord": "Skorpekh Lord",
    # The second file without the "Necron " prefix, and the second pair that
    # could in principle shadow: "Lokhust Lord" contains neither "Lokhust
    # Destroyers" nor "Lokhust Heavy Destroyers", so no ordering matters here
    # either.
    "Lokhust Lord": "Lokhust Lord",
    "Lokhust Destroyers": "Necron Destroyer",
    "Lokhust Heavy Destroyers": "Necron Heavy Destroyer",
    "Doomsday Ark": "Necron Doomsday Ark",
    "C'tan Shard of the Void Dragon": "Necron Shard of the Void Dragon",
    # Crypteks. DER ORDNER GEWINNT: the Orikan file spells "the" in lower case
    # where the datasheet spells it "The". os.path.isfile is case-insensitive
    # on Windows, so an unmapped name would APPEAR to work here and break on a
    # case-sensitive filesystem - which is why it is written out rather than
    # left to the resolver.
    "Chronomancer": "Chronomancer",
    "Psychomancer": "Psychomancer",
    "Orikan The Diviner": "Orikan the Diviner",
    "Deathmarks": "Deathmarks",
    "Cryptothralls": "Cryptothralls",
    "Tomb Blades": "Tomb Blades",
    # Destroyer Cult. Both files agree with their datasheet exactly, which
    # after eight Necron disagreements is worth stating rather than assuming.
    # NEKROSOR AMMENTAR HAS NO ART - pinned as an absence in
    # test_necron_destroyer_cult.py, at the MODEL, so adding one later is a
    # visible change.
    #
    # SHADOWING, checked rather than hoped: _key_for_name() returns the FIRST
    # key that is a substring of the squad name, so a new key can be swallowed
    # by an earlier one or swallow a later one. Neither happens here -
    # "Hexmark Destroyer" and "Ophydian Destroyers" each contain no other key,
    # and no other Necron squad name contains either of them ("Lokhust
    # Destroyers" and "Skorpekh Destroyers" share only the word "Destroyer",
    # which is not a key on its own). Measured in the suite, not asserted here.
    "Hexmark Destroyer": "Hexmark Destroyer",
    "Ophydian Destroyers": "Ophydian Destroyers",

    # --- Death Guard ---
    # EIGHT of these eleven files disagree with the datasheet name, and the
    # folder wins in every one - the same decision "Warpspider", "JainZar",
    # "Eldrad Ultran", "Flash GItz", "Ghostkheel" and "Necron IlluminorSzeras"
    # already record. Four kinds of disagreement, all deliberate:
    #   * a space the datasheet does not have: "Death Shroud Terminators",
    #     "Malignant Plague Caster", "Pox Walkers", "Blight Hauler",
    #     "Bloat Drone";
    #   * a faction prefix the datasheet does not carry: "Deathguard Defiler";
    #   * words the datasheet does not use: "Blight Hauler" and "Bloat Drone"
    #     drop the printed "Myphitic" and "Foetid";
    #   * two misspellings in one filename: "Demon Price of Nurgle" for the
    #     Daemon Prince. Kept verbatim - _resolve_path() matches the base
    #     filename exactly, so "correcting" it here would lose the art.
    #
    # ORDERING HAZARD, checked rather than assumed, because _key_for_name()
    # returns on the FIRST substring match and this faction has three keys
    # beginning "Plague": "Plague Marines", "Plagueburst Crawler" and
    # "Malignant Plaguecaster". None contains another ("Plague Marines" is not
    # inside "Plagueburst Crawler", and neither is inside "Malignant
    # Plaguecaster"), so no ordering between them matters. The suite pins that
    # by asserting the three resolve to three DIFFERENT files.
    "Plague Marines": "Plague Marines",
    "Poxwalkers": "Pox Walkers",
    "Typhus": "Typhus",
    "Malignant Plaguecaster": "Malignant Plague Caster",
    "Daemon Prince of Nurgle": "Demon Price of Nurgle",
    "Chaos Spawn": "Chaos Spawn",
    "Deathshroud Terminators": "Death Shroud Terminators",
    "Defiler": "Deathguard Defiler",
    "Foetid Bloat-drone": "Bloat Drone",
    "Myphitic Blight-hauler": "Blight Hauler",
    "Plagueburst Crawler": "Plagueburst Crawler",
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
    # The two Kroot Hounds printed INSIDE a Kroot Farstalkers unit. Fourth
    # instance of the one-datasheet-several-lines case, and the first with
    # THREE lines: the Kill-broker and the Farstalkers take the squad-level
    # "Kroot Farstalkers" -> Kroot Carnivores art, and these take the Kroot
    # Hounds datasheet's own. A squad-level key cannot reach them - the squad
    # is named "1 Kroot Farstalkers 1", so the "Kroot Hounds" key never
    # matches - which is exactly what this table is for.
    "Kroot Hound (Farstalker)": "Kroot Hounds",
    # Storm Guardians' Serpent's Scale Platform. Same one-datasheet-two-lines
    # case again, and it used to be the documented EXCEPTION to it: there is no
    # art of its own, so it fell through to SQUAD_SPRITE_KEYS' "Assault
    # Guardian" and was drawn as a rank-and-file Storm Guardian. On user
    # request it now borrows the Guardian Defenders' platform art instead
    # ("benutze das bright lance waffen platform sprite auch fuer das serpent
    # shield der storm guardians") - the two are the same kit, and reading as a
    # platform matters more than the gun on it being wrong (this one carries no
    # gun at all).
    "Serpent's Scale Platform": "Bright Lance Weapon Platform",
}

# Maps (squad sprite key, weapon name) -> base filename, for variant art whose
# file is NOT named to the "<key> - <weapon>" convention. Consulted before
# that convention in _variant_candidates(), so a mapped file wins and an
# unmapped one still works the conventional way.
#
# Rail rifle: the art is in Sprites/ under the user's own name, and the
# convention would otherwise demand "Pathfinder Pulse Carbon - Rail Rifle.png".
# It is LIVE - the Retaliation Cadre list fields three rail rifles. (This note
# used to say "nothing reaches it YET, no Rail rifle weapon profile has been
# supplied"; that stopped being true when the weapon was added.)
#
# Ion rifle: BORROWED art, on user request ("nimm fuer die ion rifles bei den
# pathfindern bitte auch das rail rifle sprite"). There is no ion rifle image,
# and the two are the same silhouette - a long-barrelled rifle rather than the
# carbine the rank and file carry - so reading as "this one has the big gun"
# matters more than which big gun it is. Exactly the trade already recorded for
# the Serpent's Scale Platform borrowing the Bright Lance platform's art.
#
# Keyed on "Ion Rifle - Standard", not "Ion Rifle": the profile carries its
# firing MODE in its name (it has an overcharge profile), and this table is
# matched against the weapon name a model actually holds. The overcharge mode
# is an alternative ON that instance rather than a second weapon, so it never
# appears here and needs no second entry.
WEAPON_SPRITE_KEYS = {
    ("Pathfinder Pulse Carbon", "Rail Rifle"): "Pathfinder Rail Rifle",
    ("Pathfinder Pulse Carbon", "Ion Rifle - Standard"): "Pathfinder Rail Rifle",
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
    # User: "defiler bitte verkleinern. genau so groß wie devilfish, falcon".
    # Its BASE was already identical to theirs (2.1", see UnitProfile) - what
    # made it look bigger is the art: measured, the Defiler's opaque content
    # fills 0.93 x 0.88 of its image where the Devilfish fills 0.94 x 0.70 and
    # the Falcon 0.74 x 0.88, i.e. ~25% more area inside the same box. The art
    # box is therefore shrunk by sqrt(0.655 / 0.82) = 0.89, which is what makes
    # the three read as the same size on the table.
    "Deathguard Defiler": 1.43,
}


def sprite_scale(base_name):
    """The art-box factor for this image - its SPRITE_SCALE_OVERRIDES entry
    if it has one, otherwise the shared SPRITE_SCALE."""
    return SPRITE_SCALE_OVERRIDES.get(base_name, SPRITE_SCALE)

# THE THREE MAP TEXTURES COME FROM THE SELECTED BIOME (game/biomes.py), not
# from three fixed names here any more. They used to sit loose in Sprites/ as
# wüste-boden.jpg / Dense_Cover-Desert.jpg / Light_Cover-Desert.jpg; the user
# sorted them into Sprites/Map Textures/<biome>/ and added a city and a forest
# set beside them ("ich habe die texturen für die maps in ordner geordnet. es
# gibt jetzt 3 biome"), which broke all three of the old lookups at once -
# measured, every one of them resolved to None and the renderer had quietly
# fallen back to flat colours.
#
# WHAT EACH IS FOR is unchanged, and stays described here because this is
# where the renderer asks:
#
#   ground       one picture of a whole battlefield, NOT a repeatable tile
#                (User: "das sprite soll die gesamte map ausfuellen") - the
#                static layer scales a single copy to cover the ENTIRE board.
#                Falls back to the flat BACKGROUND_COLOR fill when missing.
#   dense cover  tiled inside a non-Dense terrain footprint whose TerrainArea
#                ALSO has a Dense feature (a wall) standing on it - a ruin's
#                floor with walls rising out of it.
#   light cover  tiled inside a non-Dense footprint with no wall at all - a
#                standalone barricade, crater or rubble patch.
#
# The split between the last two is "does this footprint have a wall on it",
# NOT the terrain CATEGORY - which is why normal_cover_texture_path() keeps
# its NORMAL_ name even though the file it now resolves to says "Light".
# Both fall back to the old translucent colour tint when missing.
def _biome_texture_path(role):
    """Resolved path to the current biome's picture for `role`
    (biomes.GROUND / DENSE_COVER / LIGHT_COVER), or None if that folder has
    no file for it - same "missing art is fine" convention as sprite_for().

    None ALSO for a biome that has no art at all - the arena one is DRAWN
    (game/biomes.py's is_procedural(), game/arena_biome.py). That is not the
    same "missing art" as above and the renderer must not treat it as one, so
    the renderer asks is_procedural() BEFORE it asks here; the guard is
    repeated on this side because the alternative is a crash on
    os.path.join(..., None) for anyone who calls these in the other order.

    The file is found by PREFIX inside the biome's folder rather than by a
    transcribed name (see game/biomes.py for why: the shipped folders spell
    the same role three different ways). Sorted before picking, so a folder
    that somehow holds two candidates answers the same way every run instead
    of following whatever order the filesystem happened to hand back."""
    biome = biomes.current()
    if biomes.is_procedural(biome):
        return None
    prefix = biomes.ROLE_PREFIXES[role].lower()
    folder = os.path.join(SPRITES_DIR, biomes.TEXTURE_SUBDIR, biome.folder)
    cache_key = (folder, role)
    if cache_key in _texture_cache:
        return _texture_cache[cache_key]
    resolved = None
    try:
        entries = sorted(os.listdir(folder))
    except OSError:
        entries = []
    for entry in entries:
        base, ext = os.path.splitext(entry)
        if ext.lower() in _EXTENSIONS and base.lower().startswith(prefix):
            resolved = os.path.join(folder, entry)
            break
    _texture_cache[cache_key] = resolved
    return resolved

FACTION_LOGO_KEYS = {
    # Sprites/<value>.<ext> - one faction badge each, keyed by the faction
    # keyword that game/factions/faction.py's Faction carries (and every one
    # of its datasheets with it), so the lookup goes through the same name
    # the rules use rather than a second list of army names to keep in sync.
    # Drawn by GameStatusPanel beside each player's name. A keyword with no
    # entry (or an entry with no file) still gets a TILE - the panel fills it
    # with the faction's monogram instead (see _faction_monogram there), so
    # adding a badge here is art arriving for an existing tile, not a feature
    # switching on. DEATH GUARD is the one built faction currently in that
    # position.
    "AELDARI": "Aeldari Logo",
    "ORKS": "Ork Logo",
    "T'AU EMPIRE": "Tau Logo",
    "NECRONS": "Necron Logo",
    # Delivered later than the other four. THE FOLDER WINS, as everywhere in
    # this module: the file is "Deathguard_Logo.jpg" - one word, underscore -
    # where the other four are "<Faction> Logo" with a space, and the keyword
    # is two words. Transcribed as it is on disk rather than renamed.
    "DEATH GUARD": "Deathguard_Logo",
}

MENU_BACKGROUND_NAME = "main-manu-background"  # Sprites/**/main-manu-background.<ext> - the startup menu's backdrop. The user's own spelling ("manu"); see menu_background_path().
BLOOD_DECAL_NAME = "Blood"  # Sprites/Blood.<ext> - a small stain left where a model died (see GameState.add_blood_decal / Renderer.draw_blood_decals), purely cosmetic, no rule attached
# One fixed size for every stain, in inches, rather than one scaled off the
# dead model's own base. User: "mach die blutflecken immer klein". The old
# relative sizing (1.15x the base DIAMETER) meant a Riptide or a Battlewagon
# left a stain several inches across while a Gretchin left a dot - the bigger
# ones read as terrain rather than as a mark on the floor.
#
# The value is the middle of the range the old rule produced for INFANTRY,
# which is the size the user had been looking at without complaint (a
# Gretchin's 0.5" base gave 1.15", a Boy's 0.63" gave 1.45") - so "small"
# here means "the infantry stain, for everyone", not a new smaller dot.
BLOOD_DECAL_DIAMETER_IN = 1.3
BLOOD_DECAL_ALPHA = 255  # full opacity (User: first asked for ~50%, then "können wieder etwas auffälliger sein... also 100% opacity") - baked into the cached surface below via BLEND_RGBA_MULT (a no-op multiply at 255, i.e. the PNG's own per-pixel alpha is used as-is), not re-applied every frame

_texture_cache = {}  # (biome folder, role) -> resolved path or None, so switching biome on the map screen re-lists a folder once rather than once per frame; keyed by FOLDER so each biome keeps its own answer
_file_cache = {}  # base filename (no ext) -> resolved path or None, so a repeated miss doesn't re-stat the disk every frame
_surface_cache = {}  # (path, target_px) -> pygame.Surface, so scaling only happens once per size actually needed, not every frame
_menu_background_cache = {}  # (path, w, h) -> cover-scaled backdrop; the window size only changes when the window does, and this is a full-screen smoothscale
_blood_surface_cache = {}  # target_px -> pygame.Surface, alpha already baked in - separate from _surface_cache since that one's shared with full-opacity unit portraits
_printed_loadout_cache = {}  # (datasheet, profile class) -> frozenset of printed weapon names or None, so _printed_weapon_names() doesn't walk a datasheet's compositions once per token per frame


#: Sprites/ is sorted into one folder per faction, plus the cross-faction files
#: that stay at the top level (Blood, Dice, Map3, and the Map Textures biomes).
#: The folders are SEARCHED, not encoded in the mapping tables - every key in
#: SPRITE_KEYS/MODEL_SPRITE_KEYS/FACTION_LOGO_KEYS is still a bare file name, so
#: sorting the folder cost those tables nothing and a file can be moved between
#: factions without touching code.
#:
#: Listed rather than derived from the faction modules on purpose: this module
#: must not import game.factions (that would be a cycle, and sprites are
#: resolved on the render path), and a folder that is renamed on disk should
#: fail loudly here rather than silently resolve nothing.
SPRITE_FACTION_DIRS = ("Aeldari", "Orks", "Tau Empire", "Necrons", "Death Guard")


def _resolve_path(base_name):
    """The file for this key, searched at the top level and then in each
    faction folder.

    Top level FIRST, so a cross-faction file always wins over a same-named one
    inside a faction folder - and so anything dropped loose into Sprites/ keeps
    working, which is how new art arrives before it is sorted."""
    if base_name in _file_cache:
        return _file_cache[base_name]
    resolved = None
    folders = [SPRITES_DIR] + [os.path.join(SPRITES_DIR, d)
                               for d in SPRITE_FACTION_DIRS]
    for folder in folders:
        for ext in _EXTENSIONS:
            candidate = os.path.join(folder, base_name + ext)
            if os.path.isfile(candidate):
                resolved = candidate
                break
        if resolved is not None:
            break
    _file_cache[base_name] = resolved
    return resolved


def faction_logo_path(faction_keyword):
    """Resolved path to this faction's badge, or None if the faction has no
    entry in FACTION_LOGO_KEYS or its file isn't in Sprites/ - the caller
    draws a monogram tile in that case rather than dropping the badge (see
    GameStatusPanel._draw_badge), so None here costs a picture, not a row."""
    base_name = FACTION_LOGO_KEYS.get(faction_keyword)
    return _resolve_path(base_name) if base_name is not None else None


def ground_texture_path():
    """The current biome's battlefield floor, or None if it isn't there -
    caller falls back to a flat colour fill in that case."""
    return _biome_texture_path(biomes.GROUND)


def dense_cover_texture_path():
    """The current biome's cover texture for a footprint that HAS a wall
    standing on it, or None - caller falls back to the old translucent colour
    tint for that footprint."""
    return _biome_texture_path(biomes.DENSE_COVER)


def normal_cover_texture_path():
    """The current biome's cover texture for a footprint with NO wall on it,
    or None - same fallback as dense_cover_texture_path().

    Named NORMAL_ rather than LIGHT_ because the renderer's split is
    wall/no-wall, not the terrain CATEGORY - the file it resolves to is the
    biome's Light_Cover one."""
    return _biome_texture_path(biomes.LIGHT_COVER)


def menu_background_path():
    """Resolved path to the main menu's backdrop, or None if the file isn't
    there - the caller falls back to the flat fill it used before, the same
    "missing art is fine" convention as every other lookup in this module.

    The file the user supplied sits in Sprites/Death Guard/ rather than loose
    at the top level. That is fine and deliberately not "corrected": this
    module already searches the faction folders after the top level, and the
    standing rule here is that the FOLDER wins over what a name suggests it
    should be (the same rule that keeps Ghostkheel, Starsythe, Skyray and
    Deathguard_Logo spelled the way they arrived). Dropping it loose into
    Sprites/ later keeps working too, because the top level is searched first.

    The name carries the user's own spelling, "manu" and all - transcribing it
    "correctly" would resolve to nothing."""
    return _resolve_path(MENU_BACKGROUND_NAME)


def menu_background_surface(path, size):
    """The backdrop scaled to COVER a `size` window, centre-cropped.

    Cover rather than fitted_surface()'s fit: a letterboxed backdrop leaves
    bars of flat colour down two sides of the screen, which reads as art that
    failed to load rather than as a background. Aspect ratio is preserved and
    the overhang is cropped off the middle, so nothing is stretched.

    Cached per (path, size) like every other surface here - a window size only
    changes when the window does, not per frame, and this is a full-screen
    smoothscale."""
    width, height = max(1, int(size[0])), max(1, int(size[1]))
    cache_key = (path, width, height)
    cached = _menu_background_cache.get(cache_key)
    if cached is not None:
        return cached
    raw = pygame.image.load(path)
    raw = raw.convert() if pygame.display.get_surface() is not None else raw
    src_w, src_h = raw.get_size()
    scale = max(width / src_w, height / src_h)
    scaled = pygame.transform.smoothscale(
        raw, (max(1, round(src_w * scale)), max(1, round(src_h * scale))))
    surface = pygame.Surface((width, height))
    surface.blit(scaled, ((width - scaled.get_width()) // 2,
                          (height - scaled.get_height()) // 2))
    _menu_background_cache[cache_key] = surface
    return surface


def blood_decal_path():
    """Resolved path to Sprites/Blood.<ext>, or None if it isn't there -
    caller simply draws no decal in that case, same "missing art is fine"
    convention as the other sprite lookups in this module."""
    return _resolve_path(BLOOD_DECAL_NAME)


def blood_decal_surface(path, diameter_px):
    """A cached surface for the blood decal at BLOOD_DECAL_ALPHA opacity,
    scaled (preserving aspect ratio) to fit within a diameter_px square -
    the caller passes BLOOD_DECAL_DIAMETER_IN converted to pixels, so every
    stain is the same size and only the zoom level changes it. Alpha is
    baked into the
    surface once here via BLEND_RGBA_MULT (multiplies the existing
    per-pixel alpha, so the splat's own transparent background stays
    transparent regardless of BLOOD_DECAL_ALPHA's value) rather than
    re-applied every frame - unlike scaled_surface(), this path is only
    ever used for decals, so there's no other-opacity use case to protect
    by keeping the cached surface itself untouched."""
    target_px = max(1, round(diameter_px))
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


def _printed_weapon_names(model):
    """The weapon names this model's own datasheet LINE prints as its
    default loadout, or None when they can't be determined - a hand-built
    Squad (every testkit scene) has no datasheet, and neither does a model
    whose profile matches no line on the one it has.

    Looked up on the model's own COMPONENT for an attached unit (19.01),
    falling back to the squad's datasheet for an ordinary one: the variant
    sprites this feeds are per datasheet ("Boyz - Power Klaw"), so an
    attached Character has to be measured against HIS sheet, not against the
    bodyguards' one.

    Keyed by profile CLASS rather than by line name, because a ModelLine's
    name is free text an army list may override while the profile class is
    the model's identity. Checked across all 71 datasheets rather than
    assumed: no sheet has two lines that share a profile class and print
    different weapons, so the answer is unambiguous. Cached because
    sprite_for() runs per token per frame - and read off the weapon CLASSES
    (their `name` is a class attribute) so nothing is instantiated here."""
    if model.profile is None:
        return None
    component = _component_of(model)
    datasheet = component.datasheet if component is not None else None
    if datasheet is None and model.squad is not None:
        datasheet = model.squad.datasheet
    if datasheet is None:
        return None
    profile_cls = type(model.profile)
    cache_key = (datasheet, profile_cls)
    if cache_key in _printed_loadout_cache:
        return _printed_loadout_cache[cache_key]
    printed = None
    for composition in datasheet.compositions():
        for line in composition:
            if line.profile_cls is profile_cls:
                printed = frozenset(w.name for w in line.default_weapons)
                break
        if printed is not None:
            break
    _printed_loadout_cache[cache_key] = printed
    return printed


def _unusual_weapon_names(model):
    """Which of this model's own weapon names its datasheet line does NOT
    print - i.e. what it picked up from a Wargear Option, which is exactly
    what a "<key> - <weapon>.png" file depicts.

    THIS IS A STATIC FACT ABOUT THE MODEL, and it has to be: the art shows
    the gun in the model's hands, so casualties elsewhere in the unit cannot
    change which picture is right. An earlier version asked instead whether
    the loadout differed from the squad's live MAJORITY, reusing
    Squad.unusual_loadout_models()' notion so a variant sprite lined up with
    the same tint highlight. That drifted, and was reported: once losses left
    the plain rank and file merely TIED with a special-weapon group,
    Counter.most_common() broke the tie by model order and crowned the
    special weapon "the majority" - so Storm Guardians' two fusion gunners
    stopped counting as unusual and fell back to the plain Assault Guardian
    art mid-battle (measured: 2 plain and 1 flamer dead is enough).

    The two notions are deliberately no longer the same question. The tint
    says "this model stands out from the squadmates around it", which is a
    live, relative statement and right for a highlight; this says "this model
    carries a weapon its datasheet doesn't print", which is what the file
    name means. Squad.unusual_loadout_models() is left alone.

    Falls back to the old majority vote when the printed loadout can't be
    read at all (a hand-built Squad has no datasheet), so every testkit scene
    keeps working exactly as before."""
    squad = model.squad
    if squad is None:
        return []
    printed = _printed_weapon_names(model)
    if printed is not None:
        return [w.name for w in model.weapons if w.name not in printed]
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


def _by_line_frequency(models):
    """`models` reordered so the most numerous model line comes first,
    keeping each line's own relative order (a stable sort by -count).

    A unit is recognised by its rank and file, not by the one support model
    standing in it: a Guardian Defenders squad reads as "Guardian Defenders"
    and only incidentally as "one Bright Lance platform", and a Boyz mob as
    Boyz rather than as its single Boss Nob. The datasheet's own model order
    puts those single models FIRST (it lists the special line before the
    rank and file), so without this a two-thumbnail listing spends one of
    its two slots on the least representative model in the unit."""
    counts = {}
    for model in models:
        counts[model.profile.name] = counts.get(model.profile.name, 0) + 1
    return sorted(models, key=lambda m: -counts[m.profile.name])


def _portrait_model_order(squad):
    """Which models portrait_paths() scans, and in which order.

    An ordinary unit is its own models, most numerous line first (see
    _by_line_frequency()). An attached unit (19.01) is one Squad holding
    several datasheets' models, and there the model order is whatever
    attach() happened to concatenate - which put the bodyguards first, so a
    two-thumbnail listing of a Guardian Defenders mob led by a Farseer
    showed the Guardians and their weapon platform and cut the character off
    entirely.

    User: "wenn du 2 sprites anzeigen laesst ... dann zeige immer zuerst den
    charakter an und danach den squad ... dort soll der der teurste charakter
    angezeigt werden (farseer) und dann der squad (defenders)". So exactly
    ONE character leads - the most expensive one, which is what tells a
    Farseer from the Warlock Conclave attached to the same unit - then the
    bodyguards, then any remaining characters. Leading with one and not with
    all of them is the point: with two thumbnails the pair has to say
    "Farseer" AND "Guardian Defenders", not "Farseer and a Warlock".

    Scanned over AttachedComponent.starting_models rather than Squad.models
    because that is what carries the provenance; dead models are filtered by
    the caller, and keeping them here is what lets a wiped-out unit still
    fall back to its own art (same as before)."""
    components = getattr(squad, "attached_components", None) or []
    if not components:
        return _by_line_frequency(list(squad.models))

    characters = [c for c in components if c.is_leader_or_support]
    bodyguards = [c for c in components if not c.is_leader_or_support]
    # points may be None (an unpriced faction) - sorted last among the
    # characters rather than first, the same "None is not cheap, it is
    # unknown" reading ai/agent_driver.py's garrison cost key uses.
    characters.sort(key=lambda c: -(c.points or 0))
    ranked = (characters[:1] + bodyguards + characters[1:])

    ordered, seen = [], set()
    for component in ranked:
        for model in _by_line_frequency(component.starting_models):
            if id(model) not in seen:
                seen.add(id(model))
                ordered.append(model)
    for model in squad.models:  # defensive: anything no component claims
        if id(model) not in seen:
            seen.add(id(model))
            ordered.append(model)
    return ordered


def portrait_paths(squad, limit=2):
    """The distinct images that represent this UNIT, most representative
    first - for panel/card listings, where a unit has to be recognised
    rather than a single model drawn.

    Per model rather than per squad for the same reason _squad_key() is: an
    attached unit (19.01) is one Squad holding two datasheets' models, so
    "the squad's sprite" is not a thing - a Boyz mob led by a Warboss has
    two, and showing both is exactly what tells it apart from the plain mob
    next to it. Deduped in _portrait_model_order() (see there for why an
    attached unit leads with its character) and capped at `limit`, since a
    listing tile has room for a couple of thumbnails, not for one per model
    line.

    Empty list if the unit has no art at all - callers draw text only, the
    same "missing art is fine" convention as sprite_for()."""
    if squad is None:
        return []
    return _paths_of(_portrait_model_order(squad), limit)


def models_portrait_paths(models, limit=2):
    """The distinct images representing an arbitrary set of models.

    The same question one level down from portrait_paths(): the army
    selection screen lists an attached unit's LEADER separately from its
    bodyguards, so what needs a picture there is one AttachedComponent's
    models rather than a whole Squad's.

    Ordered by _by_line_frequency() - a set of models with no component
    structure is recognised by its rank and file, which is exactly what that
    ordering is for. NOT the same as calling portrait_paths() on the squad:
    that one deliberately leads with the character (see
    _portrait_model_order()), which is the opposite of what a tile that has
    already split the character out wants."""
    return _paths_of(_by_line_frequency(list(models)), limit)


def _paths_of(ordered_models, limit):
    """Distinct sprite paths for models already in the order they should be
    considered, capped at `limit`. Living models are preferred, with a
    wiped-out set falling back to its own art."""
    models = [m for m in ordered_models if not m.is_dead()] or list(ordered_models)
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
