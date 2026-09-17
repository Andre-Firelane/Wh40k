# Aktionen und Primary Missions

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Aktionen (Regel 16.01, game/actions.py)

**Diese Engine hatte bis Cleanse überhaupt keinen Aktions-Begriff** (`game/fall_back.py` schrieb das
selbst aus, CLAUDE.md führte es als benannte Lücke). Der User lieferte den Kernregeltext von 16.01
wörtlich; `game/actions.py` ist dessen Transkription plus genau die Haken, die die erste Karte
braucht — kein spekulatives System.

- **`ActionDefinition` sind die sechs gedruckten Felder und nichts weiter** (STARTS / UNITS /
  USE LIMIT / COMPLETES / EFFECT plus Zusatzbeschränkungen), also ist eine neue Aktion ein Objekt
  und keine neue Mechanik.
- **EIN `ActionController` für ALLE Aktionen**, nicht einer pro Aktion: Eignung, die zwei Sperren
  und der Bewegungs-Abbruch sind geteilt, und *"it started another action this turn"* ist eine
  Frage über alle gleichzeitig.
- **Die zwei Sperren liegen NICHT als Squad-Flags herum**, sondern werden bei diesem einen
  Controller erfragt — `shooting.can_shoot()` und `charge.can_declare_charge()` beantworten diese
  Fragen schon, ein zweiter Merker wäre die Drift, die dieses Repo laufend konsolidiert.
  - **Die Asymmetrie ist gedruckt und einzeln gepinnt:** die Schuss-Sperre nimmt TITANIC aus, die
    Charge-Sperre NICHT.
  - **Beide Sperren überleben den ABBRUCH der Aktion.** Wer eine Aktion begonnen hat, hat sie
    begonnen — eine Bewegung nimmt die Vollendung, nicht die Sperre.
- **Der Bewegungs-Abbruch bekommt die Bewegungs-ART übergeben** (`notify_move(squad, move_mode)`),
  gemeldet aus `confirm_move()` — der einen Stelle, durch die jede bestätigte Bewegung läuft. Die
  zwei gedruckten Ausnahmen (Pile-In, Consolidate) werden damit BEIM NAMEN erkannt statt geraten,
  und eine neue Bewegungsart muss sagen, welche sie ist.
- **AIRCRAFT, FORTIFICATION und TITANIC sind belegte No-ops** (keines der Keywords existiert hier,
  dieselbe Ausnahme, die `rapid_ingress.py` schon dokumentiert) — trotzdem ausgeschrieben und die
  Profil-Flags gelesen, damit die Transkription vollständig bleibt.
- **`start_eligibility()` gibt einen GRUND zurück**, nicht nur False: ein Angebot, das lautlos nicht
  erscheint, ist genau die Form, in der sich ein Eignungsfehler versteckt.
- **`reset_for_turn()` läuft NACH `begin_end_of_turn()`** — vorher zu löschen würfe die Aktionen
  dieses Zuges unvollendet weg, und der Quell-Wächter prüft die Reihenfolge.

## Primary Missions über Force Dispositions (game/primary_missions.py)

**Jedes Detachment lässt mindestens eine Force Disposition zu (fast alle genau eine, War Horde seit
dem Ork-Codex 2026-09 zwei); die Liste schreibt eine davon fest, und die bestimmt die Primary
Mission** (User: "jedes detachment hat zugang zu einer force disposition.
diese wählt man beim listen bau ... ist aber in der Liste festgeschrieben"). Fünf Dispositionen,
fünf gelieferte Karten. **Nur Spieler 1** — die KI behält "Hold the Line"
(`config.PRIMARY_MISSION_CARD_PLAYERS`).

**Die Dispositionen sind TRANSKRIPTION, nicht Zuweisung.** Sie standen die ganze Zeit im Cache:
Wahapedia druckt sie als ICON im `<h2>` jedes Detachments, direkt neben den DP, die der Scraper
schon las — `page_headings()` strippt die Tags und warf damit genau das Icon weg.
`heading_force_dispositions()` ist der zweite Pass über das ROHE Heading-HTML, `--offline` reicht
(0 Netzzugriffe), und **alle 56 Detachment-`.md` tragen die Zeile** neben ihren DP. Der Diff IST
die Evidenz; zwei Läufe erzeugen 56 byte-identische Dateien.
- **Das Heading ist auch der einzig sichere Weg:** die Detachment-FILTER-Liste derselben Seite
  schreibt "Kauyоn" mit KYRILLISCHEM о (U+043E) — dieselbe Falle, die `fetch_datasheet_rules.py`
  schon für `dsLeftСolKW` dokumentiert. Das Heading schreibt lateinisch, und
  `rules/tau_empire/detachments/Kauyon.md` heißt bereits so.
- **Gegenprobe zur Vertrauenswürdigkeit:** alle 10 automatisch vergleichbaren DP-Werte des Repos
  stimmen mit Wahapedia überein. `test_force_dispositions.py` pinnt die 17 modellierten
  Detachments gegen den KORPUS, nicht gegen Literale.

| Liste | Detachment | Disposition | Primary Mission |
|---|---|---|---|
| Aeldari | Seer Council + Path of the Outcast | Priority Assets | **Secure Asset** |
| Aeldari (`aeldari_warhost`) | Warhost | Reconnaissance | **Reconnaissance Sweep** |
| Aeldari (`aeldari_guardian_battlehost`) | Armoured Warhost + Guardian Battlehost | Take and Hold | **Battlefield Dominance** |
| Orks | War Horde | Take and Hold | **Battlefield Dominance** |
| Necrons | Awakened Dynasty | Take and Hold | **Battlefield Dominance** |
| Necrons (`necrons_hypercrypt`) | Hypercrypt Legion | Reconnaissance | **Reconnaissance Sweep** |
| T'au (`tau`) | Kauyon + Adv. Acquisition Cadre | Reconnaissance | **Reconnaissance Sweep** |
| T'au (`tau_montka`) | Mont'ka | Priority Assets | **Secure Asset** |
| T'au (`tau_recon`) | Advanced Acquisition + Auxiliary + Experimental Prototype Cadre | Reconnaissance | **Reconnaissance Sweep** |
| T'au (`tau_retaliation`) | Retaliation Cadre | Purge the Foe | **Unstoppable Force** |
| Death Guard | Death Lord's Chosen | Priority Assets | **Secure Asset** |

**ZWEI Listen fielden ein Detachment-PAAR, und nur eine davon hat wirklich eine WAHL.** Bei den
T'au hat der User sie benannt ("für die Tau Liste nehme ich reconnaissance (advanced acquisition
cadre)") — beide ihrer Detachments gewähren ohnehin Reconnaissance, die Wahl fällt also auf
dieselbe Mission, aber WOHER sie kommt ist die Listenbau-Tatsache und steht aufgeschrieben. Bei den
Aeldari gewährt das Paar seit dem 2026-09-01-Tausch **zwei verschiedene** (Seer Council Priority
Assets, Path of the Outcast Reconnaissance) — die erste echte Wahl hier. Sie bleibt auf Priority
Assets: die Bitte nannte ein Detachment, keine andere Primary Mission, also steht die Deklaration,
wo sie stand. EINE Zeile in `ARMY_LISTS`, falls das nicht gemeint war.

**VIER der fünf Missionen werden gespielt; DEATH TRAP ist wieder dormant.** Die Geschichte lohnt
den Eintrag, weil sie zweimal gekippt ist: die zwei letzten waren lange gebaut, getestet und per
Konstruktion unerreichbar, weil kein Roster ihr Detachment fieldete; die drei T'au-Listen vom
2026-09-05 holten sie (Prototypes → Death Trap, Retaliation Cadre → Unstoppable Force); und am
2026-09-07 wurde die Prototypes-Liste auf User-Wunsch zurückgezogen ("diese liste kann weg"),
womit Death Trap zurückfiel. **Es ist die einzige, und sie ist eine Zeile davon entfernt, wieder
live zu sein:** Disruption gewähren Auxiliary Cadre UND Windrider Host, beide modelliert — jede
Liste, die eines davon deklariert, holt sie zurück.

Der Pin, der das festhält, ist zweimal zu Recht rot geworden und ist genau dafür gesetzt. Er nennt
die dormante Mission jetzt NAMENTLICH statt nur zu zählen, und pinnt zusätzlich, dass gar keine
ausgelieferte Liste mehr Disruption deklariert — sonst läse sich "eine ist dormant" auch auf einem
Stand, auf dem eine andere es geworden ist.

### Warum das keine `SecondaryMissionCard` ist

Eine Secondary ist EINE Karte mit EINEM Zeitpunkt, EINMAL einlösbar, aus einer Hand. Eine Primary
ist EINE Karte für die ganze Schlacht mit MEHREREN unabhängigen Wertungsboxen — je eigener
Zeitpunkt, eigenes Rundenband — und **jede zahlt JEDES Mal**, wenn ihr Zeitpunkt eintritt.
`ScoringBox(key, timing, score, label, min_round, max_round)`; `score(ctx)` ist eine reine
Funktion wie bei einer Secondary.

**Automatisch, ohne Prompt.** Die Secondary fragt, weil eine Karte eine Ressource ist, die man
aufheben kann. Eine Primary bietet keine Wahl: eine Karte, nicht abwerfbar, jede Box eine feste
Bedingung. **Folge: die Headless-Harnesses brauchen KEIN Opt-out** (anders als beim Kartenstapel),
`selfplay.py` und alle Smokes fahren die echte Primary in jedem Lauf mit — als Abwesenheit
getestet, damit der neunte Harness es nicht "vorsorglich" abschaltet. **Kein VP-Cap**
(User-Entscheidung; die Karten drucken keinen, und Hold the Line hat auch keinen).

### Drei Zeitpunkte, alle an einer BESTEHENDEN Naht in main.py

| Timing | Naht |
|---|---|
| END OF YOUR TURN | `if ending_player is not None:` |
| END OF CMD PHASE | `if phase_before == PHASE_COMMAND:` mit `mover_before` |
| END OF BATTLE | `_check_battle_end()`, VOR `battle_end_overlay.show()` |

**Das ENDE der Command-Phase ist NICHT der Zeitpunkt, an dem Hold the Line wertet** (deren Naht
ist der ANFANG). Battle Shock liegt dazwischen, und die OC einer geschockten Einheit wird zum
Strich (01.07/02.02) — wer was kontrolliert kann sich zwischen den beiden also echt
unterscheiden. Eigene Testzeile.

### Vier Zugbeginn-Schnappschüsse, nach dem Vorbild von Overwhelming Force

Drei Boxen fragen nach einem Moment, der beim Werten vorbei ist, und nach Einheiten, die es dann
nicht mehr gibt: `enemies_in_terrain_at_turn_start` (Death Trap braucht WELCHE Area),
`enemies_on_central_objective_at_turn_start` (Secure Asset), `objectives_controlled_at_turn_start`
(Unstoppable Force). Zu Beginn JEDES Zuges, bedingungslos — ob eine Box sie braucht, steht dann
nicht fest.

### Die zwei Objective Actions — Regel 16.01 trug beide ohne neue Mechanik

- **Secure Asset** ist Cleanse mit PLUNDERS Use Limit (einmal pro ZUG, nicht Cleanses
  Eindeutigkeit pro Objective) — zwei Formen, die gleich aussehen.
  **Seit 2026-09-10 teilen die zwei auch ihr START-Tor** (`mission_context.objective_action_
  targets_for()`): dieselbe UNITS- und dieselbe COMPLETES-Zeile, also darf es nicht zwei Kopien
  geben — es gab sie, und beide waren gleich falsch. Siehe `## Cleanse bot einen Knopf an, der
  nicht auszahlen konnte`.
- **Booby Trap** ist Plunders Form (`completes_immediately`) mit CLEANSES Use Limit
  (Eindeutigkeit auf dem Ziel). Es ist die einzige Action mit einem echten CALLBACK, weil
  *trapped* eine bleibende Tatsache über das BRETT ist statt über diesen Zug.
  - **Zwei Buchführungen, zwei Lebensdauern**: `trapped` (ganze Schlacht — die UNITS-Zeile sagt
    "not yet trapped") und `trapped_this_turn` (was die 2-VP-Box zählt, am Zugende geleert). In
    eine gefaltet würde entweder dieselbe Area jede Runde 2 VP zahlen oder die zweite Runde
    unsichtbar.
  - Der Zustand liegt im CONTROLLER, **nicht** auf `TerrainArea` (die trägt gar keinen) und
    **nicht** aus den `ActionState`s abgeleitet wie bei Plunder: `reset_for_turn()` leert die
    jeden Zug, *trapped* überlebt sie.
  - "Diese Area IST ein Objective" ist IDENTITÄT, nicht Geometrie — `GameState.add_objective()`
    gibt dem Objective genau die `TerrainArea`, die in `state.terrain_areas` steht.
- **`ActionController.resolve_end_of_turn()` bekam einen Idempotenz-Wächter** (`(player, turn)`,
  geleert in `reset_for_turn()`): ZWEI Missionssysteme besitzen jetzt Actions und fragen an
  derselben Naht. Zweimal aufgelöst feuerte jeden EFFECT zweimal — lautlos, weil ein Effekt nichts
  zurückgibt. **Gemessen mit einer konstruierten Action mit echtem Effekt**, weil keine der vier
  ausgelieferten an dieser Naht einen hat (drei geben `effect=None`, Booby Traps feuert bei
  `start()`) — eine A/B-Sonde ohne den Wächter änderte deshalb NICHTS Beobachtbares.
- Der hartkodierte Slot-Name (`if action.key == "plunder" else ...`) wandert als `result_slot`
  auf die `ActionDefinition`. Verhaltensgleich für die zwei alten Karten — der Gewinn ist, dass
  eine dritte Action nicht im else-Zweig landen kann, und genau das prüft der Test.

### `central_objectives()` — geometrisch, ohne erfundene Konstante

Nötig für Secure Asset und Unstoppable Force. **map3 hat gar kein Objective namens "Central"** —
seine Mitte ist eine 9"-Scheibe mit ZWEI Objectives. Also: **das der Brettmitte nächste, Gleichstand
zählt mit**, Kandidaten sind die No-Man's-Land-Objectives. Gemessen:

| Karte | zentral | nächstbestes |
|---|---|---|
| map1 | Central Objective 0.00" | 17.35" |
| map2 | Central Objective 0.00" | 19.96" |
| map3 | Objective East + West, je 6.13" | 22.78" |
| map4 | Central Objective 0.00" | 20.24" |

**map3s Gleichstand ist BIT-IDENTISCH** (Differenz exakt 0.0), die 0.001"-Toleranz ist auf den
ausgelieferten Karten also nachweislich INERT und nur das Netz für eine künftige Karte, deren
Spiegelung durch andere Arithmetik läuft (dieselbe 7e-15-Sorte, die schon einmal aus einem
Rechteck ein Fünfeck gemacht hat). Der Home-Ausschluss ist ebenfalls ein gemessener No-op auf
allen vier Karten — und wird deshalb an einem KONSTRUIERTEN Brett geprüft, auf dem ein
Home-Objective wirklich das nächste zur Mitte ist. **map4 ist der klarste Fall der Tabelle:** sein
Mittelstück steht EXAKT auf der Brettmitte, ist damit sein eigener 180°-Spiegel, und die zwei
nächsten stehen 20.24" weit weg — hier arbitriert weder die Toleranz noch der Ausschluss.

### 26. Extraktion: `game/mission_context.py`

Die Primaries sind der ZWEITE Konsument von `MissionContext` und dem ganzen Geometriesatz.
Andersherum zu importieren hätte die PRIMARY von der SECONDARY-Deck abhängig gemacht — zwei
Systeme, die nichts teilen außer dieser Geometrie, und eines davon ist für die meisten Spieler aus.
`secondary_missions.py` **re-exportiert alles**, also sind seine 17 Karten und die 552 Prüfungen
seiner Suite **per Konstruktion** unverändert (im Test als Objekt-IDENTITÄT gepinnt, nicht als
Gleichheit — dieselbe Idiom wie `is_tau_unit` und `has_detachment`).
`ENGAGE_CENTRE_EXCLUSION_IN` heißt dort jetzt `CENTRE_EXCLUSION_IN`, weil Reconnaissance Sweep die
6"-Klausel wörtlich genauso druckt (Fehlerklasse 11) — der alte Name bleibt als Alias auf DENSELBEN
Wert.

### Getestet

- Neu `test_primary_missions.py` (**250/250**, dreizehn Abschnitte) und
  `test_force_dispositions.py` (**146/146**, sieben Abschnitte).
- **33 A/B-Sonden an der QUELLE (`ab_primary_missions.py`), alle beißend.** **Fünf bissen zuerst
  NICHT, und alle fünf waren Befunde über den TEST** (Fehlerklasse 24): die
  Trapped-Persistenz-Prüfung war von 16.01s eigenem Per-Zug-Limit MASKIERT (der Test räumt jetzt
  `reset_for_turn()` dazwischen, wie main.py es tut); der Idempotenz-Wächter war ohne eine Action
  mit echtem Effekt unmessbar; der `result_slot` ist für die zwei alten Karten verhaltensgleich;
  der Home-Ausschluss in `central_objectives()` ist auf allen drei Karten ein No-op; und die
  Scraper-Sonde las Dateien, die schon auf der Platte lagen, statt den Parser.
- **Neu `smoke_primary_mission.py`** — die drei Nähte durch `main()`s ECHTE Schleife, weil ein
  Quell-Wächter nicht zeigt, dass sie LAUFEN, und dieses Repo sechs "gebaut, aber nie
  gefüttert"-Fälle hat. `--neutralize` kippt 7 von 21 Prüfungen. Es unterscheidet dabei Secure
  Assets +8 von Hold the Lines +9 auf demselben Brett — eine Prüfung, die "es hat überhaupt
  gewertet" nicht leisten kann.
- **Ein echter Fehler, den nur der AST-Wächter fand:** `Renderer.draw_terrain_markers()` rief
  `_clamp_rect_to_surface()` als freien Namen, obwohl es eine statische METHODE ist — ein
  `NameError` beim ersten Marker MIT Label. Weder Suite noch Smoke erreichten die Zeile (der Smoke
  setzt seine Falle im letzten Frame). `test_event_chain_wiring.py` Abschnitt 1b hat ihn gemeldet;
  jetzt gibt es zusätzlich einen VERHALTENStest, der wirklich auf eine Surface zeichnet.
- **Zwei fremde Pins wurden zu Recht rot** und sind ehrlicher nachgezogen: `test_actions.py` pinnte
  den hartkodierten Sekundär-Aufruf des Panels (das Panel fragt jetzt BEIDE Systeme), und
  `test_secondary_missions.py` pinnte den EXAKTEN mehrzeiligen `mission_cards_overlay.draw()`-Aufruf
  — ein Wächter, der Whitespace pinnt, scheitert an Formatierung statt an Bedeutung.
- **`test_detachments.py`s `fielding()` musste die Disposition mitleeren:** eine hypothetische
  Detachment-Menge trägt keine Meinung darüber, mit welcher Disposition die Liste geschrieben
  worden wäre, und die echte stehenzulassen ließ jeden Block an einer Regel scheitern, um die
  keiner von ihnen geht.
- Volle Regression **162 Suiten, ~14249 Prüfungen, 161 grün / 0 rot / 1 bekannt**, alle neun
  Smokes plus fünf `--neutralize`-Gegenproben rot, `selfplay.py` auf map2 und map3.
- **Im ECHTEN Spiel belegt:** je ein `selfplay.py`-Lauf unter JEDER der fünf Dispositionen (alle
  exit 0), jeder mit seiner eigenen `[primary]`-Zeile im Log — also auch die zwei dormanten
  Missionen. Und die Wertung selbst: `Player 1 scores 2 Primary VP (Battlefield Dominance - MORE
  OBJ)` neben `Player 2 scores 3 Primary point(s)` — der Mensch auf seiner Karte, die KI auf Hold
  the Line, in derselben Runde.

### Die Ökonomie, gemessen — weil es keinen Cap gibt

Da kein VP-Cap existiert, ist die Größenordnung eine Aussage und keine Formalie. Gemessen auf
map2 (5 Objectives), VP je Schlachtrunde NUR aus den Objective-Boxen — ohne Kills, ohne Actions,
ohne Spread:

| gehalten | Hold the Line | Battlefield Dom. | Recon Sweep | Unstoppable | Secure Asset |
|---|---|---|---|---|---|
| 1 (nur Home) | 6 | 3 | 0 | 0 | 0 |
| 3 | 18 | 13 | 3 | 8 | 8 |
| 5 | 30 | 23 | 3 | 16 | 8 |

Über eine ganze Schlacht mit konstant 3 von 5 gehaltenen Objectives: Hold the Line **90 VP** (fünf
Runden), Battlefield Dominance 52, Unstoppable Force und Secure Asset je 32, Reconnaissance Sweep
12. Die drei niedrigen holen ihren Rest woanders (Recon aus Spread 3-6/Zug plus 1 je Kill, Secure
Asset aus 4/Zug für die Action, Unstoppable aus Kills plus 5 in der Endwertung). Zwei Zeilen der
Tabelle sind Regeln, keine Balance: bei EINEM gehaltenen Objective zahlen drei der vier Karten
NULL, weil ihre Box das eigene Home-Objective ausschließt; und Battlefield Dominance zieht bei
hoher Kontrolle davon, weil ihr kumulativer Home-Bonus jedes Vorwärts-Objective von 3 auf 5 hebt.

**Die Aussage dieser Tabelle hat sich UMGEDREHT, und das ist bestellt.** Sie las früher "die Karten
liegen in derselben Größenordnung wie die Mission der KI, nicht darüber" — bei 3 VP je Objective
kam Hold the Line auf 45 gegen die 52 von Battlefield Dominance. Auf User-Wunsch zahlt sie jetzt
**6 statt 3** (und No Mercy **3 statt 1**, siehe unten), also liegt die KI-Mission deutlich VORNE.
Es ist ein bewusster Handicap-Regler zugunsten der KI, keine Balance-Messung; die Zahlen stehen
hier, damit die nächste Änderung an einer Force-Disposition-Karte weiß, wogegen sie antritt.

### Bewusst offen

Kein KI-Pfad (Spieler-1-Vorgabe, als Negativraum geprüft: kein neuer Name in
`ai/agent_driver.py`); und die "OPPONENT: TAKE AND HOLD"-Annahme aller fünf Karten wird NICHT
erzwungen, sondern bei Verletzung als `[primary]`-Logzeile benannt (beide Default-Listen erfüllen
sie).
