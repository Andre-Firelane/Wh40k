# Meldungen aus Partien (4)

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Vier Meldungen aus einer T'au-gegen-Death-Guard-Partie (2026-09-11)

`tau_retaliation` gegen `death_guard`, map4, Biom Arena. **Alle vier sind VOR jeder Änderung im Log
der gemeldeten Partie reproduziert** (`logs/game_20260911_132318.log`), und zwei davon haben beim
Nachverfolgen einen zweiten Fehler mitgebracht, den niemand gemeldet hatte.

| # | Meldung | Im Log | Ursache |
|---|---|---|---|
| 1 | „Fireknife kann all failed hits rerollen … wurde mir nicht angeboten" | Z. 284/285 | `shooting.py` unterdrückte die Fails-Option für sieben Fähigkeiten |
| 2 | „Rapid ingress und eater plague overlays überlappen sich" | Z. 506-518 | der Shooting-Start-Block lief VOR den Ende-der-Movement-Reaktionen |
| 3 | „Zug 3 KI macht nichts mehr nach Fight Step" | Z. 1067, 1447 | die KI wartete unsichtbar auf einen Retro-thrusters-Zug des Menschen |
| 4 | „bei Tempting Target nicht sichtbar, welches gewählt wurde" | Z. 1715 | `detail` stand als LETZTER Block, nur im aufgeklappten Zustand |

### 1. „nur Fehlschläge" fehlte bei sieben Reroll-Quellen

**User-Entscheidung: alle sieben, Fails-Option dazu.**

**Das Repo widersprach sich selbst, und zwar in derselben Datei.** `game/reroll_scope.py` begründete
die Unterdrückung damit, „failures only" erlaube „re-rolling a 2 that missed, which none of these
abilities permit". Drei Stellen widerlegen das:

1. **`game/protocol_conquering_tyrant.py`** zitiert den gedruckten Text wörtlich als *„you can
   re-roll the Hit roll **for that attack** instead"* — pro Attacke, und pro Attacke ist „the Hit
   roll" EIN Würfel.
2. **`game/shooting.py:4391-4394`**, im Wund-Schritt, liest denselben Satz richtig herum: *„'You CAN
   re-roll the Wound roll' permits re-rolling any subset of it, and re-rolling only the failures is
   the subset a player almost always wants"* — und `:4300-4302` sagt es ein drittes Mal.
3. Alle sieben Träger drucken denselben Satz („re-roll a Hit roll of 1. If ⟨Bedingung⟩, you can
   re-roll the Hit roll instead.").

**Dieselbe Formulierung, zwei Lesarten, nebeneinander ausgeliefert — Fehlerklasse 10 in ihrer
dritten Form.** Im Log kostete es einen Treffer: Z. 284/285 nahm der Spieler mangels Alternative den
ganzen Wurf und ging von 6 auf 5.

- **Die MENGE `ONES_OR_WHOLE_LABELS` bleibt, ihre BEDEUTUNG ändert sich.** Sie heißt jetzt „diese
  sieben haben eine MANDATORISCHE 1er-Klausel, also ist ‚Keep result' keine legale Antwort" statt
  „diese sieben verbieten die Fails-Teilmenge". Der Docstring war die eigentliche Fehlerquelle und
  ist korrigiert statt gelöscht.
- **Vier Aufrufstellen**, Hit und Wound in `shooting.py` und `fight.py`. Optionsreihenfolge
  einheitlich: Fehlschläge → ganzer Wurf → 1er-only.

**MITGEFUNDEN, NICHT GEMELDET: derselbe Reroll war zweimal nutzbar.** Die Asymmetrie ist gemessen
und steht als Tatsache im Docstring, sonst wird sie „symmetrisch repariert":

| | setzt `_used` beim ANBIETEN? | kehrt der 1er-Pfad zum Angebot zurück? | kaputt? |
|---|---|---|---|
| `shooting._offer_hit_reroll_choice` | **NEIN** | **JA** (`_finish_hit_roll`) | **JA** |
| `shooting._offer_twin_linked_choice` | JA | JA | nein |
| `fight._offer_hit_reroll_choice` | JA | NEIN | nein |
| `fight._offer_twin_linked_choice` | JA | NEIN | nein |

Der Fix ist EINE Zeile am OFFER-Ort, nicht in `_begin_ones_reroll()` — das ist auch der
Forward-Observers-Pfad, und dort gesetzt unterdrückte ein automatischer Reroll ein späteres
Monster-Hunters-Angebot. **Dritter Nebenbefund:** `fight._reroll_wound()` schrieb `[TWIN-LINKED]`
fest in die Würfel-Beschriftung, eine Implacable-Eradication-Wiederholung hieß also schon vorher
falsch; es nimmt jetzt ein `reason`.

**Getestet:** neu `test_reroll_scope.py` (**111/111**, sechs Abschnitte — es fährt alle VIER
Aufrufstellen für alle SIEBEN Labels und prüft die tatsächlich angebotene OPTIONSLISTE; vorher pinnte
KEIN Test die Labels, nur `is_ones_or_whole()`). Die tragende Gegenprobe: eine Quelle OHNE 1er-Klausel
(Grim Reapers, bis Orks E3a Monster Hunters) bekommt weiterhin „Keep result" statt „1s only" — ohne sie bestünde der Abschnitt
auch, wenn jede Unterscheidung gelöscht würde. Dazu ein AST-Quell-Wächter auf das INNERSTE
umschließende `if` (die erste Fassung meldete die Wund-Zweige falsch, weil das äußere
`if is_ones_or_whole` den Fails-Eintrag legitim umschließt). Neu `ab_reroll_failures_option.py`
(**11 A/B-Sonden, alle beißend**).

**Zwei fremde Pins wurden zu Recht rot und sind UMGEDREHT**, beide hatten den Fehler als Regel
protokolliert: `test_tau_walkers.py` (*„Its two clauses are ALTERNATIVES ('instead'), so 'failures
only' must not be on offer"*) und `test_awakened_dynasty.py`. `test_windriders.py` war eine
Fixture-Falle: `[1,1,6,6,6,6]` ließ Fehlschläge und 1en beide „(2 dice)" lesen, also sind es jetzt
`[1,1,2,6,6,6]` (3 Fehlschläge, 2 Einsen) plus eine Doppel-Angebots-Prüfung.

### 2. Rapid Ingress und Eater Plague auf Brett und Panel zugleich

**User-Entscheidung: Reihenfolge + Kette.**

`main.py`s `advance_turn_phase()` führte beim Übergang Movement→Shooting BEIDE Blöcke im selben
Aufruf aus, und den **falschen zuerst**: `if turn_tracker.phase == PHASE_SHOOTING:` (Matter
Absorption, Living Lightning, **Eater Plague**, Auxiliary Cadre, Guiding Presence) stand VOR
`if phase_before == PHASE_MOVEMENT:` (Guide, Doom, Flickerjump, **Rapid Ingress**). Das ENDE der
Movement-Phase liegt regeltechnisch VOR dem Beginn der Shooting-Phase — die Reihenfolge war also
auch regelseitig verkehrt.

Im Log: Rapid Ingress angenommen → Platzierung offen (Reserves-Strip, Brett-Overlay, linkes Panel) →
**währenddessen** würfelt Eater Plague und teilt fünf Mortal Wounds zu. **Die LOG-REIHENFOLGE ist der
Beleg:** Würfel werden erst gemeldet, wenn sie bestätigt sind, und bestätigen ließen sie sich nicht,
solange die Entscheidung darunter offen stand — `main.py`s Kette dispatcht Entscheidungen über
Würfeln.

**Der Mechanismus existierte schon; genau EIN Glied war kaputt.** `rapid_ingress.py`s `_pick()` parkt
sein `on_resolved` und feuert es erst aus `consume()`/`expire_if_unused()`, und sein Kommentar
beschreibt WÖRTLICH diese Fehlerklasse — für Fire Overwatch, das genau deshalb schon verkettet war.
`overwatch.py`s `choose_unit()` feuerte sein `on_resolved` aber, sobald die Snap-Shooting-Aktivierung
**gestartet** war, nicht wenn sie endet: eine naive Kette hätte Eater Plague mitten in die
Overwatch-Salve geworfen — dieselbe Kollision, eine Stufe später.

- **`choose_unit()` parkt jetzt** und `_on_shot_finished()` feuert; `decline()` und der
  „nichts qualifiziert"-Zweig weiterhin sofort. **Verhaltensneutral für den Bestand**, weil vorher
  niemand ein `on_resolved` übergab.
- **Die fünf ANGEBOTE sind in `_offer_start_of_shooting_phase()` gewandert**, die **RESETS bleiben**
  im Phasenwechsel — sie gehören dorthin, aufgeschoben lebten die Marken in die neue Phase hinein.
- **Das Sicherheitsnetz ist Pflicht, nicht Kür.** Das Risiko dieses Fixes ist nicht die Kollision,
  sondern eine Kette, die irgendwo NICHT feuert und die fünf Fähigkeiten **still** ausfallen lässt.
  Der Token wird deshalb **genommen, nicht gelesen** (eine doppelt feuernde Kette bietet einmal an),
  und am nächsten Phasenwechsel LAUT verfallen — **vor** `expire_if_unused()`, weil genau dieser
  Aufruf die geparkte Kette feuert und ein Netz danach die Angebote eine Phase zu spät ausliefern
  würde.
- **ZWEITES Netz, eine Ebene tiefer:** `start_snap_shooting()` hat einen frühen Ausstieg, auf dem
  `on_finished` nie gesetzt wird — dort strandete schon vorher `turn_tracker.active_player`.
  „Nie begonnen" ist „schon fertig", also ruft `_resolve()` `_on_shot_finished()` selbst, wenn die
  Aktivierung gar nicht startete.
- **Warum kein dritter Pfad nötig ist, gemessen:** `TurnTracker.advance_phase()` schreitet um genau
  eins fort, und jede andere Zuweisung an `phase_index` setzt auf die ERSTE Phase zurück — die
  Shooting-Phase wird also immer aus der Movement-Phase heraus betreten. Als AST-Prüfung gepinnt,
  nicht als Zeichenketten-Zählung (vier der fünf Zuweisungen sind Rundenwechsel).

**Getestet:** neu `test_shooting_start_order.py` (**41/41**, vier Abschnitte) plus ein
MENGENDIFFERENZ-Quell-Wächter in `test_one_modal_at_a_time.py` (**55/55**, Abschnitt 6) — dessen
eigener Docstring beschreibt dieselbe Klasse eine Ebene höher, und er ist ausdrücklich ein
SOURCE-Wächter, „because what broke was wiring". Geprüft wird per AST, dass in JEDEM
`phase == PHASE_SHOOTING`-Block NICHTS angeboten wird (mit Liveness: die Resets laufen dort weiter),
also muss ein SECHSTES Start-of-Shooting-Angebot sich benennen. Neu `ab_shooting_start_order.py`
(**11 A/B-Sonden, alle beißend**).

**ZWEI fremde Pins wurden zu Recht rot, und beide pinnten QUELLTEXT-ORDNUNG als Stellvertreter für
LAUFZEIT-Ordnung** (`test_tau_detachment_rules.py`, `test_aeldari_enhancements.py`:
`_main.index(reset) < _main.index(offer)`). Das Angebot lebt nicht mehr am Phasenwechsel, steht in
der DATEI also später und läuft zur LAUFZEIT trotzdem danach. Beide sind in je ZWEI Zeilen
umgedreht — Reset im Phasenwechsel-Block, Angebot in der aufgeschobenen Funktion und NICHT im
Block —, also stärker als vorher.

**Im ECHTEN Spiel belegt** (`verify_shooting_start_after_movement.py`, map4, die gemeldete Paarung).
**Es stagt NICHTS:** beide Hälften laufen an JEDER Movement→Shooting-Grenze, unabhängig vom Brett.

| | gefixt | `--neutralize` |
|---|---|---|
| Shooting-Grenzen erreicht | 2 | 1 |
| Start-Angebot lief **VOR** den Movement-Reaktionen | **0** | **1** |
| …lief danach | **2** | 0 |

Die Grenzen-Zahl selbst ist ein Nebenbefund: die neutralisierte Welt kommt weniger weit, weil Living
Lightning zum falschen Zeitpunkt feuert und die Schleife länger blockiert.

### 3. Die KI wartete unsichtbar auf einen Retro-thrusters-Zug

**User-Entscheidung: Hinweis + Warnung.**

**Kein Regelfehler.** `ai/agent_driver.py` hält den eigenen Zug offen, solange der Gegner eine
Retro-thrusters-Entscheidung am Ende der Fight-Phase schuldet — korrekt, 12.04 macht den Fight-Step
gemeinsam — und das einzige Zeichen dafür war EINE Zeile im Log. `game/retro_thrusters.py` schreibt
den Grund selbst aus: *„the button itself is only visible once the unit is selected."* Im Log Z. 1067
und 1447, beide Male unmittelbar gefolgt von „Player 2's turn ends.": der End-Turn-Klick des Menschen
ging durch und warf den Gratis-6"-Zug still weg.

Vier Hälften, jede mit eigener Sonde:

- **(a) Panel-Hinweis** in `_draw_fight_step_status()`, spiegelbildlich zu `_draw_pile_in_pending()`,
  in BEIDEN Zweigen (DONE und SELECTING) und in einem EIGENEN Akzent — die Pile-in-Farbe zu borgen
  ließe zwei verschiedene Meldungen als eine lesen. Der Controller kommt als ANGEHÄNGTES
  Keyword-Argument (Fehlerklasse 22).
- **(b) Brett-Ring** über `draw_retro_thrusters_pending()`, unterdrückt, solange eine
  Schadenszuteilung offen ist: das Brett darf nicht zwei Antworten auf zwei Fragen gleichzeitig
  ringen.
- **(c) Ein ZWEITER GRUND auf der bestehenden End-Turn-Warnung**, nicht ein neunter Eintrag in
  `_front_notice()`: beide beantworten dieselbe Frage („darf dieser Klick durchgehen"), und zwei
  Overlays müssten nacheinander weggeklickt werden. **Das Ein-Grund-Bild bleibt pixelgleich** — die
  Box wächst nur, wenn wirklich beide Gründe anliegen —, also gelten die schon abgenommene
  Darstellung und `smoke_end_turn_warning.py` per Konstruktion weiter.
- **(d) Eine Log-once-Zeile für JEDEN stillen KI-Halt.** Der Fight-Zweig des Treibers hatte gar kein
  `else`: jeder Nicht-DONE-Zustand war ein stummer Frame-Loop. Jetzt nennt er den GRUND (offener
  Pile-In des Menschen, 12.04-Alternation auf der Gegenseite, offene Aktivierung) — damit wird die
  ganze Fehlerklasse sichtbar, nicht nur dieser Pfad.

**`game/wait_notice.py` ist die Extraktion am zweiten Konsumenten:** „sag das genau einmal pro
Fight-Phase" beantworten Retro-thrusters und der neue Ansager gleichermaßen, nur mit verschiedenen
SCHLÜSSELN (einmal pro OWNER gegen einmal pro GRUND). Ein Ledger zweimal geführt ist die Drift, die
dieses Repo laufend konsolidiert.

**Bewusst NICHT gemacht:** `retro_thrusters_controller` kommt nicht in
`_has_unresolved_declaration()` — das wäre eine harte Sperre, und wer den Skip-Knopf nicht findet,
säße fest (vom User ausdrücklich verworfen).

**Getestet:** neu `test_retro_thrusters_notice.py` (**54/54**, sieben Abschnitte),
`test_fight_end_turn_warning.py` 44 → **56/56** (neuer Abschnitt 4 — die Suite deckte den zweiten
Grund wirklich nicht ab, was eine Sonde gefunden hat), plus `ab_retro_thrusters_notice.py`
(**12 A/B-Sonden, alle beißend**). `smoke_end_turn_warning.py`s einarmiger `warn_once`-Stub musste auf
`lambda self, *a, **k: False` nachgezogen werden, sonst bricht der Smoke; er läuft grün und sein
`--neutralize` weiterhin rot.

**Im ECHTEN Spiel belegt** (`verify_retro_thrusters_stall.py`, map2). GESTELLT wird EINE Tatsache —
dass überhaupt eine Einheit den Zug schuldet (die Fight-Phasen-Grenze plus The Twin Lance sind auf
diesem Harness passiv unerreichbar); alles danach ist echt:

| | gefixt | `--neutralize` |
|---|---|---|
| Controller landet im richtigen Panel-SLOT | **899 Frames** | 899 |
| Panel NENNT die Einheit | **3 von 3** Fight-Status-Frames | **0** |
| Brett RINGT sie | **884 Frames** | **0** |
| End Turn wird auf diesem Grund allein abgefangen | **ja** | **nein** |

Die erste Zeile ist in beiden Welten gleich und misst die ~80-Parameter-Kette POSITIONELL, indem sie
die echte Signatur bindet — die eine Sache, die ein Quell-Wächter nicht kann.

### 4. A Tempting Target zeigte sein gewähltes Objective nicht

**User-Entscheidung: Balken + Kopf der Karte.**

`card.detail` war der **allerletzte** Block der aufgeklappten Karte, nach der ganzen Prosa, ohne
Label, nicht fett — und alles außer Tag/Titel/Status wird überhaupt nur gezeichnet, wenn die Karte
aufgeklappt ist. Im Log steht das Ziel (Z. 1715), auf der Karte praktisch nicht.

**Die Einschränkung, die den Entwurf bestimmt hat: ELF Karten tragen ein `detail`, und sie zerfallen
in zwei Klassen.** Vier sind eine GEMERKTE WAHL (A Tempting Target, Beacon, Burden of Trust, Defend
Stronghold), **sieben sind ein LIVE-Fortschritt**, der sich jeden Frame ändert. `mission_cards.py`
hält als tragende Entscheidung fest, dass der Balken bewusst KEINE Momentaufnahme zeigt — das war die
erste Fassung und wurde auf User-Meldung entfernt (*„mir ist aufgefallen, dass ich gerade Center
Ground mitten im Zug schon erfüllt habe"*). Ein Balken, der Klasse B zeigt, führt genau diesen Fehler
wieder ein.

- **`SecondaryMissionCard.subject` ist EXPLIZIT vom Kartenautor gesetzt, keine Heuristik.** „Hat ein
  `on_draw`" wäre eine: Burden of Trust und Defend Stronghold haben keins, und eine Heuristik läuft
  beim nächsten Kartenautor still falsch. Dazu `detail_is_live=True` an den sieben — als
  MENGENDIFFERENZ geprüft (18 Kartenobjekte, 11 mit `detail`, 4 mit `subject`, 7 live, **0
  unklassifiziert, 0 beides**), damit eine zwölfte Karte sich benennen muss.
- **`subject` trägt NUR den Namen, nie die Live-Hälfte** („Objective Southeast", nicht „… (held by
  nobody)"). Die Invarianz gegenüber dem Brettzustand ist die tragende Testzeile.
- **Auf dem BALKEN ersetzt es das Timing, im KOPF der aufgeklappten Karte steht eine hervorgehobene
  `TARGET`-Zeile.** Das verliert nichts: `info_rows()` beginnt ohnehin mit `("WHEN", timing_label)`.
  `READY – N VP` schlägt weiterhin beides.
- **`_full_height()` ist UNVERÄNDERT, per Konstruktion:** die TARGET-Zeile ist eine gewöhnliche
  Info-Zeile, ihre Höhe fließt also über `_info_height()` ein, und `card.detail` ist für Klasse A
  `None`. Vorhersage und Zeichnung können nicht auseinanderlaufen — genau der Vergleich, der bei
  diesen Karten schon einmal einen doppelt gezählten Abstand gefunden hat.
- **Gemessen, warum das Timing weichen muss:** beides gleichzeitig auf dem Balken überläuft 3 von 4
  Karten (−2, −19, −57 px); das Subject an seiner Stelle passt auf allen vier (+100, +187, +102,
  +27 px).
- **`text_utils.ellipsised()` ist die Extraktion am zweiten Konsumenten** (aus `tile_screen.py`,
  das re-exportiert — die Aufrufstelle dort ist byte-identisch geblieben, damit
  `ab_menu_and_decline.py`s Anker überlebt).

**Getestet:** `test_mission_cards_ui.py` → **130/130** (neuer Abschnitt 10, auf PIXELN: das Ziel steht
auf dem EINGEKLAPPTEN Balken, der Titel behält seine natürliche Breite, die Vorhersage stimmt weiter
mit dem Gezeichneten), `test_secondary_missions.py` → **563/563** (Abschnitt 11, die
Klassifikations-Mengendifferenz). Neu `ab_mission_card_subject.py` (**10 A/B-Sonden, alle beißend**).
**Die tragende Gegenprobe:** eine Klasse-B-Karte darf auf dem Balken nichts Live-Abgeleitetes zeigen —
ohne sie bestünde der Abschnitt auch mit der wiedereingeführten Momentaufnahme.

**Drei eigene Testfehler, alle von den Sonden gefunden:** drei Sonden ließen die Suite ABSTÜRZEN statt
sie rot zu machen (`info[0][2]` auf einer 2-Tupel-Zeile); die „die Wahl kann dem Titel Platz
wegnehmen"-Sonde biss nicht, weil das Subject zu kurz war (jetzt eine absichtlich lange Fixture plus
eine Liveness-Zeile); und die Prüfung maß `card.status` statt des GEZEICHNETEN Textes — es gibt jetzt
`_last_bar_status`, dieselbe Idiom wie `_last_content_bottom`.

### Regression

**224 Suiten, ~20462 Prüfungen, 222 grün / 1 fremd rot / 1 bekannt**, `run_tests.py --smoke` komplett
grün (alle neun schweren Skripte), `smoke_end_turn_warning.py` grün mit rotem `--neutralize`,
`selfplay.py map4` mit `tau_retaliation` gegen `death_guard` (die gemeldete Paarung) und
`selfplay.py map2` mit den Defaults, beide exit 0. Unveränderlichkeits-Kontrollen:
`test_weapon_characteristics.py` **23/23** und `verify_rules_vs_engine.py` unbewegt gegenüber dem
Stand der Parallelsitzung.

**Der eine rote Fehlschlag gehört einer PARALLELEN Sitzung** (Fehlerklasse 20): `test_necron_titans.py`
und `ab_necron_titans.py` sind UNGETRACKT und mitten in der Necron-Etappe 9; die roten Zeilen nennen
`TriarchalMenhirProfile` und Relentless March, und die tragenden Dateien (`game/triarch_auras.py`,
`game/factions/necrons.py`, `game/units.py`) hat diese Arbeit nicht angefasst. Dieselbe Herkunft haben
die drei zusätzlichen Zeilen in `verify_rules_vs_engine.py` (67 → 70, alle Necron-Fahrzeuge).

**Fehlerklasse 21 hat wieder zugeschlagen, in einer neuen Form:** ein `\n` in einem Python-String,
über ein `<<'PY'`-Heredoc geschrieben, kam als ECHTER Zeilenumbruch an — der Anker traf danach nie,
und die Ersetzung meldete stumm `AssertionError`. **Ein Pin, der Einrückung festhält, ist ohnehin der
falsche Pin:** die betroffene Zeile ist durch eine AST-Prüfung ersetzt worden, und der
Reihenfolge-Vergleich daneben von `index()` auf `find()` — ein fehlender Anker muss ROT werden, nicht
den Lauf abbrechen.

## GRENADES fehlte auf 18 Profilklassen — Explosives unerreichbar (2026-09-12)

**Gemeldet:** *"warum kann ich mit meinem autarch+ scorpions keine explosives einsetzen?"*, dann
*"kann es sein, dass es daran liegt, dass ich 0 cp habe? aber der autarch reduziert es auf 0."*

- **Ursache ist eine TRANSKRIPTIONSLÜCKE, dieselbe Klasse wie CHARACTER und EPIC HERO.** Das
  Autarch-Datenblatt druckt `GRENADES`, `AutarchProfile` setzte das Flag nie. Striking Scorpions
  drucken es nicht — also hatte 19.03s Keyword-Pooling nichts zu poolen, `_qualifying_models()` war
  leer, und Explosives wurde **nie** angeboten, mit oder ohne CP.
- **Gemessen über alle 161 Datenblätter gegen die GEDRUCKTE Leiste** (`rules_text.keywords_for()`):
  15 druckten GRENADES ohne ein einziges Flag (14 Aeldari — Asurmen, beide Autarchs, Baharroth,
  Fuegan, alle drei Corsair-Trupps, Dire Avengers, Fire Dragons, Guardian Defenders, Storm Guardians,
  Swooping Hawks, Starfangs — plus Plague Marines), eins nur teilweise (die zwei Kroot Hounds in
  Kroot Farstalkers, 10 von 12). Die ganze Aeldari-Fraktion hatte außer den Starfangs' eigener
  Fähigkeit **null** `grenades`-Flags.
- **Das Flag sitzt auf den BLATT-Klassen, nie auf einer geteilten Basis:** `CorsairProfile` trägt
  auch Kharseth und Prince Yriel (ohne GRENADES), `KrootHoundProfile` die eigenständigen Kroot Hounds
  (ohne). Exarchen, Felarchs, Specialists und der Plague Champion erben. Die Plattformen der
  Guardians bekommen es mit, weil die Leiste unit-weit ohne Pro-Modell-Aufteilung gedruckt ist.
- **Einzige Leser** sind `explosives.py` und `enh_internal_grenade_racks.py` — die Änderung wirkt
  also nur auf 15.05. **Folge für die KI:** `_handle_explosives_for_squad()` bietet ihr Explosives
  jetzt auch für diese Einheiten an (regelkonform, über `declined_explosives` einmal je Phase).
- **Die CP-Frage war ein ZWEITER, legitimer Grund, nicht die Ursache.** Path of Command rechnet
  korrekt mit (`_cost_for()` faltet `cost_discounts` vor dem Leistbarkeits-Test, 0 CP reichen) —
  aber einmal pro Schlachtrunde PRO ARMEE. Im Log (`game_20260912_225758.log:686`) war er in Runde 2
  schon für Blitzing Firepower auf dieselbe Einheit ausgegeben, und in dieser Phase blockierten
  zusätzlich 15.01 (die Einheit war schon Stratagem-Ziel) und "eligible to shoot".
- **Getestet:** `test_explosives.py` 30 → **42/42** — §10 der Sweep über alle Fraktionen in BEIDE
  Richtungen mit Liveness, §11 die gemeldete Einheit durch `attached_units.attach()` (nur das
  Autarch-Modell wirft; 0 CP ohne Rabatt abgelehnt mit Grund; mit unverbrauchtem Path of Command
  angeboten; nach Verbrauch abgelehnt; nächste Runde wieder frei). Neu `ab_explosives_grenades.py`
  (**3 A/B-Sonden, alle beißend** — Autarch-Flag weg, alle 18 weg, Leck auf die geteilte
  Kroot-Hound-Basis). Volle Regression **228 Suiten, ~20938 Prüfungen, 226 grün / 1 rot / 1 bekannt** —
  der eine rote ist `test_ere_we_go.py` (seit Orks E2 gelöscht), die dokumentierte Parallel-Runner-Flake,
  einzeln 3 von 3 grün.
