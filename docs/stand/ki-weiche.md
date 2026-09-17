# Die KI-Weiche

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die KI-Weiche: deterministisch fuer die KI, waehlbar fuer den Menschen

**Eine Regel BIETET IMMER AN; der Determinismus lebt auf der ANTWORTSEITE**
(User: "die KI soll das zwar deterministisch anwenden, aber die Funktion selbst soll nicht
deterministisch sein. wenn ein Mensch zb. necrons spielt, muss er die stratagems, Faehigkeiten und
Platzierung der Modelle manuell ganz normal steuern koennen. es muss also eine weiche geben").

Das Muster war in ~83 Modulen schon richtig — `game/mortal_wound_abilities.py:268-279` (Living
Lightning) und `game/technomancer.py:108-127` sind die Referenz: gemeinsame Kandidatenmenge,
`_pick()` als KI-Politik, volle Optionsliste plus „Decline" fuer alle anderen. **Ein mechanischer
Abgleich aller 88 Gates — Owner im Gate gegen den Empfaenger des `decision_manager.request()`, an
das es durchfaellt — ergibt 88 von 88 Treffern.** Die Arbeit bestand also darin, das Muster dort
einzuloesen, wo es fehlte, tot war oder vorgefiltert wurde.

**Warum `auto_players` ueberhaupt existiert, und warum es nie in die Regel gehoert:**
`ai/agent_driver.py:6660 _maybe_resolve_decision()` kann JEDEN offenen Prompt des eigenen Spielers
beantworten — aber ueber das LLM, also kostenpflichtig. `auto_players` ist ausschliesslich dazu da,
die KI **gratis und deterministisch** antworten zu lassen. Eine Regel, die selbst entscheidet, nimmt
dem Menschen die Wahl; eine Regel ohne `auto_players`-Zweig kostet die KI Geld. Beide Haelften
gehoeren zusammen.

**DIE TRENNLINIE, die den Konflikt mit Fehlerklasse 5 aufloest:**
- **Eignung / Inertheit** — die Regel erlaubt es nicht, oder die Option bewirkt NACHWEISLICH nichts
  → weiter fuer alle unterdrueckt.
- **Wuenschbarkeit** — lohnt sich der CP, der Token, das Risiko → **nur KI-Politik**, der Mensch
  wird trotzdem gefragt.

### Eine Definition statt fuenf Schreibweisen

`config.AI_PLAYERS` ist die eine Antwort auf „welche Seite beantwortet die Engine selbst".
`main()` bildet daraus EINMAL `ai_players`/`human_players` (aus `sorted(armies)`, also aus den
Spielern dieser Schlacht abgeleitet statt als zweites Literalpaar) und reicht sie weiter.

Vorher: **82 Literale `("Player 2",)` in `main.py`**, plus vier weitere Schreibweisen derselben
Tatsache — `scouts.human_players` (invers), `pregame.human_player` und `plagues.human_player`
(singular), `deployment_ai.resolve_scouts(ai_players=)` (ein Default, den niemand ueberschrieb) und
`agent_driver.take_one_action(player=)`.

- **EINGEFROREN per Konstruktion, und das ist der Grund, warum die Frage vor der Schlacht gestellt
  werden darf:** jedes der ~83 Module normalisiert in seinem eigenen `__init__`. Keine der
  `set(auto_players)`-Zeilen musste angefasst werden; die sieben `tuple(...)`-Module bleiben
  `tuple` (beide beantworten `in` identisch — sieben Dateien Risiko fuer null Verhalten).
- **SIEBEN Controller lasen `auto_players` und bekamen es nie** (`kauyon_*` x3, `montka_*` x3,
  `aac_autoreactive_camouflage`) → die KI waere dort in `_maybe_resolve_decision()` gelandet und
  haette pro Prompt gezahlt. Heute inert, weil kein Roster diese Detachments fieldet. Jetzt verdrahtet.
- **`resolve_scouts`' Default ist von `("Player 2",)` auf `()` gekippt**: ein Aufrufer, der es
  vergisst, loest jetzt NICHTS auf statt still die Scouts-Bewegung eines MENSCHEN zu nehmen.
- **`ai_players` leer ist erreichbar**, also kehren beide KI-Einstiege (`run_ai_action()`,
  `run_ai_pregame_action()`, EINE Aufrufstelle bei `main.py:5753-5755`) frueh zurueck — sonst
  `IndexError`, und schlimmer: der Agent handelte fuer einen Menschen und zahlte dafuer.
- **Ein Kommentar, der zur Luege geworden waere, ist mitkorrigiert** („Player 2 is this project's AI
  player throughout main.py").

### Was wirklich kaputt war

| # | Fundstelle | Defekt |
|---|---|---|
| A | `pestilent_fallout.py:79-81` | Das Gate war **toter Code** — beide Zweige byte-gleich — und der Controller hatte gar kein `decision_manager`. Ein Mensch bekam das Enfeeble-Ziel von `_best_damage_target` gewaehlt. Sein vier Zeilen frueher gebautes Geschwister `barrage_of_filth.py` hat den Prompt immer gehabt. |
| B | `word_of_the_phoenix.py` | Speicherte `auto_players` UND `decision_manager`, las keines. Lief aus `main.py:3721-3725` bedingungslos fuer den Command-Phasen-Spieler — **auch Spieler 1**. Der Docstring behauptete das Gate, das der Code nicht hatte. |
| C | `ard_as_nails.py:280`, `dlc_sickening_impact.py:135` | `is_worth_using()` lief **vor** dem Split: ein KI-Heuristik entschied, ob ein MENSCH das Stratagem ueberhaupt sieht. `dlc_undying_spite.py` machte es richtig und beschrieb 'Ard as Nails dabei falsch. |
| D | `reanimation_protocols.should_reroll()` | Der Necron-Warriors-Reroll wurde nur angeboten, wenn das KI-Urteil ohnehin ja sagte — bei gewuerfelter 2 oder 3 nie. Jetzt getrennt: `can_reroll()` ist die Regel (samt Inertheit), `should_reroll()` die KI-Politik. |
| E | `resurrection_orb.py:104` | Die KI rankte nach `recoverable_wounds`, der Mensch bekam `candidates[0]` (alphabetisch) als blosses Ja/Nein. Jetzt die volle Kandidatenliste, mit der Wundzahl im Label. |
| F | `bounty_hunters.py` | Waehlte das Beuteziel auch fuer die Farstalker des MENSCHEN, per `target_pick=_best_damage_target` — und hatte weder `decision_manager` noch `auto_players`. |
| G | acht Module | **Jede** Modell-Rueckkehr platzierte engine-gewaehlt — siehe den eigenen Abschnitt unten. |

**Zwei Befunde, die KEINE Aenderung brauchten und deshalb aufgeschrieben statt „behoben" sind:**
`curse_of_the_walking_pox` druckt zwar „you can return", aber beide Haelften sind inert (ein
zurueckkehrendes Modell kommt gratis mit vollen Wunden, und POXWALKERS ist eine Ein-Zeilen-
Datenblatt, also sind alle Kandidaten identisch); und `raid_and_run` / `spiritseer.TearsOfIsha`
haben zwar tote Gates, sind aber fuer BEIDE Seiten unerreichbar (`start_move()` / `resolve()` ohne
Aufrufer) — ein Menschprompt hinter einem toten Pfad waere spekulativ. Der Quell-Waechter
**verifiziert die Unerreichbarkeit**, die Ausnahme laeuft also von selbst ab, sobald jemand sie
verdrahtet.

### Die Platzierung zurueckkehrender Modelle (game/return_placement.py)

Regel 01.02.03: ein zurueckgestelltes Modell wird AUFGESTELLT, und Aufstellen ist Sache des
Spielers. Acht Faehigkeiten holen Modelle zurueck und **alle acht waehlten den Platz selbst, fuer
beide Seiten**. Der Platz war nie illegal — `formation_layout.returning_positions()` setzt in
Kohaerenz per Konstruktion — er war nur nie jemandes Wahl.

- **`SetupController` lernt eine TEILMENGE** (`start_setup(..., models=, positions=, mark_set_up=)`,
  alle drei mit dem heutigen Default). `placing_models` ist die EINE Antwort darauf, welche Modelle
  diese Platzierung bewegt, gelesen von neun Stellen (Stapel-Schleife, beide Drags, Line-Drag,
  `is_placeable()`, die Ueberlappungs-Ausnahme, `cancel_setup()`). **Fuer jeden bestehenden Aufrufer
  per Konstruktion inert** — die volle Regression ist ohne eine einzige Aenderung gruen.
- **Es reitet auf `PLACING` statt einen zweiten Pending-Zustand zu bauen**, und das ist der Kern:
  was `main()` blockiert, MUSS anklickbar UND gezeichnet sein, sonst ist es ein harter Deadlock
  (Fehlerklasse 25). `PLACING` wird bereits blockiert, geroutet, gemalt und hat Confirm/Cancel.
- **DREI Fallen, alle vom Design-Durchlauf gefunden und einzeln gepinnt:**
  - **`mark_set_up=False`** — `confirm_setup()` setzt sonst `set_up_this_turn`, was 18.02 als „darf
    nicht einsteigen" liest. Eine Einheit, die zwei Krieger reanimiert hat, wurde NICHT aufgestellt.
    Faellt erst eine Phase spaeter auf.
  - **Die Ueberlappungs-Ausnahme gehoert der PLATZIERUNG, nicht der Einheit.** Bei einer Teilmenge
    stehen die Ueberlebenden still und muessen gemieden werden — sonst laesst der Drag zu, was
    `confirm_setup()`s squad-weites `check_model_overlap()` am Ende ablehnt. Fehlerklasse 8, die
    schon einmal eine ganze Einheit gekostet hat.
  - **`allow_engaged=True` plus der Validator der Faehigkeit**: 01.02.03 erlaubt engaged, wenn die
    Einheit ohnehin gebunden ist, und der Validator erzwingt genau das pro Position.
- **VIER der acht sind verdrahtet** (Reanimation Protocols, Crude Surgery — seit Orks E3b statt des
  stillgelegten Grot Orderly —, Unquenchable Resolve,
  Curse of the Walking Pox); die anderen vier stehen mit ihrem Grund im Test, damit die fuenfte eine
  sichtbare Einzeiler-Aenderung ist.
- **Aber eine FAEHIGKEIT zu verdrahten ist nicht dasselbe wie ihren TRICHTER zu verdrahten** (User:
  "Einheiten wurde automatisch platziert bei protocol of the undying legion, obwohl ich necrons
  spiele. da scheint sich noch eine automatismus zu verstecken, der nur bei KI greifen soll").
  Fehlerklasse 9 in Reinform — der Trichter ist nicht immer der, der so aussieht.
  - **`reanimation_protocols.reanimate()` hat DREI Aufrufer, nicht einen.** Der Controller der
    Armeeregel bekam seinen Placer; **Protocol of the Undying Legions und der Resurrection Orb
    rufen dieselbe Funktion direkt** und bekamen keinen — also setzte die Engine die Modelle des
    MENSCHEN weiter selbst. `reanimate(placer=None)` faellt per Default auf den alten Pfad zurueck,
    ein vergessener Aufrufer ist also still und sieht von innen richtig aus.
  - **Reproduziert vor jeder Aenderung**, beide Tueren, beide Seiten: der Mensch bekommt seine
    Modelle zurueck und `setup.state` bleibt `idle` — identisch zur KI. Danach `placing` fuer den
    Menschen, `idle` fuer die KI.
  - **Der Waechter ist eine MENGENDIFFERENZ an der QUELLE** (`test_return_placement.py`
    Abschnitt 7): jeder `reanimate()`-Aufruf ausserhalb seines eigenen Moduls muss `placer=`
    mitgeben, und `main.py` muss dem zugehoerigen Controller einen geben. Ein Verhaltenstest kann
    die VIERTE Tuer nicht sehen, weil es sie noch nicht gibt.
  - **Und der Waechter musste den AUFRUFAUSDRUCK pruefen, nicht einen Teilstring** — die eigene
    A/B-Sonde hat das gefunden (Fehlerklasse 24): `"placer=return_placement_controller," in
    MAIN_SRC` ist schon wahr, weil Curse of the Walking Pox es ebenfalls uebergibt, also blieb die
    Zeile gruen, waehrend Undying Legions unverdrahtet war. Jetzt per AST, und in BEIDEN Formen,
    die die Konstruktionsreihenfolge erzwingt (Konstruktor-kwarg fuer den nach dem Placer gebauten
    Controller, Attributzuweisung fuer den davor gebauten — Fehlerklasse 23).
- **Eine RÜCKKEHR-Platzierung trägt jetzt auch 09.02s KOHÄRENZ — im Overlay UND im Drag** (User:
  "immer wenn man Einheiten platzieren muss, zb durch Reanimation, muss man in coherency
  platzieren. dementsprechend muss auch das overlay sein. im Moment geht das über die ganze map?").
  - **Gemessen vor der Änderung, map2:** das Overlay malte **85.9 % des Bretts grün, legal waren
    2.0 %** — **42× zu viel Boden**, und die Ablehnung kam erst beim Confirm. Eine gewöhnliche
    Aufstellung sieht genauso aus (86.8 % gegen 2.6 %).
  - **`position_valid()`s Docstring nannte den Grund und war für diesen Fall falsch:** Kohärenz
    "depends on the whole squad's final positions together, not a single point" — wahr, solange
    jedes Modell der Einheit noch in der Luft ist. Eine RÜCKKEHR ist genau der Fall, in dem das
    nicht gilt: die Überlebenden stehen still und SIND der Anker, also hat "würde dieses Modell die
    Einheit in einem Stück lassen" eine exakte Antwort pro Position.
  - **NUR Teilmengen-Platzierungen** (User-Entscheidung): die gewöhnliche Aufstellung bleibt, wie
    sie ist — dort gibt es keinen Anker —, und die Aufstellungs-KI ist per Konstruktion unberührt,
    weil sie `position_valid()` direkt liest und nie durch `placement_validator()` geht.
  - **Overlay UND Klemmung, nicht nur die Anzeige** (User-Entscheidung): die vier Konsumenten von
    `placement_validator()` sind Overlay, `clamp_drag`, `apply_group_drag` und `pack_positions` —
    also bleibt die dokumentierte Zusicherung "was grün ist, ist da, wo das Modell stehenbleiben
    darf" erhalten, statt an genau dieser Stelle zu brechen. **Gemessen:** ein Zug quer über das
    Brett klemmt jetzt an die Kohärenzgrenze zurück, statt dort zu landen, wo der Confirm ablehnt.
  - **`squad.coherency_probe(models, moving)` beantwortet ZUSAMMENHANG, nicht "hat einen Nachbarn
    in 2\"".** Der schwächere Test ist genau der Fehler, für den `check_coherency()` einst
    umgeschrieben wurde (zwei gegenseitig kohärente Cluster erfüllen ihn, während die Einheit in
    zwei Teile zerfallen ist). Die Sonde berechnet EINMAL die Komponenten der übrigen Modelle und
    fragt je Punkt nur, ob er ALLE berührt — O(Komponenten) statt Graph-Neubau, weil das Overlay
    Tausende Punkte fragt und der Drag bisektiert.
  - **Der gecachte Overlay-Layer musste mitziehen:** die Maske wird bewusst einmal pro Platzierung
    gebaut, und `placement_generation` reichte, solange die legale Fläche eine Tatsache über das
    BRETT war. Der Kohärenzring stammt aus den NACHBARN, und die bewegen sich beim Platzieren.
    `SetupController.overlay_cache_key(token)` ist die eine Antwort darauf — beim Controller, nicht
    im Zeichencode: "wovon hängt die legale Fläche ab" ist eine Tatsache über die Regel. Sie lässt
    das gezeichnete Modell bewusst AUS (sonst würde die Maske bei jeder Mausbewegung neu gebaut)
    und nimmt seine Identität mit auf (sonst teilten sich zwei gleich große Modelle eine Maske, die
    nur für eines stimmt).
  - **Getestet:** `test_return_placement.py` 89 → **111/111** (Abschnitt 9: die GRENZE wird
    gelaufen statt gepinnt — das Modell wandert nach außen, bis der Validator ablehnt, und dieser
    Punkt wird gegen die Regel-Sonde geprüft; der Brücken-Fall zwischen zwei Clustern; die
    unveränderte volle Aufstellung; der Cache-Schlüssel in beide Richtungen).
    `ab_return_placement.py` 13 → **18 Sonden, alle beißend**.
  - **Zwei eigene Testfehler, beide von den Sonden gefunden:** der erste Grenzfall-Punkt war
    konstruiert und scheiterte an ÜBERLAPPUNG statt an Kohärenz (jetzt wird die Grenze abgelaufen,
    was die anderen Terme aus der Antwort hält); und zwei Sonden ließen die Suite ABSTÜRZEN statt
    rot zu werden (Indizieren in `placing_models`, das in der Vor-Fix-Welt leer ist, und `*None`
    aus dem abgebrochenen Lauf) — **zwölfte und dreizehnte Instanz** derselben Lehre.
  - **Im ECHTEN Spiel belegt:** `verify_return_placement.py` misst jetzt zusätzlich die gemalte
    Fläche durch DASSELBE Prädikat, das `main()` dem Renderer reicht — **1.7 % des Bretts** statt
    der 85.9 % davor, bei unveränderten "1 von 5 Modellen platziert / 0 für die KI geöffnet /
    0 bewegte Überlebende".
  - **Und das Overlay zeichnet seither BASISRÄNDER statt Mittelpunkte** (User: "momentan ist die
    Grenze des overlays so dass der Base Mittelpunkt bis zur Grenze gehen kann. intuitiver wäre
    aber der Baserand ... bei Baserand muss jedes Modell unabhängig von der Basegröße den selben
    Abstand einhalten"). Derselbe Handel wie bei den Engagement-Ringen, und aus demselben Grund
    richtig — nur ist hier zusätzlich ein echter Fehler mitgefallen.
    - **Die alte Begründung war eine Tatsache über die REGEL, keine über die Zeichnung.** Jede
      Prüfung dieser Engine misst Kante zu Kante (`edge_distance` = Mittelpunkte minus beide
      Radien), die Regel behandelt also alle Basisgrößen gleich. Die legale MITTELPUNKT-Fläche ist
      dagegen pro Basisgröße eine andere Kurve, das Overlay kann nur EINE zeigen, und `main.py`
      wählte das größte Modell mit der Begründung, dessen Fläche sei "eine Teilmenge jeder
      anderen".
    - **Die Kohärenz hat diese Begründung gebrochen, und das ist gemessen:** sie WÄCHST mit dem
      Radius (`Mittelpunkte ≤ 2" + r_a + r_b`), während Gelände und Brettkante mit ihm schrumpfen.
      An Necron Warriors + Overlord: **8.6 sq.in nur fürs große Modell legal, 9.3 sq.in nur fürs
      kleine** — es gab also gar keine sichere Einzelmaske mehr.
    - **`SetupController.base_edge_zones()` liefert ZWEI Zonen, weil ein Vorzeichen dreht:**
      `keep_out` (Brettkante, Dense-Gelände, fremde Modelle, plus was die Regel ergänzt — hier darf
      KEIN Teil einer Base hin) und `band` (09.02s Kohärenz — dieses Band MUSS die Base erreichen).
      Beide für eine PUNKTFÖRMIGE Base ausgewertet, und genau das macht sie basisgrößenunabhängig.
    - **Beide Lesarten sind die Regel selbst, keine Näherung**: `position_valid()` prüft die
      Scheibe des Modells gegen die Geometrie, also ist "die ganze Base ist aus dem Roten heraus"
      dieselbe Aussage; und `edge_distance <= 2"` heißt, die Base überlappt die um 2" gewachsenen
      Nachbarn, also ist "die Base berührt das Grüne" ebenfalls wörtlich die Regel. Die KLEMMUNG
      bleibt deshalb unverändert bei `placement_validator()` — Bild und Spiel können nicht driften.
    - **Der Punkt-Radius wird geholt, indem der Radius des Tokens für die Dauer JEDES Aufrufs auf 0
      gesetzt wird** (`try/finally`). Damit werden dieselben Prädikate gefragt statt einer zweiten
      Kopie der Regeln, und die IDENTITÄT des Modells bleibt erhalten — ein Stellvertreter-Objekt
      würde sie verlieren, und `position_valid()` nimmt ein Modell per Identität von der
      Kollision mit sich selbst aus.
    - **`max(overlay_models, key=radius_in)` ist ersatzlos entfallen.** Die Keep-out-Linie ist für
      die ganze Einheit dieselbe; nur das Band hängt noch am gezogenen Modell (weil "die anderen"
      je Modell eine andere Menge sind) und bekommt deshalb seinen eigenen Cache-Schlüssel.
    - **Getestet:** `test_return_placement.py` 111 → **132/132** (Abschnitt 10), `ab_return_placement.py`
      18 → **24 Sonden, alle beißend**. **Vier Befunde über den TEST**, alle von den Sonden: der
      Basisgrößen-Vergleich benutzte ein FREMDES Modell (was die Nachbarmenge ändert und damit aus
      einem anderen Grund abweicht — jetzt dasselbe Modell mit getauschtem Radius); er prüfte nur
      zwei 30" auseinanderliegende Punkte, die jede Radius-Abhängigkeit überleben (jetzt zusätzlich
      ein Punkt DIREKT an der Bandkante); der Renderer-Pin prüfte einen STRING, den ein `if False:`
      davor überlebt (jetzt die Erreichbarkeit); und die Radius-Prüfung stand VOR dem ersten Aufruf,
      während der Radius nur währenddessen null ist. Dazu **vierzehnte und fünfzehnte Instanz** der
      "eine Sonde muss rot machen, nicht abstürzen"-Lehre.
    - **Im ECHTEN Spiel belegt** (`verify_return_placement.py`): die Keep-out-Linie ist für eine
      1.26"- und eine 4.2"-Base **an 2745 von 2745 Punkten identisch, 0 Unterschiede**, das Band
      wird gezeichnet, und der Radius des Modells überlebt die Abfrage.
- **Und das BRETT sagt jetzt, WELCHE Modelle gerade zurueckgekommen sind** (User: "Widerbeleben -
  ich kann nicht erkennen, welche einheiten gerade zurueckgekommen sind, um sie zu verschieben.
  bitte hervorheben").
  - **Die Luecke war strukturell, nicht eine fehlende Farbe.** Eine Rueckkehr setzt ein, zwei
    Modelle in eine Einheit, die SCHON STEHT — und die einzige Markierung war
    `draw_placement_identity()`s Umriss um die GANZE Einheit, der fuer die zwanzig Ueberlebenden
    genauso zutrifft wie fuer die zwei neuen Basen. Nichts sagte, welche zwei gerade erschienen sind.
  - **`Renderer.draw_returning_models(surface, board, models)` nimmt eine MODELL-Liste**, keine
    Einheit — genau das ist der Punkt. Dieselbe Form wie `draw_damage_choice_highlight()` eine
    Methode darueber, aus demselben Grund. `draw_placement_identity(..., placing_models=)` ist die
    einzige Naht: eine echte Teilmenge bekommt die Ringe, `None` oder die ganze Einheit zeichnet
    exakt das alte Bild (was jede gewoehnliche Aufstellung will).
  - **WEISS und ein DOPPELring.** Weiss, weil jede andere Brettmarkierung bereits einen Farbton
    besitzt (Cyan Auswahl, Gelb Schadenswahl, Orange Schussziel, Rot Kohaerenz/Feind, Gruen eigene
    Armee, Violett Zuteilung) — ein sechster Farbton waere eine weitere Vokabel, Weiss gehoert
    keinem und liest auf jedem Biom-Boden. Der zweite Ring, weil ein einzelner sich vom
    Auswahl-Umriss nur in der FARBE unterscheidet, und das hier in einem gepackten Blob auf einen
    Blick zu finden sein muss — was die ganze Meldung war.
  - **Die Namensplakette zaehlt sie** ("... - place 2 returning models") und haengt ueber den
    ZURUECKKEHRENDEN Modellen statt ueber der Einheit: die sind es, die gezogen werden muessen, und
    die Ueberlebenden koennen irgendwo stehen. Das linke Panel sagte "Returning Models" schon
    laenger — jetzt hat diese Ueberschrift auch auf dem Brett eine Antwort.
  - **Getestet:** `test_return_placement.py` 132 → **140/140** (Abschnitt 11, auf PIXELN: jedes
    zurueckkehrende Modell hat seinen Ring, KEIN Ueberlebender hat einen, die Ringe sind wirklich
    zwei, und eine gewoehnliche Aufstellung zeichnet gar keine — ohne die letzte Gegenprobe
    bestuende der Abschnitt auch, wenn alles geringt wuerde). Der Test stellt die zwei Modelle
    dafuer FREI: `tk.line_up()` packt Basen 1.4" auseinander, enger als die Ringe breit sind, ein
    Ring liesse sich sonst keinem Modell zuordnen. `test_unit_selection.py`s Quell-Pin auf den
    `draw_placement_identity`-Aufruf ist zu Recht rot geworden und prueft jetzt den
    AUFRUFAUSDRUCK per AST statt einer Zeile Formatierung.
  - **Im ECHTEN Spiel belegt** (`verify_return_placement.py`, dritte Haelfte derselben Sonde):
    `models ringed as RETURNING: 1 of 5 in the unit` ueber 2964 Identity-Zeichnungen;
    `--neutralize` meldet `None of 5` und die Zeile "the board never said which models came back".
    **Die Sonde brauchte dafuer mehr Frames** — ihr altes 1200er-Budget erreicht die erste
    Command-Phase des Menschen gar nicht und meldete 0 Aktivierungen, was wie ein Fehler des
    Gemessenen aussieht statt wie ein zu kurzer Lauf; Default jetzt 3000.
- **Die KI ist unveraendert, und das ist gepinnt**: fuer einen Owner in `auto_players` landen die
  Modelle auf exakt den Punkten, die die Faehigkeit ohnehin berechnet hat, im selben Frame, ohne
  dass etwas geoeffnet wird.

### Getestet

- Neu `test_ai_mode.py` (**29/29**) + `ab_ai_mode.py` (**8 Sonden, alle beissend**),
  `test_deterministic_gates.py` (**38/38**) + `ab_deterministic_gates.py` (**8 Sonden**),
  `test_return_placement.py` (**132/132**) + `ab_return_placement.py` (**24 Sonden, alle
  beissend**; die zwei zusaetzlichen Tueren in `reanimate()` je 5, die Koherenz-Haelfte 4, die
  Basisrand-Darstellung 6).
- **Quell-Waechter gegen die KLASSE** in `test_ai_mode.py`: jedes Modul, das `auto_players` nimmt,
  muss es LESEN (oder an eine Basis weiterreichen — ohne diese Klausel meldet der Waechter die vier
  `CommandPhaseMark`-Unterklassen falsch mit, und ein Waechter mit Fehlalarmen wird geloescht); und
  jeder Controller, den `main.py` baut, muss es am AUFRUFAUSDRUCK bekommen, nicht bloss dem Namen
  nach (Fehlerklasse 24).
- **Im ECHTEN Spiel belegt**, mit Necrons auf BEIDEN Seiten:
  `verify_ai_players_wiring.py` (**83 von 83** Controllern gefuettert, EIN Wert),
  `verify_human_choice_paths.py` (**0** Prompts an die KI, **0** LLM-Fallbacks) und
  `verify_return_placement.py` (der Mensch platziert **1 von 5** Modellen, die Ueberlebenden bewegen
  sich **nicht**, fuer die KI wird **nichts** geoeffnet); dazu
  `verify_undying_legions_placement.py` fuer die zwei ANDEREN Tueren in `reanimate()`, das die LIVE
  von `main()` gebauten Controller aus dessen eigenem Frame nimmt und meldet
  `placement opened for the human: True (placing 1 of 5)` gegen `--neutralize`s `False (0 of 5)` —
  der gemeldete Fehler woertlich. Alle vier **STAGEN die Tatsache selbst** —
  ein MockAgent-Lauf erreicht keine Reanimation, weil nichts stirbt, und ein passiver Zaehler haette
  0 gemeldet und wie ein Bestehen ausgesehen.
- Volle Regression **176 Suiten, ~15366 Pruefungen, 175 gruen / 0 rot / 1 bekannt**, alle Smokes.
- **Eigene Fehler, alle vom Werkzeug gefangen und hier notiert, weil sie sich wiederholen werden:**
  `verify_ai_players_wiring.py` fand sofort einen `TypeError` in `main.py`s `take_one_action`-Aufruf
  (ich hatte die 13 positionellen Argumente auf Keywords umgeschrieben und `memory` als `ai_memory`
  benannt) — **von 15 000 gruenen Pruefungen nicht gesehen, weil keine Suite `main()` faehrt**;
  seither steht dort wieder die positionelle Kette mit nur `player=` angehaengt. Eine Regex ueber
  einen Konstruktoraufruf hat den ARGUMENTBLOCK EINES ANDEREN Controllers verschluckt. Und die
  vierstufige Panel-Kette (`draw` → `_draw_dispatch` → `_draw_pregame_ui` →
  `_draw_pregame_deploying` → `_draw_setup_ui`) war nach dem ersten Anlauf halb verdrahtet — genau
  die Narbe, die `action_panel.py` traegt; ein AST-Sweep „welcher Name wird benutzt, ohne Parameter
  zu sein" hat beide Male die Stelle genannt.

### EIN Schalter: KI-Modus IST Auto-Play (game/ai_mode.py, 2026-09-04)

**Gemeldet nach einer Partie:** *"Protokoll of undying legions wurde wieder automatisch ausgeführt,
obwohl KI Modus aus war"* — und auf die Rückfrage, ob Auto-Play und die Fähigkeits-Gates zwei
verschiedene Dinge seien: *"das ist für mich das gleiche. KI - Modus ist autoplay, erkennbar am
roten punkt. das steuert auch, ob die ki pfade für fähigkeiten und stratagems aktiviert sind.
verstehe nicht warum man das trennen sollte."*

- **Die KI handelte über ZWEI Kanäle, und nur einer hörte auf den Punkt:** `take_one_action()` pro
  Frame (von Auto-Play gegated) und die ~83 `auto_players`-Gates in den Fähigkeits- und
  Stratagem-Controllern (von gar nichts gegated). **Im Log des Users belegt**
  (`game_20260904_174253.log`): `auto-play OFF` in Zeile 17, danach hat der Mensch alle acht
  Player-2-Einheiten von Hand aufgestellt (Kanal eins stand also wirklich), und in Zeile 175 gab
  Kanal zwei trotzdem 1 CP aus.
- **`game/ai_mode.py` ist die Fusion, und der Trick ist die Trennung von WER und OB.**
  `config.AI_PLAYERS` sagt weiter, welche Seite der KI gehört; das Modul sagt, ob diese Seite
  gerade überhaupt von der Engine gespielt wird. **Eingefrorene MITGLIEDER, lebende
  MITGLIEDSCHAFT:** `players()` gibt eine Sicht zurück, deren `__contains__` den Modus mitfragt —
  damit erreicht ein Schalter ~83 Gates, die EINMAL beim Schlachtbau entstehen und nie wieder.
  **Keine der ~90 Lesestellen musste angefasst werden** (alle fragen `x in self.auto_players`),
  nur die 80 Schreibstellen (`set(auto_players)` → `ai_mode.players(auto_players)`).
- **`ai_players` in `main()` IST diese Sicht**, und das gatet den zweiten Kanal gratis mit: beide
  KI-Einstiege beginnen ohnehin mit `if not ai_players: return`, und die Sicht liest sich bei
  ausgeschaltetem Modus als leer — also stehen Frame-Tick UND die Einzelschritt-Taste „A" still,
  ohne dass eine von beiden vom Modus wissen muss. `human_players` ist die lebende KOMPLEMENTÄR-
  Sicht (`ai_mode.humans()`).
- **DEFAULT AN, SCHLACHTSTART AUS** — kein Widerspruch, sondern dieselbe Trennung: ohne laufende UI
  sagen die eingefrorenen Mitglieder alles (~18 Suiten reichen `auto_players=(AI,)` und erwarten
  genau das), und `main()` setzt den Modus dort explizit, wo vorher `ai_auto_play = False` stand.
  Ein Spiel startet also wie immer mit stiller KI, und die zehn Harnesses (alle schicken Shift+A)
  sind unberührt.
- **Der rote Punkt ist ein TOGGLE geworden** (User: "außerdem wäre ein toggle in der oberfläche gut
  für den KI Modus. vielleicht dort, wo jetzt der rote punkt ist"), gezeichnet in BEIDEN Zuständen,
  in der Brett-Ecke oben rechts (anfangs unter dem MENU-Knopf, seit dessen Umzug in die Kopfzeile
  des rechten Panels allein dort — siehe `## Game Menu`). Ein Punkt, den es nur im EIN-Zustand gab, war das
  eigentliche Problem: es gab nichts anzuklicken, um den Modus wieder einzuschalten, und nichts auf
  dem Schirm sagte, dass es ihn gibt. `button_style.draw_toggle()`, also dieselbe Bildsprache wie
  die Schalter im linken Panel samt ihrer drei redundanten Zustands-Signale (Knopfseite, Track-,
  Rahmenfarbe). Der Klick-Zweig steht VOR der ~48-Zweige-Kette (Fehlerklasse 15) und verbraucht den
  Klick, sonst schwenkte er zusätzlich die Kamera.
- **Der Log nennt den Schalter jetzt beim Namen** (`Player 2: AI mode ON (Shift+A).` /
  `(AI toggle)`) — genau die Zeile, die den gemeldeten Fehler überhaupt lesbar gemacht hat.
- **Getestet:** `test_ai_mode.py` 29 → **61/61** (Abschnitte 8-10: die lebende Sicht, der gemeldete
  Fall end-to-end durch den ECHTEN `UndyingLegionsController` mit echtem CP-Konto, eine
  MENGENDIFFERENZ an der Quelle — kein Gate darf eine eingefrorene Kopie halten, und jedes muss
  `ai_mode` wirklich importieren —, und `main()`s Verdrahtung); `test_ai_busy_badge.py` 62 →
  **63/63** (Abschnitt 6 misst den Schalter jetzt in BEIDEN Zuständen, inklusive der
  Graustufen-Probe); `test_game_menu.py` **139/139** nachgezogen.
  Neu **`ab_ai_mode_switch.py`: 8 A/B-Sonden an der QUELLE, alle beißend.**
- **Im ECHTEN Spiel belegt** (`verify_ai_mode_switch.py`, `runpy` auf `selfplay.py`s echte
  `main()`-Schleife): der Schalter wird bei `Rect(700, 40, 92, 26)` gezeichnet — seit dem Umzug des
  MENU-Knopfes weicht er nicht mehr aus, vorher waren es `Rect(700, 50, ...)` —, ein Klick auf genau
  diese Koordinaten kippt den Modus `True -> False`, und der LIVE von `main()` gebaute Controller
  antwortet für **`2 Canoptek Wraiths 1`** — die Einheit aus dem Bericht — mit `mode ON: cp 5->4,
  kein Prompt` gegen `mode OFF: prompt, cp 5->5`. **`--neutralize` reproduziert den Bericht
  wörtlich:** `mode OFF: cp 5->4`, ohne Prompt.
- **Zwei eigene Sondenfehler, beide Fehlerklasse 24:** eine Sonde schrieb
  `ai_toggle_rect = ai_mode.enabled() and draw_ai_mode_toggle(` und die Suite blieb grün (der Pin
  fragte nur, ob ein `elif` fehlt — jetzt muss die Zuweisung ein NACKTER Aufruf sein), und eine
  zweite machte den Klick-Zweig mit `and False` tot statt ihn zu löschen, was die ehrliche
  Vor-Fix-Welt gewesen wäre.

### Und zwei Folgeberichte aus derselben Partie

**Beides Folgen desselben Satzes „KI-Modus aus muss ein echter Modus sein" — der erste ist aber
ein EIGENER Bug, der auch mit eingeschalteter KI zugeschlagen hätte.**

- **Rapid Ingress: gekauft, aber nichts platzierbar** (User: *"Ich habe im letzten spiel als player
  2 rapid ingress für den shard of the voiddragen verwendet, konnte aber danach keine einheit
  platzieren"*). `main()`s Frame-Poll verwarf eine getragene Reserve-Karte, sobald die Phase nicht
  Bewegung ist — und **15.07s Fenster ist per Definition nicht in der Bewegungsphase**: es geht auf,
  während die gegnerische Bewegungsphase ENDET, also nach `advance_phase()`, wenn die Uhr schon
  Schießen sagt. Karte aufnehmen, nächster Frame, Karte weg. Im Log: Fenster in Zeile 259, eine
  Zeile nach „Shooting phase begins", ungenutzt geschlossen in Zeile 313.
  **Nichts mit dem KI-Modus zu tun** — die KI erreicht ihre Reserven über `ai/deployment_ai.py` und
  nie über diesen Pick, weshalb nur ein Mensch darauf treffen konnte. Die Ausnahme gilt GENAU der
  einen Einheit, für die ein Fenster offen ist, damit der Wächter weiter tut, wofür er da ist
  (keine fremde Reserve-Einheit auf dem Rücken eines fremden Stratagems außer der Reihe hereinholen).
- **Ohne KI-Modus ging es vor der Aufstellung nicht weiter** (User: *"es gibt keinen knopf mit dem
  man den roll für attacker/defender auslösen könnte"*). Der Roll-off war nie das Problem — er
  beginnt von selbst, sobald BEIDE Spieler ihre Formations erklärt haben. Was nicht passieren
  konnte, war Player 2s Erklärung: `PregameController` wurde mit dem Default `human_player =
  "Player 1"` gebaut (`main()` hat nie einen übergeben), und das Panel bot genau dessen Einheiten
  an. Also stand dort „Waiting for your opponent..." — für einen Gegner, der bei ausgeschalteter KI
  die Person an der Maus ist.
  **`human_player` (singular) → `human_players` (Menge)**, an allen fünf Stellen: der
  Formations-Start, der Deploy-Roll-off, `_begin_battle()`, `game/plagues.py` und das Panel, das
  jetzt JEDEN menschlichen Owner nacheinander durchgeht und ihn benennt, sobald mehr als einer
  dran ist. `main()` reicht dieselbe lebende Sicht durch, die auch die Regel-Gates bekommen. Das
  war der als offen geführte „zweite Teil" der KI-Weichen-Arbeit.
  **`PregameController.human_player` bleibt als weiterleitende Property** (erster menschlicher
  Owner) — acht Harnesses treiben die Aufstellung darüber, und bei eingeschaltetem Modus antwortet
  sie exakt wie vorher.
- **Getestet:** `test_pregame.py` 125 → **138/138** (neuer Abschnitt „Hotseat", der die gemeldete
  Sackgasse als Vor-Fix-Welt festhält: mit EINEM Menschen zeigt das echte Panel **keinen einzigen
  Knopf**, und der Roll-off beginnt nie); `test_line_drag.py` 146 → **150/150** (Quell-Pins auf die
  Ausnahme, samt der Gegenprobe, dass sie NICHT auf „irgendein Fenster ist offen" verallgemeinert).
  Beide sind in `ab_ai_mode_switch.py` mit je einer beißenden Sonde belegt.

### Bewusst offen

- **Der SCHALTER steht (siehe oben), die FRAGE zu Schlachtbeginn nicht.** `config.AI_MODE_SELECT`
  liegt weiter bereit und hat weiter keinen Leser: der Modus wird heute im Spiel umgelegt (Toggle
  in der Brett-Ecke oder Shift+A), nicht vor der Schlacht erfragt (User: „Frage am Anfang der
  Schlacht durch ein promt, ob der ki Modus an oder aus sein soll"). Sie
  gehoert nach `main.py`s `run()` — zwischen Game-Menue und `main()` —, weil alle zehn Harnesses
  `main.main()` DIREKT rufen: dort kostet ein Screen **null** Opt-outs, in `main()` zehn plus einen
  Waechter. Mit „KI aus" muessen zusaetzlich `pregame.human_player` (singular) zu einer MENGE werden
  und die beiden KI-Treiber gegated bleiben.
- Die vier uebrigen Rueckkehr-Faehigkeiten (siehe oben), und `reanimate()`s zwei restliche
  Unterentscheidungen (welches Modell geheilt wird, welches zurueckkommt) — beide heute noch
  deterministisch fuer alle. Vor dem Bau ist die PROMPTZAHL zu messen: Reanimation feuert fuer jede
  Einheit jede Command-Phase, und ein Prompt pro Wunde koennte schlimmer sein als das, was er behebt
  (`measure_stim_injectors_prompts.py` ist die Vorlage).
- `raid_and_run` und `dlc_signal_pox` sind fuer BEIDE Seiten unverdrahtet — eine andere
  Fehlerklasse als die gemeldete, hier benannt statt nebenbei gebaut. **`plasmacyte` stand
  bis zur Necron-Etappe 3 in dieser Liste**: sein Grant, sein Per-Phasen-Reset und sein
  Markenzaehler waren verdrahtet und nichts hat je GEFRAGT. Behoben, als die Ophydian
  Destroyers dieselbe Zeile woertlich druckten — der zweite Traeger ist der Ort, an dem
  eine fehlende Haelfte sichtbar wird.
