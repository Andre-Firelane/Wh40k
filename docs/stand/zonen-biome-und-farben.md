# Aufstellungszonen, Biome und Farben

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Aufstellungszonen sind FORMEN (game/shapes.py, game/deployment.py)

**Stufe 1 der Karten-Geometrie-Arbeit** (User: "ja zonen müssen auch gedreht werden. sie haben
sogar spezielle shapes wie auf dem screenshot. mit einem kreis in der mitte. und bei schrägen oder
ecken-aufstellungszonen muss die map für die territories auch diagonal geteilt werden"). Terrain
ist noch achsparallel — das ist Stufe 2.

- **Eine Zone wird genau DREI Dinge gefragt, und alle drei sind dieselbe Distanzfrage.** Deshalb
  ist eine Form eine SIGNED DISTANCE (positiv innen, Betrag = Zoll zum Rand), und
  `contains_point` ist `sd >= 0`, `contains_circle` (03.01 "wholly within") ist `sd >= r`,
  `distance_to_point` (24.20 INFILTRATORS) ist `max(0, -sd)`. Eine neue Zonenform kostet damit
  **null Code** in `deployment.py`.
- **Primitiven:** `Rect(x, y, w, h, angle_deg)` (gedreht; `angle_deg=0` nimmt den alten Pfad),
  `HalfPlane` (+`through()` — die Primitive, die Diagonalen ÜBERHAUPT möglich macht, und vier
  davon sind ein gedrehtes Rechteck), `Disc`, `Outside(shape)` (der Kreis in der Mitte, als
  SUBTRAKTION geschrieben statt als `inside=False`-Flag), `Intersection`/`Union`.
- **Warum nicht weiter mit Rechtecken annähern — gemessen, und es ist der entscheidende Befund.**
  Beim Terrain kostete die Treppe 25% Mehrfläche (lebbar). Bei einer ZONE ist sie
  **nicht-monoton kaputt**, weil `contains_circle` verlangt, dass EIN EINZELNES Rechteck die ganze
  Base hält: an einer diagonalen Eckzone (44"×44") bleiben von der legalen Aufstellfläche bei
  4/8/16/32 Streifen für eine 25-mm-Base 101/95/71/**10** %, für 50 mm 96/76/22/**0** %, für einen
  Grav-Panzer 84/33/**0**/**0** %. Verfeinern macht es STRIKT SCHLECHTER, und der Kreis in der
  Mitte ist mit Rechtecken gar nicht darstellbar. Es gibt hier also keinen Rückfallplan.
- **Exaktheit steht pro Kombinator da, nicht als Annahme.** `Union` = `max()` reproduziert die
  alte Lesart BIT FÜR BIT (`max_i sd_i >= r` genau dann, wenn irgendein einzelnes Rechteck die
  ganze Base hält), Naht-Konservatismus inklusive. `Intersection` = `min()` ist innen exakt;
  AUSSERHALB einer ECKE meldet es die Distanz zur näheren Kanten-GERADEN statt zum Eckpunkt,
  unterschätzt also, wie weit draußen ein Punkt ist — was jeder Konsument als "näher an der Zone"
  liest und damit eine Platzierung ABLEHNT statt eine illegale zu erlauben. Sichere Richtung, im
  Test gepinnt.
- **Die dokumentierte Naht-Schwäche ist geschlossen**, aber nur für neue Formen: eine als
  Halbebenen-Schnitt geschriebene Zone hat keine Naht, an der ein Modell zu Unrecht abgelehnt
  würde. Als Rechteck-Union geschrieben bleibt sie bewusst wie bisher.
- **`.rects` ist ab jetzt die AUTOREN-EINGABE, nicht die Form.** Eine formgebaute Zone hat keine.
  Kein Produktivmodul liest es mehr (Quell-Wächter); Tests dürfen es weiter benutzen, um ein
  Modell an eine bekannte Stelle zu setzen.
- **`secondary_missions.zone_distance()` war eine ZWEITE Kopie von `distance_to_point()`**
  (Fehlerklasse 10, identische Arithmetik) und delegiert jetzt. Die beiden widersprachen sich nur
  im Leer-Zonen-Fall (0.0 gegen inf); `inf` gewinnt — eine leere Zone enthält nichts, also ist
  24.20 überall erfüllt statt nirgends. Kein Roster erreicht den Fall.

### Territorien: Abstand zur ZONE, nicht zu einem Punkt darin

`in_own_territory()` leitete die Trennung schon immer aus den Zonen ab, konnte aber zuerst nur
eine WAAGERECHTE oder SENKRECHTE Linie erzeugen (Achsen-Wahl), dann eine Mittelsenkrechte zwischen
den zwei Zonen-ZENTREN. Seit map4 gilt: **mein Territorium ist jeder Punkt, der meiner ZONE näher
ist als der gegnerischen** — gemessen zur FORM über `DeploymentZone.distance_to_point()`, nicht zu
einem Stellvertreterpunkt darin. Drei Karten hängen dran (Beacon, Outflank, Plunder).

- **Die Zentren-Fassung ist an map4 gescheitert, und zwar an ihrem eigenen Versprechen** ("die
  Trennlinie dreht sich mit den Zonen"). map4s Zonen sind Dreiecke hinter zwei PARALLELEN
  Diagonalen, und der User verlangt die Grenze als dritte Parallele in der Mitte. Gemessen: die
  Zentren-Mittelsenkrechte läuft dort bei **69.85°**, die Zonenkanten bei **55.71°** — vierzehn
  Grad daneben.
- **Mit dem Abstand zur FORM ist es exakt, nicht nur nahe dran:** zwischen zwei parallelen Kanten
  ist der Gleichstand genau die Parallele in der Mitte. Über ein 401×401-Raster **0 von 160600**
  Punkten weichen von der Ideallinie (15,0)–(45,44) ab; die Zentren-Regel wich auf 5.72% ab.
- **Was sich auf den ausgelieferten Karten bewegt** (201×201, beide Spieler, 80802 Punkte): map1
  und map2 **0** (achsparallele Bänder — Kanten- und Zentrenabstand trennen an derselben Linie),
  **map3 4993 = 6.18%**. Das ist eine bewusste Änderung an einem ausgelieferten Brett und kein
  Nebeneffekt: gegen map3s Quadranten liegt die Formen-Regel **näher an der Eck-Diagonale des
  Bretts** als die Zentren-Regel (7.81% Abweichung gegen 11.68%), ist dort also ebenfalls die
  bessere Antwort.
- **`_zone_centre()` hat damit KEINEN Produktivleser mehr** und bleibt trotzdem (samt Re-Export in
  `secondary_missions.py`): `test_deployment_shapes.py` baut beide abgelösten Regeln daraus nach.
  Eine Vor-Fix-Welt, die man nicht herstellen kann, ist ein Fix, den man nicht messen kann.
- **Testfalle, die bleibt:** die vier BRETTECKEN unterscheiden die Regeln NICHT (bei symmetrischen
  Eckzonen stimmen sie dort zufällig überein) — der Test muss Punkte nehmen, die auf verschiedenen
  Seiten der Diagonale, aber derselben Seite der Mittellinie liegen.
- **Getestet:** `test_deployment_shapes.py` 106 → **110/110** (der map4-Block misst gegen die
  IDEALLINIE, nicht gegen den Code, der sie erzeugt), plus drei A/B-Sonden in
  `ab_map4_sundered.py` (Zentren-Regel zurück, Seiten vertauscht, Abstand zur Bounding Box).

### Renderer und Aufstellungs-KI ziehen mit

- **`renderer._shape_outline_segments()`** trägt den Umriss per MARCHING SQUARES aus der Signed
  Distance ab (0.25"-Raster, Kreuzungen linear interpoliert, damit ein Bogen glatt wird). Läuft
  auf der GECACHTEN statischen Ebene, also einmal pro Szene. **Eigener Fehler, der dabei auffiel:**
  ein Punkt auf der Grenze zählt als innen (`sd >= 0`), also findet das Verfahren am Rand der
  Bounding Box gar keinen Vorzeichenwechsel — der Umriss verschwand entlang jeder Kante, die bündig
  mit der Box liegt, also jeder Kante eines Rechtecks. Der Sampling-Bereich wird deshalb um zwei
  Zellen VERGRÖSSERT.
- **`renderer.own_board_edges()`** ist eine reine Funktion: eine Brettkante gehört der Zone, wenn
  ihre Außennormale in dieselbe Richtung zeigt wie "von der Brettmitte zu dieser Zone". Das
  verallgemeinert den alten Nord/Süd-Test und ist auf den drei Karten identisch — **das strikte
  `>` ist der Grund**: eine vollbreite Bande berührt West und Ost wirklich, aber deren Normalen
  stehen exakt SENKRECHT (Skalarprodukt 0) und fallen raus. Eine Eckzone behält beide Kanten.
- **Gemessen statt behauptet:** gegen die alte Zeichnung liegen 94% der alten Linie innerhalb von
  2 px der neuen und **0 neue Pixel** ohne Entsprechung; der Rest ist EINE Bildzeile des unteren
  Kanten-Bandes (jetzt symmetrisch zum oberen).
- **`deployment_ai` sampelt die FORM.** `sampling_boxes(inset)` liefert die Boxen, über die das
  Kandidatenraster gelegt wird — für ein achsparalleles Rechteck ist das EXAKT das alte Raster
  (Beweis im Docstring: `sd >= inset` heißt, die ganze Scheibe liegt drin, also liegt der Punkt
  mindestens `inset` von jeder Seite der Bounding Box), und `Union` gibt eine Box PRO TEIL, damit
  eine gestufte Zone weiter pro Rechteck gerastert wird.

### Drei eigene Fehler, alle erst von den Sonden gefunden

1. **Die Randlage kippte, und die erste A/B-Sonde sah es nicht.** 720 000 ZUFÄLLIGE Vergleiche
   meldeten 0 Abweichungen — aber das Kandidatenraster der KI setzt seine Punkte ABSICHTLICH exakt
   eine Basisbreite innerhalb der Kante, und dort rundet die Signed Distance anders als der
   Rechteck-Vergleich: **103 von 210** dieser Punkte kippten von legal auf illegal, also der ganze
   äußere Ring und damit die vorderste Reihe. `test_report_20260824.py` wurde dadurch rot.
   `PLACEMENT_TOLERANCE_IN = 1e-9` behebt es. **Fehlerklasse 16 in Reinform: eine Sonde, die die
   eine Lage nicht herstellt, auf die es ankommt, beweist nichts.**
2. `_zone_probe_points(zone)` OHNE Brettmaße (so rufen `measure_deployment_safety.py` und
   `smoke_pregame.py` es) klemmte die Box auf (0,0,0,0) und lieferte eine LEERE Probenliste — ein
   Default, der zwei Harnesses still entwertet hätte.
3. Der INFILTRATORS-/Kein-Zonen-Pfad in `_candidate_points` bekam den Inset nicht mehr, weil ich
   das rohe Brettrechteck übergab statt es durch `sampling_boxes()` zu schicken.

**Getestet:** neu `test_deployment_shapes.py` (**77/77**, acht Abschnitte) plus **sechs A/B-Sonden**
an der QUELLE, jede kippt genau ihre eigenen Prüfungen. **Drei Sonden bissen zuerst NICHT, und alle
drei waren Befunde über den TEST** (Eckpunkte, die beide Territoriums-Regeln gleich beantworten;
keine ausgelieferte Zone mit zwei Rechtecken, also lief `Union` nie; und ein reiner Quell-Wächter
statt eines Verhaltenstests für die Kantenwahl — deshalb ist `own_board_edges()` jetzt eine
extrahierte reine Funktion). Volle Regression **149 Suiten, ~11748 Prüfungen, 148 grün / 0 rot /
1 bekannt**, alle fünf Smokes, `measure_deployment_safety.py` auf beiden Karten PASS,
`measure_home_garrison.py` unverändert und `selfplay.py map2`.

## Aufstellungszonen-Markierungen (game/renderer.py)

**Zone des Spielers GRÜN, die des Gegners ROT, beide Markierungen dicker** (User: "nur die
aufstellungszonen müssen sichtbarer sein. mach die markierungen dicker. gegner: rot / spieler:
grün"). Player 1 war ein Blau nahe `OWN_ARMY_COLOR`.

- **Der eigentliche Grund für die Unsichtbarkeit war ein SKALIERUNGSFEHLER, kein zu kleiner Wert.**
  Beide Breiten gingen ROH an `pygame.draw.line()` — auf einer Fläche, die `main.py` mit dem
  Mehrfachen der Bildschirmauflösung rendert. **Gemessen bei Default-Zoom:** die "2-Pixel"-Kontur
  landete auf **0.70** Bildschirmpixeln (map2, 1920×1080) bzw. **0.37** (map1), die "5-Pixel"-
  Kantenmarkierung auf 1.74 bzw. 0.94. Die Zahlen im Quelltext beschrieben eine Linie, die nie
  jemand gesehen hat.
- **Es ist exakt der Fehler, für den `_ring_width()` schon existiert** (er hat
  `TOKEN_INNER_RING_WIDTH` hervorgebracht, und der Konstruktor-Kommentar schreibt ihn aus). Beide
  Konstanten sind jetzt ON-SCREEN-Pixel und gehen dort hindurch; "dicker machen" ist also
  überwiegend, sie in der Breite zu zeichnen, die sie ohnehin behaupteten. 2 → 3 und 5 → 7 kamen
  obendrauf — und genau dieses Obendrauf ist auf Nachtrag wieder abgeräumt (User: "die
  aufstellungszonen linien sind jetzt sehr gut erkennbar, aber mach sie bitte etwas dünner"): jetzt
  **2.4 und 5**, der FIX bleibt. Gemessen 1920×1080/map2: Kontur 3.48 → 2.78 px, Kantenband
  8.35 → 5.92 px, das dickere also am stärksten. **Warum ein Bruch:** `_ring_width()` nimmt einen
  Float, und glatte 2.0 landeten EXAKT auf dem Modell-Basisring (beide 2.44 px) — womit die einzige
  Schranke dieser Arbeit fiele; 2.5 wiederum ist ein `round()`-Gleichstand (bricht auf GERADE, also
  2 px bei Skalierung 1 und 8 bei 3, ein 4x wo die Konstante 3x verspricht).
- **Und die zwei Breiten sind jetzt EINE** (User: "bei den Aufstellungszonen gibt es an den
  spielfeldrändern sehr dicke Linien. können die genau so dick sein wie die innenliegenden
  Linien?"): `BOARD_EDGE_LINE_WIDTH = DEPLOYMENT_ZONE_LINE_WIDTH`, **abgeleitet statt zweimal
  hingeschrieben** — Gleichheit IST die Bitte, und zwei getrennt gepflegte Zahlen sind der Weg, auf
  dem sie aufhört zu gelten. Gemessen 1920×1080/map2: Kantenband **5.92 → 2.78 px**, also exakt die
  Kontur; auf map1 4.30 → 2.06. Der Name bleibt, weil es weiter zwei ROLLEN sind.
  - **"Zuordnung der Spielfeldkanten" überlebt das**, und das ist der Grund, warum die Änderung
    gefahrlos ist: WEM eine Brettkante gehört, sagt die FARBE der Linie und ihre ANWESENHEIT (eine
    Kante, die niemandem gehört, bekommt gar keine) — nie ihre Dicke.
  - **Zwei fremde Pins waren zu Recht rot** und sind umgedreht: „das Kantenband ist das dickere der
    beiden" (jetzt: exakt gleich) und ein Vergleich einer gemessenen Pixelzeile gegen die
    Float-Konstante (jetzt gegen `_ring_width()`, also gegen die wirklich gezeichnete Breite).
    Die Basisring-Schranke steht jetzt AUCH fürs Kantenband ausdrücklich da, statt aus der
    heutigen Gleichheit zu folgen.
  - **Ein Befund vor dem Ausliefern:** die naheliegende Prüfung `BOARD_EDGE_LINE_WIDTH is
    DEPLOYMENT_ZONE_LINE_WIDTH` ist eine TAUTOLOGIE — CPython faltet gleiche Float-Konstanten eines
    Moduls zu EINEM Objekt, `2.4 is 2.4` über zwei Zuweisungen ist also True und die Prüfung
    bestünde für genau die Kopie, die sie verbieten soll. Geprüft wird deshalb der QUELLTEXT.
  - **Getestet:** `test_deployment_zone_markings.py` 50 → **58/58**, neu `ab_zone_edge_width.py`
    (**4 A/B-Sonden, alle beißend** — das fette Kantenband zurück, dieselbe Breite als KOPIE statt
    Ableitung, eine um 0.2 abweichende Breite, und die ungeskalierte Originalfassung).
- **`_draw_inset_edge_line()` bekommt die Breite ÜBERGEBEN** statt sie aus der Konstanten zu lesen:
  nur `Renderer` kennt die Render-Skalierung, und der Einzug wird aus derselben Zahl gebildet wie
  die gezeichnete Linie — aus zwei verschiedenen gerechnet hängt die halbe Linie über der
  Brettkante, was eine 7-Pixel-Markierung wie eine 3er aussehen lässt.
- **Die Schranke im Test ist ein VERHÄLTNIS, keine absolute Zahl**, und das ist gemessen begründet:
  `render_scale × camera` ist `Fläche_px / (Brett_in × PIXELS_PER_INCH)`, also schrumpft auf einem
  kleinen Fenster JEDE On-Screen-Pixel-Angabe dieses Renderers gemeinsam — Modellringe und Schriften
  eingeschlossen (1366×768 map1: das ganze Brett läuft auf 58% von nominal, die Kontur landet dort
  auf 1.8 statt 3.5 px). Eine absolute Untergrenze wäre also gar keine Aussage über die
  Markierungen, sondern über das Fenster. Geprüft wird deshalb: der Fix hat sie mit der
  Render-Skalierung multipliziert, und sie sind dicker als der Modell-Basisring, den der User
  bereits als lesbar akzeptiert hat.
- **Zonenfarbe und Basenfarbe stimmen wieder überein, und das ist eingetragen statt stillschweigend
  repariert:** hier stand, die Spielerzone sei bewusst NICHT die Basenfarbe — das hörte auf zu
  stimmen, als `OWN_ARMY_COLOR` zu Grün zurückging (siehe unten). Beide User-Entscheidungen wollten
  auf der Spielerseite Grün, das Zusammenfallen ist also zweimal bestellt und keine Kollision;
  "grün gehört mir, rot gehört ihm" sagt jetzt an beiden Stellen dasselbe. Die zwei Grüntöne
  bleiben verschieden (Ring (40,200,60) gegen das hellere (80,225,115), 40 auseinander) und liegen
  ohnehin nie nebeneinander — eines ist ein Ring auf einem Modell, das andere eine Linie an einer
  Zonengrenze.
- **Getestet:** neu `test_deployment_zone_markings.py` (**43/43**, vier Abschnitte) plus **acht
  A/B-Sonden**, jede kippt ihre eigenen Prüfungen. **Vorher gab es zu dieser Zeichnung GAR KEINEN
  Test** — 13 562 Prüfungen liefen grün durch eine so sichtbare Änderung, und genau deshalb konnte
  eine 0.37-Pixel-Linie jahrelang dort stehen. `test_deployment_shapes.py` besitzt weiter die
  FORMEN (was drin liegt, welche Brettkante wem gehört), diese Suite das AUSSEHEN.
- **Nebenbefund derselben Sitzung: der Objective-Hover stürzte ab** (User: "NameError: name 'rect'
  is not defined ... beim hovern über das objective info icon"). Vorbestehend, in `HEAD` belegt —
  siehe Fehlerklasse 15s Kehrseite oben für die Ursache und den Wächter. Die zweite Hälfte ist ein
  VERHALTENStest: **nichts in diesem Repo hat je ein Objective gezeichnet**, `draw_objectives()`
  kam in genau einer von 13 600 Prüfungen vor, und die ruft es nicht auf. Neu
  `test_objective_hover_label.py` (**11/11**) fährt jedes Objective jeder Karte unter dem Cursor —
  A/B mit wiederhergestellter Meldung: 6 von 11 fallen, jede nennt den gemeldeten Fehler wörtlich.
  Ein Quell-Wächter allein hätte nur gesagt, dass der Zweig LAUFEN kann, nicht dass das Label
  stimmt (es hängt jetzt nachweislich über dem Icon, an dem es klebt).
- **Zwei eigene Sondenfehler:** die "Vorher"-Zahl wurde zunächst mit der NEUEN Konstante gerechnet
  und schmeichelte der Vor-Fix-Welt um einen halben Pixel (die gelieferten Werte 2 und 5 stehen
  jetzt als eigene Konstanten im Test); und zwei Sonden ließen die Suite ABSTÜRZEN statt rot zu
  werden, weil eine Liste per Entpacken gelesen wurde — dritte Instanz derselben Lehre wie bei den
  `str.index()`-Wächtern.

## Biome (game/biomes.py)

**VIER Biome — City, Desert, Forest, Arena — als vier Knöpfe ganz oben im Kartenauswahl-Screen.**
Die ersten drei sind je DREI BILDER, das vierte ist ZEICHENCODE — siehe `## Das Arena-Biom` unten.
`Biome.folder is None` markiert es, `biomes.is_procedural()` ist die EINE Frage danach, und alles
Übrige (Knopf, Vorschau, Cache, `--biome`, "rein kosmetisch") behandelt alle vier gleich.

Ursprünglich drei (User:
"ich habe die texturen für die maps in ordner geordnet. es gibt jetzt 3 biome. kannst du bei der map
auswahl bitte ganz oben noch 3 knöpfe reinpacken, über die man sein biom wählen kann?"). Ein Biom
sind genau DREI Bilder: der Boden plus die zwei Cover-Texturen, mit denen ein Terrain-Footprint
gefüllt wird.

- **REIN KOSMETISCH, und das ist gemessen statt angenommen.** Brettmaße, beide Zonen, jedes
  Terrainstück, jedes Objective sind unter allen drei Biomen identisch (im Test als Gleichheit der
  gebauten Szene gepinnt); nur das gerenderte Bild unterscheidet sich (als Hash der drei Karten unter
  drei Biomen: 9 von 9 verschieden). Beide Hälften zusammen, weil jede allein wertlos ist — ein Biom,
  das nichts ändert, ist ein toter Knopf; eines, das das Brett ändert, ist ein Fehler.
- **Das Verschieben in Ordner hatte alle drei Texturen TOT gemacht.** Gemessen vor der ersten
  Änderung: `ground_texture_path()`, `dense_cover_texture_path()` und `normal_cover_texture_path()`
  gaben ALLE `None` zurück, der Renderer war also still auf seine Flat-Color-Fallbacks
  zurückgefallen. Die drei festen Namen in `sprites.py` zeigten auf `Sprites/wüste-boden.jpg` &
  Co., die jetzt in `Sprites/Map Textures/<Biom>/` liegen.
- **Default ist `desert`, und der LOOKUP ist belegt verhaltensneutral:** die drei Dateien im
  Ordner `Dessert` sind BYTE-IDENTISCH mit den drei alten (per sha1 geprüft — `Ground_Desert.jpg`
  IST `wüste-boden.jpg`), und der über das Biom aufgelöste Pfad rendert auf allen drei Karten
  **pixelidentisch** zum direkt gereichten alten Pfad. Die Umstellung der AUFLÖSUNG ist damit
  unsichtbar. **Der Kachel-Blend-Fix darunter ist die eine bewusste Ausnahme** — er hellt jedes
  Terrain-Footprint auf, auch im Desert-Biom (Kontrast dort 80 → 43, weiterhin klar lesbar; im
  Bild geprüft, nicht nur gerechnet).
- **Die TABELLE entscheidet, die DATEINAMEN werden GEFUNDEN.** `BIOMES` trägt nur, was eine
  Entscheidung ist: welche Biome es gibt, wie sie auf dem Knopf HEISSEN und in welcher Reihenfolge.
  Keine Dateinamen — die drei gelieferten Ordner widersprechen sich schon untereinander
  (`Light_Cover-Desert.jpg` mit Bindestrich gegen `Light_Cover_City.jpg` mit Unterstrich), und der
  Desert-Ordner heißt **"Dessert"**, während jede Datei darin "Desert" sagt. Stehende Repo-Regel:
  **DER ORDNER GEWINNT** (wie bei den acht Necron- und vier T'au-Sprite-Namen), also wird die ROLLE
  über ihren Dateinamen-PRÄFIX gematcht (`Ground` / `Dense_Cover` / `Light_Cover`) statt neun Namen
  plus einen Tippfehler zu transkribieren. Ein viertes Biom kostet EINE Zeile plus den Ordner.
  Der ANZEIGENAME wird bewusst NICHT so abgeleitet — sonst stünde "DESSERT" auf dem Knopf.
- **Kein Dateisystem in `biomes.py`.** Es beantwortet "welche Biome / welches ist gewählt / welcher
  Ordner"; `sprites.py` beantwortet "und wo liegt dessen Bodenbild", weil dort `SPRITES_DIR` und
  `_EXTENSIONS` schon einmal definiert sind. Hält den Import einseitig (sprites → biomes).
- **`get()` wirft, `current()` nicht** — und das ist Absicht: `get()` ist die Tabellenabfrage
  (Tippfehler soll laut sein, wie `maps.get()`), `current()` läuft auf dem RENDER-Pfad bei jedem
  Neubau der statischen Ebene, wo ein veralteter Settings-Wert die Karte umfärben soll statt das
  Spiel mitten im Frame zu killen.
- **Die Knöpfe sitzen IM Kopfzeilen-Balken, nicht in einer eigenen Zeile darunter** — die
  Kartenvorschauen rechnen ihre Boxhöhe aus dem, was übrig bleibt, eine Zeile darüber würde also
  jedes Brettbild auf dem Schirm schrumpfen. Gemessen: die Überschrift endet bei 382 px, der Block
  ist rechtsbündig und hält selbst bei 1280 px Fensterbreite ~380 px Abstand.
  `tile_screen.header_bar()` ist die dafür extrahierte gemeinsame Rechteck-Definition (zweiter
  Konsument: `draw_header()` und das Hit-Testing im `layout()`).
- **Sie gehören auf DIESEN Screen, weil die Kacheln darunter Bilder des Bretts sind:** ein Klick
  malt alle drei neu, die Wahl wird also durch Hinsehen getroffen statt durch drei Wörter. Deshalb
  sind BEIDE Caches in `map_preview.py` nach `(Karte, Biom)` gekeyt — nach Karte allein täte der
  erste Klick sichtbar nichts.
- **`map_preview._render()` baut jetzt einen FRISCHEN `Renderer` pro Aufruf.** Der geteilte
  Modul-Renderer cacht seine statische Ebene unter einem Schlüssel, der mit `id(board)` beginnt —
  und `board` ist dort ein Local, das beim Verlassen Müll ist. Dieselbe Karte unter einem zweiten
  Biom kann also eine recycelte id bekommen, den Cache-Eintrag des VORIGEN Bioms treffen und den
  falschen Boden blitten. Echte Kollision (gleiche Karte → gleiche Pixelmaße) und probabilistisch,
  also die schlimmste Sorte.
- **Der Screen schreibt `config.BIOME` beim Klick**, und das ist NICHT die Regel, die
  `map_preview.py`s Docstring aufstellt: verboten ist, dass eine VORSCHAU die Brettmaße schreibt,
  also das Schlachtfeld allein durch Angesehenwerden entscheidet. Hier entscheidet nichts durchs
  Ansehen, nur durchs Klicken — und ein Biom entscheidet ohnehin nichts am Spiel. Live geschrieben
  ist außerdem das, was die Kacheln antworten lässt: es gibt EINE Antwort auf "welches Biom", keine
  gewählte und eine gezeichnete.
- **`--biome` überspringt den Kartenscreen NICHT** (anders als `--map`): `--map` beantwortet dessen
  Frage, ein Biom ist eine zweite, kosmetische Einstellung, die derselbe Screen mitträgt.
- **Der ausgewählte Knopf wird PRESSED gezeichnet** (`button_style`s Active-Palette) — ein
  Drei-Wege-Umschalter, bei dem immer einer an ist, und "pressed" ist genau der Zustand, den der
  geteilte Knopf dafür schon hat. Sonst hat nichts auf diesem Screen einen bleibenden Zustand, es
  kann also nicht mit Hover verwechselt werden.
- **Eine maskierte Kachel wurde ZWEIMAL geblendet — vorbestehender Renderer-Fehler, den erst die
  neue Kunst sichtbar gemacht hat** (User: "Light_Cover_City.jpg sieht man nicht"). Ein GEDREHTES
  Footprint lässt sich nicht per `set_clip()` beschneiden, seine Kacheln laufen deshalb über eine
  Hilfsfläche plus Polygonmaske — und dort wurde `TERRAIN_TILE_ALPHA` erst beim Blitten auf die
  transparente Hilfsfläche (also gegen deren SCHWARZ, was abdunkelt) und dann noch einmal beim
  Zurückblitten angewandt. Gemessen an einer 200-grauen Vollton-Kachel über 60-grauem Boden:
  **154 statt der beabsichtigten 170**, also 16 der 110 Kontrastpunkte verloren. Bei den
  Wüstentexturen jahrelang unsichtbar (Boden 231 gegen Cover 116/167); die City-Kunst liegt in der
  QUELLE nur ~27 Punkte auseinander, dort war es also mehr als die Hälfte. **Der Fix lässt `alpha`
  in der MASKE mitreiten** (Kacheln deckend auf die Hilfsfläche, Maskenpolygon mit `alpha` statt
  255) — ein Schritt, exakt die Arithmetik des Clip-Pfades. Gemessen am Brett: City-Light-Cover
  Kontrast **8.1 → 20.9**, Dense **3.5 → 11.1**. `tile.set_alpha()` wird jetzt pro Pfad EXPLIZIT
  gesetzt bzw. gelöscht, weil die Kachel-Surface zwischen allen Aufrufen desselben Pfades geteilt
  ist. Vier neue Prüfungen in `test_ground_texture.py`, A/B belegt (4 von 38 kippen, und die
  Meldung nennt die 154).
- **Mittlerer Farbabstand ist ein GROBER Näherungswert für "sieht man es"** — Forest-Light-Cover
  misst 6.0 und ist am Bildschirm trotzdem deutlich (dunkles Holz auf moosigem Boden: das MUSTER
  trägt, nicht die mittlere Helligkeit). Deshalb wurde jedes Biom auch angesehen und nicht nur
  gerechnet.
- **Das Log nennt Karte UND Biom in einer `[setup]`-Zeile** (`file_only`): die Karte ist aus den
  Terrain-Koordinaten rekonstruierbar, das Biom aus gar nichts — ohne die Zeile lässt sich ein
  Screenshot in einem Bericht keinem Lauf zuordnen.
- **Getestet:** neu `test_biomes.py` (**87/87**, fünf Abschnitte) plus **neun A/B-Sonden** an der
  QUELLE, jede kippt genau ihre eigenen Prüfungen; dazu vier Prüfungen und eine Sonde für den
  Blend-Fix in `test_ground_texture.py` (**38/38**, neutralisiert 34/38). **Zwei bissen zuerst
  NICHT, beide Fehlerklasse 24
  (Befund über den TEST):** die "der gewählte Knopf ist heller"-Prüfung mittelte über den ganzen
  Knopf und maß damit die TEXTMENGE ("DESERT" hat mehr Tinte als "CITY"), bestand also mit
  fest verdrahtetem `pressed=False`; und die "BIOME steht da"-Prüfung zählte die akzentfarbene
  Trennlinie am Balkenboden mit, die `draw_header()` über die volle Breite zieht. Beide messen jetzt
  einen textfreien HINTERGRUND-Punkt gegen `button_style`s Paletten-Konstanten bzw. nur das
  y-Band des Knopfes. `test_ground_texture.py` wurde zu Recht rot (seine Pins nannten die
  verschobenen Dateien) und ist nachgezogen; es fixiert jetzt ein Biom und prüft weiter nur die
  ZEICHENregeln. Volle Regression **153 Suiten, ~12797 Prüfungen, 152 grün / 0 rot / 1 bekannt**,
  alle sechs Smokes plus drei `--neutralize`-Gegenproben, und `selfplay.py map2` unter JEDEM der drei
  Biome (je 1500 Frames, exit 0).
- **Im ECHTEN Spiel belegt:** `smoke_setup_screens.py` klickt jetzt ZUERST einen Biom-Knopf und dann
  erst die Kartenkachel, durch `main()`s echte Schleife — `forest` gegen das per Default gesetzte
  `desert`, ein Bestehen kann also nicht von den Defaults kommen. Es prüft nicht nur die Einstellung,
  sondern **wo der Renderer sein Bodenbild wirklich herliest** (Ordner `Forest`), und dass der
  Biom-Klick den Screen NICHT beendet — genau das Risiko, zwei Arten von Knöpfen auf einen Screen zu
  legen. 11/11 → **13/13**; `--neutralize` weiterhin rot (0/13). Er klickt nach KEY, nicht nach
  Position, hat das vierte Biom also gratis überlebt.

## Das Arena-Biom (game/arena_biome.py)

**Das vierte Biom wird GERENDERT statt fotografiert** (User: "ich bin unzufrieden mit dem aussehen
der maps ... dort besteht die map nicht aus sprites, sondern du renderst sie. sie soll aussehen, wie
eine simulations arena. ähnlicher look wie das interface. eventuell mit leichten farbverläufen oder
ein ganz subtiles kariertes muster. natürlich dann unterschiedlich: boden, dense cover, light
cover") — und ist auf Nachtrag der **DEFAULT** ("und dann mach arena biom bitte als default").

- **`config.BIOME` UND `biomes.DEFAULT_BIOME` stehen beide auf `arena`, und das ist Absicht.** Die
  zwei beantworten verschiedene Fragen ("womit starten wir" / "was tun wir mit einem unbekannten
  Wert"), aber die richtige Antwort ist dieselbe: ein veralteter Settings-Wert soll auf dem Brett
  landen, das das Spiel normalerweise zeigt, nicht auf einem anders aussehenden. Im Test gegen
  EINANDER gepinnt, nicht gegen ein Literal.
- **Die alte Begründung für `desert` ist nicht verschwunden, sondern umgezogen.** Sie lautete: die
  drei Desert-Dateien sind byte-identisch mit denen, die früher lose in `Sprites/` lagen, ein
  unangetastetes Setup rendert also exakt das Vor-Biom-Bild. Das gilt UNVERÄNDERT für das
  Desert-BIOM und wird weiter geprüft — `test_biomes.py` Abschnitt 4 setzt das Biom dafür selbst,
  hängt also nie am Default. Nur "was ein unangetastetes Setup öffnet" ist jetzt etwas anderes.

- **Es beantwortet DIESELBEN drei Rollen, nur mit Code.** `sprites.*_texture_path()` gibt für dieses
  Biom `None` — und das ist **nicht** dasselbe `None` wie "Kunst fehlt", auf das der Renderer mit
  einem Flachfüller antwortet. Deshalb fragt der Renderer `is_procedural()` VOR dem Pfad; der Guard
  steht zusätzlich in `_biome_texture_path()`, weil sonst `os.path.join(..., None)` kracht.
  Der Fehlerfall wäre besonders unauffällig: `config.BACKGROUND_COLOR` ist selbst ein dunkles
  Blaugrau, ein unverdrahtetes Arena-Biom sähe also aus wie ein plausibles dunkles Brett —
  deshalb prüft der Test das GITTER, nicht die mittlere Farbe.
- **DREI Nähte im Renderer, jede an `biomes.is_procedural()`**: `_draw_ground()`, das neue
  `_cover_tile(role, board)` und der Wand-Zweig. `_tile_texture()` nimmt jetzt die FERTIGE Kachel
  statt eines Pfades — woher eine Kachel kommt, ist eine eigene Frage mit zwei Antworten, das
  Wrapping/Origin-Alignment/der Masken-Blend sind dieselben. Damit erbt der gezeichnete Pfad den
  hart erkämpften Masken-Alpha-Fix, statt ihn zu duplizieren.
- **REICHT bis auf die Wände, und das ist gemessen statt angenommen.** DENSE-Terrain ist gar keine
  der drei Rollen — es wird in jedem Biom als EIN flaches `OBSTACLE_COLOR` gezeichnet, was
  funktioniert, weil alle drei Fotoböden HELL sind. Auf einem dunklen nicht: Kontrast zum offenen
  Boden **Desert 137, Forest 30, City 22 — Arena mit der geteilten Farbe 11.8**, der schlechteste
  der vier um die Hälfte. Wände blockieren Sichtlinie, sind also das Wichtigste zum Ablesen; die
  Arena malt sie deshalb selbst (`draw_wall()`: Körper plus helle Kante, wie die HUD jedes solide
  Ding zeichnet). **Danach 60.1.** Die Testschranke ist keine Zauberzahl, sondern das SCHLECHTESTE,
  was die ausgelieferten Fotobiome schaffen, im Test selbst berechnet.
- **Die drei Rollen trennen sich über MUSTER zuerst, HELLIGKEIT zweitens** — nicht über Farbton:
  Boden flaches Gitter, Dense Cover ein ORTHOGONALES Plattenraster (am hellsten), Light Cover
  DIAGONALE Schraffur (dunkler, dünner). Zwei unabhängige Achsen, also übersteht die Trennung
  sowohl Farbenblindheit als auch den `TERRAIN_TILE_ALPHA`-Blend. Gemessen: Dense/Boden 32.9,
  Light/Boden 15.3, Light/Dense 17.6 — alle besser als die entsprechenden City- und Forest-Werte.
- **Die Kacheln müssen WRAPPEN**, weil der Renderer sie am Brett-Ursprung ausrichtet: jede Linie
  wird nur an der OBEREN/LINKEN Kante gezogen (die andere Hälfte liefert die Nachbarkachel), und
  die Schraffur-Steigung TEILT die Kachelgröße. Im Test an einem echten Dreier-Streifen geprüft:
  keine doppelt breite Naht-Linie, und die Diagonale wiederholt sich über die Naht ohne einen
  einzigen abweichenden Pixel.
- **Die Arena wählt ihre EIGENE Kachelgröße (3.0")** statt `DENSE_COVER_TILE_SIZE_IN` (4.5")
  wiederzuverwenden: die Renderer-Werte wurden gewählt, damit FOTOGRAFIERTE Pflastersteine
  glaubwürdig groß herauskommen — ein gezeichnetes Raster hat keine solche Vorlage. 3" ist eine
  ganze Zahl 1"-Zellen, jede Plattenkante landet also AUF einer Gitterlinie; 4.5" läge eine halbe
  Zelle daneben (im Test von beiden Seiten gepinnt).
- **Alles in ZOLL, nichts in Pixeln** — das ist der eigentliche Gewinn gegenüber einem vierten
  Bilderordner: dasselbe Gitter auf der Kartenvorschau (~11 px/Zoll) wie im Spiel (~62 px/Zoll),
  im Test an beiden Auflösungen gemessen. Und das Gitter IST das Lineal: 1" (Kohärenz, halbe
  Engagement Range) und 6" (der Mittelkreis, den der Renderer ohnehin zeichnet).
- **Die Palette ist an der HUD verankert, nicht daneben gewählt**: `GROUND_BASE` ist
  `button_style.BOX_BG_COLOR`, `GRID_COLOR` ist `BORDER_NORMAL`, `EDGE_COLOR` ist `BORDER_HOVER`.
  `button_style` wird bewusst NICHT importiert (es liegt unter `game/ui/` und zieht den Panel-Stack
  mit; dieses Modul läuft auf dem Render-Pfad) — die Werte stehen mit ihrer Quelle daneben und
  werden im Test GEGEN `button_style` gepinnt, was das Einzige ist, was der Import gekauft hätte.
- **Die Modelle lesen sich darauf nicht schlechter** — das Risiko eines DUNKLEN Bodens, denn eine
  Base ist nur ein farbiger RING ohne Füllung. Gemessen: eigener Ring 116 (Arena) gegen 117
  (Desert), Gegner 76 gegen 73. Als Prüfung gepinnt, weil "die Modelle verschwinden" genau von hier
  käme.
- **Kosten:** Boden 65 ms (map2) / 121 ms (map1) gegen 36 ms für den Fotopfad, EINMAL je Brettgröße
  (nach Pixelgröße gecacht, weil `map_preview` pro Render ein Wegwerf-`Board` baut). Die statische
  Ebene ist ohnehin pro Szene gecacht.
- **Getestet:** neu `test_arena_biome.py` (**58/58**, sechs Abschnitte) plus **13 A/B-Sonden** an
  der QUELLE, jede kippt genau ihre eigenen Prüfungen; die `is_procedural()`-Sonde kippt LAUT (der
  `os.path.join(..., None)`-Guard). `test_biomes.py` 87 → **97/97** (die "jedes Biom liefert drei
  Dateien"-Schleifen gehören jetzt `PHOTO_KEYS`, und die Arena bekommt die Gegenprobe: sie liefert
  KEINE). `test_ground_texture.py` **38/38** an der neuen `_tile_texture`-Signatur nachgezogen.
  Volle Regression **155 Suiten, ~13562 Prüfungen, 154 grün / 0 rot / 1 bekannt**, alle fünf Smokes
  und `run_tests.py --smoke` komplett grün. **Im ECHTEN Spiel belegt:** `selfplay.py` unter
  `BIOME = "arena"` auf map2 (2500 Frames) und map3 (800 Frames), beide exit 0.
- **VIER eigene Sondenfehler, alle von der Sonde selbst gefunden** — und drei davon sind
  Fehlerklasse 24 in Reinform:
  1. Der Checker-Vergleich prüfte gegen die MODULKONSTANTE, also bewegte die Sonde beide Seiten:
     mit `GROUND_CHECKER_LIFT = 0` blieb die Suite grün. Beide Schranken werden jetzt am BILD
     abgelesen. Zweites Mal dieselbe Tautologie in diesem Repo (siehe T'au-Enhancements).
  2. Die erste Checker-Messung verglich zwei BENACHBARTE 6"-Zellen und maß damit den Gradienten
     mit (1.47 statt 5). Die richtige Isolation sind zwei an der Brettmitte GESPIEGELTE Zellen —
     gleicher Gradient, andere Parität. Danach exakt 4.95/Kanal.
  3. Die Gitter-Erkennung benutzte EINEN Helligkeitsschwellwert für die ganze Zeile — die
     Mittenaufhellung macht dieselbe Linie in der Brettmitte ~18 Punkte heller als am Rand, ein
     fester Schnitt beantwortet also an beiden Enden verschiedene Fragen. Jetzt Linie gegen ihre
     eigene Nachbarlücke.
  4. Die 45°-Prüfung rotierte die Zeile in die FALSCHE Richtung und schlug gegen einwandfreie
     Kunst fehl. Eine verkehrte Richtung sieht hier genauso aus wie ein kaputtes Muster.

## Spielerfarbe zurück auf GRÜN (game/renderer.py)

**`OWN_ARMY_COLOR` ist wieder (40, 200, 60)** (User: "ändere die spielerfarbe von spieler 1 wieder
zu grün. blau kann man schlecht erkennen auf blauem grund"). Der frühere Wechsel auf Blau
(60, 120, 240) war eine eigene User-Entscheidung und wird zurückgenommen, weil das ARENA-Biom —
inzwischen der DEFAULT — erst DANACH kam und den Boden mit einem BLAUEN Gitter zeichnet.

- **Der Befund ist die dokumentierte GRENZE des Mittelfarben-Proxys in Reinform.** Gegen den
  arena-BODEN misst das blaue Ring 115.4 und das grüne nur 75.4 — der Proxy nennt also BLAU das
  bessere von beiden, und genau deshalb blieben `test_arena_biome.py`s Ring-Prüfungen grün, während
  niemand seine Modelle fand. Gegen die GITTERLINIE, unter der ein Ring dort wirklich liegt, ist
  Blau **21.7** entfernt bei IDENTISCHEM Rotkanal (60 gegen 60), Grün **71.7**. Gleicher Farbton wie
  die Linien, auf denen es liegt: das ist "blau auf blauem Grund", und keine Boden-gegen-Ring-Zahl
  kann es sehen.
- **75.4 auf diesem Boden ist exakt der Wert von `ENEMY_ARMY_COLOR`** — ein Ring, der dort schon als
  lesbar akzeptiert ist. Und Grün liegt WEITER von `SELECTED_MODEL_COLOR`s Cyan (85.0) als das Blau,
  das es ersetzt (58.3) — dieser Abstand war die einzige Begründung des alten Kommentars für Blau.
- **Die Prüfung, die den Fehler gefangen HÄTTE, ist neu**: jeder Team-Ring muss auch von
  `arena_biome.GRID_COLOR` weg sein (> 40). A/B belegt — mit dem alten Blau nennt sie die Meldung
  wörtlich (`22 from GRID_COLOR`).
- **Die zweite Ring-Prüfung war relativ zum WÜSTEN-Boden formuliert und damit schief:** sie verlangte
  MEHR von einem Ring, der zufällig weit von Wüstensand entfernt liegt. Grün erreicht auf dem
  Arena-Boden dieselben 75 wie das Rot, das dieselbe Prüfung akzeptiert, und wäre allein daran
  gescheitert, auf Sand 88 zu erreichen. Die Schranke ist jetzt das SCHLECHTESTE Ring/Boden-Paar der
  drei fotografierten Biome, im Test berechnet — dieselbe Form wie die Wand-Schranke darüber.
- **Getestet:** `test_arena_biome.py` **60/60**. Volle Regression **162 Suiten, ~14273 Prüfungen,
  161 grün / 0 rot / 1 bekannt**, dazu `smoke_pregame.py map2`, `smoke_log_input.py map2` und
  `selfplay.py map2` — keine Formalie, weil `game/renderer.py` pro Frame läuft.

### Und sie WECHSELN NICHT MEHR: Player 1 grün, Player 2 rot, konstant

**`_token_color()` hing an `turn_tracker.active_player`, die zwei Armeen TAUSCHTEN also die
Farben** (User: "Die Farben der Spieler sollen nicht mehr wechseln, je nachdem wo der Fokus ist.
Sie sollen konstant bleiben. Spieler 1 - grün, Spieler 2 - rot").

- **Das ist kein seltenes Ereignis, und genau darin liegt der Fehler.** `game/turn.py` schreibt
  selbst aus, dass `active_player` ein transientes "wessen Entscheidung ist das gerade" ist — es
  flippt bei JEDEM Verteidiger-Save und jedem reaktiven Stratagem, und nur `turn_owner` trägt
  "wessen Zug". Das Brett wechselte also zweimal pro Schussangriff die Farbe, und das Einzige,
  wofür ein Ring da ist — die zwei Armeen auseinanderhalten — war das Erste, was ausfiel. Die
  laufende `turn_owner`-vs-`active_player`-Konvention oben in Teil 1 ist die Diagnose; hier ist
  sie einmal als Zeichnung aufgetreten.
- **`TOKEN_TEAM_COLORS` ist nach OWNER gekeyt, genau wie `DEPLOYMENT_ZONE_LINE_COLORS`** — das war
  schon immer so gebaut und sagt dieselben zwei Wörter. Die zwei stimmten vorher nur in den Frames
  überein, in denen der Fokus zufällig bei Player 1 lag; jetzt immer.
- **Der Parameter ist ENTFERNT, nicht ignoriert** (`Renderer.draw()`, `_draw_tokens()`,
  `draw_embarked_passengers()`, `_draw_embarked_icon()`, `_token_color()`). `draw()` wird
  positionell gerufen — ein toter Parameter mitten in der Signatur ist Fehlerklasse 22, die auf
  ihren Träger wartet. Sechs Aufrufstellen nachgezogen (zwei in `main.py`, zwei Messskripte; zwei
  weitere reichten ihn schon per Keyword).
- **Im ECHTEN Spiel belegt, und das ist der eigentliche Beweis:** ein Spion an `_token_color()`
  über 1200 Frames `selfplay.py map2` meldet für Player 1 **genau eine** Farbe (40,200,60) und für
  Player 2 **genau eine** (220,40,40). **A/B im echten Spiel mit dem alten Rumpf: BEIDE Spieler
  bekommen BEIDE Farben** — das gemeldete Verhalten, über denselben Lauf.
- **Getestet:** neu `test_player_colors.py` (**23/23**) plus `ab_player_colors.py` (**5 A/B-Sonden,
  alle beißend**; die ganze Vor-Fix-Welt kippt 7 von 23). **Vorher pinnte NICHTS das Verhältnis von
  Ring zu aktivem Spieler** — `test_arena_biome.py` und `test_token_base_fill.py` fassen diese
  Farben an, reichen aber beide ein fest verdrahtetes `"Player 1"`, konnten einen Tausch also gar
  nicht sehen. Die Prüfungen ankern bewusst an den zwei GESPROCHENEN Wörtern (Grünkanal dominiert /
  Rotkanal dominiert), nicht an `TOKEN_TEAM_COLORS` selbst — sonst bewegte eine Sonde beide Seiten
  des Vergleichs und die Tabelle dürfte zwei identische Grautöne enthalten.
- **Gemeinsame Regression dieser drei Änderungen** (Farben, Auswahl-Kasten im Panel, Volks-Grid):
  **173 Suiten, ~15205 Prüfungen, 172 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett
  grün, dazu `smoke_measure_tool.py`, `smoke_end_turn_warning.py`, `smoke_primary_mission.py`,
  `smoke_pregame.py map1`, `smoke_setup_screens.py` (+`--neutralize` weiter rot) und `selfplay.py`
  auf map2 und map3. Keine Formalie: `game/renderer.py` und `game/ui/action_panel.py` laufen beide
  pro Frame.
