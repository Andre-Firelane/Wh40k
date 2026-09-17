# Aeldari: Datenblatt- und Detachment-Nachzug

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die restlichen Aeldari-Datenblätter (27 Stück, sieben Etappen)

**Aeldari geht von 27 auf 54 Datenblätter** (User: "ziel restliche aeldari datasheets holen,
abspeichern und einbauen. in etappen / keine ki pfade nötig / keine legends / keine titanischen";
Aircraft, Harlequins und die Ynnari-Drukhari-Einträge auf Nachfrage ebenfalls ausgeschlossen).
Damit ist die Fraktion die zweite nach T'au, deren engine-native Abdeckung vollständig ist.

**Der Umfang ist GEMESSEN, nicht geschätzt.** Aus `rules/.cache/aeldari.html`: 99 Datenblöcke,
minus 27 gebaute, 23 Legends (`sLegendary`), 2 Forge World (`FW_logo2`), 2 TITANIC
(`tooltip_contentTitanic` in der Keyword-Leiste), 2 Aircraft, 8 Harlequins, 8 Ynnari-Drukhari
= **27**. **Stonesinger und D-cannon Platform sind NICHT titanisch** — eine naive Textsuche meldet
sie, weil ihr REGELTEXT "excluding TITANIC units" enthält. Das Keyword steht nur bei den zwei
Wraithknights wirklich in der Leiste.

| Etappe | Einheiten | Warum zusammen |
|---|---|---|
| 1 | Wraithlord, Wraithblades | geteiltes Wraith-Vokabular, einziges vorhandenes Sprite |
| 2 | D-cannon / Shadow Weaver / Vibro Cannon Platform | EIN Chassis, drei Datenblätter → EINE Suite (Kroot-Shaper-Muster) |
| 3 | Fire Prism, Night Spinner, Vypers | Falcon-Rumpf bzw. Windrider-Waffenmenü |
| 4a/4b | Warlock, Spiritseer, Farseer Skyrunner / Autarch, Autarch Wayleaper, Maugan Ra | schließt die Reverse-Leader-Lücken des Rosters |
| 5 | Dragon Knights, Clanblade, Leystalker, Stonesinger | geschlossene Sub-Fraktion EXODITE |
| 6 | Voidreavers, Voidscarred, Skyreavers, Starfangs, Kharseth, Prince Yriel | alle ANHRATHE |
| 7 | Yvraine, The Visarch, The Yncarne | YNNARI |

### Etappe 0 — der Korpus musste zuerst verallgemeinert werden

`fetch_datasheet_rules.py`s Dedupe war ein IDENTITÄTSTEST auf ein einziges Faction-Objekt
(`if faction is tau_empire.TAU_EMPIRE`). `MISSING_BY_FOLDER` ist jetzt eine `folder`-gekeyte
Tabelle — und das ist der Mechanismus, der **jedes gebaute Datenblatt null Wartung kosten lässt**:
der Name wandert von `MISSING_*` nach `faction.datasheets`, die Gesamtzahl bleibt gleich. Am Ende
von Etappe 7 belegt: die drei Ynnari stehen genau EINMAL im Korpus, `rules/aeldari/` trägt 74
Datenblätter plus `army_rules.md`, und zwei `--offline`-Läufe erzeugen **222 byte-identische**
Dateien.

### Sechs Extraktionen, alle am ZWEITEN Konsumenten

`fight_after_death.py` (18., geteilt von Undying Spite 4+ und Malevolent Souls 3+; seit Orks E2 mit
`Token.kept_after_death`, siehe `## War Horde` — inklusive der
vier Hälften von "zurück auf dem Brett"), `activation_reroll.py` (19., Targeting Array und Crystal
Matrix, die sich nur in `shared_use` unterscheiden), `cp_discount.py` (20., am VIERTEN Konsumenten:
Puretide, My Will Be Done, War Leader), `battle_shock_after_shooting.py` (21.),
`conditional_devastating_wounds.py`, `objective_control.py`-Nachbarn. Dazu
`game/detection_range.py`-Stil-Umbenennungen, wo ein Name log.

### Was diese Etappen an ECHTEN Fehlern gefunden haben

- **`protocol_sudden_storm.maybe_offer_advance_reroll()` war gebaut, unit-getestet und wurde
  von `main.py` NIE aufgerufen** — und sein eigener Docstring platzierte es NACH `acknowledge()`,
  wo `DiceManager.reroll_die()` grundsätzlich ablehnt (es braucht `pending_values`). Fünfter Fall
  der "gebaut, aber nie GEFÜTTERT"-Klasse. Jetzt aus EINER Stelle VOR `acknowledge()` angeboten,
  für Sudden Storm und Superlative Strategist zusammen.
  - **Und genau diese Stelle war danach eine ENDLOSSCHLEIFE** (User: "im letzten spiel wurde ich
    immer wieder gefragt, ob ich den advance rerollen will mit den destroyern. es war eine
    schleife bis ich ihn gererollt habe"). Kein Fehler in einer der zwei Fähigkeiten, sondern
    eine Eigenschaft der KETTE: der Zweig bietet zuerst an und macht dann
    `if decision_manager.is_pending: continue`, hält den Wurf also bewusst UNBESTÄTIGT, solange
    ein Prompt offen ist — er MUSS das, weil `acknowledge()` `pending_values` leert und
    `reroll_die()` danach nichts mehr wirft. "Keep it" hinterließ damit exakt das Brett, das die
    Frage erzeugt hat, und der nächste Klick fragte erneut. **Nur Rerollen beendete es**, weil das
    die einzige Antwort ist, die den gelesenen Zustand ändert (`already_rerolled`).
  - **Das Gedächtnis gehört dem WURF, nicht der Fähigkeit** → `DiceManager.claim_reroll_offer(source)`,
    von `roll()` geleert wie `already_rerolled` daneben. **EIN Aufruf, kein Fragen/Merken-Paar:**
    ein Angebot, das gemacht und nicht gebucht wird, IST der Fehler, also gibt es keine Möglichkeit,
    die Hälfte davon zu tun.
  - **Nach QUELLE gekeyt, nicht ein geteiltes Flag** — zwei Fähigkeiten dürfen je einmal aus ihrem
    eigenen gedruckten Grund fragen. **Gemessen: keine Einheit kann beide halten** (Aeldari-
    Datenblatt gegen Necron-Stratagem-Grant), also kann eine A/B-Sonde gegen die zwei
    Fähigkeits-Suiten ein Set nicht von einem Flag unterscheiden — die Zusicherung steht deshalb
    KONSTRUIERT in der Suite des `DiceManager` selbst.
  - **Die andere Richtung ist die gefährlichere und hat eine eigene Sonde:** wird das Gedächtnis
    nicht von `roll()` geleert, wird der ZWEITE Advance der Schlacht nie mehr angeboten — ein
    stiller Verlust ist schlimmer als die Schleife.
  - **Getestet:** `test_hazard_lock_and_dice.py` 43 → **50/50** (der `DiceManager` selbst),
    `test_autarchs_and_maugan_ra.py` 129 → **137/137**, `test_awakened_dynasty.py` 89 → **95/95**;
    neu `ab_advance_reroll_loop.py` (**5 A/B-Sonden, alle beißend**, über alle DREI Suiten — ein Fix,
    der nur eine der zwei Fähigkeiten erreicht, ist genau die Drift, die dieses Repo konsolidiert).
  - **Im ECHTEN Spiel belegt** (`verify_advance_reroll_loop.py`, `runpy` auf `selfplay.py`s echte
    `main()`-Schleife, mit ECHTEN Mausklicks in die ECHTE Event-Kette): **1 Prompt, abgelehnt, Würfel
    bestätigt** gegen `--neutralize`s **130 Prompts und ein Würfel, der nie verschwindet**. Der
    Grant und der Advance-Wurf werden gestellt (ein MockAgent-Lauf erreicht "gekauft UND advanced
    UND der Mensch klickt" nicht), alles danach ist echt.
    **Harness-Falle dabei, und sie kostete einen Fehllauf:** `movement_controller.selected_squad`
    ist das Feld, aus dem der Zweig die Einheit liest, und die parallel laufende KI ruft
    `select(None)` zwischen den Frames — die Sonde maß dadurch einen Klick ohne Einheit und meldete
    wahrheitsgetreu aussehende Nullen. Sie hält die Auswahl jetzt. **Und ein zweiter Fehllauf war
    die dokumentierte `__pycache__`-Rennbedingung** (Fehlerklasse 19): direkt nach einem
    Sondenlauf, der den Cache im Sekundentakt loescht, meldete derselbe Aufruf 0 statt 130 —
    wiederholt nach `rm -rf __pycache__` sofort korrekt.
- **`MissilePodProfile` trug die BS des DROHNEN-Datenblatts fest verdrahtet** — unsichtbar,
  solange nur Drohnen ihn benutzten, falsch ab dem ersten BATTLESUIT-Träger.
- **`UnitProfile.support_weapon` wurde von KEINEM Datenblatt gesetzt**, obwohl Etappe 2 die drei
  SUPPORT-WEAPON-Plattformen mit dem Keyword in der `keywords`-Leiste gebaut hat. Damit konnte
  `branching_fates.py`s "excluding SUPPORT WEAPON models"-Klausel auf genau den Einheiten nicht
  feuern, für die sie geschrieben war — sie stand als "kein SUPPORT-WEAPON-Datenblatt existiert
  hier" im Kommentar, was seit Etappe 2 falsch war. Gefunden, weil Word of the Phoenix der ZWEITE
  Leser derselben Klausel ist. Beide sind jetzt scharf.
- **Sechs Aeldari-EPIC-HEROes setzten `epic_hero` nicht** (Asurmen, Avatar, Baharroth, Eldrad,
  Jain Zar, Lhykhis), obwohl ihre Datenblätter das Keyword drucken — also war **Regel 15.03 (Epic
  Challenge) für sie still inert**. Dieselbe Klasse wie die CHARACTER-Lücke, die dieselbe Fraktion
  schon einmal hatte. Aufgefallen, weil die Mythic Stance des Visarch die erste Waffe im Repo ist,
  die `[ANTI-EPIC HERO]` druckt. Als **fraktionsweite Invariante** gepinnt (jedes Datenblatt, das
  das Keyword druckt, setzt die Flagge), nicht als sechs Einzelzeilen.
- Ein `.index()` in einem Reihenfolge-Wächter **stürzte ab, statt rot zu werden** — ersetzt durch
  einen `find()`-Helfer, dieselbe Lehre wie bei den zwei `str.index()`-Wächtern der T'au-Etappe.
- Der AST-Wächter fing zweimal einen freien Namen in `main()` (`strategic_reserves_controller`,
  das gar kein Controller ist sondern ein MODUL; und ein `random`, das dort nie gebunden ist).
  Beide genau die Klasse, für die er existiert.

### Etappe 7 — die drei Ynnari, und warum sie ein Satz sind

Alle drei drucken **Servant Of The Whispering God** ("deine Armee darf keine Nicht-YNNARI-EPIC-
HEROes enthalten") — eine **LISTENBAU-Beschränkung, also ein belegter No-op**: es gibt keinen
Armeebau-Schritt, die Liste steht beim Schlachtbeginn fest, es gibt keinen Moment, in dem sie
feuern könnte. Benannt und gepinnt statt weggelassen. Ebenso **Disparate Paths**, die YNNARI-
ARMEEREGEL, die als zweite FACTION-Zeile auf dem Datenblatt steht — Armeeregeln baut diese Engine
aus der `ArmyList`, nicht aus einem Datenblatt.

- **Der Asu-var des Visarch hat DREI Stances**, wo jede andere Mehrprofilwaffe des Repos zwei hat.
  `overcharge_profile` ist EIN Link, also werden sie VERKETTET (quicksilver → duellist → mythic),
  und nur die erste wird vergeben — sonst führte er drei Schwerter.
- **Way of the Blade ist die DRITTE Quelle von Fights First** und die erste, die weder die eigene
  gedruckte 24.13-Fähigkeit noch 11.04s Nachcharge-Grant ist. Sie faltet deshalb in
  `squad_has_fights_first()`, die eine Stelle, die das beantwortet — irgendwo sonst hätte
  `FightController`s AKTIVIERUNGSREIHENFOLGE eine zweite Meinung bekommen, und die Reihenfolge ist
  der ganze Inhalt von 24.13.
- **Yvraine's Champion: drei Wörter tun echte Arbeit** ("OTHER" schließt den Visarch selbst aus,
  "CHARACTER models" die Bodyguards, "while LEADING" ist 24.22). Jedes einzeln gemessen, weil das
  Weglassen jedes einzelnen eine Fähigkeit ergibt, die weiter feuert und bloß weiter ist.
  **Rückgabewert ist `"-"`, nicht `None`** — der No-FNP-Sentinel, den jede andere Quelle liefert;
  mit `None` kollabierte `_better_threshold()` acht fremde Suiten.
- **Word of the Phoenix ist der sechste Modell-Rückholer** und der mit den meisten
  Danebengriff-Möglichkeiten: vier Qualifikatoren, alle vier Beschränkungen. "BODYGUARD models"
  wird aus `AttachedComponent.role` gelesen — der Provenienz, die `attach()` ohnehin führt —, nicht
  aus dem Aussehen der Modelle. **ZWEI Würfel, also zwei Fenster**: `DiceManager` hält einen Wurf,
  der D6-Gate und der D3+1-Zähler können sich keins teilen.
- **Inevitable Death ist Fuegans Unquenchable Resolve mit umgedrehtem Pfeil**: derselbe
  Ringlauf, dieselbe Engagement-Range-Pflicht — aber es ist der Tod eines ANDEREN, der ein die
  ganze Zeit lebendes Modell bewegt, also geht nichts auf oder von der `destroyed_models`-Liste.
  **"once in each OPPONENT'S turn"** ist nach Zugbesitzer gekeyt; als "einmal pro Zug" gelesen
  hätte es jede Runde einen zweiten Teleport verschenkt.
- **Ethereal Forms D3 wird IM MODUL geworfen, nicht über den DiceManager** — bewusste Ausnahme
  von der Sichtbarkeitsgewohnheit: es feuert im Todes-SWEEP, wo Deadly Demise und die
  Notausstiegs-Queue schon um das eine Wurffenster streiten (genau die Kollision, die
  `deadly_vectors.py` festhält und dort durch eine andere Naht gelöst wurde — hier gibt es keine
  andere Naht). Das LOG trägt Wurf und Heilung getrennt.
- **Zwei Wächter waren gegenseitig maskiert**: `ethereal_form_applies()` und der Pro-Modell-Filter
  können auf einem gebauten Roster nie widersprechen, weil kein Datenblatt den Yncarne mit
  irgendetwas anderem in eine Einheit bringt. Die gemischte Einheit wird deshalb von Hand gebaut —
  die einzige Art zu fragen, welcher der beiden die Arbeit tut, und die Antwort muss der
  Pro-Modell-Filter sein, weil das gedruckt ist.

**Getestet:** sieben neue Suiten — `test_wraith_constructs.py` (139), `test_support_weapon_platforms.py`
(120), `test_aeldari_gun_tanks.py` (102), `test_aeldari_psykers.py` (100),
`test_autarchs_and_maugan_ra.py` (129), `test_exodites.py` (128), `test_corsairs.py` (135),
`test_ynnari.py` (**153**). Für Etappe 7 **23 A/B-Sonden an der QUELLE, alle beißend** — vier
bissen zunächst nicht, und alle vier waren Befunde über den TEST (Fehlerklasse 24): eine Klausel,
die kein gebautes Paar erreichen kann, ein "up to", das mit mehr Würfeln als Leichen nichts
beschränkt, ein voll geheilter Statist, der einen Filter nicht beweisen kann, und eine Sonde, die
hinter einer Docstring einfügte. Volle Regression **147 Suiten, ~11264 Prüfungen, 146 grün /
0 rot / 1 bekannt**, alle fünf Smokes, `selfplay.py` auf map2 UND map3, und
`python run_tests.py --smoke` komplett grün.

**Bewusst offen:** keines der 27 steht in einer Demo-Armee, keines hat einen KI-Pfad (User-Vorgabe,
als Negativraum geprüft: kein Name taucht in `ai/agent_driver.py` auf), und außer `Wraithlord.png`
hat keines ein Sprite — alle Abwesenheiten sind am MODELL gepinnt, damit späteres Hinzufügen eine
sichtbare Änderung ist.

## Die sieben Aeldari-Detachment-REGELN

**Aeldari geht von einem auf acht modellierte Detachments** (User: "jetzt folgende detachment
regeln in Etappen: Aspect Host, guardian battle host, warhost, Windrider hist, spirit conclave,
armoured warhost, path of the outcast"). Der Korpus trägt 15 Aeldari-Detachments; diese sieben
sind gebaut.

**Umfang ist auf User-Entscheidung die REGEL, nichts sonst.** Die sieben drucken zusammen 36
Stratagems und 24 Enhancements (hier stand zuerst 30 — nachgezählt am Korpus sind es
6+6+6+6+6+3+3; die falsche Zahl hatte ausgerechnet die beiden Detachments übersprungen, die
weniger als sechs drucken); die bleiben Daten und sind die nächste Arbeit — dieselbe
Dreiteilung wie beim T'au-Nachzug (6 Regeln → 25 Stratagems → 19 Enhancements). `stratagems=`
und `enhancements=` sind deshalb LEER, mit dem Grund darüber. **Die damals einzige
Aeldari-Liste fieldete weiter Seer Council** (User-Entscheidung): die sieben waren deklariert
und einzeln per `selfplay.py` verifiziert, aber nichts am Default-Spiel änderte sich — dieselbe
Behandlung wie die 27 Datenblätter, die in keiner Demo-Armee stehen. **Seit den zwei Listen
vom 2026-09-08 sind VIER der sieben wirklich gefieldet** — Warhost, Armoured Warhost, Guardian
Battlehost und (schon länger) Path of the Outcast; ungefieldet bleiben Aspect Host, Windrider
Host und Spirit Conclave. Der Default (`config.PLAYER1_ARMY`) ist unverändert `aeldari`.

| # | Detachment | DP | Regel | Naht |
|---|---|---|---|---|
| 1 | Armoured Warhost | 1 | Skilled Crews | Adjuster-Kette + `coldstar.weapon_has_assault()` |
| 2 | Path of the Outcast | 1 | Far-Reaching Doom | `detection_range.py` (vierte Quelle) |
| 3 | Guardian Battlehost | 2 | Defend at All Costs | `_hit_modifiers()` ×2 |
| 4 | Aspect Host | 3 | Path of the Warrior | automatische 1er-Rerolls ×4 + Wahl |
| 5 | Warhost | 3 | Martial Grace | `battle_focus.py`, drei Klauseln |
| 6 | Windrider Host | 2 | Ride the Wind | zwei Ankunfts-Tore + Zugende-Rückzug |
| 7 | Spirit Conclave | 2 | Shepherds of the Dead | neunte Feindmarke + Battle-Focus-Aura |

### Etappe 0 — drei Voraussetzungen

- **`ASURYANI` ist ein eigenes Feld, kein `battle_focus`-Ersatz.** `Datasheet` hat jetzt
  `faction_keywords` — die ZWEITE gedruckte Keyword-Zeile. Gemessen: **54** Aeldari-Datenblätter
  setzen `battle_focus`, aber nur **51** drucken ASURYANI; das Ynnari-Triumvirat druckt die
  Armeeregel und gehört zu YNNARI. Genau zwei davon sind PSYKER — also die Menge, die Spirit
  Conclaves "ASURYANI PSYKER" ausschließen muss. Mit dem Flag als Stellvertreter wäre die Klausel
  an der EINZIGEN Stelle falsch gewesen, an der sie beißt.
  - **Die Zeile ist NICHT ein Keyword pro Datenblatt** — 41 drucken BEIDE (die meisten
    Craftworld-Einheiten dürfen in einer Ynnari-Armee stehen). Erste Transkription war falsch und
    wurde vom Korpus-Vergleich sofort gefangen.
  - **Die zehn ASURYANI-only sind kein Zufall: sie sind Servant Of The Whispering God in den
    Daten.** Ein Ynnari-Heer darf keine EPIC HEROes ohne YNNARI enthalten, also können diese zehn
    das Keyword nicht tragen — und es sind exakt die zehn, die `epic_hero` setzen. Daraus
    abgeleitet statt von Hand gelistet, gegen den Korpus gepinnt.
- **`game/detachment_gate.py` (22. Extraktion).** `has_detachment()` lag in
  `game/tau_detachments.py`, liest aber nur eine `config`-Konstante und weiß von keiner Fraktion.
  Mit dem ersten Nicht-T'au-Konsumenten ist das der lügende Name (Fehlerklasse 11).
  `tau_detachments.py` re-exportiert, also weiter EINE Definition; im Test als Identität gepinnt.
  Dazu **`game/aeldari_detachments.py`** als Spiegel: `is_aeldari_unit` kam aus
  `psychic_guidance._is_aeldari` — einem PRIVATEN Namen in einem DATENBLATT-Modul, in den
  **dreizehn** andere Module hineingriffen.
- **Nebenbefund mitgefixt: die sechs Seer-Council-Stratagems waren ungegatet.** Solange Seer
  Council das EINZIGE Aeldari-Detachment war, waren "eine Aeldari-Armee" und "eine
  Seer-Council-Armee" dieselbe Menge, also waren sie zufällig richtig. Mit acht wäre eine
  Warhost-Armee im Besitz von Strands-of-Fate-Stratagems. Alle sechs lesen jetzt
  `strands_of_fate.has_detachment()`. **Isha's Fury fragt den REAKTOR, nicht den Beweger** —
  eigene Testzeile, weil die andere Lesart sich gut liest.

### Was die sieben an echter Mechanik gekostet haben

- **Skilled Crews muss an ZWEI Stellen ankommen.** [ASSAULT] in die Adjuster-Kette ist die
  Hälfte, die man sieht; die Hälfte, für die das Detachment gekauft wird, ist
  `coldstar.weapon_has_assault()` — Advance-und-Schießen (24.04). Ein Grant nur in der Kette
  sähe verdrahtet aus und täte genau das Falsche nicht.
- **Far-Reaching Doom heißt nach der REGEL, nicht nach dem Detachment.** `game/path_of_the_outcast.py`
  ist die RANGERS-DATENBLATT-Fähigkeit gleichen Namens und teilt kein Wort Text. Von beiden Seiten
  gepinnt. **Richtung ausgeschrieben:** Detection Range gehört dem VERSTECKTEN Modell, +6" auf die
  Feinde macht sie von WEITER WEG sichtbar; in BEIDEN Bändern gemessen (15" und die 12"-Hauswandregel).
- **Defend at All Costs: "and/or" ist ein ODER** — drei der vier Brettlagen zahlen, jede eine
  eigene Testzeile. **Und die Granularität ist die KOMPONENTE, nicht die Einheit**: der eigene
  Test hat gefangen, dass ein Farseer, der Guardian Defenders führt, das GUARDIANS-Keyword seiner
  Leibwache geerbt hätte. Jetzt über `AttachedComponent.starting_models` gelesen, mit genau
  diesem realen Paar als Testfall.
- **Path of the Warrior ist eine ECHTE Wahl** (zwei exklusive Optionen), also ein Prompt — der
  Gegenfall zu Herald of Ynnead, dessen eine Option reiner Gewinn war. Gelesen an **vier**
  Stellen, und zwar in den `automatic_ones`-Disjunktionen, NICHT in den Reroll-Reason-Methoden:
  jede Klausel ist eine schlichte Pflicht-1er-Wiederholung ohne "you can" und ohne "instead".
  Kein `reroll_scope`-Eintrag, als Abwesenheit gepinnt.
- **Martial Grace' drei Klauseln liegen alle in `battle_focus.py`** — das Detachment fügt keine
  Mechanik hinzu, es dreht an der vorhandenen. **Welche Manöver wirklich einen D6 werfen, ist
  GEMESSEN**: von sechs nur Opportunity Seized und Fade Back, beide durch EINEN Aufruf. Sudden
  Strike ist der Beinahe-Treffer — seine "up to 6"" ist eine Distanz, kein Würfel.
- **Ride the Winds Rundenklausel gilt NUR fürs Aufstellen** und erreicht deshalb BEIDE
  Ankunfts-Tore in `ingress.py` (20.03s Runde-2-Sperre und die Runde-3-Zonenlockerung). Der
  Zähler selbst bleibt unberührt — VP, Missionen und die Zerstörung übriger Reserven lesen weiter
  die echte Zahl. **Zwei der vier Klauseln sind gemessene No-ops**: 20.01 lässt ohnehin jede
  Einheit in Reserve, und BATTLELINE liest bei Aeldari kein Modul.
- **Shepherds of the Dead ist die NEUNTE Feindmarke und die erste, die ein TOD setzt** — also
  kein `offer_*`, sondern der Todes-Sweep. Zwei Dinge, die keine der acht anderen hat: sie ist
  KUMULATIV ("one or more tokens") und sie LÄUFT NIE AB (kein `reset_turn`/`reset_phase`) — genau
  die Abwesenheit, die ein späterer Leser "repariert", deshalb gepinnt.

### A/B-Sonden: 85, alle beißend — und fünf Befunde über den TEST

Je Etappe eine Sondendatei, jede neutralisiert EINE Klausel an der QUELLE.
**Fünf bissen zunächst nicht, und alle fünf waren Fehlerklasse 24** — eine ZWEITE Bedingung
verdeckte die geprüfte:

1. 19.03-Pooling bei `faction_keywords`: jedes BODYGUARD-Datenblatt druckt beide Keywords, die
   eigene Zeile des Squads antwortet also immer zuerst — der Komponenten-Lauf entscheidet nie.
2. Ride the Winds ASURYANI-Hälfte: nichts MOUNTED ist Ynnari, die Prüfung kann auf dem gebauten
   Roster nicht diskriminieren.
3. Spirit Guides' Keyword-Filter: der Nicht-Wraith-Testfall stand ausserhalb der Aura und wurde
   aus dem falschen Grund abgelehnt.
4. Aspect Hosts Reroll-Reason-Wächter war eine TAUTOLOGIE (`... or True`).
5. Der Etappe-6-Sondenlauf hatte eine um eins zu hohe BASELINE, wodurch jede Sonde trivial "biss".

Die ersten drei sind jetzt von Hand isoliert (ein konstruierter Fall, weil der Roster keinen
hergibt) — dieselbe Behandlung wie die zwei sich gegenseitig maskierenden Ethereal-Form-Wächter.

**Getestet:** neu `test_aeldari_detachment_rules.py` (**369/369**, acht Abschnitte) plus **85
A/B-Sonden**. Volle Regression **148 Suiten, ~11671 Prüfungen, 147 grün / 0 rot / 1 bekannt**,
alle fünf Smokes, `python run_tests.py --smoke` komplett grün, und **ein echter
`selfplay.py map2`-Lauf je Detachment** (alle exit 0, alle innerhalb des 3-DP-Budgets legal).

**Bewusst offen:** die 24 Enhancements der sieben. Die 36 Stratagems sind gebaut — siehe den
eigenen Abschnitt darunter. Kein KI-Pfad (stehende Aeldari-Vorgabe, als Negativraum geprüft — kein
neuer Name in `ai/agent_driver.py`); und keine Demo-Armee ändert sich.

**KORREKTUR eines Befundes aus dieser Sitzung:** `test_report_20260824.py` wurde hier zeitweise
als bekannter Fehlschlag (61/65) eingetragen. **Das war ein `__pycache__`-Artefakt, kein echter
Fehlschlag.** Nach `find . -name __pycache__ -exec rm -rf {} +` meldet die Suite dreimal
hintereinander **65/65**. Die Fehldiagnose entstand, weil die A/B-Sondenskripte dieser Sitzung den
Cache im Sekundentakt löschen und neu schreiben — genau die Rennbedingung, die dieses Repo als
Fehlerklasse 19 führt ("ein Fehlschlag direkt nach vielen Edits erst WIEDERHOLEN, dann suchen").
Die Wiederholung war deterministisch und hat mich deshalb in die falsche Richtung geschickt: vier
gezielte Reverts und ein HEAD-Worktree-Lauf später stand fest, dass keine meiner Änderungen
schuld war — der Cache war es. **Lehre: bei einem Fehlschlag nach einem Sondenlauf zuerst den
Cache löschen, nicht bisecten.** Der HEAD-Worktree-Lauf (58/64) misst eine ÄLTERE Fassung der
Suite und sagt über den heutigen Stand nichts.

## Die 36 Aeldari-Detachment-STRATAGEMS (sieben Etappen)

**Alle 36 sind gebaut** (User: "jetzt die stratagems jedes detachment eine Etappe / keine KI
pfade"), eine Etappe je Detachment, aufsteigend nach Aufwand. **35 Dateien für 36 Stratagems**:
Skyborne Sanctuary steht in Warhost UND Aspect Host, WHEN/TARGET/EFFECT byte-identisch, also EIN
Modul mit zwei Controller-Instanzen — der Gate ist ein Konstruktorargument, kein zweites File.

| Etappe | Detachment | Präfix | # |
|---|---|---|---|
| 1 | Armoured Warhost | `armoured_` | 3 |
| 2 | Path of the Outcast | `outcast_` | 3 |
| 3 | Guardian Battlehost | `guardian_` | 6 |
| 4 | Windrider Host | `windrider_` | 6 |
| 5 | Warhost | `warhost_` | 5 (+ das geteilte) |
| 6 | Spirit Conclave | `conclave_` | 6 |
| 7 | Aspect Host | `aspect_` | 5 (+ das geteilte) |

**`game/proactive_stratagems.py` ist der Grund, warum 36 tragbar sind.** `ActionPanel.draw()`
nimmt 81 `=None`-Parameter durch eine dreistufige, streckenweise POSITIONELLE Kette — 36 weitere
wären 36 Gelegenheiten für genau den Fehler, dessen Narbe die Datei trägt. Ein proaktives
Stratagem tritt der Registry mit `can_use`/`use`/`panel_label` bei; das Panel wurde für die 36
**zweimal** angefasst, beide Male für MOVE-Routing und nie für einen Knopf (Overflight und
Warhosts Fire and Fade brauchen einen eigenen Confirm-Zweig, weil sie Konsequenzen "if it does"
tragen bzw. `active_player` zurückgeben müssen).

### Die vier Extraktionen dieser Etappen

| # | Modul | Am wievielten Konsumenten |
|---|---|---|
| 21 | `game/move_exceptions.py` | 09.06/09.07s Ausnahmen lagen als DREI hartkodierte Ketten in zwei Dateien |
| 22 | `game/detachment_gate.py` | `has_detachment()` lag in einem T'au-Modul und kannte keine Fraktion |
| 23 | `game/engagement.py` | 03.04s "within Engagement Range", dreimal ausgeschrieben, mit zwei weiteren Konsumenten |
| 24 | `game/ignore_characteristic_modifiers.py` | Seer's Eye (AP+D), dann Warrior Focus (+S) |
| 25 | `game/whole_unit_drag.py` | Block-Deployment und Block-Movement waren EINE Einstellung mit zwei Flags (siehe die Toggle-Leiste) |

- **`move_exceptions` führt VIER Fragen, nicht eine**, und das ist gedruckt: Vectored Engines hebt
  einen Bann auf, Time to Strike zwei, Feigned Retreat zwei ANDERE, Wind of Blades alle vier. Vier
  Mengen, jede mit eigener Quellliste; eine Pauschale hätte Wind of Blades' Umfang still an alle
  verteilt. **Die vierte Frage hat keine Datenblatt-Quelle:** [ASSAULT] ist, wie eine WAFFE nach
  einem Advance feuert (24.04) — diese Stratagems befreien die EINHEIT, also wäre ein Keyword-Grant
  eine stillschweigende Verbreiterung dessen, was [ASSAULT] bedeutet.
- **`engagement.is_engaged()` unterscheidet sich GEMESSEN von `Squad.is_engaged()`**: letzteres
  filtert keine Toten, weil `remove_dead_models()` einmal pro Frame läuft. Beide Einheiten leben →
  gleich; der Feind gerade ausgelöscht → **True gegen False**; die eigene Einheit ausgelöscht →
  ebenso. Für eine Ende-der-Phase-Klausel ist das der Unterschied zwischen Angebot und Ablehnung.
  **`Squad.is_engaged()` ist bewusst NICHT geändert** — Schussberechtigung, Charge und Fall Back
  lesen es, das ist eine eigene Messreihe. Benannt und gegeneinander gepinnt.
- **`ignore_characteristic_modifiers` löst das Problem, das AP und Damage KEINE Modifikatorliste
  haben.** Der Trefferwurf hat eine (`game/modifiers.py`, drei Filter darauf); S/AP/D entstehen als
  flache Werte auf einer Kopie, mit jeder Quelle bereits überschrieben. Also **per VERGLEICH**: die
  angepasste Waffe gegen ihre eigene GEDRUCKTE Klasse, das Bessere je Charakteristik. Kein Ledger,
  und es kann nicht aus dem Takt geraten, weil es die Ausgabe der Kette selbst liest.
  **"Besser" läuft in zwei Richtungen** (S höher, AP negativer, D höher) — ein einzelnes
  `min()`/`max()` wäre für die Hälfte richtig. Eine gewürfelte Damage-Notation bleibt unangetastet.
  "Any or all" wird AUTOMATISCH aufgelöst, dieselbe Lesart, die Kauyon und 24.29 [PSYCHIC] schon
  ausschreiben.

### Neue Nähte, die es vorher nicht gab

- **`ChargeController.on_charge_move_finished`** — Etappe 3 (Crushing Strides ist der vierte Nutzer).
- **`FallBackController` veröffentlicht ZWEI Momente**, und die zwei Karten stehen ein Wort
  auseinander: `on_fall_back_declared` ("is SELECTED to Fall Back", Khaine's Vengeance) in
  `declare()`, `on_fall_back_finished` ("just after it FALLS BACK", Feigned Retreat) in `confirm()`
  — letzteres NUR bei geglücktem Zug, und VOR dem Desperate-Escape-Wurf, weil der eine Folge EINER
  Art Fall Back ist und nicht Teil davon.
- **`IngressController.ingressed_this_turn`** — "set up from Reserves THIS TURN" (Death from on
  High). `Squad.set_up_this_turn` setzt JEDE Platzierung inkl. Aufstellung; `ingressed_this_phase`
  ist die richtige TATSACHE auf der falschen UHR (sie stimmt in Schuss/Nahkampf nur, weil
  `reset_movement_phase()` noch nicht wieder lief — ein Ordnungszufall).
- **`crit_hit_threshold(weapon=)`** — Blitzing Firepowers zweite Klausel ist eine Eigenschaft der
  WAFFE; jede Quelle davor gehörte dem Modell oder seiner Einheit.
- **`weapon_range` bekommt einen ÜBERSCHREIBUNGS-Term**, seinen ersten: sein Docstring sagte "THE
  TERMS ADD" (drei Quellen, alle +6"). Doom Inescapable SETZT 18".
- **`FightAfterDeath(bonus_for=)`** — To Their Final Breaths +1 variiert PRO EINHEIT innerhalb
  einer Phase, kann also nicht in die feste Schwelle gefaltet werden.
- **`can_embark(range_in=, require_move=)`** und **`Squad.embark_locked_until_end_of_turn`** — das
  Gegenstück zu `charge_locked_until_end_of_turn`, das es seit fünf Regeln gibt.
- **`MortalWoundOfferController` hat den Unterstrich verloren** — privat, solange alle fünf
  Subklassen im selben Modul wohnten; Crushing Strides ist der sechste und wohnt woanders.

### Was diese Etappen an ECHTEN Fehlern gefunden haben

1. **`move_exceptions.clear_turn_flags()` wurde von NIRGENDS aufgerufen** — sechster Fall der
   "gebaut, aber nie GEFÜTTERT"-Klasse, und meiner aus Etappe 1. Jede "bis zum Ende des Zuges"-
   Ausnahme hätte den Rest der Schlacht gelaufen; ein Kommentar in `main.py` behauptete den Sweep.
   Beide Suiten waren grün, weil sie ihn selbst rufen. **Gefegt wird über JEDE Einheit**, nicht über
   `ending_squads`: ein Zug ist EINES Spielers Zug, also beendet jedes Zugende ein solches Latch.
2. **`overflight_controller` wurde nie an das Panel ÜBERGEBEN** — Etappe 4 ergänzte den Parameter,
   Etappe 5 fand die tote Verdrahtung. Ein Panel-Wächter sieht das nicht; die AUFRUFSTELLE muss
   geprüft werden.
3. **Die WRAITH CONSTRUCTs hatten Battle Focus, das sie nicht drucken** — siehe den eigenen
   Abschnitt darunter.

### Vier Regel-ENTSCHEIDUNGEN, die keine Transkription sind

- **Blitzing Firepowers "if such a weapon ALREADY has that ability"** wird am GEDRUCKTEN Profil
  entschieden, nicht an der Instanz aus der Kette. Sonst zählte eine Dire-Avenger-Katapult in
  Halbdistanz als "hat bereits", weil Bladestorm es gerade gewährt hat — und die Antwort hinge
  davon ab, welcher Adjuster zuerst lief. Die andere Lesart ist vertretbar und im Modul benannt.
- **Seer's Eye liest AELDARI PSYKER**, wie gedruckt (User-Entscheidung), obwohl Soul Bridge daneben
  ASURYANI sagt — in dieser Engine zwei verschiedene Mengen.
- **Doom Inescapable ist als OVERRIDE geschrieben, obwohl "+6" heute dasselbe ergäbe.** Gemessen:
  die Wailing Doom druckt **12"**, nicht 24" (ich hatte 24 angenommen und lag falsch), also ist 18"
  eine VERLÄNGERUNG. Sobald eine der drei bestehenden +6"-Quellen dieselbe Waffe erreicht, läse ein
  Bonus 24", wo die Karte 18" sagt.
- **"You can remove one Aspect Shrine token" wird GEFRAGT, nicht aufgelöst** (Preternatural
  Precision, To Their Final Breath) — anders als "any or all modifiers", wo kein Zweig je schlechter
  ist. Hier sind beide Zweige lebendig: der Token ist ein Einmal-pro-Schlacht-Würfeltausch.

### A/B-Sonden: 259 über sieben Etappen, alle beißend

Je Etappe eine Sondendatei, jede neutralisiert EINE Klausel an der QUELLE (31 / 39 / 46 / 40 / 42
plus die früheren). **Etwa 20 bissen zuerst NICHT**, und fast alle waren Befunde über den TEST
(Fehlerklasse 24). Die wiederkehrenden Formen, weil sie sich wiederholen werden:

- **Eine ZWEITE Quelle desselben Effekts verdeckte die geprüfte.** Death from on High gegen eine
  [TWIN-LINKED]-Waffe; Blitzing Firepower auf Dire Avengers, die BLADESTORM drucken; Warrior Focus
  auf Dark Reapers, die INESCAPABLE ACCURACY drucken. Jedes Mal hätte die Prüfung mit UNVERDRAHTETEM
  Stratagem bestanden.
- **Rule 15.01s Einmal-pro-Phase verdeckte den zweiten Kauf** — derselbe `StratagemController`
  wiederverwendet, also lehnte `can_use()` aus dem falschen Grund ab. Fünfmal aufgetreten; jetzt
  bekommt jeder zweite Kauf einen frischen Controller.
- **Der Wächter matchte seine eigene ERKLÄRUNG.** `"aspect_shrine.usable(" not in src` fand den
  Docstring, der ausschreibt, warum es NICHT gerufen wird — dieselbe Form wie der
  `max_per_battle`-Fall der T'au-Etappe. Jetzt wird der AUFRUF geprüft.
- **`str.index()` in einem Reihenfolge-Wächter STÜRZT AB statt rot zu werden**, zum dritten Mal in
  diesem Repo. Es gibt jetzt `before(src, first, second)` in der Suite, und der Docstring nennt die
  drei Vorfälle.
- **Eine falsche BASELINE macht jede Sonde trivial "beißend"** — zweimal passiert (BASE um eins zu
  hoch, dann um 23 zu niedrig). Die Zahl gehört nach jedem Suite-Zuwachs nachgezogen.
- **Zwei Sonden waren GEMESSENE No-ops**, kein Testfehler: Soul Bridges drei Datenblattnamen SIND
  auf diesem Roster exakt die WRAITH-CONSTRUCT-Menge, und die zwei Nahkampf-Wailing-Doom-Zeilen sind
  eigene Klassen (keine Unterklassen der Fernkampfzeile), sodass der `isinstance`-Test sie ohnehin
  ausschließt. Beide Tatsachen sind jetzt gepinnt, statt als Testlücke dazustehen.

**Getestet:** `test_aeldari_detachment_stratagems.py` (**965/965**, acht Abschnitte) plus die
Sonden. Der Abschnitt-7-Zählsweep zählt die Module je Präfix und verlangt von jedem, dass es auf
sein Detachment gatet und seinen gedruckten Regeltext zitiert — ein 37. kann nicht auftauchen, ohne
dass diese Zeile sich bewegt. Volle Regression **153 Suiten, ~12980 Prüfungen, 152 grün / 0 rot /
1 bekannt**, `python run_tests.py --smoke` komplett grün, und **ein echter `selfplay.py map2`-Lauf
je Detachment** mit dieser Liste temporär gefieldet.

**Kein KI-Pfad** (User-Vorgabe), für alle 36 als Negativraum geprüft. **Keine Demo-Armee änderte
sich** — die damals einzige Aeldari-Liste fieldete weiter Seer Council. **Seit den zwei Listen
vom 2026-09-08 sind Warhost, Armoured Warhost und Guardian Battlehost gefieldet**, ihre
Stratagems also nicht mehr dormant: von den neunzehn PANEL-Knöpfen der Fraktion sind **acht statt
drei** im echten Spiel erreichbar. **Die Reichweite ist dabei sehr ungleich gewachsen** — Warhost
allein brachte EINEN Knopf, weil fast alles daran reaktiv ist und ein reaktives Stratagem gar nicht
erst auf die Registry kommt; das Paar darunter hat sie verdoppelt. Genau deshalb leitet der Wächter
die Zahl aus den deklarierten Detachments ab, statt sie hinzuschreiben.

## WRAITH CONSTRUCTs hatten Battle Focus, das sie nicht drucken

**Vom User beim Lesen von Spirit Conclave bemerkt** ("wraith constructs wie zum beispiel
wraithguard haben gar kein battle focus. sie dürfen also außerhalb von dieser detachment regel gar
keine agile manouver benutzen. das ist jetzt noch nicht so oder?"). Richtig, und die Folge war
größer als die Frage.

**Gemessen gegen den Korpus:** SECHS Datenblätter setzten `battle_focus`, obwohl ihr gedrucktes
Blatt **gar keine FACTION-Zeile** trägt, während jedes Aeldari-Blatt MIT der Armeeregel
`FACTION: **Battle Focus**` druckt — die drei WRAITH CONSTRUCTs (Wraithguard, Wraithblades,
Wraithlord) und die drei SUPPORT-WEAPON-Plattformen. Es ist **nicht** "Wraith Constructs haben es
nie": der Wraithknight DRUCKT es. Pro Datenblatt, deshalb ist der Korpus die Instanz und keine
Faustregel.

**Die eigentliche Folge:** `battle_focus.has_battle_focus()` hat seit dem Bau von Spirit Conclave
eine TEMPORÄRE Quelle — Spirit Guides, "while a WRAITHBLADES, WRAITHGUARD or WRAITHLORD unit is
within 12" of this model, that unit HAS the Battle Focus ability". Die Aura gewährte also, was ihre
Ziele bereits dauerhaft besaßen: **die halbe Detachment-Regel war inert.** Nach der Korrektur
gemessen: Wraithguard allein `False` → in 12" eines Spiritseers `True` → Psyker geht weg `False`.

**Fünf Suiten wurden zu Recht rot**, alle Pins auf das falsche Flag. Der bezeichnendste stand in
`test_aeldari_detachment_rules.py` und stammte von mir: *"all three named datasheets already print
Battle Focus"*, mit dem Kommentar, die Aura sei "a near-no-op on the built roster, measured". **Ein
Pin, der den Fehler als Regel protokolliert hatte.** Alle fünf behaupten jetzt die korrigierte
Tatsache samt Grund.

**Lehre für die nächste Fraktion:** ein Armeeregel-Flag gehört gegen die FACTION-Zeile des Korpus
geprüft, nicht gegen die Fraktionszugehörigkeit — `test_aeldari_detachment_stratagems.py`s
Abschnitt 6z tut das jetzt für JEDES gebaute Aeldari-Datenblatt und würde ein siebtes sofort nennen.
