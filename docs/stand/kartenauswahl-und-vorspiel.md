# Kartenauswahl und Vorspiel

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Kartenauswahl (game/ui/map_select.py)

**Der erste Screen des Spiels** (User: "Vor der Fraktion würde ich jetzt allerdings gerne noch die
Map auswählen. Da wäre es cool, wenn ein Screenshot der Map angeboten werden würde"). Er läuft vor
der Listenauswahl und lange vor dem Vorspiel, weil alles Weitere daran hängt: Brettmaße, Zonen,
Terrain — und auf map3 sogar, WELCHE Einheiten überhaupt antreten (`BattleMap.army_roster`).

- **Die Vorschau ist GERENDERT, kein Screenshot** (`game/ui/map_preview.py`). Ein von Hand
  gespeichertes PNG wäre eine zweite Kopie der Karte, und das Erste, was es täte, wäre veralten —
  das Terrain beider großen Karten ist mehrfach nachgemessen, begradigt und neu gewählt worden.
  Gezeichnet wird die statische Ebene durch denselben `Renderer`, den das Spiel benutzt: Boden,
  jedes Terrain-Footprint samt Wänden, beide Deployment-Zonen und die Objective-Marker. Keine
  Modelle — es ist ja noch nichts aufgestellt.
- **Die Vorschau darf `config` NICHT anfassen.** Der Screen läuft VOR `maps.apply_to_config()`, also
  steht dort noch das Brett des letzten Laufs. Eine Vorschau, die die Maße ihrer Karte hineinschriebe,
  würde das Schlachtfeld allein dadurch entscheiden, dass man sie ANGESEHEN hat. Sie muss es auch
  nicht: `Renderer` bekommt sein `Board` als Argument und `BattleMap.build()` liest die eigenen Maße.
  Als Prüfung festgehalten, nicht als Zusage.
- **Alle Karten werden in DIESELBE Box letterboxed** (gleiche Breite, gleiche Höhe, Seitenverhältnis
  erhalten). Die vier Bretter haben zwei Formen (44×60 hoch, 3× 60×44 quer; das 30×30-Testbrett ist
  seit map3 weg) — Kacheln mit je eigener Bildhöhe läsen sich als Layout-Unfall, in einer
  gemeinsamen Box ist die Form des Bretts selbst Teil der Aussage. Genau dafür ist ein Bild besser als eine Beschreibung.
- **Die Textzeile wiederholt die Brettgröße NICHT** — die steht schon im Kartennamen ("Take Cover
  (44"x60", portrait)"). Stattdessen Zonentiefe und Niemandsland (map1 18"/24", map2 12"/20", map3
  21"/12.7", map4 17.5"/25") plus Terrain- und Objective-Zahlen, alles am GEBAUTEN Brett gezählt
  statt danebengeschrieben. **map4 ist die Karte, mit der der PAGER dieses Screens scharf wird:**
  vier Kacheln passen erst ab 1920 px nebeneinander.
- **Er trägt seit den Biomen auch DEREN drei Knöpfe** (ganz oben im Kopfzeilen-Balken, siehe
  `## Biome` unten) — sie gehören hierher, weil die Kacheln darunter Bilder des Bretts sind
  und ein Biom-Klick sie neu malt.
- **`config.MAP_SELECT`** schaltet ihn; `--map` ist eine ANTWORT und überspringt ihn deshalb,
  ebenso `--no-map-select` und ein `--load`-Szenario (der Snapshot nennt sein Brett selbst).
- **`pygame.display.set_mode()` ist in `main()` nach oben gewandert**, vor `apply_to_config()` — ein
  Screen braucht ein Fenster. Zwischen beiden liest nichts eine Brettdimension, was den Tausch
  sicher macht; die Reihenfolge (Fenster → Karte → Brett → Armeen → Einheiten) ist als Quell-Wächter
  in `test_map_select.py` festgenagelt.

**`game/ui/tile_screen.py` ist das geteilte Gerüst beider Screens** — vierzehnte Extraktion, am
ZWEITEN Konsumenten wie die Konvention es verlangt: Seitenrechnung, Kachelrechtecke, Kopf- und
Fußzeile, Kachelrahmen und die Event-Schleife. NICHT darin: was in einer Kachel steht, wie hoch sie
sein muss und was ein Klick bedeutet — genau das ist der ganze Unterschied, und eine Basisklasse, die
das mitbesitzen wollte, wäre nur eine abstrakte Methode pro Unterschied gewesen. Deshalb Funktionen
plus ein kleiner `Paged`-Mixin, und jeder Screen behält seine eigene Klasse. Ein Quell-Wächter
verlangt von BEIDEN, dass sie wirklich hindurchgehen.

### Eine Kachel ist so hoch wie ihr INHALT, nicht wie das Band (2026-09-09)

**Gemeldet:** *"Die map kacheln sind sehr hoch. unten der text ist sehr gequetscht und fällt
teilweise raus. mach die kacheln etwas kleiner. dann hat der NEXT button auch etwas mehr platz."*

**ZWEI Fehler in einer Meldung**, beide vor jeder Änderung an der Quelle reproduziert — und
**196 grüne Prüfungen sahen keinen von beiden**, weil zu diesem Layout nie jemand die HÖHE gemessen
hat (`test_map_select.py` prüfte "jede Kachel liegt im Fenster" und "jede Vorschau liegt in ihrer
Kachel", also genau die zwei Aussagen, die auch für eine zu hohe Kachel gelten).

1. **`_text_height()` reservierte EINE Namenszeile.** Drei der vier ausgelieferten Karten tragen
   ihr Layout im Namen (`Take Cover (44"x60", portrait)`) und brechen in einer Kachel auf ZWEI
   Zeilen um. Gemessen bei 1920×1080: die letzte Zeile endet bei y=1013, die Kachel bei 1010, der
   Fußzeilen-Streifen beginnt bei 1016 — der Text stand also **3 px unter seiner eigenen Kachel
   und im Fußzeilenband**. Das ist das gemeldete "fällt teilweise raus", und der Bodenrand
   (`TILE_PAD`) war restlos aufgebraucht.
2. **Die Vorschau-Box nahm "was übrig bleibt".** Damit füllte jede Kachel das ganze Band, egal was
   die Bretter brauchen: Box 414×796, während das HÖCHSTE Brett (map1, 44"×60") davon nur 565
   füllt und die drei Querformat-Bretter nur 303 — **231 px jeder Kachel und 493 px der meisten
   waren leere Platte**. Das ist "die kacheln sind sehr hoch".

- **Der Fix ist eine MESSUNG, keine Konstante:** `_preview_box_height()` fragt die Karten dieses
  Screens nach dem höchsten Seitenverhältnis (`map_preview.surface_for()` letterboxt mit
  `min(box_w/w, box_h/h)`, jeder Pixel darüber ist auf JEDER Kachel tot). Eine neue Karte mit
  höherer Form hebt den Deckel von selbst. Über `items` statt über die SEITE, aus `fit_page()`s
  Grund: eine zwischen Seiten wechselnde Boxhöhe skalierte die Bilder unter dem Cursor um.
- **Die geteilte EINE Box bleibt** — sie ist eine dokumentierte Entscheidung ("so lines up a
  portrait board with a landscape one, und die Form des Bretts ist selbst Teil der Aussage").
  Gedeckelt wird auf das MINIMUM, das sie einlöst; die Letterbox-Balken der Querformat-Bretter
  bleiben also und sind Absicht.
- **`name_lines` wird an derselben `wrap_text()`-Stelle gemessen, die das Zeichnen benutzt** —
  eine Reservierung, die aus einer zweiten Quelle kommt, ist genau die Drift, aus der der Fehler
  entstand.
- **Zentriert im Band über `ts.grid_block()`**, dem VIERTEN Konsumenten: die zurückgewonnene Höhe
  je zur Hälfte über und unter die Reihe, und die untere Hälfte IST der Platz, den die Fußzeile
  brauchte. Nicht oben angenagelt — das Argument steht schon im Docstring des Helfers ("eine Reihe
  an der Decke mit einem Loch darunter").
- **Gemessen, 1920×1080:** Kachel **906 → 700 px**, Text **+3 px Überstand → 22 px Luft** in der
  Kachel, Abstand zur Fußzeile **−3 → 131 px**. **Bei 1600×900 und darunter bewegt sich die HÖHE
  nicht** — dort passt ein Hochformat-Brett ohnehin nicht in seine Breite, der Restplatz bindet
  weiter; nur die Reservierung wird richtig (der Zwei-Zeilen-Name von map3 lag dort ebenfalls 3 px
  daneben).
- **Getestet:** `test_map_select.py` 166 → **196/196** (neuer Abschnitt 3b) plus neu
  `ab_map_tile_height.py` (**7 A/B-Sonden, alle beißend**; die ganze Vor-Fix-Welt kippt 15 von
  196). Der Abschnitt misst den Textboden so, wie `_draw_tile()` ihn läuft, statt gegen die
  Reservierung zu prüfen, die ihn erzeugt hat — und trägt eine LIVENESS-Zeile ("mindestens ein
  Name bricht wirklich um"), weil jede Textprüfung auf einer Seite mit lauter Ein-Zeilen-Namen
  vakuum-grün besteht. Dazu zwei GEGENGEWICHTE, ohne die der Deckel auch bei einer auf nichts
  geschrumpften Box bestünde (das höchste Brett muss die Box füllen, und das Bild muss die Kachel
  weiter dominieren).
  - **Eine Sonde war ein Befund über den TEST** (Fehlerklasse 24) und musste die DATEI wechseln:
    die Vakuitäts-Sonde kürzte zuerst den Namen im ZEICHNEN — die Suite ruft `wrap_text()` aber
    selbst, auf dem echten Namen, maß also weiter zwei Zeilen und meldete NO BITE. Sie schreibt
    jetzt `game/maps.py`, weshalb der Sonden-Treiber die Zieldatei pro Sonde führt.
- **Im ECHTEN Spiel belegt:** `smoke_setup_screens.py` **17/17** — der Screen wird weiter durch
  `main()`s echte Schleife geklickt (Biom, Kachel, Confirm), und `main()` spielt auf der geklickten
  Karte.

### Auswählen und BESTÄTIGEN — zwei Takte statt einem

**Ein Klick wählt AUS, erst der Knopf unten entscheidet** (User: "momentan geschieht die auswahl
schon, wenn man draufklickt. ich hätte gerne ein auswahl highlight + button. also erst auswählen,
dann wird die entsprechende kachel gehighlightet und dann auf den auswahl button unten drücken").
Gilt für BEIDE Screens; kein einzelner verirrter Klick entscheidet hier noch etwas.

- **`select()` / `confirm()` sind neu, `choose()` bleibt UNVERÄNDERT** — es tut jetzt beides in
  einem Aufruf. Der Klickpfad geht über die zwei Takte, der programmatische Einzelaufruf bedeutet
  weiter genau das, was er bedeutet hat; kein Aufrufer außerhalb der UI musste angefasst werden.
- **Der Bestätigen-Knopf wird ERST GEZEICHNET, wenn etwas gewählt ist** — dieselbe Konvention, die
  die Fußzeile für den Pager schon hat ("kein Chrome für ein Steuer, das nichts tun kann"). Ein
  ausgegrauter Knopf wäre ein zweites Ding zum Erklären. Was die zwei Takte stattdessen beibringt,
  ist die HINWEISZEILE, die sich mitändert ("… selected - press Confirm below, or pick another").
- **Er NENNT die Wahl** ("CONFIRM: ORKS"), weil eine Auswahl das Blättern ÜBERLEBT: sie ist eine
  Antwort, keine Zeigerposition. Ohne den Namen wäre ein Druck von einer anderen Seite aus
  erschreckend statt eindeutig.
- **Die Auswahlfarbe ist ein anderer FARBTON als der Hover, keine hellere Stufe davon.** Hover
  heißt "der Cursor ist hier" und wandert mit der Maus, Auswahl heißt "das ist deine Antwort" und
  bleibt. Zwei Helligkeiten einer Farbe läsen sich als ein Zustand mit zwei Stufen — genau die
  Verwechslung, die hier abgeschafft wird. Dazu ein Wort **SELECTED** in der Kachelecke: Farbe
  allein lässt einem farbenblinden Leser nur die Rahmen-BREITE.
  - **Eine gewählte Kachel reagiert trotzdem auf Hover** (hellerer Grünton) — sonst wäre
    ausgerechnet die Kachel, die man am ehesten noch einmal anklickt, die einzige ohne Rückmeldung.
    **Erst als Fehler bemerkt, weil der eigene Docstring es versprach und der Code es nicht tat** —
    dieselbe Klasse wie ein Kommentar, der ein Verhalten zusagt, das niemand gebaut hat.
- **`draw_footer()` gibt jetzt einen NAMENSSATZ zurück (`FooterButtons`), kein Tupel.** Das alte
  Tupel wurde positionell gelesen UND geschnitten (`ts.draw_footer(...)[1:]` im Kartenscreen) — ein
  vierter Knopf hätte diesem Aufrufer stillschweigend die falschen Rechtecke gegeben, also
  Fehlerklasse 22 in Reinform. `__slots__` und kein `__getitem__`, damit beides nie zurückkommt.
- **ENTER ist die Tastaturhälfte des Knopfes**, keine Abkürzung an Takt eins vorbei: ohne Auswahl
  tut es nichts.
- **Der Bestätigen-Knopf wird VOR den Kacheln getroffen** — dieselbe Begründung, die die Biom-Reihe
  schon trägt: ein Steuer, das nur antwortet, wenn darüber nichts gepasst hat, ist eine Umbaurunde
  davon entfernt, nie mehr zu antworten.
- **`MapSelectScreen(default=)` hatte gar keinen Leser** und öffnet den Screen jetzt auf der SEITE
  der aktuellen Einstellung. **Vorausgewählt wird bewusst nichts:** eine Kachel, die hervorgehoben
  ist, bevor der Spieler etwas angefasst hat, ließe die Hervorhebung "hier bist du" bedeuten statt
  "das ist deine Antwort".
- **Getestet:** `test_map_select.py` 129 → **150/150** (neuer Abschnitt 4b: die drei Zustände einer
  Kachel gegeneinander auf PIXELN, das Badge, der Namenssatz, und alle vier Fußzeilen-Knöpfe
  überschneidungsfrei und im Fenster bei 1280 — inklusive der Prüfung, dass kein echter Karten- oder
  Armeename den Knopf aus dem Fenster schiebt); `test_army_select.py` **253/253**;
  `test_biomes.py` 98 → **100/100** (der Pin "ein Kartenklick wählt eine Karte" maß das COMMIT und
  ist auf die zwei Takte nachgezogen — seine Aussage, dass die Biom-Reihe keine Kachelklicks
  schluckt, ist unverändert). Neu **`ab_pick_then_confirm.py`: 12 A/B-Sonden, alle beißend** — die
  erste stellt buchstäblich das alte Verhalten wieder her (Kachelklick committet), und wenn die
  Suiten das überleben, prüfen sie die Änderung gar nicht.
- **Im ECHTEN Spiel belegt:** `smoke_setup_screens.py` klickt jetzt als ZWEI Klicks auf zwei Frames
  durch `main()`s echte Schleife und prüft beide Hälften einzeln — dass die Auswahl den Screen
  STEHEN lässt und dass beim Druck auf Confirm wirklich schon etwas gewählt war. 13 → **17/17**;
  `--neutralize` weiterhin rot (0/17).

## Vorspiel (Regel 03.01)

`game/pregame.py` ist ein SEQUENZER, keine zweite Platzierungs-Engine — jede Platzierung geht durch
`SetupController.start_setup()` wie Ingress und Disembark auch. Ablauf: Declare Battle Formations
(Transporter füllen, Reserven deklarieren, Support Artillery, 20.01 hart erzwungen) → Roll-off →
abwechselnd aufstellen → zweiter Roll-off (erster Zug) → SCOUTS. **`TurnTracker` bekam `deferred_start=`/`start_battle()`**
statt einer neuen Konstruktionsreihenfolge für ~35 Controller; Battle Round 0 macht Ingress gratis
tot. Beweisbar API-frei (0 Agent-Calls, per Stub-Zähler im Smoke erzwungen).

- **DIE SCHLACHT BEGINNT GENAU EINMAL — `pregame.Resume` erzwingt das Hand-off-Protokoll, statt es
  zu dokumentieren** (User: "der erste zug ging noch nicht los und der gegner spieler 2 hat schon
  36 VP").
  - **Reproduziert im ECHTEN `main()`-Lauf, bevor irgendetwas angefasst wurde:** `_finish_deployment`
    **3×**, `ScoutsStep.start` **3×**, `_begin_battle` **3×**. Das Log des Users zeigt genau das
    (dreimal "deployment complete", dreimal der Erste-Zug-Roll-off, zweimal der ganze
    Schlachtstart-Block) — und weil `main()`s `begin_battle()` Core CP verteilt UND die Primary der
    ersten Command-Phase wertet, sind 2 × 18 = 36 VP vor dem ersten Zug.
  - **EIN Protokoll, ZWEI widersprüchliche Lesarten, beide ausgeliefert.** Jedes Hand-off hier hat
    dieselbe Form: `step.start(self, on_done)`, und der Treiber macht selbst weiter, wenn der Schritt
    "nichts zu tun" antwortet. `enh_solid_image_projection._apply()` schreibt die eine Lesart wörtlich
    aus ("calling on_done AND returning False would run _finish_deployment() twice, and the second run
    would start a second first-turn roll-off"); `test_wraith_constructs.py` PINNT die andere an
    `fated_hero` (on_done gefeuert UND `start()` gibt False). **VIER ausgelieferte Schritte nehmen die
    zweite Lesart** — `fated_hero`, `enh_strike_swiftly`, `prince_of_corsairs` und der terminale Zweig
    von `main.py`s `_RedeployChain` —, und jeder ließ seinen Treiber die Sequenz ZWEIMAL weiterlaufen.
    Fehlerklasse 10 in der Form "ein Vertrag, zwei Lesarten": ein Kommentar in EINEM Modul erreicht den
    nächsten Autor nicht.
  - **Deshalb liegt die Durchsetzung beim TREIBER, nicht beim Schritt.** `Resume` feuert höchstens
    einmal und merkt sich, DASS es gefeuert hat; beide Treiber (`_finish_deployment`s Redeploy-Haken,
    `_run_next_prebattle_step`) und `main.py`s `_RedeployChain` lesen `fired` zusätzlich zum
    Rückgabewert. Damit ist JEDE der zwei Lesarten richtig, und ein fünfter Schritt kann es nicht
    erneut brechen. Die Rückgabewerte der vier Schritte sind bewusst UNANGETASTET — sonst würde
    `test_wraith_constructs.py`s Pin zu Recht rot, für eine Änderung, die nichts kauft.
  - **Die Fortsetzung ist `_deployment_finished`, nicht `_finish_deployment`**: ein Schritt, der
    zurückgibt, hat die Aufstellung nicht ein zweites Mal beendet und darf das nicht protokollieren.
    Der ECHTE zweite Besuch (ein Redeploy, der Einheiten nach `_pending` zurücklegt) kommt weiter über
    `_advance_if_nothing_to_place()` und loggt zu Recht erneut.
  - **`_begin_battle()` ist zusätzlich idempotent** (`state == DONE` → return). Kein Ersatz für den
    Fix, sondern der Backstop für den katastrophalen Ausgang: was zweimal dort ankommt, darf nicht
    zweimal CP und VP auszahlen.
  - **Getestet:** `test_pregame.py` 138 → **149/149** (neuer Abschnitt 9: die ganze Sequenz mit
    Schritten in der gefährlichen Form, plus ein Spion auf `finish_prebattle_abilities` — ohne den ist
    ein doppelt gelaufener Prebattle-Treiber hinter dem `_begin_battle`-Guard UNSICHTBAR, und eine
    Sonde darauf sähe harmlos aus). Neu `ab_pregame_starts_once.py` (**9 A/B-Sonden, alle beißend**);
    die ganze Vor-Fix-Welt kippt 5 von 149, und die erste rote Zeile meldet
    `the battle starts exactly ONCE -- ['Player 1', 'Player 1', 'Player 1']`.
  - **Im ECHTEN Spiel belegt:** `verify_pregame_starts_once.py` fährt `selfplay.py`s echte
    `main()`-Schleife und meldet **1/1/1/1/1** (Aufstellung fertig, Roll-off, Prebattle, Scouts,
    Schlachtstart) und **keine Primary-VP in Runde 1**; `--neutralize` (die volle Vor-Fix-Welt,
    inklusive `main.py`s Kette) meldet **3 Aufstellungs-Abschlüsse, 3 Roll-offs, 3 Scouts-Queues, 2-3
    Schlachtstarts** und Primary-Zahlungen in Runde 1. Nichts wird dafür gestellt — das Vorspiel läuft
    zu jedem Schlachtbeginn von selbst, also der seltene PASSIV messbare Fall.
- **SUPPORT ARTILLERY ist die DRITTE Deklaration des Schritts** (User: "im pre game muss man sich
  entscheiden ob die Support weapons (d-cannons) an einen Guardian Trupp angeschlossen werden
  sollen oder allein stehen. ähnlich wie man im pregame Einheiten in Transporter steckt").
  Gedruckt auf allen drei SUPPORT-WEAPON-Plattformen: *"At the start of the Declare Battle
  Formations step, this model can join one GUARDIAN DEFENDERS unit from your army (a unit cannot
  have more than one SUPPORT WEAPON model joined to it)."*
  - **Die REGEL war fertig, die FRAGE fehlte** — die schon dokumentierte Form, nur eine Ebene
    höher als sonst: 19.01s SUPPORT-Rolle, `can_attach()` und die Paarungstabelle stehen seit dem
    Bau der drei Plattformen, und `can_attach(platform, guardians)` gab die ganze Zeit `[]` zurück.
    Angeboten hat es nichts. Eine `armies/*.json` hätte es über `leaders:` einbacken können — und
    genau das wäre die falsche Zeit: der gedruckte Text stellt die Frage dem SPIELER, im Vorspiel.
  - **`pregame.JOIN` ist die dritte Destination**, und ihr Ziel ist ein SQUAD, wo EMBARKs ein
    Transporter-TOKEN ist. Beide reiten im selben Slot der Deklaration, weil eine Einheit genau
    ein Ziel hat und die zwei per gedrucktem Text exklusiv sind (eine gejointe Einheit darf nicht
    einsteigen).
  - **Aufgelöst wird ZUERST**, vor der Reserven-/Embark-Schleife: der gedruckte Text sagt "at the
    START of the step", und mechanisch ist die GEMERGTE Einheit das, worauf alles danach wirkt —
    eine Plattform an einer reservierten Einheit geht mit in die Reserve, und `_pending` darf sie
    nie als eigenes zu platzierendes Ding führen. Gemessen: Starting Strength 11 → **12**
    ("increases its Starting Strength accordingly"), die Plattform ist aus `army()` und vom Brett,
    und die Guardians werden als EIN Ding aufgestellt.
  - **`game/formations.py` bekommt `support_join_errors()`/`eligible_join_targets()`** — dieselbe
    "eine Definition von legal, zwei Wähler"-Teilung, die dort schon für Transporter und Reserven
    gilt. Die PAARUNG delegiert an `can_attach()` statt sie herzuleiten; alles Zusätzliche ist eine
    Bedingung des Vorspiel-SCHRITTS, von der `can_attach()` nichts wissen soll.
  - **Das ROLLEN-Tor ist tragend, und die eigene Sonde hat das gezeigt:** ohne es bekäme ein
    FARSEER einen "Join"-Knopf, denn `can_attach(farseer, guardians)` ist völlig legal (zur
    Listenbau-Zeit). Erst der Test mit einem Leader lässt die Sonde beißen — vorher meldete sie
    NO BITE, was ein Befund über den Test war und keine Entwarnung.
  - **"Deploy on the battlefield" IST die Allein-stehen-Antwort**, es braucht also keinen eigenen
    Default. Und die KI antwortet weiter mit genau dieser: der Join ist optional und sein Handel
    geht in beide Richtungen (er kauft der Plattform einen Schirm aus Guardian-Körpern und drückt
    sie zugleich auf Toughness 3, ihre eigene Support-Weapon-Regel), es gibt per stehender Vorgabe
    keinen Aeldari-KI-Pfad, und der Default ist eine legale Antwort statt eines Hängers. NAMENTLICH
    in `ai/deployment_ai.py` festgehalten, damit es nicht wie ein Versehen aussieht.
- **ZWEITER, ECHTER FEHLER, beim Lesen desselben gedruckten Absatzes gefunden: der Transport-Bann
  galt bei 18.01 nicht.** *"This model, and any unit it is joined to, cannot embark within a
  TRANSPORT."* `TransportController.can_embark()` erzwingt das seit dem Bau der Plattformen —
  `game/formations.py`s `embark_errors()` nicht. Reproduziert: `embark_errors(D-cannon, Wave
  Serpent)` gab `[]`, und `eligible_transports()` bot den Wave Serpent an; der Vorspiel-Screen
  hätte die Plattform also eingeladen, und erst die Mitten-im-Spiel-Regel hätte je widersprochen.
  EIN Satz, ZWEI Leser, nur einer antwortete. Beide Hälften sind jetzt da, inklusive der zweiten
  ("and any unit it is joined to"), die nur im FENSTER zwischen den zwei Deklarationen existiert —
  danach trägt die gemergte Einheit das Modell selbst und derselbe Pro-Modell-Test beantwortet sie.
- **`can_attach()` sagt einem SUPPORT-Trupp jetzt "join", nicht "lead".** Die Meldung wurde an dem
  Tag spielersichtbar, an dem es das Angebot gab — sie ist der Grund, warum eine Einheit NICHT auf
  der Liste steht.
- **INFILTRATORS (24.20) ist kein eigener Schritt**, sondern ein anderes `position_valid`-Prädikat
  während des normalen Aufstellzugs — und wird deshalb ZULETZT sortiert (früh platziert gewinnt es
  nichts). Distanz 8" (User-bestätigt).
- **Die Aufstellungs-Overlay malt den Modell-Überlappungs-Term NICHT** (User: "ich finde es sinnlos
  bei der aufstellung. ich sehe ja, wenn sich modelle überlappen"). `PregameController.
  overlay_position_valid()` ist das volle Prädikat minus genau diesem einen Term — dem einzigen, den
  man mit eigenen Augen vom Brett ablesen kann, weil dort eine Base gezeichnet steht. Alles Übrige
  bleibt, weil es UNSICHTBARE Information ist: Zonenkante (03.01), Dense-Gelände (13.05),
  Brettkante, die 8"-INFILTRATORS-Blasen (24.20). Gemessen auf map2 mit 32 bereits aufgestellten
  Modellen: **230 → 132 sq.in rot** in der eigenen Zone (31.9% → 18.3%), 98 sq.in verschwinden.
  **Aus dem echten Prädikat NICHT entfernt** — die Regel wird weiter doppelt erzwungen
  (`clamp_drag()`/`apply_group_drag()` rutschen an die Grenze, `confirm_setup()` prüft
  `check_model_overlap()`), was hier verborgen wird, kann also nicht COMMITTET werden. Damit ist die
  gemalte Fläche etwas GRÖSSER als die legale, und diese Richtung ist die sichere: ein Zug dort
  hinein stoppt, und der Grund steht sichtbar davor. Nur die Aufstellung — Ingress (20.04) und
  Disembark (18.04/18.05) behalten das volle Bild, weil dort ein an eine fremde Base verlorener Platz
  weder offensichtlich noch billig ist (ein gescheiterter Emergency Disembark tötet die Einheit).
  Die KI ist unberührt: `deployment_ai` ruft `pregame_ctrl.position_valid()` direkt, nicht über den
  Overlay-Pfad. Getestet in `test_pregame.py` (Abschnitt 6b/6c, **125/125**), A/B in beide Richtungen
  (Relaxation an der Quelle zurückgebaut → 2 rot; `main.py`s Zweig entfernt → 2 rot).
- **SCOUTS (24.31/24.32)** in allen drei Zweigen; der DEDICATED-TRANSPORT-Zweig ist als WÄCHTER gebaut
  (gibt `[]` plus eine Logzeile, welche Vorbedingung fehlte) statt spekulativ.
- **KI-Formationen sind deterministisch**: DEEP STRIKE zieht in die Reserve (in PUNKTEN gerechnet,
  nicht als flacher Bonus — der erste Versuch war ein Skalierungsfehler), Transporter füllen nach
  einer expliziten Prioritätstabelle je Transportertyp (`TRANSPORT_PASSENGER_PRIORITY`, erschöpfend;
  Gretchin stehen zusätzlich auf `TRANSPORT_NEVER_EMBARK`).
- **KI-Aufstellung misst Exposition gegen die gegnerische ZONE**, nicht gegen Modelle (beim
  abwechselnden Aufstellen steht der Gegner nur teilweise). Rollenabhängiger Scorer (key/screen/
  shooter/heavy/assault) plus ein HIDDEN-Term (13.09): die ganze EINHEIT muss verdeckt sein, also
  wird der PACKER auf Dense-Areas eingeschränkt, statt nur den Abwurfpunkt zu bewerten. Gemessen
  2/9 → 9/9 (map1) bzw. 7/9 (map2) vollständig verdeckte Einheiten, Preis ~1.3" Vormarsch.
- **`assault` ist die fünfte Rolle und nimmt nur Einheiten, die sonst ein `screen` wären.** User:
  "die skorpekh destroyer standen sehr weit hinten und sind nicht durch die warrior durchgekommen
  ... nahkämpfer sollten eher weiter vorne starten, aber möglichst versteckt." Der SCORER war nie
  das Problem — ein Screen-Schlüssel beginnt bereits mit `-forward_bucket`. Falsch waren die
  WARTESCHLANGE (nach `-len(models)` sortiert, also wählte ein 3-Modell-Elitetrupp aus dem, was ein
  21-Modell-Blob übrig ließ) und der HIDDEN-PASS, den `_wants_hidden_pass()` einem Screen
  vorenthält. Gemessen auf der gemeldeten Aufstellung: Skorpekh **−3.04" → +0.97" vorwärts und
  1/3 → 3/3 verdeckt** (map1: −2.04" → +3.98", 0/3 → 3/3), Canoptek Wraiths und Lychguard
  0/6 → 6/6.
  - **Der Preis ist benannt:** die großen Fernkampf-Blobs verlieren die Dense-Fläche an die
    Nahkämpfer (Necron-Armee 32/59 → 20/59 verdeckte Modelle auf map1). Die MITTLERE Exposition
    bleibt praktisch gleich (0.0 → 0.2), es geht also der 13.09-Schutz verloren, nicht die Deckung
    — und der Shooter-Scorer wählt dann eine Schusslinie (Exposition 3 von 33, innerhalb
    `SHOOTER_IDEAL_EXPOSURE`), was seine Aufgabe ist. Bei den Orks geht es umgekehrt aus
    (30/79 → 38/79). Der Vormarsch-Mittelwert der Armee steigt leicht auf 3 von 4 Szenarien.
  - **Der Rollen-Test ist derselbe wie bei der Charge-Sperre** (`combat_focus.is_assault_unit()`),
    aber bewusst die STRENGE Fassung statt "lehnt nach Nahkampf": Gretchin lehnen auch nach Nahkampf
    (0.97) und sind genau der billige Screen, den der frühere Report auf dem Home Objective haben
    will. Band 0.16..0.97, Schwelle 1/1.4 = 0.71.
  - **Nebenbefund:** `_hidden_pass_points()`s Vorwärts-Bucket-Einschränkung nannte `"screen"` und
    war damit UNERREICHBAR (`_wants_hidden_pass()` schließt Screens vorher aus). Die Messung dahinter
    wurde gemacht, das Ergebnis behalten — und der Code, der es trug, blieb beim nächsten Umbau
    stehen. `assault` ist die Rolle, die diesen Handel wirklich will; damit lebt der Fund wieder.
