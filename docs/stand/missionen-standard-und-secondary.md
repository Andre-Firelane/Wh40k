# Standard-Missionen und Secondary-Kartenstapel

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Missionen (game/missions.py, game/secondary_missions.py)

### Die erste Schlachtrunde zahlt keine Primary-VP

**`missions.PRIMARY_FIRST_SCORING_ROUND = 2`** (User: "außerdem sollte man im ersten zug noch keine
vp für objectives bekommen. erst ab zug 2").

- **Das ist Hold the Line, das nachzieht, was jede Force-Disposition-Karte längst DRUCKT.** Alle
  fünf banden ihre Objective-Boxen auf "2ND ROUND ONWARD" (`primary_missions.SECOND_ROUND_ONWARD`);
  die Standard-Primary war die EINZIGE, die noch für das Brett zahlte, wie es nach der Aufstellung
  stand — wer auf drei Objectives aufstellte, hatte eine volle Runde VP, bevor ein Modell gezogen
  war. Im Test gegen `SECOND_ROUND_ONWARD` gepinnt, nicht gegen ein Literal.
- **BENANNTE AUSNAHME, bewusst stehengelassen:** Battlefield Dominances "MORE OBJ"-Box ist auf ihrer
  Karte "Rounds 1-2" gedruckt, und eine transkribierte Regel gewinnt gegen diese hier. Als eigene
  Testzeile festgehalten, damit sie nicht wie eine übersehene Stelle aussieht.
- **`battle_round` hat KEINEN Default** — dieselbe Begründung wie bei `_detectable_models()`: eine
  Aufrufstelle, die es vergisst, wäre still wieder der gemeldete Fehler und kein kleinerer. Alle drei
  `main.py`-Aufrufe reichen `turn_tracker.battle_round`; ein Quell-Wächter liest die AUFRUFAUSDRÜCKE
  und würde einen vierten mit hartkodierter Runde melden.
- **Beide KI-Prompts sagen es jetzt** ("round 1 pays nothing, so round 1 is for getting onto the
  objectives, not for sitting on the ones you deployed on"). Der Planner wägt Boden gegen Kills mit
  genau dieser Arithmetik ab — eine Rundenbande, die nur die Engine kennt, ist jeden Zug ein
  falscher Plan, und nichts im Spiel widerspricht ihr.
- **Getestet:** `test_standard_missions.py` 33 → **44/44** (neuer Abschnitt 1b, beide Seiten der
  Grenze gemessen — "< 2" als "< 3" geschrieben bestünde sonst mit); drei A/B-Sonden in
  `ab_pregame_starts_once.py`, alle beißend. **Im ECHTEN Spiel belegt:**
  `verify_pregame_starts_once.py` meldet in Runde 1 `none`, `--neutralize` meldet die Zahlungen.

### Die Raten der Standard-Missionen (User-Handicap zugunsten der KI)

**Hold the Line zahlt 6 statt 3, No Mercy 3 statt 1** (User: "ändere die Missionen der ki leicht.
primary gibt 6 Punkte pro objektive, statt 3. und secondary gibt 3 statt 1").

- **"Die Missionen der KI" ist, was sie im AUSGELIEFERTEN Zustand sind — keine von beiden gehört
  einem Spieler.** Hold the Line spielt jeder, der NICHT in `config.PRIMARY_MISSION_CARD_PLAYERS`
  steht, No Mercy jeder, der nicht in `config.SECONDARY_MISSION_CARD_PLAYERS` steht — und beide
  Tupel nennen Player 1, den Menschen. Heute erreichen die Raten also nur die KI; leert ein Harness
  eines der Tupel, bekommt sie der Mensch auch. Steht als Kommentar an den Konstanten.
- **Die Zahl stand an VIER Stellen, und drei davon hätten still veralten können:** die Konstante,
  der gedruckte Kartentext auf dem Missionsstreifen, und BEIDE KI-Prompts. Der Kartentext und die
  Prompts interpolieren sie jetzt aus `game/missions.py`, statt sie zu wiederholen.
- **Der Prompt ist die gefährlichste davon.** Der Planner wägt Boden gegen Kills mit exakt dieser
  Arithmetik ab; eine veraltete Rate dort ist jeden Zug ein falscher Plan, und nichts im Spiel
  widerspricht ihr. Das wäre die Sorte Änderung, die fertig AUSSIEHT und es nicht ist.
- **Die Beratungsregel überlebt die Umstellung**, und das ist geprüft statt angenommen: "Boden zahlt
  wiederholt, ein Kill einmal" gilt bei 6/Runde gegen 3 einmalig weiterhin — nur der Wechselkurs
  verschiebt sich (ein Kill ist jetzt eine halbe Objective-Runde statt einer drittel).
- **Die Ökonomie-Tabelle weiter oben hat sich dadurch UMGEDREHT** — Hold the Line liegt jetzt vor
  den fünf Force-Disposition-Karten statt gleichauf. Bewusst: es ist ein Handicap-Regler, keine
  Balance-Messung. Dort ausgeschrieben, damit die alte Aussage nicht als Messung stehenbleibt.
- **Getestet:** neu `test_standard_missions.py` (**33/33**) — **zu diesem Modul gab es vorher GAR
  KEINEN Test**, die zwei Raten wurden nur nebenbei als Literale in drei anderen Dateien
  behauptet, was genau der Weg ist, auf dem eine Neujustierung halb ankommt. Abschnitt 3 ist der
  tragende: jede Stelle, an der eine Rate GEZEIGT oder ERZÄHLT wird, muss aus der Konstante kommen —
  mit der Gegenprobe, dass die ALTEN Zahlen nirgends mehr stehen ("quotes the new number" besteht
  auch auf einem Prompt, der beide enthält). Drei fremde Pins nannten die alte Rate als Literal und
  sind auf die Konstante umgestellt, also kostet die nächste Justierung EINE Zeile.
  Neu `ab_mission_rates.py`: **9 A/B-Sonden, alle beißend**, darunter die zwei, die nur die
  Prompts zurückdrehen.
- **Im ECHTEN Spiel belegt:** `selfplay.py map2` protokolliert
  `Player 2 scores 6 Primary point(s) (controls 1 objective(s))`.
- **Eigener Testfehler, der dabei auffiel und ein echtes Merkmal des Moduls ist:**
  `record_destroyed_squad()` dedupliziert über `id(squad)`, und ein inline erzeugtes Squad wird
  sofort wieder freigegeben — CPython vergibt dieselbe id an das nächste, drei Opfer zählten also
  als eines. Im echten Spiel harmlos (die Squads leben auf dem Brett), aber eine Falle für jeden
  Test, der das Modul direkt treibt.

Primary **"Hold the Line"** (**6** VP je kontrolliertem Objective, zu Beginn der eigenen
Command-Phase)
gilt für BEIDE Spieler, **außer für wen `config.PRIMARY_MISSION_CARD_PLAYERS` nennt** — der spielt
die Force-Disposition-Primary des Abschnitts darüber. `score_primary()` trägt den Early-out an
EINER Stelle, nicht an seinen drei Aufrufstellen. Die Secondary **"No Mercy"** (**3** VP je zerstörter
Feindeinheit) gehört jetzt nur noch der KI: wer in `config.SECONDARY_MISSION_CARD_PLAYERS` steht
(= Player 1, der Mensch), spielt STATTDESSEN einen **Tactical-Secondary-KARTENSTAPEL**. Der Flag ist
eine Listenbau-Erklärung, aus dem Brett nicht ableitbar — dieselbe Begründung wie
`SEER_COUNCIL_PLAYERS`. `BATTLE_ROUNDS = 5` liegt weiter in `missions.py`, weil Missionen die
Spiellänge definieren.

- **Der Ablauf** (User-Vorgabe, keine Kernregel): zu Beginn der EIGENEN Command-Phase zwei Karten
  ziehen → Klick-weg-Overlay zeigt sie → sie landen in der Leiste links. Handkartenzahl ist
  **unbegrenzt**. Ist die Bedingung einer Karte an ihrem eigenen Zeitpunkt erfüllt, wird GEFRAGT
  ("jetzt einlösen oder behalten") — **nie automatisch gutgeschrieben**. Am Ende des eigenen Zuges
  kann stattdessen eine Karte für **+1 CP** abgeworfen werden. Höchstens **15 Secondary-VP pro
  Schlachtrunde**.
- **Der Stapel wird NICHT nachgemischt** (User-Entscheidung): jede Karte einmal pro Schlacht, danach
  läuft er leer. Mit den bisher zwei Karten heißt das: Runde 1 zieht beide, ab Runde 2 nichts mehr.
- **Der +1-CP-Deckel ist NICHT nachgebaut** — `CommandPointManager.gain_cp()` trug ihn schon
  (`BONUS_CP_PER_ROUND_CAP = 1`, geteilt über ALLE Bonus-Quellen). Neu ist nur
  `bonus_cp_remaining()`, gelesen von `gain_cp()` UND vom Angebot, damit ein Abwurf nicht angeboten
  wird, der 0 CP brächte (Fehlerklasse 5). Zweiter Konsument → eine Definition.
- **Die 15-VP-Grenze KLAMMERT statt abzulehnen**, und das Prompt-Label sagt es
  ("Score 3 VP (this round's 15 VP cap)"). Ist die Runde ganz ausgeschöpft, wird gar nicht erst
  gefragt.
- **Der Kartenstreifen ist BEWUSST reine Anzeige.** Die Karten liegen bei
  x ≥ `left_panel_rect.right`, also INNERHALB `board_rect_screen` — ein Klick fiele durch die
  zustandsgegatete Kette auf den Board-Zweig (Kamera-Schwenk). Ein neuer Zweig davor wäre genau
  Fehlerklasse 15. Deshalb läuft JEDE Wahl über `DecisionManager`, den Overlay, der ohnehin jede
  andere Entscheidung des Spiels zeichnet. Nebeneffekt: `_maybe_resolve_decision()` könnte die Karten
  ohne Zusatzverdrahtung für einen KI-Spieler beantworten.
- **Layout: Akkordeon statt Schlitze** (User: "nicht vertikal an der Leiste hängen, sondern
  horizontal übereinander geschichtet … fahren sie aus wie ein Akkordeon-System"). Eine Karte ist ein
  volle Breite hoher **Balken (28 px)** mit Kategorie, Namen und STATUS. Hover öffnet die HÖHE genau
  einer Karte.
  - **Der Status einer Secondary nennt IHREN Zeitpunkt ("end of your turn"), keine Live-Erfüllung.**
    Die erste Fassung zeigte eine Momentaufnahme ("würde das punkten, wenn der Zug jetzt endete") als
    `READY` — und damit stand Centre Ground schon in der Bewegungsphase auf erfüllt (User: "mir ist
    aufgefallen, dass ich gerade Center Ground mitten im Zug schon erfüllt habe … Center Ground wird
    erst am Ende meines Zuges erfüllt"). Eine Karte wird an IHREM gedruckten Zeitpunkt gemessen und
    an keinem anderen; die Mitte zu halten ist bis dahin eine Stellung, kein Punktestand — und ein
    Balken, der etwas anderes behauptet, lädt genau zu dem Zug ein, der sie vor Zugende wieder
    hergibt. `READY - n VP` (grün) erscheint jetzt ausschließlich, solange der Einlöse-Prompt DIESER
    Karte offen steht; die Quelle dafür ist `offered_now()`, nicht `achieved()`. Der alte Aufbau war die andere
  Achse (150-px-Karten, Breite 26→250, Titel um 90° gedreht) und skalierte nicht: vier Karten
  brauchten schon 648 px. **Player 2s Karten sind ganz raus** (User-Vorgabe).
  - **Überlauf = SCHINDELN**: passt die Hand nicht mehr, wird der Abstand negativ und die Balken
    überlappen, geklammert auf `MIN_BAR_OVERLAP_STEP = 12` sichtbare Pixel je Karte. Gemessen: 42
    Karten passen exakt bis `TOP_MARGIN`. Genau das macht die unbegrenzte Hand ohne Paginierung
    möglich.
  - **Das VORZEICHEN des Bottom-up-Akkumulators ist die Stolperstelle**: nach oben gebaut liegt die
    Unterkante der nächsten Karte einen Abstand ÜBER der Oberkante dieser — ein negativer Abstand muss
    also SUBTRAHIERT werden. Falsch herum spreizt es die Balken, statt sie zu schindeln, und der
    Stapel läuft still oben aus dem Bild (gemessen: `top = -472`). Mit drei Karten sieht das gesund
    aus, mit dreißig nicht. **A/B belegt:** Vorzeichen zurückgedreht → 4 Prüfungen fallen.
  - **Trefferprüfung von OBEN nach unten** (zuletzt gezeichnete Karte zuerst): geschindelte Balken
    überlappen, und die obenauf gezeichnete ist die, auf die der Cursor zeigt.
  - Hover wird wie bisher GEPOLLT (`pygame.mouse.get_pos()` in `draw()`) — nichts hängt in der
    Event-Kette. Kosten gemessen: 0.21 ms/Frame bei 2 Karten auf einem 130-Modell-Brett
    (40 Karten: 3.2 ms, mit dem Zwei-Karten-Stapel unerreichbar).
- **`game/ui/mission_draw_overlay.py`** ist das Klick-weg-Overlay, nach `StratagemNoticeOverlay`
  gebaut (QUEUE, nicht Slot). Es steht in der Kette ÜBER dem Stratagem-Hinweis: die Karten sind ab
  dem Ziehen auf der Hand, also soll man sehen WAS man gezogen hat, bevor irgendetwas daraus zu
  entscheiden ist. Es gatet die KI an denselben drei Stellen wie sein Geschwister — im Test daran
  gepinnt, dass beide Zählungen GLEICH sind.
- **NUR EIN MODAL GLEICHZEITIG** (`main.py`s `_front_notice()`, `test_one_modal_at_a_time.py`).
  User: "Ich möchte keine gleichzeitigen Overlays. Das soll wieder nacheinander kommen: erst das
  Overlay, wer am Zug ist, und danach die Secondaries." Ursache war ein Auseinanderfallen von
  EINGABE- und ZEICHEN-Priorität: die Event-Kette ist ein `if/elif`, also besitzt genau EIN Overlay
  die Klicks — der Renderer zeichnete aber alle fünf bedingungslos übereinander. Die hinteren
  lugten unbeantwortbar hervor. Sichtbar wurde es erst durch das Missions-Overlay, weil Zug-Banner
  und Kartenzug BEIDE zu Beginn der Command-Phase feuern. `_front_notice()` ist jetzt die eine
  Definition der Reihenfolge (Zug-Banner → Turn-Plan → Missionen → Stratagem → WAAAGH!); gezeichnet
  wird nur das vorderste, und der Decision-Overlay wartet ebenfalls, weil er unter einem Notice
  ohnehin nicht anklickbar ist. Das `suppressed=`-Argument des Würfelpanels liest jetzt dieselbe
  Funktion, statt eine eigene handgepflegte Viererliste zu führen — die war schon veraltet, sie
  kannte das Missions-Overlay nicht. **A/B belegt:** Vor-Fix-Welt wiederhergestellt → 9 von 44
  Prüfungen fallen.
- **`_announce()` PUFFERT**, wenn das Overlay noch nicht existiert. Kein hypothetischer Fall: auf dem
  Legacy-Instant-Pfad (`PREGAME_DEPLOYMENT` aus) startet `main()` die Schlacht — und zieht damit
  Runde 1 — hunderte Zeilen bevor die UI gebaut ist. `flush_announcements()` läuft direkt nach dem
  Anhängen.
- **Ziehen ist IDEMPOTENT pro Schlachtrunde** (`_drawn_round`), weil `draw_at_command_phase()` von
  DREI Stellen erreichbar ist: beide Schlachtstart-Pfade und der Command-Phasen-Haken — und die
  allererste Command-Phase ist von zweien davon abgedeckt.
- **Der Stapel teilt siebzehn Karten aus**: Centre Ground, Bring It Down, A Grievous Blow,
  Assassination, A Tempting Target, Beacon, Behind Enemy Lines, Cleanse, Defend Stronghold, Display
  of Might, Engage on All Fronts, Forward Position, No Prisoners, Outflank, Overwhelming Force,
  Plunder, Secure No Man's Land. Zwei je Runde, ohne Nachmischen — man sieht also höchstens zehn
  davon pro Schlacht.
  - **Burden of Trust ist GEBAUT, aber bewusst NICHT im Stapel** (User: "lass Burden of Trust
    erstmal weg"). Ihre Ökonomie ging nicht auf: man verpflichtet jede Runde neu Wächter, aber
    abgerechnet wird nur der Stand am Ende der Schlacht — vier der fünf Verpflichtungen sind also
    unsichtbar. Alles, was sie braucht, steht weiter da und wird weiter getestet (Karte,
    Zuweisungsfenster, und die Brett-Klick-Auswahl, die sie überhaupt erst eingeführt hat), also
    ist das Zurückholen EIN Name in `ALL_CARDS`. Im Test von beiden Seiten gepinnt. Eine neue
  Karte ist EIN Eintrag in `ALL_CARDS` plus ihr Prädikat; im Test sind die Schlüssel als Liste
  gepinnt, damit ein Zuwachs eine sichtbare Einzeiler-Änderung ist. **Die Decktests bauen sich
  eigene Karten**, statt gegen `ALL_CARDS` zu prüfen — die erste Fassung schrieb "der Zwei-Karten-
  Stapel ist jetzt leer" und wurde von der dritten Karte sofort ungültig (Fehlerklasse 17 im
  Kleinen).
- **A Grievous Blow zählt EINHEITEN, Bring It Down MODELLE** — die zwei Karten sehen fast gleich
  aus und hängen deshalb an ZWEI verschiedenen Haken desselben Todes-Sweeps:
  `record_destroyed_squad()` an `main.py`s eigenem `attached_units.unit_is_destroyed()`-Zweig,
  `record_destroyed_model()` pro entferntem Modell. "Unit destroyed" aus den Modellen neu
  abzuleiten wäre eine zweite Meinung zu einer Frage, die die Engine schon beantwortet (19.01
  merged den Leader ins Squad). Der Unit-Haken dedupliziert nach `id()`, weil der Sweep dasselbe
  geleerte Squad im selben Frame mehrfach erreicht.
  - **"Starting Strength" ist `starting_model_count`, NICHT die aktuelle Stärke**: ein auf zwei
    Modelle geschossener 21er-Blob ist beim Sterben immer noch eine 13+-Einheit. Bei einer Attached
    Unit wird der Wert aus den gemergten Komponenten neu abgeleitet — genau das lässt Guardian
    Defenders + Farseer + Warlock Conclave (14) überhaupt qualifizieren.
  - **Gemessen, welche Listen betroffen sind:** Aeldari 2 Einheiten, Orks 1, Necrons 1, **T'au
    KEINE**. Gegen T'au ist die Karte also ab dem Ziehen tot — und genau dafür hat sie ihre
    WHEN-DRAWN-Klausel. Als Testzeile an der echten Liste festgehalten, nicht als Literal.
- **Assassination hat ZWEI Zweige mit demselben Wert** (5 VP), also Alternativen statt Stufen: "ein
  oder mehr feindliche CHARACTER-Modelle diesen Zug zerstört" ODER "alle feindlichen
  CHARACTER-Modelle im Lauf der Schlacht zerstört". Der zweite ist die Nachzügler-Klausel für den
  Zug NACH dem letzten Kill.
  - **"Alle zerstört" ist NICHT "keiner auf dem Schlachtfeld".** Ein Charakter in Strategic Reserves
    ist vom Brett und quicklebendig. Deshalb bekommt der Controller eine ZWEITE Quelle,
    `set_squads_source(state.all_squads)` (Brett + Reserven + Transporte), getrennt von der
    Token-Quelle — die beiden beantworten verschiedene Fragen. **Gemessen:** mit dem letzten
    Charakter in Reserve zahlt die Karte 0; läse sie nur das Brett, zahlte sie fälschlich 5.
  - **Plus eine Nicht-Leerheits-Bedingung**: mindestens ein feindlicher Charakter muss wirklich
    gestorben sein, sonst erfüllt ein Gegner, der nie einen gefieldet hat, die Klausel jeden Zug
    vakuum-wahr.
  - **Die battle-lange Liste überlebt die Zuggrenze**, anders als alles andere in
    `_destroyed_*` — eigene Testzeile.
- **A Tempting Target ist die erste Karte mit GEDÄCHTNIS** — ihre WHEN-DRAWN-Klausel wählt ein
  Objective, und das bleibt für den Rest der Schlacht ihres. Zwei neue Bausteine dafür:
  - **Der Zustand liegt im CONTROLLER, nie auf der Karte** (`self.card_state`, nach Karten-Key,
    durchgereicht als `ctx.card_state`). Die `SecondaryMissionCard`-Objekte sind modulweite
    SINGLETONS, die jede Schlacht teilt — Zustand auf eine zu schreiben ist exakt die
    geteilte-Klassenattribut-Falle, die dieses Repo für `UnitProfile` schon dokumentiert.
    `achieved()` baut deshalb einen Kontext PRO KARTE statt einen für die ganze Hand.
  - **`on_draw` ist NICHT `when_drawn_may_redraw`**: das eine richtet die Karte ein, das andere ist
    die "abwerfen und neu ziehen"-Klausel. Zwei Haken, zwei Bedeutungen.
  - **`detail()` plus `detail_for()`**: die gedruckte Zeile sagt "your tempting target" und nie
    WELCHES — ohne die Detailzeile in Streifen und Zieh-Overlay ist die Karte unspielbar. Sie wird
    als eigener Block gerendert, nicht an den Text gehängt: `wrap_text()` trennt an LEERZEICHEN,
    ein eingebettetes `
` würde also gar keine neue Zeile beginnen.
  - **Die Wahl der KI ist deterministisch und vom User geliefert** ("eines der Objectives, die die
    KI kontrolliert. Wenn sie keins kontrolliert, dann das, was am weitesten weg von meiner
    Aufstellungszone ist") — also 0 API-Calls. Gleichstände brechen über den Namen, sonst flackerte
    das Ziel zwischen zwei gleich guten Objectives und die Karte wäre unspielbar.
  - **"No Man's Land" und "excl. home objectives" sind DIESELBE Menge**, geometrisch geprüft: ein
    Objective, dessen Mitte in KEINER Aufstellungszone liegt. Auf allen vier Karten fallen die
    beiden Formulierungen zusammen (Home-Objectives liegen immer in ihrer eigenen Zone), also wird
    nach Geometrie gefiltert und nicht nach dem String "Home" — im Test ist beides gegeneinander
    gepinnt, damit eine künftige Karte, die die Deckung bricht, hier auffällt.
  - Gemessen auf map2: drei No-Man's-Land-Objectives, Abstände zur P1-Zone 13.2" / 10.0" / 6.8" —
    ohne Kontrolle wird das ferne W gewählt, sobald die KI das nahe E hält, wird E gewählt.
- **Beacon ist die erste Karte mit EINEM EINZIGEN Zeitpunkt in der ganzen Schlacht.** Das gedruckte
  Badge `END OPP TURN · R5` hat der User ausgeschrieben als **"END OF OPPONENTS TURN - ROUND 5"**:
  also am Ende des GEGNERZUGES in der LETZTEN Schlachtrunde, einmal. Man pflanzt den Beacon früh und
  er muss am Schluss noch stehen. Dritter `TIMING_*`-Wert; `BATTLE_ROUNDS` wird aus
  `game/missions.py` gelesen statt die 5 erneut hinzuschreiben.
  - **Die Rundennummer MUSS von VOR `advance_phase()` kommen.** `begin_end_of_turn()` läuft danach,
    und wenn der ZWEITE Spieler einer Runde fertig ist, hat der Zähler schon hochgezählt — gemessen:
    Runde 5 endet, `turn_tracker.battle_round` steht auf **6**. Ein Kartentest "ist das Runde 5"
    sähe also nie seinen eigenen Moment. `main.py` reicht deshalb `battle_round_before` durch, und
    ein Quell-Wächter verlangt genau das.
  - **"Territory" ist die eigene Brett-HÄLFTE** (User: "Territory heißt einfach außerhalb meiner
    Spielfeldhälfte") — deutlich größer als die Aufstellungszone darin, was die 3-VP- von der
    5-VP-Stufe trennt. Welche Hälfte wem gehört, wird aus den Aufstellungszonen ABGELEITET, nicht
    angenommen — im Test für BEIDE Spieler gespiegelt geprüft, sonst wäre die Ableitung eine
    hartkodierte Seite. **Die ABLEITUNG selbst ist seither zweimal gewachsen** (siehe
    `### Territorien`): erst eine Achsen-Wahl (die drei damaligen Karten teilten alle auf y), dann
    die Mittelsenkrechte der Zonen-Zentren, und seit map4 der Abstand zur ZONE — womit die Grenze
    auf einer Diagonal-Karte wirklich diagonal läuft.
  - **"Outside" heißt: KEIN Modell der Einheit ist drin.** Gemessen mit einem einzelnen
    zurückgezogenen Modell: eins wieder in der Zone kostet die 3 VP, eins wieder in der eigenen
    Hälfte drückt 5 VP auf 3.
  - **"On the battlefield" trägt beide Stufen**: ein Beacon im Transporter oder zerstört zahlt 0.
    Geprüft wird das BRETT (`tokens`), nicht die All-Squads-Liste.
- **Die WHEN-DRAWN-Einrichtung gibt es in ZWEI Formen**, und der Unterschied ist, WER wählt:
  `on_draw` entscheidet selbst (A Tempting Target — der Gegner wählt, deterministisch nach
  User-Regel), `draw_choices` fragt den Menschen (Beacon — "Choose one friendly unit"). Beides ist
  von `when_drawn_may_redraw` getrennt, der "abwerfen und neu ziehen"-Klausel. Die interaktive Form
  läuft als ZWEITER Durchgang NACH den Redraw-Angeboten — sonst könnte eine Karte eingerichtet und
  danach weggetauscht werden, und die Wahl wäre verschenkt.
  - Beacons Kandidaten sind Brett-Einheiten PLUS eingestiegene (18.02), aber **nicht** die in
    Strategic Reserves — die nennt die Karte nicht. Dafür gibt es `set_embarked_source()`, weil
    weder die Token- noch die All-Squads-Quelle eingestiegen von reserviert unterscheiden kann.
- **Behind Enemy Lines misst "WHOLLY within"** mit 03.01s eigenem Test
  (`DeploymentZone.contains_circle`, die ganze BASE drin, nicht nur der Mittelpunkt) — nicht neu
  hergeleitet, die Aufstellung besitzt diese Definition schon. Gemessen: ein einziges
  zurückgelassenes Modell kostet die vollen 3 VP der Einheit, und ein Modell mit dem Mittelpunkt
  exakt auf der Zonenkante zählt ebenfalls nicht. 3 VP je Einheit mit Deckel 5 heißt: eine Einheit
  3, zwei oder mehr 5.
  - **Seine WHEN-DRAWN-Klausel ist die einzige, die nach der RUNDE fragt** statt nach der
    Feindarmee ("During the first battle round"), und die einzige, die die Karte **ZURÜCK IN DEN
    STAPEL MISCHT** statt sie abzuwerfen. Dafür gibt es `when_drawn_shuffles_back`.
  - **Die REIHENFOLGE im Redraw ist die Stolperstelle, und sie wurde gemessen:** wird die Karte
    erst zurückgemischt und dann gezogen, gibt ein kleiner Stapel sie sofort wieder aus — die
    Klausel wird zum No-op, der wie ein Fehler aussieht (im Selbsttest genau so passiert: Karte
    landete wieder auf der Hand). Jetzt wird ZUERST die Ersatzkarte gezogen, DANN die alte
    zurückgemischt; "draw a NEW Secondary Mission" ist genau das, was die andere Reihenfolge nicht
    garantiert.
- **Burden of Trust ist die erste Karte mit einem LAUFENDEN Zustand, der jede Runde neu gesetzt
  wird.** "WHEN DRAWN / START OF YOUR TURN" ist EIN Fenster mit zwei Auslösern, also teilen sie
  sich `_offer_guard_gate()`. Die Zuweisungen halten "until your next turn", das Fenster LÖSCHT
  also erst und bietet dann neu an.
  - **"Guarded" wird LIVE geprüft, es gibt keine zweite Buchführung**: die Einheit in Reichweite
    (`objectives.is_within_range_of_objective()`, dieselbe 3" wie 12.08) UND `controlled_by ==
    Spieler` (14.02). Ein Wächter, der wegläuft, stirbt oder dessen Objective gekippt wird, hört
    von selbst auf zu zählen. Alle drei Ausfälle einzeln gemessen.
  - **Ein Ja/Nein-Tor vor der Kette**, weil map2 fünf Objectives hat: fünf Fragen zu Beginn JEDES
    eigenen Zuges für eine "you may"-Klausel wären schlimmer als die Karte wert ist. Ablehnen ist
    eine legale Antwort und lässt alles unbewacht.
  - Die Kandidatenliste nennt zuerst die Einheiten **in Reichweite** (mit `(in range)`
    markiert) — eine Einheit, die nirgends in der Nähe steht, kann per Definition nicht bewachen.
  - **`start_of_turn()` läuft in `main.py` VOR `draw_at_command_phase()`**: in der Runde, in der
    die Karte gezogen wird, findet es sie noch nicht auf der Hand und tut nichts, sodass nur das
    Zieh-Fenster feuert. Sonst würde zweimal gefragt.
  - **Die Zuweisung läuft über einen BRETT-KLICK, nicht über eine Namensliste** (User: "Bei Burden
    of Trust muss immer links in der Spalte das Objective genannt werden, um das es gerade geht,
    und ich muss auf der Map mein Einheit anklicken"). **Seit dem 2026-09-04-Umbau ist das der
    GETEILTE Mechanismus** (`game/unit_pick.py`, siehe `## Einheiten auf dem Brett wählen`) und
    kein eigenes Pending-System mehr: `request_unit_pick()` legt eine gewöhnliche
    `DecisionManager`-Anfrage mit getaggten Optionen an und trägt ihr `subject` — das Objective —
    weil genau das die Frage ausmacht. Die Karte gewinnt dabei das BRETT-HIGHLIGHT, das ihr alter
    Screen im eigenen Docstring als fehlend vermerkt hatte.
    - **Der Klick MUSS vor dem generischen Board-Zweig gefangen werden**, sonst schluckt ihn die
      Kamera-Behandlung: Fehlerklasse 15, fünfmal im Repo verzeichnet. Er wird jetzt im
      `decision_manager.is_pending`-Zweig aufgelöst, der weit vor jedem Controller-State-Zweig
      steht; ein Quell-Wächter prüft beide Seiten dieser Klammer.
    - **Der Panel-Zweig steht als ERSTER im `_draw_dispatch`**, weil das Panel die einzige Stelle
      ist, die sagen kann, WELCHES Objective gerade dran ist — jeder Zweig davor könnte ihn
      verdecken, und dann wartet das Brett auf einen Klick, den niemand erklärt hat.
    - **Nur Einheiten IN REICHWEITE sind klickbar**, ein Klick auf etwas anderes wird ignoriert
      statt geraten. Und es werden nur noch Objectives gefragt, für die es überhaupt eine
      Einheit in Reichweite gibt — die Kette überspringt den Rest, statt fünfmal "kein Wächter"
      zu verlangen.
    - Die eligible Einheiten stehen zusätzlich als NAMEN im Panel: sonst sucht man sie auf dem
      Brett durch Ausprobieren.
- **Cleanse ist die erste Karte mit einer AKTION** (Regel 16.01, siehe den Abschnitt darüber). Ihre
  fünf Zeilen: STARTS in der eigenen Schussphase, UNITS eine Einheit in Reichweite eines Objectives
  **außer dem eigenen Home-Objective** — **und seit 2026-09-10 eines, das sie schon KONTROLLIERT**,
  weil COMPLETES „if that unit STILL controls" sagt und „still" Kontrolle beim Start voraussetzt
  (die 3" Reichweite bleiben; siehe `## Cleanse bot einen Knopf an, der nicht auszahlen konnte`) —,
  USE LIMIT unbegrenzt aber jede Einheit an einem ANDEREN
  Objective, COMPLETES am Zugende falls die Einheit das Objective kontrolliert, EFFECT das Objective
  ist gecleanst. 2 VP für eins, 5 VP für zwei oder mehr.
  - **"excl. your home objective" ist SINGULAR und POSSESSIV** — das Home-Objective des GEGNERS ist
    ein legales Ziel. Eigene Testzeile, weil "excl. home objectives" (A Tempting Target) daneben
    steht und das Gegenteil bedeutet.
  - **Das USE LIMIT ist eine Eindeutigkeitsregel am ZIEL, keine Obergrenze für die Anzahl.** Die
    Kandidatenkette wird deshalb bei JEDEM Schritt neu abgeleitet statt vorab eingesammelt: einer
    Einheit ein Objective anzubieten, das gerade vergeben wurde, wäre sonst der Normalfall.
  - **EFFECT hat bewusst KEINEN Callback.** Vollenden IST der Effekt: `resolve_end_of_turn()` gibt
    die vollendeten States zurück, und die darin genannten Objectives sind genau die gecleansten.
    Eine Liste, in die ein Effekt hineinschreibt, wäre eine zweite Aufzeichnung derselben Tatsache.
  - **Die WHEN-DRAWN-Klausel nennt "Plunder"** — eine Karte, die dieser Stapel nicht enthält, also
    ein belegter No-op. Ausgeschrieben statt weggelassen, damit Plunder später eine
    Einzeiler-Änderung ist; im Test ist gepinnt, dass keine Karte diesen Schlüssel trägt.
- **Defend Stronghold ist die erste Karte mit einer VERPFLICHTENDEN WHEN-DRAWN-Klausel.** Ihr Text
  lautet "During the first battle round, **shuffle** this card back" — **ohne "you may"**, das
  Behind Enemy Lines in genau demselben Satz hat. Die eine ist ein Angebot, die andere eine
  Anweisung: `when_drawn_is_mandatory` löst sie ohne Prompt auf. Der Unterschied steht als eigene
  Testzeile für BEIDE Karten da, weil ein flüchtiger Vergleich sie für identisch hält.
  - **"no enemy units are WITHIN your deployment zone"** — nicht "wholly within". Ein Feindmodell,
    das die Zone nur BERÜHRT, kostet schon die 5 VP und lässt 3 übrig. Das ist die umgekehrte
    Strenge zu Behind Enemy Lines' "wholly within", darum sind es zwei verschiedene Tests; im Test
    mit einer Base gemessen, die genau auf der Zonenkante steht.
  - **"2ND ROUND ONWARD"** ist als `min_battle_round` modelliert und in `scores_at()` geprüft.
    **Unter dem heutigen Zeitpunkt kann es nie greifen** (die Karte wertet ohnehin nur in Runde 5),
    und genau das ist inzwischen ein OFFENER PUNKT statt einer Kuriosität: eine gedruckte Karte
    trägt keine Bande, die nie gilt. Der Wortlaut ist beim User erfragt — siehe
    `## Zwei Meldungen aus einer Partie`.
  - Das eigene Home-Objective wird geometrisch gefunden (`own_home_objective()`), und der Test
    prüft die Gegenrichtung mit: für Player 2 ist es das ANDERE.
- **Display of Might ist die erste Karte, deren WERT vom ZEITPUNKT abhängt statt vom Erfüllungsgrad**
  — dieselbe Bedingung, 2 VP am Ende des eigenen Zuges, 5 VP am Ende des gegnerischen. Das Halten
  des Niemandslands durch den Feindzug ist die schwerere Hälfte, und genau das ist das Design der
  Karte. `score()` liest dafür `ctx.ending_player`; `scores_at()` bleibt "Ende EINES Zuges".
  - **"wholly within No Man's Land"** = jede Base ganz außerhalb BEIDER Aufstellungszonen
    (`zone_distance() > radius`). Beide Zonen einzeln getestet — ein Modell zurück in der EIGENEN
    Zone zählt genauso wenig wie eins in der gegnerischen.
  - **Die Klammer "(excl. AIRCRAFT & battle-shocked)" steht gedruckt hinter "enemy units", wird
    aber auf BEIDE Seiten angewandt** — sie liest sich als Qualifier darauf, was für diese Karte
    als Einheit zählt, und es ist die STRENGERE Lesart, kann also keine VP verschenken, die die
    Karte nicht meinte. Als Entscheidung im Modul ausgeschrieben.
  - **"MORE friendly than enemy" — gleich ist nicht mehr.** 1:1 zahlt nichts, 2:1 schon.
- **Engage on All Fronts bringt TISCHVIERTEL** (`table_quarters()`): das Brett an der Mitte auf
  BEIDEN Achsen geteilt — die schlichte Lesart von "table quarter" und die einzige, die auf allen
  drei Brettern (44×60, 60×44, 30×30) ohne Sonderfall funktioniert. Sie werden aus `config` zur
  LAUFZEIT gebildet, ein Hochformat-Brett bekommt also andere; als Testzeile festgehalten.
  - **Die 6"-Mittenklausel ist das, was die Karte schwer macht**: eine Einheit kann ganz in einem
    Viertel stehen und trotzdem keine Presence geben, wenn sie zu nah an der Brettmitte steht.
    Auf beiden Seiten der Linie im GLEICHEN Viertel gemessen, damit nur die Distanz den
    Unterschied macht.
  - "Wholly within it" wird per Base geprüft: eine Einheit auf einer Mittellinie zählt für KEIN
    Viertel, nicht für eines von beiden.
  - **Gegnerische Einheiten sind irrelevant** — die Karte fragt nur nach den eigenen. Eigene
    Testzeile, weil die Nachbarkarte (Display of Might) genau das Gegenteil tut.
  - **Die Karte druckt KEINEN Zeitpunkt** — in dem Feld, in dem jede andere Karte ihren Moment
    trägt, steht hier FIXED bzw. TACTICAL. Vom User bestätigt: "engage on all fronts triggered am
    Ende des Zuges", also derselbe Ende-des-eigenen-Zuges-Moment wie bei jeder anderen
    Brettzustands-Karte dieses Stapels.
- **Forward Position** zahlt 5 VP für das Home-Objective des GEGNERS **und/oder** jedes
  Expansion-Objective. "and/or" macht die beiden zu Alternativen, nicht zu einer Summe: eines
  allein zahlt die eine 5-VP-Box. "EACH expansion objective" ist ALLE — genau das verhindert, dass
  die Karte auf einem Brett mit zweien trivial wird.
  - **"Expansion objective" ist eine User-Definition** ("das Objektiv, was an meiner
    Aufstellungszone am nächsten ist, außer natürlich das Home-Objektiv"): das der eigenen Zone
    NÄCHSTE Objective, Home ausgenommen — also EINES pro Spieler, und "each expansion objective"
    meint das Paar. Home wird geometrisch ausgeschlossen (es läge in der eigenen Zone, Abstand 0,
    und gewänne immer), deshalb liefert `no_mans_land_objectives()` die Kandidaten.
  - **Gemessen, und auf beiden großen Karten symmetrisch:** map1 P1→Southwest / P2→Northeast (je
    4.2"), map2 P1→East / P2→West (je 6.8") — das Central liegt auf beiden Brettern weiter weg
    (12.0" bzw. 10.0") und ist deshalb nie Expansion. Der Test prüft nicht nur WELCHES, sondern
    dass jedes andere Objective wirklich weiter weg ist.
  - **map3 hat nur EIN Nicht-Home-Objective**, also ist für beide Spieler dasselbe das nächste und
    die Menge fällt auf einen Eintrag zusammen — `expansion_objectives()` dedupliziert deshalb,
    sonst verlangte "each expansion objective" dasselbe Objective zweimal.
- **WITHIN gegen WHOLLY WITHIN ist die Falle dieses Kartensatzes** (User-Warnung: "Within: da
  reicht, wenn ich nur den kleinen Zeh mit einem Modell reinhalte. Wholly within dagegen muss die
  Einheit wirklich vollständig drin sein"). Beide Formen kommen vor, oft auf benachbarten Karten,
  und eine verwechselte Lesart besteht JEDEN Test, der eine Einheit klar drinnen oder klar draußen
  stellt. Deshalb prüft `test_secondary_missions.py`s Abschnitt 3m jede räumliche Klausel am
  GRENZFALL — eine Einheit mit einem Modell auf der einen und dem Rest auf der anderen Seite:
  - **WITHIN (ein Modell reicht):** Centre Ground (3"/6" zur Mitte), Defend Stronghold (Feind in
    meiner Zone), Outflank (6" zur Brettkante), Burden of Trust und Cleanse (Objective-Reichweite).
  - **WHOLLY WITHIN (ein Modell draußen kippt alles):** Behind Enemy Lines (Feindzone), Display of
    Might (Niemandsland), Engage on All Fronts (Tischviertel).
  - **NOT WITHIN / OUTSIDE ist der Spiegel von WITHIN**, nicht von WHOLLY WITHIN: ein Modell drin
    kippt es. Betrifft Beacon (eigene Hälfte/Zone), Engage (6" zur Mitte) und Outflanks
    "not within your territory".
- **Outflank ist die erste Karte, deren höhere Stufe eine SCHWÄCHERE Bedingung an die einzelne
  Einheit stellt.** 3 VP verlangen, dass DIE Einheit außerhalb der eigenen Hälfte steht; 5 VP
  verlangen zwei Einheiten an gegenüberliegenden Kanten, aber nur EINE davon muss draußen sein. Die
  reichere Stufe ist also nicht die ärmere zweimal — eine in der eigenen Hälfte festhängende
  Einheit kann Hälfte der 5-VP-Stufe sein, obwohl sie allein nichts zahlt. Eigene Testzeile, weil
  ein "beide müssen raus" hier naheliegt und falsch wäre.
  - "Opposite edges are the ones that run parallel to each other" steht auf der Karte, also sind
    die Paare (Nord, Süd) und (West, Ost); benachbarte Kanten und zwei Einheiten an DERSELBEN Kante
    zahlen nur die 3 VP.
- **No Prisoners ist A Grievous Blow ohne den Starting-Strength-Filter** — 2 VP je zerstörter
  Feindeinheit, Deckel 5 (drei Einheiten zahlen 5, nicht 6). Wird aus demselben Pro-EINHEIT-Haken
  gefüttert.
- **Overwhelming Force braucht einen SNAPSHOT ZUM ZUGBEGINN.** "each enemy unit that STARTED THE
  TURN within range of one or more objectives and is destroyed" — das ist eine Tatsache über einen
  Moment, der beim Punkten vorbei ist, und über Einheiten, die es dann nicht mehr gibt. Weder vom
  Brett ablesbar noch nachträglich rekonstruierbar. `snapshot_turn_start()` läuft deshalb zu
  Beginn JEDES Zuges (auch des gegnerischen — die Karte punktet am Ende EINES Zuges) und merkt
  sich `id(squad)` jeder Feindeinheit in Objective-Reichweite. Billig und bedingungslos: ob die
  Karte nächste Runde gezogen wird, ist jetzt nicht bekannt.
- **Plunder ist die erste Aktion mit "COMPLETES: Immediately"** — sie ist in dem Moment fertig, in
  dem sie beginnt. Dafür bekam `ActionDefinition` ein `completes_immediately` und `ActionState` ein
  `completed`; `resolve_end_of_turn()` meldet sofort abgeschlossene Aktionen mit, damit jeder
  Konsument EINE Liste liest.
  - **16.01s Bewegungs-Abbruch erreicht sie nicht mehr** (sie ist ja fertig), **die zwei Sperren
    aber schon** — die hängen am STARTEN, nicht am Vollenden. Beides einzeln gemessen: nach einer
    Bewegung ist `broken=True` UND `completed=True`, und sie zählt am Zugende trotzdem.
  - **"One unit within a terrain area not within your territory"** — der Zusatz hängt an der
    TERRAIN AREA, nicht an der Einheit: man plündert fremden Boden. Gemessen an der Mitte der Area,
    wie ein Objective als Home klassifiziert wird. Auf map2 sind 7 der 15 Areas plünderbar.
  - **USE LIMIT "once per turn"** — EINE Plunder-Aktion pro Zug, nicht eine je Einheit. Gegensatz
    zu Cleanse, dessen Limit "unbegrenzt, aber je Einheit ein ANDERES Objective" ist; beide
    Lesarten stehen im Test nebeneinander.
  - **Cleanses "If you have Plunder active"-Klausel ist damit scharf** — sie war ein belegter
    No-op, und der Pin in `test_actions.py` war ausdrücklich dafür gesetzt, dass das Hinzufügen von
    Plunder eine SICHTBARE Änderung wird. Genau das ist passiert: die Zeile wurde rot und ist jetzt
    umgedreht. Beide Karten drucken die Klausel spiegelbildlich, eine Hand muss also nie beide
    Objective-Action-Karten tragen.
- **Secure No Man's Land** ist die einfachste Karte des Satzes: zwei oder mehr
  No-Man's-Land-Objectives kontrolliert → 5 VP. Das gedruckte "(excl. your home objective)" ist
  doppelt gemoppelt — ein Home-Objective liegt in einer Aufstellungszone und ist damit nie in No
  Man's Land; `no_mans_land_objectives()` schließt es ohnehin geometrisch aus.
- **Bring It Down zählt MODELLE, nicht Einheiten**, und wird deshalb aus dem Pro-Modell-Todes-Sweep
  gefüttert (`record_destroyed_model()`), nicht aus `record_destroyed_squad()`: ein Squadron, das zwei
  von drei Rümpfen verliert, punktet zweimal, während seine EINHEIT weiterlebt und der
  Squad-Haken nie feuert. Und es punktet am Ende **EINES** Zuges (auch dem der KI) — Centre Ground
  dagegen nur am Ende des EIGENEN. Der gedruckte Unterschied ("end of a turn" gegen "end of your
  turn") ist als `TIMING_*` modelliert und einzeln getestet.
- **Centre Ground hat DREI Ausgänge, nicht zwei.** 5 VP braucht die Mitte bis 6" frei, 3 VP nur bis
  3". Die mittlere Bande ist die, die man beim Testen verliert; gemessen mit einem Feind 4.44" von der
  Mitte (innerhalb 6", außerhalb 3"). "excl. AIRCRAFT" ist ein belegter **No-op** — dieses Keyword
  gibt es hier nicht, dieselbe Ausnahme, die `rapid_ingress.py` schon dokumentiert.
- **Die VP-Beträge werden EAGER berechnet**, bevor irgendetwas gefragt wird: die Prompts lösen sich
  asynchron auf (der Zug ist zu dem Zeitpunkt längst umgeschlagen, genau wie bei
  `starflare_controller.offer()` an derselben Stelle), das Brett, gegen das gemessen wurde, darf also
  nicht später neu gelesen werden. Deshalb kann `_destroyed_this_turn` sofort geleert werden.
- **Die fünf Headless-Harnesses setzen den Flag auf `()`** — der Stapel fragt den Menschen am Ende
  JEDES seiner Züge etwas, und keiner von ihnen beantwortet außerhalb des Vorspiels einen
  Mensch-Prompt (dokumentierte Grenze). **Belegt statt vermutet:** mit eingeschaltetem Flag zieht
  `selfplay.py map2` die zwei Karten korrekt und bleibt danach in Player 2s Zug stehen, weil
  `_is_blocked()` auf dem offenen Prompt hält. Quell-Wächter verlangt es von allen fünf.
- **`ai/planner_prompt.py` sagt der KI jetzt, dass die Secondary des GEGNERS eine andere ist** und
  nicht vom Brett ablesbar. Ihre eigene Beschreibung stimmt unverändert.
- **Bewusst offen:** ACTIONS gibt es in dieser Engine überhaupt nicht (siehe `fall_back.py`), und
  keine der zwei Karten braucht eine — `SecondaryMissionCard.requires_action` ist der benannte Haken,
  mehr nicht (kein spekulatives System). Kein KI-Pfad: die KI behält ihre Standard-Missionen.
  (`scene_io` sicherte lange weder VP noch Hand noch Stapel — das ist seit dem Game Menu erledigt,
  siehe dort; die Grenze ist jetzt nur noch der Zeitpunkt: ein Snapshot MITTEN im Zug — F9, Save
  Game oder ein Phasen-Autosave — verliert eine angefangene Action, einer an der Rundengrenze nichts.)
- **Getestet:** neu `test_secondary_missions.py` (**543/543**), `test_mission_cards_ui.py`
  (**54/54**, gegen eine echte Surface gemessen statt gegen Konstanten) und
  `test_one_modal_at_a_time.py` (**44/44**, Quell-Wächter). Neu `test_actions.py` (**79/79**) und `test_mission_unit_pick.py` (**60/60**). Volle
  Regression **112 Suiten, ~7432 Prüfungen, 111 grün / 0 rot / 1 bekannt**, dazu alle vier Smokes und `selfplay.py map2` 2000
  Frames (0 API-Calls). Vorher gab es zu Missionen **gar keinen Test**.
