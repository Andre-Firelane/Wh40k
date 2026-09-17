# T'au: Datenblatt-Nachzug

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die drei Kroot Shaper (Etappe 1a der fehlenden T'au-Datenblätter)

**Flesh / Trail / War Shaper — ein Datenblatt je, aber EINE geteilte Statline.** Alle drei drucken
M7" T3 Sv6+ W3 Ld7+ OC1 auf 32 mm, dieselben vier Core-Fähigkeiten (Infiltrators, Leader, Scouts 7",
Stealth) und dieselbe LEADER-Zeile. Deshalb `KrootShaperProfile` als Basisklasse und **eine** Suite
für alle drei: die Zusicherung, dass sie ÜBEREINSTIMMEN, kann man in drei getrennten Suiten gar
nicht ausdrücken (die A/B-Sonde, die die Vererbung aufbricht, lässt die Suite nicht bloß rot werden,
sondern KRACHEN — die Basisklasse trägt auch das Leader-Keyword).

- **WS/BS gehören aufs PROFIL, nicht an die Waffen.** Jede Waffenzeile der drei druckt WS2+ und
  BS4+; die Pro-Waffen-Overrides sind für ein Modell, dessen Zeilen sich WIDERSPRECHEN (The Twin
  Lance, und in Etappe 1b Darkstrider mit BS2+ auf der Shade neben WS4+ im Nahkampf).
- **Kein For The Greater Good, kein MARKERLIGHT** — dieselbe Entscheidung wie bei Kroot Carnivores,
  und aus demselben Grund: die Datenblätter drucken es nicht (Auxiliare, keine "echten" T'au).
- **`Shaper's Blade` ist EINE Klasse für ZWEI Datenblätter** (Trail und War Shaper drucken sie
  identisch) — im Test gegeneinander gepinnt statt zweimal gegen Literale.
- **Der einzige Wargear-Tausch der drei ist ungewöhnlich und korrekt so**: der War Shaper tauscht
  eine FERNKAMPF-Waffe (Dart-bow and Tri-blade) gegen eine NAHKAMPF-Waffe (Bladestave and
  Prey-hook) und behält danach nur die Kroot Pistol auf Reichweite. Der gedruckte Text hat dort
  einen Tippfehler ("tri-bade"), der Kommentar hält ihn fest.
- **Vier Fähigkeiten verdrahtet, zwei bewusst nicht:**
  - **Ritual Butchery** ([SUSTAINED HITS 1] auf die Nahkampfwaffen der geführten Einheit) ist
    **United In Destruction mit einem anderen Keyword** — dieselbe gedruckte Bedingung, derselbe
    Platz in `FightController._adjusted_weapon()`, und aus demselben Grund: `_crit_note()` muss zur
    WURFZEIT wissen, ob ein kritischer Würfel ein Sustained-Würfel ist. **Wertet nie ab** — "have
    the [SUSTAINED HITS 1] ability" GEWÄHRT die Fähigkeit, es SETZT den Wert nicht; keine
    Kroot-Waffe druckt ein höheres X, weshalb das assertiert statt dem Zufall überlassen wird.
  - **Rites of Feasting** ist **Rites of Reanimation mit zweitem Gang** (FNP 6+, nach einem Kill in
    der Fight-Phase 5+ für den REST DER SCHLACHT). Zwei leicht zu verfehlende Hälften: die Marke
    lebt auf der EINHEIT und wird von KEINER Phasen- oder Zuggrenze gelöscht, und der Kill muss in
    der FIGHT-Phase passieren — was das Modul SELBST prüft, statt der Aufrufstelle zu trauen (der
    Todes-Sweep läuft in jeder Phase). **Der Täter kommt aus `fight_controller.fighting_squad`** —
    die einzige Antwort, die diese Engine auf "wer war das" hat (Kill-Attribution gibt es hier
    nicht, siehe Szeras' eigene Notiz); benannt, nicht versteckt.
  - **War Leader** ist der **fünfte `cost_discounts`-Kollaborator** und wörtlich My Will Be Done in
    anderer Typografie — "einmal pro Schlachtrunde" ist PRO ARMEE, zwei War Shaper teilen sich eine
    Nutzung. `StratagemController` brauchte keine Zeile: es faltet ohnehin eine LISTE.
  - **Root of Honour** (einmal pro Schlacht, Battle-Shock von einer KROOT-Einheit in 12" nehmen) ist
    ein kleiner eigener Controller ohne Würfel und ohne CP. Vier Bedingungen, jede eine eigene Art
    danebenzugreifen: "once per battle" ist **pro Modell** (Gegensatz zu War Leader nebenan, pro
    Armee), "at the start of ANY phase" heißt auch die gegnerische (also aus `advance_turn_phase()`
    über der ganzen phasenspezifischen Kette und für BEIDE Spieler), KROOT wird am Modell gelesen,
    und ein nicht geschockter Ziel-Trupp ist gar nicht erst eine Option (Fehlerklasse 5).
  - **Trail Finding und Kroot Ambush sind NICHT verdrahtet** und stehen als `NOT ENGINE-WIRED` in
    `abilities_text` — im Test assertiert, damit das Nachrüsten eine sichtbare Änderung ist. Bei
    Trail Finding fehlt nicht die Bewegung (`REACTIVE_MOVE_MODES` gibt es), sondern der AUSLÖSER
    "ein Feind hat gerade eine Bewegung BEENDET"; Kroot Ambush ist ein neuer Schritt in 03.01, keine
    Einheitenfähigkeit.
- **`Kroot Farstalkers` steht auf allen drei LEADER-Zeilen und hat kein Datenblatt** — dieselbe
  hängende Halb-Paarung wie Crisis Fireknife, von beiden Seiten gepinnt.
- **Kein Sprite für die drei** (nur `Kroot Carnivores.png` existiert); die ABWESENHEIT ist gepinnt,
  samt der Gegenprobe, dass `_squad_key()`s Teilstring-Matching ihnen nicht versehentlich die
  Carnivores-Kunst gibt.
- **Getestet:** neu `test_kroot_shapers.py` (**102/102**) plus **17 A/B-Sonden**, jede an der QUELLE,
  jede kippt genau ihre eigenen Prüfungen. Volle Regression **129 Suiten, ~8738 Prüfungen, 128 grün /
  0 rot / 1 bekannt**, dazu `smoke_pregame.py map2`, `smoke_log_input.py map2`,
  `smoke_setup_screens.py` und `selfplay.py map2` (4000 Frames) — die Smokes hier keine Formalie,
  weil `main.py` drei neue Stellen bekam (Controller-Konstruktion, Phasen-Haken, Todes-Sweep).
- **Nebenbefund, vom Regeltext-Korpus gefangen:** dessen Wächter "keine Streudateien" wurde rot,
  sobald die drei aus `MISSING_TAU` auch gebaut waren. `fetch_datasheet_rules.py` DEDUPLIZIERT jetzt
  gegen `faction.datasheets`, statt die Liste von Hand zu pflegen — damit kostet jedes weitere
  gebaute Datenblatt dort null Wartung.

## Die sechs übrigen T'au-Charaktere (Etappe 1b)

**Ethereal, Darkstrider, Firesight Team, Kroot Lone-Spear, Commander in Enforcer Battlesuit,
Commander Shadowsun** — alle sechs Ein-Modell-CHARAKTERE, aber im Gegensatz zu den drei Shapern
teilen sie NICHTS, also eine Suite mit sechs Abschnitten statt einer geteilten Basisklasse. Was sie
verbindet, ist die Frage, die die Suite stellt: **ist jede Fähigkeit in der RICHTIGEN Kette
gelandet?**

- **Zwölf Fähigkeiten, elf verdrahtet — und die meisten sind Zwillinge von Vorhandenem:**
  - **Failure Is Not an Option** ist das DRITTE Datenblatt mit Rites of Reanimations exaktem Satz
    (nach Dok's Toolz) — ein weiterer Fold in `current_feel_no_pain()`.
  - **Structural Analyser** (+1 Wundwurf beim Schießen, solange er führt) ist erst der ZWEITE
    ANGREIFER-seitige Eintrag in `_wound_modifiers()`, das sonst die Verteidigung ist (Tank Hunters
    ist der erste). **Vorzeichen NEGATIV** — die Konvention justiert die SCHWELLE, verkehrt herum
    wäre Darkstrider ein armeeweiter Dauermalus.
  - **Precise Targeting** brauchte KEINEN neuen Zustand: "Spotted" setzt die T'au-Armeeregel schon
    (`greater_good.is_spotted()`). **Shooting-only, und das ist keine Vereinfachung** — Spotted
    läuft am Ende der Schussphase ab, ein Nahkampfangriff kann per Konstruktion nie eine Spotted
    Einheit treffen. Ausgeschrieben, damit es niemand neu herleiten muss.
  - **Fire and Fade** ist Asurmens Tactical Acumen plus die gedruckte Engagement-Range-Bedingung.
  - **Enforcer Commander** ist Ramshackle but Rugged eine Bedingung reicher — derselbe Platz in
    `save_thresholds()`, weil beides VERTEIDIGER-seitige AP-Anpassung ist und das die eine Stelle
    ist, an der Panel und Auflösung sich über einen Save einig bleiben. **Die zwei AP-Effekte
    werden KOMPONIERT, nicht gemaxt** — heute hat kein Modell beide, aber das sagen die gedruckten
    Texte.
  - **Agile Combatant** ist die DRITTE gedruckte Formulierung derselben Fall-Back-Ausnahme (nach
    Battlesuit Support System und War Construct) → dasselbe Gate, drei Prädikate.
  - **Hero of the Empire** ist die einzige AURA unter den automatischen 1er-Rerolls: keine
    Eigenschaft der schießenden Einheit, sondern ein Abstand zu einem Modell in einer DRITTEN.
    **Nur der Trefferwurf** — Forward Observers, dem sie sonst gleicht, rerollt beide.
  - **Advanced Guardian Drone** ist Guardian Drone ein Wort enger ("targets THE BEARER" statt "the
    bearer's unit") — auf einer LONE-OPERATIVE-Einzeleinheit dieselbe Angriffsmenge, ausgeschrieben
    statt als Zufall stehengelassen.
  - **Advanced Scouting** ist eine MARKE AUF DEM ZIEL wie Guide/Doom/Whispering Web, mit drei leicht
    verfehlten Klauseln: sie wird von einem TREFFER gesetzt (nicht vom Angriff), "ANOTHER KROOT
    model" schließt den Lone-Spear selbst aus, und sie hält "until the end of the turn". Sie liest
    "an attack", also **beide** Angriffsschritte — Gegensatz zu Precise Targeting nebenan.
  - **Coordinated Leadership** rechnet den CP-Deckel NICHT nach: `bonus_cp_remaining()` ist die eine
    Definition, und es würfelt gar nicht erst, wenn kein Kopfraum bleibt (ein Würfel, der nichts
    zahlen kann, sieht wie ein Fehler aus).
- **Drei bewusst NICHT verdrahtet**, alle als `NOT ENGINE-WIRED` in `abilities_text` und im Test
  assertiert: **Jammer Array** (es beschränkt, wo der GEGNER aus Reserven ankommen darf — die
  Richtung gibt es hier noch nie), die **Command-link Drone** (`StratagemController` hat keinen
  Pro-Nutzung-Haken), und **Supreme Commander** als belegter No-op (kein Warlord-Begriff).
  Dazu die zweite Hälfte des **Battlesuit Support System** ("nur Modelle mit dieser Ausrüstung dürfen
  schießen") — es gibt kein Pro-Modell-Schuss-Gate.
- **Zwei Wargear-Formen, die es so noch nicht gab:** der Ethereal und der Enforcer haben je ZWEI
  unabhängige gedruckte Menüs, also eigene `Gear`-Gruppen (ein Hover Drone darf keinen Drohnenslot
  fressen). Und der Enforcer ist das erste Datenblatt, dessen Menü WAFFEN und SUPPORT-SYSTEME mischt
  — `game/battlesuit_wargear.py`; **die drei Systeme, die im ERSTEN Menü die Burst Cannon ersetzen,
  sind nicht modellierbar** (`WargearOption` tauscht Waffe gegen Waffe), sie stehen im zweiten Menü.
  Benannt, nicht still weggelassen.
- **Kroot Lone-Spear ist keine Tischgrößen-Entscheidung**: seine 90×52-mm-Ovalbasis wird per
  Gleichflächen-Kreis umgerechnet, genau wie Ghostkeel (105×70) und Riptide (120×92).
- **Getestet:** neu `test_tau_characters.py` (**145/145**) plus **24 A/B-Sonden**.
  **Eine davon brach die Suite NICHT** — genau Fehlerklasse 24: alles prüfte Hero of the Empires
  PRÄDIKAT, nichts prüfte, dass es den Trefferschritt erreicht. Der Wächter prüft jetzt den
  AUFRUFAUSDRUCK und seinen Gebrauch in der Disjunktion, und die Sonde kippt.
  **Und die volle Regression fand, was die Suite nicht fand:** `FightController` LAS
  `self.advanced_scouting`, bevor es das Attribut hatte — jeder Nahkampf-Trefferwurf im Spiel wäre
  abgestürzt. Ein Lesezugriff braucht einen Konstruktor-Slot UND einen Aufrufer, der ihn füllt;
  beide Hälften sind jetzt gepinnt, plus ein echter `FightController` ohne Ledger.
  Volle Regression **130 Suiten, ~8883 Prüfungen, 129 grün / 0 rot / 1 bekannt**, **alle fünf
  Smokes** und `selfplay.py map2` (4000 Frames) — hier keine Formalie, weil `main.py`, das
  `ActionPanel` (per Keyword angehängt, Fehlerklasse 22), `game/shooting.py`, `game/fight.py`,
  `game/movement.py` und `game/damage_resolution.py` angefasst wurden.

## Kroot und Vespid (Etappe 2)

**Kroot Hounds, Kroot Farstalkers, Vespid Stingwings, Krootox Riders, Krootox Rampagers** — fünf
Datenblätter, acht Fähigkeiten, und die **sechzehnte Extraktion**.

- **`game/objective_control.py` ist die sechzehnte Extraktion, am ZWEITEN Konsumenten wie die
  Konvention verlangt.** "Was ist die Objective Control dieses Modells JETZT" lag als
  `plagues.effective_oc()` in einem DEATH-GUARD-Modul — richtig, solange Scabrous Soulrot das
  Einzige war, das eine OC ändern konnte, und ein lügender Name in dem Moment, in dem Hunting Hounds
  dazukam (Fehlerklasse 11). `plagues.worsen_oc()` heißt jetzt nach seiner Wirkung. **Die
  REIHENFOLGE ist gedruckt und nicht beliebig:** Hunting Hounds SETZT (auf 1), Soulrot VERSCHLECHTERT
  danach — ein Hound bei einem Kroot-Charakter und zugleich Afflicted landet damit auf 1, nicht 0.
  Andersherum hätte Soulrot Hunting Hounds gegen genau einen Gegner still gelöscht.
- **Zwei Fähigkeiten auf EINEM Datenblatt mit zwei Dauern, und der Unterschied ist ein Wort.**
  Loping Pounce ist "AT THE START of your Command phase ... until the end of the turn" — also
  GERASTET: die Hounds dürfen danach von den Kroot weglaufen und trotzdem nach dem Advance chargen.
  Hunting Hounds ist "WHILE this unit is within 12"" — live. Ein Distanztest für das erste
  beantwortete eine andere Frage als die gedruckte.
- **Loping Pounce ist die DRITTE Quelle derselben Ausnahme** (nach Waaagh! und Full Throttle) und
  sitzt an genau demselben Gate in `game/charge.py`.
- **Kroot Packmates ist Vengeful Stars ohne CP** — dieselbe zweite Hälfte wörtlich, also dieselbe
  `start_reactive_shooting(restrict_to=...)`. Neu ist nur der Auslöser, und der hat VIER Bedingungen:
  Gegner-Schussphase, eine befreundete **KROOT INFANTRY**-Einheit in 6" wird BESCHOSSEN (nicht die
  Krootox selbst — sie reagieren für jemand anderen), einmal pro Zug **pro ARMEE**, und die eigene
  Salve kommt erst, NACHDEM der Feind fertig ist.
- **Kroot Linebreakers ist Crimson Harvests Geschwister** im selben Modul und am selben Charge-Haken.
  Drei echte Unterschiede: der erste Wurf ist eine HANDVOLL (ein W6 je Modell, das SELBST in
  Engagement Range steht — nicht die Truppgröße), jede 4+ ist ihr eigener D3, und der
  Battle-Shock-Test hängt an einem TOTEN MODELL, nicht an zugefügten Wunden. Der Test wird
  **VERSCHOBEN** statt inline ausgelöst: `DiceManager` hält EINEN Wurf, und die Zuteilung der Mortal
  Wounds kann noch laufen.
- **Airborne Agility ist die erste Fähigkeit, die eine Einheit FREIWILLIG vom Brett nimmt.** Sie
  braucht keinen neuen Zustand — `strategic_reserves.withdraw_to_reserves()` ist genau das, und es
  rechnet die Objective Control gleich mit neu. Die Zeitangabe ist die leicht zu verdrehende:
  **Ende des GEGNERZUGES**, also wird dem angeboten, dessen Zug gerade NICHT geendet hat.
- **Bounty Hunters ist die erste Marke, die VOR dem Spiel gesetzt wird** und die ganze Schlacht hält —
  jede andere (Guide, Doom, Advanced Scouting, Spotted) entsteht im Spiel. Pro FARSTALKER-Einheit,
  nicht pro Armee. Sie gewährt ZWEI Keywords aus EINER Kopie und liest "an attack", also beide
  Angriffsschritte.
- **`RampagerKrootoxFistsProfile` erbt** von den Krootox Fists der Riders und fügt NUR
  [SUSTAINED HITS 1] hinzu — gleicher gedruckter Name, gleiche Zahlen, ein Keyword mehr. Im Test
  gegeneinander gepinnt statt gegen Literale. Ebenso sind **Farstalker Firearm** und **T'au-tech
  Rifle** reine Umbenennungen (Kroot Rifle bzw. Pulse Rifle), also Unterklassen.
- **Die Farstalker-Hounds sind NICHT die Kroot Hounds:** Ld 7+ statt 8+, und keine der beiden
  Fähigkeiten des eigenen Datenblatts. Eine Zahl, zwei Datenblätter, zwei Klassen.
- **Vespids "if this unit contains 10 models" braucht keine Sonderbedingung** — `per_models=10`
  drückt es exakt aus: bei 5 Modellen rechnet der Deckel auf 0.
- **`Sprites/Vespid.png` lag seit Langem ungenutzt im Ordner** und ist jetzt verdrahtet; die anderen
  vier haben weiter keine Kunst, als Abwesenheit gepinnt.
- **BENANNTE GRENZE, gemessen statt weggenommen:** "1 Kroot Farstalker's Farstalker firearm can be
  replaced with ONE OF the following" ist nicht ausdrückbar. Zwei `WargearOption`s, die dieselbe
  Waffe aufgeben, teilen `build_squad()`s Cursor — das macht sie ÜBERSCHNEIDUNGSFREI (sie landen auf
  verschiedenen Modellen), nicht EXKLUSIV. Auf einer Ein-Modell-Zeile fallen die zwei Lesarten
  zusammen (deshalb kommt das Sechser-Menü des Enforcers ohne aus), bei neun Modellen nicht. Ein
  Build kann derzeit beide Sonderwaffen nehmen; im Test als KNOWN LIMITATION gepinnt.
- **Getestet:** neu `test_tau_kroot_and_vespid.py` (**115/115**) plus **29 A/B-Sonden**.
  **ZWEI davon brachen die Suite zunächst nicht** — beide Male, weil eine ZWEITE Bedingung die
  geprüfte verdeckte: der Nicht-Charakter im Hunting-Hounds-Test war auch kein KROOT, und die
  Nicht-Kroot-Einheiten im Packmates-Test standen außer Reichweite. Beide Negativfälle isolieren
  jetzt genau eine Bedingung, und beide Sonden kippen. Volle Regression **131 Suiten, ~9001
  Prüfungen, 130 grün / 0 rot / 1 bekannt**, alle fünf Smokes und `selfplay.py map2` (4000 Frames).
- **Der Shaper-Pin hat funktioniert:** `test_kroot_shapers.py` hielt fest, dass Kroot Farstalkers auf
  allen drei LEADER-Zeilen steht und KEIN Datenblatt hat. Etappe 2 machte die Zeile rot — genau die
  sichtbare Änderung, für die sie gesetzt war; sie prüft jetzt die Paarung in beide Richtungen.

## Die zwei Walker (Etappe 3)

**Broadside Battlesuits und Crisis Fireknife Battlesuits** — zwei Datenblätter, vier Fähigkeiten,
eine geschlossene hängende Referenz und **ein echter Fehler, den dieser Schwung selbst gefunden hat**.

- **`MissilePodProfile` hatte die BS des DRONE fest verdrahtet ("5+"), und das war ein Fehler, den
  Etappe 1b eingebaut hat.** Unsichtbar, solange nur Drohnen und die drohnengetragenen Pods des
  Riptide ihn benutzten; falsch in dem Moment, in dem ein BATTLESUIT einen trägt. Der Commander in
  Enforcer Battlesuit druckt BS3+, die Crisis Fireknife BS4+ — beide schossen still mit 5+. Die
  Basisklasse ist jetzt die gedruckte Zeile OHNE Override, `DroneMissilePodProfile` erbt und setzt
  die 5+ des Drohnen-Datenblatts. Im Test in alle drei Richtungen gepinnt (Enforcer, Fireknife,
  Riptide).
- **Advanced Armour ist die ERSTE bedingte Feel No Pain dieser Engine.** Jede andere Quelle gewährt
  eine Schwelle gegen JEDE verlorene Wunde; diese gilt nur gegen **Mortal Wounds**, und mit 4+ ist
  sie die beste Schwelle überhaupt hier — die Bedingung falsch zu lesen gäbe drei Broadsides ein 4+
  gegen alles. `current_feel_no_pain()` bekam dafür ein `mortal`-Flag, gesetzt von
  `MortalWoundAllocationSession` ALLEIN (die IST der Mortal-Wound-Pfad, 06.02), also bedeutet jeder
  andere Aufrufer unverändert dasselbe.
- **Fireknife ist die SECHSTE `reroll_scope`-Quelle** und ein Musterbeispiel der Form: eine
  automatische 1er-Wiederholung PLUS "you can re-roll the Hit roll **instead**". "Instead" macht sie
  zu Alternativen, also darf "nur Fehlschläge" NICHT angeboten werden. **"At its Starting Strength"
  zählt MODELLE, nicht Wunden** — ein Riptide mit einer Wunde von vierzehn ist noch auf voller
  Stärke; "unverwundet" ist die naheliegende falsche Lesart und hat eine eigene Testzeile.
- **Weapon Support System steht jetzt DREIMAL gedruckt, in zwei Rollen:** als WARGEAR auf Riptide,
  Enforcer und Broadside, als UNIT-Fähigkeit auf der Crisis Fireknife (und als "Inescapable
  Accuracy" bei den Dark Reapers). Genau dafür heißt das Feld `ignores_hit_modifiers` nach der
  WIRKUNG statt nach einem Datenblatt.
- **Crisis Fireknife schließt eine hängende Referenz**, die seit dem Bau der T'au in der Punkteliste
  stand: DREI `leads`-Tabellen (Farsight, Coldstar, Enforcer) nennen sie, `can_attach()` liest diese
  Tabelle — und bis jetzt zeigte sie ins Leere. Alle drei Paarungen sind gepinnt.
- **Der Broadside ist das einzige Battlesuit hier OHNE FLY** (und ohne Deep Strike) — gedruckt, nicht
  vergessen: er ist eine schwere Waffenplattform, und das fehlende Keyword sagt das.
- **`Gear(all_models=True)` erreicht `drone_options()`**, weil dieses Datenblatt als erstes
  "ANY NUMBER OF MODELS can each be equipped" druckt statt "this model can be equipped" — jedes
  frühere T'au-Menü gehörte einem Charakter. Additiv, Default unverändert.
- **Zwei printed rows namens "Twin smart missile system"** unterscheiden sich in genau einer Zahl
  (A4 gegen A3) → zwei Klassen, gegeneinander gepinnt.
- **BENANNTE GRENZE, dieselbe wie bei den Farstalkern:** die gedruckte Fußnote "no model can be
  equipped with BOTH a twin plasma rifle and twin smart missile system" ist nicht ausdrückbar —
  `Gear` kennt keine gegenseitige Ausschließung. Gemessen und als KNOWN LIMITATION gepinnt.
- **Getestet:** neu `test_tau_walkers.py` (**72/72**) plus **19 A/B-Sonden**. **Eine brach zunächst
  nicht** — sie entfernte das `mortal`-Argument aus `FeelNoPainRoll`s eigenem Aufruf, während die
  Suite `current_feel_no_pain()` nur direkt rief; die Verrohrung dazwischen war ungeprüft (zum
  dritten Mal Fehlerklasse 24 in diesem Projekt). Jetzt läuft die Prüfung durch einen echten
  `FeelNoPainRoll` und eine echte `MortalWoundAllocationSession`, und die Sonde kippt. Volle
  Regression **132 Suiten, ~9073 Prüfungen, 131 grün / 0 rot / 1 bekannt**, alle fünf Smokes und
  `selfplay.py map2` (4000 Frames).

## Die drei Fahrzeuge (Etappe 4 — damit ist der T'au-Nachzug fertig)

**Hammerhead Gunship, Sky Ray Gunship, Piranhas.** Mit ihnen sind **alle 19 engine-nativen
fehlenden T'au-Datenblätter gebaut**; T'au steht bei 33 von 40 (die übrigen 7 sind die bewusst
ausgelassenen Aircraft, Titanic und Fortifications plus Forge World).

- **Der Sky Ray ERBT vom Hammerhead** — identische Charakteristiken, identische Damaged-Stufe,
  gleiche Basis. Was ihn unterscheidet, ist MARKERLIGHT und **welche der beiden Reroll-Fähigkeiten
  er druckt**. Deshalb schaltet die Unterklasse `armour_hunter` ausdrücklich AUS: eine geerbte Flagge
  stehen zu lassen gäbe ihm einen Bonus, den sein Datenblatt nicht druckt. Genau das war eine der
  zwei A/B-Sonden, die zunächst NICHT brachen — die Suite prüfte nur, was der Hammerhead HAT.
- **Ein Keyword Unterschied, und es ist keine Kosmetik:** die Twin Pulse Carbine des Hammerhead
  druckt [TWIN-LINKED] ALLEIN, die von Sky Ray, Piranha und Devilfish auch [ASSAULT]. [ASSAULT] ist
  das, was Schießen nach dem Advance erlaubt (24.04) — eine geteilte Klasse hätte einen Hammerhead
  still advancen und schießen lassen. Eigene Klasse, gegen die andere gepinnt.
- **Armour Hunter ist Tank Hunters mit fehlender WUND-Hälfte.** Beide Tank-Hunters-Träger geben +1
  auf Treffer UND Wunde; der Hammerhead nur auf den Treffer. Eine geteilte Flagge hätte ihm still
  einen +1-Wundbonus gegeben — genau die Falle, die `tank_hunters_modifiers()` schon einmal zwischen
  Ork- und Death-Guard-Fassung dokumentiert. Den KEYWORD-Test (`is_monster_or_vehicle_unit()`) teilt
  es sehr wohl, damit die beiden sich nie uneinig sind, was ein Fahrzeug ist.
- **Targeting Array ist Command Re-roll ohne CP** — ein Würfel, vom Spieler gewählt, neu geworfen.
  Also **derselbe Panel-Knopf-Ablauf** (`can_use` → `start` → `choose_die`), der DRITTE
  Würfelauswahl-Modus in `main.py`s Klick-Routing, und drei gedruckte Unterschiede: kein Preis und
  keine 15.01-Buchführung, die RESSOURCE ist die AKTIVIERUNG ("each time this model is selected to
  shoot"), und nur **Hit ODER Wound** — nicht die acht Wurfarten, die Command Re-roll erreicht.
  Das Ledger öffnet `start_shooting()` und schließt `_actually_finish_squad()`, dieselbe Naht, an der
  19.04s Fenster zugeht.
- **Velocity Tracker ist ein GEWÖHNLICHES failures-or-whole-Angebot** — "you can re-roll the Hit
  roll", ohne Automatik-1er-Klausel, also ausdrücklich KEIN `reroll_scope`-Eintrag. Als Abwesenheit
  gepinnt, weil sich das nur dort zeigt.
- **Drone Harassment Tactics brauchte gar nichts Neues**: `start_forced_roll()` ist der
  "eine Regel ordnet einen Test außer der Reihe an"-Einstieg, den es seit Neocapacitor Shields gibt.
  Die 12" werden vom TRUPP gemessen ("within 12" of this UNIT") — Gegensatz zu Root of Honour, dessen
  "of this model" vom Träger misst, und der Unterschied ist ein Wort.
- **`Sprites/Skyray.png` lag seit Langem ungenutzt im Ordner** und ist jetzt verdrahtet — die zweite
  Waise nach `Vespid.png`. Hammerhead und Piranhas haben keine Kunst; Abwesenheit gepinnt.
- **Ein bestehender Wächter wurde rot, und zu Recht:** `test_unmodified_six_ui.py` pinnte den
  Ausdruck `command_reroll_controller.selecting_die or unmodified_six_controller.selecting_die`
  wörtlich. Der dritte Modus machte ihn ungültig — genau dafür stand die Zeile da. Sie prüft jetzt
  jeden Modus EINZELN, sodass ein vierter, der das Würfelpanel nicht erreicht, genauso auffällt.
- **Getestet:** neu `test_tau_vehicles.py` (**97/97**) plus **21 A/B-Sonden**. **Zwei brachen
  zunächst nicht**, beide aus demselben Grund wie in Etappe 2: eine zweite Bedingung verdeckte die
  geprüfte (die befreundete Einheit im Drone-Harassment-Test stand außer Reichweite; und dass der Sky
  Ray Armour Hunter NICHT hat, prüfte niemand). Beide sind isoliert, beide Sonden kippen. Volle
  Regression **133 Suiten, ~9172 Prüfungen, 132 grün / 0 rot / 1 bekannt**, alle fünf Smokes und
  `selfplay.py map2` (4000 Frames).

## T'au-Sprites vollständig

**Alle 33 T'au-Datenblätter haben jetzt Kunst** (User: "Die Sprites sind jetzt da"). Die siebzehn
Abwesenheits-Pins der vier Etappen sind umgedreht — genau die sichtbare Änderung, für die sie
gesetzt waren; sie prüfen jetzt am MODELL statt an der Tabelle, weil `sprites.sprite_for()` die
Datei wirklich lädt und ein Schlüssel, der auf keine Datei auflöst, sonst unbemerkt bliebe.

- **Vier Dateinamen weichen ab, und der ORDNER gewinnt** — dieselbe Entscheidung, die
  `Ghostkheel`, `Starsythe`, `Skyray` und `Vespid` schon festhalten: `Broadside Battlesuites`
  (Tippfehler wörtlich übernommen), `Dark Strider` (zwei Wörter), `Piranha` (Singular gegen den
  pluralen Datenblattnamen), und die zwei mit `Tau `-Präfix. Jede einzeln als Testzeile
  ausgeschrieben, damit ein späteres Umbenennen eine sichtbare Änderung ist.
- **Zwei User-Zuweisungen statt eigener Dateien:**
  - *"für alle Kroot characters Kroot Flesh Shaper.png"* — die drei Shaper teilen sich ein Bild.
    Der **Kroot Lone-Spear ist zwar auch ein CHARACTER, behält aber seine eigene Kunst**, weil es
    sie gibt; als eigene Testzeile festgehalten, damit der Sonderfall nicht wie ein Versehen aussieht.
  - *"für Farstalkers die normalen Kroot Sprites"* — Kill-broker und die neun Farstalker nehmen die
    Kroot-Carnivores-Kunst.
- **Kroot Farstalkers ist der erste Fall mit DREI Modellzeilen und ZWEI Bildern**, und die zwei
  Kroot Hounds darin brauchen `MODEL_SPRITE_KEYS` (vierter Eintrag dieser Art): der Trupp heißt
  "1 Kroot Farstalkers 1", also matcht der Schlüssel "Kroot Hounds" ihn nie — genau der Fall, für den
  diese Tabelle existiert. Sie bekommen dasselbe Bild wie das eigenständige Kroot-Hounds-Datenblatt,
  im Test gegeneinander gepinnt.
- **Getestet:** die fünf Etappen-Suiten von zusammen 416 auf **575 Prüfungen** (jede Modellzeile
  einzeln, nicht nur `models[0]`, damit eine Zeile ohne Kunst nicht hinter dem ersten Modell
  verschwindet). Volle Regression **136 Suiten, ~9568 Prüfungen, 135 grün / 0 rot / 1 bekannt**,
  dazu `smoke_pregame.py`, `smoke_log_input.py`, `smoke_setup_screens.py` und `selfplay.py map2` —
  hier keine Formalie, weil `game/sprites.py` pro Frame in der Renderkette läuft.
