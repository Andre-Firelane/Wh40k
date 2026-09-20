# Orks: Mecha Orks (ab G2)

Fortsetzung von `docs/stand/orks-codex-2026-09-2.md` (dort steht G1: Bigboss, Weirdboy, Gunwagon),
angelegt am 2026-09-19, damit die restlichen Etappen des Plans
`C:\Users\Andre\.claude\plans\mecha-orks.md` die 42.000-Zeichen-Grenze jener Datei nicht sprengen.
Wird NICHT automatisch geladen. Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem
Thema gehört VERDICHTET in den passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine
Zeile im Verzeichnis.

## Mecha Orks G2: Big Mek in Mega Armour, Ghazghkull Thraka, der Warlord (2026-09-19)

Gedruckter Text in `rules/orks/Big Mek In Mega Armour.md` und `Ghazghkull Thraka.md` (per `--only`
in derselben Sitzung), jedes Modul trägt ihn im Docstring. `armies/orks.json` UNVERÄNDERT (G6).

**Datenblätter:**
- **Big Mek in Mega Armour** (90, App-Stand 80): M5 T6 Sv2+ W5, 40 mm, WS3+/BS4+, LEADER für Meganobz
  (und Mek Gunz, nicht gebaut). Alle Waffen außer der neuen Tellyport Blasta sind vorhandene Zeilen
  mit gleichen Zahlen (Kustom Shoota/Kombi-weapon als Meganob-Ketten, Kustom Mega-blasta, Killsaw,
  Power Klaw). Wargear: Tellyport Blasta als Zusatz, Kustom Force Field als Gear-Item
  (`Token.kustom_force_field`) — das „one of" zwischen beiden ist nicht erzwungen (die benannte
  Tankbustas-Grenze); die drei Kustom-Shoota-Tausche teilen den Cursor.
- **Ghazghkull Thraka** (300, App-Stand 235 für zwei Modelle): EIN Modell (Makari ist jetzt eine
  Fähigkeit), 80 mm, M8 T10 Sv2+ W16 OC4 InSv 4+, EPIC HERO, kein Leader-Abschnitt. Mork's Roar als
  Zweiprofil (Aimed → Point Blank 2D6+2 TORRENT), Adamantine 'Eadbutt ([EXTRA ATTACKS], schwingt
  neben der Klaw), Gork's Klaw. **Transport:** 4 Plätze in Battlewagon/Gunwagon
  (`transport.GHAZGHKULL_CAPACITY_COST`, global wie die MEGA-ARMOUR-Regel), der Trukk verweigert ihn
  (`transport_excludes`) — beides war seit E3d als „nicht modelliert" benannt.

| Fähigkeit | Träger | Modul | Naht |
|---|---|---|---|
| More Dakka | Big Mek | `more_dakka.py` | [IGNORES COVER] + riled up [SUSTAINED HITS 1] in `ShootingController._adjusted_weapon()`; das Cover-Tor liest die Kette (siehe unten) |
| Kustom Force Field | Big Mek (Gear) | `kustom_force_field.py` | 4+ InSv gegen Fernkampf für die EINHEIT in `effective_invulnerable_save()`, 19.04 komponentenweise |
| Fix Dat Armour Up | Big Mek | `fix_dat_armour_up.py` | Crude Surgerys Heilung (`heal.py`, Platzierer), aber einmal pro Schlacht → ANGEBOTEN am Beginn der eigenen Command-Phase, „Save it for later" |
| Da Grand Warlord's Ladz | Ghazghkull | `grand_warlords_ladz.py` | sechste Quelle in `conditional_lone_operative.SOURCES` |
| Makari, Hoist Dat Banner! | Ghazghkull | `makari.py` | Registry-Knopf ohne CP, Einheiten-Pick bis zur Rundenzahl, einmal pro Schlacht pro Armee |
| Prophet of da Great Waaagh! | Ghazghkull | `prophet_of_da_great_waaagh.py` | Aura 6", +1 Treffer/+1 Verwunden im Nahkampf in `FightController`, eigene Einheit zählt (Shadowsun-Lesart) |
| Da Boss (Armeeregel) | Warboss, WMA, Beastboss, Ghazghkull | `da_boss.py` | `sync_battle_round()` am Schlachtbeginn und an jeder Phasengrenze, idempotent |

**DER WARLORD (`game/warlord.py`)** — die Engine hatte bis hierher keinen, und jede Warlord-Regel
war ein dokumentierter No-op. Jetzt:
- Ein Listeneintrag (Einheit oder Leader) darf `"warlord": true` tragen; der Builder schreibt es in
  Pass 2 auf das MODELL (`Token.warlord`), solange der Charakter noch eigener Trupp ist — nur auf
  CHARACTER-Modelle (die Menhire der Silent King bleiben unmarkiert). Gespeichert wird nichts: ein
  Load baut die Armee aus der Liste.
- Beim Laden geprüft: höchstens einer, ein CHARACTER, kein „cannot be your WARLORD" (C'tan),
  **Supreme Commander** muss es sein — nennt die Liste niemanden, IST er es (Ghazghkull, Shadowsun,
  The Silent King; die beiden letzten waren dokumentierte No-ops und tragen jetzt das Flag), nennt
  sie einen anderen, wird sie abgelehnt. **Keine ausgelieferte Liste nennt einen Warlord** — alle
  Warlord-Regeln bleiben für sie ruhend, auch Da Boss für die bisherige Ork-Liste (G6 bringt
  Ghazghkull). Reanimation Crypts bleibt per User-Entscheidung beim Ziel-No-op.
- **Da Boss:** ein LEBENDER Warlord mit der Fähigkeit (in Reserve zählt er, der Text sagt nicht „on
  the battlefield"). Der CP läuft über `gain_cp()` und damit unter den +1-Bonus-CP-Deckel der
  Hausregel. Die bezahlte Runde steht auf der Einheit (`Squad.da_boss_round`, gespeichert): **der
  Deckel-Zähler wird NICHT gespeichert** (`scene_io` hält nur die CP-Stände), nach einem Laden mitten
  in der Runde stünde sonst ein zweiter CP offen. Die A/B-Sonde fand das: der Deckel verdeckte die
  Idempotenz im Test, erst ein frisches CP-Ledger zeigte, welcher Term hält.

**DER COVER-TOR-FIX (vorbestehend, beim Bau von More Dakka gefunden).** Beide Leser von
[IGNORES COVER] — der Cover-Split in `_dispatch_group()` und der Benefit-of-Cover-Term in
`_hit_modifiers()` — bekamen die GEDRUCKTE Waffe. Jeder Ketten-Grant (Pech'ra, Faolchu, Oversight
Drone, Nebuloscope, Preternatural Precision) kam dort nie an; ihre Suiten prüften nur das Flag an der
Kopie. Gemessen: aktive Oversight Drone → Kopie `ignores_cover=True`, Hit Roll trotzdem „+1 (Benefit
of Cover)". Beide Leser bekommen jetzt `self._adjusted_weapon(...)`; Wächter
`test_event_chain_wiring.py` **§29** (§27s Form), A/B belegt, dazu `## Regelengine — Schießen`.

- **Makari (Lesarten):** Kandidaten sind befreundete Einheiten mit der Waaagh!-Fähigkeit, die der
  Grant VERLÄNGERN würde (Fehlerklasse 5) — auch Fahrzeuge (im Spiel gezogen: der Battlewagon). Der
  erste Pick verbraucht die Nutzung, Abbrechen davor nicht. Ein gewählter Trupp fällt von selbst aus
  den Kandidaten, weil der Grant seine Frist genau auf diese setzt — ein eigener „schon gewählt"-Term
  war ein toter Zweig (die Sonde darauf biss nicht) und ist entfernt.
- **KI (0 API-Calls):** Fix Dat per injiziertem `fix_dat_armour_up_verdict()` ab 3 heilbaren Wunden;
  Makari per `_handle_makari()` in `_handle_movement()` vor Da Jump, wenn mindestens min(Runde, 3)
  Einheiten mit Feind in Advance + Charge gewinnen, die nächsten zuerst.
- **Nachgezogen:** `test_ork_army_rules.py` (22 Blätter; §1 prüft jetzt Da Boss gegen jede gedruckte
  FACTION-Zeile, §10s „kein Warlord"-Pin ist ersetzt), `test_aeldari_enhancements.py` (sechste
  Lone-Operative-Quelle), `test_roll_modifier_cap.py` (die zwei Prophet-Modifikatoren als ROLL, 56
  Stellen), `test_tau_characters.py` und `test_necron_ctan.py` (No-op-Texte), `rules/README.md`
  (Orks 22). **Zwei Sondenanker älterer Treiber** hatte G2 verschoben — der Trukk-Ausschluss
  (`ab_ork_vehicles.py`) und eine vom Da-Boss-Handler wörtlich übernommene Zeile im Makari-Handler
  (`ab_ork_war_horde.py`, Anker doppelt; die Makari-Zeile ist jetzt eigen). `--check` über alle
  Treiber fand beide, beide beißen wieder.

**Getestet:** neu `test_ork_mecha_characters.py` (**122/122**, elf Abschnitte — Datenblätter gegen
Korpus, Transport an 18.01 UND 18.02, More Dakka am ECHTEN Cover-Tor samt Oversight Drone, Kustom
Force Field über `effective_invulnerable_save()`, Fix Dat mit Angebot/Ablehnung/Nutzung/KI, Warlord
über `army_io.parse()` und den echten Builder, Da Boss samt geladenem Spielstand, Ladz über
`lone_operative_range()`, Prophet über den echten `FightController` samt ±1-Deckel mit Sumfin' to
Prove, Makari mit Pick/Limit/echtem `ActionPanel` in allen fünf Phasen/KI, AST-Pins) und
`ab_ork_mecha_characters.py` (**66 Sonden, 71 Läufe, alle beißend, kein Rest**). **Im ersten Lauf
bissen sieben nicht** — zwei Abstürze (`next()` ohne Default, `None.attacks`), drei VERDECKTE Terme
(Fix Dat „erneut angeboten" hinter „nichts zu heilen", zweimal Da Boss hinter dem CP-Deckel), eine
KI-Szene ohne qualifizierende Einheit, und ein toter Zweig im Code (Makari, s. o.). Volle Regression
**239 Suiten, ~23339 Prüfungen, 238 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett grün,
`selfplay.py map2 1500` Orks gegen Necrons in beiden Sitzordnungen exit 0.
`verify_rules_vs_engine.py` **68** (unverändert), `fetch_datasheet_rules.py --offline` nur mit den
zwei neuen Blättern im README, `measure_crowded_movement.py` unverändert gedrängt **62 % / 210.2"**,
isoliert **87 % / 292.3"**.

**Im ECHTEN Spiel belegt** (`verify_ork_mecha_characters.py map2`, Orks als Player 1; 9/9, unter
`--neutralize` 7/7 Abwesenheitsprüfungen):

| | gefixt | `--neutralize` |
|---|---|---|
| Wiring | Fix Dat mit `main()`s Platzierer, Da Boss mit `main()`s CP-Ledger, Makari registriert | Makari fehlt |
| KI-Makari über `main()`s Auto-Play (Runde 3) | drei Player-2-Boyz riled up | nie |
| Da Boss an `main()`s Phasengrenze | 1 CP, Runde gestempelt, nächste Grenze derselben Runde 0 | nichts |
| Makari auf `main()`s Panel | gezeichnet, Pick über `main()`s DecisionManager, Einheit riled up, verbraucht | nie gezeichnet |
| More Dakka am Live-`ShootingController` | kein Benefit of Cover für die Big-Mek-Einheit, plain Meganob +1 | Cover bleibt |
| Prophet am Live-`FightController` | −1/−1 | nichts |
| Fix Dat an `main()`s Command-Grenze | gefragt, 11 → 14 Wunden, verbraucht | nie gefragt |

GESTELLT: Orks als Player 1, gebaute Einheiten (die Liste fieldet sie erst ab G6), Player 1s
Ghazghkull von Hand als Warlord markiert, die Uhr je Stufe, einmal Deckung für die Cover-Lesung, und
für die KI-Stufe Ork-Einheiten für Player 2 (dessen Armee sind Necrons).

## Mecha Orks G3: Green Tide (2026-09-19)

Gedruckter Text in `rules/orks/detachments/Green Tide.md`, jedes Modul trägt ihn im Docstring.
`armies/orks.json` UNVERÄNDERT (G6): keine ausgelieferte Liste fieldet Green Tide,
`config.GREEN_TIDE_PLAYERS` ist leer, bis eine Liste es deklariert.

**Detachment** (`game/factions/orks.py`, 1 DP, Take and Hold, Setting `GREEN_TIDE_PLAYERS`).

| Teil | Modul | Naht / Lesart |
|---|---|---|
| Mob-handed Brutality | `green_tide.py` | ein Glied der Nahkampfkette: BOYZ → [SUSTAINED HITS 1]; ORKS INFANTRY nach Charge → [LETHAL HITS] nur gegen ein Ziel, das `NON_MONSTER_VEHICLE_TARGETS` erfüllt (ohne Ziel: nichts). Nie ein Downgrade, Würfelnotation unberührt |
| Ferocious Show-off (15) | `enh_ferocious_show_off.py` | pro TRÄGER (+Term in `_melee_attack_key()`): +1 A, bei 11+ LEBENDEN Modellen der Einheit +2 A (Alternativen, keine Summe); ORKS INFANTRY CHARACTER |
| 'Ardboyz (25) | `enh_ardboyz.py` | Einheiten-Enhancement (vor 19.01 vergeben → nur die Boyz tragen das Flag); 4+ Sv als ERSETZUNG über `save_characteristic.py`, per 19.04 für die ganze angeschlossene Einheit, solange ein Boy lebt |
| Unbridled Carnage (1CP) | `green_tide_unbridled_carnage.py` | Registry-Knopf, „Fight phase" ohne „your" → auch im gegnerischen; BOYZ, die diesen Zug gechargt haben, eligible, nicht gekämpft/kämpfend; +1 A für die Phase |
| 'Ere We Go (1CP) | `green_tide_ere_we_go.py` | Registry-Knopf, eigene Bewegungsphase, BEAST SNAGGA BOYZ/BOYZ, noch nicht bewegt/advanced; +2 NUR auf den Advance-Wurf (`roll_bonus.advance_sources()`), nie auf die Charge |
| Mob Mentality (1CP) | `green_tide_mob_mentality.py` | Registry-Knopf auf der 13+-Einheit, dann Pick der BEGÜNSTIGTEN Einheit (sichtbar, 12", schuldet einen Wurf; die Einheit selbst zählt); gezahlt wird beim Pick |

**BOYZ ist ein DATENBLATT, kein Keyword** (die Boyz drucken INFANTRY, BATTLELINE, EXPLOSIVES, MOB):
gelesen über `attached_units.unit_is_datasheet()` — eine angeschlossene Einheit hat alle Keywords
ihrer Komponenten (19.03), ein Warboss-geführter Mob ist also BOYZ. Beast Snagga Boyz sind KEINE
Boyz ('Ere We Go druckt beide getrennt).

**Mob Mentality — die Lesarten.** „Start of the Battle-shock step" = kein Battle-shock-Wurf des
Spielers in dieser Command-Phase gemacht oder offen (`rolled_squad_ids`/`rolling_squad`); ein Wurf
des GEGNERS schließt das Fenster nicht. „Automatically successful" ohne Dauer = die Phase. Die drei
Wurf-Eingänge von `BattleShockController` fragen `auto_success_source()`: der 08.03-Test (`start_roll`)
löst OHNE Würfel auf (`force_pass(source=...)`, wie Insane Bravery); erzwungene und Desperate-Escape-
Würfe WERFEN weiter und werden bei der Bestätigung als bestanden gewertet — sechs Aufrufer warten auf
genau diese Bestätigung (Warteschlangen, eine Charge, die weiterläuft), ein nicht gestarteter Wurf
hätte sie alle festgehalten. Insane Bravery wird für so eine Einheit verweigert (kauft nichts). 
**Benannte Grenze:** der Psychomancer (Nightmare Shroud) wirft seine Tests schon, während `main()` die Command-Phase öffnet - vor jedem möglichen Knopfdruck, und sein erster Wurf schließt das Fenster („step has begun"). Gedruckt stünde Mob Mentality am START des Schritts davor; die Engine hat keine Unterschritte, in denen beide Seiten sich einreihen könnten.

**DER ZÄHLSTELLEN-FIX (vorbestehend, beim Bau von Unbridled Carnage gefunden).**
`FightController._begin_resolution()` zählte die Attacken von den ROHEN `pairs` — jeder +A-Grant der
Nahkampfkette (Might Is Right +3, Rokkit Charge +1, The Stars Are Right ×3) stand nur auf der Kopie,
die die Suiten prüften. Gemessen: ein gechargter Warboss warf dieselben 10 Trefferwürfel wie ein
ungechargter. Die Zählstelle (fest UND Würfelnotation) liest jetzt `self._adjusted_weapon(...)` — die
Fernkampfseite hatte das für Psychic Communion schon an ihrer Zählstelle gelöst. Nach dem Fix: 13
gegen 10. Wächter `test_event_chain_wiring.py` **§31** (die Zählstelle liest die gebundene angepasste
Waffe; jedes Modul, das `attacks` auf einer Kopie schreibt, ist mit seinem zählenden Leser benannt).

**DER SAVE-WERT HAT EINEN LESER (`game/save_characteristic.py`, Extraktion).** Sechs Stellen lasen
`armor_save`: Rettungswurf samt Panel-Überschrift, Zuteilungsreihenfolge, jede KI-Schätzung
(`defender_soak()`), die KI-Beobachtung, der Waffen-Matchup-Hinweis, die Datacard. Die Shieldvanes
der Tomb Blades („has a 3+ Save characteristic") erreichten nur den Wurf — Datacard, KI und
Zuteilung lasen 4+. 'Ardboyz ist die zweite Ersetzung; beide gehen jetzt durch `armour_save(model)`.
Wächter **§30**: jeder verbleibende `.armor_save`-Leser ist namentlich begründet.

**Zwei kleine Extraktionen:** `attached_units.unit_datasheet_names()`/`unit_is_datasheet()` (dritte
Kopie, dazu Green Tides vier Fragen) und `dice_notation.plus()` (vierte Kopie; Psychic Communion
verlor dabei still den Würfel-ANZAHL-Anteil einer Notation).

**KI (0 API-Calls):** Mob Mentality in der Command-Phase VOR dem ersten eigenen Battle-shock-Wurf,
für den Kandidaten mit der höchsten Fehlschlagchance × Punkte, ab 25 % (Ld 7+: 15/36);
'Ere We Go in `_handle_movement()` genau im Moment der Advance-Entscheidung; Unbridled Carnage im
Fight-Handler ab 2 erwarteten Zusatzwunden.

**Getestet:** neu `test_ork_green_tide.py` (**180/180**, elf Abschnitte — Detachment gegen Korpus,
Mob-handed Brutality über den echten `FightController` samt Fahrzeug-Ziel und Downgrade-Schutz, die
ZÄHLSTELLE über echte Aktivierungen (Might Is Right +3, Rokkit Charge +1 je Stormboy), Ferocious
Show-off samt Attack-Key und 11-Modell-Grenze, 'Ardboyz an allen sechs Lesern plus Shieldvanes,
Unbridled Carnage/'Ere We Go/Mob Mentality mit WHEN/TARGET-Negativen, echtem Advance-Wurf, allen drei
Wurf-Eingängen und Insane Bravery, die drei KI-Handler, die Extraktionen, AST-Pins),
`test_ork_green_tide_ui.py` (**107/107**, echtes `ActionPanel`: Liveness, Matrix 3 Knöpfe × 2
Einheiten × jede Phase, „whose phase" samt gegnerischer Fight-Phase, Detachment-Tor am Panel,
Negative, Resets einzeln, Klick zahlt — Mob Mentalitys Pick per `drain()`, Label gegen Korpus, AST)
und `ab_ork_green_tide.py` (**73 Sonden, 96 Läufe**). **Im ersten Lauf bissen sechs nicht, eine
stürzte ab** — alle Befunde über die TESTS: die INFANTRY-Klausel von Ferocious Show-off hat kein
gebautes Gegenbeispiel (jetzt ein Warboss, dessen Profil-INSTANZ das Keyword verliert), 'Ardboyz'
Einheiten-Grant warf statt rot zu werden, Mob Mentalitys „Schritt begonnen" und „deine
Command-Phase" waren im Panel-Test hinter „niemand schuldet einen Wurf" verdeckt (jetzt: der Wurf des
MOBS selbst; ein eigenes Entscheidungsfenster im gegnerischen Zug), 'Ere We Go für die fremde Einheit
hinter 15.01, und der Sichtlinien-Pin fand dieselbe Lambda eines anderen Controllers (jetzt per AST
am `visible=`-Keyword von `MobMentalityController`). Danach alle beißend, `--check` über alle **11**
Treiber sauber, keine Rückstände. Volle Regression **241 Suiten, ~23644 Prüfungen, 240 grün / 0 rot /
1 bekannt**, `--smoke` grün, `selfplay` Orks gegen Necrons beide Sitzordnungen exit 0,
`verify_rules_vs_engine.py` **68**, `fetch_datasheet_rules.py --offline` nur Datumswechsel
(zurückgesetzt), `measure_crowded_movement.py` unverändert **62 % / 210.2"**, **87 % / 292.3"**.
Nachgezogen: `test_detachments.py` (Orks namentlich: War Horde, Green Tide), `test_force_dispositions.py`
(20 Detachments).

**Im ECHTEN Spiel belegt** (`verify_ork_green_tide.py map2`, Orks als Player 1; 11/11, unter
`--neutralize` 7/7):

| | gefixt | `--neutralize` |
|---|---|---|
| Registry | alle drei, mit `main()`s BattleShock-/Fight-/Movement-Controller, Token-Liste, Sichtlinie | keiner |
| KI-Mob-Mentality über `main()`s Auto-Play | gekauft; ihr Battle-shock-Test besteht OHNE Würfel, Log nennt Mob Mentality | nie gekauft (die KI nahm Insane Bravery) |
| Mob Mentality auf `main()`s Panel | gezeichnet, ein Kandidat ohne Prompt, 1 CP; 08.03-Test ohne Würfel bestanden | nie gezeichnet |
| 'Ere We Go auf `main()`s Panel | gezeichnet, 1 CP, Advance-Terme `+2`, eine 3 wird 5 | nie gezeichnet |
| Unbridled Carnage (echt engaged) | gezeichnet, 1 CP; Choppa A3→4, [SUSTAINED HITS 1]; BSB [LETHAL HITS] gegen Infanterie | nie; A3, SH 0, kein Lethal |
| 'Ardboyz | Datacard 4+, Save-Schwelle 4 | 5+ / 5 |
| `main()`s Phasengrenze | alle drei Grants enden | — |

GESTELLT: Orks als Player 1, gebaute Einheiten (die Liste fieldet Green Tide erst ab G6),
`GREEN_TIDE_PLAYERS` für beide Seiten und `WAR_HORDE_PLAYERS` geleert (sonst gäbe Get Stuck In
jedem Ork [SUSTAINED HITS 1]), die Uhr je Stufe samt `reset_command_phase()` und CP-Auffüllung, ein
Beast-Snagga-Trupp „unter halber Stärke" als 4 von 10 gebaut, der Nahkampf-Mob neben ein
Player-2-Infanterieziel gestellt.

## Mecha Orks G4: Blitz Brigade (2026-09-19)

Gedruckter Text in `rules/orks/detachments/Blitz Brigade.md`. `armies/orks.json` UNVERÄNDERT (G6),
`BLITZ_BRIGADE_PLAYERS` leer, bis eine Liste es deklariert. WAGON ist ein Datenblatt-Keyword (Kill Rig,
Battlewagon, Gunwagon; der Trukk nicht), gelesen über `unit_has_datasheet_keyword()`.

| Teil | Modul | Naht / Lesart |
|---|---|---|
| Unstoppable Momentum, Advance | `blitz_brigade.py` | `start_run()`s No-Roll-Zweig: ein Wurf, den man immer auf sein Maximum ändern darf, IST eine 6 — kein Würfel, also bietet kein Reroll (Waaagh!, Command Re-roll) etwas an, das nichts kauft; anders als die flachen Boni dort ein WURF, die Advance-Modifikatoren (`shaken` −2) gelten weiter. Die KI-Beobachtung rechnet mit 6 statt 3,5 |
| Unstoppable Momentum, Charge | `blitz_brigade.py` | DRITTER Träger von `charge_reroll.py`, an `main()`s Quittungstür nach Phaeron of the Blades und auf dem Würfelpanel |
| Targetin' Gizmos (10) | `enh_targetin_gizmos.py` | zweite Quelle von `more_dakka.py` (`grants_more_dakka()`); die Kette bekommt die eingestiegenen Einheiten (`ShootingController.embarked_squads_provider`, in `main()` = `state.embarked_squads`); BIG MEK je MODELL per `model_has_datasheet_keyword()`, lebend; beide [IGNORES COVER]-Leser sehen es |
| Boss Boomer (10) | `enh_boss_boomer.py` | `BossMotivationController.bearer_models()` leiht die Modelle eines eingestiegenen, lebenden WARBOSS, der die Fähigkeit druckt — der WAGON wird Träger: sein Zug, seine 6", das Limit der Fähigkeit |
| Keep It Runnin' (1CP) | `blitz_keep_it_runnin.py` | dritte Druckform der Fight-Ende-Einsteige-Mechanik (siehe unten); ORKS INFANTRY, „End of THE Fight phase" beide Spieler, die KI lehnt ab (benannt) |
| Impending Krunch (1CP) | `blitz_impending_krunch.py` | Angebot am `on_charge_move_finished`-Haken in der EIGENEN Charge-Phase (Heroic Intervention nicht), nur mit engagiertem Feind, einmal je Charge-Move (Memo); die Tests über die geteilte Warteschlange; KI kauft, wenn ein engagierter Feind noch NICHT shocked ist (ein bestandener Test heilt) |
| Readied Brawlers | — | **NICHT verdrahtet** (User-Entscheidung: die „assault disembark move" gibt es im Regelbuch nicht). `blitz_brigade.NOT_WIRED` nennt die Lücke, die Suite pinnt, dass kein Modul außer der Regel sie erwähnt und nichts eine „assault disembark" baut |

**Drei Extraktionen, alle am fälligen Konsumenten:**
- **`game/end_of_fight_embark.py`** — Skyborne Sanctuarys Mechanik wörtlich verschoben, mit den drei
  Knöpfen NAME/CP, RANGE_IN und `eligible_unit()`. Ein Ork-Stratagem, das eine nach einem Aeldari-Stratagem
  benannte Klasse erbt, wäre ein lügender Name (Fehlerklasse 11). Das Aeldari-Verhalten ist unverändert
  (1013/1013). Zwei Quell-Wächter lesen jetzt das neue Modul.
- **`game/forced_shock_queue.py`** — Mobbeds Warteschlange erzwungener Battle-shock-Tests, am zweiten
  Nutzer. Der Psychomancer (Nightmare Shroud) behält seine ältere Kopie — benannt als nächster Kandidat,
  nicht in einer Ork-Etappe umgeschrieben. §21 nennt den neuen Aufrufer.
- **`game/ork_units.py`** — `is_orks_unit()`/`is_orks_infantry_unit()`, von War Horde und Green Tide
  re-exportiert; Blitz Brigade hätte sie sonst aus einem fremden Detachment-Modul importiert.

**Vorbestehender Befund:** `ab_aeldari_offer_windows.py` (ohne `--check`) hatte veraltete Skyborne-Anker
seit dem Umbau auf `unit_choice_offer` (`self._window.arm(squad.owner)` gibt es nicht mehr). Beim Umzug
mitkorrigiert, dazu `ab_unit_choice_offers.py`; beide Treiber liefen danach vollständig, alle Sonden beißen.
**Falle dabei:** diese älteren Treiber haben keinen `__main__`-Schutz — ein IMPORT (für eine Ankerprüfung)
startet den echten Sondenlauf.

**Getestet:** neu `test_ork_blitz_brigade.py` (**122/122**, zehn Abschnitte — der Advance ohne Würfel samt
`shaken` und Beobachtung, der Charge-Reroll an einem echten `ChargeController` mitten im Wurf,
Targetin' Gizmos an Kette UND Cover-Tor mit fünf Negativen, Boss Boomer an beiden Controllern und am
ECHTEN `ActionPanel` samt Phasen- und Detachment-Negativen, Keep It Runnin' mit sieben Negativen und
Stellvertretern, Impending Krunch durch `confirm_charge_move()` eines echten `ChargeController` samt
Warteschlange und KI-Regel, Readied Brawlers' Lücke, die Extraktionen, AST-Pins) und
`ab_ork_blitz_brigade.py` (**41 Sonden**). **Im ersten Lauf bissen zwei nicht, eine stürzte ab** — alle
über die Tests: Keep It Runnins INFANTRY-Klausel wird von JEDEM Ork-Transport selbst verdeckt (jetzt ein
Battlewagon, dessen Profil-INSTANZ das Verbot verliert), Krunchs „einmal je Charge-Move" war nach dem
Kauf hinter 15.01 verdeckt (jetzt nach einem Decline gemessen), und `NOT_WIRED[...]` warf statt rot zu
werden. Vorher schon per Test-Durchdenken ergänzt: ein WARBOSS-Stellvertreter für Boss Boomer (kein
gebautes Blatt druckt Intimidating Motivation ohne WARBOSS). Die umgezogenen Anker in `ab_ork_mobs.py`
(Warteschlange) und `ab_ork_mecha_characters.py` (More Dakka) beißen weiter; `--check` über alle **12**
Treiber sauber. Volle Regression **242 Suiten, ~23776 Prüfungen, 241 grün / 1 bekannt**, `--smoke`
grün, selfplay Orks gegen Necrons beide Sitzordnungen exit 0, `verify_rules_vs_engine.py` **68**, Korpus
unverändert, `measure_crowded_movement.py` unverändert **62 % / 210.2"**, **87 % / 292.3"**.
Nachgezogen: `test_detachments.py` (Orks namentlich), `test_force_dispositions.py` (21),
`test_ork_mecha_characters.py` (More Dakka mit Passagieren), `test_unit_choice_offers.py` und
`test_event_chain_wiring.py` (Skyborne im neuen Modul, §21 mit der Warteschlange).

**Im ECHTEN Spiel belegt** (`verify_ork_blitz_brigade.py map2`, Orks als Player 1; 8/8, unter
`--neutralize` 7/7):

| | gefixt | `--neutralize` |
|---|---|---|
| Wiring | Charge-Reroll mit `main()`s Würfeln/Charge, Krunch mit `main()`s BattleShock/Decision/Tokens, KIR mit Transport/Fight, die Schieß-Sicht IST `state.embarked_squads` | keine Schieß-Sicht |
| KI-Impending-Krunch am Charge-Ende-Haken | 1 CP, Test −1 für eine engagierte Player-1-Einheit | nie gehört |
| KI-Charge-Reroll an `main()`s Quittungstür | eine 3 ohne Ziel wird ganz neu gewürfelt | nie gefragt |
| Advance eines Battlewagon | +6", kein Würfel | Würfel |
| Targetin' Gizmos | [IGNORES COVER], kein Benefit of Cover | Cover bleibt |
| Boss Boomer auf `main()`s Panel | Intimidating Motivation gezeichnet, benutzt | nie gezeichnet |
| Keep It Runnin' an der Fight-Grenze | angeboten, gepickt, 1 CP, eingestiegen | nie angeboten |

GESTELLT: Orks als Player 1, gebaute Einheiten, `BLITZ_BRIGADE_PLAYERS` für beide Seiten und
`WAR_HORDE_PLAYERS` geleert, die Uhr je Stufe und CP-Auffüllung, H feuert `main()`s
Charge-Ende-Hakenliste für einen engagiert gestellten Battlewagon, C würfelt die Charge per
kurzzeitig getauschtem `random.randint` (NICHT `testkit` — dessen Import setzt JEDEN Würfel des Laufs auf
1, gemessen), F legt die Boyz in `engaged_at_start`. Zwei Bühnen-Lehren: eine gestellte Charge, die der
Reroll zufällig ans Ziel bringt, bleibt offen und hält das Panel auf dem Charge-Bildschirm — C lehnt sie
nach der Messung ab (11.02); und Keep It Runnins Preis wird NACH der Grenze gemessen, weil die
Fight-Grenze schon den Kern-CP der nächsten Command-Phase gezahlt hat.


## Mecha Orks G5: Da Big Hunt (2026-09-20)

Gedruckter Text in `rules/orks/detachments/Da Big Hunt.md`. `armies/orks.json` UNVERÄNDERT (G6),
`DA_BIG_HUNT_PLAYERS` leer, bis eine Liste es deklariert. BEAST SNAGGA ist ein Modell-Flag
(`beast_snagga`), über 19.03 gepoolt — ein Beastboss, der Beast Snagga Boyz führt, ist EINE BEAST
SNAGGA unit, und ein angeschlossener Weirdboy verwässert das nicht.

| Teil | Modul | Naht / Lesart |
|---|---|---|
| Da Hunt is On | `da_big_hunt.py` | „attacks", nicht „melee attacks": ein Glied in BEIDEN Adjuster-Ketten (`shooting.py` UND `fight.py`), +1 AP gegen MONSTER/VEHICLE. Die Bedingung gehört dem ZIEL, also nimmt der Adjuster es entgegen; ohne Ziel wird nichts gewährt (kann unter-, nie überberichten) |
| Glory Hog (25) | `enh_glory_hog.py` | NUR `may_charge_after_falling_back()` — der gedruckte Text sagt „declare a charge", nicht „shoot"; genau die Hälfte, die eine Kopie des Ork-Nachbarn Kunnin' But Brutal verlieren würde (dieselbe Unterscheidung wie Relentless Combatants) |
| Where D'ya Fink You're Going? (1CP) | `da_hunt_where_dya_fink.py` | Cornered Prey, gekauft, plus eine Klausel: dieselbe Tür `forced_desperate_escape.py`. Der MARK sitzt auf der BEAST SNAGGA unit (der gedruckte TARGET), jeder engagierte Feind wird live gemessen; das Angebot hängt an `FallBackController.declare()`s `on_fall_back_declared` (zweiter Reaktor nach Khaine's Vengeance) |
| Goaded into Action (1CP) | `da_hunt_goaded_into_action.py` | **Der erste Surge Move (21.02) dieser Engine** — die Maschinerie stand seit ihrem Bau ohne Aufrufer da. D6 als sichtbarer `DiceNotationRoll`, dann der reaktive Zug auf `main()`s MovementController, `active_player` beim reagierenden Spieler bis Confirm/Cancel (Path of the Outcasts Form). „lost a wound as a result of those attacks" beantwortet ein neues Aktivierungs-Ledger des ShootingControllers |
| Instinctive Hunters (1CP) | `da_hunt_instinctive_hunters.py` | Aerial Manoovers Naht und Rückzug, gekauft: `PhaseWindow` statt Uhr, `mover_before` statt `turn_owner`, `withdrawal_is_doomed()`; NEU ist „within 6" of a battlefield edge" (`board_edges.py`) und dass es EINE Einheit nennt |
| It Came from da Drops | — | **NICHT verdrahtet**: es gibt kein Datenblatt BEASTBOSS ON SQUIGOSAUR in dieser Engine, also könnte es niemand tragen. `da_big_hunt.NOT_WIRED` nennt die Lücke samt Grund, die Suite pinnt sie (und dass die Registry es nicht führt) |

**Zwei Extraktionen, beide am fälligen Konsumenten** (Details in `extraktionen.md`):
`game/forced_desperate_escape.py` (wer zwingt eine zurückfallende Einheit in DESPERATE ESCAPE, und was
kostet es sie — `fall_back.py` fragt die Registry statt Cornered Prey namentlich) und
`game/board_edges.py` (die Brettkanten-Helfer aus `secondary_missions.py`, das sie re-exportiert).

**Drei Engine-Fehler, die erst der erste echte Aufrufer sichtbar machte:**

- **`can_make_surge_move()` verlangte die BEWEGUNGSPHASE.** Es lief über `can_move()`, dessen Sinn
  „ist das der Bewegungsphasen-Zug dieser Einheit?" ist — und Goaded into Action feuert in der
  SCHUSSPHASE DES GEGNERS. Solange 21.02 keinen Aufrufer hatte, kostete das nichts und war
  unsichtbar; mit Aufrufer hätte es JEDEN Surge Move abgelehnt, den die Engine gewähren kann. Jetzt
  prüft die Methode die drei gedruckten Punkte selbst (nicht battle-shocked, unengaged, hat diese
  Phase nicht bewegt) — dieselbe Entscheidung, die `start_post_shooting_move()` und
  `start_battle_focus_move()` in ihren Docstrings begründen. `"surge"` steht dazu in der
  Ausschlussliste von `confirm_move()`s Bewegungs-Buchführung (ein reaktiver Zug bucht keine
  Bewegungsphase, die dem anderen Spieler gehört).
- **Cornered Preys −1 konnte die Hazard-Würfe nie erreichen** — ein VORBESTEHENDER Fehler, den erst
  die zweite Quelle sichtbar machte. Beide gedruckten Sätze messen „engaged with", und die Kosten
  landen auf den Hazard-Würfen; ein Fall-Back-Zug ENDET aber per 09.07 unengaged, also ist die
  Live-Zählung am Wurf für jede Einheit, die dort ankommt, null. `test_exodites.py` war grün, weil es
  die Modulfunktionen fragt, während die zwei Einheiten noch beieinanderstehen. Jetzt friert
  `forced_desperate_escape.snapshot()` die Kosten an den Momenten ein, in denen die Engagement noch
  besteht (`choose_mode()`, und für ein Stratagem, das ein Mensch Frames später kauft, dessen
  `use()`); `fall_back.py` räumt den Snapshot an beiden Enden wieder ab. Belegt: dieselbe Szene rollt
  jetzt −2 („Cornered Prey and Where D'ya Fink You're Going?"), vorher −1.
- **Die Hazard-Zeile log den falschen NAMEN.** `HazardRollStep` schrieb `(-1 Cornered Prey)` fest
  verdrahtet — Fehlerklasse 11, sobald ein zweiter Träger denselben Satz druckt. Der Aufrufer weiß,
  wer spricht (`forced_desperate_escape.reasons()`), also sagt er es; die Zeile trägt den Modifikator
  jetzt auch auf dem WÜRFELPANEL, nicht nur im Log.

**Ein `main()`-Reihenfolgefehler, gefunden vom ersten echten Lauf** (Fehlerklasse 23):
`where_dya_fink_controller.reset_phase(_horde_squads)` stand ÜBER der Zeile, die `_horde_squads`
baut — `UnboundLocalError` beim ersten Phasenwechsel. §4 des Verdrahtungs-Wächters sieht das nicht
(es prüft `a.b = c` auf `main()`s EIGENER Ebene, das hier war ein Aufruf-ARGUMENT in einer
verschachtelten Funktion). Dafür gibt es jetzt **`test_event_chain_wiring.py` §32**: innerhalb EINES
geradlinigen Blocks darf keine Anweisung einen Namen lesen, den derselbe Block erst weiter unten
bindet. Alles, was das legal machen könnte, wird ausgeschlossen statt geraten (Schleifenrümpfe und
alles darunter, verschachtelte def-/lambda-Rümpfe — nur Dekoratoren und Default-Argumente laufen an
der def-Zeile —, Comprehension-Variablen, Namen aus einem ÜBERGEORDNETEN Block, Parametern, Modulebene
oder `global`/`nonlocal`, und `a.b = c`, das gar nichts bindet). Gemessen über `main.py`,
`selfplay.py`, `game/` und `ai/`: **640 Dateien, ~2 s, NULL Meldungen** — und die Vor-Fix-`main.py`
liefert genau eine, mit Zeile und Namen.

**Getestet:** neu `test_ork_da_big_hunt.py` (**132/132**, acht Abschnitte — die Regel durch beide
echten Ketten, Glory Hogs Träger-Zeile und die Charge-Hälfte, Where D'ya Fink an einem echten
`FallBackController.declare()`/`confirm()` samt Extra-Würfeln, −1 und der Registry-Summe MIT einem
Clanblade auf demselben Brett, Goaded into Action durch eine ECHTE Schuss-Aktivierung bis zum
`start_surge_move()` und dem echten ActionPanel, Instinctive Hunters an der Fight-Ende-Naht, die
benannte Lücke, die Extraktionen, die Quell-Wächter). Nachgezogen: `test_detachments.py`,
`test_force_dispositions.py` (22), `test_event_chain_wiring.py` §13 (`start_surge_move` ist jetzt eine
TÜR, kein Phasenstarter) und `test_aeldari_detachment_stratagems.py` (die Khaine's-Vengeance-Zeile las
die schließende Klammer einer Ein-Eintrags-Liste).

**A/B-Sonden** (`ab_ork_da_big_hunt.py`, **76 Sonden**, alle beißen). Der erste Lauf meldete 16
Befunde, davon 12 über den TEST und 4 über die SONDE:
- **Vier Sonden krachten, statt rot zu machen**: ein Träger-Prädikat auf `None` ist nicht aufrufbar
  (jetzt `_orks_character` — ein plausibler Fehlgriff statt eines Absturzes); ein Marker hinter der
  offenen Klammer einer EINZEILIGEN `def`-Zeile ist ein SyntaxError; und zweimal stürzte die SUITE an
  einer Zeile ab, die in ein anstehendes Würfelergebnis indexierte, das die Sonde gerade wegnahm —
  die Prüfung stellt die Prämisse jetzt fest, statt sie anzunehmen.
- **Zwölf Befunde über den Test**, darunter drei „Gürtel-und-Hosenträger"-Stellen, an denen ein
  zweites Tor dieselbe Frage beantwortet (die Ledger-Mitgliedschaft in `eligible()`, das „unengaged"
  des Controllers neben 21.02s eigenem): die Sonde zielt jetzt auf die Stelle, die die Antwort
  WIRKLICH gibt, oder bricht beide Tore in EINER Sonde. Ein battle-shocktes Ziel wird nicht von 21.02
  abgelehnt, sondern von 01.07 (keine Stratagems auf eine battle-shockte Einheit) — der einzige Term,
  den nur 21.02 hält, ist „hat diese Phase schon bewegt", und genau der steht jetzt im Test.
- **Ein vorbestehender Befund in einem FREMDEN Test**: `test_ork_vehicles.py` pinnte die AI-Politik
  von Aerial Manoover mit einem blanken Teilstring auf `main.py` — Instinctive Hunters injiziert
  dieselbe Politik, also stand der Ausdruck zweimal da und die Sonde des Deffkopta-Treibers biss
  nicht mehr. Der Pin nennt jetzt SEINEN Controller (dieselbe Ausfallart wie ein Wächter, der einen
  NAMEN zählt statt den Aufruf zu lesen).

**Im ECHTEN Spiel belegt** (`verify_ork_da_big_hunt.py map2`, Orks als Player 1; 8/8, unter
`--neutralize` 5/5):

| | gefixt | `--neutralize` |
|---|---|---|
| Wiring | alle drei Controller halten `main()`s Kollaborateure (Fall-Back-Hakenliste, das Wund-Ledger des ShootingControllers, GameState/Turn-Tracker) | Haken fehlen |
| Da Hunt is On | Slugga AP 0 → −1 gegen eine Ghost Ark, 0 gegen Wraiths | AP 0 |
| Glory Hog | Beastboss darf nach dem Fall Back chargen, der Warboss nicht | darf nicht |
| Where D'ya Fink | angeboten, 1 CP, markiert; Ordered Retreat abgelehnt, 3 Extra-Würfe | nie angeboten, Ordered Retreat erlaubt |
| Goaded into Action | Haken feuert, 1 CP, D6 auf `main()`s Würfeln, Quittungstür öffnet `"surge"` mit `active_player` beim Reaktor und der gewürfelten Weite | nie gehört |
| Instinctive Hunters | an der Fight-Grenze angeboten, gepickt, 1 CP, in Reserve und vom Brett | nie angeboten |

GESTELLT: Orks als Player 1, gebaute Einheiten, `DA_BIG_HUNT_PLAYERS` für beide Seiten und
`WAR_HORDE_PLAYERS` geleert, die Uhr je Stufe und CP-Auffüllung. D und E stellen den MOMENT, nicht die
Partie: ein MockAgent-Lauf produziert weder eine Necron-VEHICLE, die sich aus einer Ork-Engagement
zurückzieht, noch eine Necron-Einheit, die genau eine bestimmte Beast-Snagga-Einheit verwundet — D ruft
`main()`s `fall_back_controller.declare()` (die Methode, die der Fall-Back-Knopf ruft), E stempelt das
Aktivierungs-Ledger so, wie `_handle_hit_results()` es stempelt, und feuert dann `main()`s eigene
Hakenliste. Alles nach diesen zwei Aufrufen gehört der Engine. Eine Bühnen-Lehre: an einer Phasengrenze
können mehrere Prompts gleichzeitig offen sein — der Harness muss die vorderen ABLEHNEN, statt auf
seinen eigenen zu warten (F meldete sonst „angeboten, aber nie gepickt").


## Mecha Orks G6: die Liste selbst (2026-09-20)

`armies/orks.json` IST jetzt die Mecha-Orks-Liste des Users (Key `orks` bleibt, damit Config,
Screens und Tests weiter finden). **12 Einträge, 1990 Punkte, jeder Preis stimmt mit dem App-Export
überein**, drei Detachments zu genau 3 DP (Blitz Brigade + Da Big Hunt + Green Tide), Take and Hold,
und vier Enhancements, die diesmal wirklich jemand TRÄGT: Ferocious Show-off (Bigboss), 'Ardboyz
(Zehner-Boyz), Boss Boomer (Battlewagon), Targetin' Gizmos (Gunwagon). Ghazghkull ist der WARLORD —
sein Supreme Commander verlangt das, und Da Boss zahlt deshalb je Schlachtrunde 1 CP.

**Transporte stehen NICHT im Export** und sind eine Entscheidung dieser Engine, in der `note` der
Datei benannt: die Boyz mit Warboss und Bigboss fahren im Battlewagon (22/22 — randvoll), dem sie
Boss Boomer leihen; Big Mek und Meganobz im Gunwagon (8/12), der Targetin' Gizmos trägt; die
SCHMUCKLOSE Beast-Snagga-Einheit im Kill Rig (10/12). Die andere Beast-Snagga-Einheit kann NICHT —
der Weirdboy, der sie führt, ist kein BEAST SNAGGA, und der Kill Rig nimmt nur solche. Erst diese
Sitzordnung macht die zwei Fahrzeug-Enhancements überhaupt wirksam (beide lesen die EINGESTIEGENEN
Einheiten), und genau das belegt die Laufzeitsonde.

**Was mit der Liste umgezogen ist** (Fehlerklasse 17 — ein Test, der seinen eigenen Roster baut,
bleibt grün, während er die falsche Armee prüft): neun Suiten.
`test_player2_army.py` ist komplett neu geschrieben (104 Prüfungen, Einheit für Einheit gegen den
Export, und Abschnitt 6 vergleicht den handgebauten Roster gegen `armies/orks.json`s eigenen Bau);
`armies/baseline.txt` per `--write` erneuert und Zeile für Zeile gelesen; `test_army_select.py`
(12/78/1990 statt 14/101/2195), `test_detachments.py` (drei Settings statt War Horde),
`test_home_garrison.py` (ohne Tankbustas halten die Gretchin das Heim-Objective auf JEDER Karte
wieder — genau die Einheit, die der ursprüngliche Report benannt hatte), `test_ork_war_horde.py`
(stellt sein Detachment selbst; die Liste fieldet War Horde nicht mehr, und bei 3 DP ginge es auch
gar nicht neben den dreien), `test_stratagem_tooltip.py` (39 statt 36 gedruckte Stratagems),
`test_take_to_the_skies_policy.py` (Stormboyz raus, zwei Deffkopta-Einheiten statt einer),
`test_unit_datacard.py` (der Support-Charakter der 20er-Boyz ist der Bigboss) und
`test_pack_inner_ring.py` (drei Einheiten-Referenzen; die 22er-Mob-Spannweite ist mit dem Bigboss
6.13" statt 6.24").

**`measure_crowded_movement.py` behält seine EIGENE Ork-Armee** — die ist eine eingefrorene
Messvorlage, an der die ganze Bewegungsqualitäts-Reihe hängt, und das steht seit jeher in ihrem
Docstring. Neu benannt (sie ist jetzt auch nicht mehr `armies/orks.json`) und um ein drittes Ziel
ergänzt: **`--army=mecha` misst die ausgelieferte Liste**. Sie bewegt sich BESSER als die Vorlage —
gedrängt **78 % / 205.3"**, isoliert **91 % / 252.3"** gegen 62 % / 210.2" und 87 % / 292.3" —, was
kein Fix ist, sondern eine Folge der Liste: 12 statt 14 Einheiten und 78 statt 101 Modelle auf
demselben Brett.

**Im ECHTEN Spiel belegt** (`verify_mecha_orks_list.py map2`, Orks als **Player 2** — die Seite, auf
der diese Liste gespielt wird; 10/10, unter `--neutralize` 10/10). Diese Sonde ist das Gegenstück zu
allen anderen `verify_*.py`: sie BAUT nichts und STELLT keine Detachment-Config, sondern fragt, was
die LISTE allein erzeugt hat.

| | die Liste | `--neutralize` (der Detachment-Schreibvorgang weg) |
|---|---|---|
| A | 12 Einheiten, 1990 pts, drei Settings, vier Enhancements aktiv | dieselben 12/1990, keines der drei Settings, kein Enhancement |
| B | Ghazghkull ist der einzige Warlord, Da Boss zahlt 1 CP | unverändert (Warlord und Armeeregel hängen an der LISTE, nicht am Detachment) |
| C | alle drei Transporte tragen | unverändert |
| D | Gunwagon ignoriert Cover (Big Mek an Bord), Battlewagon leiht die Motivation des Warboss, Zehner-Boyz 4+ Sv, Bigboss +2 A in einem 22er-Mob | alles tot: Cover bleibt, nichts geliehen, 5+ Sv, gedruckte A |
| E | Da Hunt is On: +1 AP gegen eine Necron-VEHICLE, 0 gegen den Rest | gedruckter AP |

DREI Bühnen-Lehren aus dieser Sonde, alle zuerst als scheinbare Engine-Fehler aufgetreten:
- **Ein Teilstring-Name misst die falsche Einheit**: „Boyz 2" steckt in „Beast Snagga Boyz 2 +
  Beastboss + Weirdboy", und die erste Fassung meldete 'Ardboyz als tot. Der Namensvergleich ist
  jetzt exakt (Präfix abgeschnitten, dann `==` oder `startswith(name + " ")`).
- **Der MOMENT der Messung entscheidet**: alle drei Transporte laden in Declare Battle Formations
  (18.01) — und die KI steigt in ihrer ersten Bewegungsphase aus zweien wieder aus. Gemessen wird
  deshalb im ERSTEN Frame nach dem Vorspiel („die Armee steht so da, wie die Liste es wollte"),
  nicht im ersten stillen Frame, der schon Spiel misst.
- **Wer deployt, entscheidet, ob die Transport-Hints überhaupt gelten**: mit den Orks auf Player 1
  (dem Menschen) stieg niemand ein — die Hints sind eine Vorgabe für die AUFSTELLUNGS-KI
  (`_transport_affinity`), ein Mensch stellt von Hand auf. Die Sonde fieldet die Liste deshalb dort,
  wo sie gespielt wird.
