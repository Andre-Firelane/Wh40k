# Karten und Gelände

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Karten und Szene

Vier Karten (`game/maps.py`), Auswahl über `config.MAP` (steht auf `map2`) oder `python main.py --map 1`.
Ein `BattleMap` trägt Brettmaße, Deployment-Zonen, Terrain+Objectives, optional ein `roster` (welche
Einheiten diese Karte fieldet) und die handgesetzten Alt-Positionen. Die Armeelisten selbst liegen
in `armies/*.json` (die Zeile sagte bis 2026-09-07 `main.py` und war schon lange davor falsch —
sie waren zwischendurch in `game/army_lists.py`). `maps.apply_to_config()` schreibt die Brettmaße einmalig beim Start in `config` (~24
Stellen lesen sie zur Laufzeit; kein `from game.config import` im Repo — geprüft).

- **map1** — 44"×60" Hochformat, Terrain nach dem offiziellen "Take Cover"-Layout, per Pixelvermessung
  der Bilddatei nachgebaut. 43 Features (28 sichtblockierend), 5 Objectives.
- **map2** — 60"×44" Querformat, aus `map2 layout.png` gemessen (20 px/Zoll, Zonen je 12" tief,
  180°-Rotationssymmetrie, also Nord/West gemessen und Süd/Ost gespiegelt). **Schräge Footprints
  werden BEGRADIGT gebaut** (User-Vorgabe), jedes an der Achse, an der seine Längsseite ohnehin näher
  lag, bei gemessener Mitte und Größe. 35 Features (20 sichtblockierend), 1.17 ms je Sichtlinienprüfung
  gegen map1s 1.36 ms.
- **map3 — "Crucible", 60"×44" Querformat mit ECKAUFSTELLUNG**, gebaut aus dem vom User gelieferten
  `Sprites/Map3.png` (2400×1760 px = exakt 40 px/Zoll). **Es ersetzt das alte 30"×30"-Testbrett**
  (User: "map3 ersetzen"); was daran hing, steht unten. 18 Footprints (9 gemessen, 9 gespiegelt),
  36 Features, 6 Objectives, 1.7 ms je Sichtlinienprüfung.
  - **Die Zonen sind QUADRANTEN MINUS EINER 9"-KREISSCHEIBE um die Brettmitte** — die erste Karte,
    deren Zonen gar keine Rechtecke sind, und der Grund, warum die Formen-Arbeit zuerst kam. Der
    Radius ist gemessen: 355 px in BEIDEN Zonen unabhängig, also 8.88" gegen die im Bild
    annotierten 9"; die Differenz ist die Strichbreite der gestrichelten Linie.
  - **Das Loch ist der Punkt der Karte:** die zwei mittleren Objectives stehen je in einem
    Quadranten, der sonst jemandem gehört, liegen aber IM Loch — und damit im Niemandsland.
  - **Und sie liegen jetzt GANZ darin** (User: "die beiden mittleren objectives ragen in die
    austellungszonen hinein. das ist schlecht für manche Missionen, die als Bedingung 'outside of
    your deployment zone' haben"). Gemessen vor der Änderung: **15.3 % der Fläche jedes der beiden
    Stücke lagen in einer Aufstellungszone**, die ferne Ecke 12.01" von der Brettmitte gegen die
    9" des Lochs. Eine Einheit konnte das mittlere Objective halten und dabei in der eigenen Zone
    stehen — genau das, was diese Missionen verbieten.
    - **Der Zeile, die es hätte fangen müssen, fehlte die FLÄCHE.** map3s Suite prüfte schon, dass
      die zwei Niemandsland sind — aber am MITTELPUNKT des Objectives, und der lag immer im Loch.
      Worauf eine Einheit steht und was 14.02 misst, ist die Fläche.
    - **1.2" ZUR BRETTMITTE GESCHOBEN und auf Skala 0.675 gebracht** → Mitte (34.72, 20.57),
      5.05 × 7.32. **Schrumpfen allein reichte nicht und war zu brutal**: die erste Fassung ließ die
      Mitte stehen und kam damit auf 0.481 (ein Viertel der Fläche), was der User zu Recht
      zurückwies ("die objectives sind jetzt sehr klein. die können gerne wieder etwas größer
      sein"). Der Grund ist die LAGE, nicht die Größe: das Stück steht 6.13" vom Mittelpunkt eines
      9"-Kreises entfernt, seine ferne Ecke liegt bei gemessener Breite **allein in X schon 9.61"
      draußen**, und — gemessen — schafft bei DIESER Mitte kein Seitenverhältnis mehr als ~21 sq.in,
      weil die bindende Ecke von BEIDEN Kanten zugleich hinausgeschoben wird. Platz muss aus der
      Position kommen.
    - **Warum 1.2" und nicht mehr: der KORRIDOR** (User: "es soll aber noch ein corridor zwischen
      den objectives bleiben"). Weiter hineinschieben kauft schnell Größe — 2.0" erlaubte 80 % des
      gemessenen Stücks —, schließt aber die Gasse zwischen dem Paar; bei 3.0" überlappen sie
      einander. **Die Gasse der KUNST ist 4.26" breit, und das ist die Zahl, die gehalten wird:**
      1.2" hinein lässt 4.39", weiterhin breiter als die 4.2"-Base eines Falcon oder Wave Serpent,
      also des breitesten Dings, das da durchfahren muss. Damit ist der Korridor die Schranke, die
      die Größe deckelt — nicht das Loch.
    - **Ergebnis: doppelte Fläche gegenüber der Nur-Schrumpf-Fassung, 68 % des gemessenen Stücks**,
      Fläche 8.85" und gezeichneter Ring 8.97" (beide im 9"-Loch), keine Überlappung mit anderem
      Gelände, Seitenverhältnis 1.4495 gegen gemessene 1.4505.
    - **Der Ring ist der Grund für 0.675 statt eines Hauchs mehr**: `objective_outline_points()`
      wächst um 5 BILDSCHIRM-Pixel, bei Spielzoom 0.08". Eine Fassung, deren Fläche frei ist und
      deren Ring den Bogen kreuzt, hätte ungefixt AUSGESEHEN. **Auf der Kartenvorschau (~17 px/Zoll)
      kann der Ring den Bogen weiter berühren** — das ist die feste Pixelbreite der Dekoration,
      nicht das Objective, und deshalb benannt statt weiterverfolgt.
    - **Das Paar bleibt spiegelbildlich**, also weiter exakt gleich weit von der Brettmitte — was
      beide erst zu „zentralen" Objectives für Secure Asset und Unstoppable Force macht.
    - **Es ist außerdem die ehrlichere Größe für das, was die Kunst zeichnet:** diese zwei sind
      KEILE, per aufrechtem Rechteck angenähert, und ein Keil füllt sein Rechteck zu zwei Dritteln
      (unten gemessen) — ein Rechteck, das aus dem Loch ragt, ist zum Teil die Näherung, die
      herausragt. 0.675 liegt genau in dieser Größenordnung.
    - **Eine gemessene Brettzahl ist mitgewandert und ist nachgezogen statt gepinnt geblieben:**
      `observation.garrison_reach_needed_in()` liest den Abstand vom Home Objective zum NÄCHSTEN
      anderen — und das nächste ist eines dieser beiden. map3 geht damit von 15.9" auf **16.8"**
      (in `test_map3_crucible.py` und `test_home_garrison.py`). Die Aussage, für die die Zahl
      steht, bleibt: eine 12"-Waffe kann das Home Objective weiterhin nicht sinnvoll halten, und
      genau das prüft die Zeile jetzt zusätzlich, statt nur die Zahl festzuhalten.
    - **Die Invariante ist jetzt KARTENÜBERGREIFEND gepinnt** (`test_deployment_shapes.py`
      Abschnitt 9): ein Objective ist entweder HOME (ganz in der Zone seines Besitzers, per Design)
      oder Niemandsland (ganz außerhalb BEIDER Zonen) — nichts steht mit einem Bein drin. map1 und
      map2 erfüllten das schon, map3 war der einzige Verstoß; eine vierte Karte erbt die Prüfung
      gratis. **A/B belegt:** mit der gemessenen Größe zurück fallen beide Suiten und nennen die
      Zahlen des Berichts wörtlich (15.5 % der Fläche, ferne Ecke 12.01"). Der KORRIDOR ist
      zusätzlich gepinnt (map3s Suite), gegen die 4.26" der Kunst UND gegen die 4.2"-Grav-Panzer-
      Base — sonst wäre „größer machen" beim nächsten Mal wieder eine Einladung, die Gasse
      zuzuschieben.
    - **Nebenbefund, und ein hübscher:** `test_primary_missions.py` pinnte, dass map3s zwei
      Mittel-Objectives BIT-IDENTISCH gleich weit von der Brettmitte stehen, mit dem Vermerk, die
      0.001"-Toleranz von `central_objectives()` sei auf den ausgelieferten Karten „nachweislich
      INERT ... nur das Netz für eine künftige Karte, deren Spiegelung durch andere Arithmetik
      läuft". **map3 ist diese Karte geworden:** die kleineren Stücke verschieben die Wände, aus
      denen der Mittelpunkt gemittelt wird, und das Spiegelpaar liegt jetzt ~7e-15 auseinander —
      dieselbe Größenordnung, die schon einmal aus einem Rechteck ein Fünfeck gemacht hat. Die
      Prüfung fragt jetzt die Toleranz, die die Regel selbst benutzt, und zusätzlich, dass wirklich
      noch BEIDE als zentral zurückkommen.
  - **Vier der achtzehn Stücke stehen schräg** (37.1° und −52.5°, je ein Spiegelpaar) und werden
    AUCH SO gebaut. Die Begradigung, die map2 nötig hatte, ist kein Preis mehr.
  - **GEDREHT wird nur, was wirklich ein gedrehtes Rechteck IST**, und das ist eine
    User-Korrektur: die erste Messung gab jedem Stück sein MINIMALFLÄCHEN-Rechteck, was bei den
    zwei keilförmigen Mittelstücken einen langen schmalen Block DIAGONAL durch den Keil legte
    (57°) — das engste Rechteck um die Form, aber nicht die Form, als die man sie liest. Der User
    hat die richtigen Lagen als rote Rechtecke ins Bild gezeichnet, alle aufrecht. Unterschieden
    wird jetzt an der FÜLLUNG: ein echtes gedrehtes Rechteck füllt sein Minimalflächen-Rechteck
    (gemessen 102-103%), ein Keil zu zwei Dritteln (66%) — dort gewinnt das aufrechte Rechteck.
    **Gegenprobe: die Objective-Marker der Vorlage liegen bei (36.02, 20.16); die aufrechte
    Fassung trifft (35.87, 20.22), die diagonale lag 1.8" daneben.**
  - **Eine ganze Stückgruppe hatte die erste Messung ÜBERSEHEN** — die grünen Container sind ohne
    graue Grundfläche gezeichnet, und die Maske nahm nur Grau. Sie nimmt jetzt Grün und Gold als
    eigenständiges Terrain.
  - **Jedes Footprint ist EIN sauberes Rechteck** (User: "ignoriere unregelmäßigkeiten wie schutt.
    mache saubere rechtecke draus. und alle footprints sollen rechtecke sein"). Die Vorlage zeichnet
    unregelmäßigen Schutt über die Kanten hinaus; die Messung legt das Rechteck auf das Stück und
    verwirft den Überstand. **Deckungsprobe gegen die Bilddatei: 92% des gezeichneten Terrains
    abgedeckt, 87% der gebauten Fläche liegt auf gezeichnetem Terrain** — die Differenz IST der
    verworfene Schutt.
  - **BERÜHRENDE STÜCKE werden auch gebaut, wie sie sich berühren — die einzige Stelle, an der
    eine Koordinate hier NICHT die rohe Messung ist** (User: "bei map 3 gibt es kleine lücken,
    durch die man durchschießen kann zwischen den geländestücken ... schiebe sie so zusammen,
    dass da keine lücken sind, wenn geländestücke sich berühren sollten"). **Der Perzentil-Fit
    IST die Ursache**: er trimmt an JEDEM Stück eines berührenden Paares eine Scheibe ab, also
    wurde aus einer gezeichnet geschlossenen Naht ein Schlitz von bis zu 0.43".
    - **WELCHE Paare sich berühren, ist an der Vorlage GEMESSEN, nicht angenommen**: die
      gezeichneten Stücke der vier betroffenen Paare kommen sich auf **0.05–0.15"** nahe (die
      Breite der Trennlinie), während das eine Paar, das genauso aussieht und NICHT berührt
      (Quer-Bar gegen die −52.5°-Barrikade), im Bild **2.35"** auseinandersteht und offen
      bleibt. Ohne diese Gegenprobe bestünde die Zusicherung auch auf einem Brett, das alles zu
      einem Klumpen schiebt.
    - **Verschoben wird, nie vergrößert, und nur Barrikaden bzw. mauerlose Trümmer** — kein
      objective-tragendes Stück bewegt sich, also stehen alle sechs Objectives unverändert da,
      wo sie gemessen wurden. Drei Stücke der Mittellinie stehen in EINER REIHE: das mittlere
      behält seine Messung, die zwei äußeren kommen zu ihm — die einzige Zuteilung, die beide
      Nähte gleichzeitig schließt, und die mit der geringsten Bewegung.
    - **Nur EINE der vier Lücken war wirklich eine Schusslinie**, und das ist die Trennung, die
      man hier nicht übersehen darf: die anderen drei betreffen eine Barrikade, und eine
      Barrikade ist LIGHT und hat Sicht noch nie blockiert. Das Paar an der Mittellinie sind
      dagegen zwei RUINEN, deren WÄNDE 0.15" auseinander und einander zugewandt standen — ein
      Schlitz, den eine Sichtlinie einfädelt. **Durch die echte `line_of_sight`-Kette gemessen:
      21 senkrechte Schüsse quer durch den alten Schlitz, vorher 4 von 21 geblockt, nachher
      21 von 21.**
    - **Getestet:** `test_map3_crucible.py` Abschnitt 7 (101 → **109/109**) — kein Paar liegt
      zwischen 0 und 1" voneinander (entweder bündig oder klar getrennt), acht exakte Kontakte
      (vier plus Spiegel), das offene Paar bleibt offen, die Wände berühren sich, und die
      Sichtlinie ist zu (mit Gegenprobe auf offenem Boden, sonst bestünde die Zeile auch auf
      einem Brett, das alles blockt). **A/B an der QUELLE** (alle vier Paare zurück auf die rohe
      Messung): **105/109**, und die erste rote Zeile nennt alle acht Schlitze mit ihrer Breite.
  - **180°-punktsymmetrisch wie map1 und map2**, also ist nur die Nordwest-Hälfte gemessen. Vor dem
    Schreiben geprüft: jedes gemessene Stück findet sein Spiegelbild auf 0.1" und 1.4°.
  - **Player 2 behält die LOW-Y-Ecke**, wie auf beiden anderen Karten, damit nichts sonst in der
    Szene wissen muss, welche Karte läuft. Die Vorlage tönt diese Ecke blau und die Engine zeichnet
    Player 1 blau — die gerenderten Farben stehen also andersherum als im Bild. Das ist eine
    Palette, kein Layout.
  - **Sie fieldet die ganze Armee**, wie map1 und map2. Damit hat `BattleMap.army_roster` KEINEN
    Nutzer mehr; der Mechanismus bleibt (ein Dict je Liste, `"{p}"` als Platzhalter für die
    Owner-Ziffer, aufgelöst in `roster_for(armies)`) und wird in `test_army_select.py` an einer
    eigens gebauten Karte geprüft statt an einer ausgelieferten.

- **map4 — "Sundered", 60"×44" Querformat mit DIAGONALEN Aufstellungszonen**, gebaut aus dem vom
  User gelieferten `Sprites/map4.png` (2400×1760 px = exakt 40 px/Zoll, dieselbe Skala wie map3).
  15 Footprints (8 gemessen, 7 gespiegelt), 31 Features, **5 Objectives**.
  - **Die Zonen sind DREIECKE hinter zwei PARALLELEN Diagonalen** (User: "schräge deployment
    zones"). map3s Zonen sind Quadranten mit einem Loch; hier ist der offene Boden ein BAND
    KONSTANTER BREITE von Ecke zu Ecke, kein Keil. Jede Zone ist ein Viertel des Bretts.
  - **Die Kanten sind die KONSTRUKTION, nicht die Annotation.** Gemessen an den getönten Pixeln:
    die zwei Kanten sind auf **0.0008°** parallel, und die pinke läuft durch (0.094, 0) und
    (30.039, 44) — eine Brettecke und den MITTELPUNKT der gegenüberliegenden Längskante, auf 0.09"
    bzw. 0.04". Jedes andere Stück spiegelt auf 0.03–0.13", also ist das Zehntelzoll die Zeichnung
    und nicht der Entwurf. Gebaut wird exakt (0,0)–(30,44) und der 180°-Spiegel (30,0)–(60,44).
  - **Die "24.25""-Beschriftung im Bild ist KEINE Messung, und das ist geprüft statt angenommen.**
    Die Konstruktion lässt 44·30/√(30²+44²) = **24.787"** offen, 0.54" mehr als das Label sagt.
    Das weiße Lineal, auf dem das Label sitzt, ist nur **15.05"** lang und seine Endpunkte stehen
    **5.06"** bzw. **4.52"** von den zwei gestrichelten Linien entfernt — es überspannt KEINE von
    beiden. **map3s Präzedenzfall trägt hier NICHT** (dort ist die Annotation die runde Zahl und
    die Messung weicht um die Strichbreite ab): eine Strichbreite macht die Lücke GRÖSSER, nicht
    kleiner. Die Konstruktion gewinnt, die 0.54" sind benannt statt in die Koordinaten gefälscht.
  - **Die Territoriumsgrenze ist die Parallele in der Mitte** (User: "die territory grenze ist eine
    parallele zu den deplyment zones in der mitte zwischen ihnen") — das ist eine Änderung an der
    REGEL, nicht eine Zahl in dieser Datei; siehe `### Territorien` oben. Über 401×401 Punkte
    **0 Abweichungen** von der Ideallinie (15,0)–(45,44).
  - **Der WINKEL-SIGN ist gemessen, nicht angenommen:** das NW-Ruinen-Footprint als echtes
    `Obstacle` bei **+55°** deckt **92.1%** der gezeichneten Pixel, bei −55° nur **62.0%**. Also
    ist `angle_deg` der Bildraum-Winkel ohne Vorzeichenwechsel. **Acht der fünfzehn Stücke stehen
    schräg** (6× 55°, 2× 63°) — mehr als auf jeder anderen Karte.
  - **Deckung gegen die Bilddatei, am GEBAUTEN Brett gemessen:** 92.3% des gezeichneten Terrains
    liegt in einem Footprint, und jedes Footprint liegt zu 84–99% auf gezeichnetem Terrain. Die
    Differenz IST der verworfene Schutt.
  - **Das MITTELSTÜCK steht exakt auf der Brettmitte und ist sein eigener Spiegel**, wird also
    EINMAL gebaut. Es behält `ruin()`s Vier-Seiten-Layout statt `l_walls()`' L — derselbe Grund wie
    bei map1 und map2: keine Seite eines Stücks AUF der Brettmitte "zeigt zum Feind", und
    `l_walls()` fiele auf eine willkürliche Ecke zurück. Gebaut werden nur **zwei diagonal
    gegenüberliegende** Ecken-Ls, damit auch die WÄNDE punktsymmetrisch bleiben — und WELCHE zwei
    ist hier gemessen statt Geschmack: `"sw"` zeigt zu Player 1s Dreieck, `"ne"` zu Player 2s.
  - **BERÜHRENDE STÜCKE werden gebaut, wie sie sich berühren** — dieselbe Perzentil-Fit-Ursache wie
    bei map3. Zwei Nähte plus Spiegel, alle vier bündig auf **0.000"**; verschoben werden nur
    BARRIKADEN, kein objective-tragendes Stück bewegt sich. Die Kontrolle: das nächste NICHT
    berührende Paar steht in der Kunst 1.30" und am gebauten Brett **1.876"** auseinander und
    bleibt offen.
  - **BENANNTER UNTERSCHIED ZU MAP3: keine dieser Nähte war ein Schuss-Schlitz.** Bei map3 standen
    zwei RUINEN-Wände 0.15" auseinander und einander zugewandt; hier hat jede Naht eine Barrikade
    auf mindestens einer Seite, und eine Barrikade ist LIGHT und hat Sicht noch nie blockiert. Das
    Schließen ist rein optisch, und das steht ausdrücklich da, damit der nächste Leser nicht
    annimmt, map4 habe map3s Sichtlinien-Fix geerbt.
  - **Die OST-Container ist die WEST-Container gespiegelt, und das ist eine Entscheidung:**
    unabhängig gefittet kamen die zwei 0.93" verschieden lang und 4° verdreht heraus. Beide Flanken
    nebeneinander gerendert (eine um 180° gedreht) zeigte warum — eine dünne schwarze Maßhilfslinie
    durchtrennt die Spitze der Ost-Container, und die Farbmaske schließt sie aus. Die
    VOLLSTÄNDIGE wird gemessen und gespiegelt. Ihre Deckungszahl (84.2% gegen 92.2% der West-Seite)
    ist genau dieser Befund, im gebauten Brett sichtbar.
  - **Der Seam-Fit der Diagonal-Stapel ist am PROFIL gemessen, nicht geraten:** brauner Slab und
    grüne Container lasen sich als EINE Maskenkomponente, und die Breiten-Profillinie entlang der
    55°-Achse zeigt einen sauberen Sprung von ~1.9" auf 3.64" bei u=7.50". (Ein Erosions-Sweep
    trennt sie auch, setzt die Naht aber dorthin, wo die Erosion zufällig durchbricht — ein
    Artefakt des Sweeps, keine Messung der Kunst.)
  - **`garrison_reach_needed_in()` liest hier 24.2"** — die längste der vier Karten. Das Band stellt
    ein Home Objective weiter von allem anderen ab als jedes andere Layout, eine Home-Garnison kann
    dort also gar nicht auf Reichweite beitragen. Die Zahl wird vom Brett ABGELESEN, nicht gesetzt.
  - **Die PAGINIERUNG der Kartenauswahl wird damit zum ersten Mal scharf**: vier Kacheln passen
    erst ab 1920 px nebeneinander (bei 1600 px drei, bei 1280 px zwei). Dieselbe Maschinerie, die
    beim fünften Armee-Eintrag im Armee-Screen scharf wurde — hier war sie bis dahin nur gegen eine
    künstliche Registry gemessen. `test_map_select.py` prüft deshalb jetzt "eine Kachel je Karte
    AUF DIESER SEITE" plus "jede Karte ist durch Blättern erreichbar" statt einer festen Drei.
  - **Der NAME ist kurz, und das ist eine Schranke statt Geschmack:** der Confirm-Knopf liest
    `CONFIRM: <Name>` und muss in ein 1280-px-Fenster passen. "Sundered (60"x44", diagonal
    deployment)" lief 3 px über die Fußzeilen-Luft; "diagonal" allein sagt dasselbe und passt zu
    map1s "portrait".
  - **Player 2 behält die LOW-Y-Ecke**, wie auf allen drei anderen Karten. Sie fieldet die ganze
    Armee, hat keine handgesetzten Alt-Positionen (nur 03.01s Vorspiel) und ist NICHT der Default.
  - **Getestet:** neu `test_map4_sundered.py` (**131/131**, acht Abschnitte) plus neu
    `ab_map4_sundered.py` (**17 A/B-Sonden, alle beißend, keine stürzt ab**). Zehn Cross-Map-Suiten
    haben map4 dazubekommen; `test_deployment_shapes.py` §9 ("eine vierte Karte erbt die Prüfung
    gratis") ist genau dafür geschrieben worden und hält: Home-Objectives zu **100%** in ihrer
    eigenen Zone, Niemandsland-Objectives zu **0%** in einer. `test_rotated_terrain.py`s
    map3-Sonderfall ist zu einer benannten Menge `ROTATED_MAPS` geworden.
  - **Eigener Sondenfehler, zwanzigste Instanz derselben Lehre:** zwei Sonden ließen die neue Suite
    ABSTÜRZEN statt sie rot zu machen (`min()` über eine leere Folge, `next()` ohne Default). Die
    Suite geht jetzt über `first()`/`safe_min()`, und der Sonden-Treiber MELDET einen Absturz als
    eigenen Ausgang, damit er nicht als Biss durchgeht.

**Was mit dem alten Testbrett verloren ging — und wohin es umgezogen ist.** Das 30"×30"-Brett war
kein nachgebautes Layout, sondern die gemeldeten Fehlergeometrien nebeneinander (3"-Korridor, nur
zur eigenen Kante offene Bucht, 5"-Tür, 7.2" offene Flanke) plus ein Zug in Sekunden. Drei
Suiten hingen an EIGENSCHAFTEN dieses Bretts, die die neue Karte nicht hat; alle drei sind
SYNTHETISCH neu gebaut statt gestrichen, damit die Abdeckung nicht an einer Karte hängt:
`test_home_garrison.py` (die einzige Karte, auf der beide Spieler VERSCHIEDENE Reichweite
brauchten — genau der Fall, den eine feste Zahl still verfehlt hätte), `test_secondary_missions.py`
(der Dedupe-Fall von `expansion_objectives()`, weil nur ein Nicht-Home-Objective existierte) und
`test_army_select.py` (der Roster-Mechanismus). Was wirklich weg ist: das schnelle kleine
Selbstspiel-Brett.

**Warum map2 begradigt wurde (historisch — seit Stufe 2 nicht mehr nötig):** ein `Obstacle` war
konstruktionsbedingt achsparallel, und
Sichtlinie, Bewegungs-Clamp, A*-Gitter, Platzierungs-Overlay und Renderer lesen `min_x/max_x/...` als
die FORM selbst. Die einzige Stelle mit echtem Umbaubedarf wäre `_route_around_waypoints()`, deren
Korrektheitsargument wörtlich auf Achsparallelität beruht. Eine Treppen-Approximation war gebaut und
getestet, kostete aber 105 Features gegen 35 und ~25% Mehrfläche — wieder ausgebaut.

### Objective-Namen

**Sprechend, und die Himmelsrichtungen sind gegen die gemessene Mitte geprüft** (User: "Dafür
brauchen die Objectives auch sinnvolle Namen, wie z. B. HomeObjective oder CentralObjective oder
Objective East, West oder Northeast"). Aus `No Man's Land (NE/SW/W/E)` wurde
`Objective Northeast/Southwest/West/East`; `Central Objective` und `P1/P2 Home Objective` waren schon
brauchbar und bleiben — bei zwei Home-Objectives ist die Spielerziffer das, was sie unterscheidet.
Der Anlass war Burden of Trust: sein Prompt NENNT das Objective, und "No Man's Land (W)" ist als
Frage an einen Spieler unbrauchbar. Ein Test prüft für jede Karte, dass ein Name mit
Himmelsrichtung auch wirklich auf dieser Seite der Brettmitte liegt, und dass "Central" das der
Mitte nächste ist — ein falsch zeigender Name wäre schlimmer als der alte.

**Die Umbenennung ist gefahrlos, weil nichts nach Namen SUCHT**: No Man's Land wird geometrisch
bestimmt (Mitte in keiner Aufstellungszone), Home ebenso. In `ai/` stehen die alten Namen nur in
Kommentaren und Beispieltexten.

## Terrain darf sich DREHEN (game/terrain.py, Stufe 2)

`Obstacle` nimmt jetzt `angle_deg`. Damit ist die Begradigungs-Entscheidung von map2 aufgehoben
— sie bleibt für map2 selbst bestehen (die Karte ist so vermessen und getestet), aber eine neue
Karte kann ihre Footprints tragen, wie sie gedruckt sind.

**Zwei Regeln machen das an einer Form sicher, die sechs Subsysteme lesen:**

1. **`min_x/max_x/min_y/max_y` sind die BOUNDING BOX des gedrehten Rechtecks**, nicht mehr die
   Form. Jeder VORFILTER (`line_of_sight._obstacle_relevant`, der A*-Reject) bleibt damit ohne
   jede Änderung korrekt, und alles, was den exakten Test noch nicht kennt, blockiert bloß etwas
   zu viel statt Unsinn zu antworten. Die Umstellung konnte also nicht auf halbem Weg brechen.
2. **Jede EXAKTE Frage beantwortet eine Methode am Hindernis**, im Eigenframe: `overlaps_circle`,
   `contains_point(inflate=)`, `blocks_segment`, `segment_clip`, `segment_entry_fraction`,
   `distance_to_point`, `corners`, `route_waypoints`. Aufrufer fragen das Hindernis, statt vier
   Zahlen an eine freie Funktion zu reichen — EINE Definition von „welche Form ist das" statt
   sechs. `segment_intersects_rect` hat im Produktivcode keinen Aufrufer mehr.

**`angle_deg=0.0` nimmt einen Fast Path, der die ALTE ARITHMETIK WÖRTLICH ist** — nicht die
allgemeine Formel spezialisiert. Das ist die Lehre aus Stufe 1: die beiden sind in exakter
Arithmetik gleich und runden am Rand verschieden, und genau daran ist dort ein ganzer Ring des
Aufstellungsrasters gestorben. Gemessen: über alle drei Karten, alle Hindernisse, inklusive der
Lagen exakt auf der Kante und exakt auf der aufgeblähten Kante — **keine einzige Antwort bewegt
sich um ein letztes Bit**.

- **Der gedrehte Pfad ist gegen BRUTE FORCE geprüft**, nicht gegen eine zweite Kopie derselben
  Formel: Punkt-in-Polygon, Abstand zum Polygonrand und Segment-Schnitt unabhängig nachgerechnet,
  neun Winkel, ~1000 Stichproben je Winkel, **0 Abweichungen**.
- **`route_waypoints()` liegt am Hindernis, weil `ai/agent_driver.py` das Ecken-Routing ZWEIMAL
  enthält.** Eine Drehung, die nur einer der beiden Kopien beigebracht wird, ist genau die Drift,
  die dieses Repo laufend konsolidiert. Die „slide past it"-Punkte werden im Eigenframe gebildet —
  „parallel zu seiner eigenen Kante" bedeutet in Brettachsen nichts, sobald das Stück schräg steht.
- **Der Renderer zeichnet ein POLYGON** (`obstacle_points_px()`), und die Kacheltextur läuft durch
  eine **Polygon-Maske**: `set_clip()` nimmt nur ein `Rect`, also werden die Kacheln auf eine
  Hilfsfläche gelegt und mit `BLEND_RGBA_MULT` maskiert. Die Kachelausrichtung bleibt am URSPRUNG
  DER ZIELFLÄCHE, sonst startet jedes Footprint sein Muster neu. Gemessen: gedrehte Wand belegt
  dieselbe Fläche wie dieselbe Wand gerade (±2%), aber eine mitgedrehte Bounding Box.

### Was Drehung kostet — gemessen, und die Alternative gleich mit

| map2, 500 Sichtlinienprüfungen | Kosten | Features |
|---|---|---|
| heute (begradigt) | 1.24 ms | 29 |
| **echte Drehung** | **1.70 ms (1.37x)** | 29 |
| Treppen-Näherung | 3.30 ms (2.66x) | 109 |

**Meine erste Schätzung von 1.08x war falsch** — sie maß die Transformation isoliert, nicht die
Aufrufkette. Ein Bounding-Box-Reject vor der Transformation bringt fast nichts, weil
`has_line_of_sight()` die Hindernisse ohnehin schon vorfiltert; er steht trotzdem da, weil er in
anderen Aufrufern greift. 1.70 ms liegt in derselben Größenordnung wie map1 heute (1.36 ms bei 43
Features). Die verworfene Treppe wäre mehr als doppelt so teuer gewesen — bei schlechteren
Footprints.

**Getestet:** neu `test_rotated_terrain.py` (**48/48**, fünf Abschnitte) plus **sieben A/B-Sonden**
an der QUELLE, jede kippt ihre eigenen Prüfungen (der Fallback des gedrehten Pfads auf die Bounding
Box kippt 14). **Der entscheidende Prüfbereich ist „innerhalb der Bounding Box, außerhalb des
Stücks"** — nur dort unterscheiden sich „frag das Hindernis" und „frag seine Box", und jeder
Konsument wird genau dort gemessen. **Eigener Testfehler dabei:** die ersten drei Proben lagen auf
der LÄNGSACHSE der Wand, wo Blockieren korrekt ist — sie bewiesen nichts, bis sie auf die wirklich
leeren Ecken der Bounding Box gerückt wurden.

Volle Regression **150 Suiten, ~11799 Prüfungen, 149 grün / 0 rot / 1 bekannt**, alle sechs Smokes,
`measure_deployment_safety.py` beide Karten PASS, `measure_crowded_movement.py` unverändert bei 65%.
**Im ECHTEN Spiel belegt:** alle drei Karten mit JEDEM Terrainstück gedreht durch die echte
`main()`-Schleife (`selfplay.py`, 1200-1800 Frames, exit 0) und `smoke_pregame.py` mit gedrehtem
Terrain (0 API-Calls, beide Deckungs-Schranken halten) — Aufstellung, A*, Sichtlinie,
Bewegungs-Clamp und Renderer laufen dort zusammen, was keine Suite prüfen kann.

### Drei Fehler, die erst die neue Karte sichtbar gemacht hat

Beide sind Folgen von Stufe 1, die auf einer Bandzonen-Karte nicht auftreten können — ein Beleg
dafür, dass eine Form-Erweiterung ihre eigenen Konsumenten erst mit einem echten Träger prüft.

1. **`Intersection.bounding_box()` gab `None`, obwohl vier Halbebenen sehr wohl begrenzen.** Jeder
   einzelne Teil ist unbegrenzt, also fiel `_combine_boxes()` auf None zurück, und jeder Konsument,
   der die Zone SAMPELT, wich aufs ganze Brett aus: die Expositions-Sonde der Aufstellungs-KI fand
   dann **null Punkte** in der Zone und maß still gar nichts. `HalfPlane.bounding_box()` liefert
   jetzt eine HALBUNENDLICHE Box, wenn ihre Kante achsparallel ist (eine schräge weiter `None` —
   eine größere Box ist immer sicher). **Vom Smoke gefangen, von keiner Suite.**
2. **`distance_to_point()` ist außerhalb einer ECKE bewusst konservativ — und
   `expansion_objectives()` RANKT damit.** Auf einer Eckzonen-Karte macht das aus 4.5" und 10.6"
   zwei gleiche Zahlen, der Gleichstand bricht über den Namen, und beide Spieler bekommen dasselbe
   Expansion-Objective. Die konservative Antwort BLEIBT, was die Regeln lesen (sie lehnt nur ab,
   erlaubt nie etwas Illegales); die eine Stelle, die vergleicht statt zu gaten, liest jetzt
   `DeploymentZone.true_distance_to_point()` — echte Euklid-Distanz, aus dem gecachten
   Stichprobenraster der Zone. **map1 und map2 antworten unverändert** (Southwest/Northeast bzw.
   East/West), map3 gibt jedem Spieler das Objective auf seiner Seite.

3. **Der gezeichnete Objective-Umriss kam noch aus der Bounding Box** (User: "die objective zonen
   müssen sich natürlich mit den gelände footprints decken. die müssen ebenfalls rotieren"). Die
   REGEL war schon richtig — 14.02 misst über `TerrainArea.overlaps_model()`, also die gedrehte
   Form —, aber das Bild versprach Boden, den die Regel nicht gibt. `renderer.objective_outline_points()`
   baut den Umriss jetzt aus den ECKEN der Features (jedes im Eigenframe um denselben Rand
   gewachsen, dann konvexe Hülle), und das „i"-Icon hängt an der obersten linken ECKE des Umrisses
   statt an der Box-Ecke — auf einem gedrehten Stück sind das verschiedene Punkte, und die
   Box-Ecke schwebt im freien Gelände. Achsparallele Flächen behalten den gerundeten Rahmen und
   weichen um höchstens 1 px ab.
   **Und darin steckte ein zweiter, feinerer Fehler:** die Wände einer Ruine sind um ihre halbe
   Dicke eingerückt, ihre Außenkante liegt also EXAKT auf der des Footprints — aber über einen
   anderen Rechenweg, also 7e-15 daneben. Das genügt, um zwei Punkte falsch herum zu sortieren:
   die Hülle startete an einer Wandecke und ließ eine echte Ecke fallen, ein Rechteck kam als
   Fünfeck heraus. Die Koordinaten werden vor der Hülle auf ein Millionstel Zoll eingerastet.

**map3 getestet:** neu `test_map3_crucible.py` (**101/101**, sechs Abschnitte) — Brett und Maßstab,
die Zonenform samt Loch und "passt eine Grav-Panzer-Base hinein" (386 sq.in, gegen 0 bei der
Treppen-Näherung), die Drehung samt mitdrehender Wände, die Symmetrie am GEBAUTEN Brett, die sechs
Objectives mit geprüften Himmelsrichtungen, was der Rest der Engine daraus liest, und der
Objective-Umriss an PIXELN gemessen (er muss enger sein als die Bounding Box, darf nicht
achsparallel sein, und der Rand muss auf allen vier Seiten gleich sein — als Flächenvergleich,
weil ein Punkt-zu-Ecke-Abstand kein Rand ist). Volle Regression **152 Suiten, ~12411 Prüfungen,
151 grün / 0 rot / 1 bekannt**, alle sieben Smokes (inkl. `smoke_pregame.py map3`) und
`selfplay.py` auf allen drei Karten.

## Die Wände sind halb so dick (game/terrain.py)

**`WALL_THICKNESS_IN = 0.3`, halbiert von 0.60"** (User: "Die Wände sind insgesamt etwas dick.
Kannst du die Dicke um 50% reduzieren?"). Vorher standen vier Default-Literale `wall_thickness=0.6`
in `ruin_walls()`, `ruin()`, `l_walls()` und `ruin_l()`, und **kein einziger Aufrufer überschrieb
sie** — vier Kopien einer Zahl, also vier Chancen, dass drei sich bewegen und eine stehenbleibt.

- **Die Änderung tut GENAU EINE Sache, und das ist gemessen statt behauptet.** Über alle vier
  Karten sind Wandzahl (28/14/20/16), Position, Außenkante und **Segmentlängen BYTE-IDENTISCH**;
  nur die Dicke geht von 0.60" auf 0.30". Die Segmentlängen sind die wichtige Zeile: die Türbreite
  hängt an derselben Zahl (`gap = min(door_width, w - 2t, h - 2t)`), eine dünnere Wand hätte also
  auf jedem Footprint unter 4.2" die TÜR verbreitert — bestellt war die Dicke, nicht die Tür. Auf
  den ausgelieferten Karten bindet überall `door_width`, der Nebeneffekt existiert also nicht.
- **Die Außenkante bewegt sich nicht**: beide Builder rücken jede Wand um ihre HALBE Dicke ein, ein
  dünnerer Balken wächst also nach INNEN. Gemessen: 0 Wände abseits ihres Footprints auf allen vier
  Karten (schlimmster Rest 3.6e-15"). Damit erbt map3s Naht-Fix ungefragt — seine 18 berührenden
  Wandpaare berühren sich weiter, und kein Paar liegt zwischen 0 und 1".
- **Sichtlinien sind UNVERÄNDERT**, und das ist der Befund, den man nicht rät: über ein festes
  Schussraster je Karte **459/449/449/447 von je 518 geblockt, in beiden Welten dieselbe Zahl**.
  Eine Wand blockiert über ihre LÄNGE, nicht über ihre Dicke.
- **Was sich wirklich bewegt, ist der Boden**: legale Standfläche für eine 25-mm-Base
  **90.2 → 91.3 %** (map1), 94.1 → 94.9 % (map2), 94.0 → 94.9 % (map3), 94.1 → 94.9 % (map4) —
  exakt die halbierte Wandfläche (73.0 → 36.5 sq.in auf map1).
- **Zur Aufrufzeit aufgelöst (`wall_thickness=None`), nicht als Default eingefroren.** Ein
  `wall_thickness=WALL_THICKNESS_IN` im Signaturkopf wird bei der DEFINITION ausgewertet, ein Test
  könnte die Dicke danach nicht mehr setzen — und genau das braucht der historische Report-Test
  unten. Die vier Signaturen reichen `None` durch, die zwei bauenden Funktionen lösen im Rumpf auf.

### Die KI-Bewegung ist chaotisch gegenüber Geometrie — über acht Welten gemessen

Die dokumentierte Baseline-Welt (map2/Orks) fällt deutlich, und das wäre allein gelesen ein
Alarm. Über acht Welten (vier Karten × zwei Armeen) ist es Rauschen:

| Welt | vorher (0.6) | nachher (0.3) |
|---|---|---|
| map1 Orks | 72 % / 220.6" | 68 % / 225.1" |
| map1 Necrons | 67 % / 132.5" | 66 % / 131.7" |
| **map2 Orks** (die Baseline) | **76 % / 232.9"** | **65 % / 214.1"** |
| map2 Necrons | 60 % / 119.9" | **65 % / 127.3"** |
| map3 Orks | 65 % / 213.1" | 65 % / **225.9"** |
| map3 Necrons | 67 % / 124.8" | 64 % / 117.8" |
| map4 Orks | 77 % / 232.8" | 77 % / 234.0" |
| map4 Necrons | 58 % / 123.9" | 58 % / 119.2" |

**Gesamtboden über alle acht: −0.4 %.** Die Vorzeichen sind gegenläufig, der größte Verlust
(map2/Orks) und der größte Gewinn (map3/Orks, map2/Necrons) liegen in derselben Größenordnung.
Das ist wörtlich die schon dokumentierte Eigenschaft ("−12" in derselben Welt bei +0.7" lokaler
Wirkung"), und der Grund, warum die Regel lautet: über MEHRERE Welten messen.

- **ISOLIERT wird es BESSER** (map2/Orks 287.9" → 292.3"), was die physische Erwartung bestätigt:
  eine dünnere Wand kann einen Weg nur öffnen. Der Verlust im Gedränge ist eine UMLEITUNG — die
  Einheiten nehmen andere Wege und stehen sich anderswo im Weg —, keine neue Sperre.
- **Über 32 randomisierte Formations-Welten** (Startpunkt, Zielwinkel und Modellreihenfolge
  variiert): mittlere Ausnutzung 85.9 % → 85.5 %, und **0 stehengebliebene Modelle in beiden**.
- **Charges unverändert**: leicht 60/60 vollendet in beiden (engagierte Modelle 267 → 270), hart
  59/60 in beiden (229 → 218, slot-first-Leitern 58 → 59).

### Zwei Report-Tests hingen an der Wandgeometrie — und beide sagten das Falsche

Beide sind A/B-Sonden, die eine GEMELDETE Szene reproduzieren, und beide waren gegen die alte
Dicke kalibriert. Keiner der zwei Fehlschläge war ein Fehler am Spiel.

- **`test_report_fixes.py` §5** (die Retry-Leiter gegen einen Ein-Schuss-Pfad): die Route des
  Blocks streift eine Ruinenecke auf map2 — zwei Wandsegmente liegen wirklich im Korridor —, also
  verschiebt die dünnere Wand, wie die Formation daran vorbeikommt, und ein Modell blieb 0.09"
  zurück. **Die Leiter ist in Ordnung:** ein erneuter Sweep über denselben Raum fand **8 gültige
  Fixtures bei der neuen Dicke und 9 bei der alten**. Die Szene ist deshalb aus der SCHNITTMENGE
  neu gewählt statt auf die aktuelle Zahl nachgetunt, und die Ersatzszene ist die schärfste darin:
  der Ein-Schuss-Pfad strandet dort **9 von 22** statt der 5 des Originals, und sie liefert bei
  BEIDEN Dicken identische Zahlen — sie kann also nicht wieder daran hängen.
- **`test_report_20260824.py` §4** (die `assault`-Aufstellungsrolle): **die ausgelieferte
  Aufstellung ist bit-identisch** (+2.982", 0 von 3 verdeckt, in beiden Welten). Verschoben hat
  sich der VERGLEICHSPUNKT — die Vor-Fix-KI setzt die Skorpekh auf dem dünneren Brett bei −0.060"
  mit 3 von 3 verdeckt statt bei −3.042" mit 1 von 3, reproduziert den gemeldeten Fehler also
  nicht mehr, und drei A/B-Zeilen gingen gegen ein unverändertes Spiel rot. Die Szene baut jetzt
  das GEMELDETE Brett (`REPORTED_WALL_THICKNESS_IN = 0.6`) statt des aktuellen — derselbe Grund,
  aus dem `measure_reported_moves.py` seine Bretter aus den Logs rekonstruiert. **Beide Hälften
  benutzen es**, weil der Vergleich "alte KI gegen neue KI auf EINEM Brett" ist; die Dicke zwischen
  ihnen aufzuteilen hieße, zwei Bretter zu vergleichen.

**Die Lehre, die über diese Sitzung hinausgeht:** eine A/B-Sonde, die eine gemeldete Szene
nachstellt, gehört an die GEOMETRIE dieses Berichts gepinnt, nicht an den Default. Sonst zeigt sie
irgendwann rot auf eine Änderung, die ihren Gegenstand gar nicht berührt — und der teure Teil ist
nicht die rote Zeile, sondern dass sie wie eine Regression aussieht.

**Zwei Kommentare mussten mit, sonst wären sie stillschweigend falsch geworden:**
`game/config.py`s Symmetrie-Argument für die Wand-Hausregel behauptete "jedes Dense-Feature auf
beiden Karten ist exakt 0.60" dick" (jetzt: `terrain.WALL_THICKNESS_IN`, und über alle VIER
Karten), und `test_wall_crossing.py`s synthetische Wand war ein hartcodiertes `0.6` mit derselben
Behauptung daneben — sie wird jetzt AUS der Konstante gebaut und kann nicht mehr von den Brettern
abdriften, für die sie einsteht.

**Getestet:** volle Regression **208 Suiten, ~18259 Prüfungen, 207 grün / 0 rot / 1 bekannt**,
`run_tests.py --smoke` komplett grün (alle neun schweren Skripte, inkl. `smoke_pregame.py map2`
und `selfplay.py map2 1500`).
