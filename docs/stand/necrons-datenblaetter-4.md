# Necrons: Datenblatt-Nachzug (4)

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die restlichen Necron-Datenblätter — Fortsetzung

### Etappe 9 — Monolith und The Silent King, und damit ist der Nachzug fertig

**31 von 31 Bauzielen; die Fraktion steht bei 46 von 64.** Die zwei größten
Einzelstücke der Fraktion: der Monolith ist das ERSTE TITANIC- und TOWERING-Modell dieser Engine,
The Silent King die erste Einheit, deren EIN Datenblatt ZWEI Profile mit verschiedenen Wunden,
verschiedenen Basen und verschiedenen Keyword-Leisten druckt.

#### Die Basisgröße des Monolithen ist eine NEUE Entscheidung, kein Präzedenzfall

Gedruckt ⌀160mm = r 3.150". Der **Defiler druckt DIESELBEN 160 mm und spielt auf 2.1"** — und
2.1" ist die Obergrenze des ganzen Repos, auf der Falcon, Battlewagon, Kill Rig, Doomsday Ark und
die drei Stage-8-Skimmer alle exakt sitzen. **User-Entscheidung: „2.5", dazwischen"** — also
KEINER der beiden vorhandenen Antworten. 2.1" hätte das größte Modell des Spiels genauso breit
gemacht wie einen Falcon, 3.150" anderthalbmal so breit wie alles andere. Beide verworfenen Werte
stehen im Docstring und in der Suite neben dem gewählten, damit die Begründung den Pin überlebt.

Szarekh (⌀100mm) und der Triarchal Menhir (⌀50mm) sind dagegen reine TRANSKRIPTIONEN — hier gilt
keine Grav-Panzer-Regel, und die Suite misst sie gegen die Millimeter statt gegen eine Zahl.
`verify_rules_vs_engine.py` bekommt dadurch **genau EINE** neue Zeile, nicht drei.

#### Waffen: acht neue Namen, und der FORK, den Etappe 8 namentlich vorhergesagt hat

Der Kollisions-Sweep über den ganzen Korpus: acht der neun gedruckten Namen stehen NIRGENDS sonst.
Der neunte ist `Armoured bulk` — die drei Grav-Skimmer drucken „Melee 3 4+ 6 0 1", der Menhir
„Melee 1 4+ 4 0 1" unter DEMSELBEN Namen. `game/weapons.py`s Stage-8-Block sagt wörtlich „that one
IS a fork, and stage 9 has to make it", und `MenhirArmouredBulkProfile` ist sie: **Unterklasse der
geteilten Zeile, mit genau zwei überschriebenen Feldern**, im Test GEGENEINANDER gepinnt
(„identisch bis auf Attacks und Strength" ist die eigentliche Zusicherung, und zwei unabhängige
Kopien mit denselben Zahlen erfüllen jeden literalweisen Test, während sie aufhören, die geteilte
Zeile mitzuführen).

**NULL Pro-Waffen-Skill-Overrides in dieser Etappe**, als MENGE gepinnt — der Gegensatz zu Etappe 8,
die zwei brauchte, weil die Catacomb Command Barge sich selbst widersprach. Hier ist jedes der drei
Profile mit seinen eigenen Zeilen einig (Monolith BS3+/WS2+, Szarekh BS2+/WS2+, Menhir BS2+/WS4+).

#### `game/charge_reroll.py` — 51. Extraktion, am ZWEITEN Träger

„You can re-roll Charge rolls made for this unit" drucken jetzt zwei Datenblätter. Die PRÄDIKATE
könnten kaum verschiedener sein — die Triarch Praetorians fragen rule 19.04s
`unit_wide_ability()`, Phaeron of the Blades eine AURA —, und alles davor ist identisch: das
Ein-Augenblick-Fenster VOR `acknowledge()`, der Einmal-pro-Wurf-Claim, das Alles-oder-Nichts, und
die zweiseitige deterministische KI-Antwort. `relentless_combatants.py` ist jetzt eine Unterklasse
und re-exportiert `MAX_CHARGE_ROLL_TOTAL`; **seine Suite blieb bei 143/143 ohne eine einzige
Anpassung**, was der Konstruktions-Beleg dafür ist, dass die Extraktion verhaltensneutral war.
Ein Träger besitzt genau zwei Knöpfe (`LABEL`, `applies()`), als Klassenattribute, damit ein
Vergessen LAUT bei der Konstruktion scheitert statt still ein namenloses Angebot zu erzeugen.

#### Voice of the Triarch: die WAHL lebt auf dem SQUAD, nicht im Controller

Drei austauschbare Auren, eine pro Schlachtrunde gewählt. Die vier Leser sind
`shooting.py`/`fight.py`s Treffer- und Wundschritte, `coldstar.effective_movement_in()` und
`game/charge_reroll.py` — und **zwei davon bekommen ein MODELL bzw. ein SQUAD und gar kein Brett**.
Einen Controller dorthin zu fädeln wäre der „turn_tracker durch elf Aufrufstellen"-Fehler, den
dieses Repo zweimal aufgeschrieben hat. Also: der Controller besitzt, WANN sich die Wahl ändert,
`Squad.triarch_ability` trägt, WAS gewählt wurde, und ein Per-Frame-Sweep stempelt daraus
`Squad.triarch_auras_active` — dieselbe Teilung wie `Squad.montka_killing_blow`, ein Stempel und
viele Leser.

- **Die WAHL wird GESPEICHERT, die ABLEITUNG nicht.** `triarch_ability` steht in
  `activation_state.SQUAD_FLAGS` und ist dort der **einzige nicht-boolesche Eintrag**: die Capture
  filtert auf Truthiness und restauriert per `setattr`, ein String läuft also unverändert durch
  JSON. Ein F9 dürfte nicht still ändern, unter welcher Aura eine Armee steht. Der abgeleitete
  Satz gehört nach `SQUAD_FLAGS_EXCLUDED`, weil der nächste Frame ihn neu stempelt.
- **Gemessen vom SZAREKH-MODELL, nicht von der Einheit** — der gedruckte Text sagt „within 6" of
  this unit's SZAREKH MODEL", und die Einheit trägt zwei Menhirs, die irgendwo in Kohärenz stehen
  dürfen. Eine Sonde, die von der EINHEIT misst, beißt.
- **Die eigene Einheit des Trägers ist gedeckt** („a friendly NECRONS unit", nicht „another") —
  dieselbe Lesart, die Carrier Wave eine Etappe früher genommen hat, und hier gepinnt statt dem
  Zufall überlassen.
- **Die MONSTER-Ausnahme ist auf dieser Armee real**: die C'tan Shards sind NECRONS MONSTER, ein
  C'tan neben Szarekh bekommt also KEINE der drei.

#### Die VIERTE Aura unterscheidet sich in EINEM gedruckten Wort

„The Silent King" (+1 Ld) steht NICHT auf der Voice-Liste, ist also immer an — und druckt als
einzige der vier **keine MONSTER-Ausnahme**. Ein C'tan bekommt sie, und die drei anderen nicht.
Die Suite pinnt das von beiden Seiten und zählt die Ausnahme im Korpus (dreimal, nicht viermal),
weil der naheliegende Fehler ist, ein Prädikat für alle vier zu teilen.
**„Improve by 1" SUBTRAHIERT**, weil Leadership hier eine N+-Schwelle ist — dieselbe Richtung, die
Admired Leader schon nimmt, und das Gegenteil von Scabrous Soulrot zwei Zeilen weiter.

#### Zwei „Damaged:"-Stufen, und die zweite hat ZWEI verschiedene SUBJEKTE

Das generische `damaged_threshold` beantwortet nur „−1 auf den Trefferwurf, gemessen an den EIGENEN
Wunden dieses Modells". Beide Stufen dieser Etappe brauchen mehr:

- **Der Monolith** zieht zusätzlich **4 von der Objective Control** ab → `damaged_oc_penalty`, ein
  DRITTER Worsener in `effective_oc()`, neben Scabrous Soulrot und auf 0 geklammert.
- **The Silent King** halbiert „that MODEL's weapons" (nur Szarekhs) und gibt „each time THIS UNIT
  makes an attack" −1 (Szarekh UND beiden Menhirs, **an SZAREKHS Wunden gekoppelt**). Ein Menhir
  auf vollen Wunden nimmt die Strafe also mit, und `_damaged_modifier()` nach dem Menhir gefragt
  antwortet nein. Deshalb `game/damaged_attacks.py` als unit-weite Lesart, von beiden
  Angriffsschritten NEBEN der pro-Modell-Frage gelesen, und so geordnet, dass sie sich auf Szarekh
  nie zu −2 stapeln. **Halbieren rundet AUF**, sonst löscht es eine 1-Angriffs-Waffe.

#### Eternity Gate: die VIERTE Ankunftsart

Der Homing Beacon ist die nächste Form („set up within X of the bearer instead of the board edge")
und liefert die drei Nähte. NEU ist die Distanz, die der Ersatz NENNT: jede andere Ankunft nennt
ein BAND (8", 9", 6"), diese einen ZUSTAND — „unengaged". Rule 03.04 definiert ihn, also ist die
Mindestdistanz `squad.ENGAGEMENT_RANGE_IN` und **kein viertes Literal**; bewegt sich die Lesart von
03.04, bewegt sich dies mit.

- **Der Deployment-Zone-Verzicht ist GEDRUCKT, nicht geerbt.** Der Monolith HAT [DEEP STRIKE], die
  Einheit, die durch das Tor kommt, braucht es nicht — ihn am PASSAGIER abzulesen ließe die
  Fähigkeit nur für Einheiten funktionieren, die sie nie gebraucht hätten.
- **„Excluding the first battle round" ist NICHT redundant**, obwohl 20.03 Runde-1-Ankünfte ohnehin
  verbietet: der Unterschied ist die ENTNAHME. Wer nur das Ankunftstor prüft, lässt einen Spieler
  in Runde 1 eine Einheit vom Brett ziehen und danach feststellen, dass sie erst in Runde 2
  zurückkann. Das Tor wird geprüft, BEVOR irgendetwas entfernt wird.
- **„NECRONS INFANTRY" ist all(), nicht any()** — sonst schleppt eine Infanterie-Komponente ein
  Fahrzeug durch das Tor.
- **Die KI LEHNT AB, und das ist benannt**: das Tor zieht eine Einheit vom Brett, um sie woanders
  zurückzubringen — eine Frage über den Plan der ganzen Armee, und `ai/agent_driver.py` hat keine
  Eingabe, die ein gutes von einem schlechten Gate unterscheiden könnte. Dieselbe Entscheidung, die
  `enh_solid_image_projection.py` für dieselbe Form der Fähigkeit protokolliert.

#### Triarchal Menhirs: die erste VERKETTETE Zerstörung dieser Engine

Nichts, was die fünf gebauten Armeen drucken, tötet ein Modell, WEIL ein anderes gestorben ist —
es gibt also keinen Fold, dem man beitreten könnte. Sie läuft im Todes-Sweep VOR
`remove_dead_models()`, und das ist regelförmig statt bequem: sie MUSS Szarekh tot sehen, während
die Menhirs noch stehen, also will sie genau das Vor-Sweep-Fenster, um das Fehlerklasse 12 sonst
geht. **Der Lebendigkeitstest ist `is_dead()`, nicht `not squad.models`** — die Einheit ist ja
nicht ausgelöscht. Und sie feuert NICHT rückwärts: zwei tote Menhirs lassen Szarekh weiterkämpfen.
- **Ein eigener Fehler, beim Schreiben gefunden:** `Squad` hat gar kein `starting_models`, nur
  einen `starting_model_COUNT`. Die „hatte diese Einheit je einen Szarekh"-Hälfte liest deshalb
  `models` PLUS `destroyed_models` — die Nur-Live-Fassung hätte nach dem Sweep entschieden, das
  Datenblatt habe nie einen gedruckt, und die Menhirs verschont. Genau das Versagen, das die
  Sweep-Ordnung unmöglich machen soll, und es wäre erst einen Frame später aufgefallen.

#### Getestet

Neu `test_necron_titans.py` (**219/219**, zehn Abschnitte) plus `ab_necron_titans.py`
(**37 Sonden, 39 Sondenläufe über vier Suiten, alle beißend, keine stürzt ab**).
`test_necron_triarch.py` **143/143** (der andere Träger der Extraktion, ohne eine Anpassung),
`test_necron_datasheets.py` **167/167** (Zählpins 44 → 46),
`test_death_guard_datasheets.py` **201/201**.

**SIEBEN Sondenläufe bissen zunächst NICHT, und SECHS waren echte Lücken im TEST**
(Fehlerklasse 24) — drei davon in derselben Form, die dieses Repo am häufigsten notiert:
**der Test fuhr den HELFER direkt statt der Naht, die ihn wirklich liest.**

1. **Phaeron of the Blades** wurde über `blades_adjusted_weapon()` gemessen, nie durch `fight.py`s
   eigene Adjuster-Kette — die Sonde, die die Aufrufstelle entfernte, meldete NO BITE.
2. **Die unit-weite Damaged-Hälfte** über `covers_model()`, nie durch `_damaged_modifier()`, das
   beide Angriffsschritte wirklich lesen.
3. **Zwei Eternity-Gate-Klauseln** über QUELL-STRINGS, die ein `if False:` überleben — der
   Zonen-Verzicht und die Platzierungsprüfung. Jetzt durch einen echten `IngressController`.
4. **Die Waffentabelle maß nie, auf welcher SEITE eine Waffe kämpft.** Den Staff of Stars auf
   MELEE zu drehen ließ jede Zahl und jedes Keyword intakt, die ganze Tabelle bestand also gegen
   eine Waffe, die nicht schießen kann.
5. **Zur `any()`/`all()`-Lesart von „NECRONS INFANTRY" gab es keine gemischte Einheit** — kein
   Datenblatt baut eine, sie musste konstruiert werden.
6. **Der siebte ist ein DEKLARIERTER Nicht-Beißer und ein Befund über die DATEN:** der
   `triarchal_menhir`-Filter lässt sich nicht von „nimm alles, was noch steht" unterscheiden, weil
   die Regel erst feuert, wenn Szarekh unten ist — und dann ist jedes lebende Modell der Einheit
   ein Menhir. Mit seiner Messung in `ab_necron_titans.py` eingetragen, wie der T'au-Audit und
   Etappe 8 es vormachen.

**Eine Sonde ließ eine Suite ABSTÜRZEN statt sie rot zu machen** — vierundzwanzigste Instanz
dieser Lehre. Nimmt man `relentless_combatants.py` von seiner neuen Basis, bleibt ein Konstruktor
ohne Schlüsselwortargumente, und ZWEI nackte Aufrufe in `test_necron_triarch.py` brachen den Lauf
ab, bevor eine Prüfung berichtete. Beide sind jetzt gekapselt; die Sonde meldet **neun benannte
rote Zeilen**.

**Drei fremde Pins wurden zu Recht rot und sind UMGEDREHT statt aufgeweicht:**
`test_death_guard_datasheets.py` behauptete „no other profile in the engine reaches T12" (der
Monolith ist T13) und trug daneben ein lügendes Label („Defiler W18/OC5 — the largest in the
engine"); beide Sweeps bleiben, nennen jetzt ihre Ausnahmen und haben **sofort Szarekh mit OC 6**
gefunden. `test_aeldari_detachment_stratagems.py` pinnte das Schlüsselwort `if` an einem
Ingress-Zweig, den der vierte Ankunftsmodus zu `elif` gemacht hat — Formatierung statt Bedeutung;
er matcht jetzt den Aufruf plus seinen Rumpf. Und `test_ai_mode.py` meldete, dass
`EternityGateController` `auto_players` nimmt und nie liest — mir fehlte das Angebot.

#### Bewusst offen

`armies/necrons.json` unangetastet, beide *dormant by roster*; `auto_players` in jedem neuen
Controller, aber KEINE `ai/agent_driver.py`-Urteile. **Der KI-Negativraum-Sweep matcht einen IMPORT
oder einen ATTRIBUTZUGRIFF, nie das nackte Wort** — „charge_reroll" ist Teilstring von
`_charge_reroll_verdict()`, einer VORBESTEHENDEN Funktion dort, also derselbe Fehltreffer, den die
Etappen 5 und 6 mit „Canoptek" und „C'tan" umgehen mussten.

**TOWERING und FRAME sind NICHT modelliert** und in `abilities_text` als solche markiert: TOWERING
ist eine Sichtbarkeitsregel („can be seen over other models"), und diese Engine hat gar keine
Vertikalität — dieselbe dokumentierte Vereinfachung, die Plunging Fire (22.05) fehlen lässt. FRAME
ist eine Basisform-Notiz ohne Regel. **Supreme Commander** („must be your Warlord") ist ein
belegter No-op, wie bei Farsight und Shadowsun.
