# Brett-Pick und Linien-Formation

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Einheiten auf dem Brett wählen, nicht aus einer Liste (game/unit_pick.py)

**Jede Entscheidung, deren Optionen EINHEITEN nennen, wird durch Anklicken der Einheit
beantwortet** (User: "Immer wenn man eine einheit auf dem schlachtfeld wählen muss (zb wall of
mirrors) will ich die einheit nicht aus einer liste wählen, sondern auf dem schlachtfeld. Wie bei
overwatch"). **56 Aufrufstellen** in ~50 Modulen, von Wall of Mirrors über Isha's Fury und
Heroic Intervention bis zu den fünf Mortal-Wound-Fähigkeiten.

- **KEIN zweites Pending-System, und das ist die tragende Entscheidung.** Der naheliegende Bau
  ist ein `UnitPickController` mit eigener Queue; er wurde verworfen, weil er sofort Fragen
  schuldete, die `DecisionManager` längst beantwortet: wer blockiert den Phasenwechsel, welches
  Overlay besitzt den Klick, und wie erreicht `ai/agent_driver.py`s `_maybe_resolve_decision()`
  eine Option (über den INDEX — eine Wahl außerhalb der Queue wäre für die KI unsichtbar, und sie
  stallte auf einem Prompt, den sie nicht sieht). Ein Brett-Pick ist deshalb **keine neue Art von
  Pending, sondern eine ANSICHT auf eine anstehende Entscheidung**, deren Optionen Einheiten
  nennen. `unit_pick.pending()` ist die eine Antwort darauf; vier Leser lesen sie und sonst nichts.
- **Der Tag reitet IM Optionstupel, nicht in einer Parallelliste.** Eine Aufrufstelle schreibt
  `[(sq.name, lambda s=sq: self.use(s), sq) for sq in candidates]` — ein DREI-Tupel, die Einheit
  neben ihrem eigenen Callback. Die erste Fassung war ein `squads=[...]`-Argument und ist die
  deutlich gefährlichere: 56 Stellen hätten je zwei Listen von Hand ausrichten müssen, und eine
  Fehlausrichtung KRACHT NICHT, sie löst einen Klick auf Einheit A in den Callback von Einheit B
  auf. Im Tupel gibt es nichts auszurichten.
- **`options` ist für jeden Leser unverändert** (Label/Callback am selben Index), also sind
  `choose(index)`, das Overlay und der KI-Pfad **per Konstruktion** unberührt — der Grund, warum
  ~50 Module und ihre Suiten ohne eine einzige Anpassung grün blieben.
- **ZWEI ABSAGEN, beide in die sichere Richtung.** `pending()` gibt `None` zurück — der Prompt
  bleibt das gewohnte Listen-Overlay —, wenn (1) eine getaggte Einheit **nicht auf dem Brett**
  steht (Rapid Ingress bietet Einheiten aus den Strategic Reserves an; Solid-image Projection ein
  Redeploy) oder (2) **dieselbe Einheit ZWEIMAL** angeboten wird (Rapid Ingress listet eine
  Einheit mit Homing Beacon einmal für 1 CP und einmal gratis). Sonst wartete das Spiel auf einen
  Klick, der nie kommen kann — **Fehlerklasse 25, die einzige Klasse hier, die ein harter Deadlock
  ist statt eines stillen No-ops.** Der Wächter ist GENERISCH, eine künftige Fähigkeit mit
  Off-Board-Einheit fällt also von selbst auf die Liste zurück. Lebendigkeit wird an den TOKENS
  gefragt, nicht an `squad.models` (Fehlerklasse 12).
- **Der Prompt zieht ins LINKE PANEL, das Overlay zeichnet NICHTS.** Es dimmt das ganze Fenster
  und säße damit auf genau den Einheiten, die angeklickt werden müssen. `_button_rects` wird
  trotzdem GELEERT, bevor es zurückkehrt — sonst schluckte die Knopfliste des letzten Frames
  weiter Klicks hinter einem Bild, das nicht mehr da ist. Genau die Anordnung, die Burden of Trust
  schon hatte.
- **Die Einheiten werden GERINGT, "wie bei overwatch"** — dieselbe `draw_shoot_targets()`, die
  Fire Overwatchs berechtigte Einheiten zeichnet, statt einer zweiten Bildsprache für dieselbe
  Idee. **Burden of Trust gewinnt das dabei mit:** sein alter Panel-Screen hielt in seinem eigenen
  Docstring fest, dass "nothing on the board itself marks which units qualify".
- **Der Klick-Zweig sitzt INNERHALB von `elif decision_manager.is_pending:`**, und das ist keine
  Bequemlichkeit: dieser Zweig schluckt jeden anderen Klick, solange eine Entscheidung offen ist —
  das ist, was einen NICHT-modalen Pick daran hindert, "Next Phase" unter einer unbeantworteten
  Frage anklickbar zu lassen. Die Gefahr, die die modale Box vorher schlicht durch Im-Weg-Stehen
  deckte.
- **Burden of Trust ist mit umgezogen.** Es war der einzige Brett-Pick des Spiels und hatte ein
  eigenes kleines Pending-System (`pending_pick`-Dict, eigener `main.py`-Zweig, eigener
  Panel-Screen, eigener Term in `_board_gesture_blocked`). Alles davon ist weg;
  `request_unit_pick()` ist jetzt eine Delegation an die geteilte Queue. Zwei Mechanismen für eine
  Frage sind genau die Drift, die dieses Repo laufend konsolidiert.
- **DREI Aufrufstellen sind BEWUSST nicht getaggt, jede mit ihrem Grund IM QUELLTEXT**: Rapid
  Ingress (Einheiten in Reserve, plus dieselbe Einheit zweimal) sowie die Objective- und
  Karten-Listen, die gar keine Einheiten sind. **Solid-image Projection stand hier als vierte
  und ist es seit 2026-09-06 nicht mehr**: es bot jede Einheit ZWEIMAL an (einmal je Ziel) und
  ist in zwei Schritte geteilt — Einheit auf dem Brett, dann das Schicksal als Liste. **Combat Embarkation ist getaggt und fällt bei
  zwei Transportern in Reichweite von selbst auf die Liste zurück** — ein Klick sagt "diese
  Einheit", nicht "dieses Fahrzeug".
- **Getestet:** neu `test_unit_pick.py` (**67/67**, sechs Abschnitte) plus `ab_unit_pick.py`
  (**11 A/B-Sonden, alle beißend**; die ganze Vor-Fix-Welt kippt 17 von 67).
  `test_mission_unit_pick.py` **65/65** auf den geteilten Weg umgeschrieben,
  `test_secondary_missions.py` **553/553** nachgezogen.
  - **Abschnitt 6 ist der tragende: eine MENGENDIFFERENZ an der Quelle.** Ein Verhaltenstest kann
    die 57. Aufrufstelle nicht sehen, weil es sie noch nicht gibt. Also wird jede Optionsliste in
    `game/`, deren Label `<Laufvariable>.name` nennt, gegen eine dokumentierte Ausnahmeliste
    geprüft — in BEIDEN Formen, die eine Optionsliste hier annimmt (Comprehension und
    `append` in einer Schleife). Eine neue ungetaggte fällt namentlich durch. Und die
    Ausnahmeliste darf nicht verrotten: ein Eintrag, der keine ungetaggte Liste mehr enthält,
    ist eine abgelaufene Ausrede und fällt ebenfalls durch.
  - **Zwei Befunde über den TEST, beide von den Sonden** (Fehlerklasse 24): der Verdrahtungs-Pin
    prüfte nur den Teilstring `pick.pick(clicked.squad)`, der ein `if False:` überlebt — er pinnt
    jetzt die ganze geführte ANWEISUNG; und drei Sonden ließen die Suiten ABSTÜRZEN statt rot zu
    werden (Indizieren in ein `None` gewordenes Ergebnis), **neunte bis elfte Instanz** derselben
    Lehre. Beide Suiten degradieren jetzt zu ROT.
- **Im ECHTEN Spiel belegt:** neu `smoke_unit_pick.py` (**6/6**, 45 Frames, in `--smoke` mit).
  Es STAGET die Entscheidung selbst und sagt warum: jeder solche Prompt ist reaktiv, ein
  MockAgent-Lauf erreicht keinen zuverlässig (die dokumentierte Harness-Grenze), ein passiver
  Zähler hätte 0 gemeldet und wie ein Bestehen ausgesehen. Alles danach ist echt — gemeldet wird
  `1 Dark Reapers 1 (5 living models)`, Panel-Screen gezeichnet, **5 von 5 Modellen geringt**,
  Overlay deckt das Brett NICHT ab, und **ein ECHTER Klick auf die Einheit löst die Entscheidung
  auf**. `--neutralize` (die Option verliert nur ihre Einheit) kippt **alle sechs**.
  - **Harness-Falle, eine Runde Debugging wert:** die zwei Vorspiel-SCREENS (`MAP_SELECT`,
    `ARMY_SELECT`) fahren eigene Event-Schleifen, deren Frames kein `turn_tracker` haben — ohne
    `config.MAP_SELECT = False` wird der Pump von der Kartenauswahl leergesaugt und `main()` nie
    erreicht. Der Harness meldet dann wahrheitsgetreu aussehende 6000 Frames und ein leeres
    Locals-Dict.
- Volle Regression **179 Suiten, ~15720 Prüfungen, 178 grün / 0 rot / 1 bekannt**.

### Und die rechte Spalte sagt, WAS man da wählt (game/prompt_rule.py)

**Gemeldet:** *"immer wenn ich aufgefordert werde durch eine Fähigkeit etwas auf dem Spielfeld
auszuwählen. zb. bei necron immortals oder deathguard, schreibe die Fähigkeit Regel mit in die
rechte Spalte, sonst weiß ich gar nicht was ich da auswähle."*

- **Die Ursache ist eine bewusste Entscheidung dieses Features, keine Lücke:** ein Brett-Pick
  zeichnet ABSICHTLICH kein Overlay (es säße auf genau den Einheiten, die angeklickt werden
  müssen). Damit war die ganze Erklärung die eine Prompt-Zeile im linken Panel
  (`Living Lightning - strike which unit?`) plus ein paar Ringe.
- **Der Name der Fähigkeit steht schon im Prompt, also wird er ZURÜCKGELESEN statt ein zweites
  Mal erfragt.** Der naheliegende Bau ist `request(..., rule="Living Lightning")` — verworfen an
  einer Messung: 90 `request()`-Aufrufstellen in `game/`, ~55 davon getaggt, jede eine Chance, den
  Namen falsch oder gar nicht zu nennen, und **nichts würde je rot** (das Panel bliebe leer, also
  genau der heutige Zustand). Die Prompts nennen ihre Regel ohnehin, weil sie für Menschen
  geschrieben sind.
  - **Gemessen über alle 90 Prompts × 300 gedruckte Namen der fünf Fraktionen:** 56 Prompts
    enthalten einen gedruckten Regelnamen; der Rest sind Kernregeln ohne Korpus-Eintrag
    ([PRECISION], Reroll-Angebote, Counteroffensive, Missionen, der Vorspiel-Roll-off) — dort gibt
    es nichts zu zeigen. **NULL Prompts matchten zwei VERSCHIEDENE Regeln**; der eine Doppeltreffer
    ist dieselbe Regel unter zwei Überschriften, der Längster-Treffer-Tiebreak arbitriert also nie
    zwischen zwei echten Antworten.
  - **Wortgrenzen, nicht `in`:** ohne sie beantwortet "Guide" ein "Guided". Der kürzeste gedruckte
    Name ist 7 Zeichen ("Sunforge", "Pech'ra"), keiner davon ein Alltagswort.
  - **Die KLAMMER-Variante ist tragend, nicht kosmetisch:** **29 von 264** gedruckten
    Ability-Titeln enden auf `(Psychic)`/`(Aura)`, während der Prompt den nackten Namen schreibt —
    und darunter sind Guide, Doom und Pestilent Fallout, also ausgerechnet Brett-Picks. Ohne den
    Alias hätte genau die Form, für die das Feature existiert, nichts angezeigt.
- **Die Kandidaten sind nur, was auf dem TISCH steht** — die Datenblätter der übergebenen
  Einheiten plus die Detachment-Stratagems der fragenden Armee. Der ganze Korpus würde die
  Fehltreffer-Fläche vergrößern, ohne etwas zu kaufen: eine Regel, die niemand fieldet, kann nicht
  die fragende sein. Gepinnt, indem derselbe Prompt gegen die FALSCHE Armee `None` liefert.
- **Bei einer 19.01-Anbindung zählen die KOMPONENTEN, und das ist die gemeldete Hälfte:** die
  fragende Fähigkeit gehört dem LEADER (Living Lightning ist die des Plasmancer), `squad.datasheet`
  ist die der Immortals. Nur `squad.datasheet` zu lesen findet die Regel nie — eigene A/B-Sonde.
- **`rules_text.ability_blocks()` ist die strukturierte Schwester von `abilities_for()`** —
  dieselbe "ein Parser, zwei Sichten"-Teilung wie `army_rule_text()`/`army_rule_blocks()`. Gesetzt
  wird mit **`game/ui/rules_body.py`**, dem DRITTEN Konsumenten nach Regel-Leser und
  Stratagem-Tooltip, damit "wie werden gedruckte Regeln gesetzt" eine Antwort behält.
- **Seit 2026-09-06 in der LINKEN Spalte, mit Scrollleiste** (User: "'why you are choosing' soll
  in die linke spalte, nicht rechts"). Die ursprüngliche Messung bleibt richtig und ist der
  Grund, warum die Form sich ändern MUSSTE: das rechte Panel endet bei y=248 und hatte selbst
  bei 1280×720 noch 336 px frei, dort war Abschneiden also vertretbar. Die linke Spalte trägt
  gleichzeitig Prompt, Kandidatenliste und den Ausweg — dort muss eine lange Regel LESBAR
  bleiben statt bloß zu passen, also scrollt sie. Unter allem anderen der Pick-Anzeige, als
  Pixel-Gleichheit darüber gepinnt. Siehe `## Elf Meldungen aus drei Partien`.
- **Gecacht** (0.55 ms → 0.006 ms je Aufruf): das läuft pro FRAME, solange der Prompt offen steht,
  und ein Prompt steht so lange offen, wie der Mensch braucht.
- **Getestet:** neu `test_decision_rule_panel.py` (**42/42**, vier Abschnitte — beide gemeldeten
  Fälle, die Klammer-Variante, die Wortgrenze, VERBATIM gegen die eigene `.md`, und der Kasten auf
  PIXELN) plus `ab_decision_rule_panel.py` (**8 A/B-Sonden, alle beißend**; die Immortals-Sonde
  kippt 16 von 42). **Ein fremder Pin wurde zu Recht rot** (`test_unit_pick.py` pinnte die
  Import-ZEILE `from game import unit_pick` wörtlich und ging kaputt, als ein zweites Modul
  dazukam — jetzt der Import statt seiner Formatierung).
- **Im ECHTEN Spiel belegt:** `smoke_unit_pick.py` (6/6 → **7/7**) staget seinen Prompt jetzt mit
  einem WIRKLICH gedruckten Regelnamen der gestagten Einheit (aus dem Korpus gelesen, nicht
  hingeschrieben) und prüft per Spion, dass `main()` dem rechten Panel genau diese Regel reicht:
  `'Wraith Form' vs prompt's 'Wraith Form'`. `--neutralize` kippt weiterhin alle sieben.
- **BENANNTE GRENZE:** der zweite Mechanismus, mit dem man "etwas auf dem Spielfeld auswählt", ist
  die SCHADENS-Zuteilung (`pending_damage_choice`, ~15 Controller — Death Guards Lethal Ichor,
  Spore-laced Shock Waves, Sickening Impact). Die läuft NICHT über den `DecisionManager`, hat gar
  keinen Prompt-Text ("Choose which model takes the wound") und damit keinen Namen zum
  Zurücklesen — dafür bräuchte es eine Controller→Regelname-Tabelle. Bewusst nicht mitgebaut.

#### NAME, KNOPF, ERKLÄRUNG — die Reihenfolge der linken Spalte (2026-09-09)

**Gemeldet:** *"wenn ich durch eine ability aufgefordert werde, etwas zu wählen, zb Doom oder
Guide … Erst als große überschrift der name der Ability. Dann der Knopf. Unter dem Knopf dann die
Erklärung."* Vorher: generische Überschrift "CHOOSE A UNIT", darunter Prompt, Kandidatenliste und
Hinweis, und ganz UNTEN der Ausweg-Knopf.

- **Die Überschrift ist der GEDRUCKTE Regelname**, und der lag schon vor: `prompt_rule.for_prompt()`
  liest ihn aus dem Prompt zurück (siehe darüber), `main.py` reicht ihn seit dem 2026-09-06 als
  `decision_rule` an genau dieses Panel. Es kostet also keine neue Quelle — nur die Frage, wer den
  Namen zeigen darf. `"CHOOSE A UNIT"` bleibt für die **Kernregeln ohne Korpus-Eintrag**
  (Reroll-Angebote, [PRECISION], Missionen) — kein Rand-Fall, sondern gut ein Drittel der Picks.
- **VERSALIEN und ein HEADER-BAR**, nicht bloß Fettschrift: die zwei anderen Überschriften dieses
  Screens ("WHY YOU ARE CHOOSING", die generische) sind geschrien, und ein gemischt gesetzter Name
  im selben goldenen Balken liest sich als etwas anderes. Der NAME selbst bleibt der des Korpus,
  Klammer-Tag inklusive ("DOOM (PSYCHIC)").
- **`button_style.draw_panel_header(wrap=True)` ist neu und opt-in**, weil die feste Balkenhöhe eine
  Entscheidung ist (vierzig Screens legen sich per `rect.y + N` darunter aus) — nur ein Aufrufer,
  der vom RÜCKGABEWERT stapelt, darf sie wachsen lassen. **Gemessen:** 9 von 147 gedruckten
  Ability-Titeln sind breiter als der 192-px-Titelraum, der breiteste ("Infused with the Blessings
  of Nurgle") um 76 px — eine Zeile ist für diesen Aufrufer also keine Option. Der Ein-Zeilen-Pfad
  ist unverändert, jeder andere Screen zeichnet dieselben Pixel wie vorher.
- **Der SUBJECT bleibt beim Titel** statt in die Erklärung zu rutschen: wo eine Regel eins hat, IST
  es die Frage ("um welches Objective geht es"), und genau darauf ist Burden of Trust gebaut.
- **Der Regelkasten ist jetzt so hoch wie die Regel**, nicht wie die Spalte. Er lief bedingungslos
  bis zur Unterkante, also stand unter einer Ein-Absatz-Regel ein überwiegend leerer Rahmen — was
  sich als nicht geladene Kunst liest, derselbe Grund, aus dem ohne Regel gar nichts gezeichnet
  wird. Sicher an dieser Stelle, weil die BREITE schon feststeht: der Umbruch (und damit `total`)
  hängt nicht an der Höhe, die daraus gewählt wird.
- **Getestet:** `test_decision_rule_panel.py` 53 → **72/72** (3d die Reihenfolge an PIXELN — der
  Knopf unter dem Titel, NICHTS dazwischen, die Erklärung darunter; ein Spion auf
  `draw_panel_header` belegt, dass wirklich der Regelname ankommt; 3e der Kasten gegen zwei
  verschieden lange Regeln), `ab_decision_rule_panel.py` 11 → **16 A/B-Sonden, alle beißend**.
  **Ein fremder Pin wurde zu Recht rot** ("die Zeile über dem Kasten ist pixelidentisch") — der
  TITEL darf sich jetzt unterscheiden; er prüft das erst getrennt und vergleicht dann von der
  Titel-Unterkante bis zur Oberkante des Kastens, also ABGELEITET statt gegen eine runde 200.
  **Zwei bestehende Sonden STÜRZTEN ab statt rot zu werden** (`_rule_view` ist in ihrer Welt None
  — neunzehnte Instanz dieser Lehre) und degradieren jetzt: 52/72 bzw. 59/72 mit benannten Zeilen.

#### Und ein STRATAGEM sagt es in der Überschrift: violett plus CP (2026-09-09)

**Gemeldet:** *"wenn es sich umbei der fähigkeit ind er linken spalte um ein stratagem handelt,
muss schon in der überschrift durch violette farbe zu erkenn esien, dass es sich um ein tratatgem
handelt und die die CP kosten müssen auch teil der Überschrift sein."*

- **Reproduziert vor jeder Änderung** (Cost of Victory, `aeldari_guardian_battlehost`): die
  Überschrift las `COST OF VICTORY`, gold auf navy wie jede andere — und die 1CP standen zwar
  schon auf dem Schirm, aber als ERSTE ZEILE DES REGELKASTENS, also unter dem Knopf und unter dem
  Prompt statt in der Zeile, die man vor dem Entscheiden liest.
- **`prompt_rule.PromptRule` löst das Tupel ab** (`name`, `blocks`, `is_stratagem`, `cost`), und
  das ist der `FooterButtons`-Präzedenzfall: `(name, blocks)` wurde an vier Stellen POSITIONELL
  gelesen, zwei weitere Felder hinten dran wären zwei weitere Positionen zum Verschneiden.
  `__slots__`, kein `__getitem__`.
- **FARBE UND KOSTEN KOMMEN AUS EINER ABFRAGE**, und das ist die tragende Entscheidung: die
  Kosten stehen NUR im Korpus, und der hat sie nur, wo ein STRATAGEM aufgelöst wurde. Sie
  getrennt zu beziehen (Farbe aus `DecisionManager.is_stratagem`, Kosten aus dem Korpus) kauft
  genau einen Zustand, für den diese Bitte keine Antwort hat: eine violette Leiste ohne Kosten
  darin. Der User sagt "die Fähigkeit IN DER LINKEN SPALTE" — das ist die aufgelöste Regel, und
  der Record IST sie.
  **Benannte Folge:** eine Entscheidung mit `is_stratagem=True`, deren Prompt kein Stratagem
  NENNT, bekommt hier die gewöhnliche Überschrift, während `DecisionOverlay` sie violett malte.
  Die zwei stehen nie gleichzeitig auf dem Schirm (ein Brett-Pick zeichnet absichtlich kein
  Overlay).
- **`rules_text.rule_heading()` ist die 36. Extraktion, am zweiten Konsumenten** —
  `RuleStratagem.heading` und `PromptRule.heading` sind derselbe Satz. An beiden Enden
  ausgeschrieben würden sie am TRENNZEICHEN driften, und ein Stratagem hätte zwei sichtbar
  verschiedene Überschriften. Im Test gegen `RuleStratagem.heading` selbst gepinnt, nicht gegen
  ein Literal.
- **Die Violett kommt aus `button_style`s `stratagem`-Palette**, wie die Überschrift des
  `DecisionOverlay` — eine zweite, leicht andere Violett läse sich als andere Art von Ding.
  **FÜLLUNG UND SCHRIFT, wo das Overlay Schrift und Rahmen tauscht:** diese Leiste hat keinen
  Rahmen, das sind ihre zwei Hebel. Und die Farbe trägt die Tatsache nicht allein — die CP
  stehen als TEXT daneben, was ein Graustufen-Screenshot und ein farbenblinder Leser überstehen.
- **Der Kasten wiederholt die Überschrift NICHT mehr.** `_look_up()` stellte den
  `Block("stratagem", heading)` voran, weil der Kasten die einzige Stelle war, die die Regel
  überhaupt benannte; jetzt stünde derselbe String zweimal, vierzig Pixel auseinander.
- **Gemessen über die 67 Stratagem-Überschriften, die die ausgelieferten Listen fielden:**
  **36 brauchen mehr als eine Zeile** in dieser 192-px-Spalte — der Umbruch aus dem Abschnitt
  darüber ist also das, was diese Änderung überhaupt trägt; ohne ihn liefe mehr als die Hälfte
  aus dem Panel. Das Kosten-Suffix ist einheitlich 43 px breit, und **alle 67 drucken eine
  Zahl** — der kostenlose Zweig ist damit ein NETZ und kein Live-Fall, wird deshalb an einer
  konstruierten Regel geprüft (und ist der Grund, warum `is_stratagem` ein eigenes Flag ist
  statt `cost is not None`).
- **Getestet:** `test_decision_rule_panel.py` 72 → **101/101** (neu 3f: die Auflösung an der
  ECHTEN Liste, die Überschrift die wirklich an der Leiste ankommt, die Leiste auf PIXELN —
  violett gefüllt, violett beschriftet, **null** von der gewöhnlichen Goldfarbe —, die
  GEGENPROBE, dass eine Ability-Überschrift gold bleibt und keinen Violett-Pixel trägt, und die
  breiteste gefieldete Überschrift bei 1280×720 samt Knopf und Kasten im Panel). Die gefundene
  Liste wird GESUCHT statt benannt, damit ein zurückgezogenes Roster keinen Absturz erzeugt.
  `ab_decision_rule_panel.py` 16 → **26 A/B-Sonden, alle beißend** (Kosten verworfen; Kind
  verworfen; Kosten am Zeichenort fallengelassen; Accent nie gesetzt; nur Schrift bzw. nur
  Füllung violett; eine EIGENE Violett statt der Palette; `PromptRule` mit eigenem Formatter;
  der Kasten wiederholt die Überschrift). Volle Regression **205 Suiten, ~17932 Prüfungen,
  204 grün / 0 rot / 1 bekannt**, `smoke_unit_pick.py` 7/7.
- **Im ECHTEN Spiel belegt** (`verify_stratagem_pick_heading.py`, `runpy` auf `selfplay.py`s
  echte `main()`-Schleife, `aeldari_guardian_battlehost` als PLAYER 1 — die gemeldete Armeeform,
  und auf der MENSCHEN-Seite, weil "end of your OPPONENT'S Fight phase" die andere Seite fragt):

  | | gefixt | `--neutralize` |
  |---|---|---|
  | Überschrift | **`COST OF VICTORY - 1CP`** | `COST OF VICTORY` |
  | violette Füllung / Schrift | **6210 / 561 px** | **0 / 0** |
  | gewöhnliches Navy / Gold | **0 / 0** | 6394 / 466 px |
  | Frames mit Pick-Screen | 1447 | 1445 |

  **GESTELLT wird EINE Tatsache** — dass die Schlacht überhaupt ein Fight-Phasen-Ende erreicht
  (auf diesem Harness passiv unerreichbar, die dokumentierte MockAgent-Grenze; ein passiver
  Zähler hätte 0 gemeldet und wie ein Bestehen ausgesehen). Alles danach ist echt: der
  Controller erhebt seinen eigenen Prompt, `main()` löst die Regel auf, `main()` zeichnet das
  Panel — und die Farben werden von der LEBENDEN Fläche abgelesen, nicht von den Konstanten, die
  sie erzeugt haben. `--neutralize` stellt die Vor-Fix-Welt an der ABFRAGE her (Kind und Kosten
  verworfen, Überschrift zurück als erster Block des Kastens).

## Total-War-Linien-Formation (rechte Maustaste)

**Einheit auswählen, rechte Maustaste halten und ziehen — der Trupp formiert sich entlang der
Linie, die ZIEH-LÄNGE bestimmt die Frontbreite, die Reihenzahl folgt als `ceil(N/Frontbreite)`**
(User: "kennst du das sqad Drag-Movement von den Total war Spielen … jenachdem wie lang die
gedragte linie wird entstehen dann weniger reihen"). Gilt in BEIDEN Phasen: Aufstellung und
Bewegung. Setzt die erstklassige Auswahl darüber voraus — sie ist der GEGENSTAND der Geste.

- **Drei Prämissen widerlegt, alle tragend.** (1) Button 3 ist NICHT sicher vor der Event-Kette:
  ~40 der ~48 Zweige gaten NUR auf Controller-State, ohne `event.type`-Term, also trifft ein
  Rechtsdruck den ersten anstehenden, dessen Rumpf `button == 1` will, und ist weg — Fehlerklasse
  15 zum sechsten Mal. (2) Der Pitch muss PRO PAAR gerechnet werden. (3) Daraus folgt, dass
  `match_models_to_slots()` hier unbrauchbar ist.
- **Die REIHENFOLGE ist eine PRIORITÄTENLISTE: Charaktere, dann Squadleader, dann Spezialwaffen,
  dann der Rest** (User: "ich hätte gerne eine prioliste. ganz vorne soll es losgehen mit
  Charactere, dann squadleader, dann spezialwaffen" — und zur Teilfüllung: "wenn sie nicht alle
  in den frontrank passen, dann fülle den 2ten rank damit auf ... diese nummerierung soll einfach
  mit priorität aufgefüllt werden"). **Vorher gab es GAR KEINE Reihenfolge:** rein geometrisch,
  wer schon am nächsten an der Linie stand, wurde Rang 1. Empirisch belegt an
  `1 Pathfinder Team 1 + Darkstrider` (11 Modelle, Frontbreite 4, Charakter hinten aufgestellt):
  `rank 1: SGT|spec|spec|spec` — `rank 3: ----|----|CHAR`. Der Charakter landete in der LETZTEN
  Reihe, weil `attach()` Leader-Modelle ans Ende von `squad.models` hängt.
  - **`priority` ist eine Sequenz von STUFEN, keine flache Liste**, und das ist der Grund:
    Geometrie bleibt so der Tiebreak INNERHALB einer Stufe, drei gleichrangige Spezialwaffen
    behalten also ihre Ordnung und ihre Laufwege kreuzen sich nicht — die Eigenschaft, die
    `line_positions()`' Docstring ausdrücklich als Wert benennt. Sicher ist die Umordnung, weil
    die Koordinaten DANACH aus den Radien der jeweiligen Reihe gerechnet werden; ein
    nachträglicher Koordinatentausch wäre es nicht (gemessen: 69 von 133 Basenüberlappungen).
    `front=` ist ERSETZT statt ergänzt — jeder Charakter ist ohnehin Stufe 0.
  - **Stufe 0 ist JEDER `profile.character`, nicht `front_rank_models()`s Nahkampf-Filter**, und
    das ist eine bewusste Abweichung: jenes ist die Messung für die KI-PLATZIERUNG, und sein
    Docstring argumentiert ausführlich dagegen, einen Fernkampf-Charakter nach vorn zu schieben.
    Hier zieht ein MENSCH die Linie und hat genau diese Ordnung verlangt. **Gemessene Folge:** bei
    `Guardian Defenders + Farseer + Warlock Conclave` stehen 3 Modelle (Farseer + 2 Warlocks) in
    Reihe 1, wo `front_rank_models()` **0** liefert. `drag_priority_tiers()` ist die eine Zeile,
    die auf Nahkampf-only umzustellen wäre.
  - **„Spezialwaffe" gibt es als Begriff nicht** — `Squad.unusual_loadout_models()` (Loadout
    weicht von der Mehrheit ab) ist die nächste vorhandene Idee, und der Renderer färbt genau
    diese Modelle schon heller, die Auswahl ist also auf dem Brett sichtbar. **Benannter
    Randfall:** die Mehrheit wird per `Counter.most_common(1)` bestimmt, bei Gleichstand also
    einfügungsabhängig — gemessen **2 von 61** mehrmodelligen Einheiten, beide `The Twin Lance`
    mit genau 2 Modellen, wo die Rangzuteilung ohnehin trivial ist.
  - **Eine LEITER in der Bewegungsphase** (volle Priorität → nur Charaktere → rein geometrisch,
    je nachdem was nicht mehr Modelle stranden lässt), damit eine bloß teure Priorität teilweise
    geliefert statt ganz verworfen wird. Die Aufstellung hat kein Budget und nimmt immer die
    volle. Und `legal_frontage_window()` sweept jetzt MIT derselben Priorität — der Pitch ist pro
    Paar, ein anders geordneter Block hat eine andere Spannweite, und der Sweep hätte dem Spieler
    eine Frontbreite als legal gemeldet, die der Drag dann ablehnt.
  - **NEBENBEFUND, gemessen und mitbehoben: ein Rechts-Drag während einer Reanimations-Platzierung
    stürzte ab.** `line_positions()` las `squad.models` und indizierte `origins` nach der
    TEILMENGE, die `setup.py` übergibt (`placing_models`, bei einer 01.02.03-Rückkehr eine echte
    Teilmenge) → `IndexError`. Der neue `models=`-Parameter behebt es, und die Prioritätsstufen
    hätten sonst exakt dasselbe Problem gehabt.
  - **Getestet:** `test_line_drag.py` 150 → **169/169** (Abschnitt 6, mit einer LIVENESS-Zeile —
    geometrische und Prioritätsordnung müssen wirklich auseinandergehen, sonst besteht alles
    vakuum — plus dem Überlauf bei Frontbreite 2, der Leiter an ihren Sprossen gemessen, und der
    Gegenprobe, dass eine homogene Einheit BYTE-GLEICH wie vorher liegt) und
    `ab_line_drag_priority.py` (**8 A/B-Sonden, alle beißend**; die Teilmengen-Sonde meldet
    `raised IndexError` als rote ZEILE statt den Lauf abzubrechen).
- **Pitch pro Paar (`r_i + r_j + LINE_GAP_IN`), gemessen an 21 Necron Warriors + Technomancer:**

  | Frontbreite | 3 | 4 | 5 | 6 | 7 | 8 |
  |---|---|---|---|---|---|---|
  | pro Paar | 8.35" | 6.45" | 5.54" | 6.06" | 7.34" | 8.36" |
  | einheitlich | 12.96" | 9.83" | 9.04" | 9.83" | 11.77" | 13.31" |

  Einheitlich ist die Attached Unit bei JEDER Breite über 09.02s 9" — also nirgends aufstellbar.
  Für homogene Trupps sind beide identisch. **`LINE_GAP_IN = 0.1`, nicht `MODEL_GAP_IN = 1.5`**:
  die Ring-Konvention kostet gemessen jede legale Breite (20 Boyz bei 8 breit: 8.36" gegen 18.26").
- **`match_models_to_slots()` ist gemessen VERWORFEN**, nicht vergessen: sein Vertrag setzt voraus,
  dass die Slot-KOORDINATEN unabhängig davon sind, wer darin steht — mit Paar-Pitch stimmt das
  nicht, und Umverteilen erzeugte in **69 von 133** gemischten Fällen Basen-Überlappungen, also in
  praktisch jeder Attached Unit. Stattdessen „Reihen ausrichten", ordnungserhaltend: **Mittel
  +0.04"** vom Minimax-Optimum bei **0.03 ms statt 0.9–1.9 ms**, und es kreuzt keine Laufwege.
- **Der Docstring ÄNDERT `pack_positions()`' Anti-Linien-Argument ausdrücklich, statt es zu
  löschen**: dessen Argument ist ganz über SUCHE („die Plätze, die etwas taugen, sind genau die mit
  einer Wand daneben"), hier ZEICHNET ein Mensch. Seine drei GARANTIEN gelten weiter und werden
  anders eingelöst — Pro-Modell-Legalität an die Klammern delegiert, keine Squadmate-Überlappung
  **durch Konstruktion** (auditiert: 0 Verstöße in **39 535 Paaren** über 400 zufällige gemischte
  Roster, engster Abstand exakt 0.1000"), Kohärenz ebenfalls (0/200 Blöcke unzusammenhängend).
- **Tiefe wächst ZUM Trupp hin** (Zentroid der `origins`); die Gegenrichtung kostet gemessen Mittel
  +2.24" längsten Laufweg. Liegt der Zentroid auf der Linie, gewinnt die rohe Linksnormale — mit
  dem dokumentierten Nebeneffekt, dass **andersherum ziehen die Seite spiegelt**.
- **`origins` verhindert, dass das Layout auf seiner eigenen Ausgabe frisst**: während eines Drags
  tragen die Tokens die Vorschau des LETZTEN Frames. `MovementController` übergibt `last_waypoint`,
  `SetupController` seinen Gesten-Schnappschuss (`begin_group_drag` → **`begin_drag`** umbenannt,
  zweiter Bedeutungsträger).
- **Beide Controller tragen `apply_line_drag`/`finish_line_drag` unter DEMSELBEN Namen** — wie sie
  schon beide `apply_group_drag` tragen —, also ist das Beenden verzweigungsfrei und ruft **den
  beim DRUCK gefangenen Controller** (Fehlerklasse 9b). Bewegung: live schreiben, weil eine
  Ghost-Vorschau `clamp_move()` duplizieren müsste, um zu zeigen WER NICHT HINKOMMT — die
  geklammerten Positionen SIND die Warnung; `commit_group_drag()` wörtlich wiederverwendet. Set Up:
  `clamp_drag()` pro Modell (validator-bewusst), Front-Rank immer, **committet nichts**.
- **Kein `move_mode`-Tor** — `can_advance()`s „`move_mode is None` ist die ganze Regel" überträgt
  sich nicht (Advance ist eine Regelentscheidung IN einer Bewegung, dies eine Geste, die Modelle
  bewegt), und `apply_group_drag()` hat aus demselben Grund keines. Kein Eintrag in
  `REACTIVE_MOVE_MODES`: die Geste ÖFFNET keine Bewegung.
- **Nichts wird geklemmt, Confirm lehnt ab** (User-Entscheidung) — deshalb nennt das Readout das
  **legale Frontbreiten-Fenster ab dem ersten Frame**, EINMAL beim Druck gesweept (invariant unter
  dem Drag) und mit `finally` restauriert, weil der Sweep die Modelle zum Messen bewegt. Ohne diese
  Zahl wäre die Ablehnung willkürlich: ein 20-Modell-Trupp ist nur 3–8 breit legal.
- **Die Spannweite wird NACH der Klammer gemessen, die Frontbreite davor** (`game/line_drag.py`).
  Das ist die Stelle, an der dieses Feature am ehesten „funktionierend" und falsch ausliefert: die
  gezogene Linie ist in der Bewegungsphase regelmäßig eine Lüge, und die angeforderte Spannweite zu
  melden wäre ein grünes Readout über einer Formation, die abgelehnt wird.
- **`widest_pair()`/`spread_headroom()` nach `game/squad.py`** — vierter Konsument derselben Frage.
  `check_coherency()` geht jetzt hindurch: gemessen **1.01x**, und der heiße KI-Pfad erreicht die
  Stelle ohnehin nie, weil das Owner-Tor darüber den ganzen Sweep für sie überspringt.
  `measure_crowded_movement.py` unverändert bei **65 %**.
- **Verdrahtung: drei Einfügepunkte, KEINER in der Kette.** Druck/Loslassen als eigenes `if` VOR
  der Kette, Neuberechnung als Frame-Poll DAHINTER, Loslass-Failsafe aus
  `pygame.mouse.get_pressed()[2]`. Kein `continue` (das übersprünge `camera.update_pan`). Die Kette
  darf `line_drag_active` LESEN — die Kamera-Sperre muss —, aber die Geste nie HANDHABEN.
  **`pygame.WINDOWFOCUSLOST` kommt dazu**, weil die Poll-Annahme über den Fokusverlust unter dem
  Dummy-Treiber nicht messbar ist: drei Zeilen statt einer unbelegten Annahme.
- **`_board_gesture_blocked()` gated nur den START**, über `_front_notice()` statt einer zweiten
  Overlay-Liste. Die Regel, die dabei aufzuschreiben war: *eine ANSICHT darf nie gegated werden,
  eine AKTION darf es* — Fehlerklasse 15 sagt nicht „nie gaten", sondern „nie VERSEHENTLICH gaten".
- **Getestet:** neu `test_line_drag.py` (**105/105**, fünf Abschnitte; der Überlappungs-Audit ist
  der tragende) und `smoke_line_drag.py` (**13/13**, `--neutralize` fällt 6 von 13). Dazu **13
  A/B-Sonden, alle beißend** — inklusive der zwei, die die PLATZIERUNG beweisen: Poll wie ein
  Ketten-Zweig gegated → der Drag friert unter einem Modal ein; Druck ebenso → 6 von 10 fallen.
  **Drei bissen zuerst nicht, alle drei Befunde über den TEST:** die Reihen-Zentrierung war
  ungeprüft, die Druck-Sonde zielte auf die Suite statt auf den Smoke, und — die teuerste —
  **`testkit` patcht `random.randint` GLOBAL** (über `game.dice.random`), sodass mein
  `random.randint(2, 24)` den Würfel-Default 1 lieferte: jede „Roster" hatte ein Modell, das Audit
  prüfte null Paare und sah dabei bestanden aus. Es benutzt jetzt eine eigene `random.Random`-
  Instanz und zählt zusätzlich, dass es überhaupt etwas untersucht hat.
- Volle Regression **160 Suiten, ~13851 Prüfungen, 159 grün / 0 rot / 1 bekannt**, `run_tests.py
  --smoke` grün, alle sechs Smokes plus vier `--neutralize`-Gegenproben rot, `selfplay.py` auf map2
  und map3.
- **Vorbestehende Flake benannt, nicht mir zugeordnet:** `test_ere_we_go.py` (mit Orks E2 gelöscht) fiel unter dem
  Parallel-Runner sprunghaft aus (~1 von 3), einzeln nie. **An einem HEAD-Worktree A/B belegt:**
  ohne eine einzige Änderung dieser Arbeit fällt es dort in 2 von 4 vollen Sweeps genauso. Nicht
  ursachenaufgeklärt.

### Direkt aus dem Pool / aus den Reserven, ohne Zwischenschritt

**Ein Rechts-Drag auf dem Brett SETZT eine getragene Einheit am Druckpunkt AB und formiert sie in
derselben Geste** (User: "wenn ich in der aufstellungsphase oder bei reserven meine einheiten
platzieren will, dann muss ich sie erstmal auf der map platzieren und kann dann im 2ten schritt
erst die drag-formation benutzen ... kann das direkt aus der reserve heraus funktionieren? ohne
zwischen step?"). **Reproduziert vor der Änderung:** mit einer Einheit im Pool gibt
`begin_line_drag()` **False** — die Geste hatte nur zwei Türen (`setup.PLACING` und eine gewählte
Bewegungsphasen-Einheit), und in beiden muss die Einheit schon auf dem Brett stehen.

- **`begin_line_drag(start_placement=...)` ist die dritte Tür, und sie ist ein CALLBACK.**
  "Welche Einheit wird getragen, und wohin geht sie zurück" ist `main.py`s Frage — der
  Vorspiel-Sequenzer und die Ingress-Regel besitzen je eine Hälfte, keine gehört in einen
  Input-Handler. **Die REIHENFOLGE ist gepinnt**: eine offene Platzierung gewinnt (`SetupController`
  ist Ein-Slot), sonst die getragene Einheit, sonst die Bewegungs-Route. Andersherum unterbräche
  ein liegengebliebener Pick genau die Platzierung, die gerade justiert wird. Und ein `blocked`
  Druck fragt den Callback GAR NICHT — er platziert eine Einheit, und hinter einem Modal darf nichts
  abgestellt werden.
- **`main.py`s `_place_picked_unit()` ist die EINE Antwort auf "wohin geht die getragene Einheit",
  gelesen von allen DREI Gesten**, die sie ablegen können: ein linker Klick aufs Brett, das Ende des
  Links-Drags, und der Rechts-Drag. Drei Kopien wären drei Chancen, `rapid_ingress_controller.
  consume()` (15.07) zu überspringen oder die Karte nach dem Ablegen getragen zu lassen. Erfolg wird
  am CONTROLLER abgelesen (`setup_controller.state == PLACING`), nicht an einem Rückgabewert:
  `start_ingress()` lehnt eine noch nicht berechtigte Ankunft (20.03) still ab.
- **`dragging_reserve_squad` heißt jetzt `picked_reserve_squad`** (Fehlerklasse 11): "wird gezogen"
  hörte auf zu stimmen, als ein schlichter Klick die Karte GETRAGEN lässt. **EIN Flag, nicht
  "gepickt" plus "gehalten"** — alle drei Gesten gehen durch denselben Helfer, also gibt es eine
  Antwort statt drei. Der Geist folgt dem Cursor und die Karte verlässt den Streifen, der Zustand
  ist also nicht zu übersehen; das grün/rote Platzierungs-Overlay läuft unverändert mit.
- **Der linke Klick aufs Brett legt eine getragene Karte ebenfalls ab** — dieselbe
  Klick-dann-Platzieren-Paarung, die der Vorspiel-Pool immer hatte, und der Grund, warum der
  Rechts-Drag überhaupt eine getragene Einheit vorfindet. Gegated auf `_carrying_a_unit()` und nicht
  auf "ist etwas gepickt": ein Zweig, der matcht und dann nichts tut, SCHLUCKT den Klick
  (Fehlerklasse 15 im Kleinen), und die geschluckten Klicks wären genau die, die die laufende
  Platzierung justieren.
- **Zwei Enden, die der längere Pick braucht.** Ein Frame-Poll lässt ihn VERFALLEN, sobald die
  Einheit nicht mehr in `state.reserves` steht oder die Bewegungsphase vorbei ist —
  `can_ingress()` prüft die Runde, aber nie die PHASE (was `reserves_panel_visible`s eigene Notiz
  schon festhält), sonst schmuggelte der nächste Brettklick eine Ankunft in die Schussphase. Und
  **ESC bekommt eine Sprosse**: getragene Karte ablegen → Auswahl loslassen → (heute) Menü. Ohne sie
  müsste ein Fehl-Pick erst platziert und dann per Cancel zurückgeschickt werden.
- **Der AST-Wächter (`test_event_chain_wiring.py` Abschnitt 4) war SCOPE-BLIND, und diese Arbeit hat
  es aufgedeckt.** Er sammelte per `ast.walk()` auch die Locals VERSCHACHTELTER Funktionen als
  main()-Locals; ein `squad = ...` in einem neuen Helfer ließ ihn eine Zeile melden, die in einer
  ANDEREN Funktion steht, deren `squad` ein PARAMETER ist. Er läuft jetzt nur über main()s eigene
  Ebene (gemessen: 23 nur-verschachtelte Namen hören auf, als Locals zu gelten; die geprüften
  `a.b = c`-Anweisungen fallen von 40 auf 39 — die eine ist genau der Fehlalarm) und nimmt die
  KLEINSTE Bindungs-Zeilennummer statt der zuerst durchlaufenen. **Keine Abdeckung verloren:** ob
  ein Name überhaupt gebunden ist, ist Abschnitt 1s Frage; dieser beantwortet nur, ob schon.
  A/B belegt (eine echte Ordnungsverletzung auf main()s Ebene wird weiter mit Zeile und Namen
  gemeldet).
- **Gemessene Grenze, benannt statt überdeckt:** ein MockAgent-Lauf erreicht **gar keinen** echten
  20.04-Moment — 6000 Frames, und `state.reserves` bleibt für Player 1 durchgehend LEER. Die
  Reserven-Hälfte ruht deshalb auf dem ECHTEN `IngressController` in der Suite plus Quell-Wächtern;
  die Kette selbst ist über die Pool-Hälfte belegt, die durch DENSELBEN Helfer geht.
- **Getestet:** `test_line_drag.py` 105 → **146/146** (neuer Abschnitt 4b: der Druck platziert
  wirklich, am PRESS-Punkt, die Reihenfolge in beide Richtungen, ein abgelehnter Callback fällt auf
  die Bewegungs-Route zurück, und der echte `IngressController` als 20.04-Route) plus neu
  `smoke_pool_line_drag.py` (**16/16**, 21 Frames, in `--smoke` mit; `--neutralize` fällt 7 von 12)
  und neu `ab_pool_line_drag.py` (**11 A/B-Sonden, alle beißend**; die ganze Vor-Fix-Welt kippt 15
  von 146).
  - **Drei Befunde über den TEST, alle Fehlerklasse 24:** ein Wächter matchte seinen EIGENEN
    Docstring (der zählt auf, welche Aufrufe der Helfer macht — also blieb die Suite grün,
    nachdem der echte `consume()`-Aufruf gelöscht war; **fünfte Instanz** dieser Lehre, deshalb gibt
    es jetzt `body_of()`, das den Docstring abschneidet); ein `.index()` ließ die Suite ABSTÜRZEN
    statt rot zu werden (**dritte Instanz**, jetzt `find()`); und zwei Prüfungen indizierten in
    Listen, die in der Vor-Fix-Welt leer sind (**vierte Instanz** — rot statt Absturz ist der Punkt
    einer Sonde).
- Volle Regression **166 Suiten, ~14677 Prüfungen, 165 grün / 0 rot / 1 bekannt**, `run_tests.py
  --smoke` grün, alle neun Smokes plus drei `--neutralize`-Gegenproben rot, `selfplay.py` auf map2
  und map3.
- **Fremde Fehlschläge, nicht dieser Arbeit zugeordnet (Fehlerklasse 20):** mitten im Lauf fielen
  `test_army_select.py`, `test_biomes.py` und `test_map_select.py`. Eine PARALLELE Sitzung baute
  gerade einen Confirm-Button in die Auswahl-Screens (316 uncommittete Zeilen in
  `game/ui/army_select.py`, `map_select.py`, `tile_screen.py`, Zeitstempel sekundenaktuell); keine
  der roten Zeilen berührt eine Datei dieser Arbeit, und alle drei waren zwei Minuten später von
  selbst wieder grün.
