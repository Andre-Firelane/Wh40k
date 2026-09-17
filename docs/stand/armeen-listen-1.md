# Armeelisten (1): Format und Detachments

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Armeen (armies/*.json) und Listenauswahl

**Die ELF Listen sind DATEN: je eine `armies/<key>.json`.** Fünf Fraktionen, und die T'au stellen
vier davon, die Aeldari drei, die Necrons zwei (siehe die Tabelle unten). Jede Datei ist vollständig — Name, Fraktion, Armeeregel,
Detachments, Force Disposition und jeder Eintrag —, und `ARMY_LISTS` entsteht aus einem
VERZEICHNIS-SCAN. Nichts davon steht ein zweites Mal im Quelltext; eine Liste, die man zweimal
aufschreibt, driftet.

Parameterisiert ist NUR der Owner (`owner=` plus der Namenspräfix über `unit_name()`), damit ein
Screen jede Liste JEDEM Spieler anbieten kann und ein Spiegelmatch zwei getrennte Armeen ergibt.

**Warum JSON und nicht Python** (User: "aus dem game sollte ja mal irgendwann eine ausführbare
Datei werden. wenn dann jemand eine Armeeliste importiert, sollte ja nicht der Quellcode in
army_lists neu geschrieben werden"): ein Python-Modul wird beim Bauen IN die Executable eingebacken,
ein Importer könnte danach keine Liste hinzufügen, und eine importierte `.py` auszuführen wäre ein
Code-Execution-Pfad. Eine Armeeliste trägt — anders als ein Datenblatt mit seinen
`_equip_*(token)`-Callbacks — keinerlei Verhalten, ist also datentauglich. `game/scene_io.py` ist
das Vorbild bis in die Details: `ARMIES_DIR` wird ZUR AUFRUFZEIT gelesen (der Haken, an dem ein
gepackter Build ein Benutzerverzeichnis setzt), `FORMAT_VERSION` wird laut abgelehnt, `summary()`
gibt `None` für Unlesbares.

**Eine Datenbank wäre falsch, und zwar aus einem projektspezifischen Grund:** die Methodik dieses
Repos hängt an `git diff` (`rules/*.md` existiert genau dafür). Bei 130 Datenblättern und 8 Listen
kauft eine DB nichts und kostet die Diffbarkeit. Der Standard des Genres sind ohnehin Datendateien;
Civ V/VI mit SQLite ist die Ausnahme, und die existiert fürs Mod-Merging über zehntausende Zeilen.

### Die drei Module

| Modul | Frage |
|---|---|
| `game/army_io.py` | laden, schreiben, scannen, VALIDIEREN |
| `game/army_roster.py` | `Unit`/`Leader` und der EINE Builder (vier Pässe) |
| `game/army_lists.py` | Registry, `ArmyList`, `FactionChoice`, `get`/`factions`/`apply_to_config` |

**Der Builder hat VIER PÄSSE, und das ist der Kern des Umbaus:** bauen → Enhancements → anhängen →
registrieren. Vorher registrierte jeder Builder INNERHALB der Bauschleife, und 19.01s `attach()`
muss davor laufen — also fiel jede Attached Unit aus der Tabelle in handgeschriebenen Code, und das
ist bei diesen Listen fast alles. Getrennte Pässe machen das unsagbar-falsch: Pass 2 vergibt, solange
jeder Charakter noch sein EIGENES Squad ist (nach dem Merge ist ein Fireblade eines von elf Modellen
und `grant()` lehnt eine mehrdeutige Einheit zu Recht ab — diese Begründung stand vorher dreimal da),
Pass 4 läuft in Roster-Reihenfolge, weshalb ein Transporter immer vor seinem Passagier registriert
wird. `build_tau_retaliation` hatte die halbe Idee schon (eine `leader`-Spalte in der Tabelle, null
Attach-Blöcke); dies ist sie zu Ende gedacht.

**Ein `register(squad)` für DEPLOY hat GENAU EIN Positionsargument** — vier Aufrufer übergeben ein
einargumentiges Callable (`list.append`), ein "sauber" mitgegebenes `pregame.DEPLOY` wäre ein
`TypeError` in vier Dateien.

### Was die Datei sagt

`datasheet`, `color` (PFLICHT, auch am Leader), `composition_index`, `gear`, `choices`, `leaders`
(eine GEORDNETE Liste — Aeldari hängt Farseer DANN Warlock Conclave an, und `can_attach()` erzwingt
das), `transport` (die `id` eines FRÜHEREN Eintrags), `enhancement`, `note` (freier Text, vom Loader
ignoriert — er ersetzt die Kommentare und überlebt einen Importer-Roundlauf).

`destination` gibt es nicht: EMBARK genau dann, wenn ein `transport` dasteht. `RESERVES` benutzt
keine Liste — das entscheidet der Vorspiel-Schritt.

**Der Validator ist stärker als der `NameError`, den er ersetzt.** Die 182 Wargear-Konstanten WAREN
schon Strings, der JSON-Wert ist wörtlich derselbe. Gemeldet wird jetzt aber ALLES auf einmal, je
mit Eintrag und Korrekturvorschlag ("`'Shild Drone'`. Did you mean `'Shield Drone'`?"). Und er
prüft zwei Dinge, die vorher NICHTS geprüft hat: ein `transport`, der auf einen SPÄTEREN Eintrag
zeigt, und ein Enhancement, dessen Detachment die Liste nicht fieldet — letzteres wurde bis dahin
vergeben, kostete Punkte, und `is_active()` gab still `False` zurück. Die vier handgepflegten
`_TAU_ENHANCEMENTS_*`-Slot-Tabellen samt Whitelist sind damit ersatzlos entfallen; ein Slot, den
nichts matchte, wurde vorher stillschweigend ignoriert.

### Was `tau_recon` am Coldstar aufgedeckt hat

Die erste Liste, die vollständig als Datendatei entstand — und sie hat prompt eine Datenblattlücke
gefunden, genau wie der 2026-09-05-Roster es davor tat.

**Der Commander in Coldstar Battlesuit druckt DREI Menüs**: eine Ersetzung der High-output Burst
Cannon aus zehn Optionen, „bis zu zwei" Drohnen, und „bis zu drei der folgenden" aus derselben
Zehnerliste. Die Engine modellierte das dritte als **drei handgeschnittene Bündel** — eine
`WargearOption` je Kombination, die irgendeine Liste zufällig kaufte (`+ 2x Burst Cannon`,
`+ Cyclic Ion Blaster`, `+ 3x Fusion Blaster`).

Das kann zwei Dinge nicht: eine Auswahl von drei VERSCHIEDENEN Items (Coldstar #1 nimmt Cyclic Ion
Blaster + Missile Pod + Weapon Support System), und die drei Support-Systeme überhaupt — **ein
Weapon Support System ist keine Waffe**, und eine `WargearOption` tauscht Waffe gegen Waffen.

**Der Enforcer Commander hatte die gedruckte Form die ganze Zeit richtig** (`support_menu_gear()`
plus zwei Gear-Gruppen). Der Coldstar hat sie jetzt auch, und die drei Bündel sind GELÖSCHT statt
danebengestellt — zwei Arten, „+ 3 Fusion Blaster" zu sagen, wären genau die Drift, die dieses Repo
konsolidiert. Dazu drei fehlende Waffen-Ersetzungen (Burst Cannon, Cyclic Ion Blaster, Missile Pod).

**Verhaltensneutral bis auf eine Buchführung, am Golden Master abgelesen:** 24 Zeilen bewegen sich,
alle nur im `{gear_names}`-Teil; die Waffen in `[...]` sind auf jeder Zeile byte-identisch, und
keine Einheiten-Zeile (Name, Punkte, Modelle, Transport) bewegt sich. Die vier bestehenden
T'au-Listen wurden dafür von `choices` auf `gear` umgestellt — **18 Waffen**, und der Loader hat
jede einzelne Stelle namentlich gemeldet, statt sie still fallen zu lassen.

**Ein vorbestehender Anzeigefehler fiel dabei auf und ist behoben:** `loadout.model_line_groups()`
hängte `gear_names` unbesehen an die Waffenliste, und `support_menu_gear`s Items SIND Waffen unter
demselben Namen — der Enforcer las „3x Missile Pod, 2x Shield Drone, 3x Missile Pod". Verglichen
wird jetzt gegen die ROHEN Waffennamen (`labels` trägt schon Zähler, ein Set daraus trifft nie).
Ein Gear-Item, dessen Waffe anders heißt, bleibt sichtbar — ein Gun Drone gewährt eine Twin Pulse
Carbine, und ein Shield Drone gar keine Waffe; genau dafür ist `gear_names` da.
**Benannte Restlücke:** eine Waffe, deren Profil einen Modus-Suffix trägt (`Cyclic Ion Blaster -
Standard`), matcht ihr Gear-Label nicht und erscheint weiter zweimal. Das MODELL ist richtig.

### Der Golden Master ist das Dauerwerkzeug

`test_army_rosters.py` + `armies/baseline.txt` fingerprinten **8 Listen × 2 Spieler** in
Registrierungsreihenfolge: Namen, `destination`, Transport-Paarung, Punkte, Modellzahlen, **Farbe
pro Modell**, Profil + Waffen, **Gear-Namen**, 19.01-Komponenten mit Rollen, Enhancements. Eine
Listenänderung ist eine Zeile, dann `--write`, dann den Diff lesen.

Er erfasst so viel, weil das meiste davon sonst UNSICHTBAR ist: ein getauschter Drohnentyp bewegt
weder Punkte noch Waffenzahl noch Totals (A/B belegt: 14 Einheiten / 69 Modelle / 1975 pts vor UND
nach dem Tausch), und beim Transkribieren der ersten Datei wurden prompt zwei Farben falsch geraten.
**Die Migration selbst ist damit belegt: alle acht Listen sind byte-identisch** zu dem, was die
Builder produzierten.

**Kein Hash, sondern Text** — ein Hash sagt "etwas hat sich bewegt" und nichts sonst; der Test
druckt die erste abweichende ZEILE.

### Was der Umbau gekostet und gebracht hat

2094 Zeilen (51 % Prosa) → **988 Zeilen Code plus 1123 Zeilen Daten**, und "Fireblade in die
Breacher" ist EINE Zeile in einer 197-Zeilen-Datei statt einer 25-Zeilen-Schleife plus einer
magischen `+ 4` plus eines Slot-Namens plus dreier Docstring-Stellen.

**Duplikation zwischen Listen ist eine bewusste Ausnahme von Fehlerklasse 10:** eine Armeeliste ist
eine DEKLARATION, kein Code, und zwei Listen, die zufällig Einträge teilen, sind trotzdem zwei
Listen. Der Fall, an dem das entschieden wurde, waren `tau` und `tau_epc` mit zwölf gemeinsamen
Einträgen — unter dem geteilten Builder änderte das Editieren der Kauyon-Pathfinder still auch die
Prototypes-Liste, was bug-förmige Kopplung ist. **`tau_epc` ist am 2026-09-07 zurückgezogen worden**,
das Paar existiert also nicht mehr; die Regel steht, weil das nächste Paar sie wieder braucht, und
der Golden Master pinnt jede Liste einzeln, sodass Kopien nicht unbemerkt driften können.

**Zwei Prosa-Leichen fielen dabei auf, beide vorbestehend:** `build_orks`' Docstring listete "2x
Trukk", die der Builder nie baute (`grep -c TRUKK` = 0), und der Kommentar über `ARMY_LISTS` nannte
zwei Primary Missions "DORMANT", die seit den T'au-Listen gespielt werden.

**`_check_positions` bekam nebenbei einen echten Fix:** sein `wanted` war handgepflegt und in drei
Richtungen inkonsistent (Aeldari verlangte 5 für 11 Einheiten, Kauyon 19 bei 18 verbrauchten,
Orks/Necrons/Death Guard übergaben 0 — weshalb `--no-deployment` auf map3 BESTAND und die ganze
Armee still auf (0,0) stapelte, exakt das Versagen, das der Wächter verhindern soll). Jetzt
`len(roster)`.

- **Der Squad-NAME ist ein Identifier**, keine Dekoration: `ai/agent_driver.py`s Planbefehle
  adressieren Einheiten über den exakten Namen, `game/maps.py`s Teilroster nennen sie, und ein
  Szenen-Snapshot schlüsselt darauf. Deshalb ist die Form `"<Spielerziffer> <Datenblatt> <Kopie>"`
  tragend und `army_lists.unit_name()` die eine Stelle, an der sie gebildet wird. Ein Spiegelmatch
  funktioniert genau deswegen: dieselbe Liste zweimal teilt keinen einzigen Namen.
- **Was eine `ArmyList` außer ihrem Roster trägt**: Fraktions-Keyword (damit `sprites.py` das Badge
  über denselben Namen findet, den die Regeln benutzen), Name der Armeeregel und des Detachments.
  **Das Detachment gehört zur LISTE und ist ein TUPEL** (`ArmyList.detachments`) — eine Armee kann
  mehrere gleichzeitig fielden und bezahlt jedes in Detachment Points; einen Auswahl-Screen gibt es
  bewusst nicht (siehe `## Detachments gehören zur LISTE`). `detachment_setting` ist von `ArmyList`
  auf den `Detachment`-Record gewandert.
  Die letzten beiden sind LISTENBAU-Erklärungen und aus den Einheiten NICHT ableitbar — derselbe
  Grund, aus dem `SEER_COUNCIL_PLAYERS`/`AWAKENED_DYNASTY_PLAYERS` existieren, und genau deshalb ist
  `apply_to_config()` das, was aus einer Wahl diese Settings macht. **Es setzt sie NEU statt zu
  ergänzen** — sonst liefe ein Spieler Seer Council weiter, ohne Aeldari auf dem Tisch (im Test in
  beide Richtungen belegt). Die Orks brauchen nichts davon: War Horde gatet am ORKS-Keyword.
- **`game/ui/army_select.py` ist der Auswahl-Screen vor dem Vorspiel** (User: "bevor das Pre game
  losgeht, eine Auswahlmöglichkeit für die Völker/listen ... in großen Kacheln ... Volk
  name/logo/detachment und dann die Porträts der einheiten darin ... wenn man über die Porträts
  hovert, sieht man noch mal im Detail, was in dem Squad drin steckt").
  - **VIER SCHRITTE, EIN MENSCH.** User: "Aber ich wähle für die KI. Die KI soll nicht selber
    wählen." Also kein Spieler-Schritt und ein KI-Schritt: die Person am Rechner beantwortet alle,
    Player 2s Liste wird der KI ZUGEWIESEN. Der Screen läuft, bevor überhaupt ein Agent existiert,
    und importiert nichts aus `ai/` — als Quellprüfung festgehalten, weil das stärker ist als ein
    Aufrufzähler.
    **Seit dem 2026-09-03-Umbau sind es ZWEI Fragen PRO SPIELER** (User: "ich habe vor pro Volk
    mehrere listen anzulegen. daher muss sich der Volk Auswahl Prozess etwas ändern. erst wählt
    man das Volk und dann kommen die verschiedenen Listen zur Auswahl. also in 2 Stufen") — siehe
    `### Volk zuerst, dann Liste` unten.
  - **Die Listen bleiben VORDEFINIERT.** User: "Die Listen sollen auch erstmal predefined sein. Also,
    wir brauchen noch keine Listenbaukosten. Das kommt erst viel später." Der Screen wählt, WER
    WELCHE der drei Listen spielt — er ist nicht der Army-Building-Flow der Später-Liste.
  - **Eine Kachel wird GEBAUT, nicht beschrieben**: die Einheiten kommen aus
    `army_lists.preview_squads()`, das denselben Builder ruft wie `main()`. Eine Kachel mit
    handgeschriebenen Einheitennamen wäre eine zweite Kopie der Armeeliste, und das Erste, was sie
    täte, wäre davon abzudriften.
  - **CHARAKTERE UND SQUADS STEHEN IN GETRENNTEN, BESCHRIFTETEN ABSCHNITTEN** (User: "hier würde
    ich tatsächlich in diesem Screen die Charaktere von den Squads trennen, weil jetzt sieht man
    auf dem ersten Blick schlecht, welche Squads da in der Liste sind"). Ein Porträt pro Einheit
    war genau deswegen zu wenig: eine Attached Unit (19.01) ist EINE Einheit, und ihr Porträt ist
    per `sprites._portrait_model_order()` der CHARAKTER — die Aeldari-Liste zeigte also fünf
    Charaktere und keine der fünf Einheiten, die sie führen. Eine Kachel listet jetzt
    KOMPONENTEN: die Leader/Support-Komponenten links oben unter `CHARACTERS`, die Bodyguards und
    alle übrigen Einheiten unter `SQUADS`, jeweils mit Anzahl. Eine nie angebundene Einheit
    entscheidet über das CHARACTER-Keyword ihrer Modelle (so steht ein allein stehender Illuminor
    Szeras oben, ein Doomsday Ark unten). Beschriftet wird mit dem DATENBLATTnamen, nicht dem
    Squad-Namen — der trägt Spielerziffer und Kopiennummer, was auf einer Kachel niemandem hilft.
    Die Abschnittsköpfe liegen über alle Kacheln auf DERSELBEN Höhe (die Charakterzeilen der Seite
    werden reserviert), damit die Squad-Blöcke der drei Listen vergleichbar untereinander stehen.
  - **Der Hover zeigt `loadout.model_loadout_lines()`** — dieselbe Beschreibung wie die
    Transport-Buttons des Vorspiels, nur für die Modellmenge dieser Komponente. Für eine Hälfte
    einer Attached Unit nennt die Karte zusätzlich die andere ("Leads Guardian Defenders,
    Warlock Conclave - one unit (19.01)"): die Trennung würde sonst genau die Information
    verlieren, die die ungetrennte Fassung noch hatte.
  - **Paginierung, sobald nicht mehr alle Listen nebeneinander passen** (User: "was machen wir,
    wenn es mehr als drei Listen sind? Kann man dann weiterschalten? Gibt es eine Paginierung?").
    **Wie viele Kacheln eine Seite trägt, wird aus der FENSTERBREITE abgeleitet**, nicht fest
    gesetzt: gemessen passen bei 1920 px vier Kacheln zu 446 px, bei 1366 px drei zu 418 px — eine
    feste Drei würde den breiten Bildschirm verschenken, eine feste Vier den schmalen quetschen.
    `MIN_TILE_WIDTH = 400` ist die Untergrenze, `MAX_TILES_PER_PAGE = 4` die Obergrenze (ab da
    vergleicht man leichter durch Blättern als durch Hinüberschauen). Vor/Zurück-Buttons,
    Seitenanzeige, Pfeiltasten UND Mausrad — drei Wege hinein, weil ein Screen, der nur auf eine
    Art blätterbar ist, ein geschlucktes Event von unblätterbar entfernt ist; umlaufend, damit kein
    Knopf je tot ist; die Chrome erscheint nur bei mehr als einer Seite. Die ZELLGRÖSSE wird über
    ALLE Listen bestimmt (Blättern soll die Porträts unter dem Cursor nicht umskalieren), die
    KACHELHÖHE nur über die aktuelle Seite. Ein Seitenindex aus einem breiteren Fenster wird beim
    Verkleinern GEKLAMMERT, sonst zeigt der Screen nichts. Getestet mit einer künstlichen
    Fünf-Listen-Registry (`lists=`) und an drei Auflösungen.
  - **Zellgröße und Kachelhöhe sind ABGELEITET, nicht konfiguriert**, und für alle Kacheln
    DIESELBEN — die Listen haben verschieden viele Einträge, pro Kachel gerechnet stünden
    150-px-Porträts neben 88-px-Porträten auf demselben Bildschirm. Erste Fassung deckelte bei
    88 px und ließ das untere Drittel einer 900 px hohen Kachel leer; gemessen und behoben, als
    Prüfung festgehalten ("die Porträts der vollsten Kachel reichen bis an ihre Unterkante").
  - **DER KACHEL-KOPF WIRD AUS SEINEN ECHTEN ZEILEN GEMESSEN** (User mit Screenshot: "Oben
    überlagert sich text"). Zwei Fehler in einem Bild, und 352 Prüfungen sahen keinen von beiden,
    weil nie etwas den Kopf gemessen hat: der NAME wurde umbrochen, aber `_header_height()` nahm
    flache VIER Zeilen an — also schob "T'au Empire (Prototypes)" auf einer Vier-Kachel-Seite die
    drei Zeilen darunter in die Summenzeile; und Detachment- und Dispositions-Zeile wurden GAR
    NICHT umbrochen, also lief "Auxiliary Cadre + Experimental Prototype Cadre (2 DP)" seitlich aus
    der Kachel in die Nachbarin.
    - **`_header_blocks(entry, text_width)` ist die eine Definition** der vier gedruckten Dinge
      (Name, Detachments, Force Disposition, Armeeregel), jedes an der Breite umbrochen, die es
      wirklich hat — gelesen von der HÖHENrechnung UND von `_draw_tile()`. Vorher waren es zwei
      Meinungen, und beide Hälften standen auf dem Schirm.
    - **Worst case über die Seite, nicht pro Kachel** (`self._header_px`, in `layout()` gesetzt):
      jede Kachel beginnt ihr Porträtraster auf derselben Höhe, was zwei Listen erst vergleichbar
      macht — dieselbe Begründung wie `_lay_out_sections()`' reservierte Charakterzeilen.
      Gerechnet über ALLE Listen, nicht nur die der Seite, damit Blättern das Raster nicht bewegt.
    - **Der Schlussterm ist ABGELEITET** statt der bisherigen festen 18: das ist die Summenzeile
      plus ihre Linie, und bei der größeren Label-Schrift waren 18 sieben Pixel zu wenig — die
      Summe wurde über die Armeeregel gemalt. Das war die zweite Überlappung im selben Screenshot.
    - **Getestet:** `test_army_select.py` 352 → **359/359** (Abschnitt 7d, bei 1920×1080 — vier
      Kacheln, also die fotografierte Seite und die schmalste Kachelbreite: keine Zeile läuft über
      ihre Kachel hinaus, keine erreicht die Summenzeile, der gemeldete Name bricht dort wirklich
      um, und alle vier Raster starten gleich hoch). Ein fremder Pin in
      `test_force_dispositions.py` ist zu Recht rot geworden — er matchte die einzelne
      `self.font.render(...)`-Zeile, die es nicht mehr gibt — und prüft jetzt den Blockeintrag.
      Drei A/B-Sonden, alle beißend.
  - **Eigene Event-Schleife, bewusst**: `main()`s Kette ist ein langes `if/elif` über
    Controller-State und hat fünfmal eine Eingabe geschluckt (Fehlerklasse 15). Dieser Screen
    beantwortet genau eine Frage, bevor es einen dieser Controller gibt, also nimmt er die Events
    selbst. Alles Entscheidende ist eine reine Methode (`layout`/`tile_at`/`portrait_at`/`choose`),
    `run()` fügt nur die Pumpe hinzu. Rahmen, Seiten und Schleife teilt er sich seit der
    Kartenauswahl mit dieser — siehe `game/ui/tile_screen.py` im Abschnitt darüber.
  - **Eine Seite bekommt nie mehr Slots als es Einträge gibt.** Drei Karten auf einem Bildschirm,
    der vier Kacheln trüge, ließen sonst ein Viertel der Breite leer und machten alle drei ein
    Viertel zu klein. Gezählt über ALLE Einträge, nicht über die aktuelle Seite — sonst zöge eine
    angebrochene LETZTE Seite ihre Kacheln breiter als eine volle.
  - **`config.ARMY_SELECT`** schaltet ihn (CLI: `--no-army-select`, `--army1`, `--army2`). Die vier
    Headless-Harnesses stellen ihn AUS — sie beantworten keinen Klick — und ein Quell-Wächter in
    `test_army_select.py` verlangt das von allen vieren, damit ein neuer Harness nicht hängt.
  - **`--load` überspringt ihn**: ein Snapshot hält jetzt fest, welche Listen auf dem Tisch standen
    (`scene_io.armies_in()`), und `main()` baut GENAU die — ohne das würde jeder Einheitenname im
    Snapshot danebengreifen. Optional beim Lesen: ältere Dateien haben die Zeile nicht und laufen
    wie bisher gegen die Settings.

## Detachments gehören zur LISTE (game/detachments.py)

**Ein Detachment ist Teil der aufgeschriebenen Armeeliste, keine Wahl am Tisch** (User: "das
detachment ist fest mit den listen verbunden. man kann sein detachment vor dem spiel nicht einfach
ändern. das detachment gehört zur liste mit dazu und muss dort auch auftauchen"). Ein
Auswahl-Screen war gebaut und ist **wieder ausgebaut** — der Fehler war, "welche Liste" und
"welches Detachment" als zwei Fragen zu zwei Zeitpunkten zu behandeln, während die zweite Teil der
Antwort auf die erste ist.

Was davon BLEIBT und der Grund, warum das Modul überhaupt existiert: ein Detachment ist aus den
Einheiten NICHT ableitbar (ein Crisis-Suit sieht in jedem Detachment gleich aus). Die Liste
deklariert es also, und `apply_to_config(armies)` schreibt diese Deklaration in die
`config`-Konstanten, die die Regeln lesen.

- **MEHRERE gleichzeitig, bezahlt in DETACHMENT POINTS.** `ArmyList.detachments` ist ein TUPEL.
  Jedes Detachment kostet seine gedruckten DP (die "2DP" an seiner Wahapedia-Überschrift, jetzt auf
  dem `Detachment`-Record), und sie kommen aus EINEM Budget: Kauyon (2) + Advanced Acquisition
  Cadre (1) ist ein legales Paar, Mont'ka (3) + Kauyon (2) nicht.
- **Die KOSTEN sind transkribiert, das BUDGET ist eine ANNAHME** — und das steht im Modul.
  Keine geholte Seite nennt eins; "Detachment Points" kommt im ganzen Korpus null mal vor (er
  trägt Datenblätter, Armeeregeln und Detachments, aber keine Kernregeln). **3 ist die
  User-Entscheidung**, gewählt weil die teuersten Einzel-Detachments genau so viel kosten und weil
  das gelieferte Beispiel (Kauyon + AAC) genau darauf kommt. `DETACHMENT_POINT_BUDGET` ist die eine
  Stelle, die sich ändert, sobald die gedruckte Zahl auftaucht. **Im Test gegen den Korpus
  belegt**, dass dort wirklich nichts steht — statt es nur zu behaupten.
- **Die TAG-Regel ist eine ZWEITE, unabhängige Beschränkung** und sie IST transkribiert: "cannot be
  taken with another BATTLESUIT/AUXILIARIES detachment". Zwei 1-DP-Detachments mit demselben Tag
  sind zusammen illegal, obwohl 1+1 ins Budget passt. Genau die zwei Klauseln lagen seit dem
  Regel-Nachzug als "belegte No-ops" herum, weil ein Spieler nur ein Detachment hatte — jetzt sind
  sie scharf. **T'au druckt je einen Tag genau einmal**, die Regel kann auf den echten Daten also
  nicht beißen; der Test misst sie, indem er einem zweiten Detachment denselben Tag gibt — was ein
  künftiges genau so täte.
- **`validate(army_key)` gibt GRÜNDE zurück, keine Bool** — dieselbe Form wie
  `attached_units.can_attach()`: unbekannter Name, kein Detachment, über Budget, doppelter Tag.
  Ein Tippfehler in `ARMY_LISTS` soll als benanntes Problem auftauchen und nicht als
  Detachment-Regel, die still nie feuert.
- **`game/detachments.py` ist weiter der EINE Schreiber** der Settings, jetzt mit genau einem
  Aufrufer (`army_lists.apply_to_config()`). Von Grund auf gesetzt, sonst hielte ein Spieler zwei
  Detachment-Regeln gleichzeitig.
- **Der Screen ist weg**: `game/ui/detachment_select.py` gelöscht, `config.DETACHMENT_SELECT`,
  `PLAYER1_DETACHMENT`/`PLAYER2_DETACHMENT` und `--detach1/--detach2/--no-detachment-select`
  entfernt, die sechs Harness-Opt-outs ebenso (es gibt nichts mehr abzuschalten), und
  `scene_io.detachments_in()` entfällt — der Snapshot nennt die ARMEEN, und die implizieren die
  Detachments. Ein Test hält fest, dass all das WEG BLEIBT. Mit dem Screen ist auch
  `detachments.configured_choices()` gefallen: es existierte NUR, um seine Kacheln zu füllen,
  und stand danach mit null Aufrufern da — dieselbe Behandlung wie der tote Zweig in
  `battle_round_in()`.
- **Die Armeekachel zeigt sie**, weil sie sonst nirgends stehen: `detachment_summary(entry)` gibt
  "Kauyon + Advanced Acquisition Cadre (3 DP)". EINE Funktion, damit Kopfzeile und Kachel sich
  nicht widersprechen können.
- **Sieben fremde Suiten wurden dabei zu Recht rot** und deklarieren jetzt ihre Vorbedingung: die
  T'au-Stratagem-Tests liefen darauf, dass `RETALIATION_CADRE_PLAYERS` per Default BEIDE Spieler
  enthielt. Das ist jetzt leer — niemand hält ein T'au-Detachment, bis eine T'au-Liste gewählt ist
  —, also setzen die Suiten es selbst, wie `test_death_guard_stratagems.py`s `detachment_on` es
  vormacht.
- **Getestet:** neu `test_detachments.py` (**103/103**, sechs Abschnitte; ersetzt
  `test_detachment_select.py`) plus A/B-Sonden auf Budget und Gating. Volle Regression
  **138 Suiten, ~10101 Prüfungen, 137 grün / 0 rot / 1 bekannt**, alle fünf Smokes (inkl.
  `smoke_setup_screens.py --neutralize` weiterhin rot) und `selfplay.py` — auch mit einer
  T'au-Liste, die Kauyon UND Advanced Acquisition Cadre fieldet, beide gleichzeitig aktiv.
