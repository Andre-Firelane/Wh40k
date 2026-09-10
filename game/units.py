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
    epic_hero = False  # the EPIC HERO keyword. Purely descriptive - its printed consequence ("only one of these in your army") is a Muster Armies rule, and there is no army-building flow to enforce it (see CLAUDE.md's Spaeter-Liste). Declared here rather than left as an ad-hoc attribute so `profile.epic_hero` is safe to read
    mounted = False  # the MOUNTED keyword. Descriptive today: no rule in this engine reads it, but it is what distinguishes e.g. the Kroot Lone-Spear and the Lokhust Lord from their INFANTRY siblings, and a keyword test that guessed from the base size would be wrong
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
    support_weapon = False  # the SUPPORT WEAPON keyword - read by game/branching_fates.py's and game/word_of_the_phoenix.py's exclusions. Set by the three Aeldari platform profiles
    psychic_communion = False  # Warlock Conclave's own ability: each Warlock's Destructor gains +1 A and +1 S per other friendly AELDARI PSYKER model within 6" of it, max +2 - see game/psychic_communion.py
    protect = False  # Warlock Conclave's own ability: while a FARSEER leads the unit, attacks targeting it subtract 1 from the Wound roll - see game/protect.py
    farseer = False  # the FARSEER keyword - read by game/protect.py. Kept separate from `psyker` because Protect names this keyword specifically: the Farseer and Eldrad Ulthran are FARSEER, while the Warlock Conclave is PSYKER but not
    whirling_death = False  # Jain Zar's own ability: while she leads a unit, its Advance is not rolled - a flat +6" to the Move characteristic for the phase instead - see game/whirling_death.py
    storm_of_silence = False  # Jain Zar's own ability: her attacks may re-roll the Wound roll against a CHARACTER unit - see game/storm_of_silence.py
    tactical_acumen = False  # Asurmen's own ability: while he is leading a unit, that unit may make a 6" Normal move after it shoots, at the cost of its charge - see game/tactical_acumen.py
    hand_of_asuryan = False  # Asurmen's own ability: once per battle, his Bloody Twins gains Damage 3, [ANTI-INFANTRY 5+] and [DEVASTATING WOUNDS] until end of phase - see game/hand_of_asuryan.py
    war_construct = False  # Wraithguard's own ability: this unit may shoot in a turn in which it Fell Back - the same 09.07 exception Crisis Starscythe's Battlesuit Support System grants, read at game/shooting.py's available_shooting_types()
    psychic_guidance = False  # Wraithguard's/Wraithblades' own ability: while within 12" of a friendly AELDARI PSYKER model, Ld becomes 6+ and every attack gets +1 to Hit - see game/psychic_guidance.py
    psychic_guidance_characteristics = False  # the Wraithlord's variant of the same printed name: Ld becomes 6+ and the BS/WS characteristics of this model's weapons improve by 1, rather than the Hit ROLL being modified - see game/psychic_guidance.py
    malevolent_souls = False  # Wraithblades' own ability: a model destroyed by a MELEE attack that has not fought this phase stays up on a 3+, strikes back, and is then removed - see game/malevolent_souls.py
    support_weapon_toughness = False  # Support Weapon Platforms' "Support Weapon": while the model's unit contains one or more OTHER models, it has Toughness 3 - folded into game/squad.py's attached_unit_toughness(), next to the Gretchin Runtherd override that answers the same question
    cannot_embark = False  # "cannot embark within a TRANSPORT" printed on the model itself (Support Weapon Platforms, and any unit one has joined) - read by game/transport.py
    structural_collapse = False  # the D-cannon Platform's own ability: re-roll a Damage roll of 1 with its D-cannon - see game/structural_collapse.py
    monofilament_snare = False  # the Shadow Weaver Platform's own ability: a hit enemy unit is snared and bleeds mortal wounds when it moves - see game/monofilament_snare.py
    sonic_destruction = False  # the Vibro Cannon Platform's own ability: S/AP/D improve by 1 per OTHER friendly platform that shot the same target this phase - see game/sonic_destruction.py
    reavers_of_the_void = False  # Corsair Voidreavers' own ability: automatic re-roll of Hit rolls of 1, or the WHOLE roll instead against a target in range of an objective - see game/reavers_of_the_void.py
    piratical_raiders = False  # Corsair Voidscarred's own ability: [LETHAL HITS] and [PRECISION] against one enemy unit chosen at the start of the battle - see game/piratical_raiders.py
    channeller_stones = False  # the Soul Weaver's wargear: once per turn the first failed save in its unit takes Damage 0 - see game/channeller_stones.py
    raid_and_run = False  # Corsair Skyreavers' own ability: a D3+3" Normal or Fall Back move at the end of the Fight phase - see game/raid_and_run.py
    aethersense = False  # Kharseth's own ability: enemy Reserves cannot arrive within 12" of this model - see game/aethersense.py
    fury_of_the_void = False  # Kharseth's own ability: a unit his gun hits is RIVEN, and Aeldari attacks against it get +1 Strength - see game/fury_of_the_void.py
    piratical_hero = False  # Prince Yriel's own ability: while leading, the unit's attacks get [SUSTAINED HITS 1] and +1 to Hit - see game/piratical_hero.py
    prince_of_corsairs = False  # Prince Yriel's own ability: redeploy up to three AELDARI units after both armies have deployed - see game/prince_of_corsairs.py
    hallucinogen_grenades = False  # the Starfangs' own ability: grant Stealth to a friendly AELDARI INFANTRY unit for the opponent's Shooting phase - see game/hallucinogen_grenades.py
    mistshield = False  # Corsair wargear: the bearer has a 4+ invulnerable save - read by game/invulnerable_save.py
    faolchu = False  # Corsair wargear: ranged weapons in the bearer's unit have [IGNORES COVER] - see game/faolchu.py
    on_the_hunt = False  # the Dragon Knights' own ability: a Fall Back move does not stop them shooting or charging - the FOURTH printed wording of that exception, read at the same gates as Battlesuit Support System
    agile_reach = False  # the Dragon Knights' own ability: an UNENGAGED model within 3" of an enemy engaged with its unit may still target that enemy - see game/agile_reach.py
    drakolithe = False  # Dragon Knights' and the Leystalker's own ability: a token-limited reactive mortal wound when an enemy ends a move within 8" - see game/drakolithe.py
    blade_of_the_clans = False  # the Clanblade's own ability: its unit's melee attacks have [SUSTAINED HITS 1] - see game/blade_of_the_clans.py
    cornered_prey = False  # the Clanblade's own ability: an enemy falling back from it must use Desperate Escape - see game/cornered_prey.py
    panicked_quarry = False  # the Leystalker's own ability: a non-MONSTER/VEHICLE unit it hit takes a Battle-shock test at -1 - see game/battle_shock_after_shooting.py
    elemental_ensnarement = False  # the Stonesinger's own ability: an enemy MONSTER/VEHICLE unit is ENSNARED (-2" M, and cannot be pinned) - see game/elemental_ensnarement.py
    aspect_training = False  # the Autarch's own ability: it gains Fights First while leading HOWLING BANSHEES, and Infiltrators/Scouts 7"/Stealth while leading STRIKING SCORPIONS - see game/aspect_training.py
    superlative_strategist = False  # the Autarch's own ability: while leading a unit, re-roll its Advance rolls and any roll made for it during an Agile Manoeuvre - see game/superlative_strategist.py
    path_of_command = False  # both Autarchs' own ability: once per battle round, reduce by 1CP the cost of a Stratagem used on this model's unit - see game/path_of_command.py
    indomitable_strength_of_will = False  # the Autarch Wayleaper's own ability: spending a Battle Focus token on an Agile Manoeuvre for the led unit refunds it on a 3+ - see game/indomitable_strength_of_will.py
    harvester_of_souls = False  # Maugan Ra's own ability: when the led unit fires everything at one target, nearby enemy units are struck by explosive debris - see game/harvester_of_souls.py
    face_of_death = False  # Maugan Ra's own ability: a unit he hits takes a Battle-shock test at -1 - see game/face_of_death.py
    runes_of_fortune = False  # the standalone Warlock's own ability: an enemy charge that selects this unit as a target subtracts 2 from the Charge roll - see game/runes_of_fortune.py
    spiritseer_lone_operative = False  # the Spiritseer's own ability: Lone Operative while within 3" of a friendly WRAITH CONSTRUCT unit - see game/spiritseer.py
    spirit_mark = False  # the Spiritseer's own ability: one friendly WRAITH CONSTRUCT unit gains [SUSTAINED HITS 1] against one marked enemy unit - see game/spiritseer.py
    tears_of_isha = False  # the Spiritseer's own ability: return a destroyed model to, or heal, a friendly WRAITH CONSTRUCT unit each Command phase - see game/spiritseer.py
    misfortune = False  # the Farseer Skyrunner's own ability: a marked enemy unit subtracts 1 from ITS OWN Wound rolls - see game/misfortune.py
    crystal_matrix = False  # the Fire Prism's own ability: one Hit-roll re-roll AND one Wound-roll re-roll per shooting activation - see game/crystal_matrix.py
    monofilament_web = False  # the Night Spinner's own ability: a unit its doomweaver hit is PINNED (-2 Move, -2 Charge) until the start of your next turn - see game/monofilament_web.py
    harassment_fire = False  # the Vypers' own ability: a unit they hit is SUPPRESSED (-1 to its Hit rolls) - the same status Suppression Volley applies, see game/suppression.py
    fated_hero = False  # the Wraithlord's own ability: one of INFANTRY/MONSTER/MOUNTED/VEHICLE is chosen at the start of the battle, and attacks against a unit with it re-roll Hit and Wound rolls of 1 - see game/fated_hero.py
    # --- The Ynnari triumvirate (see game/ynnari_abilities.py and its two
    # stateful siblings). Declared HERE rather than only on the three
    # profiles because attached_units.leader_ability() reads the flag with a
    # bare getattr() - an undeclared name is an AttributeError on whatever
    # model happens to be checked first, not a False.
    way_of_the_blade = False  # The Visarch: while LEADING, that unit has Fights First (24.13) - folded into squad_has_fights_first()
    yvraines_champion = False  # The Visarch: while LEADING, the OTHER CHARACTER models in that unit have Feel No Pain 4+
    word_of_the_phoenix = False  # Yvraine: while LEADING, a Command-phase 2+ returns up to D3+1 destroyed bodyguards - see game/word_of_the_phoenix.py
    herald_of_ynnead = False  # Yvraine: a start-of-Fight-phase mark; friendly AELDARI re-roll a Wound roll of 1 against it until the end of the phase
    inevitable_death = False  # The Yncarne: once in each opponent's turn it teleports to where a destroyed friendly AELDARI unit fell - see game/inevitable_death.py
    ethereal_form = False  # The Yncarne: regains up to D3 lost wounds each time it destroys an enemy unit
    wraith_construct = False  # the WRAITH CONSTRUCT keyword - a TRANSPORT counts each such model as 2 (Falcon's printed line), see game/transport.py's _model_capacity_cost()
    fire_support = False  # the Falcon's own ability: after this model shoots, one enemy unit it hit is marked, and units that disembarked from it this turn may re-roll Wound rolls against that unit until end of turn - see game/fire_support.py
    assured_destruction = False  # Fire Dragons' own ability: in YOUR Shooting phase, a ranged attack against a MONSTER or VEHICLE unit may re-roll its Hit roll, its Wound roll and its Damage roll - see game/assured_destruction.py
    aspect_shrine = False  # ASPECT WARRIORS wargear: this unit may take 1 Aspect Shrine token per 5 models, each of which can once per battle change one Hit or Wound roll made for a non-CHARACTER model in it to an unmodified 6 - see game/aspect_shrine.py
    bladestorm = False  # Dire Avengers' own ability: this unit's ranged weapons have [SUSTAINED HITS 1] while targeting an enemy unit within half range - see game/bladestorm.py
    invulnerable_save_vs_ranged = None  # an invulnerable save that applies only against RANGED attacks - the mirror of invulnerable_save_vs_melee below, and the shape Rangers and Shroud Runners print ("INSV 5+ * Against ranged attacks only"). Unlike the Banshees' clause this is usually the ONLY save the model has, so invulnerable_save stays "-" and this carries it. Read by game/invulnerable_save.py
    invulnerable_save_vs_melee = None  # a BETTER invulnerable save that applies only against melee attacks, e.g. Howling Banshees' printed "5+, improved to 4+ against melee attacks". None = no such clause, the plain invulnerable_save applies to everything. Read by game/invulnerable_save.py, which gets the attack type from the weapon the Save roll is being made against
    mandiblasters = False   # Striking Scorpions' own ability: after this unit made a Charge move this turn, its melee attacks score a Critical Hit on an unmodified 5+ - see game/crit_hit.py
    serpent_shield = False  # Serpent's Scale Platform's wargear: every model in the BEARER'S UNIT gets a 5+ invulnerable save - read live (so it ends with the bearer) by game/invulnerable_save.py
    crewed_platform = False  # marks a model that is a crew-served platform: when its unit runs out of surviving `platform_crew` models, every model with this flag in that unit is destroyed too (Guardian Defenders' "Crewed Platform") - see game/crewed_platform.py
    platform_crew = False   # marks a model that COUNTS as crew for the above. Two flags rather than "anything that is not a platform", because the rule names the crew model specifically: a CHARACTER attached under 19.01 is neither, so it cannot keep an abandoned platform alive
    battle_focus = False  # Aeldari (ASURYANI) army rule "Battle Focus" - user-supplied, not a core rulebook rule. Carries no effect of its own: it marks the unit as eligible to perform an Agile Manoeuvre, and it is also what game/battle_focus.py's qualifying_players() reads to decide whose army counts as ASURYANI (this engine has no army-faction declaration). Human-only faction, so no AI path reads it
    markerlight = False  # the MARKERLIGHT keyword - see game/greater_good.py's marked_by_markerlight()
    battlesuit = False  # the BATTLESUIT keyword - matters for the Retaliation Cadre detachment's Bonded Heroes rule, see game/retaliation_cadre.py
    starflare_ignition_system = False  # the "Starflare Ignition System" Enhancement (user-supplied, 20 pts) is on THIS model - see game/starflare_ignition.py. Per-model rather than per-unit because an Enhancement is given to one model (game/factions/detachment.py's Enhancement docstring: granting one means setting the matching field on that model's own UnitProfile instance, which build_squad() creates fresh per model), even though its EFFECT is on the bearer's whole unit
    # --- T'au Empire detachment Enhancements ---------------------------
    # One flag per engine-wired Enhancement, marking the model (or, for the
    # two "unit only" ones, every model of the unit) that bears it. Set only
    # by game/enhancements.py's grant(), which owns the printed BEARER
    # restriction, the points and the log line; the registry there names the
    # module that reads each flag. Per-model rather than per-unit because an
    # Enhancement is given to one model (game/factions/detachment.py's
    # Enhancement docstring), even where its EFFECT covers the bearer's whole
    # unit - and because rule 19.04 then means "the bearer died, the unit no
    # longer has it" for free.
    internal_grenade_racks = False  # Retaliation Cadre - see game/enh_internal_grenade_racks.py
    prototype_weapon_system = False  # Retaliation Cadre - see game/enh_prototype_weapon_system.py
    puretide_engram_neurochip = False  # Retaliation Cadre - see game/enh_puretide_neurochip.py. NOT Commander Farsight's "Puretide's Teachings" (game/puretide.py), which is a different rule printed under a similar name - named after its own Enhancement, per this repo's rename-a-lying-name rule
    exemplar_of_the_kauyon = False  # Kauyon - see game/enh_exemplars.py
    precision_of_the_patient_hunter = False  # Kauyon - see game/enh_precision_patient_hunter.py
    solid_image_projection_unit = False  # Kauyon - see game/enh_solid_image_projection.py
    through_unity_devastation = False  # Kauyon - see game/enh_guided_keyword_grants.py
    coordinated_exploitation = False  # Mont'ka - see game/enh_guided_keyword_grants.py
    exemplar_of_the_montka = False  # Mont'ka - see game/enh_exemplars.py
    strategic_conqueror = False  # Mont'ka - see game/enh_strategic_conqueror.py
    strike_swiftly = False  # Mont'ka - see game/enh_strike_swiftly.py
    thermoneutronic_projector = False  # Experimental Prototype Cadre - see game/enh_prototype_weapons.py
    plasma_accelerator_rifle = False  # Experimental Prototype Cadre - see game/enh_prototype_weapons.py
    supernova_launcher = False  # Experimental Prototype Cadre - see game/enh_prototype_weapons.py
    negation_emitters = False  # Advanced Acquisition Cadre - see game/enh_negation_emitters.py. Unit-level: every model of the STEALTH BATTLESUITS unit carries it
    unmasking_suite = False  # Advanced Acquisition Cadre - see game/enh_unmasking_suite.py. Unit-level, like negation_emitters above
    student_of_kauyon = False  # Auxiliary Cadre - see game/enh_student_of_kauyon.py
    admired_leader = False  # Auxiliary Cadre - see game/enh_admired_leader.py
    orks = False  # this model is an Orks-Faction model - matters for the War Horde detachment's Get Stuck In rule, see game/war_horde.py. No generic per-model Faction tracking exists in this engine (same documented gap as Bonded Heroes' own "is this T'au Empire" note in game/retaliation_cadre.py); unlike `battlesuit` there's no existing keyword this could piggyback on, so it's its own dedicated flag
    gretchin = False  # the GRETCHIN keyword - matters for the Runtherd ability's "if it contains one or more Gretchin models" check, see UnitProfile.runtherd_shares_gretchin_toughness/squad.py's attached_unit_toughness()
    runtherd_shares_gretchin_toughness = False  # Gretchin datasheet's own "Runtherd" ability (user-supplied, not a core rule, confusingly named the same as the model line it affects): while its unit contains 1+ living Gretchin models, this model's own Toughness counts as 2 for wound-roll purposes - see squad.py's attached_unit_toughness()
    thievin_scavengers = False  # Gretchin datasheet's own "Thievin' Scavengers" ability (user-supplied, not a core rule): at the start of your Movement phase, roll 1D6 per objective you control with a qualifying unit in range, gain 1CP if any roll is 4+ - see game/thievin_scavengers.py. User: "diese Ability wird noch öfters kommen" - a shared flag (same reuse pattern as `fieldcraft`), not Gretchin-exclusive
    explosives = False  # the EXPLOSIVES keyword - matters for the Explosives stratagem (15.05)
    grenades = False  # the GRENADES keyword - same as explosives for 15.05's "EXPLOSIVES/GRENADES" target
    deadly_demise = None  # Deadly Demise X value (rule 24.08), None = no ability
    deadly_demise_notation = None  # game/dice_notation.py's DiceNotation, e.g. D3() for a printed "Deadly Demise D3" - None means `deadly_demise` above is a real fixed X, used as-is; when set, `deadly_demise` is just a documentation leftover and the actual mortal-wound count is rolled for real by game/deadly_demise.py's DeadlyDemiseController once the D6 detonation roll succeeds
    feel_no_pain_vs_mortal_wounds = "-"  # Broadside Battlesuits' "Advanced Armour": a Feel No Pain threshold that applies ONLY against mortal wounds - the first conditional FNP source here, folded into game/feel_no_pain.py's current_feel_no_pain() behind its `mortal` flag; see game/advanced_armour.py
    fireknife = False  # Crisis Fireknife Battlesuits' own ability: automatic re-roll of ranged Hit rolls of 1, upgraded to the whole roll against a target at its Starting Strength - a ones-or-whole source, so it registers in game/reroll_scope.py; see game/fireknife.py
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
    burning_lance = False  # Fuegan's own ability: while he is LEADING a unit, Melta weapons in that unit add 6" to their Range characteristic - see game/burning_lance.py / game/weapon_range.py
    unquenchable_resolve = False  # Fuegan's own ability: the first time this model is destroyed it rolls a D6 at the end of the phase and returns on a 2+ - see game/unquenchable_resolve.py
    crystalline_targeting = False  # War Walkers' own ability: after this unit shoots, every friendly AELDARI attack against one unit it hit improves its AP by 1 until the end of the phase - see game/crystalline_targeting.py
    wave_serpent_shield = False  # Wave Serpent's own ability: -1 to the Wound roll of any ranged attack whose Strength is greater than this model's Toughness - see game/wave_serpent_shield.py
    grenade_pack_flyover = False  # Swooping Hawks' own ability: once per turn in your Movement phase, on being set up or ending a move, D6 per model at 4+ for 1 mortal wound each (max 6) against an enemy unit within 8" - see game/grenade_pack_flyover.py
    cloudstrider = False  # Baharroth's own ability, in two halves - see game/cloudstrider.py
    cry_of_the_wind = False  # Baharroth's own ability: each time this model is set up, until the end of the turn its ranged attacks score a Critical Hit on any successful unmodified Hit roll - see game/crit_hit.py
    path_of_the_outcast = False  # Rangers' own ability: in the opponent's Movement phase, when an enemy unit ends a move within 8", an unengaged unit with this may make a D6" Normal move - see game/path_of_the_outcast.py
    target_acquisition = False  # Shroud Runners' own ability: after this unit shoots, one enemy unit hit by a LONG RIFLE attack cannot have the Benefit of Cover until the end of the phase - see game/target_acquisition.py
    swift_demise = False  # Windriders' "Swift Demise": every ranged attack re-rolls a Hit roll of 1, and against the CLOSEST eligible target the whole Hit roll may be re-rolled instead (one or the other, never both) - see game/swift_demise.py
    ignores_hit_modifiers = False  # "each time a model in this unit makes a ranged attack, you can ignore any or all modifiers to that attack's Ballistic Skill characteristic and any or all modifiers to the Hit roll" - printed under TWO names so far (Riptide Battlesuit's "Weapon Support System" wargear ability, Dark Reapers' "Inescapable Accuracy"), which is why the flag is named after the EFFECT rather than either datasheet. Identical wording, and identical handling, to rule 24.29's [PSYCHIC] half; see game/shooting.py's _hit_modifiers(). The "modifiers to Ballistic Skill" half needs nothing extra here: this engine applies both to the same hit threshold
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
    joins_without_leader_slot = False  # Warlock Conclave's LEADER ability is printed as a JOIN with its OWN restriction ("a unit cannot have more than one WARLOCK CONCLAVE unit joined to it") rather than as an ordinary attachment, so 19.01's one-leader-per-bodyguard default is not what limits it. Read by game/attached_units.py's can_attach(); the direction matters and is asymmetric on purpose - see _join_not_bound_by_leader_slot() there
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

    # --- Aeldari detachment Enhancements ---
    # One flag per Enhancement, read by the game/enh_*.py module named
    # beside it. Same shape as the T'au block above.

    aspect_of_murder = False  # Aspect of Murder (Aspect Host) - see game/enh_*.py
    mantle_of_wisdom = False  # Mantle of Wisdom (Aspect Host) - see game/enh_*.py
    shimmerstone = False  # Shimmerstone (Aspect Host) - see game/enh_*.py
    strategic_savant = False  # Strategic Savant (Aspect Host) - see game/enh_*.py
    craftworlds_champion = False  # Craftworld's Champion (Guardian Battlehost) - see game/enh_*.py
    ethereal_pathway = False  # Ethereal Pathway (Guardian Battlehost) - see game/enh_*.py
    protector_of_the_paths = False  # Protector of the Paths (Guardian Battlehost) - see game/enh_*.py
    breath_of_vaul = False  # Breath of Vaul (Guardian Battlehost) - see game/enh_*.py
    phoenix_gem = False  # Phoenix Gem (Warhost) - see game/enh_*.py
    timeless_strategist = False  # Timeless Strategist (Warhost) - see game/enh_*.py
    gift_of_foresight = False  # Gift of Foresight (Warhost) - see game/enh_*.py
    psychic_destroyer = False  # Psychic Destroyer (Warhost) - see game/enh_*.py
    firstdrawn_blade = False  # Firstdrawn Blade (Windrider Host) - see game/enh_*.py
    mirage_field = False  # Mirage Field (Windrider Host) - see game/enh_*.py
    seersight_strike = False  # Seersight Strike (Windrider Host) - see game/enh_*.py
    echoes_of_ulthanesh = False  # Echoes of Ulthanesh (Windrider Host) - see game/enh_*.py
    light_of_clarity = False  # Light of Clarity (Spirit Conclave) - see game/enh_*.py
    stave_of_kurnous = False  # Stave of Kurnous (Spirit Conclave) - see game/enh_*.py
    rune_of_mists = False  # Rune of Mists (Spirit Conclave) - see game/enh_*.py
    higher_duty = False  # Higher Duty (Spirit Conclave) - see game/enh_*.py
    spirit_stone_of_raelyth = False  # Spirit Stone of Raelyth (Armoured Warhost) - see game/enh_*.py
    guiding_presence = False  # Guiding Presence (Armoured Warhost) - see game/enh_*.py
    camouflaged_snipers = False  # Camouflaged Snipers (Path Of The Outcast) - see game/enh_*.py
    assassins_eye = False  # Assassins' Eye (Path Of The Outcast) - see game/enh_*.py
    lucid_eye = False  # Lucid Eye (Seer Council) - see game/enh_*.py
    runes_of_warding = False  # Runes of Warding (Seer Council) - see game/enh_*.py
    stone_of_eldritch_fury = False  # Stone of Eldritch Fury (Seer Council) - see game/enh_*.py
    torc_of_morai_heg = False  # Torc of Morai-Heg (Seer Council) - see game/enh_*.py


    # --- Necrons (game/factions/necrons.py) ---
    noble = False  # the NOBLE keyword - matters because Lychguard's Guardian Protocols names it specifically ("while a NOBLE model is leading this unit"), the same reason `farseer` above is kept separate from `psyker`; see game/guardian_protocols.py
    reanimation_protocols = False  # the NECRONS army rule: at the end of your Command phase, every unit with this on the battlefield heals D3 wounds, and the core "heal" rule (02.02.04) turns surplus into REVIVED destroyed models (01.02.03) - see game/reanimation_protocols.py
    reanimation_reroll = False  # Necron Warriors' own ability: "each time this unit's Reanimation Protocols activate, you can re-roll the dice to see how many wounds are reanimated" - see game/reanimation_protocols.py
    implacable_eradication = False  # Immortals' own ability: re-roll a Wound roll of 1, or the whole Wound roll when the target is within range of an objective marker - see game/implacable_eradication.py
    wraith_form = False  # Canoptek Wraiths' own ability: after a Normal move, one enemy unit moved over takes a D6 per model in this unit, 1 mortal wound per 4+ - see game/wraith_form.py
    overwhelming_obliteration = False  # Doomsday Ark's own ability: if this model Remains Stationary, its doomsday cannon has [DEVASTATING WOUNDS] until the end of the turn - see game/overwhelming_obliteration.py
    hard_wired_for_destruction = False  # Lokhust Destroyers' own ability: re-roll a Hit roll of 1 against the closest eligible target, or the whole Hit roll if that target is within range of an objective marker the opponent controls - see game/destroyer_cult.py
    optimised_for_slaughter = False  # Lokhust Heavy Destroyers' own ability: re-roll a Wound roll of 1, with the enmitic exterminator against non-MONSTER/VEHICLE and the gauss destructor against MONSTER/VEHICLE - a per-WEAPON condition, unlike the flags above - see game/destroyer_cult.py
    whirling_onslaught = False  # Skorpekh Destroyers' own ability: re-roll a melee Hit roll of 1, or the whole Hit roll if this unit made a Charge move this turn - see game/destroyer_cult.py
    guardian_protocols = False  # Lychguard's own ability: while a NOBLE model leads this unit, subtract 1 from the Wound roll of any attack whose Strength exceeds this unit's Toughness - mechanically the Wave Serpent Shield, so it reads the same _wound_modifiers(strength=) hook; see game/guardian_protocols.py
    driven_by_hatred = False  # Lokhust Lord's own ability: each time THIS MODEL attacks a Below Half-strength unit, both the Hit and the Wound roll may be re-rolled - the fourth DESTROYER CULT re-roll and the only per-MODEL one; see game/destroyer_cult.py
    nanoscarab_amulet = False  # Lokhust Lord wargear: Feel No Pain 5+ on the BEARER. A per-token grant set by the Gear item, so this default only exists to keep getattr honest; see game/feel_no_pain.py
    united_in_destruction = False  # Skorpekh Lord's own ability: while this model leads a unit, melee weapons equipped by models in that unit gain [LETHAL HITS] - a FightController._adjusted_weapon() chain entry; see game/united_in_destruction.py
    crimson_harvest = False  # Skorpekh Lord's own ability: each time this model ends a Charge move, one enemy unit in Engagement Range suffers D3 (or D3+3 on a 6) mortal wounds - fired from ChargeController.on_charge_move_finished; see game/mortal_wound_abilities.py
    my_will_be_done = False  # Overlord's own ability: once per battle round, reduce by 1 the CP cost of a Stratagem targeting this model's unit - a StratagemController.cost_discounts collaborator, see game/my_will_be_done.py
    damage_reduction = 0  # "subtract N from the Damage characteristic of that attack" as a flat per-model reduction (Overlord's Implacable Resilience, Void Dragon's Necrodermis - both print N=1); 0 = no such ability. Mortal wounds are excluded, exactly as game/molten_form.py's halving is; see game/damage_reduction.py
    leading_ranged_crit_on_5 = False  # while this model is LEADING a unit (19.01), ranged attacks by that unit score a Critical Hit on an unmodified 5+ - a leader ability, so read with attached_units.leader_ability(). TWO datasheets print this under two names (Plasmancer "Harbinger of Destruction", Lokhust Lord "Destroyer Cult"), which is why the flag is named for the mechanic; see game/crit_hit.py
    living_lightning = False  # Plasmancer's own ability: in your Shooting phase, one enemy unit within 18" and visible takes four D6, 1 mortal wound per 4+ - see game/mortal_wound_abilities.py
    rites_of_reanimation = False  # Technomancer's own ability: while this model is LEADING a unit (19.01), models in that unit have Feel No Pain 5+ - one more fold in game/feel_no_pain.py's current_feel_no_pain()
    armour_hunter = False  # Hammerhead Gunship's own ability: +1 to the Hit roll against a MONSTER or VEHICLE - the HIT half of Tank Hunters and nothing else, so it is its own flag read by the same modifier helper; see game/armour_hunter.py
    targeting_array = False  # Hammerhead and Sky Ray Gunships' own ability: once per shooting activation, re-roll ONE Hit or ONE Wound die - a single-die re-roll like rule 15.02's Command Re-roll, with a panel button instead of CP; see game/targeting_array.py
    velocity_tracker = False  # Sky Ray Gunship's own ability: re-roll the Hit roll against a target that can FLY - a ShootingController._hit_reroll_reason() entry; see game/velocity_tracker.py
    drone_harassment = False  # Piranhas' own ability: at the end of your Movement phase, one enemy unit within 12" must take a Battle-shock test; see game/drone_harassment.py
    hyperspace_hunters = False  # Deathmarks' own ability: once per turn, in the Reinforcements step of the opponent's Movement phase, this unit may shoot an enemy unit that just arrived from Reserves within 18" - a full reactive activation restricted to that one target, see game/hyperspace_hunters.py
    flesh_hunger = False  # Flayed Ones' own ability: melee attacks against a Below Half-strength target turn every successful Hit roll into a Critical Hit. NOT a fixed number - the crit threshold IS the hit threshold, the same shape as Baharroth's Cry of the Wind; see game/crit_hit.py
    bound_creation = False  # Cryptothralls' own ability: while this unit is in the same unit as a CRYPTEK model, THAT model has Feel No Pain 4+. The arrow points from bodyguard to leader, which is the opposite of every other grant here - see game/cryptothralls.py
    systematic_vigour = False  # Cryptothralls' own ability: a model destroyed by a melee attack that has not fought this phase stays on the board on a 2+ and fights after the attacker finishes. The third consumer of game/fight_after_death.py
    cryptek_retinue = False  # Cryptothralls' own rule: at Declare Battle Formations this whole UNIT may join one other unit being led by a CRYPTEK INFANTRY model. The THIRD attachment role (attached_units.RETINUE) and the only one where a non-character unit joins - see game/cryptothralls.py
    evasion_engrams = False  # Tomb Blades' own ability: after this unit has shot it may make a 6" Normal move, at the cost of its charge. The FOURTH of the Tactical Acumen shape, and the one with NO Engagement Range clause printed - see game/evasion_engrams.py
    nebuloscope = False  # Tomb Blades wargear: ranged weapons equipped by the BEARER gain [IGNORES COVER]. A per-token grant set by the Gear item, so this default only exists to keep getattr honest; see game/tomb_blade_wargear.py
    shadowloom = False  # Tomb Blades wargear: the BEARER has Stealth. Per-token like the two around it - and per rule 24.33 the UNIT only has Stealth if every model does, which is what makes buying one meaningful and buying three not
    shieldvanes = False  # Tomb Blades wargear: the BEARER has Sv3+ and M8". A TRADE, not an upgrade - the save improves and the move worsens - so both halves are overrides
    timesplinter_mantle = False  # Chronomancer's own ability, HALF of it: "melee attacks that target this unit have -1 to Hit rolls". A DEFENDER-side melee malus, so it is a FightController._hit_modifiers() entry read off the TARGET squad - the same shape game/forewarned.py already sits in. The other half of the printed ability is plain `stealth` above; see game/timesplinter_mantle.py
    chronometron = False  # Chronomancer's own ability: after this model's unit has shot, if it is not in Engagement Range, it may make a 5" Normal move and then cannot declare a charge. Asurmen's Tactical Acumen one number apart, plus Fire and Fade's engagement clause - see game/chronometron.py
    nightmare_shroud = False  # Psychomancer's own ability (Aura): in the Battle-Shock step of your opponent's Command phase, an enemy unit BELOW its Starting Strength within 6" must take a Battle-shock test at -1 - see game/psychomancer.py
    harbinger_of_despair = False  # Psychomancer's own ability: once per turn, at the start of any of five phases, one enemy unit within 18" must take a Battle-shock test at -1. Its sibling above shares the -1 and the forced test; only the trigger differs - see game/psychomancer.py
    master_chronomancer = False  # Orikan The Diviner's own ability: while this model is LEADING a unit (19.01), models in that unit have a 4+ invulnerable save - one more _better() fold in game/invulnerable_save.py, read with attached_units.leader_ability()
    the_stars_are_right = False  # Orikan The Diviner's own ability: once per battle, at the start of the Fight phase, TRIPLE the Attacks and Strength of his Staff of Tomorrow and make every successful Wound roll a Critical Wound, until the end of the phase - see game/the_stars_are_right.py
    inescapable_death = False  # Hexmark Destroyer's own ability: once per TURN a unit with this ability may be targeted with Fire Overwatch for 0CP even if that Stratagem was already used this phase, and any Fire Overwatch on it hits on unmodified 2+ instead of 15.09's flat 6 - see game/inescapable_death.py
    multi_threat_eliminator = False  # Hexmark Destroyer's own ability: once per turn, after an enemy unit has shot a friendly NECRONS unit within 3" of this model, this model shoots back at that unit as if it were your Shooting phase - a ShootingController.start_reactive_shooting() consumer, the same shape as Hyperspace Hunters and Kroot Packmates; see game/multi_threat_eliminator.py
    tunnelling_horrors = False  # Ophydian Destroyers' own ability: at the end of the opponent's turn an unengaged unit may take itself into Strategic Reserves and MUST make an ingress move in its next Movement phase - Airborne Agility's withdrawal plus Unshrouded Truth's round-gate override, one phase later; see game/tunnelling_horrors.py
    protective_disciples = False  # Nekrosor Ammentar's own ability: while within 3" of one or more other friendly DESTROYER CULT units, this model has Lone Operative - the FIFTH conditional grant of that shape, registered in game/conditional_lone_operative.py; see game/nekrosor_ammentar.py
    infectious_murder_madness = False  # Nekrosor Ammentar's own ability (Aura): friendly NECRONS units (excluding MONSTER and TITANIC) within 6" get [SUSTAINED HITS 1] on attacks made by a DESTROYER CULT model or against the closest eligible target - see game/nekrosor_ammentar.py
    prophet_of_destruction = False  # Nekrosor Ammentar's own ability: each time this model destroys an enemy unit, one other friendly DESTROYER CULT unit within 9" re-rolls Wound rolls of 1 until the end of the phase - a death-sweep consumer like Vengeful Stars; see game/nekrosor_ammentar.py
    nullstone_field_generator = False  # Nekrosor Ammentar wargear (Aura): friendly NECRONS units within 6" of the bearer have Feel No Pain 5+ against mortal wounds and Psychic Attacks. The first AURA source in game/feel_no_pain.py, so it is stamped on the Squad once per frame like Nurgle's Gift; see game/nekrosor_ammentar.py
    loping_pounce = False  # Kroot Hounds' own ability: while it is active (set at the start of its owner's Command phase when a friendly KROOT INFANTRY unit is within 6"), this unit may declare a charge in a turn in which it Advanced - the THIRD source of that exception, after Waaagh! and Full Throttle, read at the same gate in game/charge.py; see game/loping_pounce.py
    hunting_hounds = False  # Kroot Hounds' own ability: while within 12" of a friendly KROOT CHARACTER model, this model's Objective Control is 1 instead of its printed 0 - read by game/objectives.py; see game/hunting_hounds.py
    airborne_agility = False  # Vespid Stingwings' own ability: at the end of the opponent's turn, a unit not in Engagement Range may take itself off the board into Strategic Reserves; see game/airborne_agility.py
    kroot_packmates = False  # Krootox Riders' own ability: a reactive shooting activation restricted to the unit that just attacked a nearby KROOT INFANTRY unit - a ShootingController.start_reactive_shooting() consumer, the same shape as Vengeful Stars; see game/kroot_packmates.py
    kroot_linebreakers = False  # Krootox Rampagers' own ability: mortal wounds and a Battle-shock test on ending a Charge move - a ChargeController.on_charge_move_finished consumer, the same hook as the Skorpekh Lord's Crimson Harvest; see game/kroot_linebreakers.py
    bounty_hunters = False  # Kroot Farstalkers' own ability: one enemy unit chosen at the start of the battle takes [LETHAL HITS] and [PRECISION] from this unit's attacks; see game/bounty_hunters.py
    pechra = False  # Kroot Farstalkers' Pech'ra wargear: ranged weapons in the BEARER'S UNIT gain [IGNORES COVER]; see game/bounty_hunters.py
    oversight_drone = False  # Vespid Strain Leader's Oversight Drone wargear: once per battle, [IGNORES COVER] on the unit's ranged weapons until the end of the phase; see game/oversight_drone.py
    failure_is_not_an_option = False  # Ethereal's own ability: while this model is LEADING a unit (19.01), models in that unit have Feel No Pain 5+ - one more fold in game/feel_no_pain.py's current_feel_no_pain(), the twin of rites_of_reanimation below; see game/failure_is_not_an_option.py
    coordinated_leadership = False  # Ethereal's own ability: at the end of your Command phase, roll one D6 - on a 4+ you gain 1CP; see game/coordinated_leadership.py
    structural_analyser = False  # Darkstrider's own ability: while this model is LEADING a unit, +1 to the Wound roll for that unit's ranged attacks - a ShootingController._wound_modifiers() entry; see game/structural_analyser.py
    precise_targeting = False  # Firesight Team's own ability: re-roll the Hit roll against a Spotted unit (game/greater_good.py's is_spotted) - a ShootingController._hit_reroll_reason() entry; see game/precise_targeting.py
    advanced_scouting = False  # Kroot Lone-Spear's own ability: an enemy unit this model's ranged attack HIT may be re-rolled against by every other KROOT model this turn; see game/advanced_scouting.py
    fire_and_fade = False  # Kroot Lone-Spear's own ability: a 6" Normal move after shooting, at the cost of this turn's charge - a MovementController.start_post_shooting_move() consumer, the twin of Asurmen's Tactical Acumen; see game/fire_and_fade.py
    enforcer_commander = False  # Commander in Enforcer Battlesuit's own ability: while this model is LEADING a unit, worsen by 1 the AP of every ranged attack targeting that unit - a game/damage_resolution.py save-threshold entry, the same slot as Ramshackle but Rugged; see game/enforcer_commander.py
    agile_combatant = False  # Commander Shadowsun's own ability: this MODEL is eligible to shoot in a turn in which it Fell Back - the per-model form of battlesuit_support_system above; see game/shooting.py's can_shoot()
    hero_of_the_empire = False  # Commander Shadowsun's own aura: friendly T'AU EMPIRE units within 6" re-roll ranged Hit rolls of 1 - one more automatic-1s source in game/shooting.py; see game/hero_of_the_empire.py
    advanced_guardian_drone = False  # Commander Shadowsun's own wargear: -1 to the Wound roll for ranged attacks that target THE BEARER. The per-MODEL form of guardian_drone above, which is unit-wide - see game/drones.py
    ritual_butchery = False  # Kroot Flesh Shaper's own ability: while this model is LEADING a unit (19.01), melee weapons equipped by models in that unit gain [SUSTAINED HITS 1] - a FightController._adjusted_weapon() chain entry, the twin of united_in_destruction above; see game/ritual_butchery.py
    rites_of_feasting = False  # Kroot Flesh Shaper's own ability: while this model is LEADING a unit, models in that unit have Feel No Pain 6+, improved to 5+ for the rest of the battle once that unit has destroyed an enemy unit in the Fight phase - one more fold in game/feel_no_pain.py's current_feel_no_pain(); see game/rites_of_feasting.py
    war_leader = False  # Kroot War Shaper's own ability: once per battle round, reduce by 1 the CP cost of a Stratagem targeting this model's unit - a StratagemController.cost_discounts collaborator, the same shape as my_will_be_done above; see game/war_leader.py
    root_of_honour = False  # Kroot War Shaper's own ability: once per battle, at the start of any phase, one friendly Battle-shocked KROOT unit within 12" stops being Battle-shocked - see game/root_of_honour.py
    technomancer_repair = False  # Technomancer's own ability: at the end of your Movement phase, one friendly NECRONS model within 6" regains up to D3 lost wounds, once per model per turn - see game/technomancer.py
    matter_absorption = False  # Void Dragon's own ability: at the start of your Shooting phase, one enemy VEHICLE unit within 12" takes D3 mortal wounds on a 2+, and this model regains up to that many lost wounds - see game/mortal_wound_abilities.py
    enslaved_star_god = False  # Void Dragon's own "Enslaved Star God": "this model cannot be your WARLORD". A documented NO-OP - this engine has no Warlord concept at all, the same status as the "ignore vertical distance" abilities
    illuminor = False  # Illuminor Szeras's own ability: while within 3" of one or more OTHER friendly NECRONS units, this model has Lone Operative - a CONDITIONAL form of `lone_operative` above, so it is resolved at read time; see game/illuminor.py
    mechanical_augmentation = 0  # Illuminor Szeras's own Aura, in inches (printed 3", grows to a maximum of 12"): a friendly NECRONS BATTLELINE unit within this range improves its attacks' AP by 1 and worsens the AP of attacks targeting it by 1; 0 = no such aura - see game/mechanical_augmentation.py
    mechanical_augmentation_max = 0  # the ceiling the aura can grow to, in inches (printed 12") - paired with the flag above so the growth rule has a bound to read rather than a literal
    atomic_energy_manipulator = 0  # Illuminor Szeras's own ability, in inches (printed 3"): at the end of the Fight phase, if this model destroyed one or more models this phase, add this much to its Mechanical Augmentation range for the rest of the battle - see game/mechanical_augmentation.py

    # --- Death Guard (game/factions/death_guard.py) ---
    nurgles_gift = False  # the DEATH GUARD army rule "Nurgle's Gift (Aura)": an enemy unit within this model's Contagion Range (6"/9"/12" by battle round) is Afflicted - -1 Toughness plus the chosen Plague. Carried by EVERY Death Guard model, so it doubles as this engine's "is this a DEATH GUARD model" test for the aura; see game/nurgles_gift.py and game/plagues.py
    curse_of_the_walking_pox = False  # Poxwalkers' own ability: each time a POXWALKER model destroys a non-MONSTER/VEHICLE enemy model, one destroyed Poxwalker returns to the unit after it resolves its attacks - see game/curse_of_the_walking_pox.py
    destroyer_hive = False  # Typhus' own ability: while this model is LEADING a unit, melee attacks targeting that unit subtract 1 from the Hit roll - a leader ability, so read with attached_units.leader_ability(); see game/destroyer_hive.py
    eater_plague = False  # Typhus' own PSYCHIC ability: one enemy unit within 18" and visible suffers D6 (or D3+3 on a 6) mortal wounds, and on a 1 his OWN unit suffers D3 - see game/mortal_wound_abilities.py
    gift_of_contagion = False  # Malignant Plaguecaster's own ability: while LEADING a unit, that unit's attacks against an Afflicted target have [SUSTAINED HITS 1] - see game/gift_of_contagion.py
    pestilent_fallout = False  # Malignant Plaguecaster's own ability: after it shoots, one hit enemy INFANTRY unit is enfeebled (-2" Move) until the end of the opponent's next turn - see game/pestilent_fallout.py
    death_guard_defenders = False  # Daemon Prince's own ability: while within 3" of a friendly DEATH GUARD INFANTRY unit, this model has Lone Operative - a CONDITIONAL form of `lone_operative`, resolved at read time exactly like `illuminor`; see game/death_guard_defenders.py
    fevered_strategist = False  # Daemon Prince's own ability: once per battle round, reduce by 1 the CP cost of a Stratagem targeting a friendly DEATH GUARD unit within 12" - a StratagemController.cost_discounts collaborator like My Will Be Done; see game/fevered_strategist.py
    miasma_of_pestilence = False  # Daemon Prince's own Aura: a friendly DEATH GUARD unit within 6" has the Benefit of Cover against ranged attacks - see game/miasma_of_pestilence.py
    lethal_ichor = False  # Chaos Spawn's own ability: each melee attack allocated to this unit may cost the attacking unit a mortal wound on a 4+, up to six dice per attacking unit - see game/lethal_ichor.py
    silent_bodyguard = False  # Deathshroud Terminators' own ability: a CHARACTER model leading this unit has Feel No Pain 4+ - one more fold in game/feel_no_pain.py's current_feel_no_pain()
    death_approaches = False  # Deathshroud Terminators' own ability: their Deep Strike may be set up more than 6" from an Afflicted enemy unit and more than 8" from any other, instead of the usual 9" - see game/death_approaches.py
    scuttling_walker = False  # Defiler's own ability: it moves through models and terrain, may pass through Engagement Range without ending there, and auto-passes Desperate Escape - see game/scuttling_walker.py
    barrage_of_filth = False  # Defiler's own ability: after it shoots, one hit enemy unit cannot have the Benefit of Cover until the end of the phase - the seventh consumer of on_squad_finished_shooting; see game/barrage_of_filth.py
    hovering_death = False  # Foetid Bloat-drone's own ability: eligible to shoot and declare a charge in a turn in which it Fell Back - see game/hovering_death.py
    tank_hunters_ranged_only = False  # Myphitic Blight-hauler's "Tank Hunters": the SAME +1 Hit/+1 Wound against MONSTER/VEHICLE as `tank_hunters` above, but its printed text adds "in your Shooting phase" where the Ork version has no phase clause - so a separate flag rather than a reuse, or this model would silently get the bonus with its Gnashing Maw too. See squad.py's tank_hunters_modifiers()
    spore_laced_shock_waves = False  # Plagueburst Crawler's own ability: its Plagueburst mortar rolls a D6 for the target and every enemy unit within 3" of it (+1 if Afflicted), and each 6+ takes D3 mortal wounds - see game/spore_laced_shock_waves.py

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


class KrootShaperProfile(UnitProfile):
    """The stat line the Flesh / Trail / War Shaper datasheets SHARE.

    All three print exactly M7" T3 Sv6+ W3 Ld7+ OC1 on a 32mm base, the same
    four core abilities (Infiltrators, Leader, Scouts 7", Stealth), and the
    same KROOT SHAPER keywords - so this is a base class the three subclass,
    rather than three copies that would drift the first time one is corrected.
    Each subclass adds only its own name and its own datasheet's abilities.

    WS/BS are not in the M/T/Sv/W/Ld/OC table (the same convention as every
    other T'au datasheet here). Every one of their weapon rows prints WS2+ and
    BS4+, so both live here and no weapon needs a per-weapon override - the
    contrast is Darkstrider next door, whose two rows disagree.

    Like Kroot Carnivores and for the same reason (they are auxiliaries, and
    the keyword is simply not printed on the datasheet), these do NOT get
    for_the_greater_good or MARKERLIGHT.

    base_radius_in is NOT an assumption here: the datasheets print 32mm."""
    base_radius_in = 0.63   # 32 mm printed base
    movement_in = 7
    weapon_skill = "2+"
    ballistic_skill = "4+"
    toughness = 3
    wounds = 3
    leadership = "7+"
    armor_save = "6+"
    oc = 1
    character = True
    infantry = True
    kroot = True            # the KROOT keyword - see UnitProfile's own note
    infiltrators = True     # rule 24.20
    stealth = True          # rule 24.33
    scouts = 7.0            # "Scouts 7\"" - rule 24.31, read by game/scouts.py
    leader = True           # "Leader: Kroot Carnivores, Kroot Farstalkers" - the pairing is read off the points list's own `leads` table by game/attached_units.py's can_attach()


class KrootFleshShaperProfile(KrootShaperProfile):
    """Datasheet: Kroot Flesh Shaper (T'au Empire).

    Both of its abilities are the "while this model is leading a unit" form
    (24.22), so both are read through attached_units.leader_ability() and both
    bring 19.04's grace window with them."""
    name = "Kroot Flesh Shaper"
    ritual_butchery = True   # this datasheet's own ability, see game/ritual_butchery.py
    rites_of_feasting = True  # this datasheet's own ability, see game/rites_of_feasting.py


class KrootTrailShaperProfile(KrootShaperProfile):
    """Datasheet: Kroot Trail Shaper (T'au Empire).

    Neither of its two abilities is engine-wired, and both are recorded as
    missing on the datasheet's abilities_text (and asserted in
    test_kroot_shapers.py) so that adding either is a visible change:

    - Trail Finding is a REACTIVE move in the opponent's Movement phase,
      triggered by an enemy unit ENDING a move within 8". This engine has the
      reactive-move machinery (MovementController.REACTIVE_MOVE_MODES) but no
      "an enemy just finished a move" hook to hang the offer on - every
      existing reactive move keys off an attack or a charge.
    - Kroot Ambush redeploys two units after deployment and may put them into
      Strategic Reserves regardless of the 50% cap. That is a new step in the
      Pre-game Sequence (03.01), not an ability on a unit."""
    name = "Kroot Trail Shaper"


class KrootWarShaperProfile(KrootShaperProfile):
    """Datasheet: Kroot War Shaper (T'au Empire)."""
    name = "Kroot War Shaper"
    war_leader = True      # this datasheet's own ability, see game/war_leader.py
    root_of_honour = True  # this datasheet's own ability, see game/root_of_honour.py


class EtherealProfile(UnitProfile):
    """Datasheet: Ethereal (T'au Empire) - an INFANTRY CHARACTER with a printed
    invulnerable save, unlike Cadre Fireblade next door.

    WS/BS: the datasheet prints ONE weapon row (Honour stave, WS4+) and no
    ranged weapon at all, so ballistic_skill is never read. It is set to the
    4+ his drones would use rather than left at the class default, so a drone
    granted by his own wargear menu shoots at a real number.

    Note the Ld6+ - better than the 7+ every other T'au infantry model here
    prints, which is the whole point of an Ethereal."""
    name = "Ethereal"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 6
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 3
    wounds = 3
    leadership = "6+"
    armor_save = "5+"
    invulnerable_save = "5+"        # printed INSV 5+
    oc = 1
    character = True
    infantry = True
    for_the_greater_good = True
    leader = True                   # "Leader: Breacher Team, Strike Team"
    failure_is_not_an_option = True  # see game/failure_is_not_an_option.py
    coordinated_leadership = True    # see game/coordinated_leadership.py


class DarkstriderProfile(UnitProfile):
    """Datasheet: Darkstrider (T'au Empire) - EPIC HERO.

    THE FIRST T'AU MODEL WHOSE TWO WEAPON ROWS DISAGREE about skill: the Shade
    prints BS2+ while his close combat weapon prints WS4+. So the profile
    carries the melee value and the Shade carries a per-weapon
    `ballistic_skill` override - the arrangement The Twin Lance introduced and
    the exact opposite of the Kroot Shapers above, whose rows all agree."""
    name = "Darkstrider"
    base_radius_in = 0.63           # 32 mm printed base
    movement_in = 7
    weapon_skill = "4+"
    ballistic_skill = "4+"          # overridden to 2+ by the Shade's own row
    toughness = 3
    wounds = 3
    leadership = "7+"
    armor_save = "4+"
    oc = 1
    character = True
    infantry = True
    epic_hero = True
    markerlight = True              # the MARKERLIGHT keyword
    for_the_greater_good = True
    infiltrators = True             # rule 24.20
    scouts = 7.0                    # "Scouts 7\"" - rule 24.31
    leader = True                   # "Leader: Pathfinder Team"
    structural_analyser = True      # see game/structural_analyser.py
    # Jammer Array ("enemy units set up from Reserves cannot be set up within
    # 12\" of this model") is NOT wired: it is a constraint on the OPPONENT's
    # Reserves placement (20.04), and no ability in this engine has ever
    # restricted where the other player may arrive. Recorded on the datasheet's
    # abilities_text and asserted in test_tau_characters.py.


class FiresightMarksmanProfile(UnitProfile):
    """Datasheet: Firesight Team (T'au Empire).

    ONE MODEL, despite the plural name: the datasheet's own Designer's Note
    says the Marksman and his two sniper drones "are treated as a single model
    for all rules purposes" and that the drones "do not count as models for any
    rules purposes". So the drones are not ModelLines, and their guns are the
    single Longshot pulse rifles row - which is why that weapon's name is
    plural.

    The two ranged rows disagree (rifles BS4+, pulse pistol BS3+), so the
    pistol carries no override and the profile takes the rifles' 4+ - the
    pistol keeps the 3+ its own existing class already prints... which it does
    not, so the profile takes the 4+ and the pistol is handled the same way
    every other shared PulsePistolProfile is. The one row that genuinely
    disagrees with the profile is the melee weapon (WS5+), which carries its
    own override."""
    name = "Firesight Marksman"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 6
    weapon_skill = "4+"             # the melee row prints 5+ and overrides it
    ballistic_skill = "4+"
    toughness = 3
    wounds = 4
    leadership = "7+"
    armor_save = "4+"
    oc = 3
    character = True
    infantry = True
    markerlight = True
    for_the_greater_good = True
    infiltrators = True             # rule 24.20
    stealth = True                  # rule 24.33
    lone_operative = 12.0           # rule 24.24, the printed default range
    precise_targeting = True        # see game/precise_targeting.py


class KrootLoneSpearProfile(UnitProfile):
    """Datasheet: Kroot Lone-Spear (T'au Empire) - the roster's only MOUNTED
    model outside the Aeldari jetbikes.

    base_radius_in is the EQUAL-AREA circle of the printed 90 x 52 mm oval,
    the same conversion the Ghostkeel (105 x 70) and Riptide (120 x 92) already
    use: sqrt(45 * 26) = 34.2 mm radius. Not a table-size decision - the
    printed base is simply not round."""
    name = "Kroot Lone-Spear"
    base_radius_in = 1.3466         # equal-area circle of the 90 x 52 mm oval
    movement_in = 12
    weapon_skill = "3+"             # Kalamandra's bite prints 4+ and overrides it
    ballistic_skill = "3+"          # the blast javelin prints 4+ and overrides it
    toughness = 5
    wounds = 6
    leadership = "7+"
    armor_save = "5+"
    oc = 2
    character = True
    mounted = True
    kroot = True
    stealth = True                  # rule 24.33
    scouts = 7.0                    # "Scouts 7\"" - rule 24.31
    lone_operative = 12.0           # rule 24.24
    advanced_scouting = True        # see game/advanced_scouting.py
    fire_and_fade = True            # see game/fire_and_fade.py


class EnforcerCommanderProfile(UnitProfile):
    """Datasheet: Commander in Enforcer Battlesuit (T'au Empire).

    The slow, armoured Commander: M8" and Sv2+ where the Coldstar is M12"/3+.
    No printed invulnerable save - he can BUY one with the shield generator,
    which is why that wargear item sets it rather than the profile."""
    name = "Commander in Enforcer Battlesuit"
    base_radius_in = 1.181          # 60 mm printed base
    movement_in = 8
    weapon_skill = "4+"             # battlesuit fists' own row
    ballistic_skill = "3+"
    toughness = 5
    wounds = 6
    leadership = "7+"
    armor_save = "2+"
    oc = 2
    character = True
    vehicle = True
    walker = True
    fly = True
    battlesuit = True
    deep_strike = True              # rule 24.09
    for_the_greater_good = True
    leader = True                   # "Leader: the four Crisis Battlesuit datasheets"
    enforcer_commander = True       # see game/enforcer_commander.py


class CommanderShadowsunProfile(UnitProfile):
    """Datasheet: Commander Shadowsun (T'au Empire) - EPIC HERO.

    INFANTRY, not VEHICLE, unlike every other Commander here - which is what
    lets her have Infiltrators and Stealth at all, and is printed on her own
    Keywords line.

    Her two drones are wargear she always carries rather than a menu, so their
    abilities are profile flags rather than Gear items - see the datasheet."""
    name = "Commander Shadowsun"
    base_radius_in = 0.984          # 50 mm printed base
    movement_in = 10
    weapon_skill = "4+"             # battlesuit fists' own row
    ballistic_skill = "2+"          # every ranged row but the pulse pistol
    toughness = 4
    wounds = 6
    leadership = "6+"
    armor_save = "3+"
    invulnerable_save = "5+"        # printed INSV 5+
    oc = 1
    character = True
    infantry = True
    fly = True
    epic_hero = True
    battlesuit = True
    for_the_greater_good = True
    infiltrators = True             # rule 24.20
    stealth = True                  # rule 24.33
    lone_operative = 12.0           # rule 24.24
    agile_combatant = True          # see game/agile_combatant.py
    hero_of_the_empire = True       # see game/hero_of_the_empire.py
    advanced_guardian_drone = True  # her own wargear, see game/drones.py
    # Command-link Drone ("while a friendly T'AU EMPIRE unit is within 6" of
    # the bearer, each time you select that unit as the target of a Stratagem,
    # roll one D6: on a 5+, you gain 1CP") is NOT wired: StratagemController
    # has no per-use hook a listener could hang a roll on, and adding one is a
    # change to the Stratagem flow rather than to this datasheet. Recorded on
    # the datasheet's abilities_text and asserted in test_tau_characters.py.
    # Supreme Commander ("if this model is in your army, it must be your
    # WARLORD") is a documented NO-OP - this engine has no Warlord concept at
    # all, the same status as the Void Dragon's Enslaved Star God.


class KrootHoundProfile(UnitProfile):
    """Datasheet: Kroot Hounds (T'au Empire).

    OC 0 - one of the very few models here with no Objective Control at all,
    which is exactly what Hunting Hounds below exists to fix.

    NOTE THE LEADERSHIP: 8+ on their own datasheet, but 7+ on the two hounds
    printed inside a Kroot Farstalkers unit (FarstalkerHoundProfile below). One
    number, two datasheets, so two classes - a shared one would have to be
    wrong for one of them."""
    name = "Kroot Hound"
    base_radius_in = 0.561          # 28.5 mm printed base
    movement_in = 12
    weapon_skill = "3+"
    ballistic_skill = "4+"          # never read - they carry no ranged weapon
    toughness = 3
    wounds = 1
    leadership = "8+"
    armor_save = "6+"
    oc = 0
    beasts = True                   # the BEASTS keyword - also 13.06's terrain exemption
    kroot = True
    stealth = True                  # rule 24.33
    scouts = 7.0                    # "Scouts 7\"" - rule 24.31
    loping_pounce = True            # this datasheet's own ability, see game/loping_pounce.py
    hunting_hounds = True           # this datasheet's own ability, see game/hunting_hounds.py


class FarstalkerHoundProfile(KrootHoundProfile):
    """The two Kroot Hounds printed inside a Kroot Farstalkers unit.

    Leadership 7+ rather than 8+, and NEITHER of the Kroot Hounds datasheet's
    two abilities - the Farstalkers datasheet prints its own (Bounty Hunters)
    and says nothing about Loping Pounce or Hunting Hounds. Subclassing and
    turning both off is what keeps that visible; a fresh copy of the stat line
    would let the two drift."""
    name = "Kroot Hound (Farstalker)"
    leadership = "7+"
    loping_pounce = False
    hunting_hounds = False


class VespidStingwingProfile(UnitProfile):
    """Datasheet: Vespid Stingwings (T'au Empire).

    INFANTRY and FLY but NOT for_the_greater_good and NOT MARKERLIGHT - the
    Keywords line prints neither, the same auxiliary status the Kroot have."""
    name = "Vespid Stingwing"
    base_radius_in = 0.561          # 28.5 mm printed base
    movement_in = 12
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 4
    wounds = 1
    leadership = "7+"
    armor_save = "4+"
    oc = 1
    infantry = True
    fly = True
    deep_strike = True              # rule 24.09
    airborne_agility = True         # this datasheet's own ability, see game/airborne_agility.py


class VespidStrainLeaderProfile(VespidStingwingProfile):
    """Identical stat line; only this model may take the Oversight Drone."""
    name = "Vespid Strain Leader"
    squad_leader = True


class KrootoxProfile(UnitProfile):
    """The stat line Krootox Riders and Krootox Rampagers SHARE - printed
    identically on both (M7" T6 Sv5+ W5 Ld7+ OC2 on a 50mm base), so a base
    class rather than two copies. Everything that differs between the two
    datasheets is its own ability and its own weapons."""
    base_radius_in = 0.984          # 50 mm printed base
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "4+"
    toughness = 6
    wounds = 5
    leadership = "7+"
    armor_save = "5+"
    oc = 2
    mounted = True
    kroot = True
    grenades = True
    scouts = 7.0                    # "Scouts 7\"" - rule 24.31


class KrootoxRiderProfile(KrootoxProfile):
    name = "Krootox Rider"
    kroot_packmates = True          # this datasheet's own ability, see game/kroot_packmates.py


class KrootoxRampagerProfile(KrootoxProfile):
    name = "Krootox Rampager"
    kroot_linebreakers = True       # this datasheet's own ability, see game/kroot_linebreakers.py


class KrootFarstalkerProfile(UnitProfile):
    """Datasheet: Kroot Farstalkers (T'au Empire) - the rank and file.

    A THREE-LINE unit with only TWO printed stat rows: the Kill-broker shares
    the Farstalkers' row (differing only in base size, 32mm against 28.5mm),
    and the two Kroot Hounds have their own."""
    name = "Kroot Farstalker"
    base_radius_in = 0.561          # 28.5 mm printed base
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "4+"
    toughness = 3
    wounds = 1
    leadership = "7+"
    armor_save = "6+"
    oc = 1
    infantry = True
    kroot = True
    grenades = True
    infiltrators = True             # rule 24.20
    stealth = True                  # rule 24.33
    bounty_hunters = True           # this datasheet's own ability, see game/bounty_hunters.py


class KrootKillBrokerProfile(KrootFarstalkerProfile):
    """Same printed stat row as the Farstalkers, on a bigger base - the one
    characteristic the datasheet gives him of his own."""
    name = "Kroot Kill-broker"
    base_radius_in = 0.63           # 32 mm printed base
    squad_leader = True


class BroadsideShasUiProfile(UnitProfile):
    """Datasheet: Broadside Battlesuits (T'au Empire).

    THE ONLY BATTLESUIT HERE WITHOUT FLY - its Keywords line prints VEHICLE,
    WALKER, BATTLESUIT and nothing else, which together with M5" makes it the
    slowest thing in the T'au list by a wide margin. Not an omission: it is a
    heavy weapons platform, and the missing keyword is what says so.

    Advanced Armour is Feel No Pain 4+ **against mortal wounds only**, which is
    a narrower grant than any other FNP source in this engine - see
    `feel_no_pain_vs_mortal_wounds` below."""
    name = "Broadside Shas'ui"
    base_radius_in = 1.181          # 60 mm printed base
    movement_in = 5
    weapon_skill = "5+"             # crushing bulk's own row
    ballistic_skill = "4+"
    toughness = 6
    wounds = 8
    leadership = "7+"
    armor_save = "2+"
    oc = 2
    vehicle = True
    walker = True
    battlesuit = True
    for_the_greater_good = True
    feel_no_pain_vs_mortal_wounds = "4+"   # "Advanced Armour" - see game/feel_no_pain.py


class BroadsideShasVreProfile(BroadsideShasUiProfile):
    """Identical stat line - the datasheet prints one row for the whole unit,
    like Kroot Carnivores. Only the composition names him separately."""
    name = "Broadside Shas'vre"
    squad_leader = True


class CrisisFireknifeShasUiProfile(UnitProfile):
    """Datasheet: Crisis Fireknife Battlesuits (T'au Empire).

    The same chassis as the Starscythe and Sunforge suits (M10" T5 Sv3+ W4
    Ld7+ OC2 on a 50mm base) - the third of the three Crisis variants, and the
    one three separate LEADER lines have been naming since before it existed.

    Weapon Support System is printed as a UNIT ability here, not as wargear:
    "each time a MODEL IN THIS UNIT makes a ranged attack". So it is the
    profile's own ignores_hit_modifiers, the same field the Riptide's
    identically-named wargear uses - which is exactly why that field is named
    after the EFFECT and not after either datasheet."""
    name = "Crisis Fireknife Shas'ui"
    base_radius_in = 0.984          # 50 mm printed base
    movement_in = 10
    weapon_skill = "5+"             # battlesuit fists' own row
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
    deep_strike = True              # rule 24.09
    for_the_greater_good = True
    ignores_hit_modifiers = True    # "Weapon Support System", printed as a unit ability here
    fireknife = True                # this datasheet's own ability, see game/fireknife.py


class CrisisFireknifeShasVreProfile(CrisisFireknifeShasUiProfile):
    """Identical stat line; only the composition names him separately."""
    name = "Crisis Fireknife Shas'vre"
    squad_leader = True


class HammerheadGunshipProfile(UnitProfile):
    """Datasheet: Hammerhead Gunship (T'au Empire).

    The same hull as the Sky Ray below (M10" T10 Sv3+ W14 Ld7+ OC3 on a 60mm
    flying base, Damaged at 1-5) - two datasheets on one chassis, which is why
    the Sky Ray subclasses this one.

    base_radius_in is the same 2.1" every grav-tank here uses: the printed base
    is 60mm, but the Falcon was raised to a table size by user decision and the
    Devilfish and Wave Serpent already share it. Same hull, same footprint."""
    name = "Hammerhead Gunship"
    base_radius_in = 2.1            # printed 60mm; the established grav-tank table size
    movement_in = 10
    weapon_skill = "5+"             # armoured hull's own row
    ballistic_skill = "4+"
    toughness = 10
    wounds = 14
    leadership = "7+"
    armor_save = "3+"
    oc = 3
    vehicle = True
    fly = True
    for_the_greater_good = True
    damaged_threshold = 5           # "Damaged: 1-5 wounds remaining" - see game/shooting.py
    deadly_demise = 3               # documentation only - see deadly_demise_notation below
    deadly_demise_notation = D3()   # "Deadly Demise D3", rule 24.08
    armour_hunter = True            # this datasheet's own ability, see game/armour_hunter.py
    targeting_array = True          # this datasheet's own ability, see game/targeting_array.py


class SkyRayGunshipProfile(HammerheadGunshipProfile):
    """Datasheet: Sky Ray Gunship (T'au Empire) - the Hammerhead's hull with a
    missile rack instead of a railgun.

    Every characteristic is identical, so it subclasses rather than repeating
    them; what differs is the MARKERLIGHT keyword and which of the two
    re-roll abilities it prints (Velocity Tracker rather than Armour
    Hunter)."""
    name = "Sky Ray Gunship"
    markerlight = True              # the MARKERLIGHT keyword - see game/greater_good.py
    armour_hunter = False
    velocity_tracker = True         # this datasheet's own ability, see game/velocity_tracker.py


class PiranhaProfile(UnitProfile):
    """Datasheet: Piranhas (T'au Empire) - the fast skimmer.

    M14" is the fastest thing in the T'au list, and Scouts 9" is the longest
    Scout move in this engine (every other one is 7" or 8")."""
    name = "Piranha"
    # TABLE SIZE, not the printed one - a user decision (2026-08-30: "die
    # piranhas sind zu gross, die sollten in etwa nur 2/3 so gross sein wie
    # devil fish"), and the fifth of its kind after the Falcon, the Wave
    # Serpent, the Defiler and the three MOUNTED jetbikes.
    #
    # The datasheet prints a 60 mm flying base and so does the Devilfish, so
    # the printed sizes really are identical and 2.1 was faithful to them; what
    # they do not capture is that a Piranha is a fraction of the hull a
    # Devilfish is. Two thirds of the Devilfish's 4.20" is 2.80" across, which
    # is close enough to a 70 mm base to be a plausible table size in its own
    # right.
    #
    # This is a GAMEPLAY number, not a cosmetic one: edge_distance() reads the
    # radius, so Engagement Range, model overlap, coherency and formation
    # packing all move with it - the direction wanted here, since a Piranha on
    # a Devilfish's footprint is exactly the shape this terrain handles worst.
    base_radius_in = 1.4            # printed 60 mm; 2/3 of the Devilfish's 4.20" table size
    movement_in = 14
    weapon_skill = "5+"             # armoured hull's own row
    ballistic_skill = "4+"
    toughness = 7
    wounds = 7
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    vehicle = True
    fly = True
    for_the_greater_good = True
    scouts = 9.0                    # "Scouts 9\"" - rule 24.31, the longest here
    deadly_demise = 1               # "Deadly Demise 1", rule 24.08 - a flat 1, so no notation
    drone_harassment = True         # this datasheet's own ability, see game/drone_harassment.py


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
    ignores_hit_modifiers = True  # printed here as "Weapon Support System" - see game/shooting.py's _hit_modifiers()
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
    # User report: "bei warp spider und avengers kann ich den exarch nicht
    # unterscheiden". There is no separate Exarch art for these datasheets, so
    # the only thing that can tell it apart on the board is the leader ring/label
    # the renderer already draws for every other sergeant-equivalent model -
    # and this flag is what turns that on. The Striking Scorpion and Howling
    # Banshee Exarchs already set it; these three were simply missed.
    squad_leader = True


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
    # User report: "bei warp spider und avengers kann ich den exarch nicht
    # unterscheiden". There is no separate Exarch art for these datasheets, so
    # the only thing that can tell it apart on the board is the leader ring/label
    # the renderer already draws for every other sergeant-equivalent model -
    # and this flag is what turns that on. The Striking Scorpion and Howling
    # Banshee Exarchs already set it; these three were simply missed.
    squad_leader = True


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
    # User report: "bei warp spider und avengers kann ich den exarch nicht
    # unterscheiden". There is no separate Exarch art for these datasheets, so
    # the only thing that can tell it apart on the board is the leader ring/label
    # the renderer already draws for every other sergeant-equivalent model -
    # and this flag is what turns that on. The Striking Scorpion and Howling
    # Banshee Exarchs already set it; these three were simply missed.
    squad_leader = True


class FalconProfile(UnitProfile):
    """Aeldari grav-tank: the faction's first VEHICLE and first TRANSPORT here.

    weapon_skill is not printed on the statline - the Wraithbone hull prints
    its own WS4+, which is a real per-weapon override and the only melee this
    model has, so nothing ever reads a model-level one. Set to match it rather
    than left at the class default, so the two cannot disagree."""
    name = "Falcon"
    # 60 mm flying base is 1.181" by the usual mm/2/25.4 conversion, but the
    # Devilfish - the other grav-tank on the table - does NOT use its own
    # printed base either: it was enlarged to 2.1" on user request. User
    # report: "der falcon ist zu klien. genau so gross machen wie devilfish",
    # so the two now match. Purely cosmetic in the sense that no rule reads a
    # base size directly, but it is NOT free: base_radius_in feeds placement,
    # movement clamping and edge-to-edge distance everywhere, so this Falcon
    # takes up as much room as a Devilfish.
    base_radius_in = 2.1            # matched to DevilfishProfile, not the printed 60 mm
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
    # NO battle_focus. MEASURED against the printed datasheet: this one has no
    # FACTION line at all, where every Aeldari sheet that HAS the army rule
    # prints "FACTION: **Battle Focus**". Six datasheets were setting it
    # wrongly - the three WRAITH CONSTRUCTs and the three SUPPORT WEAPON
    # platforms - and on the wraiths it did real harm: Spirit Conclave's
    # Spirit Guides aura exists to GRANT them Battle Focus while they stand
    # within 12" of an ASURYANI PSYKER, and a unit that already had it
    # permanently made that whole half of the detachment rule a no-op.
    war_construct = True            # see game/shooting.py's available_shooting_types()
    psychic_guidance = True         # see game/psychic_guidance.py


class AsurmenProfile(UnitProfile):
    """Phoenix Lord: a one-model EPIC HERO who leads Dire Avengers.

    The lone AELDARI CHARACTER here so far, which is why it is also the first
    Aeldari profile to set `leader` - rule 19.01's attachment legality is read
    off the points list's own LEADER line (UnitPoints.leads)."""
    # The CHARACTER keyword. Every one of these prints it on its datasheet; the
    # engine simply never set it, which left rule 05.03's allocation protection,
    # Epic Challenge, Heroic Intervention and Precision all silently inert for
    # Aeldari. NOT set on the Aspect Exarchs - a 10th-edition Exarch is part of
    # its unit and carries no CHARACTER keyword.
    character = True
    name = "Asurmen"
    epic_hero = True                # the EPIC HERO keyword. Printed on the datasheet and never set here,
                                    # which left rule 15.03 (Epic Challenge) inert for it and, later,
                                    # [ANTI-EPIC HERO] unable to see it - found when the Visarch's
                                    # mythic stance became the first weapon to name that keyword.
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
    # The CHARACTER keyword. Every one of these prints it on its datasheet; the
    # engine simply never set it, which left rule 05.03's allocation protection,
    # Epic Challenge, Heroic Intervention and Precision all silently inert for
    # Aeldari. NOT set on the Aspect Exarchs - a 10th-edition Exarch is part of
    # its unit and carries no CHARACTER keyword.
    character = True
    name = "Jain Zar"
    epic_hero = True                # the EPIC HERO keyword. Printed on the datasheet and never set here,
                                    # which left rule 15.03 (Epic Challenge) inert for it and, later,
                                    # [ANTI-EPIC HERO] unable to see it - found when the Visarch's
                                    # mythic stance became the first weapon to name that keyword.
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
    # The CHARACTER keyword. Every one of these prints it on its datasheet; the
    # engine simply never set it, which left rule 05.03's allocation protection,
    # Epic Challenge, Heroic Intervention and Precision all silently inert for
    # Aeldari. NOT set on the Aspect Exarchs - a 10th-edition Exarch is part of
    # its unit and carries no CHARACTER keyword.
    character = True
    name = "Lhykhis"
    epic_hero = True                # the EPIC HERO keyword. Printed on the datasheet and never set here,
                                    # which left rule 15.03 (Epic Challenge) inert for it and, later,
                                    # [ANTI-EPIC HERO] unable to see it - found when the Visarch's
                                    # mythic stance became the first weapon to name that keyword.
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
    # The CHARACTER keyword. Every one of these prints it on its datasheet; the
    # engine simply never set it, which left rule 05.03's allocation protection,
    # Epic Challenge, Heroic Intervention and Precision all silently inert for
    # Aeldari. NOT set on the Aspect Exarchs - a 10th-edition Exarch is part of
    # its unit and carries no CHARACTER keyword.
    character = True
    name = "Avatar of Khaine"
    epic_hero = True                # the EPIC HERO keyword. Printed on the datasheet and never set here,
                                    # which left rule 15.03 (Epic Challenge) inert for it and, later,
                                    # [ANTI-EPIC HERO] unable to see it - found when the Visarch's
                                    # mythic stance became the first weapon to name that keyword.
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
    # The CHARACTER keyword. Every one of these prints it on its datasheet; the
    # engine simply never set it, which left rule 05.03's allocation protection,
    # Epic Challenge, Heroic Intervention and Precision all silently inert for
    # Aeldari. NOT set on the Aspect Exarchs - a 10th-edition Exarch is part of
    # its unit and carries no CHARACTER keyword.
    character = True
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
    joins_without_leader_slot = True  # its LEADER ability is worded as a JOIN with its own one-Conclave-per-unit restriction, not as a 19.01 attachment - see game/attached_units.py
    protect = True                  # see game/protect.py


class FarseerProfile(UnitProfile):
    """Does NOT make Warlock Conclave's Protect live, contrary to what this
    docstring used to claim: Protect needs a FARSEER LEADING a unit that
    contains Warlocks, and a Conclave is itself a leader unit that neither
    datasheet's LEADER line names. Eldrad Ulthran is the one that reaches it,
    through his own LEADER line - see EldradUlthranProfile and game/protect.py."""
    # The CHARACTER keyword. Every one of these prints it on its datasheet; the
    # engine simply never set it, which left rule 05.03's allocation protection,
    # Epic Challenge, Heroic Intervention and Precision all silently inert for
    # Aeldari. NOT set on the Aspect Exarchs - a 10th-edition Exarch is part of
    # its unit and carries no CHARACTER keyword.
    character = True
    name = "Farseer"
    base_radius_in = WarlockProfile.base_radius_in  # User: "farseer und eldrad scheinen mir zu klein. sie sollen genau so groesse sein, wie warlock conclaive". His printed base is 25 mm (0.492"), the smallest here - deliberately NOT used, same call as the Falcon's, and pinned against the Warlock's profile rather than repeating its number so the pair cannot drift apart unnoticed. Not cosmetic: base_radius_in feeds placement, the movement clamp, edge_distance and coherency
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
    # The CHARACTER keyword. Every one of these prints it on its datasheet; the
    # engine simply never set it, which left rule 05.03's allocation protection,
    # Epic Challenge, Heroic Intervention and Precision all silently inert for
    # Aeldari. NOT set on the Aspect Exarchs - a 10th-edition Exarch is part of
    # its unit and carries no CHARACTER keyword.
    character = True
    name = "Eldrad Ulthran"
    epic_hero = True                # the EPIC HERO keyword. Printed on the datasheet and never set here,
                                    # which left rule 15.03 (Epic Challenge) inert for it and, later,
                                    # [ANTI-EPIC HERO] unable to see it - found when the Visarch's
                                    # mythic stance became the first weapon to name that keyword.
    base_radius_in = WarlockProfile.base_radius_in  # his printed 32 mm base already equals the Warlock's, so this changes no number - pinned against that profile because the user asked for the two to match (see FarseerProfile), which makes the coupling explicit instead of a coincidence of two literals
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


class DarkReaperProfile(UnitProfile):
    """Aspect Warriors built entirely around one gun: a 48" launcher that
    ignores cover, on a unit that can also ignore every Hit-roll modifier
    working against it."""
    name = "Dark Reaper"
    base_radius_in = 0.561          # 28.5 mm printed base, as Guardian Defenders
    movement_in = 6
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 1
    leadership = "6+"
    armor_save = "3+"
    oc = 1
    invulnerable_save = "5+"
    infantry = True
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    aspect_shrine = True            # "for every 5 models, 1 token" - see game/aspect_shrine.py
    ignores_hit_modifiers = True    # printed here as "Inescapable Accuracy"


class DarkReaperExarchProfile(DarkReaperProfile):
    """Subclasses rather than repeating the statline: the two rows differ in
    Wounds and Ballistic Skill and nothing else, and a copied near-duplicate is
    how a value drifts between two lines of ONE datasheet."""
    name = "Dark Reaper Exarch"
    wounds = 2
    ballistic_skill = "2+"
    squad_leader = True


class ShiningSpearProfile(UnitProfile):
    """MOUNTED, not INFANTRY - so no Dense-terrain crossing (13.06) and no
    Hidden (13.09), and game/ai/agent_driver.py's _needs_open_ground() treats
    them the way it treats Warbikers. MOUNTED itself is purely descriptive in
    this engine (like SMOKE and PSYKER), so it lives on the datasheet's keyword
    line rather than as a flag."""
    name = "Shining Spear"
    # ON-TABLE SIZE, not the printed base. User request: these read a quarter
    # too big next to the rest of the army, so the radius is three quarters of
    # the printed 60 mm - which lands on 45 mm, itself a real base size. The
    # Warlock Skyrunner was then set to the SAME number from the other side (it
    # read too small on its printed 32 mm), so the three MOUNTED jetbike units
    # in the roster now match each other rather than their datasheets.
    #
    # This is a gameplay number as well as a visual one - edge_distance() reads
    # it, so Engagement Range, overlap, coherency and formation packing all
    # shift with it. Same kind of call as the Falcon's, which was ENLARGED to
    # the Devilfish's on user request and likewise no longer matches its own
    # printed base.
    base_radius_in = 0.886          # 45 mm on the table; printed base is 60 mm
    movement_in = 14                # the fastest profile in the engine
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 4
    wounds = 2
    leadership = "6+"
    armor_save = "3+"
    oc = 2
    invulnerable_save = "5+"
    fly = True                      # the FLY keyword, rule 21.03
    battle_focus = True


class ShiningSpearExarchProfile(ShiningSpearProfile):
    name = "Shining Spear Exarch"
    wounds = 3
    squad_leader = True


class WarlockSkyrunnerProfile(UnitProfile):
    """The jetbike Warlock. Shares the foot Warlock's psychic kit and its JOIN
    wording, and differs in three ways that matter: it rides (MOUNTED/FLY,
    M14", so no Dense-terrain crossing and no Hidden), it joins WINDRIDERS
    rather than Guardians, and it does NOT have Protect - checked against the
    printed ability list rather than inherited from its near-twin, which is
    exactly how a free ability gets handed out by accident."""
    # The CHARACTER keyword. Every one of these prints it on its datasheet; the
    # engine simply never set it, which left rule 05.03's allocation protection,
    # Epic Challenge, Heroic Intervention and Precision all silently inert for
    # Aeldari. NOT set on the Aspect Exarchs - a 10th-edition Exarch is part of
    # its unit and carries no CHARACTER keyword.
    character = True
    name = "Warlock Skyrunner"
    # ON-TABLE SIZE, not the printed base. User request: these read a quarter
    # too big next to the rest of the army, so the radius is three quarters of
    # the printed 60 mm - which lands on 45 mm, itself a real base size. The
    # Warlock Skyrunner was then set to the SAME number from the other side (it
    # read too small on its printed 32 mm), so the three MOUNTED jetbike units
    # in the roster now match each other rather than their datasheets.
    #
    # This is a gameplay number as well as a visual one - edge_distance() reads
    # it, so Engagement Range, overlap, coherency and formation packing all
    # shift with it. Same kind of call as the Falcon's, which was ENLARGED to
    # the Devilfish's on user request and likewise no longer matches its own
    # printed base.
    base_radius_in = 0.886          # 45 mm on the table; printed base is 32 mm
    movement_in = 14
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 4
    wounds = 3
    leadership = "6+"
    armor_save = "6+"
    oc = 2
    invulnerable_save = "4+"
    fly = True                      # the FLY keyword, rule 21.03
    psyker = True
    leader = True                   # its LEADER ability, worded as a JOIN
    joins_without_leader_slot = True  # ...with its own one-Skyrunners-per-unit limit, exactly the Warlock Conclave's wording - see game/attached_units.py
    battle_focus = True
    psychic_communion = True        # see game/psychic_communion.py
    # "Runes of Battle: weapons equipped by models in this unit have the
    # [IGNORES COVER] ability." Same effect as the unit-level Ignores Cover
    # rule The Twin Lance prints, so it SHARES that flag rather than getting a
    # module of its own - the game/fieldcraft.py precedent, where one flag
    # carries a rule printed under three different flavour names. Read by
    # game/shooting.py's _cover_ignored_for_group(), which asks the whole
    # unit, so after a 19.01 merge the joined Windriders get it too - which is
    # what "models in this unit" means once they are one unit.
    ignores_cover = True


class WindriderProfile(UnitProfile):
    """Jetbikes. MOUNTED rather than INFANTRY, so no Dense-terrain crossing
    (13.06) and no Hidden (13.09), and NO invulnerable save at all - the
    printed statline has an armour save of 4+ and nothing else, which was
    confirmed with a second targeted lookup because the first reading of the
    table produced a spurious "6+" invulnerable."""
    name = "Windrider"
    base_radius_in = 0.630          # 32 mm printed flying base
    movement_in = 14
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 4
    wounds = 2
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    fly = True
    battle_focus = True
    swift_demise = True             # see game/swift_demise.py


class RangerProfile(UnitProfile):
    """Snipers. Two things about this statline are easy to get wrong and were
    both confirmed with a second, targeted lookup before being written down:
    the SHURIKEN PISTOL is printed at BS2+ while the model and its long rifle
    are 3+ (a pistol more accurate than a sniper rifle reads like a
    transcription error and is not one), and the invulnerable save applies
    against RANGED attacks only."""
    name = "Ranger"
    base_radius_in = 0.561          # 28.5 mm printed base
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 1
    leadership = "7+"
    armor_save = "5+"
    oc = 1
    invulnerable_save_vs_ranged = "5+"   # "INSV 5+ * Against ranged attacks only"
    infantry = True
    battle_focus = True
    infiltrators = True             # CORE, rule 24.20 - already implemented
    stealth = True                  # CORE, rule 24.33 - already implemented
    path_of_the_outcast = True      # see game/path_of_the_outcast.py


class ShroudRunnerProfile(UnitProfile):
    """Ranger jetbikes: the sniper kit on a 14" MOUNTED platform, so no
    Dense-terrain crossing (13.06) and no Hidden (13.09) - and, unlike the
    Rangers they are drawn from, no Infiltrators. Scouts 9" instead, which is
    the longest Scout move in the engine."""
    name = "Shroud Runner"
    # ON-TABLE SIZE, not the printed base. User request: these read a quarter
    # too big next to the rest of the army, so the radius is three quarters of
    # the printed 60 mm - which lands on 45 mm, itself a real base size. The
    # Warlock Skyrunner was then set to the SAME number from the other side (it
    # read too small on its printed 32 mm), so the three MOUNTED jetbike units
    # in the roster now match each other rather than their datasheets.
    #
    # This is a gameplay number as well as a visual one - edge_distance() reads
    # it, so Engagement Range, overlap, coherency and formation packing all
    # shift with it. Same kind of call as the Falcon's, which was ENLARGED to
    # the Devilfish's on user request and likewise no longer matches its own
    # printed base.
    base_radius_in = 0.886          # 45 mm on the table; printed base is 60 mm
    movement_in = 14
    weapon_skill = "3+"
    ballistic_skill = "2+"
    toughness = 4
    wounds = 3
    leadership = "7+"
    armor_save = "5+"
    oc = 2
    invulnerable_save_vs_ranged = "5+"
    fly = True                      # the FLY keyword, rule 21.03
    battle_focus = True
    scouts = 9.0                    # CORE "Scouts 9\"" - rule 24.31/24.32
    stealth = True                  # CORE, rule 24.33
    target_acquisition = True       # see game/target_acquisition.py


class SwoopingHawkProfile(UnitProfile):
    """Jump-pack Aspect Warriors: INFANTRY, so unlike the Aeldari jetbikes they
    keep Dense-terrain crossing (13.06) and Hidden (13.09) despite the 14" move
    and FLY."""
    name = "Swooping Hawk"
    base_radius_in = 0.630          # 32 mm printed base
    movement_in = 14
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 1
    leadership = "6+"
    armor_save = "4+"
    oc = 1
    invulnerable_save = "5+"
    infantry = True
    fly = True                      # the FLY keyword, rule 21.03
    jump_pack = True                # the JUMP PACK keyword
    deep_strike = True              # CORE, rule 24.09
    battle_focus = True
    aspect_shrine = True            # "for every 5 models, 1 token"
    grenade_pack_flyover = True     # see game/grenade_pack_flyover.py


class SwoopingHawkExarchProfile(SwoopingHawkProfile):
    """Subclasses rather than repeating the statline: the two rows differ in
    Wounds and nothing else."""
    name = "Swooping Hawk Exarch"
    wounds = 2
    squad_leader = True


class BaharrothProfile(UnitProfile):
    """Phoenix Lord of the Swooping Hawks - the fourth here, after Asurmen,
    Jain Zar and Lhykhis, and the first with DEEP STRIKE."""
    # The CHARACTER keyword. Every one of these prints it on its datasheet; the
    # engine simply never set it, which left rule 05.03's allocation protection,
    # Epic Challenge, Heroic Intervention and Precision all silently inert for
    # Aeldari. NOT set on the Aspect Exarchs - a 10th-edition Exarch is part of
    # its unit and carries no CHARACTER keyword.
    character = True
    name = "Baharroth"
    epic_hero = True                # the EPIC HERO keyword. Printed on the datasheet and never set here,
                                    # which left rule 15.03 (Epic Challenge) inert for it and, later,
                                    # [ANTI-EPIC HERO] unable to see it - found when the Visarch's
                                    # mythic stance became the first weapon to name that keyword.
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 14
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 3
    wounds = 5
    leadership = "6+"
    armor_save = "2+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    fly = True
    jump_pack = True
    deep_strike = True              # CORE, rule 24.09
    leader = True                   # CORE - leads Swooping Hawks and nothing else
    battle_focus = True
    cloudstrider = True             # see game/cloudstrider.py
    cry_of_the_wind = True          # see game/crit_hit.py


class WarWalkerProfile(UnitProfile):
    """A light Aeldari walker - VEHICLE, but not a grav-tank, so unlike the
    Falcon and the Wave Serpent it keeps its own printed 60 mm base rather than
    being matched to the Devilfish."""
    name = "War Walker"
    base_radius_in = 1.181          # 60 mm printed base
    movement_in = 10
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 7
    wounds = 6
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    invulnerable_save = "5+"
    vehicle = True
    battle_focus = True
    scouts = 9.0                    # CORE "Scouts 9\"" - rule 24.31/24.32
    crystalline_targeting = True    # see game/crystalline_targeting.py


class WaveSerpentProfile(UnitProfile):
    """The Aeldari troop transport - the same hull as the Falcon, which is why
    it takes the same base radius rather than its own printed 60 mm: the two
    would otherwise sit on the table at wildly different sizes (see
    FalconProfile, enlarged to match the Devilfish on user request).

    weapon_skill is not printed on the statline; the Wraithbone hull prints its
    own WS4+, which is the only melee this model has, so it is set to match
    rather than left at the class default."""
    name = "Wave Serpent"
    base_radius_in = 2.1            # matched to FalconProfile/DevilfishProfile, not the printed 60 mm
    movement_in = 14
    weapon_skill = "4+"
    ballistic_skill = "3+"
    toughness = 9
    wounds = 13
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    invulnerable_save = "5+"
    vehicle = True
    fly = True
    battle_focus = True
    deadly_demise_notation = D3()   # CORE "Deadly Demise D3", rule 24.08
    damaged_threshold = 4           # "DAMAGED: 1-4 WOUNDS REMAINING" - -1 to Hit
    wave_serpent_shield = True      # see game/wave_serpent_shield.py
    transport = True                # rule 18.01
    transport_capacity = 12
    transport_requires_infantry = True
    transport_excludes = ("jump_pack",)


class FueganProfile(UnitProfile):
    """The Phoenix Lord of the Fire Dragons.

    The statline is the shared Phoenix Lord chassis this project already fields
    four times over (Asurmen, Jain Zar, Baharroth, Lhykhis): T3, Sv2+, W5, Ld6+,
    OC1, Invulnerable 4+. Those four are why T3 is transcribed as printed rather
    than queried - it is the edition's number for an Aspect Warrior, not a slip."""
    name = "Fuegan"
    base_radius_in = 0.787          # 40 mm, like the other foot Phoenix Lords
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
    character = True
    epic_hero = True
    leader = True                   # the CHARACTER/LEADER pair, rule 24.22 - the pairing itself is UnitPoints.leads
    battle_focus = True
    burning_lance = True            # see game/burning_lance.py
    unquenchable_resolve = True     # see game/unquenchable_resolve.py


# --- Wraith Constructs ------------------------------------------------------


class WraithbladeProfile(UnitProfile):
    """The Wraithguard chassis rebuilt for melee: same Sv2+/W3, same worst-in-
    the-engine Ld8+, but T6->T6 kept and the gun traded for blades.

    Deliberately pinned against WraithguardProfile in the test rather than
    against literals - the two are the same printed construct in two roles, and
    a change to one that silently misses the other is the drift worth catching."""
    name = "Wraithblade"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 6
    weapon_skill = "4+"
    ballistic_skill = "4+"          # no ranged weapon, carried for completeness
    toughness = 6
    wounds = 3
    leadership = "8+"
    armor_save = "2+"
    oc = 1
    infantry = True
    wraith_construct = True         # WRAITH CONSTRUCT - two transport slots each
    # NO battle_focus. MEASURED against the printed datasheet: this one has no
    # FACTION line at all, where every Aeldari sheet that HAS the army rule
    # prints "FACTION: **Battle Focus**". Six datasheets were setting it
    # wrongly - the three WRAITH CONSTRUCTs and the three SUPPORT WEAPON
    # platforms - and on the wraiths it did real harm: Spirit Conclave's
    # Spirit Guides aura exists to GRANT them Battle Focus while they stand
    # within 12" of an ASURYANI PSYKER, and a unit that already had it
    # permanently made that whole half of the detachment rule a no-op.
    psychic_guidance = True         # see game/psychic_guidance.py
    malevolent_souls = True         # see game/malevolent_souls.py


class WraithlordProfile(UnitProfile):
    """A one-model MONSTER WALKER: T10/Sv2+/W10, and the only Aeldari model in
    this engine that picks an enemy keyword to hate at the start of the battle.

    Its base is the printed 60 mm and stays there: it is a walker, not a
    grav-tank, so unlike the Falcon and the Wave Serpent it does not take the
    2.1 table size - the same call WarWalkerProfile records."""
    name = "Wraithlord"
    base_radius_in = 1.181          # 60 mm printed base
    movement_in = 8
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 10
    wounds = 10
    leadership = "8+"
    armor_save = "2+"
    oc = 3
    monster = True
    walker = True
    wraith_construct = True         # WRAITH CONSTRUCT
    # NO battle_focus. MEASURED against the printed datasheet: this one has no
    # FACTION line at all, where every Aeldari sheet that HAS the army rule
    # prints "FACTION: **Battle Focus**". Six datasheets were setting it
    # wrongly - the three WRAITH CONSTRUCTs and the three SUPPORT WEAPON
    # platforms - and on the wraiths it did real harm: Spirit Conclave's
    # Spirit Guides aura exists to GRANT them Battle Focus while they stand
    # within 12" of an ASURYANI PSYKER, and a unit that already had it
    # permanently made that whole half of the detachment rule a no-op.
    deadly_demise = 1               # "Deadly Demise 1", rule 24.08 - a flat 1, so no notation
    fated_hero = True               # see game/fated_hero.py
    # The Wraithlord's Psychic Guidance is NOT the Wraithguard/Wraithblade one:
    # it improves the BS and WS characteristics of this model's weapons by 1,
    # where theirs adds 1 to the Hit roll. In this engine both end up adjusting
    # the same threshold, but they are separate printed effects and are kept as
    # separate flags so that a future rule which distinguishes "improve the
    # characteristic" from "modify the roll" has something to distinguish.
    psychic_guidance_characteristics = True   # see game/psychic_guidance.py


# --- Support Weapon Platforms -----------------------------------------------


class SupportWeaponPlatformProfile(UnitProfile):
    """The chassis the D-cannon, Shadow Weaver and Vibro Cannon platforms all
    print: M7"/T6/Sv4+/W5/Ld7+/OC1 on a 40 mm base, WS/BS 3+, and the same two
    shared abilities.

    A BASE CLASS rather than three copies, because the assurance worth making
    about these three is that they AGREE - which cannot be written down in
    three independent profiles. Same call the Kroot Shapers record. What each
    subclass adds is its own heavy gun and its own second ability, which is the
    entire difference between the three datasheets.

    They are SUPPORT models (24.34), not LEADERs: "Support Artillery" lets one
    join a GUARDIAN DEFENDERS unit at Declare Battle Formations. That is the
    SUPPORT attachment role this engine already has, so the pairing is declared
    the ordinary way - UnitPoints.supports in game/factions/aeldari_points.py."""
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 6
    wounds = 5
    leadership = "7+"
    armor_save = "4+"
    oc = 1
    infantry = True
    support = True                  # the SUPPORT keyword, rule 24.34 - see game/attached_units.py
    # NO battle_focus. MEASURED against the printed datasheet: this one has no
    # FACTION line at all, where every Aeldari sheet that HAS the army rule
    # prints "FACTION: **Battle Focus**". Six datasheets were setting it
    # wrongly - the three WRAITH CONSTRUCTs and the three SUPPORT WEAPON
    # platforms - and on the wraiths it did real harm: Spirit Conclave's
    # Spirit Guides aura exists to GRANT them Battle Focus while they stand
    # within 12" of an ASURYANI PSYKER, and a unit that already had it
    # permanently made that whole half of the detachment rule a no-op.
    support_weapon_toughness = True  # "Support Weapon": T3 while in a unit with other models - see game/squad.py
    # The SUPPORT WEAPON keyword itself. Etappe 2 put it on the three platform
    # DATASHEETS but never on their profiles, so the flag below sat at False
    # everywhere and game/branching_fates.py's "excluding SUPPORT WEAPON
    # models" clause could not fire on the very datasheets it was waiting for.
    # Yvraine's Word of the Phoenix is the second reader of the same clause,
    # which is what made the gap visible.
    support_weapon = True
    cannot_embark = True            # "This model, and any unit it is joined to, cannot embark within a TRANSPORT."


class DCannonPlatformProfile(SupportWeaponPlatformProfile):
    name = "D-cannon Platform"
    structural_collapse = True      # see game/structural_collapse.py


class ShadowWeaverPlatformProfile(SupportWeaponPlatformProfile):
    name = "Shadow Weaver Platform"
    monofilament_snare = True       # see game/monofilament_snare.py


class VibroCannonPlatformProfile(SupportWeaponPlatformProfile):
    name = "Vibro Cannon Platform"
    sonic_destruction = True        # see game/sonic_destruction.py


# --- Fire Prism / Night Spinner / Vypers ------------------------------------


class AeldariGunTankProfile(UnitProfile):
    """The Fire Prism and Night Spinner are one hull with two guns bolted on:
    M14"/T9/Sv3+/W12/Ld7+/OC3, Deadly Demise D3, the same DAMAGED bracket, and
    FLY/FRAME. A base class for the same reason the Support Weapon Platforms
    have one - the assurance worth writing down is that they AGREE.

    Base: the printed 60 mm flying base is NOT used. Both are the Falcon's
    grav-tank hull, and the standing table size for that hull in this project
    is 2.1 (the user's call, matched to the Devilfish; the Falcon and the Wave
    Serpent already carry it). Pinned against the Falcon in the test rather
    than against the literal, so the four cannot drift apart."""
    base_radius_in = 2.1            # matched to FalconProfile/WaveSerpentProfile, not the printed 60 mm
    movement_in = 14
    weapon_skill = "4+"             # only the wraithbone hull, which prints 4+
    ballistic_skill = "3+"
    toughness = 9
    wounds = 12
    leadership = "7+"
    armor_save = "3+"
    oc = 3
    vehicle = True
    fly = True
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    deadly_demise = 3               # documentation leftover - deadly_demise_notation is what is rolled
    deadly_demise_notation = D3()   # "Deadly Demise D3", rule 24.08
    damaged_threshold = 4           # "DAMAGED: 1-4 WOUNDS REMAINING" - -1 to Hit


class FirePrismProfile(AeldariGunTankProfile):
    name = "Fire Prism"
    crystal_matrix = True           # see game/crystal_matrix.py


class NightSpinnerProfile(AeldariGunTankProfile):
    name = "Night Spinner"
    monofilament_web = True         # see game/monofilament_web.py


class VyperProfile(UnitProfile):
    """A light two-model skimmer, and the only one of the three that is NOT the
    grav-tank hull - so it keeps its own converted base rather than the 2.1.

    Its 105 x 70 mm oval takes the equal-AREA circle conversion this file uses
    everywhere, which is the same oval the Ghostkeel prints; pinned against it
    in the test so the two conversions cannot disagree."""
    name = "Vyper"
    base_radius_in = 1.69           # 105 x 70 mm oval -> equal-area circle, as GhostkeelProfile
    movement_in = 14
    weapon_skill = "4+"             # only the wraithbone hull, which prints 4+
    ballistic_skill = "3+"
    toughness = 6
    wounds = 6
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    vehicle = True
    fly = True
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    deadly_demise = 1               # "Deadly Demise 1", rule 24.08 - a flat 1, so no notation
    harassment_fire = True          # see game/suppression.py - the SAME "suppressed" status Suppression Volley applies


# --- The three standalone Asuryani psykers -----------------------------------


class LoneWarlockProfile(WarlockProfile):
    """The standalone "Warlock" datasheet, which is NOT the Warlock Conclave's
    model even though both print a model called Warlock on the same statline.

    Inherits the statline so the two cannot drift; overrides exactly what the
    two datasheets print differently:
      * the Conclave prints PROTECT, this one does not;
      * this one prints RUNES OF FORTUNE, the Conclave does not;
      * this one is an ordinary SUPPORT attachment, where the Conclave's line
        is modelled as a JOIN that occupies no leader slot (see
        game/attached_units.py) - so `joins_without_leader_slot` is switched
        back OFF here. An inherited flag left standing would give this datasheet
        a restriction-free join its own text does not print, which is exactly
        the inheritance trap the Sky Ray's `armour_hunter` records."""
    protect = False
    joins_without_leader_slot = False
    leader = False
    support = True                  # its CORE line reads Support, not Leader
    runes_of_fortune = True         # see game/runes_of_fortune.py


class SpiritseerProfile(UnitProfile):
    """The WRAITH CONSTRUCT support psyker: no invulnerable-save-piercing gun,
    a witch staff, and three abilities that all point at wraith units."""
    name = "Spiritseer"
    base_radius_in = 0.492          # 25 mm printed base
    movement_in = 7
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 3
    wounds = 3
    leadership = "6+"
    armor_save = "6+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    character = True
    psyker = True
    stealth = True                  # its CORE line
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    spiritseer_lone_operative = True  # conditional Lone Operative near WRAITH CONSTRUCTs - see game/spiritseer.py
    spirit_mark = True              # see game/spiritseer.py
    tears_of_isha = True            # see game/spiritseer.py


class FarseerSkyrunnerProfile(UnitProfile):
    """The Farseer on a jetbike. MOUNTED, so it takes the 45 mm table size the
    other three jetbike datasheets share rather than its printed 32 mm - the
    standing user decision, pinned against them in the test."""
    name = "Farseer Skyrunner"
    base_radius_in = 0.886          # 45 mm on the table; printed base is 32 mm
    movement_in = 14
    weapon_skill = "2+"
    ballistic_skill = "3+"
    toughness = 4
    wounds = 5
    leadership = "6+"
    armor_save = "6+"
    oc = 2
    invulnerable_save = "4+"
    mounted = True
    fly = True
    character = True
    psyker = True
    farseer = True                  # the FARSEER keyword - read by game/protect.py
    leader = True                   # its CORE line
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    branching_fates = True          # see game/branching_fates.py - the same ability the foot Farseer prints
    misfortune = True               # see game/misfortune.py


# --- Autarchs and Maugan Ra --------------------------------------------------


class AutarchProfile(UnitProfile):
    """The Aspect Warriors' commander: T3/Sv3+/W4 with a 4+ invulnerable, and
    the widest LEADER line in the faction - seven datasheets."""
    name = "Autarch"
    base_radius_in = 0.630          # 32 mm printed base
    movement_in = 7
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 3
    wounds = 4
    leadership = "6+"
    armor_save = "3+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    character = True
    leader = True
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    aspect_training = True          # see game/aspect_training.py
    superlative_strategist = True   # see game/superlative_strategist.py
    path_of_command = True          # see game/path_of_command.py


class AutarchWayleaperProfile(UnitProfile):
    """The same commander with a jump pack: M14", DEEP STRIKE, and a Battle
    Focus token economy of his own instead of the re-rolls.

    NOT a subclass of AutarchProfile, deliberately: the two share a statline in
    everything but Movement, and every one of their three named abilities
    differs. Inheriting would mean switching off more than it kept - the
    inverse of the LoneWarlockProfile case, where inheritance earned its
    keep."""
    name = "Autarch Wayleaper"
    base_radius_in = 0.630          # 32 mm printed base
    movement_in = 14
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 3
    wounds = 4
    leadership = "6+"
    armor_save = "3+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    character = True
    jump_pack = True
    fly = True
    leader = True
    deep_strike = True              # its CORE line
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    indomitable_strength_of_will = True   # see game/indomitable_strength_of_will.py
    path_of_command = True          # see game/path_of_command.py


class MauganRaProfile(UnitProfile):
    """The Phoenix Lord of the Dark Reapers, on the shared Phoenix Lord chassis
    (T3/Sv2+/W5/Ld6+/OC1/Inv4+) that Asurmen, Jain Zar, Baharroth, Lhykhis and
    Fuegan all print - pinned against them in the test rather than against
    literals, for the same reason Fuegan's T3 is."""
    name = "Maugan Ra"
    base_radius_in = 0.787          # 40 mm, like the other foot Phoenix Lords
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
    character = True
    epic_hero = True
    leader = True
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    harvester_of_souls = True       # see game/harvester_of_souls.py
    face_of_death = True            # see game/face_of_death.py


# --- Exodites ----------------------------------------------------------------


class ExoditeProfile(UnitProfile):
    """The drakesteed all four Exodite datasheets ride: M10"/T5/Sv4+/W4/OC2 on
    a 75 x 42 mm oval, MOUNTED and MOBILE.

    Only the Clanblade's Leadership differs (6+ against 7+), which is why that
    one characteristic is overridden below rather than the whole statline being
    written four times.

    Base: the 75 x 42 mm oval takes the equal-AREA circle conversion this file
    uses for every oval - r = sqrt(37.5 * 21) = 28.06 mm ~= 1.105"."""
    base_radius_in = 1.105          # 75 x 42 mm oval -> equal-area circle
    movement_in = 10
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 5
    wounds = 4
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    mounted = True
    mobile = True                   # the MOBILE keyword - already read by [ANTI-MOBILE]
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py


class DragonKnightProfile(ExoditeProfile):
    name = "Dragon Knight"
    on_the_hunt = True              # the FOURTH printed wording of the Fall Back exception - see game/shooting.py
    agile_reach = True              # see game/agile_reach.py
    drakolithe = True               # see game/drakolithe.py


class ClanbladeProfile(ExoditeProfile):
    name = "Clanblade"
    leadership = "6+"               # the one characteristic that differs from the chassis
    character = True
    leader = True                   # its CORE line
    blade_of_the_clans = True       # see game/blade_of_the_clans.py
    cornered_prey = True            # see game/cornered_prey.py


class LeystalkerProfile(ExoditeProfile):
    name = "Leystalker"
    character = True
    lone_operative = 12.0           # its CORE line, rule 24.24 - printed outright, unlike the Spiritseer's conditional grant
    scouts = 9.0                    # its CORE line, rule 24.31
    stealth = True                  # its CORE line, rule 24.33
    panicked_quarry = True          # see game/battle_shock_after_shooting.py
    drakolithe = True               # see game/drakolithe.py


class StonesingerProfile(ExoditeProfile):
    name = "Stonesinger"
    character = True
    psyker = True
    support = True                  # its CORE line
    elemental_ensnarement = True    # see game/elemental_ensnarement.py


# --- Anhrathe (Corsairs) -----------------------------------------------------


class CorsairProfile(UnitProfile):
    """The Corsair foot chassis: M7"/T3/Sv4+/W1/Ld7+ on a 28.5 mm base, with
    Scouts 7" as a CORE line on every Anhrathe datasheet here.

    OC differs between the two foot squads (Voidreavers 2, Voidscarred 1), so
    that is the one characteristic a subclass overrides."""
    base_radius_in = 0.561          # 28.5 mm printed base
    movement_in = 7
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 1
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    infantry = True
    scouts = 7.0                    # its CORE line, rule 24.31
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py


class CorsairVoidreaverProfile(CorsairProfile):
    name = "Corsair Voidreaver"
    reavers_of_the_void = True      # see game/reavers_of_the_void.py


class VoidreaverFelarchProfile(CorsairVoidreaverProfile):
    name = "Voidreaver Felarch"
    squad_leader = True


class CorsairVoidscarredProfile(CorsairProfile):
    name = "Corsair Voidscarred"
    oc = 1                          # the one characteristic that differs from the chassis
    piratical_raiders = True        # see game/piratical_raiders.py


class VoidscarredFelarchProfile(CorsairVoidscarredProfile):
    name = "Voidscarred Felarch"
    squad_leader = True


class ShadeRunnerProfile(CorsairVoidscarredProfile):
    name = "Shade Runner"


class SoulWeaverProfile(CorsairVoidscarredProfile):
    name = "Soul Weaver"
    channeller_stones = True        # see game/channeller_stones.py


class WaySeekerProfile(CorsairVoidscarredProfile):
    name = "Way Seeker"
    psyker = True


class CorsairSkyreaverProfile(CorsairProfile):
    """The jump-pack Corsairs: faster, lighter armour, and one less OC."""
    name = "Skyreaver"
    movement_in = 12
    armor_save = "5+"
    oc = 1
    jump_pack = True
    fly = True
    deep_strike = True              # its CORE line
    raid_and_run = True             # see game/raid_and_run.py


class SkyreaverFelarchProfile(CorsairSkyreaverProfile):
    name = "Skyreaver Felarch"
    squad_leader = True


class KharsethProfile(UnitProfile):
    """An ANHRATHE EPIC HERO and PSYKER who leads the Corsair squads."""
    name = "Kharseth"
    base_radius_in = 0.630          # 32 mm printed base
    movement_in = 7
    weapon_skill = "2+"
    ballistic_skill = "3+"
    toughness = 3
    wounds = 4
    leadership = "6+"
    armor_save = "6+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    character = True
    epic_hero = True
    psyker = True
    leader = True
    scouts = 7.0                    # its CORE line
    battle_focus = True
    aethersense = True              # see game/aethersense.py
    fury_of_the_void = True         # see game/fury_of_the_void.py


class PrinceYrielProfile(UnitProfile):
    """The other Corsair EPIC HERO - no psyker, a much better save, and the
    two abilities that make him a list-building piece."""
    name = "Prince Yriel"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 7
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 3
    wounds = 5
    leadership = "6+"
    armor_save = "3+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    character = True
    epic_hero = True
    leader = True
    scouts = 7.0                    # its CORE line
    battle_focus = True
    piratical_hero = True           # see game/piratical_hero.py
    prince_of_corsairs = True       # see game/prince_of_corsairs.py


class StarfangProfile(UnitProfile):
    """The Anhrathe skimmer. Same 105 x 70 oval as the Vyper, so it takes the
    same converted radius - pinned against it rather than against a literal."""
    name = "Starfang"
    base_radius_in = 1.69           # 105 x 70 mm oval -> equal-area circle, as VyperProfile
    movement_in = 14
    weapon_skill = "4+"
    ballistic_skill = "3+"
    toughness = 6
    wounds = 6
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    vehicle = True
    fly = True
    scouts = 7.0                    # its CORE line
    deadly_demise = 1               # "Deadly Demise 1", rule 24.08 - a flat 1, so no notation
    battle_focus = True
    hallucinogen_grenades = True    # see game/hallucinogen_grenades.py


# --- The Ynnari triumvirate --------------------------------------------------


class YvraineProfile(UnitProfile):
    """Emissary of Ynnead. Her 75 x 42 mm oval is the Exodite drakesteed's, so
    it takes the same converted radius - pinned against it rather than a
    literal."""
    name = "Yvraine"
    base_radius_in = 1.105          # 75 x 42 mm oval -> equal-area circle, as ExoditeProfile
    movement_in = 8
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 3
    wounds = 4
    leadership = "6+"
    armor_save = "6+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    character = True
    epic_hero = True
    psyker = True
    leader = True
    battle_focus = True             # Aeldari army rule - see game/battle_focus.py
    word_of_the_phoenix = True      # see game/ynnari_abilities.py
    herald_of_ynnead = True         # see game/ynnari_abilities.py


class TheVisarchProfile(UnitProfile):
    """Yvraine's champion, and a SUPPORT model rather than a LEADER - which is
    what lets him join a unit she is already attached to."""
    name = "The Visarch"
    base_radius_in = 0.630          # 32 mm printed base
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
    character = True
    epic_hero = True
    support = True                  # its CORE line
    battle_focus = True
    # His printed SUPPORT line adds "even if YVRAINE has already been attached
    # to it" - the same shape Eldrad's own line has, and the same flag, because
    # the engine's question is identical: may this model join a unit that
    # already has a leader?
    joins_warlock_led_unit = True
    way_of_the_blade = True         # see game/ynnari_abilities.py
    yvraines_champion = True        # see game/ynnari_abilities.py


class TheYncarneProfile(UnitProfile):
    """The avatar of Ynnead: a T10/W12 MONSTER that teleports to its own
    army's dead."""
    name = "The Yncarne"
    base_radius_in = 1.575          # 80 mm printed base
    movement_in = 10
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 10
    wounds = 12
    leadership = "6+"
    armor_save = "2+"
    oc = 3
    invulnerable_save = "4+"
    monster = True
    character = True
    epic_hero = True
    fly = True
    psyker = True
    daemon = True
    deep_strike = True              # its CORE line
    deadly_demise = 3               # documentation leftover - deadly_demise_notation is what is rolled
    deadly_demise_notation = D3()   # "Deadly Demise D3", rule 24.08
    battle_focus = True
    inevitable_death = True         # see game/ynnari_abilities.py
    ethereal_form = True            # see game/ynnari_abilities.py


# ===========================================================================
# Necrons - see game/factions/necrons.py
#
# Every profile here carries reanimation_protocols: it is the army rule, and
# rule 01.02.03's "revived models" half is the reason Squad.destroyed_models
# exists at all. Note that MOUNTED and BATTLELINE are NOT flags on this class
# - they are purely descriptive keywords and live in the Datasheet's keyword
# tuple, read through attached_units.unit_has_datasheet_keyword().
# ===========================================================================


class NecronWarriorProfile(UnitProfile):
    name = "Necron Warrior"
    base_radius_in = 0.630          # 32 mm
    movement_in = 5
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 4
    wounds = 1
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    infantry = True
    reanimation_protocols = True
    reanimation_reroll = True       # see game/reanimation_protocols.py


class ImmortalProfile(UnitProfile):
    name = "Immortal"
    base_radius_in = 0.630          # 32 mm
    movement_in = 5
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 5
    wounds = 1
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    infantry = True
    reanimation_protocols = True
    implacable_eradication = True   # see game/implacable_eradication.py


class LychguardProfile(UnitProfile):
    name = "Lychguard"
    base_radius_in = 0.630          # 32 mm
    movement_in = 5
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 5
    wounds = 2
    leadership = "7+"
    armor_save = "3+"
    oc = 1
    infantry = True
    reanimation_protocols = True
    guardian_protocols = True       # see game/guardian_protocols.py
    # NOTE: no invulnerable_save here. The 4+ comes from the dispersion shield,
    # which is a Gear item and therefore a per-TOKEN grant read by
    # game/invulnerable_save.py - the same arrangement as the shimmershield.


class OverlordProfile(UnitProfile):
    name = "Overlord"
    base_radius_in = 0.787          # 40 mm
    movement_in = 5
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 5
    wounds = 6
    leadership = "6+"
    armor_save = "2+"
    oc = 1
    invulnerable_save = "4+"
    infantry = True
    character = True
    noble = True                    # the printed NOBLE keyword - read by game/guardian_protocols.py
    leader = True                   # rule 24.22 - the pairing itself is UnitPoints.leads
    reanimation_protocols = True
    my_will_be_done = True          # see game/my_will_be_done.py
    damage_reduction = 1            # "Implacable Resilience", see game/damage_reduction.py


class PlasmancerProfile(UnitProfile):
    name = "Plasmancer"
    base_radius_in = 0.630          # 32 mm
    movement_in = 5
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 4
    wounds = 4
    leadership = "6+"
    armor_save = "4+"
    oc = 1
    infantry = True
    character = True
    # SUPPORT, not Leader - its printed CORE line reads "Support" and so does
    # this datasheet's abilities_text. It carried `leader = True` until the
    # Cryptek batch measured it: 19.01 allows one Leader AND one Support on a
    # unit, so the wrong flag meant a Necron Warriors squad with an Overlord
    # could not also take this model - can_attach() refused it as a second
    # leader. See game/attached_units.py's attachment_role().
    support = True
    reanimation_protocols = True
    leading_ranged_crit_on_5 = True  # printed here as "Harbinger of Destruction"; see game/crit_hit.py
    living_lightning = True          # see game/mortal_wound_abilities.py


class TechnomancerProfile(UnitProfile):
    name = "Technomancer"
    base_radius_in = 0.984          # 50 mm
    movement_in = 10                # 11th edition puts this Cryptek on a Canoptek construct - M10" and FLY, checked rather than assumed
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 4
    wounds = 4
    leadership = "6+"
    armor_save = "4+"
    oc = 1
    infantry = True
    character = True
    fly = True
    # SUPPORT, not Leader - its printed CORE line reads "Support" and so does
    # this datasheet's abilities_text. It carried `leader = True` until the
    # Cryptek batch measured it: 19.01 allows one Leader AND one Support on a
    # unit, so the wrong flag meant a Necron Warriors squad with an Overlord
    # could not also take this model - can_attach() refused it as a second
    # leader. See game/attached_units.py's attachment_role().
    support = True
    reanimation_protocols = True
    rites_of_reanimation = True     # see game/feel_no_pain.py
    technomancer_repair = True      # see game/technomancer.py


class ChronomancerProfile(UnitProfile):
    """Datasheet: Chronomancer (Necrons).

    The first of three Crypteks in this batch, and they share a chassis with
    the Plasmancer already here: M5" T4 Sv4+ W4 Ld6+ OC1 on a 40 mm base. What
    separates them is the invulnerable save (this one and Orikan print 4+, the
    Psychomancer prints none) and their own abilities."""
    name = "Chronomancer"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 5
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 4
    wounds = 4
    leadership = "6+"
    armor_save = "4+"
    invulnerable_save = "4+"
    oc = 1
    infantry = True
    character = True
    support = True                  # its CORE line reads Support
    reanimation_protocols = True
    stealth = True                  # Timesplinter Mantle, first half - rule 24.33
    timesplinter_mantle = True      # ...and its second half; see game/timesplinter_mantle.py
    chronometron = True             # see game/chronometron.py


class PsychomancerProfile(UnitProfile):
    """Datasheet: Psychomancer (Necrons).

    The one Cryptek of the three with NO invulnerable save printed - checked
    against the corpus rather than assumed from its two neighbours."""
    name = "Psychomancer"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 5
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 4
    wounds = 4
    leadership = "6+"
    armor_save = "4+"
    oc = 1
    infantry = True
    character = True
    support = True                  # its CORE line reads Support
    reanimation_protocols = True
    nightmare_shroud = True         # see game/psychomancer.py
    harbinger_of_despair = True     # see game/psychomancer.py


class OrikanTheDivinerProfile(UnitProfile):
    """Datasheet: Orikan The Diviner (Necrons).

    WS 3+ where the other two Crypteks print 4+, because his Staff of Tomorrow
    does - the profile carries it rather than the weapon, which is this repo's
    rule: a per-weapon override exists only where a sheet contradicts its own
    bearer, and his single weapon does not."""
    name = "Orikan The Diviner"
    base_radius_in = 0.787          # 40 mm printed base
    movement_in = 5
    weapon_skill = "3+"
    ballistic_skill = "4+"          # he prints no ranged weapon at all
    toughness = 4
    wounds = 4
    leadership = "6+"
    armor_save = "4+"
    invulnerable_save = "4+"
    oc = 1
    infantry = True
    character = True
    epic_hero = True                # rule 15.03 (Epic Challenge) and [ANTI-EPIC HERO]
    support = True                  # its CORE line reads Support
    reanimation_protocols = True
    master_chronomancer = True      # see game/invulnerable_save.py
    the_stars_are_right = True      # see game/the_stars_are_right.py


class DeathmarkProfile(UnitProfile):
    """Datasheet: Deathmarks (Necrons).

    T5 on a 1-wound INFANTRY body, which is the datasheet: a 36" sniper squad
    that arrives by Deep Strike and shoots things as they arrive."""
    name = "Deathmark"
    base_radius_in = 0.630          # 32 mm
    movement_in = 5
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 5
    wounds = 1
    leadership = "7+"
    armor_save = "3+"
    oc = 1
    infantry = True
    deep_strike = True              # rule 24.09
    reanimation_protocols = True
    hyperspace_hunters = True       # see game/hyperspace_hunters.py


class FlayedOneProfile(UnitProfile):
    """Datasheet: Flayed Ones (Necrons)."""
    name = "Flayed One"
    base_radius_in = 0.561          # 28.5 mm
    movement_in = 5
    weapon_skill = "3+"
    ballistic_skill = "4+"          # no ranged weapon printed
    toughness = 4
    wounds = 1
    leadership = "7+"
    armor_save = "4+"
    oc = 1
    infantry = True
    infiltrators = True             # rule 24.20
    stealth = True                  # rule 24.33
    reanimation_protocols = True
    flesh_hunger = True             # see game/crit_hit.py


class CryptothrallProfile(UnitProfile):
    """Datasheet: Cryptothralls (Necrons).

    Sv3+ W3 on a two-model unit that exists to stand in front of a Cryptek -
    which is what both of its abilities and its Cryptek Retinue rule are for."""
    name = "Cryptothrall"
    base_radius_in = 0.630          # 32 mm
    movement_in = 5
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 4
    wounds = 3
    leadership = "8+"
    armor_save = "3+"
    oc = 1
    infantry = True
    reanimation_protocols = True
    bound_creation = True           # see game/cryptothralls.py
    systematic_vigour = True        # see game/cryptothralls.py
    cryptek_retinue = True          # attached_units.RETINUE; see game/cryptothralls.py


class TombBladeProfile(UnitProfile):
    """Datasheet: Tomb Blades (Necrons).

    MOUNTED and FLY on a 32 mm flying base, M12" - the fastest thing this
    faction fields. Its Shieldvanes wargear TRADES that speed for a save
    (Sv3+, M8"), which is why game/tomb_blade_wargear.py overrides rather than
    improves: one half of that swap is worse, and a max() would silently keep
    the 12"."""
    name = "Tomb Blade"
    base_radius_in = 0.630          # 32 mm flying base
    movement_in = 12
    weapon_skill = "4+"
    ballistic_skill = "3+"
    toughness = 5
    wounds = 2
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    mounted = True
    fly = True                      # rule 21.03
    scouts = 9.0                    # "Scouts 9\"" - rule 24.31
    reanimation_protocols = True
    evasion_engrams = True          # see game/evasion_engrams.py



class HexmarkDestroyerProfile(UnitProfile):
    """Datasheet: Hexmark Destroyer (Necrons).

    A one-model CHARACTER whose whole datasheet is one gun and two abilities
    that fire it OUTSIDE its own Shooting phase - Inescapable Death (a cheaper,
    more accurate Fire Overwatch) and Multi-threat Eliminator (a free
    activation when something shoots a neighbour). LONE OPERATIVE is PRINTED
    here, unlike Illuminor Szeras's and Nekrosor Ammentar's, which are
    conditional grants."""
    name = "Hexmark Destroyer"
    base_radius_in = 0.984          # 50 mm - the Destroyer size, and printed
    movement_in = 8
    weapon_skill = "3+"
    ballistic_skill = "2+"
    toughness = 5
    wounds = 5
    leadership = "6+"
    armor_save = "3+"
    oc = 1
    infantry = True
    character = True
    deep_strike = True              # rule 24.09
    lone_operative = 12.0           # rule 24.24, the printed default range
    reanimation_protocols = True
    inescapable_death = True        # see game/inescapable_death.py
    multi_threat_eliminator = True  # see game/multi_threat_eliminator.py


class OphydianDestroyerProfile(UnitProfile):
    """Datasheet: Ophydian Destroyers (Necrons).

    M10" INFANTRY with a five-attack AP-2 D2 melee row and no gun at all -
    Deep Strike plus Tunnelling Horrors is how it gets there."""
    name = "Ophydian Destroyer"
    base_radius_in = 0.984          # 50 mm - printed, and the Destroyer size
    movement_in = 10
    weapon_skill = "3+"
    ballistic_skill = "4+"          # no ranged weapon printed
    toughness = 5
    wounds = 3
    leadership = "7+"
    armor_save = "4+"
    oc = 2
    infantry = True
    deep_strike = True              # rule 24.09
    reanimation_protocols = True
    tunnelling_horrors = True       # see game/tunnelling_horrors.py


class NekrosorAmmentarProfile(UnitProfile):
    """Datasheet: Nekrosor Ammentar (Necrons).

    T8 W9 with a 4+ invulnerable on an 80 mm INFANTRY base, three auras and
    Fights First - the Destroyer Cult's EPIC HERO.

    THE 80 MM IS KEPT, and that is a decision rather than a transcription
    reflex. The standing user instruction "alle Destroyer sollen die gleiche
    Groesse haben" is why both Lords sit on 50 mm despite printing 60 mm, and
    the reason recorded with it is rule 19.01: a Lord LEADS a Destroyer squad
    and is merged into it, so a bigger base would be seen shoulder to shoulder
    with 50 mm ones. Nekrosor Ammentar prints no LEADER line at all - he can
    never be merged into anything - so that reason does not reach him, and his
    two stage-mates (Hexmark Destroyer, Ophydian Destroyers) print 50 mm
    anyway. Every model whose datasheet NAME says "Destroyer" is still 50 mm
    here; this one's does not."""
    name = "Nekrosor Ammentar"
    base_radius_in = 1.575          # 80 mm
    movement_in = 10
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 8
    wounds = 9
    leadership = "6+"
    armor_save = "3+"
    oc = 3
    invulnerable_save = "4+"
    infantry = True
    character = True
    epic_hero = True
    fights_first = True             # rule 24.13 (CORE), not rule 11.04's post-charge grant
    deep_strike = True              # rule 24.09
    reanimation_protocols = True
    protective_disciples = True         # see game/nekrosor_ammentar.py
    infectious_murder_madness = True    # see game/nekrosor_ammentar.py
    prophet_of_destruction = True       # see game/nekrosor_ammentar.py
    nullstone_field_generator = True    # see game/nekrosor_ammentar.py


class IlluminorSzerasProfile(UnitProfile):
    name = "Illuminor Szeras"
    base_radius_in = 1.575          # 80 mm
    movement_in = 8
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 8
    wounds = 9
    leadership = "6+"
    armor_save = "2+"
    oc = 3
    invulnerable_save = "4+"
    feel_no_pain = "4+"
    infantry = True
    character = True
    epic_hero = True
    reanimation_protocols = True
    illuminor = True                        # conditional Lone Operative, see game/illuminor.py
    mechanical_augmentation = 3             # printed 3", grows by 3" a phase to a maximum of 12"
    mechanical_augmentation_max = 12
    atomic_energy_manipulator = 3           # see game/mechanical_augmentation.py
    # NOTE: no `leader`. Szeras has no printed LEADER line - his Aura is how he
    # helps a unit, and that is a range test, not an attachment.


class CanoptekWraithProfile(UnitProfile):
    name = "Canoptek Wraith"
    base_radius_in = 0.984          # 50 mm
    movement_in = 10
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 6
    wounds = 4
    leadership = "8+"
    armor_save = "3+"
    oc = 2
    invulnerable_save = "4+"
    beasts = True
    fly = True
    reanimation_protocols = True
    wraith_form = True              # see game/wraith_form.py


class SkorpekhDestroyerProfile(UnitProfile):
    name = "Skorpekh Destroyer"
    base_radius_in = 0.984          # 50 mm
    movement_in = 8
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 6
    wounds = 3
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    infantry = True
    reanimation_protocols = True
    whirling_onslaught = True       # see game/destroyer_cult.py


class SkorpekhLordProfile(UnitProfile):
    name = "Skorpekh Lord"
    # THE FOURTH DESTROYER-CULT DATASHEET, and it takes the same table size as
    # the other three on the user's standing instruction ("alle Destroyer
    # sollen die gleiche Groesse haben"). Printed 60 mm, so this is a
    # reduction, exactly like the two Lokhust sheets. It matters more here than
    # there: he LEADS Skorpekh Destroyers, so under 19.01 he is merged into
    # their unit and stands shoulder to shoulder with 50 mm bases - a 60 mm
    # Lord inside a 50 mm squad is where the mismatch would actually be seen.
    base_radius_in = 0.984          # printed 60 mm, table size 50 mm (the Skorpekh size)
    movement_in = 8
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 7
    wounds = 7
    leadership = "6+"
    armor_save = "3+"
    oc = 2
    invulnerable_save = "4+"
    infantry = True
    character = True
    leader = True                   # rule 24.22 - the pairing itself is UnitPoints.leads
    reanimation_protocols = True
    # NOTE: NOT noble. His printed keywords are INFANTRY, CHARACTER, DESTROYER
    # CULT, SKORPEKH LORD, NECRONS - the Overlord is the roster's only NOBLE,
    # so leading a unit with this model does NOT switch on Guardian Protocols.
    united_in_destruction = True    # see game/united_in_destruction.py
    crimson_harvest = True          # see game/mortal_wound_abilities.py


class LokhustDestroyerProfile(UnitProfile):
    name = "Lokhust Destroyer"
    # ALL THREE DESTROYER DATASHEETS SHARE ONE TABLE SIZE - the Skorpekh
    # Destroyers' printed 50 mm - on the user's instruction ("alle Destroyer
    # sollen die gleiche Groesse haben"). Printed 60 mm for this one, so it is
    # a reduction; see SkorpekhDestroyerProfile, which is where the number
    # comes from and which is what the tests pin these against.
    base_radius_in = 0.984          # printed 60 mm, table size 50 mm (the Skorpekh size)
    movement_in = 8
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 6
    wounds = 3
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    fly = True
    reanimation_protocols = True
    hard_wired_for_destruction = True   # see game/destroyer_cult.py


class LokhustLordProfile(UnitProfile):
    name = "Lokhust Lord"
    # The Destroyer table size again, for the same reason as the Skorpekh Lord
    # ("alle Destroyer sollen die gleiche Groesse haben"): printed 60 mm, and
    # he leads Lokhust Destroyers or Lokhust Heavy Destroyers, so under 19.01
    # he stands inside a squad of 50 mm bases.
    base_radius_in = 0.984          # printed 60 mm, table size 50 mm (the Skorpekh size)
    movement_in = 8
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 6
    wounds = 6
    leadership = "6+"
    armor_save = "3+"
    oc = 2
    invulnerable_save = "4+"
    # MOUNTED, not INFANTRY - the only Necron character here that is, and the
    # reason the Skorpekh Lord and this one cannot share a keyword test.
    mounted = True
    fly = True
    character = True
    leader = True                   # rule 24.22 - the pairing itself is UnitPoints.leads
    reanimation_protocols = True
    # NOT noble, like the Skorpekh Lord: the Overlord remains the roster's only
    # NOBLE, so leading with this model does not switch on Guardian Protocols.
    leading_ranged_crit_on_5 = True  # printed here as "Destroyer Cult"; see game/crit_hit.py
    driven_by_hatred = True         # see game/destroyer_cult.py


class LokhustHeavyDestroyerProfile(UnitProfile):
    name = "Lokhust Heavy Destroyer"
    # The same table size as the other two Destroyer datasheets - see
    # LokhustDestroyerProfile above. Deliberately the SAME number rather than
    # three literals: a shared size written down three times drifts apart the
    # next time one of them is touched, so the tests pin all three against
    # SkorpekhDestroyerProfile, which is where the 50 mm actually comes from.
    #
    # This is a GAMEPLAY number, not only a cosmetic one: edge_distance()
    # reads the radius, so Engagement Range, overlap, coherency and formation
    # packing all move with it. Smaller is the wanted direction here for the
    # reason the movement section records - six 60 mm bases are among the
    # worst-fitting footprints on this terrain.
    base_radius_in = 0.984          # printed 60 mm, table size 50 mm (the Skorpekh size)
    movement_in = 8
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 6
    wounds = 4
    leadership = "7+"
    armor_save = "3+"
    oc = 2
    fly = True
    reanimation_protocols = True
    optimised_for_slaughter = True      # see game/destroyer_cult.py


class DoomsdayArkProfile(UnitProfile):
    name = "Doomsday Ark"
    # Matched to the other grav tanks (Falcon, Devilfish, Wave Serpent, Kill
    # Rig), not to the printed 60 mm - user: "doomsday Ark so gross wie die
    # anderen panzer: falcon und devilfish". Third case of a base deviating
    # from its printed size on purpose, after the Falcon (matched to the
    # Devilfish) and the three MOUNTED jetbikes.
    #
    # Note this makes the Ark BIGGER, where every previous request of this
    # kind made something smaller - and it is the only unit here that grows.
    # It is a real gameplay change in the harder direction: a 2.1" radius is
    # nearly twice the 1.181" it had, so the corridors on map 3 (where it now
    # fields) are correspondingly tighter for it.
    base_radius_in = 2.1            # matched to the other grav tanks, not the printed 60 mm
    movement_in = 10
    weapon_skill = "4+"
    ballistic_skill = "3+"
    toughness = 9
    wounds = 14
    leadership = "7+"
    armor_save = "3+"
    oc = 5
    invulnerable_save = "4+"
    vehicle = True
    fly = True
    reanimation_protocols = True
    overwhelming_obliteration = True    # see game/overwhelming_obliteration.py
    damaged_threshold = 5               # "Damaged: 1-5 Wounds Remaining" -> -1 to its own Hit rolls, see game/shooting.py's _damaged_modifier()
    deadly_demise = 3                   # documentation leftover only, see deadly_demise_notation below
    deadly_demise_notation = D3()       # "Deadly Demise D3"


class CtanShardOfTheVoidDragonProfile(UnitProfile):
    """The C'tan Shard of the Void Dragon.

    Necrodermis is `damage_reduction`, the same flat -1 the Overlord's
    Implacable Resilience prints, so both read one module rather than two."""
    name = "C'tan Shard of the Void Dragon"
    base_radius_in = 1.575          # 80 mm
    movement_in = 10
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 11
    wounds = 16
    leadership = "6+"
    armor_save = "3+"
    oc = 4
    invulnerable_save = "4+"
    feel_no_pain = "5+"
    monster = True
    character = True
    epic_hero = True
    fly = True
    deep_strike = True
    reanimation_protocols = True
    matter_absorption = True        # see game/mortal_wound_abilities.py
    damage_reduction = 1            # "Necrodermis", see game/damage_reduction.py
    enslaved_star_god = True        # "cannot be your WARLORD" - a documented no-op, this engine has no Warlord
    deadly_demise = 6               # documentation leftover only, see deadly_demise_notation below
    deadly_demise_notation = D6()   # "Deadly Demise D6"


# ---------------------------------------------------------------------------
# Death Guard - see game/factions/death_guard.py
#
# EVERY profile here carries nurgles_gift = True. That is not decoration: the
# army rule is printed on every Death Guard datasheet, so the flag doubles as
# this engine's "is this a DEATH GUARD model" test for the aura, and
# game/death_lords_chosen.py falls back to it for a squad built without a
# datasheet. A new Death Guard profile that forgets it is invisible to the
# whole faction.
#
# TWO BASE SIZES ARE DECISIONS RATHER THAN TRANSCRIPTIONS, both stated here so
# nobody "corrects" them later:
#
#   * DEFILER: the printed base is 160 mm, which would be a radius of 3.15" -
#     half again as large as anything else in this engine. It plays at 2.1"
#     instead, the size the Battlewagon, Kill Rig, Falcon, Devilfish, Wave
#     Serpent and Doomsday Ark all use. USER DECISION, and the third of its
#     kind after the Falcon (matched to the Devilfish) and the three jetbikes
#     (brought to 45 mm) - so BOTH numbers are named here and on the line
#     itself, to stop anyone "correcting" it back later. It is a gameplay
#     number, not a cosmetic one: edge_distance() reads it, so Engagement
#     Range, overlap, coherency and formation packing all move with it.
#   * PLAGUEBURST CRAWLER: its datasheet prints NO base at all (it has the
#     FRAME keyword). 2.1" is chosen as the engine's established big-vehicle
#     size rather than invented from the model's hull, so it sits alongside the
#     Battlewagon and the Doomsday Ark it plays like.
# ---------------------------------------------------------------------------


class PlagueMarineProfile(UnitProfile):
    """Statline shared by the Plague Champion below - only squad_leader and the
    default loadout differ, which is why the Champion subclasses this."""
    name = "Plague Marine"
    base_radius_in = 0.63  # 32 mm
    movement_in = 5
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 6
    wounds = 2
    leadership = "6+"
    armor_save = "3+"
    oc = 2
    infantry = True
    nurgles_gift = True  # the DEATH GUARD army rule - see game/nurgles_gift.py


class PlagueChampionProfile(PlagueMarineProfile):
    name = "Plague Champion"
    squad_leader = True


class PoxwalkerProfile(UnitProfile):
    """Sv 7+ - no armour save any AP can improve, and the worst in this engine.
    Its survivability is entirely the Feel No Pain 5+."""
    name = "Poxwalker"
    base_radius_in = 0.5  # 25 mm
    movement_in = 5
    weapon_skill = "5+"
    ballistic_skill = "5+"
    toughness = 4
    wounds = 1
    leadership = "8+"
    armor_save = "7+"
    oc = 1
    infantry = True
    infiltrators = True          # "CORE: Infiltrators" (24.20)
    feel_no_pain = "5+"          # "CORE: Feel No Pain 5+" (24.12)
    nurgles_gift = True
    curse_of_the_walking_pox = True  # this datasheet's own ability - see game/curse_of_the_walking_pox.py


class TyphusProfile(UnitProfile):
    name = "Typhus"
    base_radius_in = 0.984  # 50 mm
    movement_in = 5
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 7
    wounds = 6
    leadership = "6+"
    armor_save = "2+"
    invulnerable_save = "4+"
    oc = 1
    infantry = True
    character = True
    psyker = True
    leader = True
    deep_strike = True
    nurgles_gift = True
    destroyer_hive = True  # this model's own ability: while LEADING, melee attacks targeting his unit are -1 to Hit - see game/destroyer_hive.py
    eater_plague = True    # this model's own PSYCHIC ability: one enemy unit within 18" and visible takes D6 (or D3+3 on a 6) mortal wounds, and a 1 hurts his OWN unit - see game/mortal_wound_abilities.py


class MalignantPlaguecasterProfile(UnitProfile):
    """No invulnerable save at all, unlike every other character in this list -
    checked rather than assumed, since a PSYKER without one is unusual."""
    name = "Malignant Plaguecaster"
    base_radius_in = 0.63  # 32 mm
    movement_in = 5
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 6
    wounds = 4
    leadership = "6+"
    armor_save = "3+"
    oc = 1
    infantry = True
    character = True
    psyker = True
    leader = True
    nurgles_gift = True
    gift_of_contagion = True   # while LEADING, that unit's attacks against an Afflicted target gain [SUSTAINED HITS 1] - see game/gift_of_contagion.py
    pestilent_fallout = True   # after this model shoots, one hit enemy INFANTRY unit is enfeebled (-2" Move) - see game/pestilent_fallout.py


class DaemonPrinceOfNurgleProfile(UnitProfile):
    """T12/W10/Sv2+/Inv4+ - the toughest single model in this engine. It has NO
    Leader line at all: Death Guard Defenders is what protects it instead."""
    name = "Daemon Prince of Nurgle"
    base_radius_in = 1.18  # 60 mm
    movement_in = 8
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 12
    wounds = 10
    leadership = "6+"
    armor_save = "2+"
    invulnerable_save = "4+"
    oc = 3
    monster = True
    character = True
    deadly_demise = 3  # documentation leftover only, see deadly_demise_notation - same convention as the Devilfish
    deadly_demise_notation = D3()  # "Deadly Demise D3"
    nurgles_gift = True
    death_guard_defenders = True   # within 3" of a friendly DEATH GUARD INFANTRY unit, this model has Lone Operative - see game/death_guard_defenders.py
    fevered_strategist = True      # once per battle round, -1 CP on a Stratagem targeting a friendly DEATH GUARD unit within 12" - see game/fevered_strategist.py
    miasma_of_pestilence = True    # a friendly DEATH GUARD unit within 6" has the Benefit of Cover against ranged attacks - see game/miasma_of_pestilence.py


class ChaosSpawnProfile(UnitProfile):
    name = "Chaos Spawn"
    base_radius_in = 0.984  # 50 mm
    movement_in = 8
    weapon_skill = "4+"
    ballistic_skill = "4+"
    toughness = 7
    wounds = 4
    leadership = "7+"
    armor_save = "4+"
    oc = 1
    beasts = True
    deadly_demise = 1        # "Deadly Demise 1" - a flat 1, so no notation
    feel_no_pain = "5+"
    scouts = 6.0             # "Scouts 6\"" (24.31)
    nurgles_gift = True
    lethal_ichor = True      # each melee attack allocated to this unit may cost the attacker a mortal wound - see game/lethal_ichor.py


class DeathshroudTerminatorProfile(UnitProfile):
    name = "Deathshroud Terminator"
    base_radius_in = 0.787  # 40 mm
    movement_in = 5
    weapon_skill = "2+"
    ballistic_skill = "2+"
    toughness = 7
    wounds = 4
    leadership = "6+"
    armor_save = "2+"
    invulnerable_save = "4+"
    oc = 1
    infantry = True
    deep_strike = True
    nurgles_gift = True
    silent_bodyguard = True   # a CHARACTER leading this unit has Feel No Pain 4+ - see game/feel_no_pain.py
    death_approaches = True   # its Deep Strike may arrive 6" from an Afflicted enemy unit and 8" from any other - see game/death_approaches.py


class DeathshroudChampionProfile(DeathshroudTerminatorProfile):
    name = "Deathshroud Champion"
    squad_leader = True


class DefilerProfile(UnitProfile):
    """W18 and OC5 are both the largest in this engine. Its base is a table
    size, not the printed one - see the section header."""
    name = "Defiler"
    base_radius_in = 2.1  # printed 160 mm (r 3.15"); TABLE size 2.1", matched to the Battlewagon/Falcon - user decision, see the section header
    movement_in = 12
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 11
    wounds = 18
    leadership = "6+"
    armor_save = "3+"
    invulnerable_save = "5+"
    oc = 5
    vehicle = True
    walker = True
    damaged_threshold = 6  # "Damaged: 1-6 Wounds Remaining" -> -1 to this model's own Hit rolls
    deadly_demise = 6      # documentation leftover only, see deadly_demise_notation
    deadly_demise_notation = D6()  # "Deadly Demise D6"
    nurgles_gift = True
    scuttling_walker = True  # moves through models and terrain; may pass through Engagement Range but not end there - see game/scuttling_walker.py
    barrage_of_filth = True  # after this model shoots, one hit enemy unit loses the Benefit of Cover until the end of the phase - see game/barrage_of_filth.py


class FoetidBloatDroneProfile(UnitProfile):
    name = "Foetid Bloat-drone"
    base_radius_in = 1.18  # 60 mm
    movement_in = 10
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 9
    wounds = 10
    leadership = "6+"
    armor_save = "3+"
    invulnerable_save = "5+"
    oc = 3
    vehicle = True
    fly = True
    deadly_demise = 3
    deadly_demise_notation = D3()
    nurgles_gift = True
    hovering_death = True  # eligible to shoot and declare a charge in a turn it Fell Back - see game/hovering_death.py


class MyphiticBlightHaulerProfile(UnitProfile):
    name = "Myphitic Blight-hauler"
    base_radius_in = 1.575  # 80 mm
    movement_in = 10
    weapon_skill = "3+"
    ballistic_skill = "3+"
    toughness = 9
    wounds = 10
    leadership = "6+"
    armor_save = "3+"
    invulnerable_save = "5+"
    oc = 3
    vehicle = True
    deadly_demise = 3
    deadly_demise_notation = D3()
    nurgles_gift = True
    # Its ability is printed under the SAME NAME as the Tankbustas' - "Tank
    # Hunters", +1 to Hit and +1 to Wound against MONSTER/VEHICLE - but with
    # one extra clause: "IN YOUR SHOOTING PHASE". The Ork version has no phase
    # restriction and applies in melee too. So this is a SEPARATE flag rather
    # than a reuse of tank_hunters: sharing it would silently hand this model
    # the bonus with its Gnashing Maw as well. The narrower reading is also the
    # safe one - it cannot grant more than the printed text does. See
    # squad.py's tank_hunters_modifiers().
    tank_hunters_ranged_only = True


class PlagueburstCrawlerProfile(UnitProfile):
    """Its datasheet prints no base at all (the FRAME keyword); see the section
    header for why 2.1" was chosen."""
    name = "Plagueburst Crawler"
    base_radius_in = 2.1  # no printed base - the engine's big-vehicle size
    movement_in = 10
    weapon_skill = "4+"
    ballistic_skill = "3+"
    toughness = 10
    wounds = 12
    leadership = "6+"
    armor_save = "2+"
    invulnerable_save = "5+"
    oc = 3
    vehicle = True
    damaged_threshold = 4  # "Damaged: 1-4 Wounds Remaining" -> -1 to this model's own Hit rolls
    deadly_demise = 3
    deadly_demise_notation = D3()
    nurgles_gift = True
    spore_laced_shock_waves = True  # its Plagueburst mortar showers the target and everything within 3" - see game/spore_laced_shock_waves.py
