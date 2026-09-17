# Status-Panels und Farbcodes

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die Fraktions-Badges (game/ui/faction_badge.py, game_status_panel, turn_start_overlay)

**Das Zug-Banner trägt jetzt auch das Fraktionslogo** (User: "es gibt ja den promt, der anzeigt,
wer jetzt am zug ist. 'Player 2, Turn 1' baue dort bitte auch das fraktions Logo ein").

- **29. Extraktion am zweiten Konsumenten:** „wie sieht eine Fraktionskachel aus" (Rahmen,
  Aktiv-Glow, Kunst, Monogramm-Rückfall, Schriftsuche) lag im Game-Status-Panel, solange es die
  einzige Stelle war, die eine zeichnet. Das Panel **re-exportiert** jede Konstante, `_faction_monogram`
  IST jetzt `faction_badge.monogram`, und `_draw_badge`/`_monogram_font` delegieren — seine
  Pixel-Tests sind damit per Konstruktion unverändert (63/63 ohne eine Anpassung).
- **Die Kachel-RECT kommt vom Aufrufer, nicht eine Größe.** Panel 58 px (für eine 200-px-Spalte
  bemessen), Banner **76 px** — es steht in der Bildschirmmitte, hat 460 px zur Verfügung und ist
  einen Klick lang zu sehen. Nur die SCHRIFT wird gesucht, eine größere Kachel kostet also nichts.
- **ÜBER der Überschrift und zentriert, nicht daneben:** `draw_panel_header()` zeichnet eine
  Leiste über die volle Boxbreite, es gibt also keine Seite, auf die eine Kachel passt, ohne sie
  zu überlagern oder die Leiste kürzer zu machen als jede andere Überschrift im Spiel. Die
  Überschrift wird verschoben, indem ihr ein Rect gereicht wird, das UNTER der Kachel beginnt —
  `draw_panel_header()` muss nichts von Badges wissen.
- **Reserviert wird nur, was auch etwas zeigt** (`faction_badge.has_content()`): eine handgebaute
  Squad hat kein Datenblatt und damit keine Fraktion, und ein leeres gerahmtes Quadrat liest sich
  als Kunst, die nicht geladen hat. Ohne Fraktion ist das Banner exakt so hoch wie vorher.
- **`dismiss()` lässt Keyword UND Pfad los.** Sonst trüge das NÄCHSTE Banner — der Zug des anderen
  Spielers — das Wappen der falschen Armee. Eigene Testzeile, eigene A/B-Sonde.
- **`active=True`**, weil das Banner GENAU EINEN Spieler nennt und es seiner ist. Das Panel reicht
  dieselbe Flagge für die transiente „auf wen wartet das Spiel"-Frage — zwei Fragen, je eine
  Antwort pro Aufrufer, und genau deshalb bekommt `faction_badge.draw()` sie übergeben statt sie
  abzuleiten.
- **EINE Ableitung von „wer spielt welches Volk"**, `main.py`s `current_player_factions()`, gelesen
  vom Panel UND vom Banner. Zwei Kopien sind der Weg, auf dem die eine mit einem halbfertigen
  Vorspiel-Roster antwortet, während die andere sich längst gesetzt hat.
- **Getestet:** neu `test_turn_start_overlay.py` (**36/36**, fünf Abschnitte) — **zu diesem Overlay
  gab es vorher GAR KEINEN Test**. Gemessen auf PIXELN statt gegen die Konstanten, die das Layout
  erzeugt haben: die Box wächst wirklich um den reservierten Block, die Tinte liegt IN der Kachel
  und zentriert, die Überschrift liegt DARUNTER, und ein Volk ohne Kunst bekommt sein Monogramm.
  Plus `ab_turn_start_badge.py` (**10 A/B-Sonden, alle beißend**), das beide Suiten fährt — eine
  Änderung am geteilten Modul, die nur einer der zwei Aufrufer bemerkt, ist genau die Drift, gegen
  die die Extraktion gebaut ist.
  - **Ein Befund über den TEST:** die Sonde „der Logopfad wird nie nachgeschlagen" biss ZUERST
    NICHT — nichts unterschied KUNST von MONOGRAMM (beides ist Tinte in der Kachel, und zwei Völker
    unterscheiden sich so oder so). Jetzt wird dasselbe Volk zweimal gerendert und ihm einmal nur
    die Kunst weggenommen.
- **Im ECHTEN Spiel belegt:** `verify_turn_badge.py` fährt `selfplay.py`s echte `main()`-Schleife
  und meldet `Player 1 -> faction 'AELDARI', art 'Aeldari Logo.png'`, `Player 2 -> 'NECRONS',
  'Necron Logo.png'`, Kachel **76 px, artwork=True**. `--neutralize` meldet `faction None, art
  None` und **0 gezeichnete Kacheln**. Nichts wird dafür gestellt — das Banner öffnet zu Beginn
  jedes Spielerzuges von selbst, also ist das der seltene Fall, der PASSIV messbar ist.

### Die Badge-Zeile im Game-Status-Panel

**Sie hängt an der bekannten FRAKTION, nicht mehr an vorhandener KUNST** (User, mitten
in einer Aeldari-gegen-Death-Guard-Partie: "das rechte panel sieht wieder zurückgesetzt aus. das
hatten wir mal überarbeitet ua. mit logos der fraktionen").

- **Es war nichts verloren — es war das Alles-oder-nichts-Tor.** `_badge_row()` verlangte von BEIDEN
  Spielern eine Logodatei und ließ sonst die GANZE Gruppe auf ihre Vor-Umbau-Textform zurückfallen.
  Death Guard war die eine gebaute Fraktion ohne Badge, also nahm **ein fehlendes Bild** den goldenen
  Aktiv-Rahmen und die kompakten CP/VP/BF-Spalten mit — beides hat mit Logos nichts zu tun.
  **Reproduziert vor jeder Änderung:** aeldari vs necrons/orks/tau → Badges; aeldari vs death_guard →
  `None`, alte Darstellung. Der Sprite-Ordner-Umzug war NICHT schuld (`_resolve_path()` durchsucht
  die Fraktionsordner, alle vorhandenen Logos lösten auf).
- **Eine Fraktion ohne Kunst bekommt jetzt eine MONOGRAMM-Kachel** (`_faction_monogram()`), gleicher
  Rahmen, gleiche Größe, gleicher Aktiv-Highlight. Die alte Begründung ("eine halb gefüllte Zeile
  liest sich schlechter als die Zeile, die sie ersetzt") galt einer LEEREN Kachel — eine beschriftete
  ist weder leer noch halb gezeichnet, also war das nicht der abgewogene Handel.
- **Immer ZWEI Zeichen**, damit die zwei Kacheln symmetrisch bleiben, egal welche die Kunst
  vermisst: Initialen bei mehreren Wörtern (`DEATH GUARD` → `DG`, `T'AU EMPIRE` → `TE`), die ersten
  zwei Buchstaben bei einem (`AELDARI` → `AE`). Eine einzelne Initiale war die naheliegende erste
  Form und liest sich als Tippfehler.
- **Ein fehlendes KEYWORD lässt die Zeile weiter fallen**, und aus dem einzigen Grund, der bleibt:
  dann gibt es nichts zu zeichnen UND nichts zu schreiben, die Kachel wäre wirklich leer. Das ist der
  Fall einer handgebauten `Squad` ohne Datenblatt.
- **Die Schriftgröße wird GEMESSEN, nicht aus der Kachelhöhe abgeleitet** — ein fettes Zweizeichen-
  Wort ist breiter als hoch, eine nur an der Höhe gewählte Größe liefe seitlich über den Rahmen.
  Gecacht, weil das auf dem Zeichenpfad läuft.
- **Death Guards Logo kam noch in derselben Sitzung** (`Deathguard_Logo.png`) — **der Ordner
  gewinnt** wie überall in `sprites.py`: ein Wort mit Unterstrich, wo die anderen vier
  `<Fraktion> Logo` heißen. Damit ist der Platzhalter **von keinem ausgelieferten Roster mehr
  erreichbar** — ein belegter No-op, der als Netz für die nächste Fraktion stehen bleibt und deshalb
  an einem KONSTRUIERTEN Fall geprüft wird.
- **Zwei Befunde über den TEST (Fehlerklasse 24), beide von den eigenen Sonden:**
  1. „jede Fraktion hat Kunst" war über `FACTION_LOGO_KEYS`' EIGENE Schlüssel formuliert und damit
     eine TAUTOLOGIE — den Death-Guard-Eintrag zu löschen ließ die Suite grün, weil das gelöschte
     Keyword dann gar nicht mehr geprüft wird. Gefragt wird jetzt die ARMEELISTE (`ArmyList.
     faction_keyword`), also „kann eine Fraktion, die dieser Build FIELDEN kann, ein Monogramm
     zeigen". Eine sechste Liste ohne Kunst macht die Zeile rot und nennt die Fraktion.
  2. Die Vor-Fix-Sonde ließ die Suite ABSTÜRZEN statt rot zu werden (Indizieren in ein `None`
     gewordenes Row) — **dritte Instanz** derselben Lehre wie die zwei `str.index()`-Wächter.
     Jetzt über eine gepolsterte Kopie, also 55/62 mit sieben namentlichen Fehlern.
- **Getestet:** `test_faction_badges.py` 47 → **62/62** plus **vier A/B-Sonden an der QUELLE**, jede
  kippt ihre eigenen Prüfungen (Tor zurück auf KUNST → 55/62 und die Meldung wörtlich zurück;
  Monogramm nie geblittet → 61; Monogramm auf ein Zeichen → 58; Death-Guard-Eintrag entfernt → 61).
  Zwei fremde Pins sind zu Recht rot geworden und umgedreht — genau die sichtbare Einzeiler-Änderung,
  für die sie gesetzt waren (`test_army_select.py`s `LISTS_WITHOUT_ART` ist jetzt LEER und bleibt als
  Platz für die nächste Fraktion stehen; `test_death_guard_datasheets.py` prüft die DATEI samt ihrer
  abweichenden Schreibweise). Volle Regression **164 Suiten, ~14401 Prüfungen, 163 grün / 0 rot /
  1 bekannt**, alle acht Smokes exit 0.
- **Im ECHTEN Spiel belegt, nicht nur im Test** — das Panel läuft pro Frame in der Renderkette, und
  „gebaut, aber nie GEFÜTTERT" hat dieses Repo sechsmal getroffen: ein Spion an `_draw_badge()` in
  einem echten `selfplay.py map2`-Lauf mit der GEMELDETEN Paarung meldet **2998 Zeichnungen über 1500
  Frames**, beide Fraktionen mit Kunst, und der Highlight wandert zwischen ihnen. Der
  Monogramm-Pfad ebenso, mit zur Laufzeit entferntem Death-Guard-Eintrag: 1598 Zeichnungen, Zeile
  steht, `DEATH GUARD` als Monogramm-Kachel.
  **Harness-Falle dabei:** `import selfplay` führt NICHTS aus (`if __name__ == "__main__"`), der
  Spion meldete erst ein wahrheitsgetreu aussehendes 0 für eine Partie, die nie stattfand — `runpy`
  mit `run_name="__main__"`.

#### Und die Kacheln sind groesser: LOGO_BOX 58 -> 72 (2026-09-11)

**Gemeldet:** *"mach die faction logos ingame in der rechten spalte etwas groesser."*

- **Den Platz hatte der RUNDENZAEHLER hinterlassen.** Die zwei Kacheln hugen die Kanten des
  Inhaltsbereichs, und der Balken dazwischen fuellte frueher die Mitte; seit er in den
  Fortschrittsbalken am oberen Brettrand gewandert ist, standen dort **84 px tote Flaeche**. 72
  laesst 56 davon stehen — weiter klar zwei Kacheln statt eines Paars — und vergroessert die KUNST
  von einem 50-px- auf ein 64-px-Quadrat (`LOGO_BOX - 2 * LOGO_PADDING`).
- **Die DECKE ist das Zug-Banner, nicht diese Spalte.** `turn_start_overlay.BADGE_BOX` (76) ist
  bewusst das groessere der beiden — Schaukasten in der Bildschirmmitte mit 460 px gegen eine
  Referenzkachel in einer 200-px-Spalte — und `test_turn_start_overlay.py` pinnt die Ordnung. Die
  zwei liegen jetzt enger beieinander; die ORDNUNG ist die Design-Aussage, nicht die Marge, und
  wer die Panel-Kachel weiter wachsen laesst, muss das Banner mitziehen. Steht an BEIDEN
  Konstanten.
- **Alles Uebrige ist GEMESSEN und hat Luft:** die zwei „see rules"-Links werden WEITER (sie sind
  unter ihrer eigenen Kachel zentriert, ein breiterer Tile schiebt ihre Mitte von der Panelkante
  weg — 29 → 36 px Halbbreite), das lange Label passt weiterhin nicht (83 > 72), also aendert sich
  die Beschriftung nicht; und die 14 px, die die Gruppe waechst, kosten den Log-Streifen auf einem
  1080er Schirm **nichts** (er bleibt bei vollen 480) und lassen ihm auf einem 720er noch 212 px.
- **Der MONOGRAMM-Rueckfall musste mitwachsen, sonst waere die Zusicherung des Moduls still falsch
  geworden.** `faction_badge.py`s Docstring sagt „only the FONT is searched to fit, so a bigger
  tile costs nothing here" — das gilt nur, solange die Suche Kopfraum hat.
  `MONOGRAM_FONT_SIZES` endete bei 44 und war **schon bei der alten 50-px-Innenbox die Antwort**,
  also bekamen beide Kacheln 48x30 Lettern, egal wie viel Platz sie hatten. 56/52/48 davor; beide
  lebenden Boxen (Panel 64, Banner 68) waehlen jetzt 56.
  **NICHT als inert behauptet, sondern gemessen:** bei einer 50-px-Box wuerde „TE" von 44 auf 48pt
  gehen (46x30 → 50x33, weiter in der Kachel). Kein Aufrufer hat mehr eine 50-px-Box, es rendert
  also nichts davon — aufgeschrieben, weil „diese Eintraege aendern unterhalb X nichts" genau die
  Sorte Satz ist, die angenommen statt geprueft wird.
- **ZWEI Pins in `test_faction_badges.py` waren PROXYS, die den Kopfraum verbraucht hatten, und
  sind auf die BEHAUPTUNG umgestellt.** „Die Spalten ERSETZEN die zwei beschrifteten Gruppen,
  statt sie zu ergaenzen" wurde an der Position des Buttons gemessen — dreimal nachkalibriert
  (Army-Rules-Link dazu, Rundenzaehler weg) und jetzt endgueltig gekippt: die Badge-Form ist
  4 px TALLER als die Lang-Form (288 gegen 284), waehrend sie strikt WENIGER Gruppen zeichnet.
  **Das ist der Stellvertreter, der faellt, nicht die Aussage.** Gezaehlt werden jetzt die
  GRUPPEN-Kaesten (jeder `rect.width - 12` breit, was sie von den Kacheln und ihren Glow-Ringen
  trennt, die durch dasselbe `draw_box()` gehen) — keine kuenftige Kachel- oder Zeilenhoehe kann
  das mehr falsch antworten lassen. A/B belegt (die drei `not score_columns`-Tore entschaerft →
  beide Zeilen rot).
- **Ein VORBESTEHENDER roter Pin derselben Datei ist mitgefixt**, und er ist die Lehre wert: „the
  Ork badge art is drawn in the right tile" nannte die GRUENE Farbe von `Ork Logo.jpg`
  (94, 166, 93). Eine Parallelsitzung hat die Datei durch ein schwarz-braunes `.png` ersetzt
  (`8c13d29`), und die Zeile wurde rot gegen ein Panel, das die Kunst einwandfrei zeichnete — sie
  pinnte EIN BILD, nicht das Verhalten. **Die naheliegende Reparatur ist schlechter:** die
  dominante Farbe des neuen Bildes ist (16, 0, 0), also innerhalb von 40 zur Kachel-Hintergrundfarbe
  — sie koennte Kunst nicht von einem leeren Rahmen unterscheiden, und genau das hat die eigene
  Liveness-Zeile gemeldet. Gemessen wird jetzt die DECKUNG gegen dieselbe Kachel ohne Kunst
  (Kunst 2801 von 3844 px, Monogramm 1134): ein Logo fuellt seine Kachel, zwei Buchstaben nicht,
  und der Monogramm-Wert ist der BODEN statt einer Konstante, also haelt die Aussage bei jeder
  Kachelgroesse. A/B belegt (Kunst-Blit entfernt → rot).
- **Getestet:** `test_faction_badges.py` 64 → **65/65**, `test_turn_start_overlay.py` **36/36**,
  `test_army_rules_overlay.py` **122/122**, `test_game_menu.py` **208/208**. Volle Regression
  **224 Suiten, ~20503 Pruefungen, 223 gruen / 0 rot / 1 bekannt** — der eine vorbestehende
  Fehlschlag ist damit ebenfalls weg. Dazu `selfplay.py map2 1200` (exit 0), weil
  `game/ui/game_status_panel.py` pro Frame in der Renderkette laeuft.

## Der Rundenbalken am oberen Brettrand (game/ui/round_progress_bar.py)

**Die Rundenzahl im rechten Panel ist durch einen Fortschrittsbalken ersetzt**
(User: "für die Anzeige der aktuellen runde hätte ich gerne anstatt der Zahl
einen schönen Fortschrittsbalken am oberen Bildschirmrand. die Phasen können
dort getrennt sein, müssen aber nicht beschriftet sein. aber der Zug soll
beschriftet sein. und das Volk Logo/Farbe muss drin sein").

- **"VOLL" ist die GANZE SCHLACHT** (User-Entscheidung): `BATTLE_ROUNDS` Runden
  × 2 Züge = 10 Zug-Segmente, jedes in seine 5 Phasen unterteilt — 50 Zellen.
  Die Alternative (nur die fünf Phasen DIESES Zuges, Runde als Zahl daneben)
  wurde vorgelegt und abgelehnt: sie sagt nichts darüber, wie weit die Partie
  ist, und genau dafür gibt es einen Fortschrittsbalken.
- **Jedes Zug-Segment trägt die Farbe SEINES Besitzers, und zwar VON ANFANG AN**
  (`TOKEN_TEAM_COLORS`, also dieselben konstanten Brett-Farben — Player 1 grün,
  Player 2 rot), und links steht das Logo dessen, der GERADE dran ist. Auch das
  war die Wahl gegen die ruhigere Variante (alles in der Farbe des
  Zugbesitzers). **Drei Stufen EINES Farbtons** (`cell_color()`): kommend dunkel
  (`UPCOMING_DIM` 0.3), gespielt heller (`PLAYED_DIM` 0.55), laufende Phase voll
  plus Goldrahmen — „wessen" und „wie weit" sind gleichzeitig lesbar. Kommende
  Züge waren zuerst GRAU, der Balken konnte also vor dem Spielen nicht sagen,
  wem welcher Zug gehört (User: "auch von anfang an in den richtigen farben").
  - **Vor dem Erster-Zug-Roll-off bleiben die ZELLEN NEUTRAL (grau), und das ist
    eine Tatsache über `TurnTracker`, keine Stilwahl:** ein Deferred-Start-Tracker
    trägt bis `start_battle()` einen PLATZHALTER-`first_player`. Die Reihenfolge
    schon im Deployment zu färben hieße, eine Ordnung zu zeichnen, die der
    Roll-off einen Moment später umdrehen kann. (Die Rundenzahlen stehen dort
    trotzdem — siehe unten.)
- **Die RUNDE ist beschriftet, nicht der Spieler: "1 2 3 4 5" AUF dem Balken**
  (User, zuletzt: "die farbe reicht als player indikator. ich hätte aber gerne
  den Turncounter als Label über der Leiste nicht den Spieler, also 1 2 3 4 5").
  **Dritte Fassung:** zuerst ein graues 11-pt-"3.2" in einer Zeile UNTER 9 px
  hohen Zellen ("ganz kleine labels unter den zugabschnitten"), dann "P1"/"P2" AUF
  jedem der zehn Zug-Segmente — was zweimal sagte, was die Zellfarbe schon sagt,
  und nie das, was sie nicht sagen kann: welche Runde wo liegt. Die Zellen haben
  weiter die volle Spurhöhe; der laufende Zug steht weiter ausgeschrieben neben
  dem Badge ("ROUND 3 - PLAYER 2", vor Schlachtbeginn "DEPLOYMENT").
  - **EINE Zahl je Schlachtrunde, zentriert über deren ZWEI Zug-Segmenten**
    (`round_spans()`, aus `turn_segments()` gebaut statt ein zweites Mal gelegt).
    Sie steht damit auf der Lücke zwischen erstem und zweitem Zug — der einen
    Stelle der Spur, die keinem Spieler gehört. „Turn" heißt in dieser UI die
    Schlachtrunde (das Zug-Banner liest "Player 2, Turn 1"), daher 1-5 und nicht
    1-10.
  - **Neutrales Hellgrau (`LABEL_COLOR`), nie eine Teamfarbe** — die Farbe der
    ZELLEN ist der Spieler-Indikator. **Die laufende Runde in Header-Gold**,
    demselben Gold wie der Titel, damit "3" und "ROUND 3" als eine Aussage lesen.
    `current_round()` leitet aus `current_turn_index()` ab und erbt dessen
    Klammer: im Frame nach dem letzten Zug bleibt "5" gold, nie eine sechste
    Runde. Dunkler 1-px-Ring bleibt (die Zahl liegt auf Zellen jeder Helligkeit).
  - **Schon im DEPLOYMENT gezeichnet** (alle neutral, keine gold): der Grund, aus
    dem P1/P2 bis zum Roll-off warten mussten, gilt für eine Rundenzahl nicht.
  - **"über der Leiste" ist als AUF gelesen, nicht als eigene Zeile darüber** —
    eine Entscheidung, keine Transkription: eine Zeile über der Spur kostete
    genau die Höhe, die schon zweimal verhandelt ist (Zellen wieder winzig, oder
    `BAR_HEIGHT` aus Brett und Reserves-Panel mit 4 px Rest). Wenn darüber
    gemeint war, ist das die Stelle.
  - **Größe gemessen:** `LABEL_FONT_SIZE = 18` gibt Ziffern von 8×12 px mit 9 px
    Glyphen (bei 12 pt sind es 6 px, nicht größer als die gemeldeten). Eine
    Runden-Spanne ist bei 1280 px 231 px breit; eine zu schmale Spanne bekommt
    keine Zahl statt einer über Zwei-Pixel-Züge geschmierten.
  - `owner_label()`/`label_color()` sind **entfernt**, nicht liegen gelassen
    (Testzeile).
  - **Zentrieren an den Glyphen-Metriken war für P1/P2 gebaut und ist wieder
    raus:** bei 12 bis 20 pt gemessen landet es auf derselben Zeile wie das
    Zentrieren der Textfläche — Code ohne Wirkung.
- **Er hat eine EIGENE ZEILE über die volle Fensterbreite, und Brett wie beide
  Panels beginnen darunter.** Das ist die ZWEITE Antwort auf diese Frage, und
  die erste gehört hierher, weil ihr Fehler nicht offensichtlich ist: der
  Balken war zuerst Chrome ÜBER dem Brett (Brett-Rect unangetastet, die vier
  Steuer am oberen Brettrand bekamen einen verkürzten Rect zum Ausweichen).
  Er war grün getestet und sah auf einem Streifen-Screenshot richtig aus.
  **Gemeldet: "der balken überdeckt die map. das muss nicht sein"** und **"die
  map schließt jetzt nicht mehr links und rechts mit den 2 seiten panels ab"**
  — die Oberkante der Karte lag 34 px unter der der Panels, die drei Spalten
  fluchteten oben also nicht mehr, und der Streifen fraß Karte statt Platz zu
  belegen.
- **Die eigene Zeile behebt beides und ist EINFACHER.** Das Brett-Rect beginnt
  jetzt per Konstruktion unter dem Balken, also gibt es keinen zweiten Rect
  abzuleiten, keine vier Konsumenten umzuhängen — und keine Möglichkeit, dass
  der MENU-Knopf aus dem einen Rect GEZEICHNET und gegen ein anderes GEKLICKT
  wird. `chrome_rect()` ist ersatzlos entfallen; `test_round_progress_bar.py`
  pinnt, dass kein `board_chrome_rect` zurückkommt.
- **Die Höhe kommt zur Hälfte aus der Reserves-Sektion** (User-Vorschlag: "du
  kannst zb die reserves sektion unten etwas kleiner machen") **und zur Hälfte
  aus der Brettspalte.** Gemessen, warum nicht ganz von unten:
  `RESERVES_PANEL_HEIGHT` war 136 und ihr eigener Inhalt braucht
  `HEADER_MARGIN + HEADER_BAR_HEIGHT + 8 + (CARD_PORTRAIT_PX + 2 ×
  CARD_TEXT_PADDING) + HEADER_MARGIN = 122` — also **14 px Luft**. Sie gibt 10
  ab (→ 126, 4 px Rest), der Balken ist dafür auf **28** statt 34 geschrumpft,
  und die Brettspalte trägt die übrigen 18. **Gepinnt wird die LUFT, nicht die
  Zahl**: eine größere Karte dort wird rot, statt still abgeschnitten zu
  werden.
- **`DicePanel` musste dafür seine absolute Verankerung aufgeben.** Es rechnete
  `top_y = PLAYER_BANNER_HEIGHT + DICE_TOP_MARGIN` und las `bounds_rect` nur
  für x/Breite — ein verkürzter Rect hätte es also nicht bewegt. Jetzt
  `max(bounds_rect.y, PLAYER_BANNER_HEIGHT)`, EINMAL berechnet und von der
  Höhenrechnung UND vom Layout gelesen (es waren zwei Ausdrücke für dieselbe
  Zahl). `PLAYER_BANNER_HEIGHT` bleibt als UNTERGRENZE, weil `PlayerBanner`
  seine blockierenden Warnungen über die volle Fensterbreite zieht.
- **`PlayerBanner` darf den Balken überdecken**, und die Zeichenreihenfolge sagt
  das: es beansprucht denselben Streifen, aber nur für "Regaining Coherency"
  und einen fälligen Battle-Shock-Wurf — zwei Dinge, die das Spiel anhalten,
  bis sie beantwortet sind, und die für diesen Moment mehr wert sind als eine
  Fortschrittsanzeige. Sonst zeichnet es gar nichts.
- **Aus dem Panel ist die Rundenzahl ERSATZLOS verschwunden**, samt ihrer
  Kopfleiste: die stand zwischen den zwei Badge-Kacheln, und ohne Text wäre sie
  ein leerer Rahmen gewesen. Die Phasenzeile darunter bleibt. **Folge, gemessen:**
  die Lang-Form (ohne Badges) wird dadurch um eine `SUBHEADER_HEIGHT`-Zeile
  kürzer — und das ist genau die Form, gegen die `test_faction_badges.py` seine
  "die Spalten ERSETZEN die zwei langen Gruppen"-Zeile vergleicht. Der Pin ist
  nachgezogen und sagt jetzt, was wirklich gilt (274 gegen 284 px), statt gegen
  eine Konstante zu messen, die er nicht mehr erreicht.
- **`last_track_rect` / `last_badge_rect` zeichnen auf, was WIRKLICH gelegt
  wurde** (Idiom von `DicePanel.last_backdrop_rect`). Die Spur ist alles, was
  nach Badge und Titel übrig bleibt — wer sie ein zweites Mal herleitet, misst
  einen anderen Rect als den gezeichneten. **Genau daran ist die erste Fassung
  der Suite gescheitert:** sie scannte Badge und Titel mit und meldete
  29 gefüllte Pixel für eine Schlacht, die noch nicht begonnen hatte.
- **Getestet:** neu `test_round_progress_bar.py` (**76/76**, acht Abschnitte —
  Geometrie an vier Breiten, die Kachelung ohne Drift, der Zustand→Füllung an
  PIXELN, die Farbe PRO Zug, das Badge nach INHALT statt nach Pixelzahl, und
  die Verdrahtung) plus `ab_round_progress_bar.py` (**8 A/B-Sonden, alle
  beißend**). **Zwei Befunde über den TEST**, beide von den Sonden: die
  Pixelzahl eines Badges unterscheidet die Aeldari- und die Necron-Kunst NICHT
  (beide inken gleich viele Pixel in einer 29-px-Kachel — verglichen wird jetzt
  der Inhalt), und eine Sonde ließ die Suite mit `min()` auf einer leeren
  Sequenz ABSTÜRZEN statt rot zu werden (**neunzehnte Instanz**). Volle
  Regression **205 Suiten, ~17900 Prüfungen, alle grün bis auf den einen
  bekannten Fehlschlag**.
- **Im ECHTEN Spiel belegt** (`verify_round_progress_bar.py`, `runpy` auf
  `selfplay.py`s echte `main()`-Schleife, nichts gestellt — der Balken wird in
  jedem Frame gezeichnet, also der seltene passiv messbare Fall):

  | | gefixt | `--neutralize` |
  |---|---|---|
  | Frames mit Balken / mit Badge | 1999 / 1999 | 1999 / 1999 |
  | **Balken überdeckt das Brett** | **0** | **1998** |
  | Balken frei vom Brett | **1998** | 0 |
  | **Spalten teilen die Unterkante des Balkens** | **1998** | **0** |
  | Spalten aus der Flucht | **0** | **1998** |

  `--neutralize` stellt die gemeldete Welt in zwei Zügen her (`BAR_HEIGHT = 0`,
  damit `main()` die Spalten wieder oben ansetzt, plus ein `bar_rect`, das sich
  in Brettbreite über das Brett legt). **Die ersten beiden Zeilen sind in
  beiden Welten gleich, und das ist die Aussage:** der Balken zeichnet
  neutralisiert genauso schön, nur liegt er auf der Karte und die Spalten
  fluchten nicht. **Ein Screenshot des Streifens kann diesen Fehler nicht
  zeigen** — deshalb misst die Sonde RECTS, die sie sich von den Widgets
  abgreift, denen `main()` sie reicht (Würfelpanel → Brett, Action-Panel →
  links, Game-Status-Panel → rechts).
  **Eigener Sondenfehler dabei:** die erste Fassung scannte den Bildschirm
  NACH `runpy` und meldete 0 Pixel jeder Farbe — `main()` ist dann weg und
  seine Display-Surface nicht mehr lesbar. Gemessen wird jetzt IM Frame, eine
  Scanline statt der ganzen Spur (14k `get_at()` je Frame wären eine eigene
  Messverfälschung).

- **Beschriftung getestet (2026-09-12, Rundenzahlen):** `test_round_progress_bar.py`
  **111/111**. Abschnitt 4 prüft Text UND Farbe per Font-Spion (ein Label mit
  falschem TEXT hat den richtigen Platz und die richtige Farbe): genau eine Zahl
  je RUNDE, 1..5 in Spurreihenfolge, kein "P…" je gerendert, jede Zahl über der
  Lücke ihrer zwei Züge und samt Ring innerhalb ihrer Spanne, Gold NUR auf der
  laufenden Runde und identisch zur gerenderten Titelfarbe, das Neutralgrau am
  GERENDERTEN Wert gegen die Teamfarben geprüft (nicht gegen `LABEL_COLOR` — eine
  Sonde bewegte sonst beide Seiten), Zahlen schon im Deployment, und eine zu
  schmale Spur ohne Zahl gegen eine breite mit allen fünf im selben Aufruf.
  `ab_round_progress_bar.py` **23 A/B-Sonden, alle beißend** — darunter P1/P2
  zurück, eine Zahl je Zug, Label in Teamfarbe, keine Hervorhebung, Gold um eins
  verschoben, Klammer umgangen, Zahlen im Deployment unterdrückt. Eine Sonde, die
  ihre Suite ABSTÜRZEN lässt, zählt dort jetzt als Fehlschlag statt als Biss.
  - **Vorsorglich umgebaut:** die Prüfung auf den Goldrahmen der laufenden Zelle
    liest außerhalb der Label-Boxen — die goldene Rundenzahl liegt in derselben
    oberen Spurhälfte und hätte sie sonst allein erfüllen können.
  - **Ein älterer Befund über den TEST, weiter gültig:** die Farbprüfungen lesen
    Zeile +1 der Spur, weil das 18-pt-Label Zeile +3 abdeckt; dass Zeile +1 kein
    Label kreuzt, ist eigens gepinnt.
  - **Im ECHTEN Spiel** (`verify_round_progress_bar.py map2 1500`): **1499 von
    1499 Frames mit Rundenzahlen** (Deployment eingeschlossen), gezeichnete Texte
    genau `['1'..'5']`, Label-Tinte 3630 px in den Label-Farben / **0 unter der
    Spur**, in **29 von 29** gesampelten Schlacht-Frames ist genau die laufende
    Runde gold; Layout unverändert (0 Überlappungen mit dem Brett, 0 Spalten aus
    der Flucht).
  - Volle Regression **228 Suiten, ~20955 Prüfungen, 227 grün / 0 rot /
    1 bekannt**.

## Agile Manoeuvres sind TÜRKIS, nicht violett (game/ui/button_style.py)

**Eine vierte Accent-Palette** (User: "colorcode für agile manouvers ist momentan lila wie
stratagems. soll aber türkis sein. (buttons, überschriften)"). Die vier Agile-Manoeuvre-Knöpfe
trugen `accent="stratagem"` und sagten damit das Falsche über ihren PREIS: eine Agile Manoeuvre
zahlt einen **Battle-Focus-TOKEN**, keine CP — sie ist kein 15.01-Kauf.

- **Türkis und nicht das Default-BLAU**, obwohl blau die naheliegende "gratis"-Farbe wäre: blau
  heißt in diesem Panel "kostet nichts", und eine Manoeuvre ist nicht gratis — sie zehrt an einem
  pro Runde geteilten Vier-Token-Konto. Sie ist eine EIGENE Art von Kosten, bekommt also eine
  eigene Farbe, genau wie violett die der CP ist.
- **Der Farbton ist echtes Türkis (#40E0D0)**, nicht ein vom Default abgerücktes Blaugrün.
  **Gemessen, und die engste Paarung steht ausgeschrieben:** Abstand zum Default-Blau **74.2**, zum
  Confirm-Grün 110.3, zum Violett 176.4. Türkis liegt per Konstruktion ZWISCHEN dem Blau und dem
  Grün dieser Palette, ist also näher an beiden als die beiden aneinander (Blau/Grün 106.4) — das
  ist dem gewünschten Farbton inhärent und kein Versehen. Der Nachbar, der wirklich danebensteht,
  ist das Blau ("Move"/"Advance" sitzen direkt an den Manoeuvre-Knöpfen).
- **Vier Zeichenstellen**, alle gemessen: die drei Bewegungsphasen-Manoeuvres (Swift as the Wind,
  Flitting Shadows, Star Engines) an EINER Stelle, **Sudden Strike an seiner eigenen, in einer
  anderen Phase** — deshalb einzeln geprüft statt als mitgekommen angenommen.

### Die "Überschriften"-Hälfte, und warum sie eine ABLEITUNG bekam

"Überschriften" ist wörtlich dieselbe Stelle wie in der früheren Violett-Bitte: die
`{player} - Decision`-Zeile des `DecisionOverlay`. Die reaktiven Manoeuvres (Fade Back,
Opportunity Seized) öffnen dort einen Prompt, der bis hierher das schlichte Gold trug.

- **`DecisionManager.request()` bekam `is_battle_focus=`** neben `is_stratagem=`. Die zwei sind
  verschiedene REGEL-Fragen ("ist das ein 15.01-CP-Kauf" / "ist das eine Agile Manoeuvre") und
  behalten deshalb ihre eigenen Namen — `battle_focus._raise_offer()`s Kommentar erklärte den
  Unterschied schon, jetzt hat er auch seine positive Hälfte.
- **Aber "welche Farbe hat die Überschrift" ist EINE Frage mit EINER Antwort**, also gibt es
  `DecisionManager.accent` als abgeleitete Property und `decision_overlay.ACCENT_COLORS` als EINE
  Tabelle. Ohne das wäre am Zeichenort ein zweites `if/else` über zwei Flags entstanden — die Form,
  die dieses Repo bei `whole_unit_drag.py` schon einmal zusammengelegt hat. Eine vierte Kategorie
  kostet jetzt eine Tabellenzeile statt eines Zweigs. Die zwei Flags sind per Konstruktion exklusiv
  (ein Stratagem ist keine Agile Manoeuvre), die Reihenfolge arbitriert also nie — sie steht
  trotzdem da, damit sie nicht driften kann.
- **Die 30+ bestehenden `is_stratagem=True`-Aufrufstellen sind unangetastet.**

### Getestet

- `test_battle_focus.py` 168 → **195/195**, neuer Abschnitt 13. Beide Hälften werden dort geprüft,
  **wo sie GEZEICHNET werden**, nicht an der Konstante: die Knöpfe als PIXEL durch das echte
  `ActionPanel` (Manoeuvre-Knöpfe identifiziert wie in Abschnitt 8 — durch ANKLICKEN und schauen,
  welcher einen Token ausgibt, also kann die Prüfung nicht von der Regel abdriften), die Überschrift
  durch das echte `DecisionOverlay` mit einem Angebot, das der echte Pool erhoben hat. **Zwei
  Gegenproben, ohne die der Abschnitt auf einem durchgehend türkisen Panel bestünde:** kein
  Nicht-Manoeuvre-Knopf desselben Renders trägt Türkis, und ein Stratagem-Overlay bleibt violett.
  - **Eigene Scene statt Abschnitt 8s**: dessen Pool ist zu dem Zeitpunkt leergespielt, und ein
    leerer Pool bietet gar keine Manoeuvre-Knöpfe an — der Abschnitt hätte bestanden, indem er
    NICHTS misst.
  - **Ein Wächter benutzte `_PALETTES[...]` und STÜRZTE unter der Lösch-Sonde AB statt rot zu
    werden** — vierte Instanz derselben Lehre (die zwei `str.index()`-Wächter, die gepolsterte
    Zeile in `test_faction_badges.py`). Jetzt `.get()`.
- **Neu `ab_battle_focus_colour.py`: sieben A/B-Sonden an der QUELLE, alle beißend** (Knöpfe zurück
  auf violett → 191/195; Sudden Strike allein → 193; Flag entfernt → 193; Overlay ignoriert den
  Accent → 194; Paletten-Eintrag gelöscht → 191; Türkis auf Default-Blau genudget → 193; die GANZE
  Vor-Fix-Welt → **187/195**).
- Volle Regression **164 Suiten, ~14430 Prüfungen, 163 grün / 0 rot / 1 bekannt**, alle acht Smokes
  exit 0, `selfplay.py map2`.
- **Im ECHTEN Spiel belegt, nicht nur im Test** — `game/ui/action_panel.py` läuft pro Frame, und
  "gebaut, aber nie GEFÜTTERT" hat dieses Repo sechsmal getroffen: ein Spion an
  `button_style.draw_button()` in einem echten `selfplay.py map2`-Lauf mit Aeldari auf BEIDEN Seiten
  meldet **2578 Türkis-Zeichnungen über 3000 Frames**, auf einem echten Manoeuvre-Knopf
  (`Flitting Shadows - no Fire Overwatch at this unit (4 token(s))`), und **null** Violett im ganzen
  Lauf. **A/B im echten Spiel:** mit den Knöpfen zurück auf `accent="stratagem"` sind es **2620
  Violett-Zeichnungen und 0 Türkis** — genau das gemeldete Verhalten.

## Decline-Buttons sind ROT — auch im Overlay (game/decline_option.py)

**Gemeldet:** *"Decline Buttons auch in den overlays rot einfärben."*

- **Der Farbcode stand schon fest, er galt nur nicht überall.** `button_style.py`s eigener
  Docstring schreibt aus, was Rot in dieser HUD heißt ("this button abandons/declines the current
  action"), und das linke Panel hält sich seit Langem daran (26 `accent="danger"`-Stellen: jedes
  Cancel, jedes "Decline Charge"). `DecisionOverlay` — die modale Box, über die ~90 Bruchstellen
  dieses Spiels laufen — malte JEDE Option im selben flachen Grau. Also war ausgerechnet die
  Stelle, an der eine Entscheidung wirklich FÄLLT, die einzige ohne den Farbcode.
- **`game/decline_option.py` ist die eine Definition**, gelesen vom Overlay. Ein PRÄDIKAT auf das
  LABEL, nicht ein Flag an ~100 `request()`-Aufrufstellen — und das ist eine Messung, keine
  Bequemlichkeit: ein vergessenes Flag macht nichts rot, also bleibt der Knopf grau, also ist der
  Fehler exakt der heutige und verrottet still. Die Labels sind ohnehin für Menschen geschrieben
  und sagen "nein" in einem kleinen, geschlossenen Wortschatz.
- **Als PRÄFIXE gematcht**, weil mehrere davon per f-string ihre eigenen Zahlen tragen ("Keep the
  Advance roll (7)") und der Teil, der "nein" sagt, immer vorne steht.
- **Was NICHT rot wird, ist der Punkt:** eine echte Zwei-Wege-Wahl hat gar keinen Nein-Zweig
  ("Leap to Defend" gegen "Into the Fray", `[LETHAL HITS]` gegen `[SUSTAINED HITS 1]`) — die
  Hälfte davon rot zu malen behauptete etwas Falsches über sie.
- **Der Wächter ist eine MENGENDIFFERENZ an der QUELLE** (`test_decline_buttons.py` Abschnitt 3):
  jedes literale Options-Label in `game/` wird per AST eingesammelt und gegen eine erwartete
  Klassifikation gestellt. Ein Verhaltenstest kann eine NEUE Schreibweise von "nein" nicht sehen,
  weil es sie noch nicht gibt; hier wird die Zeile rot, statt dass noch ein grauer Decline gemalt
  wird. Beide Richtungen: eine unklassifizierte Absage UND eine fälschlich rot gemalte echte Wahl.
- **Die Farben kommen aus `button_style`, nicht aus einem zweiten Rot** — Panel und Box können
  damit nicht auseinanderlaufen. Die FORM bleibt die flache Rechteck-Liste des Overlays: das sind
  Antworten in einer Liste, und die Form zu ändern war nicht die Bitte.
- **Nur `decision_overlay` war betroffen** — geprüft, nicht angenommen: die sieben anderen Overlays
  haben gar keine Options-Knöpfe (sie sind Klick-weg-Notices), das Game Menu malt Quit längst rot,
  und der Brett-Pick-Screen des Panels zeichnet seine `skip_options` schon mit `accent="danger"`.
- **Getestet:** neu `test_decline_buttons.py` (**54/54**, vier Abschnitte — Füllung, Rahmen UND
  Textfarbe auf PIXELN durch die ECHTE Box, dazu die Gegenprobe, dass eine Liste aus lauter echten
  Wahlmöglichkeiten gar kein Rot bekommt; ohne die bestünde der Abschnitt auf einem durchgehend
  roten Panel) plus vier A/B-Sonden in `ab_menu_and_decline.py`, alle beißend.
  **Ein eigener Testfehler:** die Textfarbe wurde auf EINER Scanzeile gesucht, und ein
  antialiasiertes Label hat dort nicht zwingend einen Glyphenkern — jetzt über die ganze
  Knopffläche.

### ...und die GEWÖHNLICHE Option ist BLAU, nicht grau (2026-09-09)

**Gemeldet:** *"und bei normalen overlays habe ich jetzt meiste einen grauen knopf und einen roten
decline knopf. ändere die grauen knöpfe in blau."* — die zweite Hälfte desselben Farbcodes, eine
Meldung später.

- **Es war die einzige Stelle im HUD ohne Farbcode.** `button_style.py` schreibt aus, was Blau
  heißt ("ein Druck kostet nichts"), und `ActionPanel` hält sich seit Langem daran; `DecisionOverlay`
  malte die gewöhnliche Option in einem eigenen flachen Grau — also war ausgerechnet die Box, über
  die ~90 Bruchstellen dieses Spiels laufen, die eine, die nichts sagte. Der rote Decline-Knopf
  daneben war eine Meldung vorher aus genau diesem Grund gefixt worden.
- **Die drei Werte kommen aus `button_style` (`BG_NORMAL`/`BORDER_NORMAL`/`TEXT_NORMAL`), nicht ein
  zweites Mal hingeschrieben** — dieselbe Begründung wie bei den Decline-Farben darüber: Box und
  Panel dürfen nicht mit zwei Blautönen für eine Sache enden. Die FORM bleibt das flache Rechteck
  des Overlays; gefragt war die Farbe.
- **Getestet:** `test_decline_buttons.py` 54 → **67/67** (neuer Abschnitt 2b, auf PIXELN: Füllung,
  Rahmen und Textfarbe einzeln gegen die Palette, dazu die Frage GRAU getrennt gestellt —
  `len(set(farbe)) > 1` —, weil ein Overlay, das `button_style` liest und eine graue Palette
  bekäme, die erste Prüfung erfüllt und die gemeldete nicht; die drei ALTEN Literale als
  verschwunden gepinnt; und der Vergleich gegen das, was `ActionPanel` wirklich ZEICHNET, nicht
  gegen die Konstante, die beide lesen).
- **Die tragende A/B-Sonde ist die, die keine Pixel bewegt:** dieselben drei Werte von HAND
  hingeschrieben statt aus `button_style` gelesen. Jeder Pixel ist identisch, sie beißt also nur,
  wenn der Quell-Wächter tragend ist — und eine Kopie ist genau der Weg, auf dem die zwei Blautöne
  entstünden. (`ab_menu_button_and_blue.py`, 66/67 statt 67/67.)
