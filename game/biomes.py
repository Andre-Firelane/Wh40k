"""WHICH BIOME the battlefield is painted in - city, desert, forest or arena.

User: "ich habe die texturen für die maps in ordner geordnet. es gibt jetzt 3
biome. kannst du bei der map auswahl bitte ganz oben noch 3 knöpfe reinpacken,
über die man sein biom wählen kann?"

A biome answers exactly THREE ROLES: the ground under everything, plus the two
cover textures a terrain footprint is filled with (game/renderer.py splits
those by "does this footprint have a wall standing on it", not by terrain
CATEGORY - see DENSE_COVER/LIGHT_COVER below).

THREE OF THEM ANSWER WITH PICTURES, THE FOURTH WITH DRAWING CODE. Arena is
rendered rather than photographed (User: "dort besteht die map nicht aus
sprites, sondern du renderst sie") - see game/arena_biome.py, and
is_procedural() below, which is the ONE question the rest of the code asks
about the difference. Everything else here treats all four alike, which is the
point: a biome is still "which of the four buttons is pressed", and the two
ways of answering are a detail of the answer.

PURELY COSMETIC, and that is worth stating rather than assuming: no rule reads
the floor or the cover art, and the board size, both deployment zones, every
terrain footprint, every objective and every unit are identical whichever
biome is picked. Choosing one repaints the table; it does not change the game.
Pinned in test_biomes.py rather than left as a promise.

WHERE THE FILES LIVE: Sprites/Map Textures/<folder>/, one folder per biome -
the arrangement the user made. Until then the same three pictures sat loose in
Sprites/ under three fixed names in game/sprites.py, so moving them broke all
three lookups: measured before any of this was written, ground, dense-cover
and light-cover ALL resolved to None, i.e. the renderer had silently dropped
back to its flat-colour fallbacks. Restoring them is half of this module's job.

WHAT IS DECIDED HERE AND WHAT IS DISCOVERED. The table below carries the one
thing that is a decision - which biomes exist, what each is CALLED on its
button, and in what order they sit there. It does NOT carry filenames:

  * the three shipped folders already disagree about how to spell the same
    thing (Light_Cover-Desert.jpg with a hyphen against Light_Cover_City.jpg
    and Light_Cover_Forest.jpg with an underscore), and
  * the desert folder is spelled "Dessert" while every file inside it says
    "Desert".

This repo's standing rule for art is that THE FOLDER WINS - a spelling is
transcribed verbatim and never renamed (see game/sprites.py's eight Necron
cases and the four T'au ones). Transcribing nine filenames plus that typo
would be nine chances to drift; instead a ROLE is matched by its filename
PREFIX and whichever file carries it wins, so renaming
Light_Cover-Desert.jpg to Light_Cover_Desert.jpg later changes nothing here.
The display NAME is not discovered the same way, because it is a decision and
because deriving it from the folder would put "DESSERT" on a button.

A further biome therefore costs ONE LINE in BIOMES plus the folder - or, for a
drawn one, one line plus a module beside game/arena_biome.py.

NO FILESYSTEM IN THIS MODULE. Resolving a role to an actual file is
game/sprites.py's job, because that is where "where art lives" and "which
extensions count" are already defined once (SPRITES_DIR / _EXTENSIONS), and a
second copy of either is exactly the drift this repo consolidates. So this
module answers "which biomes exist / which is selected / which folder is it",
sprites.py answers "and where is its ground picture" - which is also what
keeps the import one-way (sprites imports biomes, never the reverse).
"""

from collections import namedtuple

from game import config

#: The three pictures a biome supplies. The names are the RENDERER's split -
#: "a footprint with a wall on it" against "a footprint without one" - not the
#: terrain category, same distinction game/sprites.py's public functions keep.
GROUND = "ground"
DENSE_COVER = "dense_cover"
LIGHT_COVER = "light_cover"

#: role -> the filename prefix that identifies it inside a biome folder.
#: Three mutually exclusive prefixes, so a file can only answer one role.
ROLE_PREFIXES = {
    GROUND: "Ground",
    DENSE_COVER: "Dense_Cover",
    LIGHT_COVER: "Light_Cover",
}

#: Sprites/<this>/<Biome.folder>/ - the folder the user sorted the textures
#: into. Relative to game/sprites.py's SPRITES_DIR, which is the one
#: definition of where art lives.
TEXTURE_SUBDIR = "Map Textures"

Biome = namedtuple("Biome", "key name folder")

#: In the order their buttons appear. `folder` is the name ON DISK, typo and
#: all - see the module docstring; `name` is what the button says.
#:
#: `folder=None` means THERE IS NO ART: that biome is drawn by code rather than
#: blitted from pictures (game/arena_biome.py). It is a fourth kind of answer
#: to the same three roles, not a fourth kind of biome - everything else on
#: this screen and in the renderer treats it exactly like the other three, and
#: is_procedural() below is the one place the difference is asked about.
BIOMES = (
    Biome("city", "City", "City"),
    Biome("desert", "Desert", "Dessert"),
    Biome("forest", "Forest", "Forest"),
    Biome("arena", "Arena", None),
)

BIOMES_BY_KEY = {b.key: b for b in BIOMES}

#: What an unknown config.BIOME falls back to: the same one config ships with,
#: so a stale or misspelled setting lands on the board the game normally opens
#: on rather than on a different-looking one. Kept in step with config.BIOME
#: deliberately - they answer two questions ("what do we start on" and "what do
#: we do with nonsense") whose right answer is the same, and a test pins that
#: they agree.
#:
#: It was "desert" until the arena biome arrived, on the grounds that those
#: three files are BYTE-IDENTICAL to the three that used to sit loose in
#: Sprites/ (verified by hash - Ground_Desert.jpg is the old wüste-boden.jpg,
#: Dense_Cover_Desert.jpg and Light_Cover-Desert.jpg are the old cover pair),
#: so an untouched setup rendered exactly what it did before biomes existed.
#: That is still TRUE of the desert biome and still checked - it is simply no
#: longer what the game opens on.
DEFAULT_BIOME = "arena"


def keys():
    """Every biome key, in button order."""
    return [b.key for b in BIOMES]


def get(key):
    """The Biome for `key`.

    Raises rather than falling back, same as maps.get()/army_lists.get(): a
    typo should surface as the named problem it is instead of quietly playing
    the default one - a silently wrong table is exactly what nobody notices."""
    try:
        return BIOMES_BY_KEY[key]
    except KeyError:
        raise KeyError(
            f"unknown biome {key!r} - known biomes are {', '.join(keys())}") from None


def current():
    """The selected Biome (config.BIOME).

    Tolerates a bad setting here where get() does not: this one is read on the
    RENDER path, every time the static layer is rebuilt, and a stale value in
    a settings file should repaint the table rather than take the game down
    mid-frame."""
    return BIOMES_BY_KEY.get(getattr(config, "BIOME", DEFAULT_BIOME),
                             BIOMES_BY_KEY[DEFAULT_BIOME])


def is_procedural(biome=None):
    """Is this biome DRAWN rather than blitted from pictures? (`biome` defaults
    to the selected one.)

    The one question anybody asks about the difference, so it is one function
    rather than a `folder is None` test spelled out at each of the renderer's
    two seams and again in every test - which is how two places end up
    disagreeing about what an empty folder means."""
    return (current() if biome is None else biome).folder is None
