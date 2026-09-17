# Meldungen aus Partien (2)

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## "TARGET: One <X> unit from your army" wurde NICHT gewählt (2026-09-08)

**Gemeldet:** *"cost of victory wird mir pauschal angeboten, aber ich habe 3 guardian squads. ich
kann nicht wählen welchen squad zurück in reserve schicken will. es muss auf dem feld angeklickt
werden."*

- **Reproduziert an der Quelle, bevor etwas angefasst wurde:** mit drei berechtigten Guardian
  Defenders öffnete das Angebot einen Prompt, der EINEN von ihnen nannte — den in Sortierreihenfolge
  ersten —, mit den Optionen `['Use (1 CP)', 'Decline']`, **keine davon mit einem Squad getaggt**,
  also gab `unit_pick.pending()` `None` zurück und es konnte nie ein Brett-Klick sein. Der Spieler
  wurde gebeten, eine Wahl zu bestätigen, die die Engine schon getroffen hatte.
- **VIER Stratagems hatten diese Form, und alle vier drucken dieselbe TARGET-Zeile:** Cost of
  Victory (GUARDIANS), Webway Tunnel (ASURYANI INFANTRY), Skyborne Sanctuary (unengaged ASURYANI)
  und Overflight (ASURYANI MOUNTED). **"One <X> unit from your army" ist eine Wahl des SPIELERS**;
  jedes der vier lief über die berechtigten Einheiten, bot die erste an und kehrte zurück.
- **Das FÜNFTE mit derselben gedruckten Zeile war schon richtig gebaut** — Kauyons Wall of Mirrors
  (`[(s.name, cb, s) for s in candidates]`), und genau das macht die vier als Defekt lesbar statt
  als Design. Ausgerechnet Cost of Victorys eigener Docstring vergleicht sich mit dessen Nachbarn.

### `game/unit_choice_offer.py` — 33. Extraktion, und NICHT `per_unit_offer`

Die zwei sind leicht zu verwechseln, weil der FALSCHE Code für beide gleich aussieht:

| Modul | Frage | Prompts |
|---|---|---|
| `per_unit_offer.offer_each()` | "JEDE berechtigte Einheit bekommt ihr EIGENES Angebot" (eine FÄHIGKEIT: Airborne Agility, Ride the Wind, Cloudstrider) | N, verkettet |
| `unit_choice_offer.offer_one_of()` | "der Spieler wählt EINE davon" (ein STRATAGEM) | 1, N getaggte Optionen |

**Die vier waren zu keiner der beiden Formen geschrieben:** ein Prompt über eine willkürlich
gewählte Einheit beantwortet keine der zwei Fragen.

- **EIN Request statt einer Kette**, und das ist keine Abkürzung: `per_unit_offer` verkettet
  bewusst, weil sich Eignung zwischen Antworten ändern kann und Ride the Wind einen laufenden
  Zähler druckt. Bei EINER Wahl gilt beides nicht — und jeder Kandidat muss GLEICHZEITIG sichtbar
  sein, damit ein Brett-Pick überhaupt etwas bedeutet: **die Ringe SIND der Prompt**.
- **Das FENSTER bleibt beim Aufrufer.** `PhaseWindow` zu armen ist zwei Zeilen, aber WER an einer
  Phasengrenze reagieren darf, ist die gedruckte WHEN-Zeile ("your opponent's Fight phase" bietet
  der Gegenseite; "the end of THE Fight phase" gehört niemandem und bietet beiden) — eingefaltet
  wäre das ein Flag je WHEN-Klausel für eine Frage, die das Modul nicht sehen kann.

### Skyborne Sanctuary ist ZWEISTUFIG, weil seine TARGET-Zeile ZWEI Dinge nennt

"One unengaged ASURYANI unit ... **and** one friendly TRANSPORT it is able to embark within" — es
fragte nach keinem von beiden: Prompt über die erstsortierte Einheit, Transporter still als
`transports_for(squad)[0]`. Jetzt Brett-Pick für die Einheit, danach eine gewöhnliche LISTE für den
Transporter — **und nur, wenn es wirklich mehr als einen gibt** (Fehlerklasse 5). Dass die alte
Ein-Schritt-Fassung überall dort richtig las, wo genau ein Wave Serpent in Reichweite stand, ist der
Grund, warum sie überlebt hat. Eine LISTE und kein zweiter Brett-Pick: die Optionen nennen
TRANSPORTER desselben Spielers, die unter der gerade angeklickten Einheit stehen können.

### Warum keine der vier Suiten es sah

**Jede stagt genau EINE berechtigte Einheit** — und bei einem Kandidaten sind die kaputte und die
richtige Form nicht unterscheidbar. Deshalb ist die tragende Prüfung der neuen Suite nicht "ein
Prompt ging auf", sondern **"ein Klick auf den ZWEITEN Kandidaten löst den ZWEITEN auf"**: eine
bloße Options-ZÄHLUNG besteht auch gegen ein Angebot, das jede Option auf dieselbe Einheit
verdrahtet (die Late-Binding-Sonde belegt genau das).

### Der Wächter: `test_event_chain_wiring.py` §18

**Ein Angebot, das seinen Request INNERHALB einer Kandidaten-Schleife erhebt, muss mindestens eine
Option mit einer Einheit TAGGEN.** Eine Einheit im Prompt-TEXT zu nennen und ein nacktes Ja/Nein
anzubieten ist die gemeldete Form. Faction-blind, per AST, mit Liveness-Zeile.

- **Was er BEWUSST nicht meldet, gemessen statt angenommen:** vier per-Unit-FÄHIGKEITEN erheben
  ihren Request ebenfalls in so einer Schleife (`auxiliary_cadre`, `elemental_ensnarement`,
  `hallucinogen_grenades`, `neocapacitor_shields`). Alle vier taggen ihre Optionen mit der
  FEIND-Einheit, die die Fähigkeit anzielt — dort wird also weiterhin auf dem Brett gewählt, und die
  Schleife läuft über TRÄGER, was eine andere Frage ist. Ein Wächter, der sie meldet, ist eine
  Fehlalarm-Maschine, und ein Wächter mit Fehlalarmen wird gelöscht.
- **Er muss ein LOKALES auflösen**, und das hat seine eigene erste Runde gefunden:
  `neocapacitor_shields` baut `options = [...]` und übergibt dann den Namen — eine Prüfung, die nur
  die Argumente des Aufrufs durchsucht, meldete einen sehr wohl anklickbaren Prompt als ungetaggt.
  Eigene A/B-Sonde dafür.

### Ein fremder Wächter wurde zu Recht rot, und ist gewachsen statt aufgeweicht

`test_ai_mode.py`s "no class takes auto_players and ignores it" meldete alle vier: sie LESEN
`self.auto_players` nicht mehr, sie reichen es an den geteilten Helfer weiter. Der `forwards`-Term
kannte nur die Weitergabe an eine BASIS-Klasse. Er kennt jetzt auch die an einen KOLLABORATOR — und
**die Zusicherung ruht nicht auf dem Token**: alle vier werden in der neuen Suite mit einem
KI-Besitzer gefahren und müssen nichts anbieten und ihr Fenster wieder schließen.

### Getestet

- Neu `test_unit_choice_offers.py` (**64/64**, sechs Abschnitte — eine Datei für EINEN Defekt über
  vier Module, dieselbe Begründung wie `test_mortal_wound_drains.py`), plus Wall of Mirrors als
  gemessene REFERENZ. `test_event_chain_wiring.py` → **142/142** (neuer §18),
  `test_ai_mode.py` **61/61**.
- **Neu `ab_unit_choice_offers.py`: 12 A/B-Sonden an der QUELLE, alle beißend** — je Controller die
  alte Schleife byte-für-byte zurück, dazu drei auf den Helfer selbst (Tag weg → 42/64, nur der
  erste Kandidat → 48/64, Late Binding → 59/64) und die ganze Vor-Fix-Welt (**32/64**).
- **Zwei Befunde über den TEST, beide von den Sonden** (Fehlerklasse 24): die Sonden ließen die neue
  Suite zuerst ABSTÜRZEN statt rot zu werden (`unit_pick.pending()` gibt in der Vor-Fix-Welt `None`,
  und `.squads` darauf bricht den ganzen Lauf ab) — jetzt über einen `_NoPick`-Platzhalter; und die
  zwei Sonden gegen `test_aeldari_detachment_stratagems.py` bzw. `test_aeldari_stratagem_ui.py`
  meldeten **NO BITE**, was WAHR ist: die Suiten stagen eine Einheit und KÖNNEN diesen Defekt nicht
  sehen. Sie zielen jetzt auf den Quell-Wächter, der die Klasse wirklich abdeckt.
- Volle Regression **193 Suiten, ~17166 Prüfungen, 192 grün / 0 rot / 1 bekannt**,
  `run_tests.py --smoke` komplett grün (alle neun schweren Skripte).

### Im ECHTEN Spiel belegt

`verify_cost_of_victory_choice.py` fährt `selfplay.py`s echte `main()`-Schleife mit
**`aeldari_guardian_battlehost` als PLAYER 1** — der ausgelieferten Liste, die Guardian Battlehost
fieldet und **genau DREI GUARDIANS-Einheiten** hat, also die gemeldete Armeeform wörtlich, statt
einer für die Sonde erfundenen Szene. Sie liegt auf der MENSCHEN-Seite, weil eine Frage über dessen
Prompts sonst die Armee der KI misst (die Lehre der drei Necron-Sonden).

| | gefixt | `--neutralize` |
|---|---|---|
| berechtigte Einheiten auf dem Brett | 3 | 3 |
| vom Prompt genannte Einheiten | **3** | **0** |
| per Brett-Klick beantwortbar | **ja** | **NEIN** |
| geringte Einheiten | **3** | 0 |
| angeklickt wurde NICHT die erste | **2×** | 0 |
| die angeklickte Einheit zog sich zurück | **2×** | 0 |

`--neutralize` meldet die Meldung wörtlich: `prompt 'Cost of Victory (1 CP): pull 1 Guardian
Defenders 1 + Farseer + Warloc' -> NOT a board pick; 0 unit(s) named, 3 eligible on the board`.

**GESTELLT wird EINE Tatsache, und der Grund steht im Modulkopf:** dass die Schlacht überhaupt ein
Fight-Phasen-Ende erreicht. Auf diesem Harness überlebt allein die Schussphase das Framebudget, die
Grenze ist passiv also unerreichbar (die dokumentierte MockAgent-Grenze) — ein passiver Zähler hätte
0 gemeldet und wie ein Bestehen ausgesehen. Alles danach ist echt.

## Zwei Meldungen aus einer Partie (2026-09-08)

Beide reproduziert, bevor etwas angefasst wurde; beide haben eine Ursache, die MEHR als die
gemeldete Fähigkeit betrifft.

### "nur einer der beiden Vespid-Squads wurde gefragt" — drei Controller, ein Defekt

**Gemeldet:** *"ich habe 2 vespiden, aber die rückkehr in reserve wurde mir immer nur von einem der
beiden squads angeboten."*

- **Reproduziert an der Quelle:** zwei berechtigte Vespid-Einheiten, `offer_at_end_of_turn()` →
  **ein** Prompt. Der Rumpf war eine Schleife, die beim ERSTEN berechtigten Trupp `request()` rief
  und `return True` machte; `main.py` ruft die Methode genau einmal je Zugende, also gab es kein
  zweites Angebot.
- **Dieselbe Schleife steht dreimal da** — Airborne Agility (Vespid), Ride the Winds
  Rückzugs-Klausel (Windrider Host) und Cloudstrider (Aeldari) —, und alle drei tragen einen
  KOMMENTAR, der das Gegenteil verspricht: `main.py` schreibt neben den Aufruf "unlike Airborne
  Agility, which is per unit", und Cloudstrider schreibt die Ausrede aus ("one at a time; the next
  end of turn offers again"). **Das nächste Zugende ist ein ANDERER Moment derselben Fähigkeit,
  kein zweiter Versuch für diesen** — dieselbe Klasse wie `resolve_scouts()`' nie gebauter
  Menschenpfad: ein Kommentar, der ein Verhalten zusagt, das kein Code einlöst.
- **`game/per_unit_offer.py` ist die 32. Extraktion**, am zweiten UND dritten Konsumenten:
  `offer_each()` bietet EINEM Trupp an und hängt die Fortsetzung an BEIDE Optionen, also auch an
  die Absage.
  - **Warum verkettet und nicht alles auf einmal.** `DecisionManager` ist selbst eine Queue, ein
    `request()` je Einheit wäre also kürzer — und für Ride the Wind falsch: dessen Rückzug ist
    nach Schlachtgröße GEDECKELT und sein Prompt DRUCKT den Reststand. Vorab gebaut läsen alle
    dieselbe veraltete Zahl, und die Angebote jenseits des Deckels täten beim Annehmen nichts
    (Fehlerklasse 5). Verkettet wird die Eignung vor JEDEM Prompt neu gefragt, also stimmt der
    Zähler und der Deckel hält. **Gemessen:** vorher 1 Prompt und `remaining()` konnte sich nie
    bewegen; jetzt "2 of 2 left" → "1 of 2 left", dritte Einheit gar nicht mehr gefragt.
  - Der Reset des Zählers bleibt in `offer_at_end_of_turn()`, weil die Kette in `offer_each()`
    zurückkehrt und nie in die Methode — sonst schenkte eine Antwort mitten in der Kette eine
    frische Erlaubnis.
  - **Ein `auto_players`-Owner wird jetzt aus den KANDIDATEN gefiltert statt den Sweep zu beenden.**
    Die alte Form gab beim ersten KI-Trupp `return False`, ein menschlicher weiter hinten in der
    Sortierung bekam also gar kein Angebot. Was die KI TUT, ist unverändert: sie bleibt stehen.
- **Warum keine der drei Suiten es sah:** jede stellte GENAU EINE berechtigte Einheit. Die
  Prüfung ist deshalb jetzt die ZAHL über eine Zwei-Einheiten-Armee, durch die echte
  DecisionManager-Queue gedrainiert.
- **Getestet:** `test_tau_kroot_and_vespid.py` 140 → **146/146**, `test_aeldari_detachment_rules.py`
  380 → **385/385** (der Deckel-Fall mit drei Einheiten), `test_baharroth.py` 66 → **70/70**.
  Neu `ab_per_unit_offer.py` (**9 A/B-Sonden, alle beißend**) — je Controller die alte Schleife
  zurück, plus die Kette selbst ohne Fortsetzung gegen alle drei Suiten.
  **Ein Befund über den TEST:** zwei Sonden ließen `test_aeldari_detachment_rules.py` ABSTÜRZEN
  statt rot zu werden (Indizieren in eine Prompt-Liste, die in der Vor-Fix-Welt einen Eintrag
  hat) — die Prüfung polstert jetzt.
- **Im ECHTEN Spiel belegt** (`verify_airborne_agility_offers.py`, `runpy` auf `selfplay.py`s echte
  `main()`-Schleife, mit `tau_recon` — der einzigen ausgelieferten Liste mit ZWEI
  Vespid-Einheiten, also der gemeldeten Armeeform): der LIVE von `main()` gebaute Controller meldet
  **2 berechtigte Einheiten und 2 Prompts**; `--neutralize` (die alte Schleife) meldet
  **2 berechtigte und 1 Prompt** — die Meldung wörtlich.
  **Drei gestellte Tatsachen, jede mit Grund benannt:** die Position (die Ecke wird aus dem
  Standort des Gegners ABGELEITET — eine feste setzte sie beim ersten Lauf in Player 2s eigene
  Aufstellungskante), das Zugende, und ein FRISCHER `DecisionManager` für die Messung, weil die
  Kette eine ANTWORT braucht und die laufende Partie fast immer einen eigenen Prompt vorne in der
  Queue hat (gemessen: hier auch) — den auf Spielerkosten zu beantworten hätte die gemessene
  Partie verändert. Nur der Briefkasten ist getauscht.

### Defend Stronghold: die Endrunden-Karten konnten nie ausgezahlt werden

**Gemeldet:** *"defend stronghold wurde mir nicht zugerechnet, obwohl ich meine homeobjective die
ganze zeit hatte. lag es an objective secured?"*

- **An "Secured" (14.03) lag es NICHT** — `_defend_stronghold()` liest `Objective.controlled_by`,
  also 14.02s gewöhnliche Kontrolle; `secured_by` kann sie nur HALTEN, nie verhindern, und wird
  ohnehin allein von Marker Beacon gesetzt.
- **Der gefundene Fehler ist eine REIHENFOLGE in `main.py`.** Drei der siebzehn Karten werten an
  genau einem Moment — "am Ende des gegnerischen Zuges in der letzten Schlachtrunde" (Beacon,
  Burden of Trust, Defend Stronghold). Nimmt der Kartenspieler den ERSTEN Zug der Runde, IST das
  das letzte Zugende der Schlacht, und `advance_turn_phase()` rief `_check_battle_end()` in
  DEMSELBEN Durchlauf, in dem `begin_end_of_turn()` den Wertungs-PROMPT geöffnet hatte. Das
  kostete die Karte doppelt: `BattleEndOverlay.show()` FRIERT die angezeigten Zahlen ein (die VP
  fehlten also), und `_front_notice()` stellt dieses Overlay vor die Entscheidungsbox, die
  `main.py` nur zeichnet, solange `_front_notice()` None ist — der Prompt dahinter war damit auch
  nicht mehr beantwortbar.
- **Reproduziert:** Karte vollständig für 5 VP, Prompt offen, eingefrorener Endstand **0**.
- **Der Fix ist ein Tor plus ein Wiedervorlage-Punkt** (Fehlerklasse 14): `_check_battle_end()`
  hält an, solange `decision_manager.is_pending`, und wird zusätzlich EINMAL PRO FRAME gerufen,
  außerhalb der Event-Kette (Fehlerklasse 15) — also erscheint das Ergebnis den Frame nach der
  Antwort. `decision_manager` statt des Deck-eigenen Flags, weil das EINE Bedingung ist statt
  zweier, die sich widersprechen können; und alles andere, was an dieser Naht noch offen steht
  (Starflare sitzt dort), hat denselben Anspruch, vor dem Schlussstand beantwortet zu werden.
- **Die Gegenrichtung ist mitgeprüft**, sonst tauscht der Fix ein stilles Versagen gegen ein
  anderes: eine Schlacht ohne offene Frage endet unverändert im selben Aufruf.
- **Getestet:** neu `test_final_round_scoring.py` (**22/22**, vier Abschnitte) — **zu diesem
  Zusammenspiel gab es GAR KEINEN Test**: `test_secondary_missions.py` besitzt die KARTEN und
  fasst `main.py`s Reihenfolge nie an, und kein Smoke erreicht Runde 5. Die Kartenmenge ist eine
  MENGENDIFFERENZ über die Karten-OBJEKTE, nicht über `ALL_CARDS` — Burden of Trust ist gebaut und
  bewusst nicht im Stapel, eine Prüfung am Deck hätte also zwei von drei abgedeckt.
  **BENANNTE GRENZE:** Abschnitt 2 fährt `main.py`s Tor in der FORM nach, nicht dessen eigene
  Closure (`_check_battle_end()` lebt in `main()`, das keine Suite fährt) — die Verdrahtung hält
  Abschnitt 4 per AST fest, weil der Name auch in seiner eigenen `def`-Zeile und in einem Kommentar
  steht und ein Zähler auf ERWÄHNUNGEN genau die Schwäche ist, an der dieses Repo schon zweimal
  hing. **Keine Laufzeit-Sonde:** das letzte Zugende liegt fünf Runden tief, und ein
  MockAgent-Lauf schafft gemessen ~7 Phasenwechsel je 3000 Frames gegen die ~50 einer Schlacht.
- **OFFEN und beim User erfragt: die RUNDENBANDE der Karte.** Sie trägt neben dem
  Endrunden-Zeitpunkt ein `min_battle_round=2`, das unter diesem Zeitpunkt **niemals greifen
  kann**. Eine gedruckte Karte trägt keine Bande, die nie gilt — es ist also entweder die Bande
  zu viel oder der Zeitpunkt falsch, und im zweiten Fall wertet die Karte am Ende JEDES
  gegnerischen Zuges ab Runde 2, was genau die Beobachtung des Users erklärt (Home Objective die
  ganze Zeit gehalten, in den Runden 2-4 nichts bekommen). Nicht geraten, sondern der WORTLAUT
  erfragt (Fehlerklasse 13).
  - **Drei Messungen, die den offenen Punkt schärfen** (Nachtrag, nachdem der User sagte "dann war
    es aber ein anzeige Fehler, mein home objective war die ganze Zeit in meiner Farbe"):
    1. **Das BRETT hat nicht gelogen.** `renderer.draw_objectives()` färbt aus
       `objective.controlled_by` — GENAU dem Feld, das `_defend_stronghold()` liest. Farbe und
       Karte können per Konstruktion nicht auseinanderlaufen; "die ganze Zeit meine Farbe" heißt
       also, die Bedingung war die ganze Zeit erfüllt.
    2. **Die KARTE widerspricht sich auf dem Schirm.** `info_rows()` zeigt für sie
       `WHEN end of enemy turn, round 5` UND `FROM battle round 2` übereinander, und ihr
       `text` öffnet mit beiden Klauseln in einem Satz. Beacon, das denselben Zeitpunkt trägt,
       zeigt nur die WHEN-Zeile. Das ist der ANZEIGE-Fehler, den der User meint — kein
       Rendering-Fehler, sondern der sichtbar gewordene Datenwiderspruch.
    3. **Sie ist die EINZIGE der 18 Karten mit einer Rundenbande** überhaupt, und die ist inert.
    Die FROM-Zeile wird deshalb NICHT vorsorglich unterdrückt: das wäre kosmetisch und löschte
    genau das Signal, an dem der Widerspruch überhaupt aufgefallen ist.

## Der Avatar-Charge und der Home-Objective-Klumpen (2026-09-08)

**Gemeldet:** *"der große necron warrior squad hat den avatar of khaine gecharged. das sollte er
lieber nicht machen."* und *"die necrons kommen immer nicht so richtig von ihrem home objective
weg. sowohl necron warriors als auch immortals klumpen auf dem home objective und können sich von
da aus keine guten schusspositionen erarbeiten."*

**DIE ZWEI SIND DIESELBE GESCHICHTE**, und das ist der Befund, der die Arbeit zusammenhält: der
Blob war nach dem Charge zwei seiner fünf Runden im Nahkampf des Avatars festgenagelt. Gemessen an
`logs/game_20260908_204854.log`s eigenen `[move detail]`-Zeilen (Zentroide je Zug): Necron
Warriors T1 (32,4) → T2 (33,6) → nie wieder, Immortals 1 (29,9) → nie wieder, Immortals 2
(13,13) → nie wieder. **43 Modelle, zwei Zoll Boden in fünf Runden**, während jede andere Einheit
der Armee vorrückte.

### Der Charge: die taktische Schicht bekommt GAR KEINE Bewertung

- **Reproduziert an den echten Datenblättern:** der Charge auf den Avatar entfernt **7.5
  pts/Runde und 0.0 Modelle** (3 % einer Ein-Modell-Einheit), der Gegenschwung des Avatars nimmt
  **89.1 pts/Runde** — ein 12:1-Verlust. Das Log bestätigt es: **2 von 21 Modellen** kamen in
  Engagement Range, der Kampf machte **0 Wunden**.
- **Die Ursache ist eine Beobachtungslücke (Fehlerklasse 1+2), keine Modellschwäche.**
  `observation.squad_summary()` trägt ÜBERHAUPT KEINE Bewertung — Name, Modelle, Wunden, OC. Die
  `[threat]`-Zeile mit „by charging: Avatar 10.0 pts/turn (0.0 models, trading down)" geht
  ausschließlich an den PLANNER. **Das Log ist das A/B:** derselbe Spielstand, dieselbe
  Modellfamilie — der Planner, der die Zahlen bekommt, hat den Charge dreimal in Folge
  abgelehnt und wörtlich begründet („Charging the Avatar trades down badly (345 vs 250 pts)");
  die taktische Schicht, die keine bekommt, hat ihn gemacht.
- **`_charge_trade_note()` ist die Antwort, und sie steht in der Option — nicht als zweite
  Sperre.** Genau die Form, die dieselbe Funktion für die ODDS schon hat („it belongs in the
  option's own text"). Gelesen an zwei Stellen: der Deklaration und der Zielwahl.
- **EINE ZWEITE SPERRE WURDE GEMESSEN UND VERWORFEN, und das ist die tragende Entscheidung.**
  Über die zwei KI-Armeen gegen jede ausgelieferte Gegnerliste (**2070 Paarungen**) liegt der
  gemeldete Fall bei gain/loss 0.08, in den schlechtesten 1.7 % — aber die Population, von der
  er getrennt werden müsste, ist STETIG: unter den Einheiten, die die bestehende
  Shooting-Specialist-Sperre nicht ohnehin stoppt, läuft der entfernte Anteil 0.01, 0.02, 0.03
  (der gemeldete Fall), 0.04, 0.05, 0.06, 0.07, 0.08 **ohne jede Lücke**, und die
  Chaff-Charges, die eine Geschützlinie binden, liegen im selben Band wie die aussichtslosen.
  Eine Schwelle dort läge INNERHALB einer Überlappung — genau das, wofür
  `_shooting_specialist_charge_block()` eine Pro-Ziel-Ratio verworfen hat. Withholding ist die
  richtige Antwort für eine Option, die NIE genommen werden soll; diese soll manchmal.
- **Die bestehende Sperre ist unverändert und schweigt zu Recht**: Necron Warriors sind 1.1x,
  unter der 1.4-Schwelle. Sie war das falsche Werkzeug, nicht ein kaputtes.

### Der Klumpen: eine Bedrohung setzt die LATTE, sie schaltet den Pass nicht ab

- **`_uncontested_objectives()` ist zu `_held_objectives()` geworden** und liefert
  `(objective, threat_oc)` für JEDES kontrollierte Objective. Vorher nahm ein Gegner irgendwo
  innerhalb `GARRISON_THREAT_RANGE_IN` das Objective KOMPLETT aus dem Over-Garrison-Pass — im
  gemeldeten Spiel stand der Avatar ab Runde 2 etwa 12" von P2 Home, also durfte beliebig viel
  dort parken.
- **Regel 14.02 sagt selbst, wie groß eine Garnison sein muss:** Kontrolle ist die höhere
  OC-Summe, die Latte ist also die OC des Gegners und nicht seine Anwesenheit. Am gemeldeten
  Brett gemessen: **Avatar OC 5, Immortals OC 21, Necron Warriors OC 41** — die Immortals halten
  es allein, die 41 waren restlos überflüssig.
- **`_garrison_surplus()` ist die EINE Definition** von „wer wird gebraucht, wer ist übrig",
  gelesen vom Bericht an den Planner UND von der Korrektur. Die zwei hatten dieselben sechs
  Zeilen doppelt — die Form, die dieses Repo laufend konsolidiert, und sie wäre in dem Moment
  gedriftet, in dem eine der beiden Seiten von Bedrohungen erfahren hätte. **Damit fällt
  `_garrison_fitness` von drei Lesern auf zwei** (siehe die Extraktionsliste in Teil 1).
- **Der unbedrohte Fall ist per Konstruktion unverändert:** `threat_oc` ist dann 0, die OC des
  ersten Keepers übertrifft das, also bleibt genau eine Einheit stehen. Das `keepers and`-Gate
  ist, was das wahr macht statt fast wahr — ohne es hielte eine battle-shocked Einheit (OC 0,
  Regel 01.07) die Schleife am Laufen und niemand würde befreit.

### Der 0-Zoll-Freeze, und was er WIRKLICH war

- **Gemessen am kompletten gemeldeten Brett (alle 74 Modelle, wo das Log sie lässt):** der Blob,
  auf `(34,8)` befohlen — 1.97" vom Zentroid und INNERHALB der eigenen Formation —, bewegt sich
  **0.00"**; derselbe Blob auf demselben Brett auf Punkte außerhalb seiner Formation befohlen
  bewegt sich **2.50"** und **4.72"**. Nichts war blockiert: die Modelle auf der anderen Seite des
  Punktes müssten rückwärts in ihre eigenen Kameraden laufen, also kam jede Sprosse von
  `_advance_toward()`s Leiter mit nichts zurück.
  - **KORREKTUR einer eigenen Zwischenmessung:** eine frühere Zahl von 7.24" stammte von einem
    Brett, dem die Canoptek Wraiths fehlten — die stehen direkt nördlich des Blobs und kosten
    ihn den Weg. Die Zahlen oben sind die vom vollständigen Brett.
- **Der gemeldete Befehl war aber `hold`, und die Einheit hat ihn korrekt ausgeführt.** Der
  Widerspruch lag im PLAN (Rolle „hold" neben einem Fließtext, der eine Umpositionierung
  beschreibt) — dieselbe Falle wie Fehlerklasse 4, nur andersherum: hier wurde das FELD befolgt,
  und das ist die richtige Hälfte. Befreit wird die Einheit vom Garnisons-Pass, der eine Regel
  hat, die sagt, dass sie weg muss.
- **Der Wächter im Validator gilt deshalb NUR einer AKTIVEN Rolle**: ein Punkt in der eigenen
  Formation ist dort ein No-op, der die echten Optionen verdrängt (eine benannte Position
  unterdrückt Advance und Move-to-Target). Bei `hold`/`screen`/`stage` heißt derselbe Punkt
  „bleib stehen", was ein echter Befehl ist — die erste, breitere Fassung nahm prompt dem KEEPER
  seine eigene Garnisons-Koordinate weg, und `test_over_garrison.py` hat das sofort gemeldet.
- **`geometry.convex_hull()` / `point_inside_hull()` (34. Extraktion)**, am zweiten Konsumenten:
  `game/renderer.py` hatte den Hull privat (Objective-Umrisse) und kann von `ai/` nicht
  importiert werden (pygame, Renderpfad). Der Renderer RE-EXPORTIERT ihn unter dem alten privaten
  Namen, also ist jeder Pixel-Test der Objective-Umrisse per Konstruktion unverändert.

### Was NICHT angefasst wurde, und warum

Die dritte Ursache des Klumpens ist die dokumentierte Bewegungsgrenze großer Trupps
(`measure_crowded_movement.py`: 15+ Modelle realisieren ~20 % ihres erreichbaren Zuges) — ein
echter 16"-Vormarsch des Blobs kommt auf 54 %. Auf User-Entscheidung bewusst ausgelassen; CLAUDE.md
führt dort vier gemessene und wieder ausgebaute „Verbesserungen".

### Getestet

Neu `test_report_20260908.py` (**48/48**, acht Abschnitte) plus `ab_report_20260908.py`
(**13 A/B-Sonden, alle beißend, keine stürzt ab**). `test_over_garrison.py` 71 → **77/77**
(Abschnitt 6 stellt jetzt die NEUE Regel fest und misst die Latte in beide Richtungen — eine
größere Bedrohung hält eine zweite Einheit dort), `test_home_garrison.py` **86/86**.
- **Zwei Befunde über den TEST, beide von den Sonden:** der `_garrison_fitness`-Zähler war
  `src.count(...) - 1` und blieb durch genau diese Änderung grün, weil eine Erwähnung im
  DOCSTRING den weggefallenen Leser ersetzte (die „ein Wächter matcht seine eigene Erklärung"-
  Falle, fünfte Instanz) — er zählt jetzt per AST echte AUFRUFE; und drei Sonden ließen ihre
  Suite mit `KeyError` ABSTÜRZEN statt sie rot zu machen (Nachschlagen mit `[...]` auf ein Dict,
  das in der Vor-Fix-Welt den Schlüssel nicht hat) — **achtzehnte Instanz** derselben Lehre,
  jetzt `.get()`.
- Volle Regression **196 Suiten, ~17339 Prüfungen, 195 grün / 0 rot / 1 bekannt**,
  `run_tests.py --smoke` komplett grün (alle neun schweren Skripte).

### Im ECHTEN Spiel belegt

`verify_charge_trade_and_garrison.py` fährt `selfplay.py`s echte `main()`-Schleife mit der
gemeldeten Paarung (Aeldari gegen Necrons):

| | gefixt | `--neutralize` |
|---|---|---|
| Charge-Optionen mit dem Handel | **4 von 4** | **0 von 6** |
| Garnison: Einheiten befreit / behalten | **1 / 1** (threat OC 5) | **0 / 2** |

Die Optionstexte zeigen die Unterscheidung, um die es geht:
`it would remove about 6.7 of its models (101 pts/turn) ... 11 pts/turn back` gegen
`about 0.1 of its models (12 pts/turn) ... 78 pts/turn back`. `--neutralize` liefert dafür
`charge 1 Guardian Defenders 1 ...` und `charge 1 Wraithguard 1` — zwei nackte Namen.
**GESTELLT wird je eine Tatsache pro Hälfte, beide im Modulkopf benannt:** dass die KI überhaupt
in ihrer Charge-Phase neben etwas steht, und die Plan-FORM (MockAgents `plan_turn()` gibt jeder
Einheit „advance" ohne Koordinate, also findet `_planned_garrisons()` nie eine Garnison und der
Pass kann von selbst nicht feuern). Die Bedrohung wird ebenfalls gestellt — ohne sie ist das
Objective unbedroht, beide Welten befreien den Überschuss, und die Sonde misst nichts.
