# Regelengine: Bewegung

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Regelengine — Bewegung

Move-Typen (09.02): Remain Stationary, Normal, Advance (09.06), Fall Back (09.07), Charge (11.04),
Pile-In (12.03), Consolidate (12.07/12.08), Surge (21.02), Ingress (20.04)/Strategic Reserves,
Transport Embark/Disembark (18.x inkl. Rapid/Tactical/Combat/Emergency + Hazard-Rolls), Take to the
Skies (21.03). Dazu Sonderzüge außerhalb der Bewegungsphase: Scout Move, Retro-thrusters, Torchstar
Gambit, Tactical Acumen, Battle Focus' reaktive Züge, Path of the Outcast — alle über
`start_post_shooting_move()`/eigene Starter, bewusst NICHT über `can_move()` gegated (das fragt "ist
das der Bewegungsphasen-Zug dieser Einheit", die falsche Frage) und mit eigenem `move_mode`, der den
Confirm-Button an den zuständigen Controller routet.

- **Sofort-Prüfung pro Segment**: Terrain/Überlappung/Engagement werden beim Committen jedes
  Modell-Segments geprüft (`try_commit_segment()`), nicht erst bei `confirm_move()`. Ein abgelehntes
  Modell springt nur selbst zurück. Coherency und "muss das Ziel erreichen" bleiben squad-weite
  Confirm-Prüfungen (nicht einem Modell zuordenbar).
- **Ein abgelehnter Versuch kostet nichts** — `try_commit_segment()` zieht nur bei Erfolg ab. Deshalb
  ist Hartnäckigkeit billig: `_advance_model_toward()` weicht bei Ablehnung erst SEITLICH aus (±45°,
  kleinste Winkel zuerst — cos(45°) behält 71% Vorwärtsanteil) und kürzt erst danach.
- **Hausregel: die KI bewegt ALLE ihre Einheiten GRATIS durch Wände** (`config.VEHICLES_CROSS_WALLS`
  / `WALL_CROSSING_PLAYERS` / `WALL_CROSSING_COST_IN`). Zwei Hälften, die man getrennt lesen muss —
  ERLAUBNIS und PREIS —, und nur die zweite hat sich 2026-09-09 bewegt (User: "um der ai das
  movement noch weiter zu erleichtern, darf sie ALLE einheiten durch wände bewegen").
  - **Die ERLAUBNIS war immer schon keyword-blind.** `Obstacle.blocks_movement_for()` endet mit
    `return not terrain.may_cross_walls(model)`, und das fragt NUR den OWNER — jede
    Keyword-Prüfung fällt für ein Modell der KI vorher weg. Gemessen über **alle zehn Listen ×
    drei Karten × beide Seiten**: Player 2 **0 von 701** Modellen geblockt (MOUNTED **0 von 7**),
    Player 1 **116 von 701** (MOUNTED **7 von 7**). Auf die Nachfrage "gilt das zb auch für
    Mounted?" ist das die Antwort — und MOUNTED ist im Repo ohnehin rein beschreibend, es tragen
    es nur Krootox Rampager und Lokhust Lord (Windriders lesen als FLY).
  - **Der PREIS war es nicht, und das war die Ungleichheit.** Die 3"-Maut traf per Konstruktion
    genau die Modelle, die 13.06 nicht ohnehin durchlässt: von den 701 querten **584 gratis**
    (INFANTRY/BEASTS) und **117 zahlten** (Windrider, War Walker, Lokhust Destroyer, Deffkopta,
    Crisis-Suits, Coldstar, Krootox Rampager, Avatar). Ein Windrider durfte durch dieselbe Wand
    wie der Guardian daneben — für die halbe Bewegung. **`WALL_CROSSING_COST_IN = 0.0`** hebt das
    auf.
  - **Die Affordability-Sperre fällt als FOLGE mit weg**, nicht als eigene Änderung: unterhalb der
    Maut blockierte eine Wand die Querung doch (`remaining <= cost` bzw. "die bezahlbare Strecke
    erreicht gar keine Wand"), und beides liegt hinter `_wall_toll()`s erster Zeile. Gemessen über
    `measure_crowded_movement.py map2`: **1386 Segmente pro Lauf**, in denen eine Wand ein
    KI-Modell doch stoppte → **0**.
  - **Und die KI rechnet jetzt richtig.** Nichts in `ai/` hat die Maut je gelesen (gemessen: null
    Vorkommen außerhalb `config.py`/`movement.py`), `reachable_this_turn` und `turns_to_reach`
    waren für diese 117 Modelle also um bis zu 3" zu optimistisch. Bei 0 stimmen sie exakt.
  - **Gemessen, was es bringt** (derselbe Lauf, Spion auf `_wall_toll`): Gesamtboden
    **209.1" → 217.7"**, Züge unter 35% des Erreichbaren **14.3% → 11.9%**, Seitwärtszüge
    **11.9% → 9.5%**, und die schlechteste Einheit der Baseline — der Battlewagon — **30% → 54%**.
    ISOLIERT (eine Einheit allein) **77% → 92%**. **Der CROWDED-Median bleibt bei 65%**, und das
    ist keine Enttäuschung, sondern die dokumentierte Aussage dieser Baseline: der Verlust im
    Gedränge kommt daher, dass die KI sich selbst im Weg steht, nicht von den Wänden.
  - **ZWEI Dinge bleiben ausdrücklich stehen**, beide mit eigener A/B-Sonde: die Erlaubnis bleibt
    OWNER-gekeyt (der Mensch spielt die gedruckten Regeln — "für mich als menschlicher spieler
    soll alles so bleiben"), und **13.05 gilt weiter für alle** — durch eine Wand ja, AUF einer
    Wand enden nein. Letzteres ist mit Abstand die häufigste Wand-Ablehnung (**5133 gegen 0**
    Maut-Fälle) und war schon einmal gemessen und bewusst nicht ausgeliefert.
  - **Der MECHANISMUS bleibt, 3.0 ist eine Zeile entfernt.** `WALL_CROSSING_COST_IN` ist ein
    Regler, den der User jetzt zweimal gesetzt hat; ihn auf 0 auszuliefern darf `_wall_toll()`
    nicht still zu totem Code machen. `test_wall_crossing.py` Abschnitt **2b** fährt ihn deshalb
    an einem selbst gesetzten Wert ungleich 0, Abschnitt **2a** pinnt, was AUSGELIEFERT ist —
    und 2a muss die A/B im Test selbst haben, weil `Kosten == WALL_CROSSING_COST_IN` bei 0 die
    Tautologie `0 == 0` ist und auch mit gelöschtem Mechanismus bestünde.
- **Kohärenz-Buchführung**: die 9"-Spannweitengrenze gilt nur noch für `config.SPREAD_LIMIT_PLAYERS`
  (= Player 1) — für die KI aufgehoben (User: sie würde Screens nicht über die Karte ziehen). Die
  2"-Zusammenhangs-Hälfte gilt für alle; sie ist die eigentliche Anti-Missbrauchs-Regel.
- **Eine gebrochene Einheit kann sich reparieren**: `_regroup_move()` packt sie mit
  `formation_layout.pack_positions()` neu (Zusammenhang per KONSTRUKTION), bevor der gewöhnliche
  Sweep läuft. Ohne das war sie dauerhaft eingefroren, weil `confirm_move()` 09.02 absolut erzwingt,
  während die KI-Seite gegen eine Baseline misst. Gemessen 20/90 → 2/90 eingefrorene Szenarien.
- **Regaining Coherency (09.02) entscheidet die KI selbst** (`_coherency_removal_pick()`): Charaktere
  zuletzt, dann Sergeant, dann wenigste Wunden. Vorher konnte nur ein Mensch die Wahl beantworten —
  auch für Einheiten der KI.
- **`_place_packed()` ist ein KANDIDAT, kein Ersatz**: eine Einheit scheitert oft an ihrer eigenen
  FORM, nicht am Boden (starr blockiert / gepackt passt). Packen läuft deshalb durch dieselbe
  `consider()`-Bewertung wie jeder andere Kandidat. Gemessen +2 Punkte Median, +5.5" Gesamtboden,
  Stillstände 2 → 0.
- **Der innerste Packungs-Ring wird ZUSÄTZLICH angeboten, nicht verschoben** (`ring_candidates`s
  `inner_radius`, gesetzt von `pack_positions()`). `step` kommt aus der KLEINSTEN Basis, auf dem
  Abwurfpunkt steht aber per Widest-First die GRÖSSTE — der erste Ring fällt dann an
  `_first_legal_slot()`s Überlappungsschranke KOMPLETT aus, nicht nur um einen Slot. Gemeldet an den
  Necron Warriors ("so viel Abstand zu ihrem Character ... Footprint unnötig groß"): Ring 1 mit NULL
  Modellen, Technomancer allein in einem 1.39"-Graben, während seine Krieger 0.29" auseinander
  standen. Mit dem Extra-Ring: Graben 0.05", Ring 1 trägt 6, Spread 7.20" → 6.24", bbox 8.33×7.50 →
  6.00×7.50. **Addieren statt Ersetzen ist der Kern:** innerhalb EINER Einheit ist der nötige Abstand
  paarweise verschieden, ein einzelner Radius kann nicht allen dienen — ein zusätzlicher Ring nimmt
  keinem Modell einen Platz weg, ein verschobener schon. Nur wenn er WEITER AUSSEN liegt als der
  erste reguläre; sonst bekäme jede homogene Einheit einen zweiten, engeren Ring, den sie nie
  brauchte (2r+0.05 gegen einen 2r+0.1-Pitch). **Nicht gratis, und das ist gemessen:** ein dichterer
  Block ist ein anderer Block, `measure_crowded_movement.py` bewegt sich pro Einheit in beide
  Richtungen (Boyz+Warboss+Painboy +6 auf map1, Gretchin 2 −10 auf map2), Mediane 64→65 / 62→59 /
  29→28. Betroffen sind ausschließlich Einheiten mit gemischten Basen; die großen Einzelausschläge
  bei homogenen Einheiten (Tankbustas −20) sind belegte KOPPLUNG, sie bekommen nie einen Ring.
- **Landeplatz-Suche statt Abschneiden an der Linie (2026-09-09).** Regel 03.01 lässt eine Base
  DURCH befreundete Modelle ziehen und verbietet nur das ENDEN darauf; `_clamp_target_against_
  friendly_models()` schnitt einen Zug trotzdem an der ERSTEN befreundeten Base auf der Linie ab.
  Gemessen am gemeldeten 21-Modell-Blob (`measure_reported_moves.py` C, Brett aus dem Log MIT
  Terrain): **535 von 821** Zielpunkten in EINEM Zug abgeschnitten, 810" Zielstrecke verworfen, und
  in **445 der 535** Fälle lag ein freier Landeplatz in 2" um den Punkt. Die Abgeschnittenen standen,
  die Läufer liefen, die Einheit riss, `confirm_move()` verwarf alles — das ist der Mechanismus
  hinter "die Modelle stehen sich gegenseitig im Weg". `_free_landing_near()` sucht jetzt den
  nächsten LEGALEN Endpunkt (Ringe alle 0.25" bis 2" bzw. eine Basisbreite; on board, 13.05,
  Tokens, `disallowed_enemy_squads_for_move`, Budget, `clamp_move`-Transit), bevorzugt einen Platz
  in Kohärenz (1.9") mit schon platzierten Squadmates und bestraft seitliches Rutschen
  (`_LANDING_LATERAL_WEIGHT`), damit ein Modell eher kurz stehen bleibt als an der Blockade entlang
  zu gleiten. **Zwei Caller sind GEMESSEN ausgeschlossen** (`_LANDING_SEARCH_EXCLUDED`): der
  Route-Walker (der Blob fiel im dritten Zug von 52 % auf 14 %, 18 Modelle neben einer Wand neu
  gelandet für 0.89") und der Engagement-Schritt (die Suche kennt keine Engagement Range und landete
  ein Pile-In-Modell NEBEN seinem Slot, außer Reichweite — die gemeldete Warbikers-Pile-In fiel
  unter ihr gemessenes Optimum 2/3). Der Squadmate-Radius-Regler `_LANDING_SQUADMATE_RADIUS_IN`
  trägt seine Messtabelle im Kommentar. **Ergebnis:** Fall C 2.71" → 3.72" (54 → 74 %), Fall B
  (C'tan-Charge) vollendet, Orks crowded 217.7" → 232.9" (Median 65 → 74 %), Necrons crowded
  117.9" → 119.9"; Preis: Necrons ISOLIERT 74 → 68 % Median (eine Zeile: der Blob allein im
  zweiten Zug, 92 → 43 %, weil das Re-Landing die Form weitet und der Packed-Kandidat seine Slots
  nicht mehr erreicht). `[move sweep]` im Log zählt clear/relanded/truncated je Zug.
- **Zwei Bewegungs-"Verbesserungen" derselben Sitzung sind GEMESSEN und wieder AUSGEBAUT**, damit
  sie nicht erneut gebaut werden: das Budget des LANGSAMSTEN Modells statt des schnellsten in den
  drei Pässen (Fall C 54 → 37 %; der Zielpunkt eines gemischten Trupps darf dem langsamen Modell
  vorauslaufen, der Pass kürzt es ohnehin), und die **"Leine"** (`_repair_split_by_leash`: Streuer
  eines gesplitteten Passes aus dem Pre-Pass-Snapshot mit vollem Budget zur Hauptkomponente
  zurückführen, vor der Schrumpf-Leiter). Die Leine änderte auf zwölf gemischten Welten je Armee im
  Mittel NICHTS (Orks −1.7", Necrons ±0.0"), bewegte keine Fixture, und im ECHTEN Pfad
  (Regroup an) blieb das Stress-Set von `test_coherency_recovery.py` bei 1/90 eingefroren mit UND
  ohne — sie rettete nur mit ABGESCHALTETEM Regroup (22 → 6), war also ein zweiter Mechanismus für
  einen Fall, den `_regroup_move()` trägt. Der eine übrige Fall ist ein 8"-Split mit einer
  Dense-Wand dazwischen, physisch. Beide Messungen stehen mit Zahlen in `CLAUDE.history.md`.
- **`_creep_toward()`** als letztes Netz: größte noch legale starre Translation per Bisektion. Sie
  bewertet die GEMESSENE Strecke, nicht die angefragte, und verwirft einen Versuch, der nicht wirklich
  starr blieb (Step-over und Friendly-Clamp können einzelne Modelle abweichend weit bewegen).
- **Take to the Skies (21.03): NUR FLY-Modelle zahlen, und eine reine INFANTERIE-Einheit
  deklariert es NIEMALS.** Beide Hälften sind User-Entscheidungen, erfragt nachdem die Messung
  ergab, dass die zwei Hälften der Regel VERSCHIEDENE Modellmengen trafen.
  - **Wer zahlt** (User: "es fliegen nur fly modelle"): `clamp_move()`s Bypass war immer schon
    pro Modell an `token.profile.fly` gegated — richtig; falsch war `take_to_the_skies()`s
    Preisschleife über das GANZE Squad. Gemeldet als "die necron krieger sind hinten nicht
    rausgekommen. sie hatten enorme schwierigkeiten nach vorne zu laufen": ein Technomancer (FLY)
    in 20 Necron Warriors (kein FLY), 19.01 merged beide, **21 von 21 zahlten, 1 von 21 flog** —
    5" auf 3", also 40%, jede Bewegungsphase des ganzen Spiels (im Log 1.63"/1.23"/1.19"
    Fortschritt). Jetzt zahlt nur der Technomancer; der Krieger behält seine 5", durch
    `clamp_move()` gemessen und nicht nur am Budget. **HOVER (24.17) bleibt bewusst eine
    squad-weite Ausnahme** — das ist die bestehende Lesart, kein Datenblatt der vier Roster
    druckt HOVER, und das Verengen war nicht Teil der Entscheidung.
  - **Wer deklariert** (User: "einheiten, die ausschließlich aus infanterie modellen bestehen
    sollten niemals take to the skies benutzen, weil sie ja eh durch wände laufen können"):
    13.06 lässt INFANTERIE Dense-Gelände ohnehin queren, die WERTVOLLE Hälfte von 21.03 kauft
    ihnen also nichts. Übrig bliebe das Durchqueren von MODELLEN, und das ist 2" je Modell nicht
    wert. `game/movement.py`s `take_to_the_skies_pays(squad)` ist die eine Definition, gelesen
    von `ai/agent_driver.py` UND `measure_crowded_movement.py` (der trug eine eigene Kopie —
    sein Header zählt auf, dass genau solche Kopien ihn dreimal von seinem Messgegenstand haben
    abdriften lassen). Vorher stand an beiden Stellen `any(m.profile.fly ...)`, begründet damit,
    die Deklaration "can only ever help this squad's own mobility" — wahr für die Crisis
    Battlesuits, für die sie geschrieben wurde, falsch für einen Leader-Flieger.
    **"Niemals" ist wörtlich genommen: die INFANTERIE-Prüfung steht VOR dem HOVER-Zweig**, als
    Testzeile gepinnt, weil sich die zwei Reihenfolgen nur in diesem einen Fall unterscheiden.
    Bewusst das INFANTRY-Keyword und nicht `can_move_through_dense_terrain()` (das deckt vier
    Keywords ab): die Entscheidung nennt Infanterie, und BEASTS sind ein anderer Fall — die
    Canoptek Wraiths queren Wände per 13.06 UND fliegen, und niemand hat verlangt, sie zu erden.
  - **Betroffen sind VIER Einheiten über alle vier Roster** (alle rein INFANTERIE): Necron
    Warriors + Technomancer, Stormboyz, Warp Spiders + Lhykhis, Stealth Battlesuits. **Sechzehn
    behalten es**, und keine davon ist reine Infanterie — Fahrzeuge, Walker, Beasts, Monster.
  - **Gemessen, nicht behauptet.** Der Fortschritt der gemeldeten Einheit
    (`measure_fly_penalty.py`, Brett aus den Log-Koordinaten rekonstruiert): **+0.93"/Zug** im
    Gedränge. Und die dokumentierte Bewegungs-Baseline wird durch die INFANTERIE-Regel BESSER,
    nicht schlechter — A/B in `measure_crowded_movement.py`: erreichter Fortschritt
    **60% → 65%**, Gesamtboden **202.1" → 209.1"**, Einheiten unter 60% **50.0% → 42.9%**. Die
    Stormboyz, die der Harness-Header als einen seiner zwei schlimmsten Fälle führt, stehen
    danach nicht mehr unter den fünf schlechtesten; der Header ist entsprechend nachgezogen.
  - **Getestet:** `test_take_to_the_skies_policy.py` (**33/33**), mit den zwei Hälften EINZELN
    neutralisiert (Engine-Hälfte → 27/33, INFANTERIE-Regel → 28/33), sodass keine die andere
    deckt.
- **Raumbedürftige Einheiten**: `_needs_open_ground()` fragt "kann diese Einheit Dense-Gelände
  durchqueren" (13.06) statt nach dem VEHICLE-Keyword — Warbikers haben alle Probleme eines Fahrzeugs
  und keines seiner Keywords. Bewegungsreihenfolge in Stufen: (0) räumt einem Fahrzeug den Korridor
  ODER steht in einer Ausladezone, (1) raumbedürftig, (2) Rest. Stufe 0 verdient sich ein Trupp nur,
  wenn er den Korridor durch seinen eigenen Zug SEITLICH verlässt; ein Fahrzeug, das auf dem
  ausdrücklichen Plan-Platz eines anderen parken würde, fällt auf Stufe 2.
- **`find_route()`** weicht bei blockierter START-Zelle auf die nächste brauchbare aus (der
  Zellmittelpunkt kann in einer Wand liegen, während die Einheit legal davor steht) — vorher gab es
  für eine wandnah geparkte Einheit dauerhaft `None`. Der geroutete Kandidat wird an der ROUTENLÄNGE
  gemessen, nicht am Luftlinien-Fortschritt (der erste Schenkel eines Umwegs steht fast senkrecht zum
  Ziel), plus `_place_rigid_route()` als starre Variante.
- **Charge**: `_CHARGE_STEP_OVER_IN`-Leiter (Modell auf einer dünnen Wand rückt entlang derselben
  Linie weiter, statt zurückzuspringen), `_engagement_slots()` verteilt Standplätze RINGS UM das Ziel
  (Charge 5 → 9 Modelle im Nahkampf), 11.04s 1"-Pflicht wird über die Ringtiefe erzwungen (Pile-In
  bekommt sie per 12.03 ausdrücklich NICHT), Baseline-Fehler werden vor Phase 1 gemessen (eine schon
  gebrochene Einheit muss den geerbten Zustand nicht reparieren).
- **Charge seit dem Bewegungs-Review 2026-09-09** (User: "Charges klappen oft nicht, weil die AI
  schlecht Lücken findet"), alles gemessen mit `measure_charge_scenes.py` (100 harte / 100 leichte
  Szenen, jede per Brute-Force möglich) und den zwei Log-Fällen aus `measure_reported_moves.py`:
  - **Der Engagement-Ring ist DICHT und LEGAL.** `_engagement_slots()` sampelte den Ring alle
    `2r+0.1"` in Bogen UND Tiefe — ein 1.57"-C'tan bekam SECHS Slots auf einem 19"-Ring und einen
    Ring —, und kein Slot wusste, ob er auf einer Wand, auf einer fremden Base oder in der
    Engagement Range einer DRITTEN Einheit lag; jeder solche kostete einen der sechs
    `_ENGAGEMENT_SLOT_TRIES` für nichts. Jetzt Bogenabstand 0.45" und Ringtiefe 0.5"
    (`_ENGAGEMENT_ARC_STEP_IN`/`_ENGAGEMENT_RING_STEP_IN`), `legal(x, y)` aus
    `_engagement_slot_filter()` (on board, 13.05, fremde Tokens, Keep-out-Engagement:
    `_charge_keep_out()` = alle Feinde außer dem Ziel; Pile-In/Consolidate leer per
    `disallowed_enemy_squads_for_move`), EINMAL je Ziel in `_run_charge_attempts()` gebaut und per
    `slots=` durchgereicht, Winkel-Dedupe in `_ranked_free_slots()` (kein Slot innerhalb 2r eines
    schon gereihten). **Der Charge-Ring beginnt bei BASISKONTAKT** (`_CHARGE_RING_INNER_EDGE_IN =
    PILE_IN_CLEARANCE_IN`), nicht bei `CHARGE_TARGET_CLEARANCE_IN` (das bleibt Phase 1s Stopp):
    gemessen 273 → 325 engagierte Modelle über die harten Szenen bei gleicher Vollendung.
  - **Slot-zuerst-Anlauf (`_charge_slot_first`) als ERSTE Sprosse, nicht auf Wände gegated.** Alle
    dreizehn Sweep-Anläufe beginnen mit dem starren Schub des ganzen Blocks zum nächsten Paar; endet
    die Linie auf einer Wand oder in der Engagement Range eines Dritten, ist der Wurf verbraucht,
    bevor Phase 2 beginnt. Der neue Anlauf ist die Charge, wie ein Spieler sie macht: Leitmodell
    (Nahkampf-Charakter, sonst das nächste) per DIREKTER Linie oder `find_route()` zum besten
    legalen Slot — mit Feind-BASEN als Transit-Blocker, NICHT mit aufgeblasenen Nicht-Zielen
    (gemessen: aufgeblasen findet Fall B gar keinen Pfad und Fall A einen 14.05"-Pfad statt 12.26");
    Wegpunkte, die die Engine nicht als ENDE akzeptiert, werden per `_free_landing_near()` (Caller
    `charge-route`) neu gelandet; die Follower gehen dieselben gerouteten Schritte zu eigenen Slots
    oder zu acht Punkten 1.5" hinter einem schon platzierten Squadmate und werden nur behalten, wenn
    sie den Anschluss (09.02) halten; danach läuft die gewöhnliche Spread-Phase über die Reste.
    **Warum geroutete Follower:** `--diagnose` zeigte 14 Fehlschläge, die per legalem Pfad
    erreichbar waren — das Leitmodell landete in 8, und die Follower (geradeaus mit ±45°-Ausweichen)
    verloren 7 davon.
  - **Machbarkeit VOR der Deklaration** (`_charge_nearest_legal_slot`): gibt es um KEINEN Feind in
    12" einen legalen Slot in 12" Luftlinie irgendeines Modells, wird die Charge NICHT angeboten
    (Fehlerklasse 5; `declined_charge` + `[charge] ... not offered`-Zeile); sonst wird der nötige
    Wurf aus dem LÄNGEREN von geroutetem Abstand und Weg zum nächsten legalen Slot gemeldet ("the
    near side is blocked"). 11.02s Eligibility und `observation.charge_now` bleiben Luftlinie —
    eigene Entscheidung, eigener Pin.
  - **Gemessen, gegen die Leiter vor der Sitzung** (alter Ring bei 1.0", kein Slot-zuerst):
    harte Welt **89 → 96 vollendet, 259 → 365 engagierte Modelle**; leichte Welt **96 → 100,
    349 → 447**. `--diagnose` danach: 3 Fehlschläge, 2 davon per Pfad erreichbar.
  - **Fall A (Lychguard + Overlord vs Krootox, 12", game_20260907_224519:966) ist per PFAD nicht
    erreichbar:** die Brute-Force zählte 87 legale engagierte Endpunkte in LUFTLINIE, der kürzeste
    legale Pfad zu irgendeinem legalen Slot ist 12.05–12.26" (Feindbasen blockieren den Transit,
    03.01). Die Ablehnung der KI war richtig; die Luftlinien-Zahl ist eine Untergrenze. Fall B
    (C'tan vs Dire Avengers, 6") wird seit der Landeplatz-Suche vollendet (Pfad 5.70").
  - Neu: `test_charge_slots.py`, `test_charge_slot_first.py`, `test_charge_feasibility.py`,
    `test_charge_retry_reactions.py` (Fehlerklasse 26); Sonden `ab_charge_slots.py`,
    `ab_charge_approach.py`, `ab_charge_retry.py`. `test_front_rank.py` §5 pinnt jetzt 11/11 im
    Engagement Range auf dem dichten Ring (vorher "< 11" als Szenen-Prämisse).
- **Disembark**: KLUMPEN statt Ring (Kandidaten nach Abstand zu einem Abwurfpunkt am ÄUSSEREN Rand
  der Zone, greedy kohärent gefüllt) — die Ringform erzeugte Ketten mit Single-Point-of-Failure.
  Gemessen 0 Bridge-Kanten und ≥95% Drift-Überleben gegen vorher 5 bzw. 73%. Acht Facings,
  Pro-Modell-Prüfung gegen `position_valid()` (inkl. Engagement Range — das Fehlen kostete einmal
  einen ganzen Trupp im Emergency Disembark), gemischte Basen: dichte Kandidaten aus der KLEINSTEN
  Basis, Vergabe breitestes Modell zuerst.
- **Front Rank**: Nahkampf-Charaktere werden ZUERST platziert (aus einer vorne-zuerst sortierten
  Kandidatenliste), nicht nachträglich getauscht — ein Tausch scheitert bei größerer Basis am Raster.
  Gilt für Aufstellung, Ausstieg und die Engagement-Slot-Vergabe. Übernommen wird nur, wenn die
  Variante nicht MEHR Kohärenz-Einzelpunkte hat (`bridge_count()`/`no_worse_than()`).

## Bewegungsqualität — was gemessen ist

Die wichtigste Einsicht dieses Repos zur KI-Bewegung, weil sie erklärt, warum Fixes lange nicht hielten:

- **`measure_crowded_movement.py` misst weiterhin die ORK-Armee, und zwar absichtlich.** Es baut
  seinen eigenen Roster und liest `config.PLAYER2_ARMY` nicht — beim Armeetausch also NICHT
  mitgezogen. Das ist hier richtig und nicht Fehlerklasse 16: es ist eine BASELINE, keine Suite.
  Jede Zahl im Abschnitt unten (54% → 64%, 185" → 206", "perfekte Reihenfolge ist ~3% wert", der
  verworfene Formations-Solver) wurde gegen genau diese Armee auf genau diesem Gelände gemessen;
  sie auf eine andere Armee umzuhängen würde die Zahlen nicht aktualisieren, sondern
  unvergleichbar machen. **Die Zahlen sagen also, wie gut die KI-Bewegung ist — nicht, wie gut die
  Bewegung der aktuellen Default-Armee ist.** Bis zum Armeetausch war das dieselbe Aussage.
- **`measure_movement_fixes.py` misst ein LEERES Brett** (`state.tokens = list(sq.models)`) —
  Blockierung durch eigene Einheiten kann darin per Konstruktion nicht auftreten. Jedes "300/300 ohne
  Stehenbleiben" stammt aus dieser Welt. `measure_crowded_movement.py` ist die ehrliche Welt.
- **Gemessen (map2, ganze Armee, 3 Züge):** allein 81%, mit der GEGNER-Armee 77% (kostet also nichts),
  mit der EIGENEN 54%. Der gesamte Verlust kommt daher, dass sich die eigenen Einheiten im Weg stehen.
- **Perfekte Bewegungsreihenfolge ist ~3% wert** (beste von 15 zufälligen gegen die eigene Heuristik)
  — eine Reservierungs-/Sortier-Umstellung wurde deshalb NICHT gebaut.
- **Der Formations-Solver ("erst eine legale Zielformation, dann hineinlaufen") ist gebaut, gemessen
  und ausgebaut worden**: 51% → 26%, nach zwei Reparaturen 37%. Die Winkelfreiheit der Sweep ist mehr
  wert als eine Kohärenz-Garantie, und die Sweep verwandelt bereits 89% ihres verbrauchten Budgets in
  Fortschritt — sie geht nicht in die falsche Richtung, sie kommt nur nicht weit genug.
- **Die "bewertete Platzierungs-Alternativen"-Umstellung ist ebenfalls gemessen und abgelehnt**
  (`measure_placement_headroom.py`): beim Vorrücken liegt die Decke auf dem, was die KI erreicht;
  Verstecken kostet auf diesem Gelände IMMER Boden (0 Plätze, die eine Einheit als FLÄCHE verdecken
  und einen halben Zug gewinnen); die vermeintliche Schussfeld-Lücke war fast vollständig ein
  Messfehler (jedem Modell wurde die beste Waffe der EINHEIT zugerechnet). Was die Messung
  STATTDESSEN fand — Einheiten scheitern an ihrer eigenen FORM — ist als `_place_packed()` umgesetzt.
- **Aktueller Stand (map2, Gedränge, seit der Wandhalbierung 2026-09-10):** Orks
  **65 % / 214.1" Gesamtboden** bei 1 Stall, Necrons **65 % / 127.3"**; isoliert Orks
  87 % / 292.3", Necrons 66 % / 136.7". Zahlen wie der Harness sie druckt (oberer Median).
  Ausgangslage der ganzen Messreihe war 54 % / 185".
  **Davor, mit den 0.60"-Wänden:** Orks 76 % / 232.9" und Necrons 60 % / 119.9", beide 0
  Stalls. **Diese eine Welt ist NICHT der Maßstab für die Änderung, die sie bewegt hat** —
  über alle vier Karten × beide Armeen gemessen ist der Gesamtboden **−0.4 %** und die
  Vorzeichen sind gegenläufig (map2/Necrons und map3/Orks gewinnen, was map2/Orks verliert);
  siehe `## Die Wände sind halb so dick`. Der Stall ist ein CROWDED-Effekt: ISOLIERT stallt
  auf keiner Karte etwas, und dort wird der Boden größer statt kleiner.
- **EINE Welt ist chaotisch, und das ist gemessen:** eine Änderung, die den ERSTEN Zug der
  Deffkoptas um 0.8" verschiebt, verändert jeden späteren Zug (−12" in derselben Welt bei +0.7"
  lokaler Wirkung). Wer eine kleine Änderung beurteilt, misst sie PAARWEISE (jeder Zug zweimal vom
  selben Brett) oder über MEHRERE Welten (Reihenfolge der Einheiten gemischt, Feindband variiert;
  die Layout-Bänder 0.28–0.34 ergeben dasselbe Brett) — so wurde die Leine als Null erkannt.
- **Charges haben seit derselben Sitzung ihren eigenen Harness** (`measure_charge_scenes.py`):
  harte Welt 96 von 100 möglichen Charges vollendet / 365 engagierte Modelle (vorher 89 / 259),
  leichte Welt 100 / 447 (vorher 96 / 349). Die Decke: von den 4 Fehlschlägen sind 2 per legalem
  Pfad erreichbar.
- **Verbleibende Grenze ist teils physisch**: ein 3.5"-Schlitz nimmt keine drei 0.98"-Basen kohärent
  auf, und der Umweg ist länger als eine Zugbewegung. Das richtig zu lösen bräuchte
  formationsbewusste Pfadsuche plus Mehrzug-Planung — die naive Version davon ist gemessen und
  verworfen.
