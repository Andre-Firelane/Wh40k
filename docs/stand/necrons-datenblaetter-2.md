# Necrons: Datenblatt-Nachzug (2)

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die restlichen Necron-Datenblätter — Fortsetzung

### Etappe 4 — TRIARCH (Triarch Praetorians, Triarch Stalker)

Die kleinste der neun Etappen, und die erste, in der ein gedruckter Waffenname
**GETEILT statt geforkt** werden muss — die inverse Fehlerform zu der, die
Etappe 3 dreimal fangen musste.

**Der Kollisions-Sweep lief VOR der ersten Klasse und kam andersherum heraus als
in Etappe 3.** `Particle caster` steht auf den Triarch Praetorians und ist
BYTE-FÜR-BYTE die Zeile der Canoptek Wraiths, die es schon gibt (12" A3 S5 AP0 D1,
[DEVASTATING WOUNDS] [PISTOL]). Die einzige abweichende Spalte ist BS (4+ Wraiths,
3+ Praetorians) — **und BS lebt in dieser Engine auf dem MODELL-PROFIL, nicht auf
der Waffe**, also gibt EINE Klasse jedem Träger seine gedruckte Fertigkeit
gratis. Ein Fork wäre genau der Fehler von Etappe 3 mit umgekehrtem Vorzeichen
gewesen.
- **Und die Prüfung dafür war zuerst eine TAUTOLOGIE** — sie verglich die
  geteilte Klasse mit sich selbst (beide Seiten lasen die Wraiths-Option), also
  wäre ein Fork ungehindert durchgekommen. Von der eigenen A/B-Sonde gefunden,
  die als einzige NO BITE meldete. Sie liest jetzt die Option des
  PRAETORIANEN-Datenblatts gegen die der Wraiths, plus die gelöste BS je
  Träger — zwei Zeilen, von denen ein Fork die eine besteht und die andere
  reißt.
- **Genau EIN per-Waffen-Skill-Override in diesem Schwung, und er ist gedruckt:**
  der `Particle shredder` des Stalkers sagt BS **2+**, während seine beiden
  anderen fertigkeitstragenden Zeilen 3+ sagen. Ein Modell, dessen eigene Zeilen
  sich WIDERSPRECHEN, ist genau der Fall, für den der Override existiert; die
  sieben übrigen Triarch-Waffen tragen keinen, und das ist als Menge gepinnt.
- **Der `Heat ray` ist EIN gedrucktes Datenblatt-Feld mit ZWEI Modi**
  (dispersed 2D6 [TORRENT] / focused [MELTA 4]), also ein Feuermodus-PAAR über
  `overcharge_profile` wie der Speer des Void Dragon — sonst feuerte der Stalker
  beide in einer Aktivierung (04.01). Nur die dispersed-Zeile steht im Loadout.

**Relentless Combatants: EIN Satz, ZWEI Klauseln, ZWEI Nähte** — und sie liegen
nicht nebeneinander.
- **Klausel 2 („eligible to declare a charge in a turn in which it Fell Back")
  hatte längst ein Zuhause**: `game/move_exceptions.py` besitzt 09.07s
  Charge-Bann. Neu ist nur WER — es ist die erste NECRON-Quelle in diesem Fold.
  **Nur die CHARGE-Hälfte**: der gedruckte Text sagt „declare a charge", nicht
  „shoot", und das ist der Unterschied zu Hovering Death daneben. Beide
  Richtungen gepinnt, und die Sonde, die sie in den SCHUSS-Fold legt, beißt.
- **Klausel 1 („you can re-roll Charge rolls made for this unit") ist die Arbeit**,
  und ihre Form ist Sudden Storms Advance-Reroll, eine Wurfart weiter:
  - **Angeboten VOR `acknowledge()`, und nur dort.** `acknowledge()` leert
    `pending_values`, und `reroll_all()` lehnt danach ab — ein Angebot eine Zeile
    später ist eines, das nicht angenommen werden kann. Als REIHENFOLGE in
    `main.py` gepinnt, mit eigener Sonde.
  - **EINMAL pro Wurf, über `DiceManager.claim_reroll_offer()`.** Ablehnen lässt
    exakt das Brett stehen, das die Frage erzeugt hat — die gemeldete
    Endlosschleife, für die dieser Helfer existiert.
  - **ALLES ODER NICHTS**: ein Charge-Wurf ist 2W6, und 15.02s eigene
    Formulierung für seine Wiederholung lautet „must be re-rolled in full", also
    `reroll_all()`. `can_reroll_all()` lehnt ab, sobald ein Würfel des Wurfs
    schon zweimal geworfen wurde — das hält Command Re-roll und dies vom Stapeln
    ab, und ist einzeln gemessen.
  - **Die KI antwortet in BEIDE Richtungen deterministisch**, und ihre Regel ist
    ENGER als die CP-zahlende in `ai/agent_driver.py`, weil dieser Reroll GRATIS
    ist: erreichte der Wurf NICHTS und könnte ein 12er etwas erreichen → werfen;
    erreichte er etwas → BEHALTEN (all-or-nothing, gratis macht das Verzocken
    einer lebenden Charge nicht gut); ist auch auf einer 12 nichts erreichbar →
    gar nicht erst fragen. Beide Antworten kommen aus
    `ChargeController.targets_reachable_with()`, dem ECHTEN 11.04-Tor, statt aus
    einer zweiten Kopie der Reichweiten-Arithmetik. **Ein MENSCH wird im zweiten
    Fall trotzdem gefragt** — einen Treffer gegen einen längeren zu tauschen ist
    ein echtes Urteil, dieselbe Teilung, die das CP-Verdikt an genau dieser
    Stelle macht.
  - **Der „hopeless"-Zweig war im TEST zuerst unerreichbar**, und das ist ein
    Befund über die Engine-Geometrie: 11.02s 12"-Deklarationstor und „auf einer
    12 erreichbar" sind DIESELBE Messung, ein Feind weit genug für aussichtslos
    ist also zu weit zum Deklarieren. Der Zustand entsteht erst, wenn sich das
    Brett MITTEN im Fenster ändert — real in dieser Engine (eine
    Deklarations-Reaktion kann ein deklariertes Ziel vom Brett nehmen, wofür
    `reopen_target_selection()` existiert). Die Bühne lässt den Feind nach der
    Deklaration abziehen, und die Sonde beißt danach.

#### `game/cover_denial.py` — 41. Extraktion, am zweiten Konsumenten

**Targeting Relay ist die Barrage of Filth des Defilers, Wort für Wort.** Beide
drucken „nach dem Schießen dieses Modells kann eine getroffene Feindeinheit bis
zum Ende der Phase keine Deckung haben"; die zwei Eröffnungen („each time this
model is selected to shoot, after resolving its attacks" gegen „after this model
has shot") unterscheiden sich im Wortlaut und nicht in der Bedeutung —
`on_squad_finished_shooting` feuert einmal je Aktivierung, also ist es dieselbe
Naht mit demselben Argument.
- **Geteilt ist genau das, was man zweimal subtil falsch macht:** die Kandidaten
  sind, was WIRKLICH GETROFFEN wurde (nicht was anvisiert wurde); es ist NICHT
  optional („select", nicht „you can" — die einzige Entscheidung ist WELCHE, und
  bei einem Kandidaten gibt es nichts zu fragen); die Marke lebt eine PHASE, nicht
  einen Zug; und eine befreundete Einheit ist nie Kandidat.
- **Eine Unterklasse besitzt ZWEI Knöpfe** — das Profil-Flag und den gedruckten
  Namen —, als Klassenattribute statt Konstruktor-Argumente: wer einen vergisst,
  scheitert LAUT bei der Konstruktion statt still eine namenlose Wahl anzubieten.
- **EIN Leser für die Verweigerung.** `_compute_benefit_of_cover()` fragt
  `cover_denial.denied(target_squad, (self.barrage_of_filth, self.targeting_relay))`
  statt zweier `if`s — die zwei können sich damit nie darüber uneinig werden, was
  „denied" heißt, und eine dritte Quelle ist ein weiterer Name an dieser
  Aufrufstelle, also im Diff sichtbar. Weiter ZUERST gefragt und False
  zurückgebend, weil „cannot have" absolut ist, während STEALTH, Miasma of
  Pestilence und die Rune of Mists Gewährungen sind.
- **BEFUND, benannt statt übergangen: Barrage of Filth hatte VORHER GAR KEINEN
  Verhaltenstest.** Drei Quell-Wächter in `test_death_guard_datasheets.py` pinnten,
  dass es GEBAUT, GEFÜTTERT und GELEERT wird — getrieben hat es nie jemand.
  `test_necron_triarch.py` §7 ist jetzt seine einzige Verhaltensabdeckung, und
  deshalb kann die Etappe-3-Lehre („eine Sonde auf die geteilte Basis muss BEIDE
  Suiten rot machen") hier nicht eingelöst werden — es gibt keine zweite Suite.
  Das steht im Kopf der Sondendatei, statt es zu übertünchen.

**Die Basisgröße des Stalkers ist eine ENTSCHEIDUNG, keine Transkription**: sein
Datenblatt druckt „Use model" (FRAME). 80 mm ist an der Myphitic Blight-hauler
ausgerichtet, dem nächstliegenden Rumpf, den diese Engine schon fieldet
(W10/T9 gegen seine W12/T8); die 2.1", die Defiler und Plagueburst Crawler
benutzen, sind die Größe für einen großen KETTEN-Rumpf, und ein Dreibein-Walker
ist das nicht. Als VERHÄLTNIS gegen die Blight-hauler gepinnt statt gegen eine
nackte Zahl, damit „warum diese Größe" den Pin überlebt.

**Kein `ai/agent_driver.py`-Urteil**, für beide als Negativraum geprüft: keine der
zwei Wahlen ist armeeweit, also antwortet jede in ihrem eigenen Controller über
`auto_players`.

**Getestet:** neu `test_necron_triarch.py` (**143/143**, acht Abschnitte) plus
`ab_necron_triarch.py` (**24 A/B-Sonden, alle beißend, keine stürzt ab**).
**Zwei Sonden bissen zuerst NICHT, und beide waren Befunde über den TEST**
(Fehlerklasse 24) — die Particle-Caster-Tautologie und der unerreichbare
Hopeless-Zweig, beide oben. **Zwei weitere ließen die Suite ABSTÜRZEN statt sie
rot zu machen** (22. und 23. Instanz dieser Lehre): ein `None < "3+"`-Vergleich
in der BS-Zeile (degradiert jetzt über einen Default), und eine Sonde, deren
EIGENE Änderung einen `NameError` erzeugte, weil sie die Klasse einsetzte, ohne
sie zu importieren — ein Sondenfehler, kein Testfehler, aber mit demselben
Ausgang.
- **Eine eigene Messung, die den Sweep halbiert hätte:** die erste Fassung von
  §8 rief `ast.get_source_segment()` für JEDEN Call-Knoten in `main.py`, was die
  Suite auf **36.3 s** brachte — die langsamste des ganzen Repos, gegen 0.2 s für
  alle anderen sieben Abschnitte zusammen. Die Aufrufausdrücke werden jetzt EINMAL
  aus den Zeilenspannen gebaut: **0.3 s**, dieselben Prüfungen.

Volle Regression **215 Suiten, ~18932 Prüfungen, 214 grün / 0 rot / 1 bekannt**,
`run_tests.py --smoke` komplett grün, `selfplay.py map2 1500` mit den
Default-Armeen UND mit Necrons auf beiden Seiten (beide exit 0).
`verify_rules_vs_engine.py` meldet unverändert **66 Differenzen, keine davon
nennt eine Triarch-Einheit**, und `test_weapon_characteristics.py` bleibt bei
**null** Waffenabweichungen. Der Korpus kostet weiter null Wartung: die zwei
Namen wandern von `MISSING_NECRONS` nach `faction.datasheets`,
`rules/necrons/` bleibt bei 49 Datenblättern, `git status --porcelain rules/`
ist leer.

**Bewusst offen, wie in den Etappen 1-3:** `armies/necrons.json` unangetastet,
beide *dormant by roster*; und keines der beiden Datenblätter wird von irgendetwas
GEFÜHRT oder führt selbst etwas — gemessen an den sechs LED-BY-Blöcken der Seite,
von denen keiner eine Triarch-Einheit nennt, statt aus dem Fehlen eines Eintrags
in der Paarungstabelle geschlossen.

### Etappe 5 — CANOPTEK (7 Datenblätter, drei Extraktionen, ein Altfehler)

Scarab Swarms, Spyders, Doomstalker, Reanimator, Macrocytes, Tomb Crawlers und
der **Geomancer** — die größte der Etappen. **19 von 32 Bauzielen.**

**Die Etappe ist von der MESSUNG de-riskt worden, nicht vom Plan.** Vier der
schwersten Einzelstücke waren gar keine: `pinned` existierte bereits (der Plan
hatte einen `shaken`-Zwilling vermutet), das Gloom Prism ist die Nullstone-Zeile
Wort für Wort, Sentinel Construct ist die Hexmark-Klausel mit einer anderen
Zahl, und die Canoptek Retinue ist die Cryptek Retinue minus einem Qualifier.

#### Drei Extraktionen, jede am ZWEITEN Träger

`game/pinned.py` (42.), `game/fnp_aura.py` (43.) und `game/retinue.py` (44.) —
Details in der Extraktionsliste in Teil 1. Was an allen dreien gleich ist: der
zweite Träger kam in DIESER Etappe an, also war die Extraktion fällig, nicht
vorgezogen.

- **Bei `pinned` ist die UHR das, was NICHT geteilt wird**, und das ist der
  ganze Unterschied zwischen den zwei Trägern: der Night Spinner pinnt bis zum
  Beginn des nächsten ZUGES, der Geomancer bis zur nächsten MOVEMENT-Phase —
  eine Phase später. Ein geteilter Reset hätte die eine Regel halbiert und die
  andere verdoppelt. Gemessen: `MonofilamentWebController.clear_for_turn_of()`
  lässt einen Geomancer-Pin STEHEN, und dessen eigene Grenze räumt ihn.
- **Bei `fnp_aura` ist `mortal_or_psychic_only` der Knopf, der zwei
  verschiedene REGELN daraus macht.** Das Gloom Prism und die Nullstone-Zeile
  sind 5+ gegen Mortal Wounds und Psychic Attacks; die Fabricator Claw Array
  ist 6+ gegen JEDE Wunde und nur für VEHICLES. Beide Knöpfe einzeln gemessen,
  weil eine Kopie, die einen davon verliert, jede andere Zeile besteht.
- **Bei `retinue` fällt der zweite gedruckte Parenthese-Satz aus 19.01 heraus** —
  „cannot have both a TOMB CRAWLERS and a CRYPTOTHRALLS unit joined to it", weil
  beide Datenblätter in derselben ROLLE stehen. **Gemessen, nicht behauptet, und
  genau daran hing der Fund unten.**

#### DER FUND: rule 19.01s Ein-pro-Rolle-Prüfung hat eine RETINUE nie gesehen

Etappe 2 hat `RETINUE` als DRITTE Anbindungsrolle eingeführt und dazu
aufgeschrieben, 19.01s Prüfung liefere die gedruckte Klammer „(a unit cannot
have more than one CRYPTOTHRALLS unit joined to it)" damit **gratis**. Sie tat
es nicht: `can_attach()` liest `leader_components()`, und dieser Helfer
(`is_leader_or_support`) deckt absichtlich nur LEADER und SUPPORT ab — eine
Cryptothralls-Einheit ist kein Charakter und darf 05.03/[PRECISION] nicht als
Leader-Modell gelten. Also sah die Prüfung **nie eine Retinue**.

- **Reproduziert vor jeder Änderung, für BEIDE gedruckten Klammern:** ein Host
  mit einer Cryptothralls-Einheit nimmt eine ZWEITE an (`can_attach → []`), und
  ebenso eine Tomb-Crawlers-Einheit daneben. Zwei Etappen lang unbemerkt.
- **Der Fix ist eine Zeile und für die zwei älteren Rollen per Konstruktion
  unbewegt**: dieselben Komponenten, derselbe Rollenfilter, ein Helfer früher
  (`components()` statt `leader_components()`). Volle Regression grün.
- **Warum die Suite es nicht sah, und das ist die Lehre:**
  `test_necron_rank_and_file.py` maß ausschließlich die
  DEKLARATIONS-Zeit-Liste, die `pregame.py` führt (`already_joined=`) — nicht
  die REGEL. Die Zeile daneben behauptete die Regel. Beide Hälften sind jetzt
  gepinnt, und die zweite ist die, die etwas wert ist.

#### Drei genuin neue Mechaniken

- **Weapon Sentinels ist der erste Ignore-Modifier-Filter dieser Engine auf dem
  WUNDWURF.** Die Hit-Hälfte gibt es seit [PSYCHIC] und Kauyon; die Wund-Hälfte
  hatte keinen Träger. EINE Funktion für beide Folds, weil der gedruckte Satz
  sie in einem Atemzug nennt — zwei Kopien wären zwei Chancen, dass eine
  aufhört, zur anderen zu passen. Der dritte gedruckte Halbsatz ist „ranged
  attack", also erreicht es `game/fight.py` NICHT, und die Abwesenheit ist
  gepinnt.
- **Das Accelerator Mandible ist die erste Änderung an einer WEAPON-SKILL-
  CHARAKTERISTIK.** Gedeckelt auf 2+ (`BEST_POSSIBLE_SKILL`), weil eine
  Charakteristik nicht besser als 2 werden kann.
- **Obelisk Node Control ist die erste Regel, die dem GEGNER vorschreibt, WO er
  ankommen darf** — und `game/units.py` hält namentlich fest, dass genau
  deshalb der T'au-Jammer-Array NICHT gebaut wurde („no ability in this engine
  has ever restricted where the other player may arrive"). Der Geomancer ist
  der zweite Träger, also der Punkt, an dem dieses Repo baut; die benannte
  Jammer-Array-Lücke ist damit einen Aufruf entfernt.
  - **Es hängt an `IngressController.position_valid()`**, der EINEN Stelle, die
    das grün/rote Overlay malt UND auf der `ai/agent_driver.py`s Kandidaten-
    Sweep filtert — ein Mensch sieht den Boden rot werden, und die KI bietet
    sich einen verbotenen Platz gar nicht erst an.
  - **Es fragt das MODELL, nicht seine Einheit** („within range of an objective
    marker YOU CONTROL" ist über den Träger geschrieben). Dafür bekam
    `game/objectives.py` seine per-Modell-Granularität (siehe die
    Extraktionsliste); die Suite misst es, indem sie den Geomancer vom Objective
    wegstellt und einen SQUADMATE darauf stehen lässt — die einzige Lage, in der
    die zwei Lesarten auseinandergehen.

#### Vanguard Protocols ist ein GEMESSENER No-op, und steht als solcher da

Der Geomancer gewährt Scouts 8", „if this model is attached to a CANOPTEK
MACROCYTES unit" — und die Macrocytes drucken Scouts 8" selbst, also hat die
gemergte Einheit sie nach 19.04s komponentenweiser Lesart ohnehin. Gemessen:
`scouts.scout_distance()` liefert **8 mit UND ohne** die Regel. Gebaut mit dem
Qualifier und von BEIDEN Seiten gepinnt, statt übersprungen oder als wirksam
ausgegeben; die A/B-Sonde zielt deshalb auf den QUALIFIER (jeder Host statt nur
MACROCYTES), weil eine Sonde auf die WIRKUNG hier per Konstruktion nicht beißen
kann.

**Zwei gedruckte Macrocyte-Optionen sind nur halb ausdrückbar** (Waffe gegen
Nicht-Waffen-Wargear) — dieselbe strukturelle Grenze, die das erste Menü des
Enforcer Commander schon protokolliert. Als KNOWN LIMITATION am Datenblatt
benannt.

#### Getestet

Neu `test_necron_canoptek.py` (**254/254**, zwölf Abschnitte) plus
`ab_necron_canoptek.py` (**34 A/B-Sonden, alle beißend, keine stürzt ab**).
`test_necron_rank_and_file.py` 102 → **102** (die Regel-Hälfte kam dazu),
`test_necron_destroyer_cult.py` 146 → **147**.

**VIER Sonden bissen zuerst NICHT, und alle vier waren Befunde über den TEST**
(Fehlerklasse 24):
1. Die OC-Floor-Zeile fragte `worsen_enemy_oc()` mit einem SCARAB-Modell —
   die Funktion sucht eine Scarab-Einheit unter den FEINDEN ihres Arguments,
   also maß die Zeile gar nichts. Jetzt an einem Feindmodell, mit einer
   Liveness-Zeile davor.
2. Der Ingress-Wächter prüfte den TEILSTRING `blocks_arrival(`, der ein
   vorangestelltes `False and ` überlebt — die Falle, die dieses Repo jetzt ein
   halbes Dutzend Mal bezahlt hat. Jetzt per AST: der Aufruf muss der ganze
   Test eines `if` sein, das den Platz ABLEHNT.
3. **Die Sonde auf `mortal_or_psychic_only` war gegen BEIDE Träger-Suiten
   deklariert und ist ein Befund über die SONDE**: sie neutralisiert einen Knopf
   der Gloom-Prism-INSTANZ, den die Nullstone-Aura nicht teilt. Die
   geteilte Hälfte ist der LESER in `fnp_aura.py`, und die hat jetzt ihre eigene
   Sonde, die beide reddened.
4. **Die Sonde „ein toter Aura-Träger strahlt weiter" biss nur EINE der zwei
   Suiten** — also maß `test_necron_destroyer_cult.py` das für die Nullstone-Aura
   gar nicht. Die Zeile ist dort ergänzt; das ist der Zweck der
   Doppel-Suiten-Regel, und dies ist die erste Etappe, in der sie wirklich
   einlösbar war (Etappe 4 musste sie mangels Verhaltenstest beim Nachbarn
   ausdrücklich schuldig bleiben).

Volle Regression **216 Suiten, ~19190 Prüfungen, 215 grün / 0 rot / 1 bekannt**,
`run_tests.py --smoke` komplett grün (alle neun schweren Skripte),
`selfplay.py map2 1500` mit den Default-Armeen UND mit Necrons auf beiden Seiten
(beide exit 0). `verify_rules_vs_engine.py` unverändert bei **66 Differenzen,
keine davon nennt eine Canoptek-Einheit**, `test_weapon_characteristics.py` bei
**null** Waffenabweichungen, und `git status --porcelain rules/` leer.

**Der `test_ere_we_go.py`-Fehlschlag (Suite seit Orks E2 gelöscht) im ersten Sweep ist die dokumentierte
VORBESTEHENDE Flake** — einzeln 44/44, unter dem Parallel-Runner ~1 von 3;
zwei weitere Sweeps meldeten 215 grün / 0 rot. Nicht dieser Arbeit zugeordnet
(Fehlerklasse 20).

**Bewusst offen, wie in den Etappen 1-4:** `armies/necrons.json` unangetastet,
alle sieben *dormant by roster*; `auto_players` in jedem der sechs neuen
Controller, aber KEINE `ai/agent_driver.py`-Urteile — keine der fünfzehn Wahlen
ist armeeweit. **Und der KI-Negativraum-Sweep darf NICHT nach „Canoptek"
suchen**: zwei VORBESTEHENDE Kommentare in `ai/agent_driver.py` zitieren einen
gemessenen Canoptek-Wraiths-Zug aus einem echten Log, das Wort steht dort also
schon.

### Etappe 6 — die drei C'tan (Deceiver, Nightbringer, Transcendent)

**22 von 32 Bauzielen; die Fraktion steht bei 37 von 64.** Der Schwung, dessen
Inhalt die ÜBEREINSTIMMUNG ist, nicht die Unterschiede: alle vier C'tan drucken
T11 Sv3+ W16 Ld6+ OC4, 4+ Invulnerable, FNP 5+, Deadly Demise D6, Deep Strike,
Necrodermis und Enslaved Star God, und unterscheiden sich in Move (10"/10"/8"/8"),
Base, Waffen und **genau einer** Fähigkeit.

- **`CtanShardProfile` macht die Übereinstimmung STRUKTURELL**, und der **Void
  Dragon ist mit reparentet** worden: eine Zusicherung „vier Datenblätter
  tragen dasselbe Chassis" lässt sich mit vier Kopien gar nicht ausdrücken
  (Kroot-Shaper-Präzedenz). Die Suite pinnt zusätzlich, dass keine Unterklasse
  einen der geteilten Namen ÜBERSCHREIBT — ein Drift liest sich sonst in jeder
  einzelnen Zeile korrekt.
- **Der Kollisions-Sweep kam LEER zurück**, als einziger Schwung des ganzen
  Nachzugs: keiner der sieben gedruckten Waffennamen steht irgendwo sonst im
  Korpus. Gepinnt wird deshalb die LEERE, über den Korpus gerechnet, samt der
  Gegenprobe, dass der Sweep die anderen 300+ Namen wirklich angesehen hat.
- **Kein Pro-Waffen-Skill-Override**, gemessen: alle vier drucken 2+ in jeder
  WS- und BS-Zelle. Der einzige Override der Fraktion bleibt der Particle
  Shredder des Triarch Stalker.
- **Die Scythe of the Nightbringer ist ein Feuermodus-PAAR** (strike/sweep, EIN
  gedruckter Eintrag) — sonst schwänge er nach 04.01 beide in einer Aktivierung.

#### `game/mortal_wound_sweep.py` (45. Extraktion) — und wo sie NICHT sitzt

„Ein D6 je Feindeinheit in einer Menge; wer besteht, nimmt Mortal Wounds."
**Drei gemessene Träger:** Drain Life (hier), Imotekhs *Lord of the Storm* (E7)
und die *Malevolent Arcing* der Annihilation Barge (E8).

- **Sie SUBKLASST `MortalWoundOfferController` statt es zu kopieren.** Jene
  Basis ist eine EIN-ZIEL-Maschine (ihre sechs Träger drucken alle „select one
  enemy unit"); diese drei drucken „for EACH enemy unit". Ersetzt wird also nur
  die Zielwahl — die 06.02-Klempnerei bleibt EINMAL geschrieben, für jetzt neun
  Träger. Genau diese Hälfte hat diese Engine zweimal kaputt ausgeliefert.
- **Eine WARTESCHLANGE, nicht `mortal_wound_sessions.py`s Liste** — die Form
  von `deadly_demise.py`, aus dessen Grund: der DiceManager hält EINEN Wurf,
  und jede Einheit braucht ihren Wundwurf ZWISCHEN Gate-Würfel und Zuteilung.
- **Das Gate ist EINE Handvoll, die Wunden sind ein Wurf JE EINHEIT.** Würfel i
  gehört Kandidat i, die Kandidatenliste wird beim Wurf also EINGEFROREN; die
  Wundbeträge können nicht zusammengefasst werden, weil sie an verschiedene
  Einheiten gehen und Lord of the Storms Betrag von seinem eigenen Gate-Band
  abhängt.
- **`active_player` wird NICHT geflippt, und das ist gemessen:** Deadly Demise
  flippt, weil seine Detonation FREUND UND FEIND fängt; hier ist jeder Kandidat
  per Definition ein Feind des Trägers, teilt also in einem Zwei-Spieler-Spiel
  einen Besitzer.
- **`start_many()` reiht mehrere TRÄGER auf.** Das Ende-der-Fight-Phase-Fenster
  gehört keinem Spieler, beide Seiten können also im selben Moment eine Sweep
  schulden — gequeut statt fallengelassen.

#### `game/post_deployment_redeploy.py` (46. Extraktion) — und der dritte Träger, der NICHT mitkommt

Grand Illusion druckt Kauyons *Solid-image Projection Unit* mit zwei geänderten
Wörtern (NECRONS statt T'AU EMPIRE, Datenblatt statt Enhancement). Also die
Extraktion am zweiten Träger; `SolidImageProjectionStep` ist jetzt eine
Unterklasse und **re-exportiert `MAX_UNITS`/`REDEPLOY`/`RESERVES`**, damit kein
Leser sich bewegt (`test_tau_enhancements.py` 361/361 ohne eine Anpassung).

- **`game/prince_of_corsairs.py` ist ein DRITTER Träger und wird bewusst NICHT
  umgestellt:** es druckt denselben Satz für AELDARI, implementiert aber nur die
  Strategic-Reserves-Hälfte und legt nie eine Einheit zurück in die
  Aufstellungs-Queue, obwohl sein eigenes „and redeploy them" das verlangt. Es
  einzufalten wäre kein Refactor, sondern eine Verhaltensänderung an einer
  ausgelieferten Aeldari-Fähigkeit — eine eigene Etappe. Benannt statt später
  wiederentdeckt.
- **„If your army INCLUDES this model" ist NICHT „if it is on the
  battlefield"**, und das ist die eine Klausel, die eine Kopie des T'au-Zwillings
  verliert: Prince of Corsairs sagt ausdrücklich das Zweite und hält im eigenen
  Docstring fest, der Reservefall sei der, der still weiterliefe. **Hier ist der
  Reservefall RICHTIG** — ein deep-struck Deceiver gewährt Grand Illusion
  weiterhin, also liest `grants()` `GameState.all_squads()` statt der Tokenliste.
- **„Regardless of how many units are already in Strategic Reserves" ist ein
  belegter NO-OP** — 20.01s Deckel wird in `finish_formations_for()` erzwungen,
  das zu diesem Zeitpunkt längst gelaufen ist.
- `main.py`s `_RedeployChain` nimmt den dritten Konsumenten als **ein weiteres
  Argument**.

#### Transdimensional Displacement — drei Klauseln, drei vorhandene Nähte

1. *„no maximum distance"* → `start_run()`s Kein-Wurf-Zweig, **vierter Träger**
   nach Whirling Death, Aggressive Mobility und Time to Strike.
2. *„through all types of model"* → `clamp_move()`s MODELL-Bypass neben
   Desperate Escape und Scuttling Walker. **Nicht der FLY-Zweig darüber**: der
   gedruckte Text nennt Modelle und sagt zu Gelände nichts, eine Wand hält also.
3. *„more than 8" from all enemy units"* → `Squad.check_min_enemy_distance()`,
   Regel 24.32s Scout-Clearance mit **parameterisiertem Wortlaut** (47.
   Extraktion, zweiter Konsument; `check_scout_move_clearance()` bleibt als
   Name stehen, damit die elf vorhandenen Leser sich nicht bewegen).

- **KEIN Advance-Wurf, und das ist eine ENTSCHEIDUNG statt einer
  Transkription** — der gedruckte Text sagt nicht „do not make an Advance
  roll", er entfernt das MAXIMUM. Wörtlich gelesen wäre das ein D6, dessen Wert
  nichts ändern kann, und diese Engine wirft solche Würfel nicht
  (`coordinated_leadership.py`s Begründung); Command Re-roll würde obendrein
  darauf angeboten. Im Modul ausgeschrieben, weil die Gegenlesart vertretbar ist.
- **Das Budget ist die BRETTDIAGONALE, nicht `float("inf")`** — `remaining_range`
  füttert Arithmetik (`budget / dist`), und eine Unendlichkeit dort ergibt beim
  ersten Null-Zoll-Segment NaN.
- **Ein PANEL-KNOPF neben „Advance"**, weil „you can use this ability" eine Wahl
  ist — dieselbe Form, in der 21.03s Take to the Skies seine Alternative
  anbietet. Der §13-Wächter hat den neuen `start_*` sofort gemeldet und ist als
  PHASEN-Starter klassifiziert (kein Out-of-phase-Modus).

#### Ein gefundener, NICHT behobener Altfehler

**VIER Definitionen von „ist das eine NECRONS-Einheit", in ZWEI Lesarten:**
`awakened_dynasty.is_necrons_unit()` liest das DATENBLATT-Keyword;
`multi_threat_eliminator.py`, `reanimation_boost.py` und `spyder_wargear.py`
tragen je eine byte-identische Kopie, die stattdessen das Pro-Modell-Flag
`reanimation_protocols` liest. Auf den gebauten Datenblättern stimmen sie
überein (jedes Necron-Blatt druckt die Armeeregel), heute ist also nichts
falsch. Grand Illusion importiert die Datenblatt-Lesart, statt eine FÜNFTE
anzulegen; das Zusammenlegen der drei Kopien berührt Module aus den Etappen 3
und 5 und ist eine eigene Messung.

Nebenbei PUBLIC geworden: `mortal_wound_abilities.py`s `_bearers`,
`_enemy_squads` und `_gap` heißen jetzt `bearers`, `enemy_squads` und `gap_to`
— dieselbe Behandlung, die `MortalWoundOfferController` beim sechsten Träger
schon bekam.

#### Getestet

Neu `test_necron_ctan.py` (**202/202**, acht Abschnitte) plus
`ab_necron_ctan.py` (**26 A/B-Sonden, alle beißend, keine stürzt ab**).
`test_necron_datasheets.py` **166/166** (die zwei Zählpins von 34 auf 37 —
genau die sichtbare Änderung, für die sie gesetzt sind),
`test_event_chain_wiring.py` **186/186**.

**SIEBEN Sonden bissen zuerst NICHT**, und sechs davon waren Befunde über den
TEST — der teuerste Ertrag dieser Etappe:

1. **Der fehlende Allokations-Drain** wurde nicht gesehen, weil die Suite kein
   EIN-MODELL-Ziel fuhr: bei mehreren Modellen räumt der Klick des Tests die
   Session ohnehin. Genau der Fall, an dem die Klasse zweimal jahrelang
   überlebt hat. Jetzt mit einem Ein-Modell-Opfer und **ohne einen einzigen
   Klick** gemessen.
2. **Die Träger-Warteschlange** war ungefahren → ein Zwei-Nightbringer-Szenario.
3. **Der NECRONS-Filter** war auf einem reinen Necron-Brett unmessbar → eine
   Ork-Einheit desselben Spielers daneben.
4. **Der Durchquerungs-Bypass** war nur am Quelltext gepinnt → jetzt durch
   `clamp_move()` gemessen, beide Läufe mit denselben 6".
5. **Der Panel-Knopf** war ein Quell-Grep, den ein `if False:` überlebt → jetzt
   ein echter Render mit Spion auf `_draw_button`. Die strukturelle Lücke, die
   beide Stratagem-Audits gefunden haben.
6. Eine Sonde zielte auf die T'au-Suite, die `remaining()` gar nicht liest.
7. **Die siebte war ein Befund über den CODE**, und der ist eingebaut worden:
   `_pending` überspannte die ganze Sweep, wodurch jeder andere Term von
   `is_busy` INERT war und nur defensiv AUSSAH. Der Slot wird jetzt freigegeben,
   sobald das Gate aufgelöst ist — er hält den Gate-Kontext und sonst nichts.

Volle Regression **217 Suiten, ~19392 Prüfungen, 216 grün / 0 rot / 1 bekannt**,
`run_tests.py --smoke` komplett grün (alle neun schweren Skripte),
`selfplay.py map2 1500` mit den Default-Armeen UND mit Necrons auf beiden Seiten
(beide exit 0), `test_weapon_characteristics.py` bei **null**
Waffenabweichungen, und `git status --porcelain rules/` bis auf das Abrufdatum
leer (zwei `--offline`-Läufe erzeugen 50 byte-identische Necron-Dateien).

**`verify_rules_vs_engine.py` geht von 66 auf 67 Differenzen, und die eine neue
Zeile IST die Entscheidung:** `C'tan Shard of the Deceiver base 40mm -> 80.0mm`.
Nightbringer und Transcendent C'tan erzeugen **null** — Statline, Waffen und
Punkte stimmen dort auf den Wert. Der Deceiver druckt 40 mm für ein
16-Wunden-MONSTER (Void Dragon 80, Nightbringer 90, Transcendent 60);
User-Entscheidung ist die Tischgröße des Void Dragon, gepinnt als Verhältnis
gegen dessen Feld statt als Zahl, mit der gedruckten 40 im Kommentar.

**Bewusst offen, wie in den Etappen 1-5:** `armies/necrons.json` unangetastet,
alle drei *dormant by roster*; `auto_players` in beiden neuen Controllern, aber
KEINE `ai/agent_driver.py`-Urteile. **Und der KI-Negativraum-Sweep darf NICHT
nach „C'tan" suchen** — das Wort steht dort schon dreimal, in vorbestehenden
Kommentaren über Charge-Geometrie (`:3771`, `:3774`, `:9893`); der Sweep nimmt
volle Datenblattnamen, dieselbe Falle wie „Canoptek" in Etappe 5.
