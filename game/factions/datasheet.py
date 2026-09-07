"""Datasheet scaffold: a unit's full rules as printed on a real 10th-edition
datasheet - stats, composition, keywords, and possible wargear - stored as
data, independent of any battle.

This engine has no generic keyword/ability-application system (see
CLAUDE.md's Später-Liste: "einzelne fest verdrahtete Boolean-/Wert-Felder
pro tatsächlich gebrauchter Fähigkeit" instead of one). A Datasheet doesn't
invent a second way to express abilities either - a model's UnitProfile
subclass and its weapons' WeaponProfile subclasses (in game/units.py and
game/weapons.py) remain the single source of truth for every rule the
engine actually enforces (e.g. LETHAL HITS, DEEP STRIKE, INFANTRY). A
Datasheet only groups those already-defined profiles into a real unit:
which model types it has, how many of each, and which of their weapons can
be swapped for which others (WargearOption) or which non-weapon wargear
items they can be given (Gear, e.g. a T'au support drone) - the same
information a paper datasheet's "Unit Composition" and "Wargear Options"
sections carry. `abilities_text` covers everything else purely for
reference/display, since attaching it to game logic would need an ability
system this engine deliberately doesn't have (see game/factions/
detachment.py's Enhancement for the same note) - a Gear item's `effect`
callback is the one deliberate exception, needed because "equip this
wargear" has to actually mutate the bearer model, unlike a purely
descriptive ability.
"""

from game import aspect_shrine
from game import drakolithe_tokens
from game.squad import Squad
from game.token import Token


class ModelLine:
    """One row of a datasheet's "Unit Composition" text, e.g. "1 Boss Nob"
    or "9 Boyz": a UnitProfile subclass (the model's stat line) together
    with how many of them a unit built from this composition option has,
    and what each one is equipped with by default. `default_weapons` is a
    list of WeaponProfile CLASSES, not instances - every model gets its own
    fresh weapon instances in build_squad(), matching Token.weapons'
    existing "never share weapon instances across models" invariant (relied
    on e.g. by melta_adjusted_weapon() and Epic Challenge's per-model
    [PRECISION] grant)."""

    def __init__(self, profile_cls, count, default_weapons, name=None):
        self.profile_cls = profile_cls
        self.count = count
        self.default_weapons = list(default_weapons)
        self.name = name or profile_cls.name


class WargearOption:
    """One "Wargear Options" bullet on a datasheet: within a given
    ModelLine (matched by name - the same line name recurs across a
    datasheet's different composition_options, e.g. a "10 models" and a
    "20 models" build of the same unit, and a wargear option applies to
    both alike), some number of models may replace one of their default
    weapons with one or more others.

    `replaces` is a WeaponProfile class, a tuple/list of them, or None for a
    pure addition rather than a swap. The multi-weapon form exists because
    some options trade away a model's whole printed loadout at once - Beast
    Snagga Boyz' thump gun carrier gives up both its Slugga AND its Choppa
    for a Thump gun plus a Close combat weapon (see game/factions/orks.py).
    That is NOT the same as the "replace-then-re-add" shape Tankbustas uses,
    which exists for the opposite problem (one of several duplicate copies
    of the SAME weapon). `max_models` caps how many models in the unit may take the
    option (None = unlimited, i.e. real text like "any model can...").
    `per_models` implements ratio-limited upgrades ("for every 5 models in
    this unit, 1 may...") - the cap is computed against the WHOLE unit's
    model count (every ModelLine's count summed), matching how that phrase
    is conventionally worded on real datasheets, not just this option's own
    line. If both are given, the tighter cap wins.

    `points` is what the faction's points list charges per model taking this
    option ("WARGEAR OPTIONS: per Cyclic Ion Raker 15 pts") - 0 for the
    majority of options, which are free. The number itself belongs to the
    points list, not to this option, so a datasheet is expected to read it
    out of its own UnitPoints.wargear rather than repeating the literal (see
    game/factions/points.py)."""

    def __init__(self, model_line_name, replaces, with_weapons, max_models=None, per_models=None, name=None, points=0):
        self.model_line_name = model_line_name
        self.replaces = replaces
        # Normalised form the swap actually reads, so a single class and a
        # tuple of them take the same code path. `replaces` itself is kept
        # as given for callers that only want to know what was declared.
        if replaces is None:
            self.replaced_profiles = ()
        elif isinstance(replaces, (tuple, list)):
            self.replaced_profiles = tuple(replaces)
        else:
            self.replaced_profiles = (replaces,)
        self.with_weapons = list(with_weapons)
        self.max_models = max_models
        self.per_models = per_models
        self.points = points
        self.name = name or self._default_name()

    def _default_name(self):
        gained = "/".join(w.name for w in self.with_weapons) or "nothing"
        if self.replaced_profiles:
            lost = " + ".join(w.name for w in self.replaced_profiles)
            return f"{lost} -> {gained}"
        return f"+ {gained}"

    def max_for(self, unit_size):
        """None means uncapped (besides the ModelLine's own model count,
        which build_squad() enforces separately)."""
        caps = [c for c in (self.max_models, (unit_size // self.per_models) if self.per_models else None) if c is not None]
        return min(caps) if caps else None


class Gear:
    """One "wargear" menu item that ISN'T a simple weapon-for-weapon swap
    (see WargearOption for that case) - a named optional item applied via
    an `effect(token)` callback that mutates the bearer directly, e.g. a
    T'au support drone granting a keyword, a characteristic change, a
    defensive rule, or (Gun Drone) an actual weapon. Real 40k datasheets
    very often phrase leader/character wargear this way - "this model can
    be equipped with up to N of the following" - a "pick up to N items"
    menu, which is a different shape from WargearOption's "how many
    rank-and-file models take this swap" counting - so it's selected via
    build_squad()'s separate `gear` parameter, not folded into `choices`,
    and capped by the owning Datasheet's `gear_slots` for that model line
    rather than a per-option max_models/per_models.

    `max_count` is normally 1 - "never the same item twice" (e.g. Strike/
    Breacher Team's drone menu: Marker/Shield/Guardian/Gun Drone, pick up
    to 2 DISTINCT ones). A datasheet can explicitly allow repeats of one
    specific item (e.g. Stealth Battlesuits' Shas'vre: up to 2 Gun Drones,
    the same item twice) by raising it - build_squad() applies effect()
    once per repeat, still bounded by the line's overall gear_slots cap.

    `group` names which MENU this item belongs to, for a datasheet whose
    model line has more than one independent menu with its own cap - e.g.
    Pathfinder Team's Shas'ui takes "up to 2 drones AND one special drone
    from these 3", two separate allowances that must not be spendable on
    each other. None (the default) means the item just counts against the
    line's single flat cap, which is what every datasheet before this one
    needed; see Datasheet.gear_slots for how the two forms are expressed.

    `all_models` turns the item from "this line's character takes it" into
    "every model on this line takes it". Every menu before the Necrons needed
    the former (a Shas'ui's drones, an Exarch's shimmershield), so it defaults
    to False and no existing datasheet changes behaviour. Lychguard are the
    first case of the latter: their printed option replaces the warscythe with
    "1 hyperphase sword and 1 dispersion shield" on ALL models at once, and a
    shield that only ever reached the first model would silently give four of
    the five no invulnerable save."""

    def __init__(self, model_line_name, name, effect, max_count=1, group=None, points=0,
                 all_models=False):
        self.model_line_name = model_line_name
        self.name = name
        self.effect = effect  # callable(token) -> None
        self.max_count = max_count
        self.group = group
        self.all_models = all_models
        # What the faction's points list charges per copy taken, same meaning
        # (and same "read it out of UnitPoints.wargear, never repeat the
        # literal" convention) as WargearOption.points. 0 for the many free
        # items - every drone menu so far - and first actually used by
        # Battlewagon's 'Ard Case.
        self.points = points


class Datasheet:
    """A full unit entry: keywords, composition, and wargear options, built
    from UnitProfile/WeaponProfile classes that already exist (or are added
    to game/units.py and game/weapons.py) elsewhere. `faction` is set by
    Faction.add_datasheet(), not passed in directly - a Datasheet is only
    ever meaningful as part of one faction's roster."""

    def __init__(
        self, name, keywords=(), model_lines=(), wargear_options=(),
        composition_options=None, points=None, abilities_text=(),
        gear_options=(), gear_slots=None, faction_keywords=(),
    ):
        self.name = name
        self.faction = None
        self.keywords = tuple(keywords)
        # A real datasheet prints TWO keyword lines, and they are different
        # things: "KEYWORDS:" (above) is what this model is, "FACTION
        # KEYWORDS:" is which army it may be taken in. Almost every rule reads
        # the first, so for a long time only the first was modelled - but the
        # Aeldari detachments ask about ASURYANI, which lives only on the
        # second, and which is NOT the same set as any flag already here: 54
        # Aeldari datasheets print Battle Focus, only 51 print ASURYANI (the
        # Ynnari triumvirate prints the army rule while belonging to YNNARI).
        # Kept as its own field rather than folded into `keywords`, because
        # merging two printed lines into one tuple is exactly the conflation
        # this repo renames rather than copies.
        self.faction_keywords = tuple(faction_keywords)
        # composition_options: a list of "unit builds", each a list of
        # ModelLine - e.g. Boyz's real datasheet offers a 10-model and a
        # 20-model build, each its own list. model_lines/composition_options
        # are two ways to say the same thing: pass model_lines for a
        # datasheet that only comes in one size (composition_options stays
        # None, compositions() wraps model_lines in a single-entry list);
        # pass composition_options directly for a datasheet with more than
        # one size, and leave model_lines empty.
        self.model_lines = list(model_lines)
        self.composition_options = (
            [list(option) for option in composition_options] if composition_options else None
        )
        self.wargear_options = list(wargear_options)
        self.gear_options = list(gear_options)  # Gear items (see Gear) - not weapon swaps
        # {model_line_name: cap}. `cap` is either an int - the flat "at most
        # N Gear items on a model of this line" every datasheet used before
        # Pathfinder Team - or a {group_name: N} dict for a line with several
        # independent menus, each with its own allowance (see Gear.group).
        # The dict form's TOTAL is the sum of its caps, so an item whose
        # group isn't listed can never be taken.
        self.gear_slots = dict(gear_slots) if gear_slots else {}
        # This unit's entry in its faction's published points list (a
        # points.UnitPoints), or None for a datasheet whose faction's list
        # hasn't been transcribed yet (every Orks one today) - see
        # points_for() and game/factions/tau_empire_points.py.
        self.points = points
        self.abilities_text = tuple(abilities_text)

    def compositions(self):
        return self.composition_options if self.composition_options else [self.model_lines]

    def wargear_for(self, model_line_name):
        return [o for o in self.wargear_options if o.model_line_name == model_line_name]

    def gear_for(self, model_line_name):
        return [g for g in self.gear_options if g.model_line_name == model_line_name]

    def points_for(self, composition_index=0, unit_index=1, choices=None, gear=None,
                   weapon_counts=None):
        """What one unit built from this datasheet costs: its points list's
        own price for that unit size, plus every priced wargear option the
        `choices` actually select (see game/factions/points.py for why a
        priced option is never charged for the printed default loadout).

        `gear` is the same {model_line_name: [item name, ...]} shape
        build_squad() takes, and priced the same way as `choices`: only what
        is actually selected is charged. build_squad() passes what it really
        APPLIED (after every cap has trimmed the request), so the two can
        never disagree; a caller asking directly is trusted as given.

        `unit_index` is which copy of this datasheet the army is buying,
        1-based - the published list prices e.g. a 3rd Ghostkeel higher than
        the first two, so the same build genuinely costs different amounts
        depending on what else is in the list.

        None means "not priced": no points list for this datasheet's faction
        yet, or a unit size the list doesn't name. Deliberately not 0 -
        "free" and "unknown" have to stay distinguishable for any later army
        builder to add up honestly."""
        if self.points is None:
            return None
        lines = self.compositions()[composition_index]
        base = self.points.cost_for(sum(line.count for line in lines), unit_index)
        if base is None:
            return None
        wargear_cost = sum(
            option.points * take
            for per_option in _resolved_choices(self, lines, choices).values()
            for option, take in per_option.items()
        )
        wargear_cost += self._gear_cost(gear)
        wargear_cost += self._per_weapon_cost(weapon_counts)
        return base + wargear_cost

    def _per_weapon_cost(self, weapon_counts):
        """What this unit's "per <weapon>" prices come to, given what it ended
        up carrying.

        The published list prices some options PER WEAPON rather than per swap
        - "per T'au flamer 5 pts" - and the two only agree while the printed
        default carries none of it. Two datasheets here break that: Crisis
        Fireknife and Crisis Starscythe Battlesuits come with one of the priced
        weapon per model as standard. See game/factions/points.py for the
        user-supplied list that settles which reading is right.

        `weapon_counts` is a {normalised weapon name: count} map of the FINISHED
        unit, which only build_squad() can produce - so a caller pricing a build
        it has not made gets the per-swap figure and, for those two datasheets,
        an answer that is short by the default's own weapons. Named rather than
        guarded, because every caller in this engine goes through build_squad().
        """
        if not weapon_counts:
            return 0
        priced = getattr(self.points, "per_weapon", None) or {}
        return sum(price * weapon_counts.get(_normalise_weapon(item), 0)
                   for item, price in priced.items())

    def _gear_cost(self, gear):
        """What the selected `gear` adds. Counts repeats (an item with
        max_count > 1 may be taken several times), and silently ignores a
        name this datasheet does not offer - the same forgiving treatment
        build_squad() gives an over-eager selection."""
        if not gear:
            return 0
        total = 0
        for line_name, names in gear.items():
            priced = {g.name: g for g in self.gear_for(line_name)}
            for name in names:
                item = priced.get(name)
                if item is not None:
                    total += item.points
        return total


def _resolved_choices(datasheet, lines, choices):
    """{model_line_name: {WargearOption: model count taking it}} for one
    composition, after applying every cap (the option's own max_for(unit
    size) and the ModelLine's model count) - i.e. what the caller's requested
    `choices` actually amount to, over-eager numbers already trimmed.

    Shared by build_squad(), which applies those swaps, and
    Datasheet.points_for(), which prices them, so the two can never disagree
    about how many models really took an option."""
    unit_size = sum(line.count for line in lines)
    resolved = {}
    for line in lines:
        option_choices = (choices or {}).get(line.name, {})
        per_option = {}
        for option in datasheet.wargear_for(line.name):
            take = _requested_count(option_choices.get(option.name, 0))
            cap = option.max_for(unit_size)
            if cap is not None:
                take = min(take, cap)
            per_option[option] = min(take, line.count)
        resolved[line.name] = per_option
    return resolved


def _normalise_weapon(name):
    """One spelling for a weapon name, so a points list's "per T'au flamer" and
    a profile's "T'au Flamer" are the same key. The published lists and the
    weapon profiles disagree on case and punctuation as a matter of course."""
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def _requested_count(value):
    """How many models a `choices` entry asks for, whether it was written as
    a plain count or as an explicit list of model indices (see build_squad).
    Pricing goes through here too, so the two spellings cost the same."""
    if isinstance(value, (list, tuple, set, frozenset)):
        return len(set(value))
    return value


def _explicit_indices(datasheet, lines, choices, resolved):
    """{model_line_name: {WargearOption: (model index, ...)}} for the options
    a caller addressed by index rather than by count - empty for the usual
    case, since every entry written as a plain number is left to the cursor.

    Trimmed against the SAME resolved count the caps produced, so an
    over-eager index list is cut down the same way an over-eager number is
    (and so it still prices as what was actually applied). Out-of-range
    indices are dropped rather than clamped: clamping would quietly pile two
    options onto the last model, which is the very thing an explicit list is
    written to avoid."""
    explicit = {}
    for line in lines:
        option_choices = (choices or {}).get(line.name, {})
        per_option = {}
        for option in datasheet.wargear_for(line.name):
            value = option_choices.get(option.name, 0)
            if not isinstance(value, (list, tuple, set, frozenset)):
                continue
            wanted = sorted({i for i in value if 0 <= i < line.count})
            per_option[option] = tuple(wanted[:resolved[line.name][option]])
        explicit[line.name] = per_option
    return explicit


def build_squad(
    datasheet, owner, composition_index=0, choices=None, gear=None,
    name=None, x_in=0.0, y_in=0.0, color=(200, 200, 200), unit_index=1,
):
    """Turns a Datasheet plus a chosen loadout into a real Squad of Tokens -
    the actual models a battle uses. Every model starts stacked on
    (x_in, y_in) - the same starting state SetupController already gives a
    reserve unit dropped on the board - spreading them into a legal
    formation is the caller's job (main.py's demo scene today, or a real
    deployment flow later), not this factory's; this only decides WHICH
    models exist and what they're carrying.

    `composition_index` selects one of datasheet.compositions() (e.g. 0 for
    Boyz's 10-model build, 1 for its 20-model build). `choices` is
    {model_line_name: {wargear_option_name: model_count}} - how many models
    of that line take each option, applied in the order given.

    A count may instead be written as an explicit list of 0-based model
    indices within that line, for the one thing the cursor cannot express:
    WHICH models. Two options replacing DIFFERENT weapons deliberately land
    on the same models (a champion taking both a gun and a melee upgrade is
    the common case, and Player 1's earlier Storm Guardians list wanted
    exactly that), so a list is how an army list says "these two upgrades go
    on different models" instead. It is a property of the list, not of the
    datasheet - both distributions are legal - which is why it lives here and
    not on WargearOption. An addressed option ignores the cursor entirely,
    and the cursor steps over any model an addressed option claimed, so the
    two spellings can be mixed on one line without colliding. Each
    option's own max_for(unit size) and its ModelLine's model count both
    still cap it, so an over-eager choice is silently trimmed rather than
    rejected - callers presenting this as a UI choice (as opposed to a
    hardcoded scene, like main.py's current demo squads) are expected to
    enforce the real cap themselves before calling, the same way e.g.
    ExplosivesController enforces its own choice's legality before
    resolving it.

    `gear` is {model_line_name: [gear_name, ...]} - Gear items (drones and
    the like), applied ONLY to the line's first model and capped/deduped at
    datasheet.gear_slots[model_line_name] - correct for every gear-bearing
    ModelLine so far (always a unique, count=1 leader slot); would need a
    per-model gear list instead of one flat name-list if a future datasheet
    ever let several models in the same line each pick their own gear.

    `unit_index` is which copy of this datasheet the army is buying (1-based)
    - it affects nothing about the models built, only what they cost, since
    a points list can price a 3rd copy of a unit differently from the first
    two (see Datasheet.points_for()). The resulting cost is stored on the
    returned Squad.points."""
    gear = gear or {}
    lines = datasheet.compositions()[composition_index]
    resolved = _resolved_choices(datasheet, lines, choices)
    explicit = _explicit_indices(datasheet, lines, choices, resolved)

    models = []
    # What gear was ACTUALLY applied, line by line, after every cap has
    # trimmed the request. points_for() is priced from this rather than from
    # the caller's raw `gear`, so applying and pricing cannot disagree about
    # how many copies were really taken - the same invariant _resolved_
    # choices() gives the weapon-swap side.
    applied_gear = {}
    for line in lines:
        assignments = [list(line.default_weapons) for _ in range(line.count)]

        # Two options that replace the SAME weapon have to land on DIFFERENT
        # models. Every option used to start at model 0, so "up to 2 can swap
        # their pistol for a flamer" and "up to 2 can swap their pistol for a
        # fusion gun" both hit models 0-1: those two ended up carrying a flamer
        # AND a fusion gun, while only two pistols were given up instead of
        # four. Real pre-existing bug, latent until Storm Guardians triggered it
        # (Pathfinders' three carbine swaps have it too, and the demo army only
        # escapes it because its two picks sit on different model LINES).
        #
        # So a cursor per group of options that compete for the same weapon.
        # Grouped by whether their replaced sets INTERSECT rather than match
        # exactly: Howling Banshees is the datasheet that needs the difference -
        # two of its Exarch options replace the Banshee Blade and a third
        # replaces the Shuriken Pistol AND the Banshee Blade, so the sets
        # overlap without being equal, and treating them as unrelated would let
        # one model take both. Groups merge as they grow, so a third
        # overlapping option joins the same cursor.
        #
        # Options that replace NOTHING - pure additions like a Homing Beacon -
        # still start at model 0, since those legitimately share a model with a
        # swap.
        cursor_groups = []  # [[union of replaced profiles, next free model index], ...]
        # Models an explicit index list has claimed on this line. The cursor
        # steps over these, so mixing the two spellings cannot silently stack
        # a counted option on top of an addressed one.
        claimed = {i for idx in explicit[line.name].values() for i in idx}
        for option, take in resolved[line.name].items():
            addressed = explicit[line.name].get(option)
            replaced = frozenset(option.replaced_profiles or ())
            group = None
            if addressed is None and replaced:
                for candidate in cursor_groups:
                    if candidate[0] & replaced:
                        candidate[0] |= replaced
                        group = candidate
                        break
                if group is None:
                    group = [set(replaced), 0]
                    cursor_groups.append(group)
            if addressed is not None:
                # Written by index: this option says which models itself, so
                # it neither reads nor advances a cursor.
                indices = list(addressed)
            else:
                indices = []
                index = group[1] if group is not None else 0
                while len(indices) < take and index < line.count:
                    if index not in claimed:
                        indices.append(index)
                    index += 1
                if group is not None:
                    group[1] = index
            for index in indices:
                weapons = assignments[index]
                if option.replaced_profiles:
                    # A swap whose premise is false is skipped, not silently
                    # turned into a free addition. Dire Avengers is the first
                    # datasheet where this can be reached: its shimmershield
                    # replaces a Shuriken Pistol the Exarch only carries if an
                    # EARLIER option put one there, and the printed text says
                    # so ("If this unit's Exarch is equipped with..."). Options
                    # are applied in order against the live weapon list, so
                    # that chaining works - and this guard is what makes the
                    # unchained choice illegal instead of merely odd. A pure
                    # addition (replaced_profiles empty) is unaffected.
                    if not any(w in option.replaced_profiles for w in weapons):
                        continue
                    weapons[:] = [w for w in weapons if w not in option.replaced_profiles]
                weapons.extend(option.with_weapons)

        line_tokens = []
        for weapons in assignments:
            profile = line.profile_cls()
            line_tokens.append(Token(
                x_in, y_in, profile.base_radius_in, color,
                profile=profile, weapons=[w() for w in weapons],
            ))
        models.extend(line_tokens)

        gear_names = gear.get(line.name, [])
        slots = datasheet.gear_slots.get(line.name, 0)
        # Either a flat int cap or per-menu caps (see Datasheet.gear_slots).
        group_caps = slots if isinstance(slots, dict) else None
        total_slots = sum(group_caps.values()) if group_caps is not None else slots
        if gear_names and total_slots and line_tokens:
            gear_by_name = {g.name: g for g in datasheet.gear_for(line.name)}
            counts = {}
            per_group = {}
            applied = 0
            for gear_name in gear_names:
                if applied >= total_slots:
                    continue  # over-eager choice - silently trimmed, same convention as wargear_options above
                item = gear_by_name.get(gear_name)
                if item is None:
                    continue
                if counts.get(gear_name, 0) >= item.max_count:
                    continue  # repeat beyond what this specific item allows (normally 1 - "never the same item twice")
                if group_caps is not None:
                    # This line has several independent menus; an item can
                    # only use up its OWN menu's allowance, so e.g. a third
                    # ordinary drone can't be taken in place of the one
                    # special drone. Trimmed silently, same convention.
                    if per_group.get(item.group, 0) >= group_caps.get(item.group, 0):
                        continue
                    per_group[item.group] = per_group.get(item.group, 0) + 1
                counts[gear_name] = counts.get(gear_name, 0) + 1
                applied += 1
                # Normally the line's first model - that is what a "this
                # character can be equipped with" menu means. Gear(all_models=True)
                # is the printed "ALL models in this unit can each have..."
                # form instead; see Gear's own docstring.
                targets = line_tokens if item.all_models else line_tokens[:1]
                for target in targets:
                    item.effect(target)
                # Remember WHAT was applied, not just its effect. A Gear item
                # is a callback that mutates the token (a Shield Drone bumps
                # Wounds, a Guardian Drone sets a flag, a Marker Drone can be
                # a no-op for a unit that already has MARKERLIGHT) - so
                # without this the item's identity is unrecoverable, and two
                # otherwise identical units that differ ONLY by their drones
                # are indistinguishable in any UI. Needed by
                # game/loadout.py's unit description.
                for target in targets:
                    target.gear_names.append(gear_name)
                # Recorded once per SELECTION, not once per bearer: this list
                # is what points_for() prices, and the printed option is one
                # choice however many models it dresses.
                applied_gear.setdefault(line.name, []).append(gear_name)

    # What the unit ENDED UP carrying, for the "per <weapon>" prices - see
    # Datasheet._per_weapon_cost(). Counted here rather than re-derived there,
    # so the price and the models can never disagree.
    built_weapons = {}
    for model in models:
        for weapon in model.weapons:
            key = _normalise_weapon(weapon.name)
            built_weapons[key] = built_weapons.get(key, 0) + 1
    squad = Squad(
        name or datasheet.name, models, owner=owner,
        points=datasheet.points_for(composition_index=composition_index, unit_index=unit_index,
                                    choices=choices, gear=applied_gear,
                                    weapon_counts=built_weapons),
    )
    # Which datasheet this unit came from - the only way rule 19.01's
    # "Leader and support units can only lead specific bodyguard units"
    # pairing table (transcribed as UnitPoints.leads/.supports) can be
    # looked up for a built unit, since Squad.name is a scene-chosen label
    # ("2 Boyz 1"), not the datasheet's own name.
    squad.datasheet = datasheet
    # ASPECT WARRIORS wargear: "for every 5 models in this unit, it can have 1
    # Aspect Shrine token". Granted here rather than offered as a menu item -
    # it costs nothing and has no downside, so it is a choice with one sensible
    # answer (see game/aspect_shrine.py). Read off starting strength, which is
    # exactly what this Squad was just built with.
    aspect_shrine.grant_tokens(squad)
    # The Exodites' Drakolithe: the Leystalker prints two outright, the
    # Dragon Knights get "2 for every 3 models". Granted here for the same
    # reason the Aspect Shrine tokens are - it is free and has no downside,
    # so it is a choice with one sensible answer - and read off the starting
    # strength this Squad was just built with.
    drakolithe_tokens.grant_tokens(squad)
    return squad
