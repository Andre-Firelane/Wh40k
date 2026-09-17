# Game Menu, Speichern und Autosave

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Game Menu (game/ui/game_menu.py, main.py's run())

**Der Rahmen um das Spiel** (User: "momentan startet das spiel direkt mit der map auswahl und
endet mit ESC. baue ein spieletypisches game menu ... im spiel öffnet ein druck auf ESC das menü.
außerdem muss noch irgendwo ein kleiner menu knopf sein. vielleicht links oben neben dem rechten
panel"). Vorher fiel `main()` direkt in die Kartenauswahl, und der einzige Ausgang war ESC im
Vollbild — es gab keinen Weg, eine Partie zu verlassen ohne das Programm zu beenden, und keinen,
eine zweite zu beginnen.

- **`main()` ist EINE SCHLACHT, `run()` ist die ANWENDUNG.** Das ist die Entscheidung, aus der alles
  Übrige folgt. Board, GameState, die ~40 Controller, `game_log`, der Agent — alles sind Locals von
  `main()` und sterben mit ihr; ein echter Neustart ist deshalb schlicht „`main()` verlassen und
  wieder aufrufen", und es gibt nichts abzuräumen.
  - **ALLE ZEHN Harnesses rufen `main.main()` direkt.** Das Menü eine Ebene höher zu legen heißt:
    ein Screen, der auf einen Klick wartet, liegt gar nicht auf ihrem Weg. Anders als `MAP_SELECT`
    und `ARMY_SELECT` braucht `START_MENU` deshalb **kein Opt-out in zehn Dateien und keinen
    Quell-Wächter**, der einen künftigen Harness daran erinnert. `--no-menu` ist reine CLI.
  - **Zurückzusetzen ist nur `config.LOAD_SCENE` und der Kartenschlüssel** — sonst öffnete „New
    Game" ewig denselben Spielstand. Alles andere wird von `maps`/`army_lists`/`detachments`
    `.apply_to_config()` je Lauf VON GRUND AUF neu geschrieben. `config.BIOME` und die zwei
    Armee-Settings überleben ABSICHTLICH: sie sind die Defaults, auf denen die Picker öffnen.
  - **`set_mode()` läuft genau EINMAL pro Prozess** (in `run()`); `main()` nimmt per
    `pygame.display.get_surface()` das vorhandene Fenster. Ein zweiter `set_mode()` je Schlacht
    zöge das Display unter jeder `convert_alpha()`-Fläche weg, die `game/sprites.py` modulweit
    cacht — und die sollen eine Schlacht überleben.
  - **Der `id(board)`-Cache ist gemessen ungefährlich:** `Renderer._static_cache_key` ist eine
    INSTANZ-Variable und `renderer` ein Local von `main()`, jede Schlacht bekommt also einen
    frischen Cache. Die dokumentierte Recycling-Falle betraf den modulweit geteilten Renderer in
    `map_preview`, der dort längst pro Aufruf neu gebaut wird. **Im echten Spiel belegt:** zwei
    `main()`-Läufe hintereinander in EINEM Prozess auf map1 und map3, der zweite zeichnet sein
    eigenes Brett (`smoke_game_menu.py`).
- **EINE Klasse, ZWEI Wirte.** Startbildschirm (eigener Screen über `tile_screen.run_screen()`) und
  ESC-Overlay sind dasselbe `GameMenu`. Geteilt: Panel-Rechteck, Eintrags-Rechtecke, Hit-Testing,
  Tastatur, Malen. Genau ZWEI Dinge verzweigen auf `in_game`: der HINTERGRUND (Scrim über dem
  laufenden Frame gegen gefüllter Screen mit Kopfzeile) und die EINTRÄGE.
  - Start: New Game / Resume / Quit. Im Spiel: Resume / **Save** / New Game / Quit.
  - **„Resume" bedeutet an beiden Orten etwas anderes, und das ist bestellt** (User: "Beides, je
    nach Ort"): im Spiel zurück zur Schlacht, beim Start der neueste Spielstand.
  - **Ein DEAKTIVIERTER Resume-Eintrag bleibt stehen**, ausgegraut, mit dem Grund darunter — das
    Gegenteil von `tile_screen`s „kein Chrome für ein totes Steuer"-Regel, und absichtlich: ihn
    wegzulassen änderte still die FORM des Menüs zwischen den Wirten.
  - **EIN Klick = eine Aktion**, kein Zwei-Takt wie bei Karte/Armee: die Rückfrage wurde
    ausdrücklich abgelehnt. **Benannte Folge:** ein Fehlklick auf „Start New Game" im Spiel
    verwirft die Partie; der Autosave ist, was das überlebbar macht.
  - **Accents sagen, was ein Druck KOSTET** (die schon geltende `button_style`-Semantik): Resume
    grün, Quit rot, New Game **blau beim Start und ROT im Spiel** — dort kostet es die Schlacht.
  - **`run()` gibt NIE `None` zurück**, anders als die zwei Picker: dieser Screen HAT einen
    Quit-Eintrag, ESC und das Fensterkreuz beantworten ihn also, statt einen vierten Zustand zu
    erfinden.
- **Verdrahtung im Spiel — alles VOR der ~48-Zweige-Kette** (Fehlerklasse 15): der
  `is_pending`-Zweig mit `continue`, und der Knopf-Hit-Test als eigenes `if`. Beide über dem
  Regel-Leser bzw. so geordnet, dass ein offener Leser den Klick zuerst bekommt.
  - **Die Antwort wird per `take_action()` EINMAL pro Frame gepollt** (Idiom von
    `take_pending_placement()`): ein Overlay kann keine `main()`-Locals schreiben, und das Löschen
    beim Übergeben ist, was einen Druck nicht zweimal bedient werden lässt.
  - **NICHT in `_front_notice()`** — das ist die Ordnung der Klick-irgendwohin-Notices mit
    `.dismiss()`; dies hat echte Knöpfe und ein eigenes `handle_event`, wie `army_rules_overlay`,
    das aus demselben Grund nicht drinsteht. `test_one_modal_at_a_time.py` bleibt unberührt.
  - **Die KI hält an, und zwar über EINEN Term:** `ai_action_paused_this_frame` bekommt
    `or game_menu.is_pending` an seiner Saat. Diese Flagge lesen beide KI-Einstiege schon, und der
    Auto-Play-Tick läuft AUSSERHALB der Event-Schleife — der `continue` des Zweigs deckt ihn also
    gar nicht ab.
  - `_open_game_menu()` beendet zuerst den Line-Drag: der wird GEPOLLT und ist vom `continue`
    ebenfalls nicht gedeckt, ein gehaltener Rechtsklick zöge sonst unter dem Scrim weiter Modelle.
- **Der Knopf sitzt seit 2026-09-09 IN DER KOPFZEILE DES RECHTEN PANELS, neben "Game Status"**
  (User: "außerdem hätte ich den 'Menu' Knopf gerne oben rechts in der rechten spalte neben der
  Game Status überschrift"). Vorher die Brett-Ecke oben rechts, wo er sich die Ecke mit dem
  AI-Schalter teilte.
  - **Die Geometrie liegt in `button_style.py`, nicht in einem der zwei Module, die sie brauchen**
    (`HEADER_BUTTON_WIDTH/HEIGHT/GAP`, `header_button_reserve()`, `header_button_rect(rect)`):
    Leiste und Knopf teilen sich EINE Zeile, die Leiste wird um exakt den Platz gekürzt, den der
    Knopf nimmt (`draw_panel_header(reserve_right=)`) — und zwei Module, die je die halbe
    Arithmetik machen, sind der Weg, auf dem eine Überschrift unter einem Knopf landet. Beide
    importieren `button_style` ohnehin, es kostet also in keine Richtung eine neue Abhängigkeit,
    und keines von beiden kann die Frage allein beantworten.
  - **Die Leiste wird GEKÜRZT, nicht überzeichnet.** Ein Knopf über einer vollbreiten Leiste sieht
    genau so lange richtig aus, wie der Titel zufällig kurz genug ist — und das ändert sich still.
    `reserve_right` ist opt-in mit Default 0, jede andere Kopfzeile des Spiels zeichnet also
    dieselben Pixel wie vorher (im Test als Extent-Vergleich gepinnt, nicht als Pixelzahl: die
    Glyphen des Titels liegen auf derselben Scanline und sind nicht die Leistenfarbe).
  - **Gemessen bei 220 px Panelbreite:** Leiste 212 → **132 px**, Knopf 74×26 mit 6 px Abstand,
    Textraum 112 px gegen 94 px für "Game Status" — 18 px Luft. Der Knopf ist in der 34-px-Leiste
    ZENTRIERT (4 px Versatz), weil eine geteilte Zeile auch ihre Mitte teilt.
  - **Er bleibt HELL, während der AI-Busy-Dim den Rest des Panels abdunkelt** (`ai_busy_dim_rects`
    deckt beide Spalten), weil er als Letztes im Frame gezeichnet wird. Gewollt statt geduldet: ein
    hängender Prompt ist genau der Zustand, aus dem man das Menü am dringendsten erreichen will.
    Als REIHENFOLGE gepinnt.
- **Damit liegt nur noch der AI-SCHALTER über der Map** (User: "Dann liegt nur noch der AI Schalter
  über der Map"), und er bekommt **keine `avoid_rects` mehr** — er hat die Ecke für sich und hört
  auf, sich zu bewegen. Ein Steuer, das stillsteht, ist mehr wert als eine knappe Marge.
  - **Gemessen über 1280/1366/1600/1920 × 1/10/40/60/100 Würfel: NULL Würfel liegen je unter dem
    Schalter.** Die erste Würfelreihe beginnt bei y=83, der Schalter endet bei y=66 — 17 px Luft,
    unabhängig davon, wie breit das Panel für eine große Salve wird. Die BACKDROP-Polsterung
    erreicht die Ecke bei 1280/1366 sehr wohl (bis −159 px Überlappung bei 100 Würfeln); das ist
    dieselbe Lage, in der der MENU-Knopf dort vorher stand, und es ist Polsterung, kein Würfel.
    Der Schalter wird NACH dem Würfelpanel gezeichnet, liegt also oben.
  - **Der `avoid_rects`-Mechanismus bleibt und wird an einem SYNTHETISCHEN Blocker geübt**
    (`test_game_menu.py`, `test_ai_busy_badge.py`) — der `WALL_CROSSING_COST_IN = 0.0`-Präzedenzfall:
    was inert ausgeliefert wird und von keinem Test gefahren wird, ist beim nächsten Träger kaputt.
    In `main.py` ist das Fehlen als NEGATIV gepinnt, weil die Regression hier "jemand trägt wieder
    einen Blocker ein" ist und nicht "jemand entfernt einen".

### Größere Schrift und ein Hintergrundbild (2026-09-07)

Zwei User-Bitten, EINE Schriftmenge: *"Die Font im Main Menu und Auswahl screen darf viel größer
sein"* und *"main-manu-background.jpg als hintergrund im hauptmenü setzen"*.

- **`tile_screen.make_fonts()` ist die eine Menge, gelesen von DREI Screens** (Kartenauswahl,
  Armeeauswahl, Game Menu) — "größer" ist also eine Änderung mit drei Konsumenten. Jeder Versatz
  ist jetzt eine benannte Konstante (`TITLE_FONT_DELTA` … `SMALL_FONT_DELTA`), also kostet "noch
  größer" eine Zeile je Rolle statt sechs Literale in einem Dict.
  Die REIHENFOLGE der Rollen bleibt (Titel > Name > Untertitel > Label > Body > Small) und ist als
  Ordnung gepinnt statt als sechs Zahlen — die Bitte galt der Größe, nicht der Hierarchie.
- **Was schiefgehen kann, sind nicht die Schriften, sondern die Kästen, die um die alten herum
  gemessen wurden** — und WELCHE davon wirklich mitwachsen mussten, hat die A/B-Sonde entschieden,
  nicht das Auge:
  - **`HEADER_HEIGHT` bleibt bei 104.** Die Sonde ("zurück auf den alten Wert") biss NICHT: die
    Leiste trägt Titel plus Hinweiszeile auch in der neuen Größe, und jeder Pixel, den man ihr
    gibt, kommt direkt aus `tile_area()`s Kachelband. Eine Änderung, die nichts kauft, ist keine.
  - **`FOOTER_HEIGHT` 58 → 70 und `CONFIRM_BUTTON_WIDTH` 240 → 300**, und was sie kaufen ist die
    LUFT unter den Knöpfen: "steht noch im Fenster" ist mit einem 4-Pixel-Streifen erfüllt, während
    die alte Fußzeile 14 px hatte. `FOOTER_CLEARANCE_PX` ist diese Marge, und erst diese Prüfung
    macht beide Konstanten tragend (vorher bissen ihre Sonden nicht). Bei 240 bricht das längste
    echte Confirm-Label auf DREI Zeilen um, der Knopf wächst auf 67 px und hängt unten heraus.
  - **`PANEL_WIDTH` 460 → 560 im Game Menu.** Eine Notiz unter einem Eintrag wird als EINE
    ungebrochene, zentrierte Zeile gezeichnet — ein Panel schmaler als die längste ("abandon this
    battle and pick a new map and armies", 370 px) malt sie über den eigenen Rahmen.
    **`ENTRY_HEIGHT` 46 → 58 ist dagegen reine SPACING-Wahl** und ausdrücklich so dokumentiert:
    `draw_button()` wächst eine zu kurze Zeile von selbst, die alte Zahl hätte also weiter
    funktioniert — die Sonde sagte es, und der Kommentar sagt es jetzt auch.
- **Ein vorbestehender Überlappungsfehler wurde dabei sichtbar und ist behoben:** die
  Kartenauswahl teilt sich ihre Kopfleiste mit der BIOM-Reihe, und ihre Hinweiszeile ist KEIN
  fester String — sie nennt die gewählte Karte. Gemessen: der Crucible-Hinweis läuft **608 px**
  schon in der alten Schriftgröße, gegen eine Reihe, die bei 1280 px bei **616 px** beginnt und mit
  dem vierten Biom weiter nach links gerückt ist. Der Kommentar an `BIOME_BUTTON_WIDTH` behauptete
  das Gegenteil ("sie sind feste Strings ... ~380 px Abstand") — das war beim Schreiben wahr.
  `ts.ellipsised()` kürzt jetzt, und `map_select._hint_width()` leitet den Platz aus
  `biome_layout()` ab statt ihn einmal zu messen und hinzuschreiben, sodass ein fünftes Biom die
  Zahl mitzieht.
- **Der Hintergrund: `sprites.menu_background_path()` / `menu_background_surface()`**, dieselbe
  "fehlende Kunst kostet ein Bild, nie den Screen"-Konvention wie jede andere Suche in dem Modul.
  - **Die Datei liegt in `Sprites/Death Guard/`, und das wird NICHT "korrigiert"** — `_resolve_path`
    durchsucht nach dem Top-Level die Fraktionsordner, und hier gilt wie überall: DER ORDNER
    GEWINNT. Auch der Name trägt die Schreibweise des Users ("manu"); ihn "richtig" zu
    transkribieren löst auf nichts auf (eigene A/B-Sonde).
  - **COVER, nicht Fit**: eine letterboxte Vorlage lässt Balken der Flächenfarbe an zwei Seiten
    stehen, was sich als nicht geladene Kunst liest. Seitenverhältnis bleibt, der Überstand wird
    mittig beschnitten. Nach `(Pfad, Breite, Höhe)` gecacht — eine Fenstergröße ändert sich, wenn
    das Fenster sich ändert, und das ist ein Vollbild-`smoothscale`.
  - **Der Schleier (`BACKGROUND_VEIL_COLOR`, Alpha 150) ist keine Dekoration:** goldene
    Überschrift, gerahmtes Panel und die rechtsbündige Tastenzeile liegen direkt auf einem Foto,
    und ohne ihn hängt ihr Kontrast davon ab, was zufällig dahinter liegt.
  - **Der IN-BATTLE-Host bleibt unangetastet** — sein Hintergrund ist das eingefrorene Brett, was
    der ganze Sinn eines Pausenschirms ist. Eigene Testzeile und eigene Sonde.
  - **Die zwei Picker bekommen die Kunst bewusst NICHT**: die Bitte nannte das Hauptmenü, und ein
    Foto hinter einem Raster aus Kartenvorschauen kämpft mit ihnen.
- **Getestet:** neu `test_menu_presentation.py` (**42/42**, vier Abschnitte) plus
  `ab_menu_and_decline.py` (16 der 20 Sonden gehören hierher, alle beißend). **Fünf Sonden bissen
  zuerst NICHT, und alle fünf waren Befunde über den TEST** (Fehlerklasse 24): die
  Fußzeilen-Prüfung fragte nur "steht es im Fenster" statt nach der Luft darunter; `HEADER_HEIGHT`
  brauchte gar keine Änderung; die Kartenauswahl reichte ihr Budget an eine Funktion, die der Test
  selbst aufrief statt den Screen (jetzt ein Spion auf `ts.draw_header`); Cover gegen Fit war an
  einer Surface fester Größe gar nicht unterscheidbar (jetzt an einem synthetischen Bild mit
  absichtlich falschem Seitenverhältnis); und `ENTRY_HEIGHT` war schlicht nicht tragend.
  Volle Regression **186 Suiten, ~16347 Prüfungen, 185 grün / 0 rot / 1 bekannt**, `run_tests.py
  --smoke` komplett grün.

### Der Titel, und keine Unterschriften mehr (2026-09-07)

- **`TITLE = "WARHAMMER 40K AI SIMULATOR"`** (User: "Oben links soll stehen Warhamer 40k AI
  Simulator"). Versalien, weil dieselbe Kopfleiste die zwei anderen Vorspiel-Screens trägt
  ("CHOOSE THE BATTLEFIELD", "CHOOSE FACTION") — die drei lesen sich sonst wie drei Programme.
  Gemessen: 582 px bei 1212 px Platz auf dem schmalsten Fenster.
- **Die Zeile unter jedem Knopf ist WEG** (User: "Die unterschriften unter den buttons können
  weg"). `entries()` liefert damit `(action, label, enabled)` statt eines Vierertupels, und
  `NOTE_GAP`/`NOTE_COLOR`/`DISABLED_NOTE_COLOR` sind ersatzlos entfallen — ein Feld, das niemand
  mehr zeichnet, ist genau der tote Code, den dieses Repo sonst findet, wenn es zu spät ist.
- **BENANNTE FOLGE, hier festgehalten statt zum Wiederentdecken:** die Startbildschirm-Zeile unter
  „Resume Game" nannte den Spielstand, der geladen wird ("map2 - battle round 1 - Player 1"), und
  die unter einem AUSGEGRAUTEN Resume nannte den GRUND ("no saved game yet"). Beides steht jetzt
  nirgends. `save_note` bleibt trotzdem Konstruktor-Argument, weil es das EIGNUNGS-TOR ist
  (Fehlerklasse 5: `summary()` gibt `None` für eine unlesbare Datei) — es war nie nur eine
  Unterschrift. Eine Zeile im Panel, falls es zurück soll.
- **`PANEL_WIDTH` und `ENTRY_HEIGHT` sind damit beide reine SPACING-Wahlen**, und das steht im
  Kommentar: die Notizen waren das Einzige, was je an die Panelbreite stieß (370 px Fließtext),
  und `draw_button()` wächst eine zu kurze Zeile ohnehin selbst. Ihre A/B-Sonden sagten es,
  bevor der Kommentar es sagte.
- **Getestet:** `test_game_menu.py` 139 → **141/141** (eine Zeile ist zu Recht rot geworden — sie
  las die Unterschrift des ausgegrauten Resume; sie prüft jetzt die FORM der Zeile und dass das
  Menü gar keine Notizfarbe mehr kennt), `test_menu_presentation.py` **42/42** (die
  Notiz-Passt-Prüfung ist durch „zwischen zwei Zeilen steht nichts mehr" ersetzt, also genau die
  Zusicherung, die eine versehentlich zurückkehrende Unterschrift bricht).

### Speichern und Laden: der Snapshot trägt jetzt den Missionsstand

CLAUDE.md führte „`scene_io` sichert keine VP" als offenen Punkt. Er ist zu.

- **Autosave bei JEDEM PHASENWECHSEL** (User zuerst "Auto save pro Schlachtrunde", dann "der
  autosave scheint nicht zu funktionieren. bitte mach einen autosave bei jedem phasenwechsel")
  nach `scenes/autosave.json` (fester Name, kein Zuwachs auf der Platte), plus ein **Save-Knopf
  im Menü** (zeitgestempelt, damit der nächste Autosave keinen Handstand überschreibt). F9
  unverändert. Kante, Gate und Grenze stehen in `### Autosave bei jedem Phasenwechsel` darunter.
  - **Eine RUNDENgrenze ist weiterhin der einzige Zeitpunkt, an dem der Snapshot per KONSTRUKTION
    vollständig ist, und ein Phasen-Autosave innerhalb eines Zuges ist es deshalb nicht.** Alles Zug-gebundene der drei Missions-Controller (`_destroyed_this_turn`, die vier
    `*_at_turn_start`-Schnappschüsse, `guards`, `*_this_turn`, `ActionController.states`,
    ein offener Brett-Pick) ist dort leer — und die Hälfte davon ließe sich gar nicht schreiben, weil sie
    lebende Squad-Referenzen, `id()`-Schlüssel oder CALLBACKS hält. **Die Regel, die entscheidet:
    ein `card_state`-Schlüssel auf `_this_turn` ist zug-gebunden, jeder andere schlachtlang.**
  - Gehalten, solange irgendetwas ansteht, und AUSSERHALB der Event-Schleife.
- **`_save_scene()` ist der EINE Schreiber** (F9, Menü-Save, Autosave) und `_mission_slots()` die
  EINE Antwort darauf, welcher Controller in welchen Slot gehört.
- **Jeder Controller serialisiert sich selbst** (`save_state()`/`load_state()`), weil „was ist hier
  zug-gebunden" eine Tatsache über SEINE Regeln ist, nicht über das Dateiformat. Karten sind
  Modul-Singletons → nach KEY; Objective und Einheit → nach NAMEN; Death Traps `trapped` hat keinen
  Namen → nach INDEX in `state.terrain_areas` (deterministisch aus dem Kartenschlüssel, den der
  Snapshot ohnehin pinnt). **Die Deck-REIHENFOLGE wird mitgespeichert** — es wird per `pop(0)`
  gezogen, ein Neumischen beim Laden teilte eine andere Schlacht aus.
- **`FORMAT_VERSION` bleibt 1.** Präzedenzfall ist `armies`: ein OPTIONALER Abschnitt, ohne die
  Version zu bewegen. Die zwei vorhandenen Dateien in `scenes/` laden unverändert, nur ohne
  Missionsstand — im Test von beiden Seiten gepinnt.
- **Eine vor dem Speichern AUSGELÖSCHTE Einheit kam zurück — behoben.** `capture()` läuft über
  dieselben drei GameState-Listen wie `all_squads()`, eine tote Einheit steht in keiner und fehlt
  im Snapshot. `restore()` meldete das nur. **Gemessen:** auf dem Default-Pfad blieb sie zufällig
  unsichtbar (bei `PREGAME_DEPLOYMENT` stellt `register_unit()` gar nichts auf), auf dem
  Legacy-Pfad (`--no-deployment`) stand sie **mit voller Stärke auf dem Brett**. `restore()`
  RÄUMT sie jetzt ab (Modelle nach `destroyed_models`, `models` leer — wie diese Engine „zerstört"
  überall buchstabiert). **Sie wird NICHT als Kill verbucht** — die VP dafür sind im
  wiederhergestellten Ledger, ein zweites Mal zu zählen zahlte jeden Verlust doppelt. **Ventil:**
  passt der Snapshot auf KEINE Einheit der Szene, wird nichts gelöscht und der Grund gemeldet —
  sonst löschte ein Snapshot vom falschen Roster beide Armeen.
- **`newest()` liefert den jüngsten LESBAREN Snapshot** (nach mtime), nicht die jüngste `.json`:
  eine halb geschriebene oder fremde Datei ließe sonst Resume ausgegraut, während ein gutes Save
  eine Datei darunter liegt. `summary()` gibt `None` für Unlesbares und IST das Eignungs-Tor
  (Fehlerklasse 5) — angeboten wird nur, was auch geladen werden kann.

**Getestet:** neu `test_game_menu.py` (**139/139**, sechs Abschnitte; seit dem Umzug des Knopfes
in die Panel-Kopfzeile **207/207** — Abschnitt 5 misst die geteilte Zeile auf PIXELN durch das
ECHTE `GameStatusPanel` und fegt die Würfel) und `smoke_game_menu.py`
(**17/17**, 13 Frames, in `run_tests.py --smoke`; `--neutralize` fällt auf **3/17**, 14 Prüfungen
kippen — es klickt den Knopf jetzt an seiner neuen Stelle, also ist der Laufzeit-Beleg für den
Umzug ein ECHTER Klick durch `main()`s eigene Kette und braucht keine eigene Sonde). `test_scene_io.py` 40 → **74/74** (Abschnitt 8 die Auslöschung in beiden Pfaden plus dem
Ventil, Abschnitt 9 der Missions-Rundlauf). Volle Regression **168 Suiten, ~14932 Prüfungen, 167
grün / 0 rot / 1 bekannt**, alle acht Smokes.
**Im ECHTEN Spiel belegt:** der Autosave schreibt in einem `selfplay.py`-Lauf wirklich (Runde 1,
mit `missions`-Abschnitt), und ein per `--load` geöffneter echter Autosave bringt VP beider
Spieler, die ungewerteten Kills und den Primary-Punktestand zurück.
**Vier fremde Pins wurden zu Recht rot** und sind nachgezogen: die zwei `pygame.quit()`-Pins der
Picker (jetzt stärker: `main()` darf das Fenster gar nicht mehr schließen), und die zwei
ESC-Leiter-Pins in `test_line_drag.py` / `test_unit_selection.py`. Der erste davon hatte ein
FESTES 2200-Zeichen-Fenster um den ESC-Zweig und enthielt die geprüfte Zeile nicht mehr — er
schneidet jetzt am nächsten Zweig ab.

### Autosave bei jedem Phasenwechsel (game/autosave.py, 2026-09-12)

**Gemeldet:** *"der autosave scheint nicht zu funktionieren. bitte mach einen autosave bei jedem
phasenwechsel."* Der Autosave SCHRIEB — zwei Dinge ließen ihn von außen tot aussehen, und nur
eines davon war die Kante.

- **Harnesses haben die Datei des Users überschrieben.** Jedes Skript, das `main()` fährt,
  schrieb dieselbe `scenes/autosave.json`: von den 26 Läufen, die am 2026-09-12 einen Autosave
  schrieben, hatten mindestens 17 einen Mock-Plan, und jeder ersetzte eine gespielte Partie
  durch sein eigenes Runde-1-Brett — vom Menü aus nicht von „speichert nicht" zu unterscheiden.
  **`config.AUTOSAVE`** ist neu und in allen 15 Skripten, die `main.main()`/`main.run()` direkt
  rufen, VOR `import main` aus (`verify_*.py` erben es über `selfplay.py`). Quellwächter
  `test_autosave.py` §5 findet die Treiber selbst, mit Liveness-Zeile.
- **Die Kante war die Runde** — zehn Phasen, zwei ganze Züge. Jetzt `(Runde, Zugbesitzer,
  Phase)`: der Phasenname allein wiederholt sich jeden Zug, die Runde allein war der Fehler, und
  `active_player` ist bewusst NICHT Teil des Schlüssels — er flippt bei jedem Rettungswurf.
- **`AutosaveEdge.take()` ist EIN Aufruf, kein Fragen/Merken-Paar** (die Form von
  `DiceManager.claim_reroll_offer()`). Ein unruhiger Frame schreibt nichts UND merkt nichts,
  also schreibt der erste ruhige Frame die Phase; zwei Phasen während einer offenen Frage fallen
  zu der letzten zusammen. Die Datei hält ohnehin nur das neueste Brett.
- **„Ruhig" ist das alte Gate plus `_has_unresolved_declaration()`, kein offener Zug und keine
  laufende Schussaktivierung** — ein Phasenwechsel ist genau der Moment, an dem
  Ende-der-Phase-Reaktionen (Rapid-Ingress-Platzierung, reaktive Züge) aufgehen, und ein
  Snapshot stellt nie eine halbe Aktivierung her. Der Block steht außerhalb der Event-Schleife
  und VOR dem KI-Tick: eine Phase, die die KI im vorigen Frame beendet hat, wird geschrieben,
  bevor sie in der neuen handelt.
- **Ein geladener Kampf wird GESEEDET, nicht gespeichert.** Die Rundenkante wurde VOR dem
  Restore initialisiert (Runde 0 im Deferred-Start) und schrieb deshalb im ersten Frame nach
  jedem `--load` den Autosave neu — genau das, was ihr eigener Kommentar ausschloss.
  `autosave_edge.seed()` steht jetzt NACH `restore_turn()`.
- **`scene_io.write()` ist atomar** (Temp-Datei plus `os.replace()`, die Temp-Datei endet auf
  `.tmp` und ist damit für `newest()` unsichtbar, bei einem Fehler wird sie entfernt). Der
  Autosave ist jetzt die Datei, die am ehesten mitten im Schreiben steht, und eine halbe Datei
  ließe Resume auf einen ÄLTEREN Stand zurückfallen. Ein `OSError` beim Autosave wird geloggt
  und beendet die Partie nicht.
- **BENANNTE GRENZE: ein Autosave INNERHALB eines Zuges ist genau so vollständig wie F9 zum
  selben Zeitpunkt.** Positionen, Wunden, CP, VP, Deck/Hand, Statistiken und wer schon
  gehandelt hat kommen zurück; die zug-gebundene Missionsbuchführung (Kills DIESES Zuges für
  Ende-des-Zuges-Karten, die Zugbeginn-Schnappschüsse, angefangene Objective Actions) und die
  Einmal-pro-Zug-Ledger der Fähigkeits-Controller nicht. Die Kommentare in
  `secondary_missions.py`, `primary_missions.py`, `activation_state.py` und `scene_io.py`, die
  „der Autosave läuft an der Rundengrenze, also ist das leer" behaupteten, sind nachgezogen.
- **Getestet:** neu `test_autosave.py` (**64/64**, fünf Abschnitte — Schlüssel, Kante,
  atomares Schreiben, `main.py`-Verdrahtung per AST, Harness-Opt-outs) plus
  `ab_phase_autosave.py` (**13 A/B-Sonden, alle beißend, keine stürzt ab**).
  `test_game_menu.py` **206/206** (die drei Rundenkanten-Pins sind ersetzt), `test_scene_io.py`
  **75/75**. Volle Regression **227 Suiten, ~20866 Prüfungen, 226 grün / 0 rot / 1 bekannt**.
- **Im ECHTEN Spiel belegt** (`verify_phase_autosave.py`, zwei `main()`-Läufe über
  `selfplay.py`, Autosave in einen Wegwerf-Ordner umgelenkt, jede geschriebene Datei zurückgelesen):

  | | gefixt | `--neutralize` (Rundenkante, kein Seed) |
  |---|---|---|
  | erreichte Phasen / geschriebene Autosaves | **8 / 8** | 7 / **1** |
  | Datei hält die Phase, bei der sie geschrieben wurde | 8 von 8 | 1 von 1 |
  | Resume startet auf der gespeicherten Phase | ja | ja |
  | Autosave beim Laden sofort überschrieben | **nein** | **ja** |
  | `selfplay.py`s Opt-out beim Bau der Kante | `AUTOSAVE = False` | dasselbe |

  Schreibzeit 4–16 ms, einmal 67 ms — einmal pro Phase, nicht pro Frame. Nichts wird gestellt:
  Phasenwechsel passieren von selbst, das ist eine der passiv messbaren Fragen.

### Ein Save trägt jetzt WELCHES Modell — und wer schon gehandelt hat

**Gemeldet:** *"schaden auf einheiten wurde nicht gespeichert"* und *"es wurde nicht gespeichert,
wer schon welche aktion ausgeführt hat. zb wer schon geschossen hat und wer nicht"* — zwei Berichte,
zwei ganz verschiedene Ursachen.

**1. Der Schaden war IMMER in der Datei. Er landete beim Laden auf dem FALSCHEN Modell.**
Ein Snapshot hält die ÜBERLEBENDEN einer Einheit, die Szene beim Laden hält sie wie GEBAUT — und
`restore()` paarte sie der Reihe nach und schnitt den REST HINTEN ab. Also bekam ein Charakter am
Ende der Modellliste (wo 19.01 ihn hinstellt) nie seine Wunden zurück, und gelöscht wurde er obendrein.
- **Am EIGENEN Save des Users belegt** (`scenes/scene_20260904_214638.json`, map3, necrons vs death
  guard): `1 Skorpekh Destroyers 1 + Skorpekh Lord` steht darin mit EINEM Modell auf 5 Wunden — das
  ist der Lord auf 5/7. Restauriert wurde daraus ein **Skorpekh Destroyer auf 5/3**, also ÜBER
  seinem Maximum (i. e. unverwundet), während der Lord als Leiche galt. Dieselbe Form trifft jede
  Attached Unit: ein Immortal bekam routinemäßig die Wunden des Plasmancer, und der Plasmancer war
  das gelöschte Modell.
- **Der Fix ist eine IDENTITÄT pro Modell** (`"model"` = Datenblattzeile, `"weapons"` = Waffennamen)
  und `_match_models()` mit DREI enger werdenden Pässen: gleiche Zeile UND gleiche Waffen → nur
  gleiche Zeile → der Rest der Reihe nach. Der dritte Pass IST das alte Verhalten, also lädt eine
  Datei ohne Identität exakt wie bisher (`FORMAT_VERSION` bleibt 1, wie bei `armies` und `missions`).
  **Der zweite Pass ist keine Kosmetik:** `firing_deck.py` und `support_turret.py` verleihen Waffen
  für die Dauer einer Aktivierung, ein mitten darin gezogener Save hat also eine Waffenliste, die
  es beim Neubau nicht gibt.
- **Eine Leiche wird jetzt als Leiche wiederhergestellt** (`_make_casualty()`: 0 Wunden, auf
  `destroyed_models`) statt bloß weggeworfen — dieselbe Behandlung, die `_evict()` einer
  ausgelöschten EINHEIT längst gibt, und der Grund ist derselbe: Reanimation Protocols, Undying
  Legions, Grot Orderly und Vengeful Stars lesen genau diese Liste. Eine geladene Necron-Schlacht
  hat damit dieselben drei Krieger zum Reanimieren wie die, aus der sie gespeichert wurde.
- **Dazu eine KLAMMER auf `current_wounds`**: über das eigene Maximum kann kein Modell mehr
  zurückkommen. Für die Dateien, die schon auf der Platte liegen, ist das alles, was noch zu retten
  ist (ihnen fehlt die Identität) — der Skorpekh Destroyer steht danach auf 3/3 statt auf 5/3.
  Gefahrlos, weil eine Shield Drone `profile.wounds` MITerhöht.

**2. „Wer hat schon gehandelt" stand nirgends in der Datei.** Neu: `game/activation_state.py`.
- **Der AUTOSAVE hat es damals nicht gezeigt, und das war kein Zufall:** er lief an der
  Rundengrenze, dem einen Moment, in dem per Konstruktion jedes dieser Register leer ist. F9 und
  „Save Game" laufen mitten im Zug — und seit 2026-09-12 auch der Autosave, bei jedem Phasenwechsel.
- **EIN Modul statt acht `save_state()`-Methoden**, und das weicht bewusst von der Missions-Regel
  ab: dort trägt jeder Controller eine ANDERE Art Zustand, hier ist es EINE Frage mit acht
  identischen Antworten (Menge von Einheiten bzw. Dict nach Einheit). Was wirklich schiefgeht, ist
  ein NEUNTES Register, das niemand einträgt — und das fängt eine Tabelle plus Quell-Wächter, acht
  verstreute Methoden nicht.
- **Drinnen:** Movement (moved/stationary/advanced + `moved_distance_this_turn` für [HEAVY] 24.16 +
  `advance_bonus_by_squad`, weil 09.06 den Advance-Wurf für die Phase festschreibt), Shooting
  (shot + `last_ranged_attack_turn`, das 13.09s Hidden beendet, + `one_shot_used` für 24.26), Charge,
  Fight, Pile-In, Consolidate, Battle Shock, For The Greater Good — plus **22 Squad-Flags**: die
  Eignungs-Sperren (11.04/09.07/18.02/20.04) und jede „bis Ende des Zuges"-Wirkung, für die CP oder
  ein Battle-Focus-Token BEZAHLT wurde.
- **`one_shot_used` ist nach `(model.id, id(weapon))` gekeyt** — beides ist nach einem Neubau
  wertlos, also wird das Modell über seinen INDEX in der Einheit benannt (dieselbe Reihenfolge, die
  `restore()` zurücklegt) und die Waffe über ihren gedruckten Namen.
- **`restore_activation()` läuft NACH `begin_battle()`**, und hier hat die Ordnung Zähne:
  `begin_battle()` löscht `set_up_this_turn` auf JEDER Einheit (18.02), vorher gesetzt wäre es
  sofort wieder weg. Eigene A/B-Sonde dafür.
- **Bewusst NICHT drin, als EINE Regel statt einer Ausredenliste:** ein Snapshot stellt ein
  GESETZTES Brett wieder her, nie eine halbfertige Aktivierung. Namentlich betroffen:
  `nova_charge_grants`, `attached_ability_grace`, `fired_weapon_types` und `ActionController.states`.

**Getestet:** neu `test_scene_activation.py` (**66/66**, sechs Abschnitte — Abschnitt 1 fährt die
Einheit aus dem echten Save des Users) plus `ab_scene_activation.py` (**13 A/B-Sonden, alle
beißend**). `test_scene_io.py` 73 → **75/75** (Abschnitt 3s Überschrift versprach „verliert seinen
SCHWANZ", was aufgehört hat zu stimmen). Volle Regression **181 Suiten, ~15873 Prüfungen, 180 grün /
0 rot / 1 bekannt**.
- **VIER Sonden bissen zuerst NICHT oder ließen die Suite ABSTÜRZEN, alle vier Befunde über den
  TEST** (Fehlerklasse 24): die wichtigste Sonde stellte nur Pass 1 ab und ließ Pass 2 laufen, also
  gar nicht die Vor-Fix-Welt (Fehlerklasse 16); der Waffen-Fall kam auf dem gewählten Brett
  ZUFÄLLIG richtig heraus, weil die Spezialwaffen vorne stehen und überlebten (jetzt stirbt der
  Fusion-Schütze, und der Flamer-Träger ist das erste überlebende „Storm Guardian"); und dreimal
  wurde in eine leere Liste indiziert bzw. `str.index()` benutzt — **sechste bis achte Instanz**
  derselben Lehre, eine Sonde muss ROT machen, nicht abstürzen.
- **Im ECHTEN Spiel belegt** (`verify_save_load.py`, zwei `main()`-Läufe über `selfplay.py`s echte
  Schleife: spielen → Zustand setzen → Save drücken → die Datei per `--load` in ein zweites `main()`
  → die LEBENDEN Objekte fragen):

  | | gefixt | `--neutralize` (Vor-Fix) |
  |---|---|---|
  | Überlebender von `1 Windriders 1 + Warlock Skyrunners` | **Warlock Skyrunner** 1/2 | **Windrider** |
  | Modelle über ihrem Maximum | 0 | 0 (die Klammer) |
  | Avatar of Khaine hat schon geschossen | **True** | False |
  | ...darf nochmal ziehen | **False** | True |
  | `moved_distance_this_turn` | **6.5** | None |
  | `charged_this_turn` | **True** | False |

  Beide Hälften werden GESTELLT statt abgewartet, und der Grund steht im Modulkopf: ein
  MockAgent-Lauf erreicht in einem festen Framebudget verlässlich keine Schussphase (die
  dokumentierte Harness-Grenze), ein passiver Zähler hätte 0 gemeldet und wie ein Bestehen
  ausgesehen. Alles nach dem Setzen — Capture, Datei, Neubau, Restore — ist echt.
