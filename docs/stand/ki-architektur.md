# KI-Architektur

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## KI-Architektur

`ai/agent_driver.py`, `ai/claude_agent.py`, `ai/observation.py`, `ai/planner_prompt.py`,
`ai/tactical_prompt.py`. Enumerierte Optionen statt Freitext-Tools (`choose_action(index)`), ein
API-Call nur bei echter Wahl. **Die KI spielt die Orks; Aeldari-Regeln haben per User-Vorgabe keinen
KI-Pfad.**

- **Zwei Schichten.** Der taktische Layer bekommt seine Optionen von der ENGINE — eine regelwidrige
  Aktion taucht gar nicht erst auf. Der Planner schreibt Freitext und kann jede Regel verletzen;
  deshalb existiert `_validate_turn_plan()` als deterministischer Backstop (Reserverunde 20.03,
  Disembark-Zeitpunkt, LONE OPERATIVE, verschwundene Ziele, unerreichbare Positionen — geklemmt auf
  den ersten Schenkel derselben Linie, seit 2026-09-09 in JEDER Größe —, Rückwärtsbefehle — eine
  Position, die weiter vom eigenen Ziel liegt als der Standort, wird durch den ersten Schenkel zum
  Ziel ersetzt —, Über- und Ein-Einheiten-Garnison, kollidierende Positionen, unbeschießbare
  Zielorte). Jede künftige Planungs-Regelverletzung gehört DORTHIN, nicht in den Prompt.
- **Der Garnisons-Tausch sortiert nach ROLLE, dann erst nach Punkten**
  (`_cheaper_garrison_candidates()`, Schlüssel `(is_assault_unit, cost, gap)`). Billigstes-zuerst
  allein hat den Job dem billigsten Trupp gegeben — und die Nahkämpfer einer Armee sind regelmäßig
  ihre billigsten, **also hat ausgerechnet die Korrektur, die verhindern soll, dass gute Einheiten
  auf leerem Boden verschwendet werden, selbst ausgewählt, welche gute Einheit verschwendet wird**.
  Gemeldet als "die lych guard waren sehr passiv. die sollten eher weiter nach vorne pushen"; der
  stärkste Fall im Log ist nicht die gemeldete Einheit, sondern die, die dieser Pass ZUGEWIESEN
  hat: er nahm die 270-Punkte-Necron-Warriors von P2 Home und gab den Job den 85-Punkte-Skorpekh
  Destroyers (0.0x Fernkampf/Nahkampf, gar keine Fernkampfwaffen), die danach **vier von fünf
  Zügen** auf Boden standen, dem kein Feind auf 12" nahe kam. Auf dem gemeldeten Brett gemessen:
  der Job geht jetzt an die Lokhust Destroyers (6.7x), **obwohl die teurer sind** — Rolle schlägt
  Punkte.
  **Die Lychguard selbst waren davon zunächst NICHT betroffen** (ihr `hold` kam dreimal in Folge
  direkt aus dem Plan, auf einem UMKÄMPFTEN Objective, das der Over-Garrison-Pass zu Recht
  ausnimmt) — bis dieselbe Form auf dem HOME Objective wiederkam, siehe den nächsten Punkt.
- **Home-Garnison: Fernkampf schlägt Punkte, an ALLEN DREI Stellen, die das entscheiden** (User:
  "die ki soll fernkampfeinheiten stark bevorzugen, wenn es darum geht das home objective zu
  halten. sie hat im letzten spiel dafür die lychguard benutzt, was völliger quatsch ist. die
  immortals wären perfekt. starke fernkämpfer mit hoher reichweite").
  - **Der Sortierschlüssel oben war die halbe Antwort, und die andere Hälfte war der FILTER.**
    "Strikt billiger als der Holder" war die ganze Definition eines lohnenden Tausches, also
    konnte der Pass eine Garnison nur die Punkteliste ABWÄRTS bewegen — die Immortals kamen als
    Kandidat gar nicht erst in Betracht, weil sie mehr kosten. Im gemeldeten Spiel
    (`logs/game_20260826_234856.log`, Zeilen 124-125) nahm er P2 Home den 270-Punkte-Necron-Warriors
    ab und gab es den 170-Punkte-Lychguard. Das Tor ist jetzt dasselbe `(Band, Punkte)`-Paar wie
    die Ordnung: **ein Trupp, der für den Job SCHLECHTER wäre, ist kein Kandidat dafür, wie billig
    er auch ist.** Die alte Begründung dagegen ("eine Garnison, die nicht stattfindet, verliert
    das Objective") gilt hier nachweislich nicht — es ist der EIN-Holder-Fall, ein abgelehnter
    Tausch lässt den Holder stehen. Als Invariante gepinnt statt behauptet.
  - **Die eigentliche Ursache lag aber eine Phase FRÜHER**, und der Turn-Plan-Pass hat sie nur
    bestätigt: `deployment_ai.home_garrison_squad()` wählte rein nach Punkten, und in der
    Necron-Liste ist die BILLIGSTE Einheit der ganzen Armee die Lychguard mit 170 — also bekam
    der Nahkampf-Amboss den Job in jedem Spiel. Deshalb standen die Immortals im gemeldeten Log
    auch 12" und 20" vom Objective entfernt: für den Turn-Plan-Pass unerreichbar. **Eine Sonde,
    die eine Immortals-Einheit neben das Objective gestellt hätte, hätte einen Fix gemeldet, den
    das echte Spiel nicht hätte nutzen können.**
  - **BEIDE HÄLFTEN DER USER-AUSSAGE SIND EIGENE TERME**, und das ist der Befund, der die Form
    bestimmt hat: "Fernkämpfer" und "hohe Reichweite" wählen NICHT dieselben Einheiten. Die
    Aeldari-Wraithguard lesen sich als Fernkampfeinheit (Ratio 2.00) auf einer 12"-Waffe — vom
    Home Objective aus tragen sie exakt so wenig bei wie die Lychguard. `home_garrison_rank()`
    setzt eine Einheit deshalb nur dann ins oberste Band, wenn ihr Schaden aus dem Schießen kommt
    UND dieses Schießen von dort hinten überhaupt etwas erreicht.
  - **DREI BÄNDER statt eines Scores** (`game/combat_focus.py`, vierter Konsument derselben
    Messung nach Charge-Sperre, `assault`-Aufstellungsrolle und Garnisons-Tausch): SHOOTER /
    neutral / ASSAULT, und die Punkte entscheiden INNERHALB eines Bandes. Ein kontinuierlicher
    Score hätte den Punkte-Term überall überstimmt — bei den Orks hätte er den Job von den
    45-Punkte-Gretchin auf den 160-Punkte-Battlewagon verschoben. Gemessen und deshalb verworfen.
  - **Die Reichweiten-Schranke wird am BRETT gemessen, nicht gesetzt**
    (`observation.garrison_reach_needed_in()`): Abstand zum NÄCHSTEN anderen Objective, also zum
    nächsten Boden, um den überhaupt gekämpft wird — 17.1" (map1), 14.8" (map2), 11.6"/13.8"
    (map3, und dort als einziges pro Spieler VERSCHIEDEN). Eine feste Zahl hätte auf allen drei
    zufällig gestimmt und genau diesen letzten Fall still verfehlt. **Bewusst NICHT der Abstand
    zum Niemandsland** — der beträgt vom Home Objective aus nur 3.8-5.2" und hätte jede
    12"-Waffe durchgelassen.
  - **Fünfzehnte Extraktion: `agent_driver._garrison_fitness()`.** Drei Stellen beantworten
    "wen lassen wir hier stehen" — der Over-Garrison-Pass (Keeper aus zwei oder drei), sein
    planner-seitiger Zwilling und der Lone-Swap-Pass. Zwei Ordnungen hätten den ersten genau die
    Einheit behalten lassen, die der dritte nicht mehr wählen soll. Quell-Wächter prüft, dass es
    genau eine Definition und drei Leser gibt.
  - **Gemessen, nicht behauptet** (`measure_home_garrison.py`, A/B über `--neutralize`):
    Aufstellung auf allen drei Karten Lychguard → **Immortals 1**; Orks (**Gretchin** — seit
    Orks E3c auf map1-3 die Tankbustas, siehe `## Ork-Spezialisten`) und
    Aeldari (**Warlock Skyrunners**) unverändert, also trifft die Änderung genau die gemeldete
    Liste. Auf dem gemeldeten Brett findet der Turn-Plan-Pass **keinen Tausch mehr**. Im ECHTEN
    Selbstspiellauf: `2 Immortals 1 + Plasmancer (shooter) deployed at (30.0,6.0) (fully hidden,
    rule 13.09) ... 11/11 models` — auf dem Home Objective, während die Lychguard an der Flanke
    stehen.
  - **Der Preis ist gemessen und benannt:** die Skorpekh Destroyers waren im alten Test-Roster
    die Home-Garnison (85 Punkte, die billigste Einheit) und hatten ihre 13.09-Deckung genau
    dort. Freigestellt gehen sie **+0.97" → +2.98"** nach vorn und verlieren **3/3 → 0/3**
    Deckung; die Immortals gehen dafür **0/11 → 11/11**, und die Armee insgesamt von **15 auf 25**
    verdeckten Modellen. Vorwärts zuerst ist die vom User selbst gesetzte Reihenfolge der beiden
    Klauseln. `measure_deployment_safety.py` bleibt auf beiden Karten PASS.
  - **Auch im Planner-Prompt**, weil eine Regel nur in der Durchsetzung jeden Zug eine Korrektur
    erzeugt: die alte Zeile "Garrison with the cheapest unit that holds it" ist ersetzt durch die
    Fernkampf-Regel samt Begründung ("a gun on a home objective keeps firing every turn it stands
    there") und der Gegenrichtung für ein UMKÄMPFTES Objective.
  - **Getestet:** neu `test_home_garrison.py` (**79/79**) plus drei A/B-Sonden, jede kippt genau
    ihre eigenen Prüfungen; `test_over_garrison.py` von 61 auf **71/71** (Abschnitte 9 und 10
    ehrlich umgeschrieben, siehe unten); `test_report_20260824.py` **65/65**.
- **Ein Retry-Kanal zurück an den Planner** (`_problems_for_the_planner()`) für Probleme, deren
  Lösung ein Urteil braucht, das der Code nicht fällen kann: ein LONE-OPERATIVE-Ziel, das vom
  bestellten Standort nicht beschießbar ist (war der Standort oder das Ziel der Punkt?), eine zu
  große Garnison (welche Einheit wird frei, und wofür?), eine allein geparkte. Läuft im
  Hintergrund-Thread, genau EINMAL, und wird nur übernommen, wenn er messbar weniger Probleme hat
  UND mindestens so viele echte Squads abdeckt — sonst ist "alle Befehle löschen" die billigste Art,
  perfekt zu punkten (genau so ist einmal ein ganzer Zug ohne Plan gelaufen).
  **Zu weite Positionen gehen NICHT mehr zurück** (bis 2026-09-09: ab 3" Überschuss). Das Argument
  dafür war richtig — eine Koordinate wird für eine EIGENSCHAFT gewählt, der Punkt auf der
  Linie erbt keine — und der Retry trotzdem die falsche Antwort, siehe Fehlerklasse 27.
- **Der Planner schickt Einheiten nicht mehr zu weit — und nicht mehr rückwärts** (User: „warum
  der planner die einheit überhaupt zu weit schickt. meiner meinung nach sollte er nur erreichbare
  positionen planen und dann eben staging positions mitgeben nicht gleich das endgültige ziel").
  Drei Stücke, ein Punkt: `observation.first_leg_toward(squad, goal, reach, obstacles)` ist die
  EINE Definition des ersten Schenkels (Zentroid → Ziel, eine Marge innerhalb der Reichweite,
  erst seitlich bis 30° geschwenkt, dann zurückgewalkt, bis der Punkt weder auf einer Wand noch
  außerhalb des Bretts liegt — der Schwenk zuerst, weil die gemessene Linie der Wraiths auf map4
  vier Zoll lang eine dünne L-Wand STREIFT und Zurückwalken allein 10" auf 5.9" verkürzt hätte).
  Die Beobachtung hängt ihn als `first_leg_this_turn` (+`if_you_advance`) an jeden Objective- und
  Feindeintrag, dessen Mitte außer einer Bewegung liegt (Passagiere ausgenommen, wie beim
  Staging); der Prompt sagt, dass ein fernes Ziel als TARGET und sein Schenkel als POSITION zu
  nennen ist; und der Validator klemmt jeden Überschuss auf denselben Helfer und ersetzt einen
  RÜCKWÄRTSBEFEHL (aktive Rolle, Ziel außer Reichweite, Position mehr als 1" weiter vom Ziel als
  der Standort; Ziel aus dem `target`-Feld oder — wie im Log — aus dem Reason-Text) durch den
  Schenkel zum Ziel, im Advance-Band, wenn der Befehl eines brauchte, mit umgeschriebenem
  `reason` (Fehlerklasse 4). Auf der gemeldeten Szene: (25,20) → geklemmt auf (28,16) ohne
  zweiten Planner-Call; (44,7) → ersetzt durch (30,17), 5" statt 21" vom Objective.
  **Bewusst NICHT angefasst:** eine Einheit, deren Ziel schon in Reichweite liegt, darf sich davon
  weg feinjustieren (aus einem Charge-Bogen, in eine Schusslinie); passive Rollen behalten ihre
  Koordinate. Getestet: `test_plan_first_leg.py` (**79**), `ab_plan_first_leg.py` (11 Sonden);
  `test_plan_churn.py` und `test_empty_turn_plan.py` pinnten den alten Retry und sind ehrlich
  umgeschrieben (letzterer trägt jetzt ein LONE-OPERATIVE-Problem als Kanal-Last).
- **Ereignisgesteuerte Neuplanung** (gegnerische Einheit stirbt, Charge scheitert), gedeckelt auf 2
  pro Zug, plus Revalidierung an jeder Phasengrenze (reine Arithmetik, kein API-Call). Der alte Plan
  bleibt in Kraft, während der neue entsteht — der Zug friert nie ein.
- **Modelle**: `config.AI_MODEL` (Haiku) für Einzelentscheidungen, `config.AI_PLANNING_MODEL`
  (Sonnet) für den einen Plan-Call pro Zug. Haiku-Pläne waren gemessen zu passiv/regelwidrig.
- **"Planner vor jeder Aktion" wurde gemessen und abgelehnt**: 15-25 Sonnet-Calls pro Zug, und der
  Nutzen eines Plans ist gerade die Zuteilung ÜBER Einheiten hinweg (Greedy-vs-Global). Der taktische
  Layer IST die reaktive Schicht.
- **Beide Prompts sind aufgeräumt** und in eigenen Modulen (Planner 19.4k → 11.2k Zeichen, taktisch
  15.2k → 11.4k), mit benannten Abschnitten und `HOW TO DECIDE` bei 2-6% statt 66%. Neue Regeln
  gehören in den passenden Abschnitt, nicht ans Ende — beide waren durch reine Anlagerung gewachsen,
  und einmal kam ein Plan als Tool-Call-Markup zurück. **Eine Taktik als ZAHL an einer Option wird
  befolgt; dieselbe Taktik als Prosa konkurriert mit allem anderen.**
- **Bewertung**: `game/damage_estimate.py` (`expected_wounds`/`expected_kills`/`damage_value`) ist die
  EINE Schätzung, gelesen von Bedrohungszahlen, Zielwahl, Reserve-Landeplatz, Nahkampf-Waffenwahl und
  drei Stratagem-Gates. Sie rechnet Punkte statt Anteile (ein Spezialist wird sonst auf Massen
  gelenkt), deckelt Überkill, liest RESTwunden, und berücksichtigt Modifikatoren, die nur vom
  angreifenden Modell und der Zieleinheit abhängen (Tank Hunters, Guardian Drone). Eine
  MEHRPROFIL-Waffe liest sie über `weapon_profiles.valued_profiles()` als das Profil, das die KI
  feuern würde (seit Orks E3c; vorher nur das getragene erste).
  **Bekannte Untererfassung, bewusst:** Re-rolls, [SUSTAINED HITS]/[LETHAL HITS]/[DEVASTATING WOUNDS],
  Deckung, Granaten und die meisten Fähigkeiten (Volley Fire, Waaagh!, Might is Right) fehlen — die
  Schätzung ist durchgehend eine UNTERGRENZE. Positionsabhängige Effekte bleiben draußen, weil sie
  auch für HYPOTHETISCHE Positionen aufgerufen wird.
- **Beobachtung** liefert u.a.: Waffen beider Seiten, `defensive_profile`, `threat_assessment`
  (Bedrohung + Handel, getrennt nach `best_to_shoot`/`best_to_charge`), `charge_threats` (Wurf +
  Odds, auch für einen geplanten ZIELORT), `staging_positions` (nur was nach der GEGNERbewegung noch
  hält und Boden GEWINNT), `reachable_this_turn` (mit `if_you_advance`), `first_leg_this_turn`
  an jedem Objective- und Feindeintrag außer Reichweite (der Wegpunkt zum Auswählen),
  `if_you_disembark` / `if_you_stay_aboard`, Terrain, Hidden-Status, `waaagh`, `charge_now` inkl.
  `chance_if_you_advance_first` (exakte gemeinsame Verteilung über beide Würfe, nicht "Mittelwert
  dann Charge").
- **Deterministische Entscheidungen ohne API-Call** (jeweils weil es ein VOLLSTÄNDIGES Verfahren ohne
  Restermessen gibt, und ein Test mit werfendem Agenten belegt die 0 Calls): Command Re-roll auf einen
  verfehlten Charge (verfehlt + Nahkampfeinheit + Lücke ≤7"), War Cry (`war_cry_verdict`), der
  Waaagh!-Advance-Reroll (unter 4), War Horde (Da Boss is Watchin', Fungus-Fuel Injection,
  Close-Range Dakka, Hit 'Em Harder, Mow 'Em Down als `_handle_*` ohne `agent`; Breakin' Heads und
  Orks Is Never Beaten über `auto_players` plus injiziertes Urteil), Ammo Runt, Boss' Ammo Runt, die
  zwei Boss-Motivationen (`boss_motivation_choice`), Catch Dat Red Bit (`catch_dat_red_bit_verdict`),
  Krushin' Impetus' Zielwahl, Bomb Squigs (sofort, Ziel per Schadensranking), Pulsa Rokkit
  (markiert immer), Rokkit Barrages Zielwahl (`battle_shock_target_choice`),
  Spirit of Gork — und die
  **gesamte Necron-Fraktion**: Reanimation Protocols samt Warriors-Reroll, Resurrection Orb,
  Technomancer, Matter Absorption, Living Lightning, Wraith Form und alle sechs
  Awakened-Dynasty-Protokolle. **Und seit Etappe 3 auch der Plasmacyte** — er stand hier
  einmal zu Unrecht (`use()` hatte ueberhaupt keinen Aufrufer, die Faehigkeit war fuer
  BEIDE Seiten unverdrahtet), und das ist mit dem ZWEITEN Traeger derselben gedruckten
  Wargear-Zeile behoben: der Offer haengt jetzt an `FightController._start_fighting()`,
  deterministisch fuer `auto_players` und als Prompt fuer den Menschen. Die drei proaktiven
  davon (Hungry Void, Sudden Storm, Conquering
  Tyrant) über `_verdict()`/`_handle_*()`-Paare, alles übrige über `auto_players`.
- **Fernkampfeinheiten bekommen den Charge gar nicht erst angeboten** (`game/combat_focus.py`,
  gelesen von `_shooting_specialist_charge_block()`). User: "havey destroyer - die sollten nicht
  chargen. das sind fernkampf einheiten ... baue gerne eine charge sperre ein, wenn die
  fernkampfwaffen so extrem viel stärker sind als die nahkampfwaffen. aber ... shard of the void
  dragen. da soll die sperre nicht greifen." WITHHELD statt begründet (Fehlerklasse 5) und spart den
  API-Call; der Vermerk läuft über `memory.declined_charge`, also genau eine Logzeile pro Phase, mit
  BEIDEN Schadenszahlen darin.
  - **Die Messung ist bewusst ZIELFREI, obwohl im Charge-Moment ein Ziel vorliegt.** Die
    Pro-Ziel-Ratio wurde zuerst gebaut und gemessen und trennt NICHT: gegen 1-Wunden-T2-Gretchin
    wundet alles, also stehen die Immortals dort bei 1.03, während die Necron Warriors — die frei
    bleiben müssen — gegen ein Deff Dread 1.19 erreichen. Die beiden Mengen überlappen, und eine
    Schwelle in einer Überlappung entscheidet danach, welcher Feind zufällig am nächsten steht.
    Das eigene Profil trennt sauber (Band 1.09..1.70, Schwelle 1.4).
  - **Der Void Dragon verfehlt die Sperre um den Faktor sechs** (0.23) — kein Grenzfall. Die
    einzige Einheit nahe der Linie sind die Ork Warbikers (1.00 gegen diesen Referenzverteidiger,
    1.50 gegen einen T8/3+/8W-Vergleich); benannt statt weggestimmt. Kein Ork-Datenblatt wird
    von der Sperre erfasst.

## Ein API-Fehler stoppt die KI, nicht das Spiel (ai/connection.py)

**Gemeldet:** *"momentan stürzt das Spiel ab, wenn KI Modus an ist und die Verbindung verloren geht
oder api Fehler oder Guthaben leer. besser wäre eine Meldung 'Connection lost' und das Spiel geht
aber ohne KI weiter."*

**Reproduziert durch die ECHTE `main()`-Schleife**, bevor etwas geändert wurde: ein Agent, der beim
ersten Aufruf `anthropic.APIConnectionError` wirft, beendet den Lauf mit
`CRASHED OUT OF main(): APIConnectionError` bei **0 weiteren Frames**.

- **Der PLANNER war längst abgesichert** (`except Exception ... out["error"]`, mit dem Kommentar
  „the whole point is to not crash the game"); der taktische `agent.decide()`-Aufruf war es nicht.
  Ein Abfangen an genau einer der beiden Stellen ist die Form, die dieses Repo als
  Fehlerklasse 10 führt.
- **`ai/connection.py` beantwortet EINE Frage** — ist der Agent erreichbar, und wenn nicht, warum.
  Vier Ausfälle interessieren einen Spieler (tote Verbindung, abgelehnter Key, leeres Guthaben,
  Rate Limit) und das SDK schreibt sie als vier Typen plus eine Statusfamilie; die Reaktion des
  Spiels ist auf alle vier dieselbe. Also eine Antwort statt einer Taxonomie, auf die nichts
  verzweigt.
- **`connection.ask(call, *args)` ist die EINE Grenze zwischen Engine und Agent** — und sie liegt
  dort und nicht in `ai/claude_agent.py`, weil `agent` ein INTERFACE ist (`ai/base.py`): nur den
  Anthropic-Client abzusichern ließe jede andere Implementierung (MockAgent, ein späteres lokales
  Modell, ein Harness-Stub) das Spiel weiter abstürzen. **Genau drei Aufrufstellen** (ein
  `decide`, zwei `plan_turn`) — die ganze Außenfläche der Engine, im Test gezählt.
  **Erst am Agenten gebaut, dann verschoben:** die erste Fassung saß in `ClaudeAgent`, und die
  Reproduktion (die MockAgent benutzt) stürzte weiter ab — der Beweis, dass die Grenze das
  Interface ist und nicht die eine Implementierung.
- **`except Exception`, bewusst, aber ENG UMSCHLOSSEN.** Eine Liste von anthropic-Klassen ließe den
  fünften Typ weiter krachen, was genau der gemeldete Fehler ist; `describe()` NENNT dafür jeden
  unerwarteten Typ beim Namen, statt ihn als „no connection" zu verkleiden — sonst schickt ein Bug
  im Agenten jemanden zum Router. Umschlossen ist nur der Agent-Aufruf: `take_one_action()` fängt
  **ausschließlich `AIUnavailable`**, also stürzt ein echter Handler-Bug weiter laut ab. Eine
  stillschweigend übersprungene KI-Runde ist viel schwerer zu bemerken als ein Traceback.
- **EIN LATCH, kein Retry.** Jeder dieser Ausfälle hält länger als einen Frame, und die Schleife
  fragt den Agenten bei Auto-Play mehrmals pro Sekunde: ein Wiederversuch machte aus einer
  verlorenen Verbindung einen Strom von Timeouts, jeder davon ein hängender Frame. `take_one_action()`
  prüft `is_online()` deshalb VOR dem Aufruf, nicht nur danach. Der ERSTE Fehler ist außerdem der
  einzig informative — jeder weitere ist seine Folge —, also gewinnt er.
- **Die Meldung sagt, was jetzt zu tun ist.** „Connection lost" allein ließe einen Spieler warten,
  dass es zurückkommt; die zweite Zeile ist die wichtige („The battle continues - you now take its
  turns as well"). Danger-Akzent, als einzige Meldung des Spiels, die einen Fehler meldet statt
  eines Ereignisses. EIN Slot statt der Queue ihrer zwei Geschwister: ein Waaagh! kann wieder
  passieren, „die KI hat aufgehört" ist ein Ereignis, dessen Wiederholung dasselbe Ereignis ist.
  Sie führt `_front_notice()` direkt hinter dem Battle-End an — alles dahinter handelt von einem
  Spiel, dessen Vorzeichen sich gerade geändert haben.
- **Dass es „weitergeht", ist keine Annahme:** der „Next Phase"-Zweig ist nicht auf den Turn-Owner
  gegatet, der Mensch kann die Phasen der KI also selbst weiterschalten. Geprüft, bevor der Rest
  entworfen wurde — ohne das wäre „ohne KI weiter" ein eingefrorenes Spiel gewesen.

**Getestet:** neu `test_ai_offline.py` (**50/50**, sechs Abschnitte) plus `ab_ai_offline.py`
(**9 A/B-Sonden, alle beißend**). Die tragende Prüfung ist nicht „eine Ausnahme wurde gefangen",
sondern dass der Fang ENG ist: eine Sonde, die `except AIUnavailable` auf `except Exception`
verbreitert, muss rot werden — sonst wäre der bequeme falsche Fix nicht von dem richtigen zu
unterscheiden.
**Drei Befunde über den TEST**, alle von den Sonden: zwei ließen die Suite ABSTÜRZEN statt rot zu
werden (`AIUnavailable` aus dem Test heraus, `str.index()` auf einen fehlenden Namen) — **achte und
neunte Instanz** dieser Lehre —, und ein Verdrahtungs-Pin prüfte nur den TEILSTRING
`ai_offline_overlay.show(...)`, der ein `if False and ...` überlebt: er pinnt jetzt die ganze
Anweisung.

**Im ECHTEN Spiel belegt** (`verify_ai_offline.py`, `runpy` auf `selfplay.py`s echte Schleife):

| | gefixt | `--neutralize` (Vor-Fix) |
|---|---|---|
| Absturz aus `main()` | **nein** | `APIConnectionError` |
| offline gelatcht | True (`no connection to the API`) | False |
| Meldung erhoben | **1×** | 0× |
| Frames NACH dem Ausfall | **919** | 0 |

Die letzte Zeile ist die eigentliche Zusicherung: „stürzt nicht ab" und „spielt weiter" sind zwei
verschiedene Behauptungen, und nur die zweite war die Bitte.
