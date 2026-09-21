# Orks: Codex 2026-09

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die Ork-Armeeregel (2026-09-Codex): Waaagh!, riled up, War Cry — Etappe E1

Plan: `C:\Users\Andre\.claude\plans\transient-munching-boot.md`. Gedruckter Text in
`rules/orks/army_rules.md`; die Module tragen ihn im Docstring.

- **Riled up ist ein Zustand PRO EINHEIT** (`game/riled_up.py`), nicht mehr pro Spieler. Gespeichert
  wird die FRIST `Squad.riled_up_expires_turn` (Zugserie `(battle_round-1)*2 + turn_index_in_round`,
  in `SQUAD_FLAGS`), abgeleitet `Squad.riled_up` (in `SQUAD_FLAGS_EXCLUDED`) — gestempelt von
  `refresh()` am Beginn jeder Phase (main.py, direkt nach dem Power-Matrix-Stempel, VOR War Crys
  Angebot), bei Schlachtbeginn und nach einem Load, und von `grant()` sofort. „Bis Ende des nächsten
  Zuges" = Serie+2; „bis Beginn deines nächsten Zuges" = +2 aus dem eigenen, +1 aus dem gegnerischen
  Zug. `grant()` lehnt eine Einheit ohne die Fähigkeit ab, und die spätere Frist gewinnt.
- **Drei Leser, nichts gefädelt:** 5+ InSv in `invulnerable_save.effective_invulnerable_save()`,
  [ASSAULT] in `ShootingController._adjusted_weapon()` UND `coldstar.weapon_has_assault()` (§7),
  Charge nach Advance in `move_exceptions.may_charge_after_advancing(squad)`. Jeder `waaagh=`-Parameter
  ist entfernt (Damage-Sessions, FNP, Save-Schwellen/-Überschrift, alle drei Angriffs-Controller);
  `test_ork_army_rules.py` §12 fegt `game/` und `ai/` per AST.
- **War Cry (`game/war_cry.py`):** „At the start of THE Command phase" → in JEDER Command-Phase
  angeboten, dem Phasenbesitzer zuerst; einmal pro Schlacht pro Armee. Mensch: Prompt mit rotem
  Decline. KI: injizierte `agent_driver.war_cry_verdict(player, tracker, tokens)` (0 API-Calls) —
  **seit 2026-09-21 die UHR allein: eigene Command-Phase, `battle_round >= WAR_CRY_ROUND = 2`.**
  Die bis dahin gebaute Reichweiten-Heuristik (≥ min(alle, max(2, ⌈40 %⌉)) der Waaagh!-Einheiten mit
  Feind in Move+Advance+12", gegnerisch dieselbe Schwelle in 18", sonst ab Runde 3) ist gestrichen:
  ihre 12" waren der MAXIMALE 2W6-Charge als gegeben, also feuerte sie direkt nach der Aufstellung.
  Sie hatte die User-Vorgabe ersetzt, die schon das alte `_maybe_call_waaagh()` trug. Siehe
  `## Zwei KI-Fragen zur neuen Ork-Liste` in `docs/stand/meldungen-4.md` für die Messung.
  `orks_players` aus `waaagh.qualifying_players()`: `None` = unbeschränkt (Harness), LEERE Menge =
  echte Absage. Die Nutzung steht auf den Einheiten (`Squad.war_cry_called`, gespeichert). Die erste
  Command-Phase bietet `begin_battle()` an, beim Resume nicht (`resuming=True`). **Benannte Grenze:**
  der Legacy-Pfad `--no-deployment` bietet für die allererste Command-Phase keinen War Cry an.
  §18 des Wiring-Wächters nimmt genau diese eine `PLAYERS`-Schleife ungetaggt aus (jeder Spieler
  bekommt seine eigene Frage — keine Einheitenwahl).
- **Advance-Reroll auf geteilter Maschine:** `game/advance_reroll_offer.py` (aus Superlative Strategist
  extrahiert; ein Träger besitzt `LABEL` + `applies()`), `WaaaghAdvanceRerollController` in
  `waaagh.py`, angeboten in `_acknowledge_pending_roll()` VOR `acknowledge()` und als
  „Re-roll Advance"-Knopf im Würfelpanel; einmal pro Wurf geclaimt; KI rerollt unter 4.
- **Unstable Energies** (`game/unstable_energies.py`): `UnitProfile.psyker_level` (Kill Rig 1),
  Rundenledger `Squad.unstable_energies_round/_spent` gespeichert, ruht bis E3e. **Da Boss** ist ein
  belegter No-op (kein Warlord-Bezeichner in `game/`/`ai/`), die **Special Move Types** nennt kein
  gebautes Ork-Blatt.
- **Stillgelegt:** `WaaaghController`, der alte Nahkampfbonus (+1 S/+1 A) samt Da Biggest and da
  Best, Dead Brutal und Krumpin'-Time-FNP, `_maybe_call_waaagh`. Die Variable
  `waaagh_notice_overlay` bleibt (Harnesses), ihr Text ist „WAR CRY!".
- **Gemessen:** 20 Boyz + Warboss gegen 20 Necron Warriors, eine Nahkampfrunde
  (`damage_estimate`): alter Waaagh! **26.8**, riled up **15.9** erwartete Wunden (**59 %**); die
  Boyz allein kamen alt auf 24.0 gegen 20 Modelle — die Schätzung deckelt keinen Overkill.
  `measure_advance_usage.py`: Advance im riled-up-Zug +15 Punkte mittlere Charge-Chance, 2 von 8
  Münzwürfen werden zum Favoriten.
- **`selfplay.py` lehnt einen War-Cry-Prompt für Player 1 ab** (wie Starflare) — sonst hängt jeder
  Lauf mit einem Ork-Player-1 in der ersten Command-Phase.
- **Getestet:** neu `test_ork_army_rules.py` (**133/133**), `ab_ork_army_rules.py` (**52 Sonden,
  56 Läufe, alle beißend**; ein Absturz in `test_advance_usage.py` — `next()` ohne Default — gefunden
  und degradiert), `verify_ork_army_rules.py` (echtes `main()`, Orks auf BEIDEN Seiten: War Cry
  in Player 1s UND Player 2s Command-Phase gefragt — Decline, dann Use, danach nie wieder —, die KI
  per Verdict ohne Prompt, 0 von 13 MockAgent-Entscheidungen zeigten War Cry oder den Reroll; 14/14
  Einheiten riled up, Battlewagon 6+ → 5+, Schusstypen nach Advance `[]` → `['Assault']`, Charge
  nach Advance nein → ja, main()s Refresh hält bis zur Frist; „Re-roll Advance"-Knopf für den
  Menschen, die KI wirft ihre Advance-1 ohne Prompt neu. `--neutralize` kehrt alles um. Gestellt:
  Orks auf beiden Seiten, die Antworten des Menschen, zwei Advance-Würfe — und zwei stehende
  Menschen-Prompts eines Ork-Player-1 (Spirit of Gork, 'Ard as Nails), die selfplay nicht beantwortet
  und die den Lauf sonst nach 5 Phasen anhielten, per letzter Option abgelehnt und benannt). Nachgezogen: `test_ere_we_go.py` (in E2 gelöscht),
  `test_advance_usage.py` (43), `test_necron_ai.py` §8, `test_event_chain_wiring.py` §18.
  `verify_rules_vs_engine.py` **173**, `CORPUS_AHEAD` **17** (beides unverändert). Volle Regression
  **234 Suiten, ~22442 Prüfungen, 233 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett
  grün; `selfplay.py map2 1500` mit Orks gegen Necrons in beiden Sitzordnungen exit 0.

## War Horde (2026-09-Codex): Detachment-Regel, vier Enhancements, sechs Stratagems — Etappe E2

Plan: `C:\Users\Andre\.claude\plans\transient-munching-boot.md`. Gedruckter Text in
`rules/orks/detachments/War Horde.md`; jedes Modul trägt ihn im Docstring. **Die Ork-Liste fieldet
War Horde** (also nicht dormant), `armies/orks.json` ist unverändert. Zwei Commits: Teil 1
(`1786db5`) baut die Nähte, Teil 2 die Regeln.

**Teil 1 — drei Nähte und die Stilllegung:**
- Gate `config.WAR_HORDE_PLAYERS` wie jedes Detachment (`game/war_horde.py`); Get Stuck In
  ([SUSTAINED HITS 1] im Nahkampf) liest es.
- `extra_attack_dice()` liest in `shooting.py` UND `fight.py` die ANGEPASSTE Waffe
  (`test_event_chain_wiring.py` §27) — sonst würfelt ein Laufzeit-Grant [BLAST]/[CLEAVE]/[RAPID FIRE]
  keinen Zusatzwürfel.
- `battle_shock.set_battle_shocked(squad, source)` ist die EINE Tür nach „becomes battle-shocked",
  mit modulweiten Listenern (`add_became_battle_shocked_listener`, geleert je Schlacht in `main()`);
  die drei direkten Zuweisungen gehen hindurch (§26).
- Stillgelegt: Unbridled Carnage, 'Ard as Nails, 'Ere We Go (Module, Suiten,
  `measure_ard_as_nails.py`, Panel- und Treiberpfade, Squad-Flags, `roll_bonus`-Term,
  `crit_hit`-Fold); abhängige Suiten zeigen auf lebende Träger.

**Enhancements** (`game/enh_*.py`, alle vier in `enhancements.py`s Registry; „ORKS model only" ist
CHARACTER plus `profile.orks`):
- **Headwoppa's Killchoppa** (15): +1 AP auf die Nahkampfwaffen des TRÄGERS, wenn seine EINHEIT
  gechargt hat (`charged_this_turn`); Per-Träger-Term in `_melee_attack_key()`.
- **Da Boss is Watchin'** (25): Registry-Knopf OHNE CP in der eigenen Movement-Phase, einmal pro
  Schlacht pro Armee (`Squad.da_boss_is_watchin_used`, gespeichert), riled up bis zum Beginn des
  nächsten eigenen Zuges über `riled_up.grant()`. Das Label sagt „no CP", weil die Registry jeden
  Knopf im Stratagem-Akzent zeichnet.
- **Kunnin' But Brutal** (20): beide Hälften von 09.07 in `move_exceptions` (wie Adaptive Strategy).
- **Follow Me Ladz** (20): +2" auf `coldstar.effective_movement_in()`s `total`.

**Stratagems** (`game/horde_*.py`, alle 1 CP):

| Stratagem | Weg | Naht |
|---|---|---|
| Hit 'Em Harder | Registry, Fight (beide Spieler) | [LETHAL HITS] in `fight.py`s Kette |
| Mow 'Em Down | Registry, Fight | [CLEAVE] +1 (ORKS VEHICLE ohne WALKER, gechargt) → `extra_attack_dice()` |
| Fungus-Fuel Injection | Registry, eigene Movement | +2" für MOUNTED/VEHICLE; „selected to move" = noch nicht bewegt |
| Close-Range Dakka | Registry, eigene Shooting | [RAPID FIRE] +1 in `shooting.py`s Kette → `extra_attack_dice()` |
| Breakin' Heads | Listener an der Battle-Shock-Tür | Angebot AUFGESCHOBEN (`offer_pending()` pro Frame nach dem Sweep); D3 sichtbar, Mortal Wounds teilt der EIGENE Spieler zu (Session mit Drain, §17), danach nicht mehr geschockt; „attached" = 19.01-Merge |
| Orks Is Never Beaten | `fight_controller.target_reactions` | `FightAfterDeath`-Ledger, 4+ (+1 riled up), TITANIC ausgenommen |

- Die vier Registry-Grants leben eine Phase (`Squad.*_active` in `SQUAD_FLAGS`, Reset im
  Per-Phasen-Block von `main.py`).
- **Never Beaten (User-Entscheidungen):** gilt in beiden Fight-Phasen; ein gehaltenes Modell kämpft
  mit seiner Einheit, bekommt keine Wunden zugeteilt (Sessions überspringen Tote) und zählt weder
  für OC (`level_of_control()`) noch für Kohärenz (`check_coherency()`); entfernt wird es, sobald
  SEINE Einheit gekämpft hat (`FightAfterDeath.remove_for()` aus dem Nach-Kampf-Haken) oder am
  Phasenende (`reset_phase()`). **Benannte Grenze:** `is_eligible_to_fight()` verlangt ein lebendes
  Modell — eine Einheit, deren jedes Modell gehalten wird, kann nicht gewählt werden.

**DER FUND: der geteilte Ledger hat seine Modelle nie gehalten.** Ein gehaltenes Modell hat
0 Wunden, `remove_dead_models()` läuft jeden Frame — also nahm der nächste Sweep es erneut, der
Konsument würfelte neu, und ein Fehlwurf nahm es endgültig, während sein `_owed`-Eintrag stehenblieb.
Gemessen mit dem echten GameState: gehalten auf Frame 0 → weg nach Median **1** Frame, **98 %** bis
Frame 5. **Betraf alle fünf Ledger-Regeln** (Undying Spite, Malevolent Souls, Systematic Vigour, To
Their Final Breath, Never Beaten): keine konnte in einem echten Spiel je zurückschlagen, und ihre
Suiten riefen den Ledger direkt, sahen also den zweiten Frame nie. Fix: `Token.kept_after_death`
(gesetzt von `_keep_up()`, gelöscht von `_take_off()`), `remove_dead_models()` überspringt es,
`_keep_up()` dedupliziert `_owed`, `scene_io.capture()` schreibt ein gehaltenes Modell nicht als
lebendes. Danach: 950 von 2000 Versuchen gehalten, jedes volle 100 Frames auf dem Brett.

**KI** (0 API-Calls): Da Boss für die dem Feind nächste nicht-riled-up Einheit mit Feind in
Advance-Reichweite plus Charge; Fungus-Fuel, wenn der nächste Feind weiter als Move und höchstens
Move+2" weg ist; Close-Range Dakka ab 4 erwarteten Zusatzwürfeln; Hit 'Em Harder ab 2.0 erwarteten
Zusatzwunden gegen einen engagierten Feind (10 Boyz kommen auf 1.61 und behalten den CP); Mow 'Em
Down gegen mindestens 5 Modelle. Diese fünf als `_handle_*` in `ai/agent_driver.py`; Breakin' Heads
(ab 6 Restwunden und Objective- oder 9"-Feindnähe) und Never Beaten (ab 2 erwarteten Verlusten)
antworten über `auto_players` plus injiziertes Urteil.

**Getestet:** neu `test_ork_war_horde.py` (**250/250**, zwölf Abschnitte, u. a. der Ledger über fünf
Frames gegen den echten Sweep und ein Sweep über die fünf `FightAfterDeath(`-Module) und
`test_ork_detachment_ui.py` (**139/139** — Liveness, 5×2×5-Phasenmatrix, gegnerischer Fight für
Hit/Mow, Detachment-Tor AM PANEL, Negative samt CP-Tor mit Da Boss bei 0 CP, isolierte Resets, der
Klick zahlt, Label gegen Korpus, AST). Neu `ab_ork_war_horde.py` (**53 Sonden, 62 Läufe, alle
beißend**; Timeout, `--check`, `--only`). **Eine biss zuerst nicht, Befund über den TEST:** „remove_for()
nimmt die Modelle ALLER Einheiten" — geprüft war nur `models_kept()`, und der Ledger listet ein Modell
weiter, das das Brett verloren hat; jetzt zusätzlich die Brettpräsenz. `game/game_state.py` ist
CRLF, ein mehrzeiliger LF-Sondenanker traf dort nicht → einzeilig. Volle Regression **233 Suiten,
~22699 Prüfungen, 232 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett grün,
`selfplay.py map2 1500` Orks gegen Necrons in beiden Sitzordnungen exit 0,
`verify_rules_vs_engine.py` **173** und `CORPUS_AHEAD` **17** unverändert.

**Im ECHTEN Spiel belegt** (`verify_ork_war_horde.py`, Orks als Player 1):

| | gefixt | `--neutralize` |
|---|---|---|
| Controller auf `main()`s Registry | alle fünf | keiner |
| Breakin' Heads an der Tür, Prompt nach dem Schock | ja, Frame +1 | nein, nie |
| Ablehnen | CP 3 → 3, weiter geschockt | — |
| gehaltenes Modell | 31 Frames, weg beim PHASENWECHSEL | nach 2 Frames erneut gefegt, dieselbe Phase |
| Knöpfe gezeichnet / außerhalb ihres WHEN | 5 von 5 / 0 | 0 von 5 / 0 |

GESTELLT: der Schock durch die Tür, das gehaltene Modell (Würfel 6, danach nur noch 1 — immer 6
hätte die Vor-Fix-Welt verdeckt) und eine Phasenrotation, die `charged_this_turn` und die
Kampfberechtigung JEDEN Frame neu stempelt: selfplay klickt weiter Next Phase, und ein echtes
Zugende löscht `charged_this_turn` — ohne das blieben Da Boss und Mow 'Em Down ungezeichnet. Die
Sonde MISST die Ablehnungen statt sie zu erzählen (Da Boss: jede Nicht-Träger-Einheit „Enhancement
not active"). `--neutralize` entfernt Listener und Registry-Adds per Import-Hook und stellt den
Vor-Fix-Sweep her.

## Ork-Mobs (2026-09-Codex): Boyz, Beast Snagga Boyz, Stormboyz, Gretchin, Meganobz — Etappe E3a

Plan: `C:\Users\Andre\.claude\plans\transient-munching-boot.md`. Drei Commits: `f1da460`
(Mehrprofilwaffen, Hunter-Profile, bedingte Keywords), `c919ef9` (die fünf Datenblätter) und die
neun Fähigkeiten. `armies/orks.json` bleibt minimal lauffähig: **14 Einheiten, 101 Modelle, 2005 pts**.

**Datenblätter (Teil 2a):** Zusammensetzungen, Wargear, Punkte, neue Waffenzeilen (Kombi, Kustom
Shoota, Burna, Rokkit Launcha, Killsaw, Thump Gun, Scavenged Shivs; Beast Snagga Choppa als
Standard/Hunter-Paar). Boss Nob → Nob; der Painboy ist SUPPORT (die SUPPORTED-BY-Zeile der Boyz).
Close-Range Dakkas KI-Zählung beachtet 24.07. **Entfallen:** Runtherd samt Toughness-Override und
Grot-Smacka; die Zwei-Leader-Erlaubnis des Boyz-Bodyguards (`can_attach()` kennt diese Ausnahmeform
nicht mehr — Kroot Carnivores drucken ein Bodyguard, es ist nicht engine-verdrahtet).

**Die neun Fähigkeiten (Teil 2b):**

| Fähigkeit | Träger | Modul | Naht |
|---|---|---|---|
| Ammo Runts | Boyz | `ork_ammo_runts.py` | Angebot in `start_shooting()`, +1 Hit in den Schuss-Modifikatoren, einmal pro Schlacht |
| Tide of Muscle | Boyz | `tide_of_muscle.py` | [LETHAL HITS] auf Nahkampfwaffen nach eigenem Charge, Fight-Adjuster-Kette |
| Never Too Busy to Fight | Boyz | `never_too_busy_to_fight.py` | hebt 16.01s Engaged-Sperre in `actions.py` |
| Mobbed | Beast Snagga Boyz | `mobbed.py` | `on_charge_move_finished` + Würfel-Queue |
| Rokkit Charge | Stormboyz | `rokkit_charge.py` | Angebot in `_start_fighting()`, Fight-Adjuster-Kette |
| Krumpin' Time | Meganobz | `krumpin_time.py` | +1 Hit im Nahkampf, solange riled up |
| Arrogant Invulnerability | Meganobz | `arrogant_invulnerability.py` | −1 AP in `save_thresholds()` |
| Downtrodden | Gretchin | `transport.squad_capacity_cost()` | Transportkapazität ⌈n/2⌉ |
| Thievin' Scavengers | Gretchin | `thievin_scavengers.py` | Ende der Movement-Phase, 14.03 Secured |

- **Lesarten (User-Entscheidungen):** Rokkit Charge gibt +1 A und +1 S PRO WAFFE (eine Notation
  bekommt `bonus + 1`) plus [HAZARDOUS]; Downtrodden zählt ⌈n/2⌉ (11 Gretchin = 6 Plätze); Mobbed −2
  ERSETZT −1 ab 13 lebenden Modellen; „+1 AP" verbessert, „-1 AP" verschlechtert.
- **`game/ap_worsening.py`, Extraktion am dritten Konsumenten** (Ramshackle, Enforcer Commander,
  Arrogant Invulnerability): `min(0, ap + 1)`, jede Quelle ein eigener Schritt, zwei komponieren zu −2.
  Arrogant Invulnerability fragt 19.04 über den Squad des zugeteilten Modells — ein Warboss in Mega
  Armour in den Meganobz ist gedeckt.
- **Downtrodden hat ZWEI Leser**, 18.02 (`embarked_model_count`, `can_embark`) UND 18.01
  (`formations.transport_capacity_used`/`embark_errors`) — die Kill-Rig-Lehre aus Necron E8. 20 Gretchin
  passen in einen Trukk, 10 Boyz + 10 Gretchin nicht.
- **Mobbed** gibt jeder engagierten feindlichen MONSTER/VEHICLE-Einheit einen Battle-Shock-Test über
  `start_forced_roll(penalty=)`; die Queue wartet einen offenen Wurf ab (`rolling_squad`/
  `pending_values`) und wird aus `main.py`s Würfel-Ack NACH dem eigenen Battle-Shock-Ack gedrainiert.
  §21 führt `mobbed` namentlich (ein weiterer Test, den Insane Bravery nicht erreicht).
- **Rokkit Charge:** Mensch Prompt, KI `agent_driver.rokkit_charge_verdict()` — Gewinn (beste
  Zusatzwunden × Punkte je Wunde des Ziels) gegen Verlust (Hazard-Fehlschläge × Punkte je Wunde der
  eigenen Einheit); 5 Stormboyz gegen ein Strike Team ja, gegen 10 Gretchin nein. Der Wunden-Tausch
  teilt `_melee_wounds_with_grant()` mit `_boosted_melee_wounds` (Waffen tauschen, `finally` zurück).
- **Ammo Runts:** `ammo_runts_used` (Schlacht) und `ammo_runts_active` (Phase) stehen in `SQUAD_FLAGS`,
  ebenso `rokkit_charge_active`; die KI nimmt Ammo Runts sofort, der Mensch bekommt „Use Ammo Runts" /
  „Save it for later".
- **Thievin' Scavengers ist neu geschrieben:** kein Wurf, kein CP, kein Controller
  (`THIEVIN_SCAVENGERS_ROLL` weg). `secure_at_end_of_movement()` läuft im
  `phase_before == PHASE_MOVEMENT`-Block NACH `update_control()` mit `mover_before`; §8 führt ihn in
  `_END_OF_PHASE_OFFERS`. „Controlling" sind die drei Filter von `level_of_control()` (Footprint,
  effektive OC > 0, nicht geschockt), am eigenen Trupp gefragt.
- **Entfallen in 2b:** Monster Hunters (Modul und Profil-Feld; die Test-Labels zeigen auf Grim Reapers,
  der Reroll-Schritt heißt `hit_optional_reroll`) und der alte Thievin'-CP-Wurf. Die
  Krumpin'-Time-FNP aus E1 bleibt weg (Quell-Pin in `test_ork_army_rules.py`).

**Getestet:** neu `test_ork_mobs.py` (**134/134**, zwölf Abschnitte — jede Fähigkeit durch ihren
echten Controller, Mobbed mit echtem `BattleShockController`, Downtrodden über `embark_errors`,
Thievin' auf map2s Central Objective samt drei Negativen, Stilllegungen, AST-Pins) und
`ab_ork_mobs.py` (**49 Sonden, alle beißend**). **Zwei bissen zuerst nicht, beide Befunde über den
TEST:** die Tide-of-Muscle-Mutation (die Kette reicht eine KOPIE, jetzt zusätzlich ein direkter
Modultest) und der Thievin'-Sweep fehlte in §8s Namensliste. Volle Regression **236 Suiten, ~22885
Prüfungen, 235 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke` grün, `selfplay.py map2 1500` Orks
gegen Necrons in beiden Sitzordnungen exit 0. `verify_rules_vs_engine.py` **173 → 133** (66
Ork-Zeilen, keine für die fünf Blätter), `CORPUS_AHEAD` **17 → 12**. `measure_crowded_movement.py`:
gedrängt **65 % / 217.2"**, isoliert **87 % / 292.2"**.

**Im ECHTEN Spiel belegt** (`verify_ork_mobs.py map2 3000`, Orks als Player 1; 10/10, unter
`--neutralize` 8/8 Abwesenheitsprüfungen):

| | gefixt | `--neutralize` |
|---|---|---|
| Ammo Runts / Rokkit Charge an den Live-Controllern, Mobbed am Charge-Haken | ja | nein |
| Thievin'-Sweep an Player 1s Movement-Grenze | Frame 150, `Objective West` gesichert | kein Sweep |
| Mobbed über `main()`s Listener und Ack | `Battle-Shock Roll - Mobbed (Ld 7+, -1 to the test)` | kein Wurf |
| Ammo-Runts-Prompt | `Use Ammo Runts` / `Save it for later` | keiner |

GESTELLT: Orks als Player 1, die Phasen, Gretchin auf einem feindfreien Objective, eine gebaute
Beast-Snagga-Einheit neben einer feindlichen MONSTER/VEHICLE (die Liste setzt ihre einzige in einen
Kill Rig) und der „Charge beendet"-Moment. `--neutralize` nimmt die Nähte per Import-Hook zurück, die
Dateien auf der Platte bleiben unberührt.

## Ork-Charaktere (2026-09-Codex): Warboss, Warboss in Mega Armour, Beastboss, Painboy — Etappe E3b

Plan: `C:\Users\Andre\.claude\plans\transient-munching-boot.md`. Gedruckter Text in `rules/orks/*.md`,
jedes Modul trägt ihn im Docstring. `armies/orks.json` bleibt minimal lauffähig: **14 Einheiten,
101 Modelle, 2025 pts** (Warboss ohne Waffenwahl, Painboy ohne Gear; Golden Master bewegt nur die
Boss-Zeilen: Boyz-Mob 355 → 325, Meganobz + WMA 305 → 350, Beast Snagga + Beastboss 165 → 170).

| Fähigkeit | Träger | Modul | Naht |
|---|---|---|---|
| Boss' Ammo Runt | Warboss | `boss_ammo_runt.py` | Unterklasse von `ork_ammo_runts`' Controller; Angebot in `start_shooting()` NACH Ammo Runts, +1 Hit nur für die Gruppe des Warboss (`_attack_key()`-Term) |
| Might Is Right | Warboss | `might_is_right.py` | +3 A / +2 S auf die Nahkampfwaffen DES MODELLS, wenn seine Einheit gechargt hat; Fight-Kette plus `_melee_attack_key()`-Term |
| Dodge Dis! | Beastboss | `dodge_dis.py` | +1 Hit in BEIDEN `_hit_modifiers()`, per `unit_wide_ability()` (19.04) |
| Intimidating Motivation / Keep Huntin'! | Warboss + WMA / Beastboss | `boss_motivation.py` | Registry-Knopf ohne CP, zwei Fenster über `on_move_started`/`on_move_finished` |
| Krushin' Impetus | WMA | `krushin_impetus.py` | `MortalWoundOfferController` am Charge-Ende-Haken; ein W6 je SELBST engagiertem Modell, 3+ je eine MW |
| Crude Surgery / Catch Dat Red Bit | Painboy | `crude_surgery.py` + `heal.py` | Beginn der eigenen Command-Phase, heilt 3 nach Kernregel 02.02.04; Red Bit +D3 einmal pro Schlacht |

- **Dodge Dis! ist wörtlich gelesen** (User): die EIGENEN Angriffe der Einheit, beide Phasen.
- **Die Boss-Motivationen** („at the start or end of this unit's move") sind ein Knopf, solange ein
  Fenster offen ist: START = die Einheit war diese Phase weder bewegt, advanced noch stationär und
  kein eigener Zug läuft; END = ihr Zug ist der zuletzt beendete und seither begann keiner.
  Kandidaten sind befreundete ORKS- bzw. BEAST-SNAGGA-Einheiten in 6" (die eigene zählt mit), und
  nur, wenn es etwas bringt (geschockt, oder riled up würde länger laufen — Fehlerklasse 5). Einer
  direkt, mehrere als Brett-Pick mit Cancel, das nichts kostet. **Das Budget ist pro FÄHIGKEIT pro
  Armee pro Schlachtrunde** (`game/per_army_round_limit.py`, der Verbrauch wird auf ein Squad-Flag
  `*_round` gespiegelt, damit ein Save ihn behält): Warboss und WMA teilen Intimidating Motivation,
  ein Beastboss hat Keep Huntin'! extra. KI über die Move-Haken mit `boss_motivation_choice()`
  (geschockt zuerst, dann die punktstärkste).
- **Krushin' Impetus hat KEIN Decline** (Würfeln kostet nichts und kann nur schaden); WELCHER Feind
  ist ein Brett-Pick für den Menschen, `_best_damage_target` für die KI. Eine Einheit ohne lebenden
  WMA würfelt nicht.
- **Crude Surgery läuft automatisch** für jede Painboy-Einheit, WO sie auch steht: eine Einheit in
  Reserve heilt vom Brett aus, Wiederbelebte kehren ohne Token in `squad.models` zurück. Auf dem
  Brett setzt der MENSCH wiederbelebte Modelle über `ReturnPlacementController` (der seine eigenen
  Platzierungen queut). **Catch Dat Red Bit wird nur gefragt, wenn mehr als 3 zu heilen sind** —
  sonst kann das +D3 nicht landen —, mit „Save it for later"; KI ab 5 heilbaren Wunden
  (`CATCH_DAT_RED_BIT_MIN_HEALABLE`). `catch_dat_red_bit_used` steht in `SQUAD_FLAGS`.
- **`game/heal.py` (Extraktion am zweiten Konsumenten):** Kernregel 02.02.04 (erst beschädigte
  heilen, dann nicht-CHARACTER-Modelle mit 1 Wunde wiederbeleben, 01.02.03-Deckel) war der Rumpf von
  `reanimation_protocols.reanimate()`; das Modul re-exportiert.
- **Die Warboss-Base bleibt 0.98"** statt der gedruckten 40 mm — benannte Abweichung: alle drei Bosse
  stehen auf 50 mm, und drei Report-Suiten hängen an dieser Geometrie. Die einzige
  `verify_rules_vs_engine.py`-Zeile der vier Blätter.
- **Stillgelegt:** Ferocious Rage, Dok's Toolz, Hold Still, Grot Orderly (Module, Suiten, Felder,
  Verdrahtung) und die Waffenklassen Attack Squig, Kombi-weapon, Twin Slugga, Big Choppa, Beast Snagga
  Klaw/Beastchoppa.

**DER FUND: die KI beantwortete eine eigene Zuteilung nur für zwölf Controller.** Im echten Spiel
gemessen: Krushin' Impetus des Menschen auf 20 Necron Warriors — die 06.02-Wahl lag bei Player 2 und
keine Wunde landete (`settled: False, open choice owner: Player 2, wounds lost: 0`), weil
`_take_one_action()` eine handgepflegte Zwölferliste an `_resolve_own_damage_choice()` gab, während
`main.py`s `damage_choice_controllers` 37 kennt. Fehlerklasse 10: die eine Liste wird jetzt an
`take_one_action(damage_choice_controllers=)` gereicht und angefügt (die zwölf bleiben vorn für
Aufrufer ohne sie). **Damit ist dieselbe Lücke für rund zwei Dutzend ältere Träger mit zu** (Living
Lightning, Matter Absorption, Crimson Harvest, Eater Plague, Kroot Linebreakers, Crushing Strides,
Isha's Fury, Grenade Pack, Grav-inhibitor, Flickerjump, Wraith Form, Drakolithe, Harvester of Souls,
Monofilament Snare, Drain Life, Lord of the Storm, Malevolent Arcing, Lethal Ichor, Spore-laced,
Sickening Impact, Internal Grenade Racks, Self-Destruction, Khaine's Vengeance) — gemessen ist nur
der Krushin'-Fall, die anderen sind aus dem Code benannt. Wächter `test_event_chain_wiring.py` **§28**
(beide Enden per AST).

**Zwei Wächter mussten wachsen:** §14 zählt eine Basisklasse mit `panel_label()` als erreichbar,
wenn eine registrierte Unterklasse sie erbt (`_BASES`-Fixpunkt); §25 löst Listener nur auf, wenn der
Controller erst gebunden und dann registriert wird (`x = Class(...)`, `proactive_stratagems.add(x)`).
**Mitwandernde Pins:** `test_transport_priority.py` (Boyz-mit-Warboss-Reichweite 24" → 18"),
`test_army_select.py` (2005 → 2025), `test_weapon_characteristics.py` (`CORPUS_AHEAD` 12 → 8:
Battlewagon, Deff Dread, Deffkoptas, Flash Gitz, Kill Rig, Tankbustas, Trukk, Warbikers),
`test_player2_army.py`, `test_ork_wargear.py`, `test_ork_war_horde.py`, `test_return_placement.py`,
`measure_crowded_movement.py`.

**Ein alter Sondentreiber, zwei Befunde:** `ab_return_placement.py` trug `BASE = 132` gegen eine
179-Prüfungen-Suite, meldete also jede BEISSENDE Sonde als NICHT beißend (jetzt gemessen), und
stellte im TEXT-Modus zurück — unter Windows wurde jede sondierte Datei LF → CRLF, und
`ab_necron_hypercrypt_legion.py --check` meldete plötzlich sechs Mehrzeilen-Anker als fehlend. Jetzt
byte-genau; die neun Dateien sind zurück auf LF (`git diff --numstat` unverändert, autocrlf
normalisiert ohnehin). Zwei seit Früherem veraltete Anker sind nachgezogen und beißen.

**Getestet:** neu `test_ork_characters.py` (**228/228**, dreizehn Abschnitte — jede Fähigkeit durch
ihren echten Controller, die Boss-Motivationen über einen echten `MovementController` und das echte
`ActionPanel`, Crude Surgery mit echtem `SetupController`/`ReturnPlacementController`, die KI-Zuteilung
durch `_take_one_action()` mit und ohne geteilte Liste) und `ab_ork_characters.py` (**50 Sonden,
56 Suite-Läufe, alle beißend, keine stürzt ab**). `test_event_chain_wiring.py` **264/264**. Volle
Regression **235 Suiten, ~22924 Prüfungen, 234 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke`
komplett grün, `selfplay.py map2 1500` Orks gegen Necrons in beiden Sitzordnungen exit 0 (die KI
nimmt Boss' Ammo Runt). `verify_rules_vs_engine.py` **133 → 115** (48 Ork-Zeilen),
`measure_crowded_movement.py` unverändert gedrängt **65 % / 217.2"**, isoliert **87 % / 292.2"**.

**Im ECHTEN Spiel belegt** (`verify_ork_characters.py map2 3000`, Orks als Player 1; 17/17, unter
`--neutralize` 8/8 Abwesenheitsprüfungen):

| | gefixt | `--neutralize` |
|---|---|---|
| Boss' Ammo Runt / beide Motivationen / Krushin' am Live-Objekt | ja | nein |
| Crude Surgery an `main()`s Command-Grenze | Painboy 3/3, beide Boys zurück, vom Menschen platziert | kein Aufruf |
| Krushin' Impetus über `main()`s Charge-Listener | gewürfelt, KI teilt zu, **settled** | kein Wurf |
| Intimidating Motivation auf `main()`s Panel | gezeichnet, Brett-Pick, verbraucht | nie gezeichnet |
| Boss' Ammo Runt beim Schießen | gefragt, Ablehnen kostet nichts | nie gefragt |

GESTELLT: Orks als Player 1, die zwei Verluste und die Uhr (Player 2s Fight) vor EINEM
`advance_turn_phase()`, die WMA-Einheit neben der Necron-Einheit samt „Charge beendet"-Moment, Phase
und Auswahl für D/E. `--neutralize` nimmt die Nähte per Import-Hook zurück.

## Ork-Spezialisten (2026-09-Codex): Flash Gitz, Tankbustas — Etappe E3c

Plan: `C:\Users\Andre\.claude\plans\transient-munching-boot.md`. Gedruckter Text in
`rules/orks/Flash Gitz.md` und `rules/orks/Tankbustas.md`, jedes Modul trägt ihn im Docstring.
`armies/orks.json` bleibt minimal lauffähig: Flash Gitz 10er ohne Gear, Tankbustas im Default —
**14 Einheiten, 101 Modelle, 2105 pts** (Flash Gitz 150 → 210, Tankbustas 125 → 145).

**Datenblätter:**
- **Flash Gitz:** Kaptin + 4 bzw. 9 Flash Gitz, W3 BS4+, Choppa (`ChoppaA4Profile`, geteilt mit dem
  Tankbusta-Nob) und die Snazzgun als DREIPROFIL-Kette: Cutta (12" A1 S9 AP-3 D3+2 [HAZARDOUS]
  [MELTA 2], das getragene erste Profil; `damage = 4` ist der Mittelwert-Platzhalter) → Dakka (24" A3
  S6 AP-1 D2 [SUSTAINED HITS 1], [LETHAL HITS] nur gegen Nicht-MONSTER/VEHICLE) → Kill Shot (36" A2 S8
  AP-2 D2 [HAZARDOUS]). 105/210, ab der dritten Einheit 135/240.
- **Tankbustas:** Nob (W3, 40 mm, Choppa + zwei Rokkit Pistols) + 5 Tankbustas (W2, BS4+, Busta Rokkit
  Launcha Standard A2 S10 → Hunter A3 S12 AP-2 D3 nur gegen MONSTER/VEHICLE, Gitstikka). Eine Pistole
  des Nobs → Smash Hammer (ebenfalls Standard → Hunter); ein Tankbusta + Busta Rokkit Launcha ODER
  Pulsa Rokkit (Gear, `Token.pulsa_rokkit`). **Benannte Grenze:** „one of the following" ist nicht
  erzwungen — eine `WargearOption` kann kein Gear ausschließen (dieselbe Lücke wie Farstalker und
  Broadside). 145, ab der dritten 155.

| Fähigkeit | Träger | Modul | Naht |
|---|---|---|---|
| Finderz Keeperz | Flash Gitz | `finderz_keeperz.py` | +1 AP in `ShootingController._adjusted_weapon()`, wenn Einheit ODER Ziel in Objective-Reichweite; nie reaktiv |
| Rokkit Barrage | Tankbustas | `rokkit_barrage.py` | vierter Träger von `battle_shock_after_shooting.py`, ohne Zielbeschränkung |
| Bomb Squigs | Tankbustas | `bomb_squigs.py` | `MortalWoundOfferController` an `on_move_finished`, nur Kind `"normal"` |
| Pulsa Rokkit | Tankbustas (Gear) | `pulsa_rokkit.py` | Angebot in `start_shooting()`, Marke je Phase, +1 AP und [LETHAL HITS] in der Kette |

- **Finderz Keeperz** teilt „Einheit UND/ODER Ziel in Objective-Reichweite" mit Defend at All Costs:
  `objectives.attacker_or_target_within_range_of_objective()` ist die Extraktion am zweiten
  Konsumenten, `defend_at_all_costs.applies()` delegiert. „Diese Einheit" per 19.04
  (`unit_wide_ability()`), ein unterstützender Painboy nimmt es nicht weg.
- **Rokkit Barrage** ist der erste Träger der Basis, den die KI spielt: sie nimmt jetzt
  `auto_players`/`target_pick` (Default leer, die drei Aeldari-Träger unverändert). KI-Antwort
  `agent_driver.battle_shock_target_choice()`: nicht geschockt zuerst (ein BESTANDENER erzwungener
  Test entschockt), dann in Objective-Reichweite, dann Punkte, dann Name. **Benannte, geteilte Grenze:**
  `start_forced_roll()` startet nicht, solange ein anderer Battle-shock-Wurf offen ist — der Test
  fällt dann still aus.
- **Bomb Squigs:** zwei gespeicherte Ledger — `bomb_squigs_used` (zwei Token je EINHEIT) und
  `bomb_squigs_turn` (1-basiert, weil der Save nur Truthy-Werte behält). Ein Token ist beim BENUTZEN
  weg, auch wenn der D6 scheitert („removing one each time this ability is used"). D6 (3+) und D3 sind
  zwei sichtbare Würfe. Mensch: Brett-Pick mit rotem Decline, das nichts kostet; KI wirft sofort, Ziel
  `_best_damage_target`; „visible" ist main()s echte Sichtlinie (`_psychic_visible`).
  - **Fund beim Lesen, behoben:** gegen ein EIN-Modell-Ziel ist die `MortalWoundAllocationSession`
    im Konstruktor fertig und blieb im Slot — `why_not()` hätte danach „already being resolved"
    gemeldet und der zweite Token wäre nie werfbar gewesen. `_inflict()` räumt eine fertige Session
    sofort ab (eigene Sonde). Die anderen Leser des Slots prüfen `.done` bzw. `pending_fnp` selbst.
- **Pulsa Rokkit:** `{id(unit): target}` je Phase (Reset im Per-Phasen-Block von `main.py`), nur
  MONSTER/VEHICLE in 24", reaktiv nichts. Mensch Brett-Pick + Decline; die KI markiert immer
  (`_best_damage_target`). Der Controller steht in `main()` direkt vor `ShootingController`, weil
  `_best_damage_target` erst dort existiert — die erste Platzierung weiter oben wäre ein
  `UnboundLocalError` gewesen (Fehlerklasse 23).
- **`weapon_profiles.valued_profiles()` — die KI las Mehrprofilwaffen nur am GETRAGENEN Profil.**
  `damage_estimate`, `combat_focus` und `deployment_ai` lasen `model.weapons`; gemessen kippten die
  Flash Gitz in der Aufstellung von shooter auf assault (Reichweite 12", Ratio 0.70) — wegen eines
  [HAZARDOUS]-Profils, das `_best_profile_index()` nie feuert. Jetzt: eine Ein-Profil-Waffe ist sie
  selbst; sonst die nicht-hazardous Profile, ein Hunter-Profil nur gegen ein erlaubtes Ziel (ohne Ziel
  keins); bleibt nichts, das erste Profil. Danach Flash Gitz 24" / Ratio 1.125. **Mitbewegt,
  gemessen:** Fuegans Reichweite 24" (Searsong Lance 18" + Burning Lance 6"), Void-Dragon-Ratio
  0.23 → 0.19 (Spear Sweep), Tankbustas gegen Fahrzeuge ×1.40-1.42 (A/B in
  `test_target_priority.py` §8, das vorher die stillgelegten Tank Hunters pinnte).
- **ENTSCHEIDUNG ZUR BESTÄTIGUNG: die Ork-Home-Garnison sind auf map1-3 jetzt die Tankbustas**
  (24"-Launcha, oberstes shooter-Band), die Gretchin nur noch auf map4 (braucht 24.2"). Das folgt
  der User-Regel „fernkampfeinheiten stark bevorzugen" und widerspricht der älteren „gretchins das
  homeobjective halten"; `test_home_garrison.py` pinnt den gemessenen Stand.
- **Stillgelegt:** Gun Crazy Show-offs, der alte Ammo Runt der Flash Gitz (`game/ammo_runt.py`,
  `Token.ammo_runt`, `Squad.ammo_runt_active`, `FLASH_GITZ_AMMO_RUNT`), das Ork-`tank_hunters`-Flag
  (`tank_hunters_modifiers()` liest nur noch den Blight-hauler, `fight.py` fragt nicht mehr),
  `test_flash_gitz.py` und die Waffenklassen RokkitLuncha, TankbustaChoppa,
  TankbustaCloseCombatWeapon, Snazzgun und FlashGitzChoppa.
- **Nachgezogen:** `test_army_select.py` (2105), `test_crit_labels.py` (Dakka gegen Strike Team
  bzw. Devilfish statt Ammo Runt), `test_dice_panel_header.py`, `test_event_chain_wiring.py` §21
  (`rokkit_barrage` als zwölfter umgangener Battle-shock-Auslöser), `test_home_garrison.py`,
  `test_ork_wargear.py`, `test_player2_army.py`, `test_report_20260824.py`, `test_target_priority.py`
  (§8 neu, drei Kalibrierungen wegen der stärkeren Launchas), `test_transport_priority.py`,
  `test_weapon_characteristics.py` (`CORPUS_AHEAD` 8 → 6), `test_wound_allocation.py` (die Tankbustas
  sind jetzt der Fall mit zäherem Leader); Sondenanker in `ab_ork_mobs.py`/`verify_ork_mobs.py`.

**Getestet:** neu `test_ork_specialists.py` (**164/164**, acht Abschnitte — jede Fähigkeit durch
ihren echten Controller, Bomb Squigs auch über einen echten `MovementController`, Pulsa Rokkit und
Finderz Keeperz durch die echte Adjuster-Kette) und `ab_ork_specialists.py` (**57 Sonden, 64
Läufe, alle beißend, Restore byte-genau**). **Drei bissen zuerst nicht, alle Befunde über den TEST:**
zwei KI-Pick-Prüfungen erwarteten eine Einheit, die zugleich die reichere bzw. die erste nach Name
war (jetzt ist die richtige Antwort keins von beiden), und eine Sonde zielte auf §10, das nur Tor →
auflösbar prüft. `verify_rules_vs_engine.py` **115 → 100** (33 Ork-Zeilen),
`measure_crowded_movement.py` gedrängt **62 % / 210.2"** (vorher 65 % / 217.2", eine Welt, siehe
`## Bewegungsqualität`), isoliert unverändert **87 % / 292.3"**. `selfplay.py map2 1500` Orks gegen
Necrons in beiden Sitzordnungen exit 0.

**Im ECHTEN Spiel belegt** (`verify_ork_specialists.py map2 4000`, Orks als Player 1; 14/14, unter
`--neutralize` 6/6 Abwesenheitsprüfungen):

| | gefixt | `--neutralize` |
|---|---|---|
| Pulsa Rokkit / Rokkit Barrage / Bomb Squigs am Live-Objekt | ja | nein |
| Bomb Squigs über `main()`s Move-Listener | gefragt, Token weg, D6 → D3, 3 Wunden am Doomsday Ark | kein Prompt |
| Pulsa Rokkit beim Schießen | gefragt, markiert, Launcha AP -2 → -3 + [LETHAL HITS], Marke nach der Phasengrenze weg | kein Prompt, AP -2 |
| Rokkit Barrage über `on_squad_finished_shooting` | Test bei -1, von `main()`s Bestätigung aufgelöst | kein Test |

GESTELLT: Orks als Player 1, eine gebaute Tankbustas-Einheit mit Pulsa Rokkit neben einer sichtbaren
Player-2-Einheit, die Phasen, die Momente „Zug beendet"/„hat geschossen", die Antworten des Menschen
und Bomb-Squigs-Würfel 6 und 3. Der Doomsday Ark ist ein Modell, eine 06.02-Wahl öffnet sich im Lauf
also nicht — die Suite drainiert eine Mehr-Modell-Einheit.
