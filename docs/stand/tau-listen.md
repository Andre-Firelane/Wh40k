# Die T'au-Listen

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die T'au-Liste (2026-09-05)

**Der vom User gelieferte Roster ersetzt die 2026-08-30-Liste vollständig.** 21 Listeneinträge,
**18 Einheiten** nach drei Anbindungen, **76 Modelle**, Engine-Summe **2165 pts** — die Zahl, die
die Liste selbst druckt.

- **SECHS ENHANCEMENTS, und das ist die eigentliche Neuerung.** Bis hierher hat KEINE Liste dieses
  Projekts eines gekauft; der Mechanismus war gebaut, verdrahtet und wurde ausschließlich mit einer
  eigenen Testtabelle gefahren. Jetzt trägt ihn ein Roster:

  | Kauyon | Advanced Acquisition Cadre |
  |---|---|
  | Through Unity, Devastation (30) → Fireblade 1 | Negation Emitters (15) → Stealth Battlesuits 1 |
  | Precision of the Patient Hunter (15) → Fireblade 2 | Unmasking Suite (15) → Ghostkeel |
  | Exemplar of the Kauyon (20) → Commander in Coldstar | |
  | Solid-image Projection Unit (20) → Ethereal | |

- **Die Enhancement-Vergabe musste umgebaut werden, und der Grund ist eine echte Grenze der alten
  Form.** `_TAU_LIST_ENHANCEMENTS` war `{Detachment: (Name, Träger-Datenblatt)}` — EIN Enhancement
  je Detachment, Träger per Datenblatt gesucht. Diese Liste ist damit nicht ausdrückbar: **ZWEI
  Cadre Fireblades nehmen VERSCHIEDENE Enhancements**, und von **zwei identischen Stealth-Teams**
  nimmt nur EINES eines. Eine Datenblatt-Suche findet jeweils das erste und gäbe still dem
  falschen. Die Vergabe passiert deshalb jetzt **am BAUORT** — der einzigen Stelle, die zwei
  gleiche Squads auseinanderhalten kann. `_grant_tau_enhancement()` lehnt einen Namen ab, den die
  Tabelle nicht nennt: die Tabelle IST die aufgeschriebene Liste, und ein Grant daneben ließe
  Roster und Protokoll (samt Punkten) auseinanderlaufen.
- **DREI Anbindungen (19.01), und zwei davon entscheidet der GEDRUCKTE TEXT, nicht eine Vorliebe:**

      Cadre Fireblade 1 (Through Unity, Devastation)   -> Breacher Team 1
      Cadre Fireblade 2 (Precision of the Patient Hunter) -> Breacher Team 2
      Commander in Coldstar (Exemplar of the Kauyon)   -> Crisis Sunforge Battlesuits

  Exemplar of the Kauyon und Through Unity öffnen beide mit **"while the bearer is leading a
  unit"** — ein allein stehender Träger gibt seine Punkte für nichts aus. Die dritte Anbindung ist
  neu und war vorher gar nicht möglich: **diese Liste fieldet zum ersten Mal eine Crisis-Einheit**,
  und die steht auf der LEADER-Zeile des Coldstar. Die zwei Fireblades setzen die eigene Vorgabe
  des Users fort ("die Fireblades in die Breacher"). **Der Ethereal steht weiter allein** ("der
  ethereal ist solo") — sein Solid-image Projection Unit ist ein armeeweiter Redeploy und braucht
  keine geführte Einheit, es zieht also nichts in die andere Richtung.
- **PUNKTE: alle 21 Einträge stimmen — der erste Roster hier, bei dem NICHTS abweicht.** Die
  Transkription gewinnt weiterhin, sie muss hier nur nirgends. Der Vorgänger wich in zehn
  Einträgen ab; mehrere dieser Datenblätter sind schlicht nicht mehr dabei (The Twin Lance,
  Shadowsun, das zweite Pathfinder Team, die zweite Piranha), und die zwei, die geblieben sind,
  stimmen in ihrer neuen Größe: Devilfish 75 (die alte Liste sagte 85) und Kroot Hounds 45.

### Die ZWEITE T'au-Liste: Mont'ka — ERSETZT am 2026-09-06

**Der User hat den Roster durch einen App-Export ausgetauscht** ("Tau - RC 1k", 1975 pts).
18 Einträge, **14 Einheiten nach vier Anbindungen**, 69 Modelle, **1975 pts** — alle achtzehn
Zeilen stimmen mit der Transkription überein.

Was hier vorher stand, war die Geschichte der ERSTEN Fassung ("fast gleich nur montka und andere
enhancements", 21 Einträge, 2150 pts, geteilter Builder). Der Teil davon, der Bestand hat, steht
unten; der Rest ist ersetzt statt angehängt.

- **SIE IST AUS DEM GETEILTEN BUILDER AUSGEZOGEN, und das ist die strukturelle Änderung.**
  `_build_tau_roster()` existierte, weil die Liste WÖRTLICH der Kauyon-Roster mit einer anderen
  Enhancement-Tabelle war. Die neue Fassung behält Breacher, Devilfish, Fireblades, Broadsides,
  Pathfinder, Riptide und die zwei Stealth-Teams — und lässt Ghostkeel, Hammerhead, Sky Ray,
  Piranha, Kroot Hounds, Vespid und den Ethereal fallen, während Farsight, Darkstrider, The Twin
  Lance und beide Crisis-Einheiten dazukommen. **14 von 21 gemeinsamen Einträgen sind kein
  geteilter Roster**, also hat sie jetzt einen eigenen Builder und `_build_tau_roster()` ist von
  drei Aufrufern auf zwei (Kauyon und Prototypes).
  - **Der Quell-Wächter dafür liest jetzt den AST statt eines Teilstrings.** Die alte Zeile zählte
    `_build_tau_roster(` im Text und kam auf **4**, weil drei Docstrings die Funktion beim Namen
    besprechen — sie beantwortete also „wie oft wird sie ERWÄHNT" statt „wer RUFT sie". Dieselbe
    Guard-matcht-seine-eigene-Erklärung-Falle, die dieses Repo schon zweimal notiert hat. Jetzt
    steht dort die MENGE der aufrufenden Funktionen (`build_tau`, `build_tau_epc`), also die
    eigentliche Behauptung.
- **VIER ANBINDUNGEN, aus ZWEI Quellen — die einzige Stelle, an der diese Liste keine reine
  Transkription ist:**

      Commander Farsight (Warlord)  -> Crisis Sunforge Battlesuits   (Export)
      Commander in Coldstar         -> Crisis Starscythe Battlesuits (Export)
      Cadre Fireblade 1             -> Breacher Team 1               (User)
      Cadre Fireblade 2             -> Breacher Team 2               (User)

  Die ersten zwei nennt zum ersten Mal die QUELLE selbst: der Export druckt eine eigene Überschrift
  „Attached Units" mit der Rolle jedes Modells, statt sie einem Satz des Users zu überlassen.
- **DIE ZWEI FIREBLADES SIND EINE ENTSCHEIDUNG GEGEN DEN EXPORT** (User, 2026-09-06: "bei der Tau
  Montka liste sollen die fireblades die breacher anführen"). Der Export druckt beide unter
  CHARACTERS und preist seine Breacher Teams mit der ungeführten 90 — das ist also ein bewusstes
  Übersteuern, keine Transkription. **Es kostet nichts:** `attach()` summiert die Komponenten, die
  Armeesumme bleibt dieselben 1975, nur die Einheitenzahl bewegt sich (16 → 14). Damit ist auch
  wiederhergestellt, was der Vorgänger-Roster tat (User damals: "die Fireblades in die Breacher").
  - **Genau deshalb sind die PAARUNGEN gepinnt und nicht die Summe:** eine Anbindung, die nichts
    kostet, ist für jede Punkteprüfung unsichtbar.
- **DARKSTRIDER STEHT WEITER ALLEIN**, und er ist der einzige Charakter, der es tut. Seine eigene
  LEADER-Zeile nennt das Pathfinder Team, eine Anbindung wäre also legal — der Export stellt ihn
  unter CHARACTERS, und dazu ist nichts gesagt worden. Als Listen- und nicht als Regelentscheidung
  gepinnt.
- **EIN Enhancement statt vier: Strategic Conqueror auf dem Coldstar** (95 + 15 = die 110 des
  Exports). Jeder andere Charakter steht auf seinem Grundpreis, was die Liste sagen lässt, dass
  sie nichts weiter kauft.
  - **DREI VON MONT'KAS VIER ENHANCEMENTS VERLIEREN IHREN EINZIGEN TRÄGER** — Coordinated
    Exploitation, Exemplar of the Mont'ka und Strike Swiftly sind gebaut, verdrahtet und getestet,
    und ab hier fieldet sie keine ausgelieferte Liste. Derselbe „dormant by construction"-Zustand,
    in dem das Experimental-Prototype-Cadre-Trio war, bevor eine Liste seine Waffen kaufte.
    Benannt und gepinnt, statt zum Wiederentdecken liegen zu lassen. Die frühere Zeile hier
    („Strike Swiftly wirkt wirklich") gilt entsprechend nicht mehr.
  - Der Träger ist am MODELL gepinnt, nicht an der Einheit: nach 19.01 hält sein Trupp vier
    Modelle, und „die Einheit trägt es" bestünde auch mit dem Enhancement auf einem
    Starscythe-Suit.
- **EIN DATENBLATT MUSSTE NACHZIEHEN, und der Fehler war ein Kommentar ohne Code.** Der Pathfinder
  Shas'ui trägt in diesem Export den Semi-automatic Grenade Launcher; die Option war nur auf der
  Mannschaftszeile verdrahtet, **während der Kommentar darüber wörtlich „Offered on BOTH model
  lines" behauptete** und sogar eine Armeeliste zitierte, die genau das kauft. Der gedruckte Text
  sagt „1 MODEL IN THIS UNIT equipped with a pulse carbine", und der Shas'ui trägt eine.
  - **Die Fehlerform ist die gefährliche:** `build_squad()` verwirft einen `choices`-Eintrag, der
    ein (Zeile, Option)-Paar nennt, das das Datenblatt nicht hat — **still**. Die Einheit kommt
    eine Waffe zu kurz und mit korrektem Preis heraus, also überlebt sie jede Punkteprüfung und
    jeden Blick auf die Summe.
  - **BENANNTE GRENZE:** `max_models` gilt PRO ZEILE, die zwei Einträge zusammen erlauben also
    ZWEI Werfer, wo der Text einen erlaubt — dieselbe schon dokumentierte Schwäche von
    `WargearOption`, die keinen zeilenübergreifenden Deckel ausdrücken kann.
- **Die Pathfinder nehmen ION RIFLES statt Rail Rifles**, und das ist der Unterschied zwischen 85
  und den gedruckten 100: beide ersetzen die Pulse Carbine auf drei Modellen, aber Rail Rifles sind
  gratis und Ion Rifles kosten 5 je Stück.
- **Die DROHNEN sind eine eigene Prüfung, weil sonst NICHTS sie fangen kann:** jede ist gratis, ein
  falsches Modell bewegt also weder den Einheitenpreis noch die Armeesumme noch die Waffenzahl.
  Drei haben sich gegenüber der Vorgängerfassung bewegt (Breacher-Shas'ui Gun → Shield, Coldstar
  Marker+Shield → zwei Shields, zweiter Fireblade nackt → zwei Gun Drones), und **eine A/B-Sonde,
  die eine davon zurückdrehte, war SILENT**, bis der Test die Drohnen Modell für Modell pinnte —
  ein Befund über den TEST, wie er im Buche steht.
- **Die FORCE DISPOSITION ist unverändert und weiter abgeleitet, nicht gewählt:** Mont'ka erlaubt
  genau Priority Assets, also spielt die Liste **Secure Asset**. 3 DP allein füllen das Budget.
- **Jede Breacher-Einheit fährt mit ihrem Fireblade in ihrem EIGENEN Devilfish** (11 von 12
  Plätzen). Der Export nennt zwei DEDICATED TRANSPORTS und sagt nicht, wer darin sitzt — dieselbe
  Lücke wie bei jedem früheren Roster; die Breacher sind weiter die einzige Einheit, deren
  10"-Pulse-Blaster ohne Transport unbrauchbar ist. Die Zuordnung wird über den ECHTEN
  `register`-Callback geprüft, weil `preview_squads()` das Ziel wegwirft.
- **DER WARLORD ist Farsight, und nichts liest das** — dieselbe belegte No-op wie Supreme Commander
  und „cannot be your WARLORD". Aufgeschrieben, weil der Export es sagt.
- **Getestet:** `test_tau_enhancements.py` 308 → **333/333** (Abschnitt 9b vollständig neu
  geschrieben) plus neu `ab_montka_roster.py` (**10 A/B-Sonden, alle beißend**; „zurück auf den
  geteilten Builder" kippt 14 Prüfungen, „die Fireblades führen die Breacher nicht mehr" fünf). Volle Regression **184 Suiten, ~16236 Prüfungen, 183 grün
  / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett grün.
- **Im ECHTEN Spiel belegt:** `selfplay.py map2` mit `tau_montka` auf BEIDEN Seiten protokolliert
  `[primary] Player 1 plays Secure Asset (Force Disposition: Priority Assets)`, alle VIER
  Anbindungen als `is one attached unit (19.01)` — inklusive
  `1 Breacher Team 1 + Cadre Fireblade` — und `Commander in Coldstar Battlesuit in 1 Crisis Starscythe
  Battlesuits 1 + Commander in Coldstar Battlesuit carries the Strategic Conqueror Enhancement
  (15 pts).`
- **BENANNT, nicht mitgeändert:** die KI stellt die Breacher zu Fuß auf, statt den Transport-Hinweis
  zu befolgen — ihr Declare-Battle-Formations-Schritt entscheidet Transporte selbst
  (`TRANSPORT_PASSENGER_PRIORITY`). **Vorbestehend und nicht dieser Änderung zuzuordnen**: die
  Kauyon-Liste verhält sich im selben Lauf identisch. Der Hinweis gilt dem MENSCHEN.

**Was von der ersten Fassung Bestand hat:** mit ihr wurde der ZWEI-STUFEN-SCREEN zum ersten Mal
echt. Der „erst das Volk, dann die Liste"-Fluss wurde für „ich habe vor pro Volk mehrere listen
anzulegen" gebaut und hatte bis dahin nur eine KÜNSTLICHE Registry (`multi_list_faction()`) zum
Gruppieren; der Helfer bleibt für das, was ein echtes Paar nicht erreicht (der Pager braucht mehr
Kacheln als eine Seite trägt).

### Die DRITTE T'au-Liste: Prototypes (2026-09-05) — ZURÜCKGEZOGEN 2026-09-07

**Diese Liste gibt es nicht mehr** (User: "diese liste kann weg"). Was mit ihr ging, steht im
T'au-Listenblock weiter oben: Death Trap ist wieder dormant, Supernova Launcher und Admired Leader
haben keinen Träger mehr.

**Der Abschnitt bleibt wegen EINER Erkenntnis stehen, und die ist über die Arbeitsweise, nicht über
die Liste:** ein Enhancement kann vollständig verdrahtet und trotzdem unerreichbar sein, wenn kein
Roster seine Vorbedingung erfüllt.

Hier stand außerdem, die drei Coldstar-Waffenersetzungen gäbe es, "weil diese Liste sie gekauft
hat". **Das war falsch herum und ist korrigiert** (User: "wieso existiert etwas, weil eine liste es
benutzt?"). Ein Datenblatt ist eine TRANSKRIPTION des gedruckten GW-Blatts; welche Optionen eine
Liste kauft, hat mit der Frage, welche EXISTIEREN, nichts zu tun. Die drei existieren, weil sie
gedruckt sind — die Liste hat nur aufgedeckt, dass sie fehlten. Gemessen: **3 von 18 T'au-
Datenblättern mit Wargear-Menü kannten weniger Optionen, als gedruckt sind.** Der Cadre Fireblade
war der reine Fall (drei gedruckte Drohnen, eine modelliert, mit "since only Gun Drone was ever
asked for on this model" als Begründung im Quelltext) und ist behoben; die anderen zwei sind
Coldstar und Enforcer, denen in Menü 1 die drei Support-Systeme fehlen — und das ist eine echte
strukturelle Grenze, keine Nachlässigkeit: eine `WargearOption` tauscht Waffen gegen Waffen und
kann kein Profil-Flag setzen.

**Auxiliary Cadre + Experimental Prototype Cadre, 2310 pts** (User: "danach diese zusätzliche
Liste die 2 weiteren coldstars sind solo"). 23 Einträge, 20 Einheiten, 78 Modelle — derselbe Kern
wie die anderen zwei plus **zwei weitere Commanders in Coldstar Battlesuit**.

- **SIE MACHT EXPERIMENTAL PROTOTYPE CADRE ÜBERHAUPT ERST ERREICHBAR.** CLAUDE.md hielt hier fest:
  *"Experimental Prototype Cadre bekäme NICHTS ... alle drei seiner Enhancements verbessern eine
  benannte Waffe, und kein Modell dieser Liste trägt T'au Flamer, Plasma Rifle oder Airbursting
  Fragmentation Projector."* Diese Liste rüstet genau die drei aus, einen je Commander — die
  Enhancements waren also **per Konstruktion dormant**, und der Grund war der Roster, nicht die
  Verdrahtung. **Gemessen, dass sie wirklich greifen:** Plasma Rifle S8/AP-3/D3 → **S10/AP-4/D4**,
  T'au Flamer S4/AP0/D1 → **S6/AP-1/D2**, Airbursting S3/AP0/D1 → **S6/AP-1/D2**.
- **DEATH TRAP wird zum ersten Mal von einem ausgelieferten Roster GESPIELT.** Die Primary-Mission-
  Karte war gebaut, getestet und dormant; `test_force_dispositions.py`s Pin ("...leaving these two
  dormant") ist genau dafür rot geworden. Es blieb eine dormant — Unstoppable Force, bis die
  VIERTE Liste sie eine Stunde später auch noch holte.
  Die Disposition ist hier eine WAHL — Auxiliary Cadre gewährt Disruption, Experimental Prototype
  Cadre Priority Assets, und die Liste deklariert Disruption.
- **Sie ist die erste Liste, die das DP-Budget NICHT ausschöpft:** 1 + 1 von 3. Das Budget ist eine
  Obergrenze, keine Zielmarke — bis hierher hat jede Liste zufällig genau 3 ausgegeben.
- **Der Builder trägt jetzt eine COMMANDER-TABELLE** statt eines einzelnen Commanders:
  `(Slot, Waffenwahl, führt-die-Sunforge)` je Eintrag. Die zwei Listen mit einem Commander
  bekommen sie als Default, lesen sich also unverändert. Der ERSTE führt die Crisis Sunforge, die
  anderen stehen allein (User-Vorgabe) — und nichts zieht dagegen: alle drei EPC-Enhancements
  wirken auf die eigene Waffe des Trägers, brauchen also keine geführte Einheit.
- **Beide Fireblades nehmen NICHTS**, und das ist die Liste: beide stehen zum Grundpreis 50. Keines
  der zwei Detachments hat ein Enhancement, das ein Fireblade tragen könnte — Admired Leader geht
  auf den Ethereal, die anderen drei sind BATTLESUIT-only.
- **Drei neue Waffenoptionen am Coldstar-Datenblatt** (Plasma Rifle, T'au Flamer, Airbursting
  Fragmentation Projector als Ersatz der High-output Burst Cannon). Alle drei stehen im gedruckten
  Menü; sie fehlten, weil sie bis hierher niemand gekauft hat.
- **Getestet:** `test_tau_enhancements.py` 267 → **283/283** (neuer Abschnitt 9c: die drei
  Commander mit ihren drei Waffen, dass die Upgrades die Waffen wirklich erreichen, die zwei
  allein stehenden, und die Punkte als Gleichung gegen die anderen Listen);
  `test_force_dispositions.py` **151/151** (vier von fünf Missionen erreicht, Death Trap namentlich
  der Prototypes-Liste zugeordnet); `test_army_select.py` **349/349** (drei T'au-Listen im
  Zwei-Stufen-Screen). Volle Regression **184 Suiten, ~16082 Prüfungen, 183 grün / 0 rot /
  1 bekannt**, `smoke_setup_screens.py` und `smoke_pregame.py map2`.
- **Im ECHTEN Spiel belegt:** `selfplay.py map2` mit `tau_epc` auf beiden Seiten protokolliert
  `[primary] Player 1 plays Death Trap (Force Disposition: Disruption)` und alle vier
  Enhancements auf ihren Trägern.

### Die VIERTE T'au-Liste: Retaliation Cadre (2026-09-05)

**Retaliation Cadre allein, 3 DP, 1965 pts** (User: "jetzt noch retaliation cadre Liste
zusätzlich"). 16 Einträge, **12 Einheiten nach vier Anbindungen**, 57 Modelle — und **die einzige T'au-Liste, die den Kern
der anderen drei NICHT teilt**: keine Breacher Teams, keine Devilfish, kein Ethereal, keine
Fireblades. Ein Battlesuit-Heer aus fünf Charakteren und sechs Crisis-Einheiten, also mit eigenem
Builder statt einer Tabelle für den geteilten.

- **UNSTOPPABLE FORCE wird damit gespielt** — die LETZTE der fünf Primary Missions, die kein
  ausgeliefertes Roster je erreicht hatte. Zusammen mit der Prototypes-Liste (Death Trap) ist die
  dormant-Spalte damit **leer**; `test_force_dispositions.py` pinnt jetzt "keine dormant" statt
  einer Namensliste.
- **VIER ANBINDUNGEN (19.01), alle vier vom User benannt** (nachgereicht: "die charactere sind
  keinen squads zugeordnet. ich dachte das wäre im text schon enthalten ... Farsight in die Flamer
  Starsythe / Burst Cannon Coldstar in die Burst Cannon Starsysthe / Missile Pod Enforcer in die
  Fireknife / Fusion Enforcer in die Sunforge"). Hier stand vorher das Gegenteil ("NICHTS ist
  angebunden ... die Liste sagt es nicht"), und der Eintrag ist die Korrektur wert: die
  Anbindungen standen im gelieferten Listentext, sie sind beim Transkribieren untergegangen.

      Commander Farsight             -> Crisis Starscythe 1 (sechs T'au Flamer)
      Commander in Coldstar          -> Crisis Starscythe 2 (sechs Burst Cannons)
      Commander in Enforcer (Pods)   -> Crisis Fireknife
      Commander in Enforcer (Fusion) -> Crisis Sunforge

  - **Die Regeln entscheiden hier GAR NICHTS** — alle drei Commander-Datenblätter nennen auf
    ihrer LEADER-Zeile alle drei Crisis-Datenblätter, jede der zwölf Paarungen wäre also legal.
    Welche zu welcher gehört, ist reine LISTEN-Tatsache; genau deshalb wäre Raten hier still
    gewesen, statt an `can_attach()` zu scheitern.
  - **Namen können die Paarung nicht prüfen, WAFFEN schon.** Die zwei Starscythe sind DASSELBE
    Datenblatt und die zwei Enforcer ebenso — ein vertauschter Leader ergibt identische
    Einheitennamen, identische Modellzahlen und dieselbe Armeesumme. Der User hat sie deshalb
    selbst nach ihren Waffen benannt, und der Test pinnt sie genauso (A/B belegt: die zwei
    Vertauschungen kippen 2 bzw. 3 Prüfungen, ohne dass sich sonst eine Zahl bewegt).
  - **Der Enhancement-SLOT reitet jetzt in der Leader-Spezifikation** statt "der erste gebaute
    Enforcer" zu sein. Die alte Form beantwortete "welcher der zwei" über die Baureihenfolge, und
    genau die hat sich mit den Anbindungen bewegt. Starflare Ignition System sitzt am
    MISSILE-POD-Enforcer, also in der Fireknife-Einheit — im Test am MODELL gepinnt, nicht an der
    Einheit: nach 19.01 hält der Trupp vier Modelle, und "die Einheit trägt es" bestünde auch mit
    dem Enhancement auf einem Fireknife-Suit.
  - **THE TWIN LANCE steht als einziger Charakter weiter allein, und das ist sein Datenblatt** —
    es druckt gar keine LEADER-Zeile (`tau_empire_points.py` gibt ihm kein `leads`), also lehnt
    `can_attach()` jede Paarung ab. Gepinnt, damit es nicht wie eine fünfte vergessene Anbindung
    aussieht.
- **Der Coldstar BEHÄLT hier seine High-output Burst Cannon** und füllt beide Slots (zwei Burst
  Cannons plus ein Cyclic Ion Blaster) — die anderen drei Listen ersetzen diese Waffe. Beide
  Slot-Optionen gab es längst; sie hatte nur nie jemand gekauft. **Das ist zugleich, was ihn als
  "Burst Cannon Coldstar" identifizierbar macht.**

#### Drei Punkte-Korrekturen, alle von dieser Liste aufgedeckt

1. **Crisis Starscythe stand auf 90/100, gedruckt sind 100/110.**
2. **The Twin Lance stand auf 220, gedruckt sind 230.** Korpus und Liste sagen dasselbe, es gibt
   hier also nichts abzuwägen — anders als bei den Abweichungen, die dieses Repo bewusst stehen
   lässt (dort widerspricht die Liste der Transkription; hier war die Transkription falsch).
3. **Ein "per <Waffe>"-Preis wird PRO WAFFE IM GEBAUTEN TRUPP berechnet, nicht pro Tausch.** Das
   kehrt eine dokumentierte Entscheidung um, und die Evidenz ist diese Liste selbst: sie preist
   **dasselbe Starscythe-Datenblatt zweimal — 130 mit sechs T'au Flamern und 100 mit keinem.**
   100 + 6×5 passt, "pro Tausch" nicht. Damit steht auch fest, was die gedruckte Basiszahl IST:
   der Trupp OHNE die bepreiste Waffe, nicht der gedruckte Default (der drei trägt und deshalb
   115 kostet).
   - `points.py`s alte Begründung nannte genau diesen Fall und schloss aus "sonst würde der
     gedruckte Default mehr kosten als die gedruckte Einheit" auf "nur der ZWEITE Flamer zählt".
     Die Prämisse war, dass die gedruckte Zahl der Preis des Defaults ist. Sie ist es nicht.
   - **`UnitPoints.per_weapon` ist der zweite Topf neben `wargear`**, und die zwei sind bewusst
     getrennt benannt: auf der Seite sehen "per Cyclic Ion Raker 15" und "per T'au flamer 5" gleich
     aus, und sie bedeuten nur dasselbe, solange der Default die Waffe nicht trägt.
   - **Gemessen über alle fünf Fraktionen: GENAU ZWEI Datenblätter sind betroffen** (Crisis
     Fireknife und Crisis Starscythe) — für jeden anderen bepreisten Eintrag trägt der Default
     keine, dort sind die zwei Lesarten identisch. Beide ziehen ihren Preis nach `per_weapon` um
     und geben ihn an ihren Optionen ab, sonst zählte er doppelt.
- **Getestet:** `test_tau_enhancements.py` 283 → **308/308** (Abschnitt 9d: die vier Paarungen an
  ihren WAFFEN statt an ihren Namen, der Enhancement-Träger am MODELL, der Alleinstand des Twin
  Lance an seinem fehlenden `leads`, die drei Korrekturen gegen den KORPUS statt gegen Literale,
  und die Zwei-Punkte-Messung an den zwei Starscythe-Einheiten — die einzige Form, in der die
  per-Waffe-Frage überhaupt eine Antwort hat; sie liest jetzt die BODYGUARD-KOMPONENTE, weil beide
  Trupps einen 80-Punkte-Commander tragen und `Squad.points` die Summe ist).
  `test_tau_walkers.py` **79/79** und
  `test_twin_lance.py` **66/66** nachgezogen — ihre Pins hielten die alten Zahlen fest, was genau
  ihre Aufgabe war. `test_force_dispositions.py` **154/154**, `test_army_select.py` **352/352**.
  Neu `ab_retaliation_attachments.py` (**5 A/B-Sonden, alle beißend**; die gemeldete Welt — jeder
  Charakter gebaut, keiner angebunden — kippt 8 von 308). **Zwei Sonden ließen die Suite zuerst
  ABSTÜRZEN statt rot zu werden** (Indizieren in ein Paarungs-Dict bzw. in eine leere
  Bewertungsliste) — **sechzehnte und siebzehnte Instanz** derselben Lehre; beide degradieren jetzt.
  Volle Regression **184 Suiten, ~16145 Prüfungen, 183 grün / 0 rot / 1 bekannt**,
  `run_tests.py --smoke` komplett grün.
- **Im ECHTEN Spiel belegt:** `selfplay.py map2` mit `tau_retaliation` auf BEIDEN Seiten meldet
  `[primary] Player 1 plays Unstoppable Force (Force Disposition: Purge the Foe)`, alle **vier**
  Anbindungen als `is one attached unit (19.01)` für jeden Spieler, das Enhancement auf
  `Commander in Enforcer Battlesuit in 1 Crisis Fireknife Battlesuits 1 + Commander in Enforcer
  Battlesuit`, und alle vier gemergten Einheiten werden aufgestellt (je 4 Modelle). Keine
  Formalie: eine Anbindung fasst Aufstellung, Kohärenz und Zielwahl an.

### Was der Roster an der Engine geändert hat

- **Der Commander in Coldstar konnte keine vier Fusion Blaster tragen.** Sein gedrucktes Menü ist
  EIN Ersatz der High-output Burst Cannon plus **bis zu DREI** Zusätze aus derselben Liste, und der
  Fusion Blaster trägt kein "keine Duplikate"-Sternchen — 1 + 3 ist also ein legaler Build. Die
  Engine hatte nur `+ 2x Burst Cannon` und `+ Cyclic Ion Blaster`. Neu:
  `COLDSTAR_BURST_TO_FUSION` und `COLDSTAR_ADD_3X_FUSION_BLASTER`, beide gratis wie ihre zwei
  Nachbarn (nichts davon steht im Wargear-Dict der offiziellen Punkteliste).
- **Der Pathfinder-Granatwerfer war als TAUSCH modelliert und ist gedruckt ein ZUSATZ.** Der Text
  lautet *"1 model in this unit equipped with a pulse carbine can be equipped with 1
  semi-automatic grenade launcher. That model's pulse carbine cannot be replaced."* Die Engine
  hatte zwei Tausch-Optionen (max 2 auf der Mannschaft plus 1 auf dem Shas'ui) — das kostete den
  Träger eine Carbine, die er behält, und erlaubte drei Werfer, wo der Text einen erlaubt.
  **Gefunden beim Transkribieren der Liste**, deren Pathfinder Team `6x Pulse carbine ... 1x
  Semi-automatic grenade launcher` über NEUN Modelle druckt — zehn Waffen für neun Körper, was nur
  aufgeht, wenn der Werfer neben einer Carbine getragen wird.
  - **Die Liste adressiert die Optionen per MODELL-INDEX**, nicht per Anzahl: eine reine Ergänzung
    startet bei Modell 0, und dort landen auch die Rail Rifles — ein schlichter Zähler gäbe den
    Werfer also genau dem Modell, dem gerade die Carbine weggetauscht wurde. Genau dafür kennt
    `build_squad()` die Indexform.
- **Der Ghostkeel brauchte NICHTS.** Die Liste kauft ein "Battlesuit Support System"; das
  Datenblatt setzt `battlesuit_support_system` bereits bedingungslos, der Kauf ändert also nichts.
  Benannt statt als Gear modelliert, das ein No-op wäre.

**Getestet:** `test_tau_army.py` neu geschrieben (**109/109**, sieben Abschnitte) — jeder
Listeneintrag Modell für Modell und Waffe für Waffe, die drei Anbindungen mit ihrem jeweiligen
Grund, die sechs Enhancements auf ihren Trägern (inklusive der zwei Fälle, die eine
Datenblatt-Suche falsch beantwortet), und die Totals **beim ECHTEN Builder erfragt** statt von
Hand nachgebaut — dieselbe Falle, die diese Datei schon einmal getroffen hat (sie war grün gegen
einen ersetzten Roster). `test_tau_enhancements.py` Abschnitt 9 fährt jetzt die ECHTE Liste statt
einer eigenen Tabelle (**256/256**) — der Grund für die Tabelle war "die Liste vergibt nichts", und
das stimmt nicht mehr. Vier fremde Suiten zu Recht rot und nachgezogen: `test_army_select.py`
(Kachelzahlen 18/76/2165), `test_detachments.py` (Enhancement-Punkte im Preview),
`test_take_to_the_skies_policy.py` (12 → 14 Keeps; **die Crisis-Suits sind zurück**, wofür der Pin
gesetzt war) und `test_pathfinders.py` (der Werfer ist ein Zusatz). Volle Regression **184 Suiten,
~16032 Prüfungen, 183 grün / 0 rot / 1 bekannt**, `smoke_pregame.py map2`,
`smoke_setup_screens.py` und `selfplay.py map2` mit T'au auf BEIDEN Seiten.
**Im ECHTEN Spiel belegt:** das Log nennt alle sechs Enhancements auf ihren Einheiten, u. a.
`Cadre Fireblade in 1 Breacher Team 1 + Cadre Fireblade carries the Through Unity, Devastation
Enhancement (30 pts).`
