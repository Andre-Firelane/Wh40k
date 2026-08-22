from game.dice_notation import D3, D6


class UnitProfile:
    """Base Warhammer-style stat profile shared by all unit archetypes.

    Matches the current (10th-edition-style) datasheet stat block: M/T/Sv/W/
    Ld/OC at the unit level, plus WS/BS as per-model characteristics (shown
    on real datasheets next to each weapon, for convenience, rather than in
    the top block - but still a model-level stat as far as our resolution
    logic is concerned). Strength and Attacks are no longer unit-level
    characteristics on a real datasheet - every weapon (ranged or melee)
    carries its own S/A/AP/D, which is why WeaponProfile has them and this
    class doesn't."""

    name = "Unit"
    base_radius_in = 0.5  # ~25mm base (radius, in inches) - the token's on-board size; overridden per profile below
    movement_in = 6
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 4
    wounds = 1
    leadership = "7+"
    armor_save = "5+"
    invulnerable_save = "-"  # "-" = no invulnerable save; e.g. "4+" once a profile has one
    oc = 1  # Objective Control - rule 14.02, read by game.objectives.Objective.level_of_control()
    character = False  # the CHARACTER keyword - matters for save-roll wound allocation (05.03)
    monster = False  # the MONSTER keyword - matters for hazard rolls (06.03)
    vehicle = False  # the VEHICLE keyword - matters for hazard rolls (06.03)
    walker = False  # the WALKER keyword - rule 15.11 (Heroic Intervention): lets an otherwise-pure-VEHICLE unit qualify alongside CHARACTER; see HeroicInterventionController._has_walker(). No other rule in this engine reads it yet (unlike AIRCRAFT/TITANIC, which remain pure no-op carve-outs since no datasheet has needed them)
    infantry = False  # the INFANTRY keyword - matters for moving through Dense terrain (13.06)
    beasts = False  # the BEASTS keyword - matters for moving through Dense terrain (13.06)
    swarm = False  # the SWARM keyword - matters for moving through Dense terrain (13.06)
    mobile = False  # the MOBILE keyword - matters for moving through Dense terrain (13.06)
    kroot = False  # the KROOT keyword - matters for a TRANSPORT's transport_excludes (e.g. Devilfish can't carry KROOT models), see TransportController.can_embark()
    vespid_stingwings = False  # the VESPID STINGWINGS keyword - same purpose as `kroot` above (another of Devilfish's named exclusions); no datasheet sets this yet
    fly = False  # the FLY keyword - matters for Take to the Skies (21.03)
    jump_pack = False  # the JUMP PACK keyword - matters for a TRANSPORT's transport_excludes (e.g. Trukk can't carry JUMP PACK models), see TransportController.can_embark(); no other rule in this engine reads it (purely descriptive otherwise, like MOUNTED/SMOKE)
    hover = False  # the HOVER ability (24.17) - Take to the Skies doesn't subtract 2" from this unit's max distance
    deep_strike = False  # the [DEEP STRIKE] ability - rule 24.09, only meaningful during an Ingress move (20.04)
    infiltrators = False  # the INFILTRATORS ability - rule 24.20, a deployment-time set-up rule (see squad_has_infiltrators())
    lone_operative = None  # LONE OPERATIVE X" range (rule 24.24), in inches; None = no ability. See status_effects.lone_operative_range()
    stealth = False  # the STEALTH ability - rule 24.33, see squad_has_stealth()
    scouts = None  # SCOUTS X" ability (rule 24.31/24.32), in inches; None = no ability. Genuinely live since the Pre-game Sequence (03.01) was built - game/scouts.py reads it for the Scout Move step (the earlier "stored but not yet consumed, deferred until Pregame Setup" note here was left behind when that arrived)
    for_the_greater_good = False  # T'au Empire army rule "For The Greater Good" - user-supplied, not a core rulebook rule; see game/greater_good.py
    fleet_of_foot = False  # Guardian Defenders' own ability: this unit performs the Fade Back Agile Manoeuvre for FREE, is not blocked by another unit having done it this phase, and does not block others from doing it either - see game/battle_focus.py. Still costs the unit its one manoeuvre per phase; the ability exempts it from the token and from the per-manoeuvre limit, nothing more
    flickerjump = False  # Warp Spiders' own ability: an optional Normal-move upgrade to a 24" Move characteristic, at the cost of the unit's charge for the turn and a D6-per-model mortal wound roll at the end of the phase - see game/flickerjump.py
    branching_fates = False  # the Farseer's own ability: while leading a unit, once per phase one Hit, Wound or Damage roll made for a model in it becomes an unmodified 6 - see game/branching_fates.py
    guide = False  # the Farseer's own ability: marks one enemy unit at the end of his Movement phase; friendly AELDARI models add 1 to Hit rolls against it until the start of his next Command phase - see game/guide.py
    doom = False  # Eldrad Ulthran's own ability: Guide's twin one word apart - marks one enemy unit at the end of his Movement phase; friendly AELDARI models add 1 to WOUND rolls against it until the start of his next Command phase. Shares its machinery with Guide (game/psychic_mark.py); unlike Guide it prints NO once-per-turn cap - see game/doom.py
    empyric_ambush = False  # Lhykhis' own ability: while she leads a unit, that unit may still declare a charge in a turn it used Flickerjump. The only ability here that undoes another one, and it works by making game/flickerjump.py skip its own charge lock rather than by ignoring the shared flag afterwards - see game/empyric_ambush.py
    whispering_web = False  # Lhykhis' own ability: after she shoots, one enemy unit she hit is marked until the end of the turn, and friendly AELDARI models score a Critical Hit against it on an unmodified 5+. First source of a lowered crit threshold that is NOT melee-only, which is why game/melee_crit.py became game/crit_hit.py - see game/whispering_web.py
    molten_form = False  # the Avatar of Khaine's own ability: each attack allocated to this model has its Damage characteristic halved (rounding up). The first halving in this engine - see game/molten_form.py, which also records why mortal wounds are not halved
    bloody_handed = False  # the Avatar of Khaine's own aura: friendly AELDARI units within 6" add 1 to Advance and Charge rolls. Folded with War Horde's 'Ere We Go in game/roll_bonus.py, which is the one place the two roll sites ask - see game/bloody_handed.py
    diviner_of_futures = False  # Eldrad Ulthran's own ability: +1 CP at the start of your Command phase while he is on the battlefield. Goes through command_points.gain_cp(), so the user's +1-bonus-CP-per-battle-round house rule applies - see game/diviner_of_futures.py
    support_weapon = False  # the SUPPORT WEAPON keyword - read by game/branching_fates.py's exclusion. No SUPPORT WEAPON datasheet exists here yet
    psychic_communion = False  # Warlock Conclave's own ability: each Warlock's Destructor gains +1 A and +1 S per other friendly AELDARI PSYKER model within 6" of it, max +2 - see game/psychic_communion.py
    protect = False  # Warlock Conclave's own ability: while a FARSEER leads the unit, attacks targeting it subtract 1 from the Wound roll - see game/protect.py
    farseer = False  # the FARSEER keyword - read by game/protect.py. Kept separate from `psyker` because Protect names this keyword specifically: the Farseer and Eldrad Ulthran are FARSEER, while the Warlock Conclave is PSYKER but not
    whirling_death = False  # Jain Zar's own ability: while she leads a unit, its Advance is not rolled - a flat +6" to the Move characteristic for the phase instead - see game/whirling_death.py
    storm_of_silence = False  # Jain Zar's own ability: her attacks may re-roll the Wound roll against a CHARACTER unit - see game/storm_of_silence.py
    tactical_acumen = False  # Asurmen's own ability: while he is leading a unit, that unit may make a 6" Normal move after it shoots, at the cost of its charge - see game/tactical_acumen.py
    hand_of_asuryan = False  # Asurmen's own ability: once per battle, his Bloody Twins gains Damage 3, [ANTI-INFANTRY 5+] and [DEVASTATING WOUNDS] until end of phase - see game/hand_of_asuryan.py
    war_construct = False  # Wraithguard's own ability: this unit may shoot in a turn in which it Fell Back - the same 09.07 exception Crisis Starscythe's Battlesuit Support System grants, read at game/shooting.py's available_shooting_types()
    psychic_guidance = False  # Wraithguard's own ability: while within 12" of a friendly AELDARI PSYKER model, Ld becomes 6+ and every attack gets +1 to Hit - see game/psychic_guidance.py
    wraith_construct = False  # the WRAITH CONSTRUCT keyword - a TRANSPORT counts each such model as 2 (Falcon's printed line), see game/transport.py's _model_capacity_cost()
    fire_support = False  # the Falcon's own ability: after this model shoots, one enemy unit it hit is marked, and units that disembarked from it this turn may re-roll Wound rolls against that unit until end of turn - see game/fire_support.py
    assured_destruction = False  # Fire Dragons' own ability: in YOUR Shooting phase, a ranged attack against a MONSTER or VEHICLE unit may re-roll its Hit roll, its Wound roll and its Damage roll - see game/assured_destruction.py
    aspect_shrine = False  # ASPECT WARRIORS wargear: this unit may take 1 Aspect Shrine token per 5 models, each of which can once per battle change one Hit or Wound roll made for a non-CHARACTER model in it to an unmodified 6 - see game/aspect_shrine.py
    bladestorm = False  # Dire Avengers' own ability: this unit's ranged weapons have [SUSTAINED HITS 1] while targeting an enemy unit within half range - see game/bladestorm.py
    invulnerable_save_vs_melee = None  # a BETTER invulnerable save that applies only against melee attacks, e.g. Howling Banshees' printed "5+, improved to 4+ against melee attacks". None = no such clause, the plain invulnerable_save applies to everything. Read by game/invulnerable_save.py, which gets the attack type from the weapon the Save roll is being made against
    mandiblasters = False   # Striking Scorpions' own ability: after this unit made a Charge move this turn, its melee attacks score a Critical Hit on an unmodified 5+ - see game/crit_hit.py
    serpent_shield = False  # Serpent's Scale Platform's wargear: every model in the BEARER'S UNIT gets a 5+ invulnerable save - read live (so it ends with the bearer) by game/invulnerable_save.py
    crewed_platform = False  # marks a model that is a crew-served platform: when its unit runs out of surviving `platform_crew` models, every model with this flag in that unit is destroyed too (Guardian Defenders' "Crewed Platform") - see game/crewed_platform.py
    platform_crew = False   # marks a model that COUNTS as crew for the above. Two flags rather than "anything that is not a platform", because the rule names the crew model specifically: a CHARACTER attached under 19.01 is neither, so it cannot keep an abandoned platform alive
    battle_focus = False  # Aeldari (ASURYANI) army rule "Battle Focus" - user-supplied, not a core rulebook rule. Carries no effect of its own: it marks the unit as eligible to perform an Agile Manoeuvre, and it is also what game/battle_focus.py's qualifying_players() reads to decide whose army counts as ASURYANI (this engine has no army-faction declaration). Human-only faction, so no AI path reads it
    markerlight = False  # the MARKERLIGHT keyword - see game/greater_good.py's marked_by_markerlight()
    battlesuit = False  # the BATTLESUIT keyword - matters for the Retaliation Cadre detachment's Bonded Heroes rule, see game/retaliation_cadre.py
    starflare_ignition_system = False  # the "Starflare Ignition System" Enhancement (user-supplied, 20 pts) is on THIS model - see game/starflare_ignition.py. Per-model rather than per-unit because an Enhancement is given to one model (game/factions/detachment.py's Enhancement docstring: granting one means setting the matching field on that model's own UnitProfile instance, which build_squad() creates fresh per model), even though its EFFECT is on the bearer's whole unit
    orks = False  # this model is an Orks-Faction model - matters for the War Horde detachment's Get Stuck In rule, see game/war_horde.py. No generic per-model Faction tracking exists in this engine (same documented gap as Bonded Heroes' own "is this T'au Empire" note in game/retaliation_cadre.py); unlike `battlesuit` there's no existing keyword this could piggyback on, so it's its own dedicated flag
    gretchin = False  # the GRETCHIN keyword - matters for the Runtherd ability's "if it contains one or more Gretchin models" check, see UnitProfile.runtherd_shares_gretchin_toughness/squad.py's attached_unit_toughness()
    runtherd_shares_gretchin_toughness = False  # Gretchin datasheet's own "Runtherd" ability (user-supplied, not a core rule, confusingly named the same as the model line it affects): while its unit contains 1+ living Gretchin models, this model's own Toughness counts as 2 for wound-roll purposes - see squad.py's attached_unit_toughness()
    thievin_scavengers = False  # Gretchin datasheet's own "Thievin' Scavengers" ability (user-supplied, not a core rule): at the start of your Movement phase, roll 1D6 per objective you control with a qualifying unit in range, gain 1CP if any roll is 4+ - see game/thievin_scavengers.py. User: "diese Ability wird noch öfters kommen" - a shared flag (same reuse pattern as `fieldcraft`), not Gretchin-exclusive
    explosives = False  # the EXPLOSIVES keyword - matters for the Explosives stratagem (15.05)
    grenades = False  # the GRENADES keyword - same as explosives for 15.05's "EXPLOSIVES/GRENADES" target
    deadly_demise = None  # Deadly Demise X value (rule 24.08), None = no ability
    deadly_demise_notation = None  # game/dice_notation.py's DiceNotation, e.g. D3() for a printed "Deadly Demise D3" - None means `deadly_demise` above is a real fixed X, used as-is; when set, `deadly_demise` is just a documentation leftover and the actual mortal-wound count is rolled for real by game/deadly_demise.py's DeadlyDemiseController once the D6 detonation roll succeeds
    feel_no_pain = "-"  # Feel No Pain X+ threshold (rule 24.12), "-" = no ability, same convention as invulnerable_save
    fights_first = False  # the Fights First core ability (rule 24.13) - permanent, datasheet-granted (see squad_has_fights_first(); distinct from Squad.fights_first, rule 11.04's temporary post-charge grant)
    transport = False  # the TRANSPORT keyword - rule 18.01, matters together with transport_capacity
    transport_capacity = 0  # rule 18.01: max total models that can embark within this model, if it's a TRANSPORT
    transport_requires_infantry = False  # rule 18.02 "eligible to embark... as described on that TRANSPORT's datasheet": this TRANSPORT only accepts INFANTRY units - e.g. Devilfish's "T'AU EMPIRE INFANTRY models" (the "T'au Empire" half of that isn't modeled - no per-model faction tracking exists in this engine, see TransportController.can_embark()'s own note)
    transport_requires = ()  # rule 18.02, the INCLUSIVE counterpart of transport_excludes below: tuple of UnitProfile boolean-attribute names EVERY model must have to embark - e.g. ("beast_snagga",) for Kill Rig's "11 BEAST SNAGGA INFANTRY models" (the INFANTRY half is transport_requires_infantry, so the two compose). Empty means no such restriction
    transport_excludes = ()  # rule 18.02: tuple of UnitProfile boolean-attribute names this TRANSPORT refuses to carry (e.g. ("battlesuit", "kroot", "vespid_stingwings") for Devilfish) - empty means no restriction, i.e. the old "any non-TRANSPORT unit is eligible" default
    firing_deck = 0  # Firing Deck X value (rule 24.14) - max embarked models that can lend the TRANSPORT a weapon each time it shoots, 0 = no ability
    rapid_deployment = False  # Devilfish's "Rapid Deployment" ability (user-supplied, not a core rule): units may Disembark from this TRANSPORT even after it Advanced (normally forbidden) - see TransportController.can_disembark()/determine_mode()
    leader = False  # the Leader core ability (24.22) - forms an attached unit with a bodyguard unit (rule 19.01)
    support = False  # the Support core ability (24.34) - same as leader, some units have this instead
    suppression_volley = False  # Strike Team's "Suppression Volley" ability (user-supplied, not a core rule) - see game/suppression.py
    support_turret_bearer = False  # "DS8 Support Turret" ability (user-supplied, shared by Strike Team and Breacher Team): this specific model can be equipped with the support turret weapon - see game/support_turret.py
    squad_leader = False  # purely cosmetic marker (no rule attaches): this ModelLine is the datasheet's own sergeant/leader model (Shas'ui, Shas'vre, Long-quill...) within an otherwise-uniform squad - NOT the same concept as `leader` above (rule 24.22, Attached Units' "leads a separate bodyguard unit"). Lets the renderer always tint/label it distinctly even when its weapon loadout happens to be identical to the rank-and-file (see Squad.unusual_loadout_models(), which only catches a loadout difference like Kroot's Long-quill, not a same-loadout sergeant like Strike/Breacher Team's Shas'ui)
    breach_and_clear = False  # Breacher Team's "Breach and Clear" ability (user-supplied, not a core rule) - see game/shooting.py's _wound_reroll_reason()
    guardian_drone = False  # the Guardian Drone wargear item (user-supplied, not a core rule): this model's UNIT gets -1 to the Wound roll against ranged attacks that target it - see game/drones.py, game/shooting.py's _wound_modifiers()
    fieldcraft = False  # sticky-objective ability (user-supplied, not a core rule) - see game/fieldcraft.py. Named after Kroot Carnivores' "Fieldcraft", the first datasheet to have it, but the rule text is generic ("if this unit is within range of an objective marker you control...") and reused as-is by other datasheets that print the identical ability under a different flavor name, e.g. Boyz's "Get Da Good Bitz"
    forward_observers = False  # Stealth Battlesuits' "Forward Observers" ability (user-supplied, not a core rule) - see game/greater_good.py's has_forward_observers()
    homing_beacon = False  # the Homing Beacon wargear item (user-supplied, not a core rule): once per battle, a free (0CP) Rapid Ingress with its own placement rule - see game/homing_beacon.py
    starscythe = False  # Crisis Starscythe Battlesuits' "Starscythe" ability (user-supplied, not a core rule): improves the AP of this model's ranged attacks (excluding MONSTER/VEHICLE targets) - see game/starscythe.py
    battlesuit_support_system = False  # Crisis Starscythe Battlesuits' "Battlesuit Support System" ability (user-supplied, not a core rule): this unit remains eligible to shoot after Falling Back - see squad_has_battlesuit_support_system()
    damaged_threshold = None  # Ghostkeel Battlesuit's own "Damaged: 1-4 Wounds Remaining" ability (user-supplied, not a core rule): while this model's own current_wounds is at or below this value, -1 to its own Hit rolls - None = no such tier, see game/shooting.py's _damaged_modifier()
    stealth_drones = 0  # Ghostkeel Battlesuit's own "Stealth Drones" ability (user-supplied, not a core rule): max uses per BATTLE of "change an allocated attack's Damage to 0" - 0 = no ability, see game/stealth_drones.py
    weapon_support_system = False  # Riptide Battlesuit's own "Weapon Support System" wargear ability (user-supplied, not a core rule): "each time the bearer makes a ranged attack, you can ignore any or all modifiers to the Hit roll" - identical wording, and identical handling, to rule 24.29's [PSYCHIC] half; see game/shooting.py's _hit_modifiers()
    ignores_cover = False  # a UNIT-level "Ignores Cover" rule (The Twin Lance): every attack this unit makes ignores the Benefit of Cover (13.08), regardless of the weapon's own [IGNORES COVER] keyword (24.18) - see game/shooting.py's _cover_ignored_for_group()
    exemplars_of_montka = False  # The Twin Lance's own "Exemplars of Mont'ka" ability (user-supplied, not a core rule): ranged attacks against the CLOSEST eligible target get [SUSTAINED HITS 1] and [IGNORES COVER] - see game/exemplars_of_montka.py
    neocapacitor_shields = False  # The Twin Lance's own "Neocapacitor Shields" ability (user-supplied): at the start of the opponent's Charge phase, one enemy unit within 12" takes a Battle-shock test and suffers -1 to its Charge rolls that turn - see game/neocapacitor_shields.py
    retro_thrusters = False  # The Twin Lance's own "Retro-thrusters" ability (user-supplied): a 6" Normal move or a Fall Back move at the END of the Fight phase - see game/retro_thrusters.py
    way_of_the_short_blade = False  # Commander Farsight's own "Way of the Short Blade" ability (user-supplied, not a core rule): while LEADING a unit, that unit's attacks against an enemy unit within 9" get +1 to the Wound roll - see game/way_of_the_short_blade.py
    puretide_teachings = False  # Commander Farsight's own "Puretide's Teachings" ability (user-supplied): once per battle round, a Stratagem targeting this model's unit costs 1CP less - see game/puretide.py
    sunforge = False  # Crisis Sunforge Battlesuits' own "Sunforge" ability (user-supplied, not a core rule): ranged attacks against a MONSTER or VEHICLE unit may re-roll both the Wound roll and the Damage roll - see game/sunforge.py
    target_uploaded = False  # Pathfinder Team's own "Target Uploaded" ability (user-supplied, not a core rule): attacks against a unit THIS unit Spotted get +1 BS and [IGNORES COVER] - see game/target_uploaded.py
    pulse_accelerator_drone = False  # Pulse Accelerator Drone wargear (user-supplied): "+6\" to the Range characteristic of pulse carbines equipped by models in the bearer's unit" - a UNIT-wide effect granted by one model's drone, see game/drones.py / game/pulse_accelerator.py
    recon_drone = False  # Recon Drone wargear (user-supplied): the bearer carries a Drone burst cannon and "the bearer's UNIT has the Infiltrators ability" - a UNIT-level grant, which is why it is its own flag instead of just setting `infiltrators` on the bearer (rule 24.20 only applies "if every model in a unit has this ability", so one flagged model would grant nothing) - see squad_has_infiltrators()
    grav_inhibitor_drone = False  # Grav-inhibitor Drone wargear (user-supplied): enemy units charging the bearer's unit take -2 on the Charge roll - see game/drones.py / game/grav_inhibitor_drone.py
    nova_charge = 0  # Riptide Battlesuit's own "Nova Charge" ability (user-supplied, not a core rule): max uses per BATTLE of "grant one of this model's ranged weapons [DEVASTATING WOUNDS] until the end of the phase" - 0 = no ability, see game/nova_charge.py
    drive_by_dakka = False  # Warbikers' "Drive-by Dakka" ability (user-supplied, not a core rule): improves the AP of this model's ranged attacks that target a unit within 9" - see game/drive_by_dakka.py
    full_throttle = False  # Stormboyz' "Full Throttle" ability (user-supplied, not a core rule): this unit remains eligible to declare a charge in a turn it Advanced or Fell Back - see squad_has_full_throttle(), game/charge.py's can_declare_charge()
    grot_riggers = False  # Trukk's "Grot Riggers" ability (user-supplied, not a core rule): at the start of its controller's Command phase, this model regains 1 lost wound - see game/grot_riggers.py
    waaagh = False  # Orks army rule "Waaagh!" (user-supplied, not a core rule): while active for this model's owner, it can charge after Advancing, its melee weapons get +1 S/+1 A, and it has (at least) a 5+ invulnerable save - see game/waaagh.py
    waaagh_biggest_and_best = False  # Warboss's own "Da Biggest and da Best" ability (user-supplied, not a core rule): while the Waaagh! is active for this model's owner, add 4 (on top of the army-wide +1 every `waaagh` model already gets) to the Attacks characteristic of this model's melee weapons - see game/waaagh.py's waaagh_extra_attacks()
    krumpin_time = False  # Meganobz's own "Krumpin' Time" ability (user-supplied, not a core rule): while the Waaagh! is active for this model's owner, this model has the Feel No Pain 5+ ability - see game/waaagh.py's effective_feel_no_pain() (that function's own note covers which damage sources this reaches and which it doesn't)
    bodyguard_two_leaders = False  # Boyz'/Kroot Carnivores' own "Bodyguard" ability (user-supplied datasheet text): if THIS unit has a Starting Strength of 20, up to TWO Leader units may be attached to it instead of one, provided one of them is a WARBOSS model - rule 19.01's own "unless otherwise stated" escape hatch. Read by game/attached_units.py's can_attach()
    joins_warlock_led_unit = False  # Eldrad Ulthran's own LEADER line: he may be attached to a unit even if one WARLOCKS unit is already attached to it. The MIRROR of bodyguard_two_leaders above - that one is printed on the bodyguard and asks what is arriving, this one is printed on the arriving leader and asks what is already there. Read by game/attached_units.py's can_attach(); it is what finally makes game/protect.py reachable
    doks_toolz = False  # Painboy's own "Dok's Toolz" ability (user-supplied, not a core rule): while this model is LEADING a unit (19.01), models in that unit have the Feel No Pain 5+ ability - see game/doks_toolz.py, read through game/feel_no_pain.py's current_feel_no_pain()
    waaagh_dead_brutal_damage = None  # Warboss in Mega Armour's own "Dead Brutal" ability (user-supplied, not a core rule): while the Waaagh! is active for this model's owner, this model's melee weapon has a Damage characteristic of this value (an absolute override, not a bonus) - None = no such override; see game/waaagh.py's waaagh_melee_adjusted_weapon()
    tank_hunters = False  # Tankbustas' own "Tank Hunters" ability (user-supplied, not a core rule): each time a model with this ability makes an attack (ranged or melee) that targets a MONSTER or VEHICLE unit, add 1 to the Hit roll and add 1 to the Wound roll - see game/shooting.py's/game/fight.py's own _hit_modifiers()/_wound_modifiers()
    ramshackle_but_rugged = False  # Battlewagon's own "Ramshackle but Rugged" ability (user-supplied, not a core rule): each time an attack is allocated to this model, worsen that attack's Armour Penetration by 1 - see game/ramshackle.py
    gun_crazy_showoffs = False  # Flash Gitz' own "Gun-crazy Show-offs" ability (user-supplied, not a core rule): a Snazzgun targeting the closest eligible target has an Attacks characteristic of 4 - see game/gun_crazy_showoffs.py
    psyker = False  # the PSYKER keyword - purely descriptive here (no engine rule reads it yet), same status as MOUNTED/SMOKE; the [PSYCHIC] weapon keyword (24.29) is a separate, wired thing on WeaponProfile
    beast_snagga = False  # the BEAST SNAGGA keyword - matters for Kill Rig's transport_requires ("11 BEAST SNAGGA INFANTRY models"), see UnitProfile.transport_requires
    spirit_of_gork = False  # Kill Rig's own "Spirit of Gork (Psychic)" ability (user-supplied, not a core rule): at the start of the Fight phase, buff one friendly ORKS unit within 12" - see game/spirit_of_gork.py
    ferocious_rage = False  # Beastboss's own "Ferocious Rage" ability (user-supplied, not a core rule): each time this model makes a Charge move, until the end of the turn, melee weapons it is equipped with have [DEVASTATING WOUNDS] - per MODEL, not per unit, which matters once it is leading one (19.01); see game/ferocious_rage.py
    monster_hunters = False  # Beast Snagga Boyz' own "Monster Hunters" ability (user-supplied, not a core rule): each time a model with this ability makes an attack (ranged or melee) that targets a MONSTER or VEHICLE unit, you can re-roll the Hit roll - same target test as `tank_hunters` above, but a re-roll rather than a modifier, so it hooks the hit-roll STEP instead of _hit_modifiers(); see game/monster_hunters.py
    mega_armour = False  # the MEGA ARMOUR keyword - matters for a TRANSPORT's capacity math ("each MEGA ARMOUR model takes up the space of 2 models", rule 18.01/Trukk's own printed exception) - see game/transport.py's _model_capacity_cost()
    coldstar_commander = False  # Commander in Coldstar Battlesuit's own "Coldstar Commander" ability (user-supplied, not a core rule): while this model is LEADING a unit (19.01), models in that unit have a Move characteristic of 12" and their ranged weapons have [ASSAULT] - a leader ability granted to the whole attached unit, so read with squad_has_coldstar_commander() rather than unit_wide_ability(); see game/coldstar.py
    might_is_right = False  # Warboss's own "Might is Right" ability (user-supplied, not a core rule): while this model is LEADING a unit (19.01), each time a model in that unit makes a melee attack, add 1 to the Hit roll - a leader ability granted to the whole attached unit, so read with squad_has_might_is_right() rather than unit_wide_ability(); see game/fight.py's _hit_modifiers()
    volley_fire = False  # Cadre Fireblade's own "Volley Fire" ability (user-supplied, not a core rule): while this model is LEADING a unit (19.01), add 1 to the Attacks characteristic of ranged weapons equipped by models in that unit - a leader ability granted to the whole attached unit, unlike every other flag here, so it is read with squad_has_volley_fire() rather than unit_wide_ability(); see game/volley_fire.py
    crack_shot = False  # Cadre Fireblade's own "Crack Shot" ability (user-supplied, not a core rule): each time this model makes a ranged attack, on a Critical Wound, that attack has an Armour Penetration characteristic of -3 (a flat override, not a modifier) - see game/crack_shot.py

    @property
    def can_move_through_dense_terrain(self):
        """Rule 13.06: INFANTRY/BEASTS/SWARM/MOBILE models can move
        horizontally through Dense terrain; every other model is blocked by
        it. Real datasheets without one of these keywords can still pass
        through sufficiently low sections of a Dense terrain feature - we
        don't model terrain height/verticality at all (a deliberate scope
        decision), so that branch is treated as never applying."""
        return self.infantry or self.beasts or self.swarm or self.mobile

    def stat_rows(self, current_wounds=None):
        wounds_display = f"{current_wounds}/{self.wounds}" if current_wounds is not None else str(self.wounds)
        return [
            ("M", f'{self.movement_in}"'),
            ("WS", self.weapon_skill),
            ("BS", self.ballistic_skill),
            ("T", str(self.toughness)),
            ("W", wounds_display),
            ("Ld", str(self.leadership)),
            ("Sv", self.armor_save),
            ("OC", str(self.oc)),
        ]


class InfantryProfile(UnitProfile):
    name = "Infantry"
    base_radius_in = 0.63  # 32mm base (Space Marine-style) - bigger than a Guardsman's 25mm (GuardProfile.base_radius_in)
    movement_in = 6
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 4
    wounds = 2
    leadership = "7+"
    armor_save = "3+"
    oc = 1
    infantry = True
    explosives = True  # so the Tactical Squad demo can test the Explosives stratagem (15.05)


class GuardProfile(UnitProfile):
    name = "Guard"
    base_radius_in = 0.5  # 25mm base - the UnitProfile default already matches this; kept explicit for clarity
    movement_in = 6
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 3
    wounds = 1
    leadership = "6+"
    armor_save = "5+"
    oc = 1
    infantry = True


class VehicleProfile(UnitProfile):
    name = "Vehicle"
    base_radius_in = 1.4  # generic vehicle-sized base (e.g. a Rhino's ~70mm width) - real vehicle bases are ovals, approximated here as a circle
    movement_in = 10
    weapon_skill = "-"
    ballistic_skill = "4+"
    toughness = 8
    wounds = 12
    leadership = "8+"
    armor_save = "2+"
    oc = 4
    vehicle = True
    transport = True  # so the demo Vehicle Squad can test Transports (18.01-18.05)
    transport_capacity = 6


class MonsterProfile(UnitProfile):
    name = "Monster"
    base_radius_in = 1.0  # generic monster-sized base (e.g. a 60mm base)
    movement_in = 8
    weapon_skill = "2+"
    ballistic_skill = "-"
    toughness = 7
    wounds = 8
    leadership = "9+"
    armor_save = "4+"
    oc = 4
    monster = True


class BoyzProfile(UnitProfile):
    """Datasheet: Boyz (Orks), see game/factions/orks.py. Keywords line
    (user-supplied): Battleline, Infantry, Mob, Grenades, Boyz - `grenades`
    is the GRENADES keyword (same target as `explosives` for rule 15.05's
    EXPLOSIVES/GRENADES check, see FireWarriorProfile's own note), not
    `explosives` - this datasheet's own printed keyword is Grenades, not
    Explosives."""
    name = "Boy"
    base_radius_in = 0.63  # 32mm base - user-confirmed official current size (was previously just assumed "same size class as InfantryProfile"; the math already matched exactly, so no value change, just upgraded from assumption to fact)
    movement_in = 6
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 5
    wounds = 1
    leadership = "7+"
    armor_save = "5+"
    oc = 2
    infantry = True
    grenades = True  # the GRENADES keyword - Boyz datasheet keyword
    fieldcraft = True  # "Get Da Good Bitz" - word-for-word the same sticky-objective rule as Kroot Carnivores' Fieldcraft, see UnitProfile's own note and game/fieldcraft.py
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)
    bodyguard_two_leaders = True  # this datasheet's own "Bodyguard" ability - see UnitProfile.bodyguard_two_leaders' own note and game/attached_units.py's can_attach()


class BossNobProfile(UnitProfile):
    """Datasheet: Boyz (Orks) - the Boss Nob is the squad's tougher leader
    model (2 wounds instead of 1), otherwise identical to a Boy."""
    name = "Boss Nob"
    base_radius_in = 0.63  # 32mm base - user-confirmed official current size, see BoyzProfile's own note
    movement_in = 6
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 5
    wounds = 2
    leadership = "7+"
    armor_save = "5+"
    oc = 2
    infantry = True
    grenades = True  # the GRENADES keyword - Boyz datasheet keyword
    fieldcraft = True  # "Get Da Good Bitz" - see BoyzProfile's own note
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)
    bodyguard_two_leaders = True  # this datasheet's own "Bodyguard" ability - see UnitProfile.bodyguard_two_leaders' own note and game/attached_units.py's can_attach()
    squad_leader = True  # cosmetic leader highlight, same convention as every other datasheet's sergeant/leader model (Shas'ui/Shas'vre/Long-quill...)


class WarbikerProfile(UnitProfile):
    """Datasheet: Warbikers (Orks), see game/factions/orks.py. Keywords line
    (user-supplied): Mounted, Grenades, Warbikers, Speed Freeks (Faction:
    Orks dropped, same reasoning as every other datasheet's Faction keyword
    - implicit in Faction registration). MOUNTED has no field of its own
    here - unlike Boyz, this datasheet's Keywords line does NOT include
    INFANTRY/BEASTS/SWARM/MOBILE, so (rule 13.06) it's actually blocked by
    Dense terrain like a normal non-infantry model, not a documented gap.
    base_radius_in: originally 1.18" from the user-supplied "60 mm bases" -
    user later asked for "die bases von den bikern etwas kleiner" (no exact
    figure given this time), so reduced to an assumed 50mm base instead:
    50mm/2 = 25mm = 25/25.4 ~= 0.98" (same mm-to-inch conversion used
    everywhere else in this file). Not an official size, just a reasonable
    "somewhat smaller" step down - flag if a specific mm figure is wanted."""
    name = "Warbiker"
    base_radius_in = 0.98
    movement_in = 12
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 6
    wounds = 3
    leadership = "7+"
    armor_save = "4+"
    invulnerable_save = "6+"  # "Invulnerable Save (6+) [Warbikers]"
    oc = 2
    grenades = True  # the GRENADES keyword
    drive_by_dakka = True  # this datasheet's own ability, see game/drive_by_dakka.py
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note; also inherited by BossNobOnWarbikeProfile below
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment); also inherited by BossNobOnWarbikeProfile below


class BossNobOnWarbikeProfile(WarbikerProfile):
    """Datasheet: Warbikers (Orks) - the Boss Nob on Warbike is the squad's
    tougher leader model (4 wounds instead of 3), otherwise identical to a
    Warbiker (same loadout, same base size)."""
    name = "Boss Nob on Warbike"
    wounds = 4
    squad_leader = True  # cosmetic leader highlight, same convention as every other datasheet's sergeant/leader model


class StormboyProfile(UnitProfile):
    """Datasheet: Stormboyz (Orks), see game/factions/orks.py. Keywords line
    (user-supplied): Infantry, Jump Pack, Fly, Grenades, Stormboyz (Faction:
    Orks dropped, same reasoning as every other datasheet's Faction
    keyword). JUMP PACK maps to `jump_pack` below - added later, when the
    Trukk datasheet's own "cannot transport JUMP PACK... models" exclusion
    needed a real attribute to check (see TrukkProfile's own note); FLY/
    DEEP STRIKE/GRENADES already mapped to a real field this engine already
    acts on. OC is 1 here, not Boyz' 2 - a real difference between the two
    Ork infantry datasheets, not an oversight.
    base_radius_in: user-supplied "base saize wie boyz" - same 0.63\" (32mm)
    as BoyzProfile."""
    name = "Stormboy"
    base_radius_in = 0.63  # 32mm base, same size class as Boyz (user-supplied: "base saize wie boyz")
    movement_in = 12
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 5
    wounds = 1
    leadership = "7+"
    armor_save = "5+"
    oc = 1
    infantry = True
    fly = True  # the FLY keyword, rule 21.03 (Take to the Skies)
    jump_pack = True  # the JUMP PACK keyword
    deep_strike = True  # "Rules: Deep Strike", rule 24.09
    grenades = True  # the GRENADES keyword
    full_throttle = True  # this datasheet's own ability, see squad_has_full_throttle()/game/charge.py
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note; also inherited by StormboyzBossNobProfile below
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment); also inherited by StormboyzBossNobProfile below


class StormboyzBossNobProfile(StormboyProfile):
    """Datasheet: Stormboyz (Orks) - the Boss Nob is the squad's tougher
    leader model (2 wounds instead of 1), otherwise identical to a
    Stormboy. Distinct class from Boyz's own BossNobProfile - same printed
    name, but a different M/OC (12"/1 here vs 6"/2 for Boyz), same reasoning
    as e.g. TauCloseCombatWeaponProfile needing its own class despite
    sharing a name with the generic CloseCombatWeaponProfile."""
    name = "Boss Nob"
    wounds = 2
    squad_leader = True  # cosmetic leader highlight, same convention as every other datasheet's sergeant/leader model


class TrukkProfile(UnitProfile):
    """Datasheet: Trukk (Orks), see game/factions/orks.py - a single-model
    TRANSPORT vehicle, like Devilfish. WS/BS aren't in the M/T/Sv/W/Ld/OC
    table (same 10th-edition convention as every other datasheet so far) -
    read off the weapon tables: Big shoota's own BS5+ matches this model's
    own BS, Spiked wheel's WS4+ matches this model's own WS.

    Keywords: Dedicated Transport, Vehicle, Transport, Trukk, Faction: Orks
    (Faction dropped, same reasoning as every other datasheet's Faction
    keyword). DEDICATED TRANSPORT isn't modeled - same already-documented
    gap as Devilfish's own (see DevilfishProfile's own note).

    Transport: "capacity of 12 ORKS INFANTRY models" - transport_requires_
    infantry covers the INFANTRY half only, same documented simplification
    as Devilfish (no per-model faction tracking in this engine, see
    TransportController.can_embark()'s own note). "cannot transport JUMP
    PACK... models" maps to transport_excludes=("jump_pack",) - Stormboyz
    is the first (and so far only) JUMP PACK datasheet, see its own note on
    why that field exists now. "...or GHAZGHKULL THRAKA models" is NOT
    modeled: that's a single named-CHARACTER exclusion, not a keyword one,
    and this engine has no generic named-unit exclusion system (nor does
    Ghazghkull Thraka exist as a datasheet here) - same kind of documented
    gap as the missing generic keyword/ability system noted throughout this
    file. "Each MEGA ARMOUR model takes up the space of 2 models" IS now
    modeled, since Meganobz (below) is the first MEGA ARMOUR datasheet -
    see game/transport.py's _model_capacity_cost(), read by both
    embarked_model_count() and can_embark()'s own capacity check.

    Rules: Deadly Demise D3 (deadly_demise_notation, a real D3 roll - see
    DevilfishProfile's own note), Firing Deck 12 (firing_deck - already
    fully generic, already-existing FiringDeckController; this is simply
    the first datasheet to actually set it to a nonzero value).

    base_radius_in: no exact mm given - user instruction: "mach die base
    size nicht so groß wie den devilfish sondern etwas kleiner" (Devilfish
    is 2.1", a deliberate 1.5x enlargement of VehicleProfile's own generic
    ~70mm-width assumption, see DevilfishProfile's own note). Using that
    same generic, un-enlarged 1.4" here - clearly smaller than the
    Devilfish's 2.1" as asked, without inventing a specific mm figure
    nothing in the user's message actually gave; revisit if a real base
    size is supplied later."""
    name = "Trukk"
    base_radius_in = 1.4
    movement_in = 12
    weapon_skill = "4+"
    ballistic_skill = "5+"
    toughness = 8
    wounds = 10
    leadership = "7+"
    armor_save = "4+"
    invulnerable_save = "6+"  # "Invulnerable Save (6+)"
    oc = 2
    vehicle = True
    deadly_demise = 3  # documentation leftover only, see deadly_demise_notation below - same convention as DevilfishProfile
    deadly_demise_notation = D3()  # "Deadly Demise D3"
    transport = True
    transport_capacity = 12
    transport_requires_infantry = True  # "transport capacity of 12 ORKS INFANTRY models" - the INFANTRY half, see class docstring
    transport_excludes = ("jump_pack",)  # "cannot transport JUMP PACK ... models" (GHAZGHKULL THRAKA exclusion not modeled, see class docstring)
    firing_deck = 12  # "Firing Deck 12"
    grot_riggers = True  # this datasheet's own ability, see game/grot_riggers.py
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note (user: "ALLE bisher angelegten Ork einheiten haben die Waaagh! ability")
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class GretchinProfile(UnitProfile):
    """Datasheet: Gretchin (Orks), see game/factions/orks.py. Keywords line
    (user-supplied): Infantry, Gretchin, Grots (Faction: Orks dropped, same
    reasoning as every other datasheet's Faction keyword) - applies to the
    whole unit, Runtherd included (see RuntherdProfile below), same
    convention as Boyz' Boss Nob carrying the BOYZ keyword. GROTS has no
    field of its own - purely descriptive, like Warbikers' MOUNTED. Rules:
    Waaagh! - see UnitProfile.waaagh's own note.
    `gretchin` is set ONLY here, not on RuntherdProfile - it's the engine's
    proxy for "a real rank-and-file Gretchin model", read by the Runtherd
    ability's "if it contains one or more Gretchin models" check (see
    RuntherdProfile.runtherd_shares_gretchin_toughness's own note); the
    printed GRETCHIN keyword itself is purely descriptive text on both
    model lines, a separate, inconsequential thing from this proxy flag.
    base_radius_in: not given by the user this time - assumed 0.5" (25mm,
    UnitProfile's own untouched default), matching a real Gretchin's
    actual small base size; purely cosmetic, no rules citation."""
    name = "Gretchin"
    movement_in = 6
    weapon_skill = "5+"
    ballistic_skill = "4+"
    toughness = 2
    wounds = 1
    leadership = "8+"
    armor_save = "7+"
    oc = 2
    infantry = True
    gretchin = True  # see this class's own docstring for why only here, not RuntherdProfile
    waaagh = True  # "Rules: Waaagh!"
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)
    thievin_scavengers = True  # this datasheet's own ability, see game/thievin_scavengers.py


class RuntherdProfile(UnitProfile):
    """Datasheet: Gretchin (Orks) - the Runtherd is the squad's tougher
    leader model, distinct stat line from Gretchin (unlike e.g. Boyz' Boss
    Nob, which only differs in wounds).
    base_radius_in: not given by the user this time - assumed 0.63" (32mm,
    same size class as BoyzProfile), matching a normal Ork-sized model;
    purely cosmetic, no rules citation."""
    name = "Runtherd"
    base_radius_in = 0.63
    movement_in = 6
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 5
    wounds = 2
    leadership = "7+"
    armor_save = "5+"
    oc = 1
    infantry = True
    waaagh = True  # "Rules: Waaagh!"
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)
    thievin_scavengers = True  # this datasheet's own ability, see game/thievin_scavengers.py
    runtherd_shares_gretchin_toughness = True  # this datasheet's own "Runtherd" ability - see UnitProfile's own note and squad.py's attached_unit_toughness()
    squad_leader = True  # cosmetic leader highlight, same convention as every other datasheet's sergeant/leader model


class WarbossProfile(UnitProfile):
    """Datasheet: Warboss (Orks), see game/factions/orks.py. Keywords line
    (user-supplied): Character, Warboss, Infantry, Grenades (Faction: Orks
    dropped, same reasoning as every other datasheet's Faction keyword -
    implicit in Faction registration). Standalone single-model Leader
    datasheet, unlike every other Ork UnitProfile so far, which is a
    ModelLine within a squad-sized datasheet.
    base_radius_in: user-supplied "Base 50 mm" - 50mm/2 = 25mm radius =
    25/25.4 ~= 0.98" (same mm-to-inch conversion used everywhere else in
    this file; also the same value Warbikers already use for their own
    assumed 50mm base, see WarbikerProfile's own note)."""
    name = "Warboss"
    base_radius_in = 0.98
    movement_in = 6
    weapon_skill = "2+"
    ballistic_skill = "5+"
    toughness = 5
    wounds = 6
    leadership = "6+"
    armor_save = "4+"
    invulnerable_save = "5+"  # "Invulnerable Save (5+)" - this model's own printed defensive rule, not the Waaagh!-granted one (they just happen to coincide numerically)
    oc = 1
    character = True
    infantry = True  # the INFANTRY keyword - Warboss datasheet keyword
    grenades = True  # the GRENADES keyword - Warboss datasheet keyword
    leader = True  # the Leader core ability (24.22) - "can be attached to Boyz/Nobz", enforced by game/attached_units.py's can_attach()
    might_is_right = True  # this datasheet's own "Might is Right" ability - see UnitProfile.might_is_right's own note and game/fight.py's _hit_modifiers()
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    waaagh_biggest_and_best = True  # this datasheet's own "Da Biggest and da Best" ability - see UnitProfile.waaagh_biggest_and_best's own note and game/waaagh.py
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class MeganobzProfile(UnitProfile):
    """Datasheet: Meganobz (Orks), see game/factions/orks.py. Keywords line
    (user-supplied): Infantry, Grenades, Meganobz, Mega Armour (Faction:
    Orks dropped, same reasoning as every other datasheet's Faction
    keyword). MEGA ARMOUR maps to the new `mega_armour` flag - the first
    datasheet to set it, which is what makes Trukk's own "each MEGA ARMOUR
    model takes up the space of 2 models" capacity rule reachable for the
    first time (see game/transport.py's _model_capacity_cost()).
    base_radius_in: user-supplied "Base 40 mm" - 40mm/2 = 20mm radius =
    20/25.4 ~= 0.79" (same mm-to-inch conversion used everywhere else in
    this file). WS/BS aren't in the M/T/Sv/W/Ld/OC table (same convention
    as every other datasheet so far) - read off the weapon tables: Kustom
    shoota's own BS5+ and Power klaw's own WS4+ both match this model's own
    values, so neither weapon needs a per-weapon override."""
    name = "Meganob"
    base_radius_in = 0.79
    movement_in = 5
    weapon_skill = "4+"
    ballistic_skill = "5+"
    toughness = 6
    wounds = 3
    leadership = "7+"
    armor_save = "2+"
    oc = 1
    infantry = True  # the INFANTRY keyword - Meganobz datasheet keyword
    grenades = True  # the GRENADES keyword - Meganobz datasheet keyword
    mega_armour = True  # the MEGA ARMOUR keyword - see UnitProfile.mega_armour's own note
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    krumpin_time = True  # this datasheet's own "Krumpin' Time" ability - see UnitProfile.krumpin_time's own note and game/waaagh.py's effective_feel_no_pain()
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class WarbossMegaArmourProfile(UnitProfile):
    """Datasheet: Warboss in Mega Armour (Orks), see game/factions/orks.py.
    Keywords line (user-supplied): Character, Infantry, Warboss in Mega
    Armour, Mega Armour, Warboss (Faction: Orks dropped, same reasoning as
    every other datasheet's Faction keyword). Standalone single-model
    Leader datasheet, like the plain WarbossProfile above - but NO Grenades
    keyword this time (unlike the plain Warboss, whose own Keywords line
    does include it - not an oversight, just a real difference between the
    two printed datasheets).
    base_radius_in: no "Base" line was ever given for this datasheet. It
    started as an assumed 0.79" (40mm), reasoned from MeganobzProfile since
    this is also a MEGA ARMOUR model - which the user then corrected on
    sight ("der Warboss in Megaarmor ist zu klein. der hat eine groessere
    Warboss base"), i.e. it takes the WARBOSS base, not the Meganob one.
    So 0.98" - WarbossProfile's own user-supplied "Base 50 mm" (50mm/2 =
    25mm radius = 25/25.4"), the same conversion every other base_radius_in
    in this file uses. WS/BS aren't in the M/T/Sv/W/Ld/OC table (same
    convention as every other datasheet so far) - read off the weapon
    tables: Big shoota's own BS4+ and 'Uge choppa's own WS2+ both match this
    model's own values, so neither weapon needs a per-weapon override."""
    name = "Warboss in Mega Armour"
    base_radius_in = 0.98  # 50mm base, same as WarbossProfile - see the docstring above
    movement_in = 5
    weapon_skill = "2+"
    ballistic_skill = "4+"
    toughness = 6
    wounds = 7
    leadership = "6+"
    armor_save = "2+"
    invulnerable_save = "5+"  # "Invulnerable Save (5+)" - this model's own printed defensive rule, not the Waaagh!-granted one (they just happen to coincide numerically, same note as WarbossProfile's own)
    oc = 1
    character = True
    infantry = True  # the INFANTRY keyword - this datasheet's own keyword
    mega_armour = True  # the MEGA ARMOUR keyword - see UnitProfile.mega_armour's own note
    leader = True  # the Leader core ability (24.22) - "can be attached to Meganobz", enforced by game/attached_units.py's can_attach()
    might_is_right = True  # this datasheet's own "Might is Right" ability, identical text to the plain Warboss's - see game/fight.py's _hit_modifiers()
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    waaagh_dead_brutal_damage = 3  # this datasheet's own "Dead Brutal" ability - see UnitProfile.waaagh_dead_brutal_damage's own note and game/waaagh.py's waaagh_melee_adjusted_weapon()
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class TankbustaProfile(UnitProfile):
    """Datasheet: Tankbustas (Orks), see game/factions/orks.py. Keywords
    line (user-supplied): Infantry, Tankbustas, Grenades (Faction: Orks
    dropped, same reasoning as every other datasheet's Faction keyword). A
    single stat table ("Tankbusta (x6)") covers the WHOLE unit including
    its own Boss Nob - unlike Boyz/Stormboyz/Warbikers, where the leader
    model has different wounds, Tankbustas' Boss Nob shares this exact
    stat line (only its own weapon loadout differs), same "identical stats,
    just squad_leader=True" relationship as T'au's own FireWarriorShasUiProfile
    to FireWarriorProfile - see TankbustaBossNobProfile below.
    base_radius_in: user-supplied "Base 32 mm" - 32mm/2 = 16mm radius =
    16/25.4 ~= 0.63" (same mm-to-inch conversion used everywhere else in
    this file; also the same value BoyzProfile already uses for its own
    32mm base). WS/BS aren't in the M/T/Sv/W/Ld/OC table (same convention
    as every other datasheet so far) - read off the weapon tables: Rokkit
    pistol's/Rokkit launcha's own BS5+ and Choppa's/Close combat weapon's
    own WS3+ all match this model's own values, so no weapon needs a
    per-weapon override."""
    name = "Tankbusta"
    base_radius_in = 0.63
    movement_in = 6
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 5
    wounds = 2
    leadership = "7+"
    armor_save = "4+"
    oc = 1
    infantry = True  # the INFANTRY keyword - Tankbustas datasheet keyword
    grenades = True  # the GRENADES keyword - Tankbustas datasheet keyword
    tank_hunters = True  # this datasheet's own "Tank Hunters" ability - see UnitProfile.tank_hunters's own note and game/squad.py's tank_hunters_modifiers()
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class TankbustaBossNobProfile(TankbustaProfile):
    """Datasheet: Tankbustas (Orks) - the Boss Nob shares TankbustaProfile's
    exact stat line (see that class's own docstring); only its weapon
    loadout differs (Choppa + 2x Rokkit pistol instead of Close combat
    weapon + Rokkit launcha)."""
    name = "Boss Nob"
    squad_leader = True  # cosmetic leader highlight, same convention as every other datasheet's sergeant/leader model


class DeffkoptaProfile(UnitProfile):
    """Datasheet: Deffkoptas (Orks), see game/factions/orks.py. Keywords
    line (user-supplied): Vehicle, Fly, Grenades, Deffkoptas, Speed Freeks
    (Faction: Orks dropped, same reasoning as every other datasheet's
    Faction keyword). A VEHICLE unit that comes in a multi-model squadron
    (3 identical Deffkopta models, no separate leader model this time,
    unlike Tankbustas/Boyz/etc.) - unusual for VEHICLE but real on this
    printed datasheet.
    base_radius_in: no "Base" line was given this time - user's own
    instruction: "wie warbikes" (same as Warbikers), so 0.98" (same assumed
    50mm value as WarbikerProfile - see that class's own note on how that
    number was reached). WS/BS aren't in the M/T/Sv/W/Ld/OC table (same
    convention as every other datasheet so far) - read off the weapon
    tables: Kopta rokkits'/Slugga's own BS5+ and Spinnin' blades' own WS3+
    both match this model's own values, so no weapon needs a per-weapon
    override."""
    name = "Deffkopta"
    base_radius_in = 0.98
    movement_in = 12
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 6
    wounds = 4
    leadership = "7+"
    armor_save = "4+"
    invulnerable_save = "6+"  # "Invulnerable Save (6+) [Deffkoptas]"
    oc = 2
    vehicle = True  # the VEHICLE keyword - Deffkoptas datasheet keyword
    fly = True  # the FLY keyword - Deffkoptas datasheet keyword
    grenades = True  # the GRENADES keyword - Deffkoptas datasheet keyword
    deep_strike = True  # "Rules: Deep Strike", rule 24.09
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class DeffDreadProfile(UnitProfile):
    """Datasheet: Deff Dread (Orks), see game/factions/orks.py. Keywords
    line (user-supplied): Vehicle, Walker, Deff Dread (Faction: Orks
    dropped, same reasoning as every other datasheet's Faction keyword).
    Single-model VEHICLE/WALKER, like a bigger cousin of Trukk - `walker`
    already exists as a UnitProfile flag (rule 15.11, Heroic Intervention
    eligibility for an otherwise-pure-VEHICLE unit), just not set by any
    datasheet until now.
    base_radius_in: user-supplied "base 60-mm" - 60mm/2 = 30mm radius =
    30/25.4 ~= 1.18" (same mm-to-inch conversion used everywhere else in
    this file; also the same value WarbikerProfile's own docstring
    computed for a 60mm base before it was revised down to an assumed
    50mm). WS/BS aren't in the M/T/Sv/W/Ld/OC table (same convention as
    every other datasheet so far) - read off the weapon tables: Big
    shoota's own BS5+ and Stompy feet's/Dread klaw's own WS3+ both match
    this model's own values, so no weapon needs a per-weapon override.

    Deadly Demise 1 (rule 24.08) needs no new code - `deadly_demise` is an
    existing generic UnitProfile field, already read by
    game/deadly_demise.py's DeadlyDemiseController; a plain fixed "1" (no
    `deadly_demise_notation`) is used as-is, same as any other non-dice-
    notation value."""
    name = "Deff Dread"
    base_radius_in = 1.18
    movement_in = 8
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 9
    wounds = 8
    leadership = "7+"
    armor_save = "2+"
    invulnerable_save = "6+"  # "Invulnerable Save (6+)"
    oc = 3
    vehicle = True  # the VEHICLE keyword - Deff Dread datasheet keyword
    walker = True  # the WALKER keyword - Deff Dread datasheet keyword
    deadly_demise = 1  # "Rules: Deadly Demise 1" - see this class's own note above
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class BeastSnaggaBoyProfile(UnitProfile):
    """Datasheet: Beast Snagga Boyz (Orks), see game/factions/orks.py.
    Keywords line (user-supplied): Battleline, Infantry, Mob, Beast Snagga,
    Beast Snagga Boyz (Faction: Orks dropped, same reasoning as every other
    datasheet's Faction keyword). Note what is NOT on that line: no
    GRENADES (unlike Boyz/Stormboyz/Warbikers/Tankbustas, so no `grenades`
    flag and rule 15.05's EXPLOSIVES/GRENADES stratagem is correctly out of
    reach), and no BEASTS - "Beast Snagga" is a faction keyword about
    hunting beasts, not the BEASTS keyword rule 13.06 reads for Dense
    terrain, so `beasts` stays False and only `infantry` grants that.

    The M/T/Sv/W/Ld/OC line is numerically identical to BoyzProfile's, but
    this is deliberately a separate class rather than a subclass: the two
    datasheets share no ability at all (this one has Feel No Pain 6+ and
    Monster Hunters where Boyz has Get Da Good Bitz/Fieldcraft), so the
    shared numbers are a coincidence of the stat line, not a relationship
    worth encoding.

    base_radius_in: 32mm base, same as every other Ork Boy-sized model here
    (32mm/2 = 16mm = 16/25.4 ~= 0.63"). WS/BS aren't in the M/T/Sv/W/Ld/OC
    table (same convention as every other datasheet) - read off the weapon
    tables: Slugga's/Thump gun's own BS5+ and Choppa's/Power snappa's/Close
    combat weapon's own WS3+ all match this model's own values, so no
    weapon needs a per-weapon override."""
    name = "Beast Snagga Boy"
    base_radius_in = 0.63
    movement_in = 6
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 5
    wounds = 1
    leadership = "7+"
    armor_save = "5+"
    oc = 2
    infantry = True  # the INFANTRY keyword - Beast Snagga Boyz datasheet keyword
    beast_snagga = True  # the BEAST SNAGGA keyword - what makes this unit eligible for a Kill Rig's transport, see UnitProfile.transport_requires
    feel_no_pain = "6+"  # "Rules: Feel No Pain 6+" - rule 24.12, an existing generic field, no new code needed
    monster_hunters = True  # this datasheet's own "Monster Hunters" ability - see UnitProfile.monster_hunters's own note and game/monster_hunters.py
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class BattlewagonProfile(UnitProfile):
    """Datasheet: Battlewagon (Orks), see game/factions/orks.py. Keywords
    line (user-supplied): Vehicle, Transport, Battlewagon (Faction: Orks
    dropped, same reasoning as every other datasheet's Faction keyword).

    base_radius_in: user-supplied "base size wie kill rig" - whatever
    KillRigProfile carries, currently 2.1" (it started at a 170x109mm oval's
    equal-area 2.68" and was then set to the Devilfish's size on user
    request; see that class's own note). Written out rather than read from
    KillRigProfile, matching how every other datasheet in this file states
    its own number - but the two are meant to stay equal, so change both.

    Its M/T/Sv/W/Ld/OC line is numerically identical to the Kill Rig's, which
    is a coincidence of the two stat blocks rather than a relationship - one
    is a MONSTER PSYKER with six weapons, the other a VEHICLE with one.

    WS/BS aren't in the M/T/Sv/W/Ld/OC table (same convention as every other
    datasheet). Its only DEFAULT weapon is Tracks and wheels at WS4+, so that
    is the model's own; the Unselected Profiles' Grabbin' klaw and Deff rolla
    print a better WS3+ and override themselves upward. BS5+ is read off the
    Unselected big shoota/lobba - no default ranged weapon exists to fix it
    otherwise, and 5+ is what every other Ork vehicle here carries."""
    name = "Battlewagon"
    base_radius_in = 2.1
    movement_in = 10
    weapon_skill = "4+"
    ballistic_skill = "5+"
    toughness = 10
    wounds = 16
    leadership = "7+"
    armor_save = "3+"
    invulnerable_save = "6+"  # "Invulnerable Save (6+)"
    oc = 5
    vehicle = True  # the VEHICLE keyword
    damaged_threshold = 5  # "Damaged: 1-5 Wounds Remaining" -> -1 to this model's own Hit rolls
    ramshackle_but_rugged = True  # this datasheet's own ability - see UnitProfile.ramshackle_but_rugged's own note and game/ramshackle.py
    deadly_demise = 6  # documentation leftover only, see deadly_demise_notation below
    deadly_demise_notation = D6()  # "Rules: Deadly Demise D6"
    firing_deck = 11  # "Rules: Firing Deck 11" - rule 24.14, an existing generic field (see game/firing_deck.py); the 'Ard Case wargear removes it, see game/factions/orks.py
    transport = True  # the TRANSPORT keyword
    transport_capacity = 22  # "a transport capacity of 22 ORKS INFANTRY models" - the Killkannon variant's reduced 12 is not modeled, see the datasheet's own note
    transport_requires_infantry = True  # the INFANTRY half of that line
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class FlashGitzProfile(UnitProfile):
    """Datasheet: Flash Gitz (Orks), see game/factions/orks.py. Keywords line
    (user-supplied): Infantry, Grenades, Flash Gitz (Faction: Orks dropped,
    same reasoning as every other datasheet's Faction keyword).

    base_radius_in: user-supplied "40 mm" - 40mm/2 = 20mm = 20/25.4 ~= 0.79".
    Bigger than the 32mm bases every other Ork Boy-sized model here uses, and
    the first 40mm base in this module.

    Both model lines share this exact stat line - the Kaptin differs only in
    being the squad's leader model (see FlashGitzKaptinProfile below), not
    even in wounds, the same relationship TankbustaBossNobProfile has to
    TankbustaProfile. WS/BS aren't in the M/T/Sv/W/Ld/OC table (same
    convention as every other datasheet) - read off the weapon tables:
    Snazzgun's BS5+ and Choppa's WS3+ both match this model's own values, so
    neither weapon needs a per-weapon override."""
    name = "Flash Git"
    base_radius_in = 0.79
    movement_in = 6
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 5
    wounds = 2
    leadership = "7+"
    armor_save = "4+"
    oc = 1
    infantry = True  # the INFANTRY keyword - Flash Gitz datasheet keyword
    grenades = True  # the GRENADES keyword - Flash Gitz datasheet keyword
    gun_crazy_showoffs = True  # this datasheet's own "Gun-crazy Show-offs" ability - see UnitProfile.gun_crazy_showoffs's own note and game/gun_crazy_showoffs.py
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class FlashGitzKaptinProfile(FlashGitzProfile):
    """Datasheet: Flash Gitz (Orks) - the Kaptin shares FlashGitzProfile's
    exact stat line AND its exact loadout (Choppa + Snazzgun); it is the
    squad's leader model and nothing else, so this subclass only sets the
    cosmetic highlight."""
    name = "Kaptin"
    squad_leader = True  # cosmetic leader highlight, same convention as every other datasheet's leader model


class PainboyProfile(UnitProfile):
    """Datasheet: Painboy (Orks), see game/factions/orks.py. Keywords line
    (user-supplied): Character, Infantry, Painboy (Faction: Orks dropped,
    same reasoning as every other datasheet's Faction keyword). A standalone
    single-model Leader datasheet, like both Warboss datasheets and the
    Beastboss.

    base_radius_in: NOT supplied by the user this time - assumed 0.63" (32mm,
    the size every Ork Boy-sized model in this module uses, and what a
    Character on foot of this size class takes). Flag if a specific mm figure
    is wanted; it is the same standing assumption GretchinProfile carries.

    WS/BS aren't in the M/T/Sv/W/Ld/OC table (same convention as every other
    datasheet) - read off the weapon tables, and here they agree with the
    project's usual reading: the 'Urty syringe prints WS3+ and the Power klaw
    WS4+, so 3+ is this model's own value and the klaw's 4+ is the genuine
    per-weapon override (PowerKlawProfile already carries it). BS is never
    read at all - this datasheet has no ranged weapon - so it keeps the
    UnitProfile default rather than inventing a number.

    On `leader` vs `support`: the datasheet text supplied for this unit is
    headed "Abilities (Leader)" and its ability is literally named "Leader",
    so this profile sets `leader`. NOTE that game/factions/orks_points.py's
    transcription of the official points list files this unit under SUPPORT
    instead (alongside Bannernob). The two differ in what rule 19.01 allows:
    as a Leader it cannot join a mob that already has a Warboss attached; as
    Support it could. game/attached_units.py's leadable_unit_names() handles
    the mismatch gracefully either way - with `leads` empty it falls back to
    the points entry's `supports` tuple, which is this datasheet's own list
    plus Breaka Boyz (a unit with no datasheet in this engine), so no legal
    pairing is lost and none that matters is gained."""
    name = "Painboy"
    base_radius_in = 0.63
    movement_in = 6
    weapon_skill = "3+"
    toughness = 5
    wounds = 3
    leadership = "7+"
    armor_save = "5+"
    oc = 1
    character = True  # the CHARACTER keyword
    infantry = True  # the INFANTRY keyword
    leader = True  # the Leader core ability (24.22) - see the docstring above on leader-vs-support, and game/attached_units.py's can_attach()
    doks_toolz = True  # this datasheet's own "Dok's Toolz" ability - see UnitProfile.doks_toolz's own note and game/doks_toolz.py
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class KillRigProfile(UnitProfile):
    """Datasheet: Kill Rig (Orks), see game/factions/orks.py. Keywords line
    (user-supplied): Monster, Transport, Psyker, Beast Snagga, Kill Rig
    (Faction: Orks dropped, same reasoning as every other datasheet's
    Faction keyword). The first MONSTER in this engine that is also a
    TRANSPORT, and the first PSYKER of either faction.

    base_radius_in: started at the user-supplied real base, "170 mm x 109" -
    an oval, converted to a circle of EQUAL AREA, the same conversion
    GhostkeelProfile's 105x70mm and RiptideProfile's 120x92mm ovals already
    use (a token here is always a circle, see VehicleProfile's own note):
    semi-axes 85mm and 54.5mm, so r = sqrt(85 * 54.5) = sqrt(4632.5)
    ~= 68.06mm = 68.06/25.4 ~= 2.68" (deliberately NOT the mean of the two
    semi-axes, 69.75mm = 2.75", which would overstate the footprint - see
    the Riptide's own note). The user then judged that too big on the board
    ("kill rig und battle wagon sind zu groß. bitte so groß machen wie
    devilfish") and asked for DevilfishProfile's own 2.1" instead, which is
    what this now carries - so it is a deliberate cosmetic choice, not the
    oval arithmetic. base_radius_in has no rules citation anywhere in this
    file (it is collision/rendering size only), so a size the user prefers
    beats a size derived from the real model. BattlewagonProfile follows
    this value, same as it followed the old one.

    WS/BS aren't in the M/T/Sv/W/Ld/OC table (same convention as every
    other datasheet) - read off the weapon tables. BS5+ is shared by 'Eavy
    lobba and Stikka kannon (the Wurrtower's printed "N/A" needs nothing:
    [TORRENT] auto-hits, rule 24.37). The melee weapons disagree - Butcha
    boyz and Saw blades are WS3+, Savage horns and hooves WS4+ - so the
    profile carries the majority 3+ and only that one weapon overrides,
    same handling as The Twin Lance's own three-way disagreement."""
    name = "Kill Rig"
    base_radius_in = 2.1
    movement_in = 10
    weapon_skill = "3+"
    ballistic_skill = "5+"
    toughness = 10
    wounds = 16
    leadership = "7+"
    armor_save = "3+"
    oc = 5
    monster = True  # the MONSTER keyword
    psyker = True  # the PSYKER keyword - descriptive, see UnitProfile.psyker's own note
    beast_snagga = True  # the BEAST SNAGGA keyword
    feel_no_pain = "6+"  # "Rules: Feel No Pain 6+" - rule 24.12, an existing generic field
    damaged_threshold = 5  # "Damaged: 1-5 Wounds Remaining" -> -1 to this model's own Hit rolls, an existing generic field (see game/shooting.py's _damaged_modifier())
    deadly_demise = 6  # documentation leftover only, see deadly_demise_notation below - same convention as Devilfish/Trukk
    deadly_demise_notation = D6()  # "Rules: Deadly Demise D6" - a real D6 roll, see game/deadly_demise.py
    transport = True  # the TRANSPORT keyword
    transport_capacity = 11  # "a transport capacity of 11 BEAST SNAGGA INFANTRY models"
    transport_requires_infantry = True  # the INFANTRY half of that line
    transport_requires = ("beast_snagga",)  # the BEAST SNAGGA half - see UnitProfile.transport_requires's own note
    spirit_of_gork = True  # this datasheet's own "Spirit of Gork (Psychic)" ability - see game/spirit_of_gork.py
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)


class BeastbossProfile(UnitProfile):
    """Datasheet: Beastboss (Orks), see game/factions/orks.py. Keywords line
    (user-supplied): Character, Infantry, Beast Snagga, Beastboss, Warboss
    (Faction: Orks dropped, same reasoning as every other datasheet's
    Faction keyword). A standalone single-model Leader datasheet, like both
    Warboss datasheets - and it shares the plain Warboss's exact
    M/T/Sv/W/Ld/OC line, which is a real coincidence of the stat block and
    not a relationship: it leads a different unit, has different weapons,
    and its own Ferocious Rage has no Warboss counterpart.

    base_radius_in: user-supplied "50 mm wie warboss" - 50mm/2 = 25mm =
    25/25.4 ~= 0.98", the same value WarbossProfile already carries.

    WS/BS aren't in the M/T/Sv/W/Ld/OC table (same convention as every other
    datasheet) - read off the weapon tables, and here they DISAGREE with
    each other: Beastchoppa is WS2+, Beast Snagga klaw WS3+, Shoota BS4+.
    With only two melee weapons there is no majority to follow (unlike The
    Twin Lance's three), so the profile carries the BETTER of the two (2+,
    matching both Warboss datasheets) and BeastSnaggaKlawProfile overrides
    itself down to 3+ - that way the override marks the weapon the datasheet
    actually prints as clumsier, rather than making the model look worse
    than it is everywhere the profile's own WS is read."""
    name = "Beastboss"
    base_radius_in = 0.98
    movement_in = 6
    weapon_skill = "2+"
    ballistic_skill = "4+"
    toughness = 5
    wounds = 6
    leadership = "6+"
    armor_save = "4+"
    invulnerable_save = "5+"  # "Invulnerable Save (5+)" - this model's own printed rule, distinct from (but numerically equal to) the conditional 5+ Waaagh! grants every `waaagh` model
    oc = 1
    character = True  # the CHARACTER keyword
    infantry = True  # the INFANTRY keyword
    beast_snagga = True  # the BEAST SNAGGA keyword - Beastboss datasheet keyword
    leader = True  # the Leader core ability (24.22) - "can be attached to Beast Snagga Boyz", enforced by game/attached_units.py's can_attach() against the pairing in the points list
    feel_no_pain = "6+"  # "Rules: Feel No Pain 6+" - rule 24.12, an existing generic field, no new code needed
    might_is_right = True  # this datasheet's "Beastboss" ability is word-for-word the Warbosses' own "Might is Right" (+1 to the Hit roll for melee attacks in the unit it leads), so it reuses that exact flag and game/squad.py's squad_has_might_is_right() - no new code
    ferocious_rage = True  # this datasheet's own "Ferocious Rage" ability - see UnitProfile.ferocious_rage's own note and game/ferocious_rage.py
    waaagh = True  # Orks army rule - see UnitProfile.waaagh's own note
    orks = True  # Orks Faction - see UnitProfile.orks' own note (War Horde detachment)
    squad_leader = True  # cosmetic leader highlight, same convention as both Warboss datasheets


class BeastSnaggaNobProfile(BeastSnaggaBoyProfile):
    """Datasheet: Beast Snagga Boyz (Orks) - the Beast Snagga Nob is the
    squad's tougher leader model (2 wounds instead of 1), otherwise sharing
    BeastSnaggaBoyProfile's exact stat line and abilities; only its weapon
    loadout differs (Power snappa instead of a Choppa). Subclassed here,
    unlike BeastSnaggaBoyProfile's own deliberate non-relationship to
    BoyzProfile above, because these two genuinely ARE the same datasheet's
    two model lines - same relationship as TankbustaBossNobProfile to
    TankbustaProfile."""
    name = "Beast Snagga Nob"
    wounds = 2
    squad_leader = True  # cosmetic leader highlight, same convention as every other datasheet's sergeant/leader model


class FireWarriorProfile(UnitProfile):
    """Datasheet: Strike Team (T'au Empire). The datasheet's own stat tables
    give identical M/T/Sv/W/Ld/OC for both the Fire Warrior Shas'ui and the
    9 rank-and-file Fire Warriors - only their wargear differs (see
    FireWarriorShasUiProfile). WS/BS aren't in that table (10th-edition
    datasheets print them per weapon instead, see UnitProfile's own
    docstring) - read off the weapon tables here: Pulse Pistol/Rifle's BS4+
    matches this model's own BS (no per-weapon override needed for those),
    Close Combat Weapon's WS5+ is this model's own WS. base_radius_in is an
    assumption (32mm, matching InfantryProfile's size class) - not given by
    the user, no rules citation, purely cosmetic (collision/rendering size)."""
    name = "Fire Warrior"
    base_radius_in = 0.63
    movement_in = 6
    weapon_skill = "5+"
    ballistic_skill = "4+"
    toughness = 3
    wounds = 1
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    infantry = True
    grenades = True  # the GRENADES keyword - user-confirmed as the same target as `explosives` for rule 15.05 (ExplosivesController._qualifying_models() already reads m.profile.explosives OR m.profile.grenades)
    markerlight = True
    for_the_greater_good = True
    suppression_volley = True  # this datasheet's own ability, see game/suppression.py


class FireWarriorShasUiProfile(FireWarriorProfile):
    """Same stat line as FireWarriorProfile - only this specific model can
    be equipped with the support turret weapon (DS8 Support Turret ability,
    see game/support_turret.py)."""
    name = "Fire Warrior Shas'ui"
    support_turret_bearer = True
    squad_leader = True


class BreacherFireWarriorProfile(UnitProfile):
    """Datasheet: Breacher Team (T'au Empire) - identical M/T/Sv/W/Ld/OC to
    Strike Team's FireWarriorProfile (both are Fire Warrior-type infantry),
    but its own datasheet/ability set. Pulse Pistol's BS4+ matches this
    model's own BS; the Pulse Blaster's BS3+ (BETTER than the model's own,
    unlike Support Turret's worse BS) needs the same per-weapon override -
    see WeaponProfile.ballistic_skill/effective_ballistic_skill()."""
    name = "Breacher Fire Warrior"
    base_radius_in = 0.63  # same assumption as FireWarriorProfile - not given by the user, purely cosmetic
    movement_in = 6
    weapon_skill = "5+"
    ballistic_skill = "4+"
    toughness = 3
    wounds = 1
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    infantry = True
    grenades = True
    markerlight = True
    for_the_greater_good = True
    breach_and_clear = True  # this datasheet's own ability, see game/shooting.py's _wound_reroll_reason()


class BreacherFireWarriorShasUiProfile(BreacherFireWarriorProfile):
    """Same stat line as BreacherFireWarriorProfile - only this specific
    model can be equipped with the support turret weapon (DS8 Support
    Turret ability, shared with Strike Team, see game/support_turret.py)."""
    name = "Breacher Fire Warrior Shas'ui"
    support_turret_bearer = True
    squad_leader = True


class KrootCarnivoreProfile(UnitProfile):
    """Datasheet: Kroot Carnivores (T'au Empire, a Kroot auxiliary unit -
    notably NOT granted For The Greater Good or MARKERLIGHT, unlike Strike
    Team/Breacher Team: neither appears in this datasheet's own Rules/
    Keywords text, matching real Kroot lore as T'au auxiliaries rather than
    "true" T'au). Only one "Kroot Carnivores" stat row is given for the
    whole unit (unlike Strike/Breacher Team's two, identical, rows), so it
    covers both the Long-quill and the 9 rank-and-file models."""
    name = "Kroot Carnivore"
    base_radius_in = 0.63  # same 32mm assumption as the Fire Warrior profiles - not given by the user, purely cosmetic
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "4+"
    toughness = 3
    wounds = 1
    leadership = "7+"
    armor_save = "6+"
    oc = 2
    infantry = True
    grenades = True
    kroot = True  # the KROOT keyword - matters for Devilfish's transport_excludes, see UnitProfile's own note
    stealth = True  # rule 24.33, already implemented - see squad_has_stealth()
    scouts = 7.0  # "Scouts 7\"" - stored, not yet consumed (see UnitProfile.scouts)
    fieldcraft = True  # this datasheet's own ability, see game/fieldcraft.py


class LongQuillProfile(KrootCarnivoreProfile):
    """The unit's Long-quill (leader model) - identical stat line, carries
    a Kroot pistol in addition to the rank-and-file's own loadout."""
    name = "Long-quill"
    squad_leader = True


class StealthShasUiProfile(UnitProfile):
    """Datasheet: Stealth Battlesuits (T'au Empire) - shared stat line for
    both the Stealth Shas'vre and the 4 rank-and-file Stealth Shas'ui (one
    stat row given for the whole unit, like Kroot Carnivores). Unlike Kroot,
    this datasheet DOES have For The Greater Good/MARKERLIGHT (both appear
    on its own Rules/Keywords text) - Stealth suits are "true" T'au, not
    auxiliaries."""
    name = "Stealth Shas'ui"
    base_radius_in = 0.8  # bigger than plain infantry (Battlesuit-class model) - not given by the user, purely cosmetic, matches VehicleProfile-style "larger than infantry" sizing intent
    movement_in = 8
    weapon_skill = "5+"
    ballistic_skill = "4+"
    toughness = 4
    wounds = 2
    leadership = "7+"
    armor_save = "3+"
    oc = 1
    infantry = True
    fly = True
    battlesuit = True  # first datasheet to actually carry this keyword - see Retaliation Cadre's Bonded Heroes, game/retaliation_cadre.py
    grenades = True
    markerlight = True
    for_the_greater_good = True
    stealth = True  # rule 24.33, already implemented
    infiltrators = True  # rule 24.20, already implemented (not wired into a live deployment flow yet, see squad_has_infiltrators())
    forward_observers = True  # this datasheet's own ability, see game/greater_good.py's has_forward_observers()


class StealthShasVreProfile(StealthShasUiProfile):
    """The unit's Shas'vre (leader model) - identical stat line, no extra
    baseline wargear beyond the same Battlesuit fists + Burst cannon every
    model in this unit carries."""
    name = "Stealth Shas'vre"
    squad_leader = True


class CrisisStarscytheShasUiProfile(UnitProfile):
    """Datasheet: Crisis Starscythe Battlesuits (T'au Empire) - identical
    M/T/Sv/W/Ld/OC for the Shas'vre and both rank-and-file Shas'ui (one stat
    row given for the whole unit, like Kroot Carnivores/Stealth
    Battlesuits). WS/BS aren't in that table (same 10th-edition convention
    as every other T'au datasheet so far) - read off the weapon tables:
    Battlesuit fists' WS5+ matches this model's own WS (no per-weapon WS
    override mechanism exists in this engine - fight.py always reads
    model.profile.weapon_skill directly, unlike shooting.py's
    effective_ballistic_skill() - so it only ever needs to line up, never
    override), Burst cannon's BS4+ matches this model's own BS (T'au
    flamer's own "N/A" needs no override either, since [TORRENT] skips the
    hit roll entirely - see _begin_resolution()'s torrent branch).

    Keywords (given separately, after the initial paste, as: Vehicle,
    Walker, Fly, Battlesuit, Crisis, Starscythe - Faction: T'au Empire is
    already implicit in which Faction this Datasheet is registered under,
    see game/factions/tau_empire.py): notably VEHICLE/WALKER, not INFANTRY -
    unlike every other T'au datasheet added so far, this unit does NOT move
    through Dense terrain for free (13.06's INFANTRY/BEASTS/SWARM/MOBILE
    check), and Rule 24.07's [CLOSE-QUARTERS] weapon-side lock doesn't apply
    to it (side_locked_out() already exempts monster/vehicle models). No
    MARKERLIGHT/GRENADES this time either (both left unset, same "don't
    invent what wasn't given" discipline as Kroot Carnivores' missing For
    The Greater Good/Markerlight - this datasheet's own Rules section only
    ever gave Deep Strike/For The Greater Good). WALKER matters for rule
    15.11 (Heroic Intervention): a pure-VEHICLE unit only qualifies if it's
    also CHARACTER or WALKER - see HeroicInterventionController._has_walker().
    base_radius_in: user-supplied, "50mm" base (bigger than the 0.8"/~40mm
    Battlesuit-class assumption these were first given - real Crisis Suits
    stand on a 50mm base, distinctly larger than a Stealth Suit's own
    smaller base) - radius = 25mm = 25/25.4 in ≈ 0.98", same mm-to-inch
    conversion already used for every other base_radius_in in this file
    (e.g. InfantryProfile's 32mm -> 0.63")."""
    name = "Crisis Starscythe Shas'ui"
    base_radius_in = 0.98
    movement_in = 10
    weapon_skill = "5+"
    ballistic_skill = "4+"
    toughness = 5
    wounds = 4
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    vehicle = True
    walker = True
    fly = True
    battlesuit = True
    deep_strike = True  # rule 24.09, already implemented
    for_the_greater_good = True
    starscythe = True  # this datasheet's own ability, see game/starscythe.py
    battlesuit_support_system = True  # this datasheet's own ability, see squad_has_battlesuit_support_system()


class CrisisStarscytheShasVreProfile(CrisisStarscytheShasUiProfile):
    """The unit's Shas'vre (leader model) - identical stat line, no extra
    baseline wargear beyond the same Battlesuit fists + Burst cannon + T'au
    flamer every model in this unit carries."""
    name = "Crisis Starscythe Shas'vre"
    squad_leader = True


class DevilfishProfile(UnitProfile):
    """Datasheet: Devilfish (T'au Empire) - a single-model TRANSPORT vehicle.
    WS/BS aren't in the M/T/Sv/W/Ld/OC table (same 10th-edition convention as
    every other T'au datasheet so far) - read off the weapon tables:
    Accelerator burst cannon's/Twin pulse carbine's own BS4+ both match this
    model's own BS (no per-weapon override needed - unlike the OTHER,
    already-existing TwinPulseCarbineProfile class, whose own BS5+ override
    was correct for a Gun Drone/Strike Team's Unselected Profile riding a
    BS4+ Fire Warrior; the Devilfish's own copy of this weapon needs its own
    class instead of reusing that one, since here the printed BS genuinely
    matches this model's own - see DevilfishTwinPulseCarbineProfile in
    game/weapons.py), Armoured hull's WS5+ matches this model's own WS.

    Keywords: Dedicated Transport, Vehicle, Fly, Transport, Devilfish,
    Faction: T'au Empire (Faction dropped here, same reasoning as every
    other T'au datasheet - implicit in Faction registration). DEDICATED
    TRANSPORT itself isn't modeled - no rule in this engine currently reads
    it (same already-documented gap as SCOUTS 24.31/24.32's own DEDICATED
    TRANSPORT exclusion, see CLAUDE.md's Später-Liste) - it's purely
    descriptive here, like the rest of this tuple.

    base_radius_in: started at VehicleProfile's own ~70mm-width assumption
    (1.4", not given by the user, purely cosmetic - Devilfish's real base is
    a distinct oval shape this engine can't represent anyway, see
    VehicleProfile's own note about approximating vehicle bases as circles)
    - user then asked to enlarge "the Devilfish, including its base" by
    1.5x, so 1.4 * 1.5 = 2.1"."""
    name = "Devilfish"
    base_radius_in = 2.1
    movement_in = 12
    weapon_skill = "5+"
    ballistic_skill = "4+"
    toughness = 9
    wounds = 13
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    vehicle = True
    fly = True
    for_the_greater_good = True
    deadly_demise = 3  # documentation leftover only, see deadly_demise_notation below - kept as the same "die's max value" number it always was, in case anything still reads it as a plain int
    deadly_demise_notation = D3()  # "Deadly Demise D3" - genuinely live (Deadly Demise's own detonation roll is already a real dice step, see game/deadly_demise.py) and, since a user report found it was resolving with no visible roll for the mortal-wound count itself, now a real D3 roll too instead of the earlier silent "always 3" placeholder
    transport = True
    transport_capacity = 12
    transport_requires_infantry = True  # "transport capacity of 12 T'AU EMPIRE INFANTRY models" - the INFANTRY half; see UnitProfile.transport_requires_infantry's own note on the un-modeled "T'au Empire" half
    transport_excludes = ("battlesuit", "kroot", "vespid_stingwings")  # "cannot transport BATTLESUIT, KROOT or VESPID STINGWINGS models"
    rapid_deployment = True  # this datasheet's own ability, see TransportController.can_disembark()/determine_mode()


class GhostkeelProfile(UnitProfile):
    """Datasheet: Ghostkeel Battlesuit (T'au Empire) - a single-model unit,
    like Devilfish. WS/BS aren't in the M/T/Sv/W/Ld/OC table (same
    10th-edition convention as every other T'au datasheet so far) - read off
    the weapon tables: Fusion Collider's own BS4+ matches this model's own
    BS (no per-weapon override needed - Twin T'au Flamer's own "N/A" needs
    none either, since [TORRENT] skips the hit roll entirely), Ghostkeel
    Fists' WS5+ matches this model's own WS.

    Keywords: Vehicle, Walker, Fly, Smoke, Battlesuit, Ghostkeel, Faction:
    T'au Empire (Faction dropped here, same reasoning as every other T'au
    datasheet). SMOKE has no given ability text anywhere on this datasheet
    (unlike e.g. Devilfish's own DEDICATED TRANSPORT, which at least maps to
    an already-documented "not modeled" gap elsewhere) - genuinely nothing
    to wire in, so it's purely descriptive here, like DEDICATED TRANSPORT.

    Rules: Deadly Demise D3 (deadly_demise_notation, a real D3 roll - see
    DevilfishProfile's own note), Infiltrators (already implemented, rule
    24.20), Lone Operative
    ("...within 12\"" - lone_operative=12.0, already implemented, rule
    24.24), Stealth (already implemented, rule 24.33), For The Greater Good
    (already implemented). Battlesuit Support System (user-supplied,
    separately from the initial paste, as part of this datasheet's actual
    build - see game/factions/tau_empire.py's _GHOSTKEEL_LOADOUT) is the
    same ability Crisis Starscythe Battlesuits already has (eligible to
    shoot in a turn it Fell Back) - reused, not redefined.

    base_radius_in: user-supplied real base is a 105mm x 70mm OVAL - this
    engine only has circular bases (see VehicleProfile's own note on the
    same limitation), so it's converted to an equal-AREA circle instead of
    just averaging the two axes: ellipse area = pi*a*b (a,b = semi-axes =
    52.5mm/35mm) = circle area pi*r^2 => r = sqrt(a*b) = sqrt(52.5*35) =
    sqrt(1837.5) ~= 42.87mm ~= 1.69" (same mm-to-inch conversion used
    everywhere else in this file)."""
    name = "Ghostkeel Battlesuit"
    base_radius_in = 1.69
    movement_in = 10
    weapon_skill = "5+"
    ballistic_skill = "4+"
    toughness = 8
    wounds = 12
    leadership = "7+"
    armor_save = "2+"
    oc = 3
    vehicle = True
    walker = True
    fly = True
    battlesuit = True
    infiltrators = True  # rule 24.20, already implemented
    lone_operative = 12.0  # "...can only be selected as the target of a ranged attack if the attacking model is within 12\"" - rule 24.24, already implemented
    stealth = True  # rule 24.33, already implemented
    for_the_greater_good = True
    deadly_demise = 3  # documentation leftover only, see DevilfishProfile's own note on deadly_demise_notation
    deadly_demise_notation = D3()  # "Deadly Demise D3" - see DevilfishProfile's own note; now a real D3 roll, not a silent "always 3"
    battlesuit_support_system = True  # see squad_has_battlesuit_support_system() / Crisis Starscythe's own use of this field
    damaged_threshold = 4  # "Damaged: 1-4 Wounds Remaining" - this datasheet's own ability, see game/shooting.py's _damaged_modifier()
    stealth_drones = 2  # "Stealth Drones" - this datasheet's own ability, see game/stealth_drones.py


class ColdstarCommanderProfile(UnitProfile):
    """Datasheet: Commander in Coldstar Battlesuit (T'au Empire) - a
    single-model CHARACTER Battlesuit, unlike every other T'au datasheet so
    far (Strike/Breacher/Kroot/Stealth/Starscythe/Ghostkeel/Devilfish are
    all non-CHARACTER). WS/BS aren't in the M/T/Sv/W/Ld/OC table (same
    10th-edition convention as every other T'au datasheet) - read off the
    weapon tables: High-output burst cannon's own BS3+ and Battlesuit
    fists' own WS4+ both match this model's own values, so no weapon needs
    a per-weapon override; Battlesuit fists reuses CrisisBattlesuitFistsProfile
    (A3/S5/AP0/D1) since the stats are identical, rather than a third
    "Battlesuit Fists"-named class.

    Keywords: Character, Vehicle, Walker, Fly, Battlesuit, Faction: T'au
    Empire (Faction dropped, same reasoning as every other T'au datasheet).

    Rules: Deep Strike (24.09, already implemented), For The Greater Good
    (already implemented).

    Leader: "This model can be attached to the following units: Crisis
    Sunforge Battlesuits, Crisis Starscythe Battlesuits, Crisis Fireknife
    Battlesuits" - enforced by game/attached_units.py's can_attach(), which
    reads the pairing off the points list's own `leads` table. Two of those
    three (Sunforge/Fireknife) still have no datasheet in this engine, same
    as Commander Farsight's own `leads` reference in the points list.

    "Coldstar Commander" ability (while leading a unit, that unit's models
    get Move 12" and their ranged weapons gain [ASSAULT]) is engine-wired
    since Attached Units (19.01) exist - see game/coldstar.py. It was
    deferred while nothing could form an attached unit, and stayed deferred
    after that changed, which left the demo scene's own led Crisis team
    quietly moving 8" and unable to shoot after Advancing.

    base_radius_in: user-supplied "base 60 mm" - 60mm/2 = 30mm radius =
    30/25.4 ~= 1.18" (same mm-to-inch conversion used everywhere else in
    this file, e.g. DeffDreadProfile's own 60mm base)."""
    name = "Commander in Coldstar Battlesuit"
    base_radius_in = 1.18
    movement_in = 12
    weapon_skill = "4+"
    ballistic_skill = "3+"
    toughness = 5
    wounds = 6
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    character = True
    vehicle = True
    walker = True
    fly = True
    battlesuit = True
    deep_strike = True  # rule 24.09, already implemented
    for_the_greater_good = True
    leader = True  # "Leader: ... Crisis Sunforge/Fireknife/Starscythe Battlesuits" - enforced by game/attached_units.py's can_attach()
    coldstar_commander = True  # this datasheet's own ability - see UnitProfile.coldstar_commander's own note and game/coldstar.py


class CadreFirebladeProfile(UnitProfile):
    """Datasheet: Cadre Fireblade (T'au Empire) - a single-model INFANTRY
    CHARACTER, unlike every T'au Battlesuit/Vehicle datasheet added so far.
    WS/BS aren't in the M/T/Sv/W/Ld/OC table (same 10th-edition convention as
    every other T'au datasheet) - read off the weapon tables: Fireblade
    pulse rifle's own BS3+ and Close combat weapon's own WS4+ both match
    this model's own values, so no weapon needs a per-weapon override.

    Keywords: Character, Infantry, Grenades, Faction: T'au Empire (Faction
    dropped, same reasoning as every other T'au datasheet).

    Rules: For The Greater Good (already implemented). No Deep Strike this
    time (this datasheet's own Rules section only ever gave For The Greater
    Good - same "don't invent what wasn't given" discipline as Kroot
    Carnivores' own missing Deep Strike/Markerlight).

    Abilities:
    - Crack Shot: each time this model makes a ranged attack, on a Critical
      Wound, that attack has an Armour Penetration characteristic of -3 -
      genuinely engine-wired (unlike Leader/Volley Fire below), since it
      only ever depends on this model's own attacks, not an attached unit -
      see game/crack_shot.py, game/shooting.py's _begin_crack_shot_save().
    - Volley Fire ("while this model is leading a unit, add 1 to the
      Attacks characteristic of ranged weapons equipped by models in that
      unit") - engine-wired since Attached Units (19.01) exist, see
      game/volley_fire.py. It was deferred while there was no way to form an
      attached unit at all, and stayed deferred one release too long after
      that changed: user report "breacher hatten nur 20 schuss, trotz
      fireblade. hätten 30 sein müssen" - 10 Pulse Blasters at A2 instead of
      A3.
    - Leader ("can be attached to Breacher Team, Strike Team") is enforced by
      game/attached_units.py's can_attach(), which reads the pairing straight
      off the points list's own `leads` table.

    base_radius_in: not given by the user - assumed 32mm, same "matching
    InfantryProfile's size class" convention already used for e.g.
    FireWarriorProfile's own base_radius_in."""
    name = "Cadre Fireblade"
    base_radius_in = 0.63
    movement_in = 6
    weapon_skill = "4+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 3
    leadership = "7+"
    armor_save = "4+"
    oc = 1
    character = True
    infantry = True
    grenades = True
    for_the_greater_good = True
    leader = True  # "Leader: ... Breacher Team, Strike Team" - see game/attached_units.py's can_attach()
    crack_shot = True  # this datasheet's own ability, see game/crack_shot.py
    volley_fire = True  # this datasheet's own ability, see game/volley_fire.py


class RiptideProfile(UnitProfile):
    """Datasheet: Riptide Battlesuit (T'au Empire) - a single-model unit,
    like Ghostkeel/Devilfish. WS/BS aren't in the M/T/Sv/W/Ld/OC table (same
    10th-edition convention as every other T'au datasheet) - read off the
    weapon tables: Heavy burst cannon's/Twin plasma rifle's own BS4+ both
    match this model's own BS, Riptide fists' WS5+ matches this model's own
    WS, so no weapon needs a per-weapon override.

    Keywords: Vehicle, Walker, Fly, Battlesuit, Riptide, Faction: T'au
    Empire (Faction dropped here, same reasoning as every other T'au
    datasheet - implicit in Faction registration). Notably VEHICLE/WALKER,
    not INFANTRY: this unit does NOT cross Dense terrain for free (13.06),
    and WALKER is what lets it qualify for rule 15.11 (Heroic Intervention)
    despite being a VEHICLE - see HeroicInterventionController._has_walker().

    Rules: Deadly Demise D6 (deadly_demise_notation, a real D6 roll - see
    DevilfishProfile's own note on why the plain int is a documentation
    leftover), For The Greater Good (already implemented).

    Abilities: Invulnerable Save (4+) - the first T'au datasheet in this
    engine to have one at all (previously only the Ork Warbikers/Stormboyz
    profiles did). Damaged: 1-4 Wounds Remaining (damaged_threshold, the
    same field and the same -1 Hit roll the Ghostkeel already uses).
    Battlesuit Support System (the same ability Crisis Starscythe/Ghostkeel
    already carry - reused, not redefined; note this datasheet's own
    printed wording adds "but when doing so only models equipped with this
    wargear can make ranged attacks", which is a no-op here because this
    unit is a single model that HAS the wargear). Weapon Support System and
    Nova Charge are both new - see the fields' own notes and
    game/nova_charge.py.

    base_radius_in: user-supplied real base is a 120mm x 92mm OVAL - this
    engine only has circular bases (see VehicleProfile's own note on the
    same limitation), so it is converted to an equal-AREA circle rather
    than by averaging the two axes, exactly as GhostkeelProfile's own
    105mm x 70mm oval was: ellipse area = pi*a*b (a,b = semi-axes = 60mm/
    46mm) = circle area pi*r^2 => r = sqrt(a*b) = sqrt(60*46) = sqrt(2760)
    ~= 52.54mm ~= 2.07" (same mm-to-inch conversion used everywhere else in
    this file). That makes it this engine's largest base, slightly under
    the Devilfish's own 2.1"."""
    name = "Riptide Battlesuit"
    base_radius_in = 2.07
    movement_in = 10
    weapon_skill = "5+"
    ballistic_skill = "4+"
    toughness = 9
    wounds = 14
    leadership = "7+"
    armor_save = "2+"
    invulnerable_save = "4+"  # "Invulnerable Save (4+)"
    oc = 4
    vehicle = True
    walker = True
    fly = True
    battlesuit = True
    for_the_greater_good = True
    deadly_demise = 6  # documentation leftover only, see DevilfishProfile's own note on deadly_demise_notation
    deadly_demise_notation = D6()  # "Deadly Demise D6"
    damaged_threshold = 4  # "Damaged: 1-4 Wounds Remaining" - see game/shooting.py's _damaged_modifier()
    battlesuit_support_system = True  # see squad_has_battlesuit_support_system() / Crisis Starscythe's own use of this field
    weapon_support_system = True  # "Weapon Support System" - see game/shooting.py's _hit_modifiers()
    nova_charge = 1  # "Nova Charge: Once per battle..." - see game/nova_charge.py


class PathfinderProfile(UnitProfile):
    """Datasheet: Pathfinder Team (T'au Empire) - one stat row for the whole
    unit (the Shas'ui and the 9 rank-and-file Pathfinders are identical),
    same convention as Kroot Carnivores/Stealth Battlesuits. WS/BS aren't in
    the M/T/Sv/W/Ld/OC table (same 10th-edition convention as every other
    T'au datasheet) - read off the weapon tables: Pulse carbine's/Pulse
    pistol's own BS4+ and Close combat weapon's WS5+ all match this model's
    own values, so no weapon needs a per-weapon override.

    Keywords: Infantry, Grenades, Markerlight, Pathfinder Team, Faction:
    T'au Empire (Faction dropped, same reasoning as every other T'au
    datasheet). INFANTRY here, unlike the Battlesuit datasheets - so this
    unit DOES cross Dense terrain for free (13.06) and can be Hidden
    (13.09).

    Rules: Scouts 7" (already implemented - game/scouts.py's Scout Move step
    of the Pre-game Sequence reads profile.scouts), For The Greater Good
    (already implemented).

    Abilities: Target Uploaded - engine-wired, see game/target_uploaded.py.

    base_radius_in: not given by the user - assumed 32mm, the same "matching
    InfantryProfile's size class" convention already used for
    FireWarriorProfile/CadreFirebladeProfile."""
    name = "Pathfinder"
    base_radius_in = 0.63
    movement_in = 7
    weapon_skill = "5+"
    ballistic_skill = "4+"
    toughness = 3
    wounds = 1
    leadership = "7+"
    armor_save = "4+"
    oc = 1
    infantry = True
    grenades = True
    markerlight = True
    for_the_greater_good = True
    scouts = 7.0  # "Scouts 7\"" - rule 24.31/24.32, see game/scouts.py
    target_uploaded = True  # this datasheet's own ability, see game/target_uploaded.py


class PathfinderShasUiProfile(PathfinderProfile):
    """The unit's Shas'ui (leader model) - identical stat line, no extra
    baseline wargear beyond the same Close combat weapon + Pulse carbine +
    Pulse pistol every model in this unit carries. It is the model that
    takes the unit's drones (see game/factions/tau_empire.py's
    PATHFINDER_TEAM), the same way every other T'au datasheet hangs its
    drone menu off the leader line."""
    name = "Pathfinder Shas'ui"
    squad_leader = True


class CrisisSunforgeShasUiProfile(UnitProfile):
    """Datasheet: Crisis Sunforge Battlesuits (T'au Empire) - one stat row
    for the whole unit (the Shas'vre and both Shas'ui are identical), same
    convention as its sibling Crisis Starscythe Battlesuits. WS/BS aren't in
    the M/T/Sv/W/Ld/OC table (same 10th-edition convention as every other
    T'au datasheet) - read off the weapon tables: Fusion blaster's own BS4+
    and Battlesuit fists' WS5+ both match this model's own values, so no
    weapon needs a per-weapon override.

    Keywords: Vehicle, Walker, Fly, Battlesuit, Crisis, Sunforge, Faction:
    T'au Empire (Faction dropped, same reasoning as every other T'au
    datasheet). VEHICLE/WALKER rather than INFANTRY, exactly like
    Starscythe: no free Dense-terrain crossing (13.06), rule 24.07's
    [CLOSE-QUARTERS] weapon-side lock doesn't apply, and WALKER is what lets
    it qualify for rule 15.11 (Heroic Intervention) despite being a VEHICLE.

    Rules: Deep Strike (24.09, already implemented), For The Greater Good
    (already implemented).

    Abilities: Sunforge - engine-wired, see game/sunforge.py. Invulnerable
    Save (4+) - the second T'au datasheet here to have one, after the
    Riptide.

    Note this datasheet has NO Battlesuit Support System, unlike Starscythe
    and Ghostkeel - it isn't on the supplied Abilities list, so the field
    stays unset rather than being assumed from the sibling datasheets.

    base_radius_in: user-supplied, "gleiche basegröße wie starsythe" - the
    same 0.98" (50mm) CrisisStarscytheShasUiProfile carries."""
    name = "Crisis Sunforge Shas'ui"
    base_radius_in = 0.98
    movement_in = 10
    weapon_skill = "5+"
    ballistic_skill = "4+"
    toughness = 5
    wounds = 4
    leadership = "7+"
    armor_save = "3+"
    invulnerable_save = "4+"  # "Invulnerable Save (4+) [Crisis Sunforge Battlesuits]"
    oc = 2
    vehicle = True
    walker = True
    fly = True
    battlesuit = True
    deep_strike = True  # rule 24.09, already implemented
    for_the_greater_good = True
    sunforge = True  # this datasheet's own ability, see game/sunforge.py


class CrisisSunforgeShasVreProfile(CrisisSunforgeShasUiProfile):
    """The unit's Shas'vre (leader model) - identical stat line, and the
    same baseline loadout every model in this unit carries (2x Fusion
    blaster + Battlesuit fists)."""
    name = "Crisis Sunforge Shas'vre"
    squad_leader = True


class TwinLanceProfile(UnitProfile):
    """Datasheet: The Twin Lance (T'au Empire) - a 2-model EPIC HERO unit
    (Ri'Lantar and Ri'Locai), one stat row for both. They differ ONLY in
    their main gun (Fusion eliminator vs Ion scattercannon), so both share
    this profile and the datasheet gives them separate ModelLines purely to
    carry those different loadouts.

    BS is not in the M/T/Sv/W/Ld/OC table (same 10th-edition convention as
    every other T'au datasheet) - read off the weapon tables, where every
    weapon the models themselves carry prints BS2+; only the MV15 Gun
    Drone's Twin pulse blaster prints BS5+, and that one carries its own
    override (see TwinPulseBlasterProfile).

    WS is the first genuine conflict in this engine: the three melee entries
    print 4+, 3+ and 4+ on one stat line. Each melee weapon therefore
    carries its own `weapon_skill` override (the per-weapon mechanism added
    for the Ork Power Klaw), which makes this field's value irrelevant to
    any result - it is set to 4+, the value two of the three print, so the
    overrides that exist are the genuinely unusual ones.

    Keywords: Epic Hero, Vehicle, Walker, Fly, Character, Battlesuit, The
    Twin Lance, Faction: T'au Empire (Faction dropped, same reasoning as
    every other T'au datasheet). CHARACTER matters for rule 05.03's wound
    allocation; VEHICLE/WALKER means no free Dense-terrain crossing (13.06)
    but does qualify for rule 15.11 (Heroic Intervention). EPIC HERO drives
    no engine logic here (no army-building flow to enforce "only one"), so
    it is descriptive on the datasheet's keyword tuple only.

    Rules: For The Greater Good, Scouts 8" (game/scouts.py), Deep Strike
    (24.09), and a UNIT-level Ignores Cover - all four already implemented.

    Abilities: Exemplars of Mont'ka, Neocapacitor Shields, Retro-thrusters
    (each in its own module) and Invulnerable Save (4+).

    base_radius_in: user-supplied - "Twin Lance und Farsight haben die selbe
    basegroesse wie Coldstar Commander", i.e. 1.18" (60mm), replacing an
    earlier 0.98" assumption made when no size had been given."""
    name = "The Twin Lance"
    base_radius_in = 1.18
    movement_in = 10
    weapon_skill = "4+"  # see class docstring - every melee weapon overrides this anyway
    ballistic_skill = "2+"
    toughness = 6
    wounds = 8
    leadership = "6+"
    armor_save = "2+"
    invulnerable_save = "4+"  # "Invulnerable Save (4+) [The Twin Lance]"
    oc = 2
    character = True
    vehicle = True
    walker = True
    fly = True
    battlesuit = True
    deep_strike = True  # rule 24.09, already implemented
    scouts = 8.0  # "Scouts 8\"" - rule 24.31/24.32, see game/scouts.py
    for_the_greater_good = True
    ignores_cover = True  # the unit-level "Ignores Cover" RULE (not a weapon keyword) - see game/shooting.py's _cover_ignored_for_group()
    exemplars_of_montka = True  # see game/exemplars_of_montka.py
    neocapacitor_shields = True  # see game/neocapacitor_shields.py
    retro_thrusters = True  # see game/retro_thrusters.py


class RiLantarProfile(TwinLanceProfile):
    """Ri'Lantar - the Fusion eliminator half of the pair. Marked as the
    squad leader purely so the two are visually distinguishable on the board
    (this unit has no leader in the rules sense); the datasheet lists it
    first."""
    name = "Ri'Lantar"
    squad_leader = True


class RiLocaiProfile(TwinLanceProfile):
    """Ri'Locai - the Ion scattercannon half of the pair."""
    name = "Ri'Locai"


class CommanderFarsightProfile(UnitProfile):
    """Datasheet: Commander Farsight (T'au Empire) - a single-model EPIC HERO
    CHARACTER Battlesuit. WS/BS aren't in the M/T/Sv/W/Ld/OC table (same
    10th-edition convention as every other T'au datasheet) - read off the
    weapon tables: the High-intensity plasma rifle's BS2+ and both Dawn Blade
    modes' WS2+ all match this model's own values, so no weapon needs a
    per-weapon override.

    Keywords: Epic Hero, Vehicle, Walker, Fly, Character, Battlesuit,
    Commander Farsight, Faction: T'au Empire (Faction dropped, same reasoning
    as every other T'au datasheet). CHARACTER matters for rule 05.03's wound
    allocation; VEHICLE/WALKER means no free Dense-terrain crossing (13.06)
    but does qualify for rule 15.11 (Heroic Intervention). EPIC HERO drives
    no engine logic (no army-building flow to enforce "only one").

    Rules: Deep Strike (24.09), For The Greater Good, Leader - all three
    already implemented.

    "Independent Power" (an army may not contain both Farsight and any
    ETHEREAL unit) is deliberately NOT modeled: it is an army-BUILDING
    restriction, and this engine has no army-building flow to enforce it
    against - the same already-documented gap that leaves EPIC HERO's own
    "only one" unenforced. No Ethereal datasheet exists here either, so
    nothing can violate it today. Recorded on the datasheet's abilities_text
    so it is visible rather than silently dropped.

    Abilities: Way of the Short Blade (game/way_of_the_short_blade.py),
    Puretide's Teachings (game/puretide.py) and Invulnerable Save (4+).

    base_radius_in: user-supplied - "Twin Lance und Farsight haben die selbe
    basegroesse wie Coldstar Commander", confirmed as a 60mm base, so
    60/2/25.4 ~= 1.18" (the same mm-to-inch conversion used everywhere else
    in this file)."""
    name = "Commander Farsight"
    base_radius_in = 1.18
    movement_in = 10
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 5
    wounds = 8
    leadership = "6+"
    armor_save = "2+"
    invulnerable_save = "4+"  # "Invulnerable Save (4+)"
    oc = 2
    character = True
    vehicle = True
    walker = True
    fly = True
    battlesuit = True
    deep_strike = True  # rule 24.09, already implemented
    for_the_greater_good = True
    leader = True  # "Leader: ... Crisis Sunforge/Fireknife/Starscythe Battlesuits" - see game/attached_units.py's can_attach(), which reads the pairing off the points list's own `leads` table
    way_of_the_short_blade = True  # see game/way_of_the_short_blade.py
    puretide_teachings = True  # see game/puretide.py


# --- Guardian Defenders (Aeldari), see game/factions/aeldari.py ---

class GuardianDefenderProfile(UnitProfile):
    """The rank and file. WS/BS are not in the datasheet's stat table (10th
    edition prints them per weapon - see UnitProfile's own docstring); both are
    3+, read off the Shuriken Catapult and Close Combat Weapon rows, so neither
    weapon needs a per-weapon override.

    base_radius_in is NOT an assumption here, unlike most profiles in this
    file: the datasheet gives 28.5mm, converted the same way every other base
    in this file is (28.5 / 2 / 25.4). That makes it the smallest base in the
    engine."""
    name = "Guardian Defender"
    base_radius_in = 0.561
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 1
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    infantry = True
    battle_focus = True      # Aeldari army rule - see game/battle_focus.py
    fleet_of_foot = True     # free Fade Back - see game/battle_focus.py's is_free()
    platform_crew = True     # keeps this unit's Heavy Weapon Platform alive - see game/crewed_platform.py


class HeavyWeaponPlatformProfile(UnitProfile):
    """Same unit, different model line: 2 wounds, OC 0, a 40mm base, and it
    carries the unit's heavy gun.

    INFANTRY like the rest of the unit - the keyword line is unit-wide, so the
    platform crosses Dense terrain (13.06) exactly as the Guardians do."""
    name = "Heavy Weapon Platform"
    base_radius_in = 0.787
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 2
    leadership = "7+"
    armor_save = "4+"
    oc = 0
    infantry = True
    battle_focus = True
    fleet_of_foot = True
    crewed_platform = True   # destroyed with the last Guardian - see game/crewed_platform.py


# --- Storm Guardians (Aeldari), see game/factions/aeldari.py ---

class StormGuardianProfile(UnitProfile):
    """Same statline and 28.5mm base as a Guardian Defender - the two lines
    differ in loadout and abilities, not numbers.

    NO fleet_of_foot: this datasheet does not have that ability, unlike Guardian
    Defenders. Checked explicitly rather than copied across, because copying a
    near-identical profile is exactly how an ability gets granted by accident."""
    name = "Storm Guardian"
    base_radius_in = 0.561
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 1
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    infantry = True
    battle_focus = True
    platform_crew = True     # keeps this unit's Serpent's Scale Platform alive
    fieldcraft = True        # printed here as "Stormblades" - the same sticky-objective rule Kroot Carnivores' Fieldcraft and Boyz' Get Da Good Bitz print under their own names, so it shares the one flag (see game/fieldcraft.py's docstring)


class SerpentsScalePlatformProfile(UnitProfile):
    """Carries no gun at all - its whole contribution is the Serpent Shield it
    grants the rest of the unit."""
    name = "Serpent's Scale Platform"
    base_radius_in = 0.787
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 2
    leadership = "7+"
    armor_save = "4+"
    oc = 0
    infantry = True
    battle_focus = True
    crewed_platform = True   # destroyed with the last Storm Guardian
    fieldcraft = True        # "Stormblades" applies to the whole unit, and squad_has_fieldcraft() is an all()-check, so the platform needs it too
    serpent_shield = True    # 5+ invulnerable save for the whole unit - see game/invulnerable_save.py


# --- Striking Scorpions (Aeldari), see game/factions/aeldari.py ---

class StrikingScorpionProfile(UnitProfile):
    """Aspect Warriors, so tougher-armoured and steadier than a Guardian:
    Sv3+ against their 4+, Ld6+ against their 7+, and OC1 rather than 2.

    All three of its core abilities were already implemented before this
    datasheet existed - INFILTRATORS (24.20), SCOUTS (24.31/24.32) and STEALTH
    (24.33). STEALTH in particular needed nothing: game/shooting.py already
    reads it as "this unit unconditionally has the benefit of cover against
    every ranged attack", which is what the datasheet says."""
    name = "Striking Scorpion"
    base_radius_in = 0.561
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 1
    leadership = "6+"
    armor_save = "3+"
    oc = 1
    infantry = True
    battle_focus = True
    aspect_shrine = True    # see game/aspect_shrine.py
    infiltrators = True
    scouts = 7
    stealth = True
    mandiblasters = True     # see game/crit_hit.py - inherited by the Exarch below


class HowlingBansheeProfile(UnitProfile):
    """Fast (M8") and precise (WS2+), with a conditional invulnerable save.

    fights_first is the CORE ability (24.13), already implemented and read by
    squad_has_fights_first() - distinct from Squad.fights_first, which is the
    temporary post-charge grant."""
    name = "Howling Banshee"
    base_radius_in = 0.561
    movement_in = 8
    weapon_skill = "2+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 1
    leadership = "6+"
    armor_save = "4+"
    oc = 1
    infantry = True
    battle_focus = True
    aspect_shrine = True    # see game/aspect_shrine.py
    fights_first = True             # rule 24.13, already implemented
    full_throttle = True            # printed here as "Acrobatic" - word for word the same rule Stormboyz print as "Full Throttle" (charge in a turn it Advanced or Fell Back), already read by game/charge.py, so it shares that flag
    invulnerable_save = "5+"
    invulnerable_save_vs_melee = "4+"


class HowlingBansheeExarchProfile(HowlingBansheeProfile):
    """Identical apart from a second wound and its own loadout - subclassed
    rather than copied, same reasoning as the Striking Scorpion Exarch."""
    name = "Howling Banshee Exarch"
    wounds = 2
    squad_leader = True


class StrikingScorpionExarchProfile(StrikingScorpionProfile):
    """The unit's leader: identical apart from a second wound and its own
    loadout. Subclassed rather than copied - copying a near-identical profile
    is how a stat silently drifts between two lines of one datasheet."""
    name = "Striking Scorpion Exarch"
    wounds = 2
    squad_leader = True


class WarpSpiderProfile(UnitProfile):
    """Jump-pack Aspect Warriors: the fastest infantry in this engine at M12",
    and 24" with Flickerjump.

    ballistic_skill is an INFERENCE, and a harmless one: every ranged weapon on
    this datasheet is [TORRENT] (rule 24.37 skips the Hit roll), so the printed
    row is "N/A" and nothing in the engine ever reads a BS for these models.
    3+ is what every other Aspect Warrior datasheet here prints."""
    name = "Warp Spider"
    base_radius_in = 0.561          # 28.5 mm printed base
    movement_in = 12
    weapon_skill = "3+"             # from the melee weapon rows, which do print one
    ballistic_skill = "3+"          # never read - see the class docstring
    toughness = 3
    wounds = 1
    leadership = "6+"
    armor_save = "3+"
    oc = 1
    infantry = True
    fly = True                      # the FLY keyword
    jump_pack = True                # the JUMP PACK keyword - this WAS wrongly commented here as having no flag; it does, and it is what a TRANSPORT's transport_excludes reads (the Falcon cannot carry these)
    deep_strike = True              # rule 24.09, already implemented
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    aspect_shrine = True    # see game/aspect_shrine.py
    flickerjump = True              # see game/flickerjump.py
    invulnerable_save = "5+"


class WarpSpiderExarchProfile(WarpSpiderProfile):
    """Identical apart from a second wound and its own loadout - subclassed
    rather than copied, same reasoning as the other Aspect Warrior Exarchs."""
    name = "Warp Spider Exarch"
    wounds = 2


class DireAvengerProfile(UnitProfile):
    """The Aspect Warrior BATTLELINE-alike: no invulnerable improvement, no
    movement trick, but [SUSTAINED HITS 1] inside half range on every ranged
    weapon it carries (Bladestorm)."""
    name = "Dire Avenger"
    base_radius_in = 0.561          # 28.5 mm printed base
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 1
    leadership = "6+"
    armor_save = "4+"
    oc = 1
    infantry = True
    battle_focus = True
    aspect_shrine = True    # see game/aspect_shrine.py
    bladestorm = True               # see game/bladestorm.py
    invulnerable_save = "5+"


class DireAvengerExarchProfile(DireAvengerProfile):
    name = "Dire Avenger Exarch"
    wounds = 2


class FireDragonProfile(UnitProfile):
    """Anti-tank Aspect Warriors: 12" melta guns and Assured Destruction, which
    lets every step of an attack on a MONSTER or VEHICLE be re-rolled."""
    name = "Fire Dragon"
    base_radius_in = 0.561          # 28.5 mm printed base
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 1
    leadership = "6+"
    armor_save = "3+"
    oc = 1
    infantry = True
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    aspect_shrine = True            # see game/aspect_shrine.py
    assured_destruction = True      # see game/assured_destruction.py
    invulnerable_save = "5+"


class FireDragonExarchProfile(FireDragonProfile):
    """Identical apart from a second wound and its own loadout - subclassed
    rather than copied, same reasoning as the other Aspect Warrior Exarchs."""
    name = "Fire Dragon Exarch"
    wounds = 2


class FalconProfile(UnitProfile):
    """Aeldari grav-tank: the faction's first VEHICLE and first TRANSPORT here.

    weapon_skill is not printed on the statline - the Wraithbone hull prints
    its own WS4+, which is a real per-weapon override and the only melee this
    model has, so nothing ever reads a model-level one. Set to match it rather
    than left at the class default, so the two cannot disagree."""
    name = "Falcon"
    base_radius_in = 1.181          # 60 mm flying base
    movement_in = 14
    weapon_skill = "4+"
    ballistic_skill = "3+"
    toughness = 9
    wounds = 12
    leadership = "7+"
    armor_save = "3+"
    oc = 3
    vehicle = True
    fly = True
    deep_strike = True              # printed on its CORE line, rule 24.09
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    fire_support = True             # see game/fire_support.py
    deadly_demise = 1               # documentation leftover - deadly_demise_notation is what is rolled
    deadly_demise_notation = D3()   # "Deadly Demise D3", rule 24.08
    damaged_threshold = 4           # "DAMAGED: 1-4 WOUNDS REMAINING" - minus 1 to the Hit roll
    transport = True
    transport_capacity = 6          # "6 AELDARI INFANTRY models"
    transport_requires_infantry = True
    # "It cannot transport JUMP PACK models" - so no Warp Spiders. The YNNARI
    # half of the printed exclusion is not modelled: this engine has no
    # per-model faction tracking, the same documented gap the Devilfish's
    # "T'AU EMPIRE INFANTRY" half carries.
    transport_excludes = ("jump_pack",)


class WraithguardProfile(UnitProfile):
    """Slow, extremely tough (T6/Sv2+/W3) infantry carrying the engine's
    highest-Strength gun.

    Its Ld8+ is the worst in the engine, which is the point of Psychic
    Guidance improving it to 6+."""
    name = "Wraithguard"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 6
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 6
    wounds = 3
    leadership = "8+"
    armor_save = "2+"
    oc = 1
    infantry = True
    wraith_construct = True         # WRAITH CONSTRUCT - two transport slots each
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    war_construct = True            # see game/shooting.py's available_shooting_types()
    psychic_guidance = True         # see game/psychic_guidance.py


class AsurmenProfile(UnitProfile):
    """Phoenix Lord: a one-model EPIC HERO who leads Dire Avengers.

    The lone AELDARI CHARACTER here so far, which is why it is also the first
    Aeldari profile to set `leader` - rule 19.01's attachment legality is read
    off the points list's own LEADER line (UnitPoints.leads)."""
    name = "Asurmen"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 7
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 3
    wounds = 5
    leadership = "6+"
    armor_save = "2+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    leader = True                   # the CHARACTER/LEADER pair, rule 24.22
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    tactical_acumen = True          # see game/tactical_acumen.py
    hand_of_asuryan = True          # see game/hand_of_asuryan.py


class JainZarProfile(UnitProfile):
    """The second Phoenix Lord here, and the faster one - M8" before Whirling
    Death, which adds another 6" to it on an Advance."""
    name = "Jain Zar"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 8
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 3
    wounds = 5
    leadership = "6+"
    armor_save = "2+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    leader = True                   # her CORE line: "Fights First, Leader"
    fights_first = True             # rule 24.13, already implemented
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    whirling_death = True           # see game/whirling_death.py
    storm_of_silence = True         # see game/storm_of_silence.py


class LhykhisProfile(UnitProfile):
    """The third Phoenix Lord here, and the fastest thing in the engine at
    M12" - before Flickerjump, which she is built to pair with: she leads Warp
    Spiders and only Warp Spiders, and her Empyric Ambush cancels the charge
    restriction that ability normally costs them.

    Prints no Ballistic Skill, and that is not an omission: her only ranged
    weapon is [TORRENT] (24.37), which makes no hit roll. Left at the
    UnitProfile default, which nothing reads for her."""
    name = "Lhykhis"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 12
    weapon_skill = "2+"
    toughness = 3
    wounds = 5
    leadership = "6+"
    armor_save = "2+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    jump_pack = True                # JUMP PACK - so she costs 2 transport slots, and a Falcon cannot carry her at all
    fly = True
    leader = True                   # the CHARACTER/LEADER pair, rule 24.22
    deep_strike = True              # her CORE line, rule 24.09
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    empyric_ambush = True           # see game/empyric_ambush.py
    whispering_web = True           # see game/whispering_web.py


class AvatarOfKhaineProfile(UnitProfile):
    """The first MONSTER in an Aeldari army here, and the toughest single model
    in the engine at T11/W14/Sv2+ with a 4+ invulnerable on top - before Molten
    Form halves what does get through.

    Not a leader: this datasheet prints no LEADER line, so there is no
    UnitPoints.leads entry either."""
    name = "Avatar of Khaine"
    base_radius_in = 1.575          # 80 mm printed base - the largest here
    movement_in = 10
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 11
    wounds = 14
    leadership = "6+"
    armor_save = "2+"
    oc = 5
    invulnerable_save = "4+"
    monster = True                  # the MONSTER keyword
    damaged_threshold = 5           # "Damaged: 1-5 Wounds Remaining" -> -1 to its own Hit rolls, see game/shooting.py's _damaged_modifier()
    deadly_demise = 3               # documentation leftover only, see deadly_demise_notation below - same convention as DevilfishProfile
    deadly_demise_notation = D3()   # his CORE line, rule 24.08 - a real D3 roll, see game/deadly_demise.py
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    molten_form = True              # see game/molten_form.py
    bloody_handed = True            # see game/bloody_handed.py


class WarlockProfile(UnitProfile):
    """The first AELDARI PSYKER in this engine - which is what makes
    Wraithguard's Psychic Guidance stop being inert.

    It is both a LEADER unit (it attaches to Guardian Defenders or Storm
    Guardians) and, per its own Protect ability, a unit that can itself be led
    by a Farseer."""
    name = "Warlock"
    base_radius_in = 0.630          # 32 mm printed base
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 2
    leadership = "6+"
    armor_save = "6+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    psyker = True                   # the PSYKER keyword - and here it is finally read by a rule
    leader = True                   # its CORE line
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    psychic_communion = True        # see game/psychic_communion.py
    protect = True                  # see game/protect.py


class FarseerProfile(UnitProfile):
    """Does NOT make Warlock Conclave's Protect live, contrary to what this
    docstring used to claim: Protect needs a FARSEER LEADING a unit that
    contains Warlocks, and a Conclave is itself a leader unit that neither
    datasheet's LEADER line names. Eldrad Ulthran is the one that reaches it,
    through his own LEADER line - see EldradUlthranProfile and game/protect.py."""
    name = "Farseer"
    base_radius_in = 0.492          # 25 mm printed base, the smallest here
    movement_in = 7
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 3
    wounds = 4
    leadership = "6+"
    armor_save = "6+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    psyker = True                   # PSYKER - so he also feeds Psychic Guidance and Psychic Communion
    farseer = True                  # FARSEER - read by game/protect.py
    leader = True                   # his CORE line
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    branching_fates = True          # see game/branching_fates.py
    guide = True                    # see game/guide.py


class EldradUlthranProfile(UnitProfile):
    """EPIC HERO, and the datasheet that finally makes Warlock Conclave's
    Protect reachable - not through anything in that ability, but through his
    own LEADER line's second sentence ("you can attach this model to a unit,
    even if one WARLOCKS unit has already been attached to it"). He is a
    FARSEER, so Guardians + Warlock Conclave + Eldrad is a unit with a Farseer
    leading Warlocks, which is exactly Protect's condition. See
    game/attached_units.py's _leader_allows_joining_led_unit()."""
    name = "Eldrad Ulthran"
    base_radius_in = 0.630          # 32 mm printed base
    movement_in = 7
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 4
    wounds = 5
    leadership = "6+"
    armor_save = "6+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    psyker = True                   # PSYKER - so he also feeds Psychic Guidance and Psychic Communion
    farseer = True                  # FARSEER - and here it is what makes Protect reachable
    leader = True                   # his CORE line
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    doom = True                     # see game/doom.py (Guide's twin, sharing game/psychic_mark.py)
    diviner_of_futures = True       # see game/diviner_of_futures.py
    joins_warlock_led_unit = True   # the second sentence of his LEADER line, see the class docstring
