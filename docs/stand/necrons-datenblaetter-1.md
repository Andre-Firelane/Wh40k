# Necrons: Datenblatt-Nachzug (1)

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die restlichen Necron-Datenblätter (32 Stück, neun Etappen)

**STAND: FERTIG. Alle 31 Bauziele gebaut, Etappen 0-9.** `MISSING_NECRONS` in
`fetch_datasheet_rules.py` ist leer von Bauzielen; was dort steht, ist der
bewusst außerhalb des Umfangs liegende Schwanz (Doom Scythe, Night Scythe,
Convergence Of Dominion), der trotzdem im Korpus mitgeschnappt wird.
**Die Zahl 32 ist unterwegs auf 31 gefallen**, weil die Night Scythe auf
User-Entscheidung gestrichen wurde („weil aircraft”) — siehe Etappe 8.
**E9 war Monolith (das erste TITANIC) und The Silent King.** Der Silent King steht
in jener Tabelle bei den Charakteren und kam trotzdem zuletzt: er ist als einziger
der fünf **kein Leader** (er druckt gar keinen `## Leader`-Abschnitt) und mit zwei
Profilen, drei tauschbaren Auren und einer Damaged-Stufe das größte Einzelstück.

**Die Necrons waren mit 15 von 64 Datenblättern die am schlechtesten abgedeckte gebaute
Fraktion** (T'au 33/40, Aeldari 54/99). Der User hat 27 Sprite-Dateien nach
`Sprites/Necrons/` gelegt und dann gesagt: *"schau, an wie die letzten datasheets aus
wahapedia extrahiert wurden. keine legends keine titanischen. nur der monolith sollte als
einzige titanische einheit angelegt werden."*

**Der Umfang ist GEMESSEN**, mit derselben Subtraktion wie beim Aeldari-Nachzug: 64 Blöcke
− 15 gebaut − 12 Legends (`sLegendary`) − 5 TITANIC (`tooltip_contentTitanic` in der
KEYWORD-LEISTE, Monolith ausgenommen) − 2 (AIRCRAFT/FORTIFICATION, User-Entscheidung) =
**32**. Forge World entfernt nichts (alle vier `FW_logo2`-Träger sind ohnehin Legends oder
TITANIC). **Night Scythe bleibt DRIN** — es liest sich wie ein Aircraft und ist in 11e
keins (`VEHICLE; FLY; TRANSPORT`, ohne AIRCRAFT), genau die Sorte Annahme, die ungeprüft
ein Datenblatt gekostet hätte.

**Gemessene Waffen-Kollisionen, und sie laufen in BEIDE Richtungen:** 65 Waffennamen, 7
mit Namenskollision — aber die MEISTEN sind byte-gleich und müssen **GETEILT** werden
(`Overlord's blade`, `Gauss cannon`, `Gauss flayer array`, `Particle caster`, `Staff of
light`, die Fahrzeug-`Armoured bulk`); nur ~3-4 sind echte Forks (der Menhir-`Armoured
bulk` A1 S4, die `Close combat weapon` in drei Ausprägungen). **Die erste Fassung des
Plans las alle sieben als Forks** — sie zu klonen wäre der inverse Fehler gewesen, und
`test_necron_datasheets.py` pinnt die Familien GEGENEINANDER als verschieden, also hätte
eine identische vierte den Pin erfüllt und still dupliziert.

### Etappe 0 — Korpus, und die TITANIC-Reparatur, die vorgezogen werden musste

`MISSING_NECRONS` in `fetch_datasheet_rules.py` (32 + Doom Scythe + Convergence Of
Dominion). `rules/necrons/` **15 → 49**, zwei `--offline`-Läufe byte-identisch.

**Der Monolith wäre das ERSTE TITANIC-Datenblatt dieser Engine, und das Versprechen hielt
nicht.** Ein Dutzend Klauseln stehen als *"documented no-op"* da, mehrere mit dem
wörtlichen *"it starts working by itself the day a TITANIC datasheet exists"*. Gemessen:
**TITANIC wurde an DREI unvereinbaren Stellen beantwortet**, und eine davon war eine stille
Lüge — **vier Stellen lasen `getattr(profile, "titanic", False)` bzw. `_flag(profile,
"titanic")`, ein Feld, das `UnitProfile` gar nicht deklariert** (`game/actions.py` zweimal,
`game/elemental_ensnarement.py`, `game/structural_collapse.py`). Unbedingt False, von innen
verdrahtet aussehend. Byte-für-byte der Fehler, den `game/wraith_construct.py`s Docstring
für `spiritseer.py` bereits anklagt.

- **Neu `game/titanic.py`** als EINE Definition (Keyword-Leiste über
  `unit_has_datasheet_keyword()`); `wraith_construct.py` re-exportiert, seine Aufrufer
  bewegen sich nicht. Es liegt NICHT dort, weil vier der Leser Necron-, Death-Guard- und
  Kernregel-Stellen sind, die mit Wraith Constructs nichts zu tun haben (Fehlerklasse 11).
- **VORGEZOGEN aus Etappe 9**, weil Nekrosor Ammentar (Etappe 3) *"excluding MONSTER and
  TITANIC units"* druckt und damit sechs Etappen vor dem Monolith gegen diesen Mechanismus
  schreibt.
- **Gemessen, dass es etwas repariert:** `test_support_weapon_platforms.py` **163 → 166** —
  die drei Zeilen der D-cannon-Klausel gegen ein TITANIC-Ziel waren rot, weil Staging UND
  Leser dasselbe nicht existierende Feld lasen und sich einig falsch waren.
- **Zwei Test-Stagings mussten mitziehen** (`test_actions.py`,
  `test_support_weapon_platforms.py`): beide inszenierten TITANIC durch ein
  `titanic`-Attribut auf einer Wegwerf-Profilkopie, also die VOR-FIX-Welt.
- **NICHT alles davon ist dormant:** zwei der vier Stellen sind CROSS-FACTION-Leser auf
  ausgelieferten Rostern (Elemental Ensnarement ist Aeldari, die D-cannon-Klausel ebenso).
- **Eigener Messfehler, notiert weil er sich wiederholen wird:** mein erster Sweep grepte
  `\.titanic\b` und fand nur Kommentare — der Feldname ist dort ein STRING-ARGUMENT, kein
  Attributzugriff.
- Neu `test_titanic_reader.py` (**19/19**, Abschnitt 4 eine MENGENDIFFERENZ per AST: kein
  Modul darf `titanic` je wieder als Profilfeld lesen) plus `ab_titanic_reader.py`
  (**6 Sonden, alle beißend**). **Zwei bissen zuerst nicht, beide Befunde über den TEST:**
  16.01s ENGAGED-Ausnahme war gar nicht gemessen (nur die Schuss-Hälfte), und zur
  Aeldari-Ensnarement-Ausnahme gab es keine Prüfung.

### Etappe 1 — die Crypteks (Chronomancer, Psychomancer, Orikan The Diviner)

**Vorher eine 19.01-Korrektur, die die Etappe erzwungen hat:** Plasmancer und Technomancer
drucken beide `CORE: Support`, ihre Profile setzten aber `leader = True`. Reproduziert: eine
Necron-Warriors-Einheit mit einem Overlord konnte KEINEN Technomancer mehr aufnehmen —
`can_attach()` meldete *"already has a leader unit attached ... 19.01 allows only one of
each"*, obwohl ein Leader und ein Support nebeneinander erlaubt sind. Gemessen sicher: alle
Necron-Suiten grün, und der Golden Master bewegt **genau sechs Zeilen**, alle nur das
Rollen-Label. Die Paarungen ziehen von `leads=` auf `supports=` nach.

**Die Abteilung der Fähigkeiten — knapp ein Viertel ist eine FALTE:**
- **Chronometron** = `game/tactical_acumen.py`/`fire_and_fade.py` zum DRITTEN Mal, 6" → 5".
  Der eine echte Unterschied ist der SUBJEKT: "this model's UNIT", also 19.03s
  Any-Model-Pooling statt `leader_ability()` — sonst verlöre ein allein stehender
  Chronomancer seine eigene Fähigkeit.
- **Timesplinter Mantle** (melee −1) = ein `FightController._hit_modifiers()`-Eintrag, die
  Naht, in der `forewarned.py` schon sitzt. Melee-only, also NICHT in `shooting.py`.
- **Nightmare Shroud / Harbinger of Despair** = beide `start_forced_roll(penalty=)`, das die
  −1 schon konnte. Ein Modul, zwei Auslöser; die Aura hält eine QUEUE, weil
  `start_forced_roll()` einen Wurf zur Zeit nimmt.
- **Master Chronomancer** = ein `_better()`-Fold in `invulnerable_save.py`.
- **The Stars Are Right** ist die einzige echte Mechanik: "triple" ist ein MULTIPLIKATOR
  (A2 S4 → A6 S12, zwei Toughness-Grenzen auf einmal), und "every successful Wound roll
  scores a Critical Wound" ist in dieser Engine *die Krit-Schwelle IST die Wundschwelle*.
  Dafür bekam `fight.py` **einen** Helfer `_wound_crit()`, durch den alle vier
  Krit-Wund-Stellen laufen.

**Der wertvollste Fund der Etappe kam von einer Sonde, die NICHT biss.** Ich hatte
`squad_has_stealth()` eine dritte Quelle gegeben, weil Timesplinter Mantle *"This unit has
Stealth"* druckt und `unit_wide_ability()` wie die falsche Frage aussieht. Die Sonde, die
sie entfernte, änderte **keine einzige Antwort**: `unit_wide_ability()` delegiert an
`attached_units.unit_has_ability()`, und das ist 19.04s KOMPONENTEN-weise Lesart ("jedes
Modell IRGENDEINER noch gewährenden Komponente"). Die Quelle war redundant und ihr eigener
Docstring behauptete das Gegenteil. **Beides entfernt bzw. korrigiert** — eine Zeile, die
ihre Notwendigkeit behauptet und keine hat, ist dieselbe Klasse wie ein Kommentar, der ein
Verhalten verspricht, das kein Code einlöst.

**Der Wiring-Wächter hat zweimal zugeschlagen, und beide Male zu Recht:**
- **§18** meldete `the_stars_are_right.offer_at_start_of_fight_phase` als Schleife mit
  ungetaggtem Prompt. Richtig: das ist "JEDE berechtigte Einheit bekommt ihr eigenes
  Angebot", also `game/per_unit_offer.py`, nicht "wähle eine von mehreren". Auf einem
  ausgelieferten Roster kann es nicht beißen (Orikan ist EPIC HERO), und es ist trotzdem
  richtig geschrieben, weil die FORM das ist, was der nächste Träger erbt.
- **§21** (Insane Braverys dokumentierte Command-Phasen-Lücke) meldete den zwölften
  Auslöser und ERZWANG eine Entscheidung. Sie steht jetzt namentlich drin, samt der
  Beobachtung, dass **Nightmare Shroud der einzige der zwölf ist, der INNERHALB einer
  Command-Phase feuert** (der gegnerischen) — die dichteste an der Kante der Lücke, und der
  Punkt, an dem eine spätere Revision anfangen sollte.

**Getestet:** neu `test_necron_crypteks.py` (**116/116**, neun Abschnitte) plus
`ab_necron_crypteks.py` (**23 A/B-Sonden, alle beißend**). **Vier bissen zuerst nicht:** die
Stealth-Quelle (der Fund oben), und drei Testlücken — Nightmare Shrouds
Starting-Strength-Tor war mit nur EINEM Kandidaten nicht messbar, die Waffennamens-Klausel
war ungeprüft, und die Krit-Hälfte wurde am MODUL statt an `fight.py`s echtem `_wound_crit()`
gemessen. **Eine fünfte Sonde war ein Befund über die SONDE:** sie weitete nur einen
redundanten Early-out und meldete zu Recht NO BITE — was wirklich schiefgehen kann, ist das
FALSCHE Modell zu fragen, und so ist sie jetzt geschrieben.

Volle Regression **212 Suiten, ~18532 Prüfungen, 211 grün / 0 rot / 1 bekannt**, und
`selfplay.py map2` (1200 Frames, exit 0) — keine Formalie, weil `main()` vier neue
Controller konstruiert und keine Suite `main()` fährt (Fehlerklasse 23).

**Bewusst offen, wie bei den Aeldari:** keines der 32 steht in einer Demo-Armee
(`armies/necrons.json` unangetastet, Golden Master unbewegt außer den sechs Rollen-Zeilen),
und die KI bekommt `auto_players` in jedem neuen Controller, aber KEINE
`ai/agent_driver.py`-Urteile — als Negativraum geprüft.

### Etappe 2 — das Fußvolk (Deathmarks, Flayed Ones, Cryptothralls, Tomb Blades)

Vier Datenblätter, die NICHTS teilen außer der Fraktion — das Gegenteil von Etappe 1, wo
ein Chassis drei Charaktere trug. Der Inhalt ist deshalb fast vollständig, an welcher NAHT
jede Fähigkeit landet, und drei dieser Nähte sind neu.

**Cryptek Retinue ist eine DRITTE Anbindungsform (19.01), und fast alles dafür stand
schon.** `attach()` merged Modelle, summiert Punkte UND summiert `starting_model_count` aus
den Komponenten — was wörtlich das gedruckte *"that Bodyguard unit's Starting Strength is
increased accordingly"* ist, und das reicht weit über Buchführung hinaus: genau diese Zahl
deckelt 01.02.03 Reanimation Protocols und liest Below Half-strength. Gemessen: 11 → 13.
`pregame.py`s JOIN-Ziel und seine Auflösungsschleife sind generisch. Neu ist EIN Rollenname.
- **`attached_units.RETINUE` ist eine eigene ROLLE und nicht eine zweite Art SUPPORT**, und
  das ist der ganze Trick: 19.01s Ein-Unit-pro-ROLLE-Prüfung liefert damit das gedruckte
  *"(a unit cannot have more than one CRYPTOTHRALLS unit joined to it)"* gratis, während ein
  Cryptek und ein Retinue weiter nebeneinander attachen dürfen.
- Die einzige Bedingung, die nichts davon kennt, ist *"being led by a CRYPTEK INFANTRY
  model"*. Sie bleibt bewusst AUSSERHALB von `can_attach()` — das besitzt Regel 19.01 und
  hat kein Geschäft damit zu wissen, was ein Cryptek ist; es ist eine Bedingung des
  Declare-Battle-Formations-SCHRITTS, dieselbe Teilung, die `formations.py`s
  `support_join_errors()` für Support Artillery schon zieht.
- **`formations.join_rule_label()` ist neu, weil das Panel jetzt ZWEI gedruckte Regeln in
  derselben Überschrift zeigen kann** ("Support Artillery" / "Cryptek Retinue"), und
  `eligible_join_targets()` dispatcht auf die Regel: die Zusatzbedingungen der zwei sind
  nicht dieselben.

**SELBST EINGEBAUTE REGRESSION, gefunden durch LESEN und nicht durch Tests, und die volle
Suite blieb dabei grün.** Etappe 1 hat den Crypteks ihre korrekte SUPPORT-Rolle gegeben —
und `formations.is_support_platform()` las die attachment-ROLLE, gab also für alle fünf
Crypteks True zurück. Das Vorspiel-Panel hätte jedem Cryptek ein "Support Artillery"-Angebot
gemacht. Behoben, indem das SUPPORT-WEAPON-Keyword gefragt wird — das ist, was die drei
Plattformen wirklich unterscheidet —, und in `test_necron_crypteks.py` in BEIDE Richtungen
gepinnt (die fünf Crypteks sind draußen, die D-cannon Platform ist weiter drin). **Die
Lehre ist die alte:** eine Rollen-Korrektur ist eine Änderung an einer Frage mit mehreren
Lesern, und der zweite Leser sieht dem ersten nicht ähnlich.

**Flesh Hunger ist die ZWEITE Krit-Schwelle, die gar keine Zahl ist.** *"A successful Hit
roll scores a Critical Hit"* heißt: die Krit-Schwelle IST die Trefferschwelle, dieselbe Form
wie Baharroths Cry of the Wind — also `min(threshold, hit_threshold)` statt gegen eine
Konstante. Ein Test, der eine 6 oder eine 5 pinnt, besteht mit der Regel als festem Wert
implementiert und sähe nicht, dass ein WS3+-Modell auf 3en krittet, was die ganze Fähigkeit
ist. Dafür reichen `fight.py`s drei Melee-Aufrufe jetzt `hit_threshold=` durch.

**Shieldvanes ist ein TRADE, und beide Hälften sind deshalb OVERRIDES**: Sv 4+ → 3+ ist
besser, M 12" → 8" ist SCHLECHTER. Ein `_better()`-Fold, wie fast jeder andere Grant dieser
Engine geschrieben ist, behielte still die 12" und verschenkte den 3+. Jede Hälfte hat ihre
eigene A/B-Sonde, weil ein Fix, der nur die gute Hälfte trägt, genau so aussieht wie einer,
der beide trägt.

**Shadowloom wird am UNIT gefragt, mit einem PRÄDIKAT statt eines Attributnamens.** Rule
24.33 ist eine Jedes-Modell-Fähigkeit, also gewährt EIN Shadowloom der Einheit nichts und
sechs gewähren ihr Stealth — das ist der gedruckte Text, wie er dasteht, keine
Vereinfachung. `squad_has_stealth()` fragt deshalb
`attached_units.unit_has_ability(squad, tomb_blade_wargear.model_has_stealth)`.

**Der Nebuloscope ist ein KEYWORD-GRANT, also die teuerste Fehlerform dieses Repos — und
[IGNORES COVER] ist der milde Fall.** Sein EINZIGER Leser ist
`ShootingController._ignores_cover()`, das ohnehin einen Waffen-Term ODERt; der Grant landet
also auf der WAFFE in der Adjuster-Kette und es gibt kein zweites Tor zu verfehlen. Dazu ein
Eintrag in `_attack_key()`, **sechste Instanz des Ein-Repräsentanten-Fixes**: Deckung wird
pro Angriffs-SEQUENZ entschieden, zwei Tomb Blades einer Einheit — einer beskopt, einer
nicht — dürfen also keine Gruppe teilen.

**Evasion Engrams ist das FÜNFTE Modul einer Familie, und das ist der Punkt, an dem sie
benannt gehört.** Tactical Acumen (6", kein ER-Satz), Fire and Fade (6", ER-Satz), Warhosts
Fire and Fade (6", + Embark-Lock), Chronometron (5", ER-Satz), Evasion Engrams (6", kein
ER-Satz). Die variierenden Teile sind auf **vier Knöpfe** zusammengefallen — Prädikat,
Distanz, ob der gedruckte Text eine Engagement-Range-Klausel trägt, welche Locks beim
Confirm greifen —, also ist die Extraktion nach der eigenen Zweiter-Konsument-Regel dieses
Repos überfällig. **Sie ist hier NICHT gemacht**: sie würde vier laufende Module und ihre
Suiten mitten in einer Datenblatt-Etappe umschreiben, was der Weg ist, auf dem sich ein
Refactor einschmuggelt. Als benannter Kandidat samt Knopfliste in
`game/evasion_engrams.py`s Docstring festgehalten.
- **Und dass es KEINE Engagement-Range-Klausel druckt, ist die Transkription und kein
  Versehen** — seine zwei nächsten Nachbarn drucken eine. Ein Tomb-Blade-Trupp im Nahkampf
  DARF diesen Zug machen. In der Suite gegen den Chronometron in DERSELBEN Lage gemessen,
  damit es nicht in Übereinstimmung "repariert" wird.

**Hyperspace Hunters baut nichts Neues**: `start_reactive_shooting(restrict_to=)` gibt es
seit Vengeful Stars, `on_ingress_resolved` seit Rapid Ingress. **Die eine Falle in dem
Haken:** er feuert auf CANCEL genauso wie auf Ankunft — er heißt "der Ingress-Versuch ist
vorbei", nicht "eine Einheit ist angekommen". `ingressed_this_turn` trennt die beiden, sonst
bekämen die Deathmarks eine Gratissalve auf eine Einheit, die gar nicht auf dem Brett steht.

**Systematic Vigour ist der DRITTE Konsument von `game/fight_after_death.py`** (nach Undying
Spite 4+ und Malevolent Souls 3+) und unterscheidet sich in genau einer gedruckten Klausel:
*"if that model has not fought this phase"*, die keiner der zwei Nachbarn druckt. Sie wird
am SQUAD beantwortet, und das ist die verfügbare Granularität statt einer Abkürzung — 12.02
wählt die EINHEIT, `fought_squad_ids` führt Einheiten, "dieses Modell hat gekämpft" und
"seine Einheit hat gekämpft" können hier nicht auseinanderfallen. Aufgeschrieben, weil das
gedruckte Wort MODEL ist.

**Bound Creation ist die ZWEITE Bodyguard→Leader-FNP-Gewährung** (nach Death Guards Silent
Bodyguard) und liest sich pro MODELL, nicht pro Einheit: der gedruckte Gegenstand ist *"that
CRYPTEK model"*. Gemessen in einer gemergten Einheit: Technomancer 4+, Necron Warrior 5+,
Cryptothrall 5+ — jede falsche Lesart gibt den 4+ mindestens einem der anderen zwei. Der
CRYPTEK wird über die DATENBLATT-Keyword-Leiste der Komponente gefragt, die einzige
Granularität, auf der die Frage nach einem 19.01-Merge überhaupt beantwortbar ist.

**Getestet:** neu `test_necron_rank_and_file.py` (**99/99**, neun Abschnitte) plus
`ab_necron_rank_and_file.py` (**31 A/B-Sonden, alle beißend**). **Vier bissen zuerst nicht,
und alle vier waren Befunde über den TEST** (Fehlerklasse 24):
- Die Hyperspace-Hunters-Prüfungen lasen den RÜCKGABEWERT von `offer_on_arrival()` — der
  ohne Shooting-Controller in BEIDEN Welten False ist, also war "abgelehnt" von "gefeuert"
  nicht zu unterscheiden. Jetzt über einen aufzeichnenden Stub, was gleich die
  `restrict_to`-Klausel messbar macht (eine fünfte Sonde, die vorher gar nicht möglich war).
- Die CRYPTEK-Klausel war nur an ihrem PRÄDIKAT geprüft, nicht dort, wo der Schritt sie
  fragt (`retinue_join_errors`).
- Der Nebuloscope-Copy-Wächter benutzte eine FRISCHE Waffen-Instanz, die eine
  In-Place-Mutation überlebt — er nimmt jetzt die Instanz, die das Modell wirklich trägt.
- Und der Grant war nur am eigenen Modul gemessen, nie durch `shooting.py`s echte
  Adjuster-Kette. Beide Enden sind jetzt gepinnt, plus die `_attack_key()`-Spaltung.
- **Eine fünfte Sonde ließ die Suite ABSTÜRZEN statt rot zu werden** (`attach()` wirft auf
  einer illegalen Paarung) — **zwanzigste Instanz** dieser Lehre; sie degradiert jetzt.

Volle Regression **213 Suiten, ~18637 Prüfungen, 212 grün / 0 rot / 1 bekannt**, und
`selfplay.py map2` (1500 Frames, exit 0) — keine Formalie, weil `main()` drei neue
Controller konstruiert und keine Suite `main()` fährt (Fehlerklasse 23).

**Ein Sprite fehlt, und das ist gepinnt statt geglättet:** Flayed Ones haben keine Kunst
(`WITHOUT_ART` in `test_necron_datasheets.py`), die anderen drei zeichnen ihre eigene. Am
MODELL geprüft, nicht an der Tabelle.

**Bewusst offen, wie in Etappe 1:** `armies/necrons.json` unangetastet, alle vier *dormant
by roster*; `auto_players` in jedem neuen Controller, aber KEINE
`ai/agent_driver.py`-Urteile — als Negativraum geprüft.

### Etappe 3 — der DESTROYER CULT (Hexmark, Ophydian Destroyers, Nekrosor Ammentar)

Drei Datenblätter, **acht Fähigkeiten**, und fast jede ist der ZWEITE Träger von etwas,
das schon da war. Der Inhalt der Etappe ist deshalb, an welcher NAHT jede landet — und
die vier Stellen, an denen der neue gedruckte Text von dem abweicht, dem er gleicht.

**DER SCHWERSTE FUND WAR NICHT GESUCHT: der Plasmacyte wurde nie ANGEBOTEN.** `use()`
und `can_use()` in `game/plasmacyte.py` hatten **null Aufrufer** in `game/`, `ai/` und
`main.py` — gemessen, nicht vermutet. Der [DEVASTATING WOUNDS]-Grant hing in
`FightController`s Adjuster-Kette, der Per-Phasen-Reset wurde aus `main.py` gerufen, das
Gear zählte die Marken — und nichts hat je gefragt. **Kein Skorpekh-Destroyer-Trupp hat
je einen Plasmacyten benutzt.** Achte Instanz der „gebaut, aber nie GEFÜTTERT"-Klasse,
und sie ist erst aufgefallen, weil die Ophydian Destroyers dieselbe Wargear-Zeile WÖRTLICH
drucken: **der zweite Träger ist der Ort, an dem eine fehlende Hälfte sichtbar wird.**
Der Grant hängt jetzt an `FightController._start_fighting()` — dem einen Ort, an dem 12.04s
„selected to fight" für BEIDE Wege dorthin passiert —, neben Path of the Warrior, das an
demselben Moment und aus demselben Grund gefragt wird. **Es bleibt eine echte Wahl**: die
Nutzungen sind ein PRO-SCHLACHT-Konto, eine aufzuheben ist also eine Entscheidung, anders
als die Einmal-pro-Runde-Berechtigungen, die dieses Repo automatisch auflöst.

#### Inescapable Death: drei Klauseln, ZWEI Berechtigungen

*"Once per turn, one unit from your army with this ability can be targeted with the Fire
Overwatch Stratagem for 0CP, even if you have already used that Stratagem on a different
unit this phase. In addition, each time you target this unit with the Fire Overwatch
Stratagem, while resolving that Stratagem, hits are scored on unmodified Hit rolls of 2+."*

| # | Klausel | Fenster |
|---|---|---|
| 1 | „for 0CP" | einmal pro **ZUG** |
| 2 | „even if you have already used that Stratagem ... this phase" | einmal pro **ZUG** (dieselbe) |
| 3 | „each time you target this unit ... 2+" | **jedes Mal**, gar keine Berechtigung |

- **1 und 2 sind EIN Satz und EINE Berechtigung**, also implementiert EIN Objekt beide
  Schnittstellen. Auf zwei Objekte verteilt könnten sie sich darüber uneinig werden, ob
  die Berechtigung noch da ist — und der Spieler bekäme eine Gratisnutzung, die 15.01
  danach ablehnt, oder eine erlaubte Wiederholung, die CP kostet.
- **Klausel 3 ist der Unterschied zu ihrem Beinahe-Zwilling.**
  `game/enh_protector_of_the_paths.py` druckt dieselbe Idee mit *„while resolving THAT
  Stratagem"* und trägt dafür einen `_free_activation`-LATCH. Dieses Datenblatt druckt
  diese Wörter nicht, bekommt also keinen Latch: **eine zweite, voll bezahlte Fire
  Overwatch auf denselben Hexmark trifft weiter auf 2+.** Eine kopierte Implementierung
  besteht jede andere Zeile der Suite und fällt genau an dieser.
- **`StratagemController.repeat_permissions` ist neu** — die Liste, die 15.01s
  „nicht zweimal dasselbe Stratagem pro Phase" für EINE Nutzung aufhebt. Eine EIGENE
  Liste neben `cost_discounts` und nicht eine zweite Pflicht darauf: „discount" wäre
  ein lügender Name für eine Regel über TIMING, und die zwei werden zu verschiedenen
  Zeitpunkten gefragt. Reine ABFRAGE, wie `available_discount()` — `refusal()` läuft
  pro Frame aus dem Panel und aus Fire Overwatchs eigenem Eignungs-Sweep.
  **Nicht zu verwechseln mit `Stratagem.allow_repeat_target`**: das hebt die
  ZIEL-Hälfte von 15.01 für ein ganzes Stratagem auf, dies die STRATAGEM-Hälfte für
  eine einzelne Nutzung.
- **„Once per TURN", nicht „once per battle round"** — der erste `cp_discount`-Konsument,
  der das nicht druckt. Eine Schlachtrunde hält BEIDE Spielerzüge (07.03), die zwei
  Fenster als gleich zu lesen halbiert also die Karte. `OncePerRoundCpDiscount` bekam
  dafür `window_key()`; die fünf bestehenden Konsumenten sind unberührt, weil der
  Default `_round()` bleibt. **Gemessen über eine ZUG-Grenze UND eine RUNDEN-Grenze
  getrennt**: ein Test, der nur die Runde weiterschaltet, besteht mit dem geerbten
  Fenster.
- **„For 0CP" ist NICHT „−1CP", und auf der ausgelieferten Karte fallen die zwei
  Lesarten ZUSAMMEN** — Fire Overwatch kostet genau 1. Genau der Fehler, vor dem
  `game/free_stratagem_once_per_round.py`s Docstring warnt („would look right on every
  1CP Stratagem"), und die A/B-Sonde, die ihn einbaute, meldete gegen jede Zeile NO BITE.
  Die Zusicherung wird deshalb an einer KONSTRUIERTEN höheren Kosten gemessen — dieselbe
  Behandlung, die dieses Repo jedem Mechanismus gibt, dessen Live-Fall zwei Lesarten
  nicht trennt.

#### `game/reactive_bodyguard_shooting.py` — 40. Extraktion, am zweiten Konsumenten

Multi-threat Eliminator ist Kroot Packmates mit zwei geänderten Wörtern (3" statt 6",
NECRONS statt KROOT INFANTRY). Beide drucken denselben vierteiligen Auslöser und enden
in dem Satz, den auch Protocol of the Vengeful Stars druckt — der SCHWANZ war längst
geteilt (`start_reactive_shooting(restrict_to=)`), der KOPF nicht.

- **Geteilt ist, was zweimal subtil falsch zu machen ist:** der `target_reactions`-Vertrag
  (`maybe_offer(attacking_squad, target_squad, melee=False)` — und den falsch zu haben ist
  nicht hypothetisch: `KrootPackmatesController` lieferte mit NUR einer pluralen
  `on_targets_selected()` aus, deren Docstring behauptete, DAS sei der Vertrag, und jedes
  Spiel starb mit einem `AttributeError`, sobald irgendeine Einheit ein Schussziel wählte);
  „after that enemy unit has finished making its attacks" als GESCHULDETER Schuss statt
  eines sofortigen; das Einmal-pro-Zug-Konto pro SPIELER statt pro Squad; und ein Reaktor,
  der an genau dem Angriff gestorben ist, den er beantwortet.
- **Jede Unterklasse besitzt fünf Dinge**: Flag, Reichweite, welche befreundeten Einheiten
  sie schützt, Label und Promptwortlaut. Als Klassenattribute plus EINE Methode, nicht als
  Konstruktorargumente — eine Unterklasse, die eines vergisst, scheitert laut bei der
  Definition statt still bei 0".
- **DER REAKTOR IST EIN SQUAD**, und Multi-threat Eliminator ist der Grund, das
  aufzuschreiben: sein Text sagt „one MODEL with this ability ... can shoot", wo sein
  Zwilling „that unit" sagt. Eine Schussaktivierung ist hier pro SQUAD, und der Hexmark
  ist eine Ein-Modell-Einheit ohne LEADER-Zeile — die zwei Lesarten können für keinen der
  beiden Träger auseinanderfallen. Ein künftiger Träger mit mehreren Modellen bräuchte
  eine Pro-Modell-Aktivierung, die es nicht gibt; benannt statt zum Wiederentdecken.
- **Verhaltensneutral belegt:** `test_tau_kroot_and_vespid.py` blieb ohne eine einzige
  Anpassung grün.

#### `attached_units.model_has_datasheet_keyword()` — 39. Extraktion

„Trägt DIESES MODELL dieses Datenblatt-Keyword", gefragt an der KOMPONENTE, aus der es
stammt. `game/cryptothralls.py` hatte es für *„that CRYPTEK model"* ausgeschrieben;
Infectious Murder-madness fragt dasselbe für *„if that model has the DESTROYER CULT
keyword"*. **Es kann nicht `unit_has_datasheet_keyword()` mit einem Modell sein** — ein
Modell weiß nicht, von welchem Datenblatt es kommt, und 19.01s Merge bewahrt jede
Komponente samt Datenblatt; der Abgleich gegen `starting_models` ist die einzige
Granularität, auf der die Frage nach einem Merge überhaupt beantwortbar ist.

#### Nekrosor Ammentars vier Fähigkeiten

- **Protective Disciples ist der FÜNFTE konditionale Lone Operative**
  (`game/conditional_lone_operative.py`) und der ENGSTE: Illuminor Szeras' identischer
  Satz fragt nach irgendeiner befreundeten NECRONS-Einheit, dieser nach einer DESTROYER
  CULT. Neben Necron Warriors zu stehen tut hier nichts — die halbe Hälfte, die eine
  Kopie seines Moduls verliert, und deshalb steht der Nicht-Cult-Fall als eigene Zeile
  in der Suite.
- **Infectious Murder-madness hat ZWEI Klauseln mit „ODER", und sie werden auf
  VERSCHIEDENEN Granularitäten gefragt** — der Teil, den man versehentlich flach macht:
  „if THAT MODEL has the DESTROYER CULT keyword" ist pro MODELL (über die Extraktion
  oben), „or that ENEMY UNIT is the closest eligible target" ist eine Eigenschaft des
  ANGRIFFS und wird deshalb vom AUFRUFER gemessen — jeder Angriffsschritt kennt seine
  eigenen berechtigten Ziele, und das hier neu herzuleiten wäre eine zweite Meinung zu
  Regel 10.02. **In der Suite wird jede Klausel mit der anderen ABGESCHALTET gemessen**;
  beide gleichzeitig zu stellen besteht mit einer von beiden unimplementiert.
  - **GEMESSEN statt angenommen:** auf jedem gebauten Datenblatt werden DESTROYER-CULT-
    Einheiten nur von DESTROYER-CULT-Charakteren geführt (Skorpekh Lord → Skorpekh
    Destroyers, Lokhust Lord → die zwei Lokhust-Blätter), es kann also keine Einheit
    geben, die ein DC- und ein Nicht-DC-Modell hält. Das macht 04.03s
    Ein-Repräsentant-Gruppierung hier EXAKT statt zu einer Abkürzung — und es ist als
    Mengendifferenz über die Paarungstabelle gepinnt, damit eine künftige Paarung, die
    es bricht, als rote Zeile auffällt statt als still falscher Grant.
  - **Die eigene Einheit des Trägers ist NICHT ausgenommen** („a friendly NECRONS unit",
    nicht „another"), drei Zeilen unter Protective Disciples, das sehr wohl „other" sagt.
- **Prophet of Destruction** hängt am Todes-Sweep, neben Vengeful Stars und Pinpoint
  Counter-Offensive, und beantwortet „wer hat es getötet" mit derselben einzigen Antwort,
  die diese Engine hat. **Die 9" werden vom LEBENDEN Träger gemessen** — das Gegenteil
  von Vengeful Stars, dessen 6" von den LEICHEN aus gemessen werden müssen, weil sein
  gedruckter Text sie so benennt.
- **Nullstone Field Generator ist die ERSTE AURA-Quelle in `feel_no_pain.py`s Fold.**
  Jede andere konditionale Quelle dort liest ein Flag, das etwas anderes gesetzt hat;
  diese ist ein 6"-Reichweitentest, und `current_feel_no_pain()` nimmt ein MODELL und hat
  rund ein Dutzend Aufrufstellen. Also ein SQUAD-FLAG, einmal pro Frame gestempelt, neben
  Nurgle's Gift und aus dessen zwei Gründen. **Gemessen gegen eine MORTAL-, eine
  PSYCHIC- und eine GEWÖHNLICHE Wunde** — nur der dritte Fall trennt „die Aura wirkt" von
  „die Aura ist bedingungslos".

#### Tunnelling Horrors: zwei vorhandene Hälften, EINE Phase auseinander

Die Entnahme ist Airborne Agilitys Satz Wort für Wort; die erzwungene Rückkehr ist
Unshrouded Truths Runden-Tor-Override. **Neu ist allein die UHR:** jenes Stratagem wird in
DEINER Bewegungsphase benutzt und die Einheit kommt in DERSELBEN zurück, sein Flag wird
also am Phasenende gelöscht. Dieses wird am Ende des GEGNERZUGES benutzt und die Einheit
kommt in der NÄCHSTEN eigenen Bewegungsphase — das Flag muss also den Rest des
Gegnerzuges UND die eigene Command-Phase überleben und wird am Ende der Bewegungsphase
gelöscht, in der es geschuldet war. Ein Per-Phasen-Reset wäre genau die halblange Flagge,
um die es in Fehlerklasse 14 geht.
- **„(including in your first turn)" ist die Klammer, die den Override TRAGEND macht**
  statt dekorativ: eine Einheit, die am Ende des ersten Gegnerzuges tunnelt, wird in
  Schlachtrunde 1 zurückerwartet, was 20.03 rundweg verbietet.
- **KEIN Deep-Strike-Grant**, anders als bei Unshrouded Truth — die Ophydian Destroyers
  drucken [DEEP STRIKE] selbst. Ausdrücklich vermerkt, weil die zwei Fähigkeiten sonst so
  dicht beieinanderliegen, dass eine fehlende Zeile wie ein Versehen aussieht.

#### Waffen: der Kollisions-Sweep lief VOR der ersten Klasse

- **„Close combat weapon" wird ein DRITTES Mal gedruckt** (Hexmark, A4 WS3+ S5) und die
  Zahlen passen zu KEINER der zwei bestehenden → eigene Klasse, nach den ZAHLEN benannt
  wie ihre zwei Nachbarn, weil der Royal Warden dieselbe Zeile druckt und sie teilen wird.
  Im Test GEGENEINANDER gepinnt (drei verschiedene Zahlensätze unter einem Namen), nicht
  gegen Literale.
- **„Blade tail and whip coils" SIEHT aus wie der Canoptek Wraiths' „Whip Coils"** und
  ist es nicht: anderer gedruckter Name, andere Zahlen (A6 S6 AP-1 [EXTRA ATTACKS] gegen
  A8 S5 AP0). Zwei Klassen, und die Ähnlichkeit ist aufgeschrieben, damit keine in die
  andere gefaltet wird.
- **Nekrosor Ammentar behält seine gedruckten 80 mm**, und das ist eine Entscheidung.
  Die stehende Vorgabe „alle Destroyer sollen die gleiche Größe haben" setzt beide Lords
  auf 50 mm trotz gedruckter 60, und der mit ihr protokollierte Grund ist Regel 19.01: ein
  Lord wird in einen Destroyer-Trupp GEMERGT. Nekrosor Ammentar druckt gar keine
  LEADER-Zeile, kann also nie gemergt werden, und seine zwei Etappen-Nachbarn drucken
  ohnehin 50 mm. Jedes Modell, dessen NAME „Destroyer" sagt, ist hier weiterhin 50 mm;
  seiner sagt es nicht.

**Getestet:** neu `test_necron_destroyer_cult.py` (**146/146**, neun Abschnitte) plus
`ab_necron_destroyer_cult.py` (**41 A/B-Sonden, alle beißend, keine stürzt ab**).
**Drei Sonden bissen zuerst NICHT, und alle drei waren Befunde über den TEST**
(Fehlerklasse 24): die Protective-Disciples-Reichweite war gar nicht gemessen (es stand
keine Cult-Einheit AUSSERHALB der 3" auf dem Brett); die Melee-Ablehnung des geteilten
Basisklassen-Vertrags war in der KROOT-Suite ungemessen, sodass eine Änderung an der
Basis nur EINEM ihrer zwei Träger auffiel — genau die Drift, gegen die die Extraktion
gebaut ist; und „gratis gegen −1 CP" ist bei einem 1-CP-Stratagem gar nicht
unterscheidbar (siehe oben). **Eine Sonde ließ die Suite ABSTÜRZEN statt rot zu werden**
(`restrict_to` ist dann None und ein nacktes `r.name` bricht den Lauf ab) —
**einundzwanzigste Instanz** dieser Lehre; sie degradiert jetzt.

Volle Regression **214 Suiten, ~18788 Prüfungen, 213 grün / 0 rot / 1 bekannt**, und
`selfplay.py map2` (1500 Frames, exit 0) mit den Default-Armeen UND mit Necrons auf
BEIDEN Seiten — keine Formalie, weil `main()` fünf neue Controller konstruiert und keine
Suite `main()` fährt (Fehlerklasse 23). Der Korpus kostete **null** Wartung: der Name
wandert von `MISSING_NECRONS` nach `faction.datasheets`, `rules/necrons/` bleibt bei 49
Dateien, und zwei `--offline`-Läufe erzeugen keinen Diff.
**Zwei fremde Pins wurden zu Recht rot und sind STÄRKER nachgezogen statt nachgezählt:**
`test_aeldari_enhancements.py` zählte die konditionalen Lone-Operative-Quellen und pinnt
jetzt ihre MODUL-MENGE (eine sechste muss sich benennen, und eine still ERSETZTE kommt
nicht mehr durch, indem die Zahl gleich bleibt); und `test_tau_kroot_and_vespid.py`
pinnte Kroot Packmates als das LETZTE Element des `target_reactions`-Tupels — Formatierung
statt Bedeutung — und liest es jetzt per AST als Menge.

**Ein Sprite fehlt und ist gepinnt:** Nekrosor Ammentar hat keine Kunst (die 27 vom User
gelieferten Necron-Dateien enthalten ihn nicht), die anderen zwei zeichnen ihre eigene.
Am MODELL geprüft, und die Verschattung ist GEMESSEN statt gehofft: `_key_for_name()`
liefert den ERSTEN Schlüssel, der Teilstring des Squad-Namens ist, also kann ein neuer
verschluckt werden oder einen älteren verschlucken — für beide neuen ist beides leer.

**Bewusst offen, wie in Etappe 1 und 2:** `armies/necrons.json` unangetastet, alle drei
*dormant by roster*; `auto_players` in jedem neuen Controller (bei Multi-threat Eliminator
GEERBT aus der Basisklasse — ein Quell-Sweep nach dem Wort antwortet dort False, also
misst die Suite es am OBJEKT), aber KEINE `ai/agent_driver.py`-Urteile: keine der acht
Wahlen ist armeeweit.
