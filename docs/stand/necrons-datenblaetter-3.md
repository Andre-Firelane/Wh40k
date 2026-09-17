# Necrons: Datenblatt-Nachzug (3)

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die restlichen Necron-Datenblätter — Fortsetzung

### Etappe 7 — die vier anbindbaren Charaktere

Royal Warden, Overlord with translocation shroud, Imotekh The Stormlord und
Trazyn The Infinite. **26 von 32 Bauzielen; die Fraktion steht bei 41 von 64.**
Die Etappe mit dem höchsten Wiederverwendungsanteil des ganzen Nachzugs:
**sechs von acht** gedruckten Fähigkeiten sind Zwillinge von Gebautem, also ist
der Inhalt nicht das neue Modul, sondern die EINE Klausel, die jeder Zwilling
nicht teilt.

**Vier Extraktionen bzw. Faltungen, alle am ZWEITEN Konsumenten**, und keine
davon war vorgezogen: der zweite Träger kam in dieser Etappe an.

| Fähigkeit | landet bei | die eine Abweichung |
|---|---|---|
| Adaptive Strategy | `game/move_exceptions.py` (2 Tore) | Relentless Combatants (E4) lifted NUR die Charge-Hälfte |
| Engrammatic Logic | **`game/end_battle_shock.py` (48. Extraktion)** | ein Wort: NECRONS statt KROOT |
| Grand Strategist | **`game/command_phase_cp.py` (49. Extraktion)** | keine — Eldrads Diviner of Futures Wort für Wort |
| Lord of the Storm | `game/mortal_wound_sweep.py` (E6) | ZWEI Bänder statt einem, plus einmal pro Schlacht |
| Ancient Collector | `game/fieldcraft.py`s Sweep, Regel 14.03 | „while this model is LEADING a unit" |
| My Will Be Done / Resurrection Orb | unverändert wiederverwendet | — |
| Translocation Shroud | `movement.py`s Kein-Wurf-Advance + `clamp_move()` | die einzige wirklich neue Bewegungsklausel |
| Surrogate Hosts | **NICHT gebaut** (User-Entscheidung) | — |

#### Kein gemeinsames Profil — und das ist die Umkehrung der Etappe davor

Die drei C'tan haben eine Basisklasse bekommen, weil sie ein Chassis teilen.
Diese vier teilen M5 T5 Ld6+ OC1 und sonst nichts: der Royal Warden ist **Sv3+
statt 2+, W4 statt 6, ohne Rettungswurf und nicht NOBLE**. Drei stimmen überein
und der vierte nicht, eine Basisklasse müsste also von einem Mitglied dreimal
überschrieben werden — vier ehrliche Kopien sagen mehr. Als MENGE gepinnt („nur
der Royal Warden hat keinen Invulnerable, nur er ist nicht NOBLE, genau zwei
sind EPIC HERO") statt als vier Zahlenlisten, und alle vier leiten nachweislich
direkt von `UnitProfile` ab.

#### Waffen: der Kollisions-Sweep lief in BEIDE Richtungen

**GETEILT, nicht geklont** — der inverse Fehler zu Etappe 3, und
`NecronCloseCombatWeaponA4S5Profile` hatte den Royal Warden in seinem eigenen
Docstring als künftigen Sharer benannt (Etappe 3 hat ihn vorhergesagt, hier wird
er eingelöst). Ebenso teilt der Shroud-Overlord die `OverlordsBladeProfile` des
Overlord. Als Klassen-IDENTITÄT gepinnt, plus der Nachweis, dass beide Träger
ihre **eigene** WS auflösen — eine Kopie mit denselben Zahlen bestünde die erste
Zeile und fiele an der zweiten. Vier Waffen sind neu.

**Der Staff of the Destroyer druckt ZWEI Zeilen unter EINEM Namen und ist KEIN
Feuermodus-Paar**: eine Fernkampf-, eine Nahkampfzeile, er trägt beide
gleichzeitig, und 04.01 muss nie wählen. Ein `overcharge_profile` hätte ihm
still eine seiner zwei Waffen genommen. Gegeneinander gepinnt (gleicher Name,
Differenz genau ein Angriff plus [DEVASTATING WOUNDS]) statt gegen Literale.
Der Gauntlet of Fire druckt BS „N/A" → [TORRENT] (24.37), und **keine Waffe
dieses Schwungs trägt einen Skill-Override** — als Menge gepinnt.

#### Die LEADER-Tabelle, und das eine Wort, das den Royal Warden trennt

Alle vier binden sich an Immortals, Lychguard und Necron Warriors — **außer dem
Royal Warden, dessen gedruckter `## Leader`-Abschnitt LYCHGUARD nicht nennt**.
Gemessen durch das ECHTE `can_attach()` (zwölf Paarungen, `[]` = legal) UND am
gedruckten Abschnitt selbst gelesen, in beide Richtungen: das Wort fehlt bei
ihm und steht bei den anderen dreien.

#### Adaptive Strategy: beide Hälften von 09.07, gegen den Nachbarn gemessen

„Eligible to shoot **and** declare a charge in a turn in which it Fell Back" —
zwei Tore in `game/move_exceptions.py`. Die Triarch Praetorians (E4) drucken
denselben Satz **ohne die Schuss-Hälfte**, eine Kopie ihres Relentless
Combatants bestünde also die Charge-Zeile und fiele an der ersten. Deshalb
misst die Suite BEIDE Einheiten durch dieselben zwei Aufrufe, und die zwei
A/B-Sonden nehmen je eine Hälfte weg.

#### `game/end_battle_shock.py` — 48. Extraktion, und ihre Sonde fand eine Testlücke

Root of Honour (Kroot War Shaper) und Engrammatic Logic sind derselbe Satz mit
einem getauschten Keyword. Geteilt sind die vier Bedingungen, jede eine eigene
Art danebenzugreifen: **einmal pro Schlacht ist pro MODELL** (nicht pro Armee
wie War Leader nebenan und von keiner Grenze zurückgesetzt), „at the start of
ANY phase" heißt auch die gegnerische (also aus beiden Spielern heraus
angeboten), das Keyword wird an den Modellen gelesen, und ein nicht geschocktes
Ziel ist gar nicht erst Option (Fehlerklasse 5). `root_of_honour.py`
re-exportiert `ROOT_OF_HONOUR_RANGE_IN`, seine Aufrufer bewegen sich nicht.

**BEFUND ÜBER DEN TEST, von der eigenen Sonde:** die Sonde „die geteilte
Reichweite ist 6\" statt 12\"" biss gegen die Necron-Suite und **NICHT gegen
`test_kroot_shapers.py`** — die maß Reichweite nur mit 40\" gegen 4\", was eine
Halbierung überlebt. Seit die Zahl GETEILT ist, bewegt sie eine Regel auf zwei
Datenblättern zugleich, also läuft die Kroot-Suite jetzt die GRENZE ab (11.5\"
eligible, 12.5\" nicht) und pinnt die 12\" gegen die GEDRUCKTE Seite statt gegen
die Modulkonstante, die eine Sonde auf beiden Seiten des Vergleichs bewegen
würde. 108 → **111/111**.
**Nebenbei gemessen:** 19.01 hängt den Leader ans ENDE der Modellliste, sein
eigenes x liegt also nirgends an der Vorderkante der Einheit — der Grund, warum
die alten 40\" so großzügig sein mussten. Die neuen Zeilen messen vom
BEARER-MODELL.

#### `game/command_phase_cp.py` — 49. Extraktion

Grand Strategist ist Eldrads Diviner of Futures Wort für Wort. Der CP läuft über
`command_points.gain_cp()`, also greift die Ein-Bonus-CP-pro-Runde-Hausregel —
eine Armee mit beiden gewinnt EINEN, nicht zwei. Gemessen an einem echten
Ledger, und „on the battlefield" ist die Tokenliste: ein toter Träger zahlt
nichts. `diviner_of_futures.py` re-exportiert Konstante, Reason und den
Bearer-Helfer.

#### Lord of the Storm — der zweite Konsument, der die E6-Extraktion rechtfertigt

`game/mortal_wound_sweep.py` wurde in Etappe 6 mit einem Träger gebaut und
nannte diesen hier von Anfang an. Er unterscheidet sich in genau den Knöpfen,
für die es sie gibt: 12\" statt 6\", Schwelle **2** statt 4, **zwei Bänder**
(2-5 → D3, 6 → D3+3) statt eines, und einmal pro Schlacht statt unbegrenzt.
Ende der EIGENEN Command-Phase, also nimmt der Haken eine SEITE — anders als
Drain Life am Ende der Fight-Phase, die keinem Spieler gehört. Gemessen
end-to-end durch echte Würfel und eine echte 06.02-Zuteilung: eine 6 plus ein
D3 von 1 tötet wirklich **vier** Ein-Wunden-Modelle, zwei Feindeinheiten geben
zwei Würfel in EINER Handvoll und zwei getrennte Zuteilungen, und die Nutzung
ist verbraucht, ob sie etwas getroffen hat oder nicht.
**Der `mover_before`-Haken ist eigens gepinnt** (§8s Naht): am Ende der
Command-Phase liest `turn_tracker.turn_owner` bereits den nächsten Spieler.

#### Translocation Shroud — und die Hälfte, die ein GEMESSENER No-op ist

Zwei gedruckte Hälften. Die erste (kein Advance-Wurf, stattdessen flache +6\")
nimmt `movement.py`s vorhandenen Kein-Wurf-Zweig, den Jain Zar und Aggressive
Mobility schon teilen. Die zweite („through models **and terrain features**",
auf Normal, Advance und Fall Back) sitzt in `clamp_move()`s
Crosses-everything-Zweig und ist **auf den MOVE gegated, nicht auf ein Flag** —
Charge, Pile In und Consolidate stehen nicht auf der gedruckten Liste, und das
ist die Hälfte, die eine reine Flag-Lesart verliert. Alle vier Modi einzeln
durch `clamp_move()` gemessen (22.6\" gegen 25.0\").

**Die TERRAIN-Hälfte ist ein gemessener No-op und steht als solcher da**, statt
als wirksam ausgegeben zu werden: Regel 13.06 lässt INFANTERIE ohnehin durch
Dense-Gelände, und jede Einheit, die dieser Overlord führen kann, ist ebenfalls
INFANTERIE. Gemessen: plain Overlord und Shroud-Overlord erreichen durch
dieselbe Wand **exakt denselben Punkt**. Gebaut wird sie mit dem Qualifier (der
gedruckte Text nennt Gelände) und von BEIDEN Seiten gepinnt — dieselbe
Behandlung, die Vanguard Protocols in Etappe 5 bekommen hat.
**Die Messung muss auf PLAYER 1s Brett laufen**: die Wand-Hausregel
(`WALL_CROSSING_PLAYERS`) lässt jedes Modell der KI ohnehin durch, ein Vergleich
auf Player 2 misst also jene Regel statt dieser.
„It cannot finish a move on top of another model or its base" braucht keinen
Code — die Engine erzwingt das für jeden — ist aber gepinnt, damit die Klausel
von etwas gedeckt ist statt von nichts.

#### Ancient Collector — der zweite Träger von 14.03s Secured

Fieldcrafts Satz plus eine Klausel: **„while this model is LEADING a unit"**.
Also ein zweites Prädikat auf demselben Sweep statt eines zweiten
Sticky-Objective-Schemas. Ein allein stehender Trazyn kontrolliert das
Objective sehr wohl und sichert trotzdem nichts — die eine Zeile, die eine
Kopie von Fieldcraft verliert. Die Kontrolle wird in der Bühne aus dem BRETT
abgeleitet (`update_control()`), nicht von Hand hineingeschrieben: ein
`controlled_by`, das keine Phasengrenze erzeugt hätte, ist die Falle, an der
zwei fremde Suiten schon einmal hingen.

#### Surrogate Hosts ist NICHT gebaut (User-Entscheidung)

Es verlangt einen Laufzeit-Modelltausch samt frischer 19.01-Anbindung, und
diese Engine hat weder das eine noch das andere. In `abilities_text` als
`NOT ENGINE-WIRED` markiert und im Test **assertiert** (kein Profil-Flag tut so
als ob, und der gedruckte Text steht wirklich auf seiner Seite), damit späteres
Nachrüsten eine sichtbare Änderung ist — die Praxis von Trail Finding, Kroot
Ambush und dem Jammer Array.

#### Der Sprite-Verschattungs-Pin bekommt seine erste Ausnahme

`_key_for_name()` liefert den ERSTEN Schlüssel, der Teilstring des Squad-Namens
ist, und **„Overlord" ist bereits ein Schlüssel UND Teilstring von „Overlord
with translocation shroud"**. Der Stage-4/5-Pin („kein bestehender Schlüssel
verschluckt diesen Namen") gibt hier `['Overlord']` zurück und kann nicht
kopiert werden. Er hat also eine dokumentierte Ausnahme plus eine POSITIVE
Zusicherung: der Name steht ÜBER dem kürzeren, beide lösen auf dieselbe Datei
auf, und die lädt wirklich. **Das ist eine Entscheidung, keine Abwesenheit** —
er ist ein Overlord, der Rückfall ist der richtige, und der Eintrag ist die
gewinnende Zeile an dem Tag, an dem er eigene Kunst bekommt. Die anderen drei
verschatten nichts und werden von nichts verschattet (gemessen).

#### Getestet

Neu `test_necron_leaders.py` (**239/239**, zehn Abschnitte) plus
`ab_necron_leaders.py` (**29 Sonden, 30 Sondenläufe über vier Suiten, alle
beißend**). Sechs Sonden laufen gegen eine geteilte Basis und müssen BEIDE
Träger-Suiten rot machen — `test_kroot_shapers.py` (108 → **111/111**) und
`test_eldrad_ulthran.py` (**96/96**) —, weil ein Bruch, den nur einer der zwei
bemerkt, genau die Drift ist, gegen die die Extraktion gebaut ist.

**Zwei Befunde über den TEST, beide von den Sonden** (Fehlerklasse 24): die
Kroot-Reichweite oben, und der Verdrahtungs-Pin auf `main.py` — er zählte
CALL-Knoten, und ein `False and <call>` überlebt das. Er prüft jetzt, dass der
Aufruf eine ganze ANWEISUNG ist (`ast.Expr` mit einem `Call` als Wert), also
wirklich läuft, wenn sein Zweig läuft. **Eine dritte Sonde ließ die Suite
ABSTÜRZEN statt sie rot zu machen** (`list.index()` und `dict[...]` auf einen
entfernten Sprite-Eintrag) — die wiederkehrende Lehre; sie degradiert jetzt und
nennt beide gebrochenen Zeilen.

Volle Regression **218 Suiten, ~19635 Prüfungen, 217 grün / 0 rot / 1 bekannt**,
`run_tests.py --smoke` komplett grün (alle neun schweren Skripte),
`selfplay.py map2 1500` mit den Default-Armeen UND mit Necrons auf beiden Seiten
(beide exit 0). `verify_rules_vs_engine.py` unverändert bei **67 Differenzen,
keine davon nennt eine Einheit dieser Etappe**;
`test_weapon_characteristics.py` bei **null** Waffenabweichungen; der Korpus
kostet weiter null Wartung (`git status --porcelain rules/` leer, zwei
`--offline`-Läufe ohne Diff); der Golden Master unbewegt.

**Bewusst offen, wie in den Etappen 1-6:** `armies/necrons.json` unangetastet,
alle vier *dormant by roster*; `auto_players` in beiden neuen Controllern, aber
KEINE `ai/agent_driver.py`-Urteile — keine der acht Wahlen ist armeeweit.

### Etappe 8 — die drei Grav-Skimmer (Catacomb Command Barge, Annihilation Barge, Ghost Ark)

**29 von 31 Bauzielen; die Fraktion steht bei 44 von 64.** Die erste Etappe des Nachzugs, deren
UMFANG sich während der Planung geändert hat, und die erste mit einem echten TRANSPORT.

#### Der Umfang, und warum eine Streichung selbst Arbeit ist

**Die Night Scythe ist auf User-Entscheidung gestrichen** („nightsythe bitte komplett weglassen
(weil aircraft)"). `fetch_datasheet_rules.py` argumentierte an genau dieser Stelle das GEGENTEIL,
und zwar mit einer MESSUNG: „NIGHT SCYTHE IS NOT AN AIRCRAFT, measured rather than assumed ... its
11th-edition keyword bar says VEHICLE; FLY; TRANSPORT with no AIRCRAFT at all." Der Kommentar ist
**umgeschrieben, nicht gelöscht** — die Messung bleibt wahr, die ENTSCHEIDUNG geht über die
Keyword-Leiste. Eine zurückgenommene Begründung stehenzulassen ist genau die Form, die dieses Repo
als „veraltete Rechtfertigung unter einer grünen Zusicherung" führt (Mont'kas [ASSAULT]-Lücke).
Kopfarithmetik **32 → 31 Bauziele**; `rules/necrons/Night Scythe.md` bleibt als Snapshot liegen,
wie `Doom Scythe.md`, die Korpus-Dateizahl bewegt sich also nicht.

**Die Ghost Ark wird MODELLIERT** („ghost ark modellieren") statt als benannte Lücke — siehe den
Transport-Abschnitt unten.

**Nebenbefund, mitkorrigiert:** der Kommentar über `"The Silent King"` las noch „Every one of the
four Leaders attaches only to units that are already built". Etappe 7 hat die vier entfernt und den
Satz stehenlassen; er beschrieb einen einzigen Namen, der gar kein Leader ist.

#### Basisgröße: 2.1" für alle drei, und das ist eine STEHENDE Entscheidung

Der erste Reflex (⌀60mm gedruckt → 1.181") ist falsch, und die Begründung steht schon an der
Doomsday Ark: „Matched to the other grav tanks (Falcon, Devilfish, Wave Serpent, Kill Rig), not to
the printed 60 mm". Die drei sind dasselbe Chassis. **User-Entscheidung: „Alle drei auf 2.1""** —
obwohl der Rumpf-Unterschied real ist (die Ghost Ark ist mit T9/W14 exakt die Doomsday Ark, die
zwei Barges sind T8/W9). Gepinnt als VERHÄLTNIS gegen `DoomsdayArkProfile` statt gegen die nackte
Zahl, mit der gedruckten Größe im Kommentar daneben, damit niemand „korrigiert".

**Gemessen kostet es ZWEI Zeilen in `verify_rules_vs_engine.py`, nicht drei** (67 → **69**): die
Annihilation Barge druckt „Use model" (FRAME), es gibt dort also gar keinen gedruckten Wert zum
Vergleichen. Für sie ist 2.1" eine Tischgrößen-ENTSCHEIDUNG nach dem Triarch-Stalker-Muster, und
der Bericht schweigt zu ihr — was leicht als „zwei statt drei, also fehlt eine" fehlgelesen wird.

#### Waffen: VIER von sieben werden GETEILT, nicht geforkt

Der Kollisions-Sweep lief vor der ersten Klasse und kam andersherum heraus als in Etappe 3:
`GaussCannonProfile`, `ArmouredBulkProfile`, `GaussFlayerArrayProfile` und `OverlordsBladeProfile`
sind byte-identisch zu schon gebauten Zeilen und werden GETEILT — `game/weapons.py` hat diese
Etappe für die vierte sogar namentlich vorausgesagt. Neu sind nur `TeslaCannonProfile` und
`TwinTeslaDestructorProfile`; letztere hat nach der Streichung **nur noch EINEN Träger im Umfang**,
und das steht an der Klasse, damit sie sich nicht wie eine geteilte liest.

**Die Catacomb Command Barge widerspricht sich SELBST**, und genau dafür gibt es die
Pro-Waffen-Overrides: ihre drei Fernkampfzeilen drucken BS 3+/3+/2+, ihre zwei Nahkampfzeilen WS
2+/3+. **Profil BS3+/WS2+, die zwei STAFF-Zeilen tragen die Overrides** — das hält die vier
geteilten Klassen sauber; die Gegenrichtung bräuchte drei Overrides und würde zwei geteilte
Klassen forken. Die zwei Staff-Unterklassen erben und überschreiben genau ein Feld und sind im Test
GEGENEINANDER gepinnt statt gegen Literale.

#### `game/strength_over_toughness.py` — 50. Extraktion, am DRITTEN Träger

Advanced Quantum Shielding ist der Wave Serpent Shield und Guardian Protocols: S > T → −1 auf den
Wundwurf. Fünf Knöpfe (`flag`, `label`, `penalty`, `ranged_only`, `extra_condition`) plus EIN Leser
`wound_modifiers()`. Die zwei alten Module **re-exportieren**, es bewegt sich also keine ihrer
Aufrufstellen.

- **Die Drift war nicht hypothetisch:** `guardian_protocols.py` behauptete zwei Etappen lang in
  seinem Docstring, die Arithmetik sei geteilt, während beide Dateien ihre eigene Kopie trugen.
- **Zwei Schwester-Suiten wurden zu Recht rot** — sie patchten das MODULWEITE `applies()`, das den
  Controller nach der Extraktion nicht mehr erreicht. Jetzt am CARRIER gepatcht
  (`sot.WAVE_SERPENT_SHIELD.applies`, restauriert per `del`), was ein STÄRKERER Pin ist.
- **Ein Docstring-Fund, den nur eine NICHT beißende Sonde liefern konnte.**
  `guardian_protocols.py` schrieb über die 19.02-Toughness-Lesart „Here it genuinely matters, as
  opposed to the Wave Serpent's documented 'cannot matter today'". **Gemessen falsch:** über jede
  Einheit, die diese fünf Armeen bauen können, gemergt und ungemergt, geben
  `models[0].profile.toughness` und `attached_unit_toughness()` DIESELBE Antwort — ein
  Lychguard-Trupp mit Overlord ist so oder so T5. Es gibt kein Brett, auf dem die zwei Lesarten
  auseinandergehen, also kann kein Verhaltenstest sie trennen. Der Docstring sagt jetzt, was gilt,
  UND dass die frühere Fassung falsch war; die Sonde steht als **deklarierter Nicht-Beißer** mit
  ihrer Messung in `ab_necron_vehicles.py`, wie der T'au-Audit es für zwei Sonden vormacht.

#### Malevolent Arcing: ZWEI Momente, und keiner ist der offensichtliche

- **Wählen** — „each time you select a target for this model's twin tesla destructor". Die fünf
  registrierten `shooting_target_reactions` sind ausnahmslos VERTEIDIGER-Reaktionen („just after an
  ENEMY unit has selected its targets"); dies ist die eigene Fähigkeit des ANGREIFERS im selben
  Augenblick. Der `maybe_offer()`-Vertrag passte mechanisch, und beizutreten hätte den Namen und
  Docstring jener Liste zur Lüge gemacht (Fehlerklasse 11) → **eigene Listener-Liste
  `ShootingController.on_target_selected`**, aus derselben Stelle gerufen, mit `reactive=`
  durchgereicht.
- **Zahlen** — „after resolving all of this model's attacks against the target unit".
  `_finish_group()` ist pro Waffengruppe UND pro Cover-Untergruppe (13.08) und zahlte zu FRÜH,
  sobald eine zweite Waffe desselben Modells noch auf dieselbe Einheit feuert.
  `on_squad_finished_shooting` feuert einmal je Aktivierung und ist damit nie zu früh.
- **Die Waffenklausel wird EXAKT beantwortet, nicht gemessen vereinfacht** (User-Entscheidung
  „Exakt: neues Aktivierungs-Feld"): `ShootingController` führt jetzt
  `_resolved_weapon_names_this_activation` und beantwortet
  `resolved_weapon_against("Twin Tesla Destructor", target)`. Ein Ziel, auf das der Destructor nie
  gefeuert hat, zahlt nichts — als eigene Testzeile gemessen.
- **DRITTER Träger von `game/mortal_wound_sweep.py`**, und sein `start(squad, candidates=)` hatte
  seit Etappe 6 **KEINEN Aufrufer** — diese Etappe ist sein erster. Die Warteschlange trägt jetzt
  `(squad, candidates)`-Paare, und `_start_next_bearer()` re-gatet nur dann auf `can_use()`, wenn
  `candidates is None`.
- **Die Kandidaten werden bei der ZIELWAHL EINGEFROREN**, gegen das ZIEL gemessen (Ziel plus
  Feinde in 3" **des Ziels**) — eine Einheit, die danach wegläuft, wird trotzdem getroffen, und
  eine, die hereinläuft, nicht. Das ist der ganze Grund, aus dem der Parameter existiert.

#### Repair Barge: die VIERTE Tür in `reanimate()`

„LOST ONE OR MORE WOUNDS AS A RESULT OF THOSE ATTACKS" ist ein DELTA, und das ist die Klausel, die
ein bequemer Stellvertreter still fallen lässt: `_hit_target_squads_this_activation` ist über
TREFFER (ein geretteter Treffer kostet keine Wunde), und `recoverable_wounds() > 0` ist „hat JE
verloren" — eine vor zwei Runden beschädigte Einheit neben der Ark löste damit bei JEDER
Gegner-Aktivierung des restlichen Spiels aus. Also wird das Wundtotal jeder nahen
Warriors-Einheit bei der Zielwahl GESCHNAPPT und beim Abschluss verglichen.

- **`maybe_offer()` ist hier ein RECORDER** und gibt immer False zurück —
  `_offer_target_reactions()`s eigener Docstring sagt „each controller decides for itself whether
  it wants to act at all", und dieser entscheidet, hinzusehen und nichts zu sagen.
- **JEDE nahe Warriors-Einheit wird geschnappt**, nicht nur die beschossene: Mortal Wounds und
  Blast-Streuung können eine Einheit Wunden kosten, ohne dass sie je das gewählte Ziel war, und
  „as a result of those attacks" deckt das ab.
- **ZWEI Ledger, beide pro Zug, und sie sind NICHT dieselbe Frage:** `_used_this_turn` nach dem
  ARK-MODELL („once per turn ... THIS MODEL" — zwei Arks dürfen je einmal) und
  `_selected_this_turn` nach der WARRIORS-EINHEIT („the same unit ... not more than once per turn"
  — auch nicht von zwei verschiedenen Arks). In eines gefaltet bräche jedes den Fall des anderen.
- **Der Reanimator-Boost wird NICHT angewandt** — benannte Entscheidung, gleich zu den drei anderen
  Türen; anders zu antworten änderte AUSGELIEFERTES Verhalten an zwei Fähigkeiten, was die Aufgabe
  einer Datenblatt-Etappe nicht ist.

#### Die Ghost Ark: die erste exakt modellierte TEIL-Kapazität

Gedruckt: „a transport capacity of 10 NECRON WARRIOR models and 1 NECRONS INFANTRY CHARACTER
model" — zwei Pools mit verschiedenen Keyword-Regeln und verschiedenen Grenzen.
`transport_requires` kann das nicht ausdrücken (sein Vertrag ist „JEDES Modell hat JEDES Keyword",
also per Definition EIN Pool) und würde die realistische Ladung ABLEHNEN, weil 19.01 den Charakter
in den Trupp MERGT und dieses eine Modell kein Krieger-Keyword trägt.

- `transport_pools` ist das neue Feld, Default `()`, also ist **jeder bestehende Transport per
  Konstruktion unbewegt** — als eigene Testzeile gepinnt (eine Mengendifferenz: genau EIN
  TRANSPORT deklariert Sub-Pools), nicht behauptet.
- **DRITTER Konsument von `attached_units.model_has_datasheet_keyword()`** (der 39. Extraktion):
  „NECRON WARRIORS" ist ein Datenblattname ohne Profil-Flag, und nach einem 19.01-Merge ist der
  Abgleich gegen die `starting_models` der Komponente die einzige Granularität, auf der eine
  PRO-MODELL-Keyword-Frage überhaupt beantwortbar ist.
- **Gemessen, dass es etwas Echtes trennt:** 10 Krieger ✔, 10 Krieger + Overlord ✔, 20 Krieger ✘,
  20 + Overlord ✘, 10 Lychguard ✘, Immortals ✘, Overlord allein ✔. Die naheliegende Näherung
  (`capacity 11` plus `transport_requires_infantry`) hätte die verbotenen Fälle erlaubt.
- **DIE ZWEI POOLS SIND DISJUNKT**, also arbitriert „first fitting pool wins" nie — gemessen und
  gepinnt statt dem Zufall überlassen, dieselbe Behandlung, die `objective_control.py` seinen
  Settern gibt. Ein künftiges überlappendes Paar bräuchte eine echte Zuordnungssuche, und der
  Kommentar sagt, wo diese Entdeckung anfangen soll.
- **ALLES ODER NICHTS**, wie jede andere Klausel von 18.02: ein Modell, das in keinen Pool passt,
  lehnt die ganze Einheit ab.

#### Der Kill-Rig-Bug, im selben Commit mitgefixt

**User-Entscheidung.** `formations.embark_errors()` — 18.01, Declare Battle Formations — hat
`transport_requires` **nie gelesen**: 18.01 bot also an, was 18.02 mitten im Spiel ablehnt. Vor dem
Fix hatte das Feld repo-weit **genau EINEN** Leser. Dieselbe „ein Satz, zwei Leser, nur einer
antwortet"-Form, die dieses Repo für den Support-Artillery-Transportbann schon führt — und der
Beleg dafür, dass die Form wiederkehrt, nicht dass sie einmal vorkam. Die Sonde dafür muss
`test_kill_rig.py` röten, nicht nur die neue Suite.

#### Sprites

Zwei Einträge (`Catacomb Command Barge`, `Annihilation Barge`, beide mit exakt passendem
Dateinamen); **die Ghost Ark hat keine Kunst** und ist AM MODELL als Abwesenheit gepinnt, wie
Flayed Ones und Nekrosor Ammentar. Der Verschattungs-Sweep ist gemessen sauber: weder enthält
„Doomsday Ark" den String „Ghost Ark" noch umgekehrt, und die zwei Barges enthalten einander nicht.

#### Die Extraktions-Nummerierung war doppelt vergeben

Etappe 6 hat 45, 46 und 47 benutzt (`mortal_wound_sweep`, `post_deployment_redeploy`,
`Squad.check_min_enemy_distance`), Etappe 7 hat 45 und 46 ein zweites Mal vergeben. Die zwei aus
Etappe 7 heißen jetzt **48** (`end_battle_shock`) und **49** (`command_phase_cp`), und die dieser
Etappe ist die **50.** Aufgeschrieben, weil eine doppelt vergebene Nummer den Zweck der Liste —
„am wievielten Konsumenten wurde extrahiert" — genau verfehlt.

#### Getestet

Neu `test_necron_vehicles.py` (**233/233**, zehn Abschnitte) plus `ab_necron_vehicles.py`
(**37 Sonden, 44 Sondenläufe über sieben Suiten, alle beißend, keine stürzt ab**). Sechs Sonden
laufen gegen ein GETEILTES Modul und müssen mehr als eine Träger-Suite röten:
`test_wave_serpent.py` (**105/105**), `test_necron_abilities.py` (**113/113**),
`test_kill_rig.py` (**124/124**), `test_necron_ctan.py` (**203/203**),
`test_return_placement.py` (**161/161**), `test_event_chain_wiring.py` (**216/216**).
`test_necron_datasheets.py` **166/166** (die Zählpins von 41 auf 44 — genau die sichtbare
Änderung, für die sie gesetzt sind).

Volle Regression **220 Suiten, ~19995 Prüfungen, 219 grün / 0 rot / 1 bekannt**,
`run_tests.py --smoke` komplett grün (alle neun schweren Skripte), `selfplay.py map2 1500` mit den
Default-Armeen UND mit Necrons auf beiden Seiten (beide exit 0),
`test_weapon_characteristics.py` bei **null** Waffenabweichungen, der Golden Master unbewegt, und
zwei `fetch_datasheet_rules.py --offline`-Läufe ohne Diff.

**SIEBZEHN Sondenläufe bissen zunächst NICHT oder ließen die Suite ABSTÜRZEN, und fast jeder war
ein Befund über den TEST** (Fehlerklasse 24) — der teuerste Ertrag dieser Etappe:

1. **Malevolent Arcings Abschnitt 6 fuhr einen STUB statt des echten `ShootingController`**, also
   war die ganze `on_target_selected`-Naht ungemessen. Er fährt jetzt den echten Controller mit
   echten Würfeln.
2. **`isinstance()` ließ einen Fork durch:** der Pin „die Waffe ist die GETEILTE Klasse" bestand
   auch gegen eine Unterklasse. Jetzt `type(w) is cls`.
3. **Drei Ledger waren nur am FELD geprüft, nicht am VERHALTEN** (beide Repair-Barge-Konten und das
   Bearer-Ledger des Orbs) — ein Test, der ein Set inspiziert, besteht auch, wenn niemand es liest.
4. **Eine vakuöse Assertion** (`... or True`) war in Abschnitt 4 gelandet; ersetzt durch eine echte
   Wave-Serpent-Gegenprobe plus eine Liveness-Zeile.
5. **Zwei STALE Quell-Pins in `test_wave_serpent.py`** hörten mit der Extraktion auf, etwas zu
   bedeuten (`"wave_serpent_shield" not in inspect.getsource(fight)` und
   `"attached_unit_toughness" in inspect.getsource(wave_serpent_shield)`) — ersetzt durch eine
   echte Nahkampf-Messung und einen Pin auf der neuen Quelle.
6. **Die Already-embarked-Sonde fand einen Fall, den die Suite nie gefahren hatte.** Abschnitt 8
   rief `fits_pools()` DIREKT mit einer Ladung an Bord und bewies damit die ARITHMETIK; ob
   `can_embark()` die Ladung überhaupt weiterreicht, stand nirgends. **Und der Fall muss GEWÄHLT
   werden:** zehn Krieger an Bord lassen einen Platz frei, ein zweiter Krieger-Trupp wird also
   wegen seiner GRÖSSE abgelehnt und die Pools werden nie gefragt. Ein einzelner Overlord an Bord
   ist die unterscheidende Ladung — zehn Plätze frei, CHARACTER-Pool voll.
7. **Zwei Sonden ließen die Suite ABSTÜRZEN statt sie rot zu machen** (`_armed[id(...)]` mit
   `[...]` und das Iterieren einer in der Vor-Fix-Welt `None`-gewordenen Kandidatenliste) —
   **zweiundzwanzigste und dreiundzwanzigste Instanz** dieser Lehre. Beide degradieren jetzt und
   nennen je drei rote Zeilen.
8. **Die Toughness-Sonde KANN nicht beißen**, und das ist ein Befund über die DATEN statt über den
   Test — siehe den Extraktions-Abschnitt oben.

**Und ein eigener Fehler beim MESSEN der Sonden, achtzehnte Instanz von Fehlerklasse 18:** der
erste Sondenlauf lief durch `| tail -120`, also war der gemeldete Exit-Code der von `tail` und
nicht der des Skripts — „exit 0" stand neben „14 probe run(s) did not bite". Der Lauf wird jetzt in
eine Datei umgeleitet statt gepipet, und das ist wörtlich die Warnung, die CLAUDE.md seit Langem
trägt („beim Backgrounden nie durch `tail` pipen, wenn der Exit-Code zählt").

**Bewusst offen, wie in den Etappen 1-7:** `armies/necrons.json` unangetastet, alle drei *dormant
by roster*; `auto_players` in jedem neuen Controller, aber KEINE `ai/agent_driver.py`-Urteile —
keine der Wahlen ist armeeweit. Der KI-Negativraum-Sweep nimmt VOLLE Datenblattnamen, weil „Barge"
und „Ark" dort in vorbestehenden Kommentaren stehen.
