# Regelengine: Command-Phase, Stratagems, Schaden, Status

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Regelengine — Command-Phase / Stratagems / Schaden

- Battle-Shock (01.07/08.03), Command Points (08.02), alle Core-Stratagems mit Anwendungsfall:
  Command Re-roll (15.02), Insane Bravery (15.04), Explosives (15.05), Crushing Impact (15.06),
  Rapid Ingress (15.07), Fire Overwatch/Snap Shooting (15.08/15.09), Heroic Intervention (15.11),
  Counteroffensive (15.12), Epic Challenge (15.03). `StratagemController` trägt die 15.01-Buchführung
  (einmal pro Phase/Ziel, optional `max_per_battle`, optional `allow_battle_shocked_target`).
  `_cost_for()` ist die EINE Definition des Preises, gelesen von `can_use()` UND `use()`; Rabatte
  hängen als Liste `cost_discounts` dran (Puretide, Strands of Fate).
- **Explosives (15.05): „eligible to shoot" heißt „hat diese Phase noch nicht geschossen" —
  und der gedruckte Text, der das entscheidet, lag zwei Jahre ungelesen im HTML-Cache.**
  Gemeldet: *"explosives geht nur vor dem schießen, weil man eligible to shoot sein muss. ich
  konnte es aber nach dem schießen machen."* `can_use()` endete bei `available_shooting_types()`
  (10.02 Schritt 2, das von geschossen-haben nichts weiß) und fragte `ShootingController` NIE —
  es bekam nicht einmal einen. Das war KEINE Nachlässigkeit, sondern eine ausdrücklich
  dokumentierte Annahme: `CLAUDE.history.md:150` hält fest, sie sei **„mangels weiterer
  Regeltexte"** getroffen worden.
  - **Der fehlende Text steht in `rules/.cache/<fraktion>.html`**, im Core-Stratagem-Block jeder
    Fraktionsseite: *"TARGET: One friendly unengaged EXPLOSIVES / GRENADES unit that is eligible
    to shoot and did not make an advance move this turn."* Der Korpus (`rules/*/*.md`) hält NUR
    Datenblätter, Armeeregeln und Detachments — die Kernregeln überleben als Tooltips im Cache,
    und das steht jetzt in `rules/README.md`, weil dort der nächste Leser sucht.
  - **Die TARGET-Zeile trägt DREI unabhängige Klauseln**, und keine impliziert eine andere:
    10.06 lässt ein engagiertes MONSTER/VEHICLE herausschießen (`can_shoot()` sagt also JA, wo
    das Stratagem nein sagt), und 09.06 kostet einen Advance die Charge und die Aktion, nie das
    Schießen — deshalb druckt die Karte die Advance-Klausel separat. Im Test wird jede an einem
    Fall belegt, in dem `can_shoot()` WEITER True sagt ([ASSAULT] nach einem Advance, ein
    engagierter Deffkopta); ohne die zwei sähe „wir haben eine redundante Zeile gelöscht"
    richtig aus.
  - **`can_shoot()` statt einer Handnachbildung** aus `shot_squad_ids` + `available_shooting_types()`:
    der gedruckte Text nennt einen BEGRIFF, den diese Engine an genau einer Stelle beantwortet —
    derselben, die der Shoot-Knopf benutzt. Die Nachbildung wäre ein FALSCHES Subset (ihr fehlt
    16.01s Aktionsschloss, dessen eigener gedruckter Satz *"it is not eligible to shoot"* lautet).
    ~15 Geschwistermodule machen es schon so; `greater_good.py:297-302` hatte genau die
    Kombination, die Explosives zur Hälfte fehlte. Dazu der `active_squad is squad`-Wächter:
    `shot_squad_ids` bucht den ABSCHLUSS, eine Einheit mitten in ihrer Aktivierung wurde aber
    schon ausgewählt.
  - **`active_player` → `turn_owner` gehört zum Fix**, nicht daneben: `can_shoot()` liest
    `turn_owner`, zwei Tore in EINER Funktion dürfen „ist das meine Phase" nicht mit zwei
    Feldern beantworten. Praktisch flackerte der Knopf bei jedem Verteidiger-Save weg — und über
    `ai/agent_driver.py:9070`, das ein False als DAUERHAFTE Absage für die Phase cacht, wäre
    daraus ein Korrektheitsfehler geworden.
  - **Zu `can_use()` gab es GAR KEINEN Test**, und das ist der Grund, warum es überlebt hat.
    Neu `test_explosives.py` (**28/28**, die gemeldete Folge durch eine ECHTE Aktivierung) plus
    `ab_explosives_eligible_to_shoot.py` (**6 A/B-Sonden, alle beißend**) und der Quell-Wächter
    `test_event_chain_wiring.py` §22 (per AST — die Funktion nennt in ihren eigenen Kommentaren
    jeden geprüften Begriff, `active_player` eingeschlossen, ein String-Sweep fiele auf seine
    eigene Erklärung herein). **Kein `verify_*.py`:** Einheit, Ziel in 8" mit Sichtlinie, CP und
    eine abgeschlossene Aktivierung müssten alle gestellt werden, dann bliebe keine echte
    Tatsache übrig; die eine Frage, die nur `main()` beantwortet, hält §22 in Millisekunden.
- **Heroic Intervention (15.11) hatte GAR KEINEN Test — der gemeldete CP-Fehler existiert aber
  nicht.** Gemeldet als "ich habe heroic intervention benutzt mit dem avatar, aber die cp scheinen
  nicht abgezogen geworden zu sein". Dieselbe Ausgangslage wie 15.12 (das ohne Test ein 2-CP-No-op
  war), also war der Verdacht berechtigt; die MESSUNG widerlegt ihn.
  - **Das Hauptbuch stimmt, an zwei unabhängigen Belegen.** Im gemeldeten Log
    (`game_20260903_212406`… bzw. `game_20260903_212846.log` Z. 422) steht `Player 1 spends 1 CP`
    direkt vor `Player 1 uses Heroic Intervention`, und eine Nachrechnung ÜBER DIE GANZE SCHLACHT
    — verankert an den fünf `now has N CP`-Zeilen, die der Log selbst druckt — geht ohne
    Abweichung auf (4/4/3/3/3). Zusätzlich hat JEDE `spends`-Zeile des Laufs eine passende
    `uses`-Zeile; die drei Ausnahmen sind Strands of Fate bzw. My Will Be Done mit `spends 0 CP`.
  - **`test_heroic_intervention.py` (neu, 35/35, vier Abschnitte)** treibt den ECHTEN
    `HeroicInterventionController` gegen ein ECHTES CP-Konto und einen ECHTEN `ChargeController`:
    1 CP beim Annehmen, dem REAGIERENDEN Spieler belastet, GENAU EINMAL (der Modus-Prompt ist eine
    zweite Entscheidung und darf nicht erneut kassieren), nichts beim Anbieten, nichts beim
    Ablehnen, kein zweiter Kauf in derselben Phase (15.01). **A/B: mit entferntem `use()`-Aufruf
    fallen 6 von 35** — die Suite würde den gemeldeten Fehler fangen, wenn es ihn gäbe.
  - **Die ZWEITE Hälfte ist `active_player`, und die ist der eigentliche Grund für die Suite.**
    15.11 läuft AUSSERHALB der Phase des Reagierenden, `offer()` dreht `active_player` also um,
    und JEDER Ausgang muss zurückdrehen — Ablehnen, der beendete Charge, UND der deklarierte,
    aber nie ausgeführte Charge (ein zu kurzer 2W6, dann Cancel; der häufigste Ausgang). Ein
    vergessener Pfad ließe den Reagierenden für den Rest der Schlacht aktiv, und
    `game/command_reroll.py` belastet CP gegen `active_player` — der NÄCHSTE Command Re-roll ginge
    also aufs falsche Konto. Genau die Form, die als "CP stimmen nicht" auffiele; alle drei
    Ausgänge sind einzeln gemessen und alle drei stellen korrekt wieder her.
  - **Die Bühne der Suite prüft ihre eigenen zwei Schranken**, statt sie zu glauben: die Lücke von
    5" ist Mitte-zu-Mitte, also 2.8" Kantenabstand — außerhalb 03.04s Engagement Range (eine
    gebundene Einheit ist nicht berechtigt) und innerhalb 15.11s 6". Die erste Fassung stand bei
    4.0" und war ENGAGED, also scheiterte alles aus dem falschen Grund.
- **Command Re-roll (15.02) zahlt und zielt über die WÜRFELNDE EINHEIT, nicht über
  `active_player`** (User: "ich konnte gerade command reroll in der selben aktiverung 2 mal
  einsetzen. einmal bei wound, einmal bei damage", mit den zwei Regeln: jedes Stratagem einmal pro
  Phase; eine Einheit pro Phase nur von einem Stratagem gezielt).
  - **Im Log reproduziert** (`logs/game_20260912_225758.log` Z. 217-221): „Player 1 uses Command
    Re-roll" auf den Wound Roll, dann „**Player 2** spends 1 CP / uses Command Re-roll" auf Player 1s
    Bright-Lance-**Damage**-Roll. Die KI hat den zweiten Re-roll des Menschen BEZAHLT.
  - **EINE Ursache für beide Regeln.** Der Controller las `turn_tracker.active_player` und reichte
    `targets=[]`. Der Save-Schritt gibt `active_player` an den Verteidiger, und beim Damage-Wurf des
    Angreifers steht es noch dort — 15.01s `(player, name)`-Schlüssel war also der des GEGNERS und
    fand nichts. Ohne Ziel konnte „eine Einheit, ein Stratagem" nie ablehnen
    (`allow_repeat_target=True` stammte aus der Zeit, als es ohnehin kein Ziel gab).
  - **`DiceManager.rolled_for` ist ein REGEL-Feld**, anders als `attacker_squad`/`target_squad`
    (Darstellung, und bei Save/Charge jeweils die andere Seite). Alle **23** Stellen in `game/`, die
    einen re-rollbaren Wurf werfen, nennen ihre Einheit: Hit/Wound/Attacks/Damage → Angreifer,
    Save → Ziel, Charge/Advance → Beweger; `DiceNotationRoll` reicht es durch. Command Re-roll zahlt
    `rolled_for.owner`, zielt `[rolled_for]` und ist ohne Einheit **fail-closed** statt geraten.
  - **Zwei ENTSCHEIDUNGEN, keine Transkription:** der X-Wurf von Deadly Demise gehört der
    DETONIERENDEN Einheit (vorher dem getroffenen Besitzer, der so seine eigenen Mortal Wounds
    re-rollen konnte), der Sweep-Wundwurf (Drain Life, Lord of the Storm, Malevolent Arcing) dem
    Träger (`_sweep_bearer` — `_pending` ist nach dem Gate schon freigegeben).
  - **Folgen, die mitkommen:** 01.07 greift jetzt (der Wurf einer battle-shocked Einheit ist nicht
    mehr re-rollbar), und Insane Braverys Docstring-Satz „Command Re-roll zählt mit" stimmt erst jetzt.
  - **Zweiter, nicht gemeldeter Befund: das Würfelpanel bot die drei Knöpfe auch auf KI-Würfen an.**
    `roll_choice.ability_actions()` fragte weder bei Command Re-roll noch bei Targeting Array /
    Crystal Matrix noch bei den Unmodified-Six-Fähigkeiten, wem der Wurf gehört — ein Klick gab CP,
    Token oder Nutzung der KI aus. `human_players=` (main.pys lebende Sicht) filtert jetzt über
    `roll_owner()` bzw. den Squad der Quelle; `None` lässt die Stub-Suiten unberührt. **Die
    Owner-Frage geht per LAMBDA**: schon der Attributzugriff auf einem Stub ohne `roll_owner`
    krachte (eigener Fehler, von `test_roll_choice.py` gefangen).
  - **KI-Pfad:** `_maybe_command_reroll()` vergleicht `roll_owner()` — vorher wurde die KI zu ihren
    EIGENEN Damage-Würfen nie gefragt.
  - **Getestet:** neu `test_command_reroll.py` (**58/58**, neun Abschnitte — die gemeldete Folge
    end-to-end durch den echten `ShootingController` mit Liveness „der Verteidiger ist beim
    Damage-Wurf aktiv", Zahler je Wurfart, beide 15.01-Hälften auf echtem `StratagemController`,
    01.07, fail-closed, Panel-Gate, KI-Pfad, und ein AST-Wächter: jeder re-rollbare Wurf nennt seine
    Einheit, ein Literal `None` zählt nicht, und wo der Aufruf beide Seiten zeigt, die RICHTIGE).
    `ab_command_reroll_owner.py`: **10 A/B-Sonden, alle beißend**. `test_reroll_once.py`s
    handgestagte Würfe nennen jetzt ihre Einheit; `test_tau_vehicles.py`s Pin auf die schließende
    Klammer liest jetzt die Argumente. Volle Regression **228 Suiten, ~20938 Prüfungen, 227 grün /
    0 rot / 1 bekannt**.
- **Ein Würfel wird NIE zweimal neu geworfen.** `DiceManager.already_rerolled` ist das Gedächtnis
  dafür (überlebt `acknowledge()` absichtlich); Command Re-roll, [TWIN-LINKED], Forward Observers,
  Breach and Clear und jede Ability-Quelle lesen es. Vier illegale Paarungen waren vorher möglich.
  Breach and Clear behält beim Vollwurf die Wunden zurückgehaltener Würfel.
- **Reroll-Umfang folgt dem Wortlaut**: "re-roll the Wound roll" = GANZER Wurf (Breach and Clear,
  Sunforge, Assured Destruction, Storm of Silence), "re-roll FAILED" = nur Fehlschläge
  ([TWIN-LINKED] — ausdrückliche User-Korrektur). **Wo ein Vollwurf angeboten wird, gibt es
  zusätzlich die Nur-Fehlschläge-Teilmenge — seit 2026-09-11 AUCH bei den sieben
  `ONES_OR_WHOLE_LABELS`-Quellen**, die sie vorher unterdrückten; der Grund dafür war eine falsche
  Lesart desselben Satzes, den `shooting.py` vier Zeilen weiter richtig herum las (siehe
  `## Vier Meldungen aus einer T'au-gegen-Death-Guard-Partie`). Was diese sieben unterscheidet, ist
  nur, dass ihre 1er-Klausel MANDATORISCH ist, "Keep result" dort also keine legale Antwort ist.
- **Deadly Demise (24.08)** würfelt die Schadensmenge PRO EINHEIT (ein geteilter Wurf machte aus
  ~14 erwarteten 24 Mortal Wounds).
- **Wundzuteilung**: Allocation-Groups sortieren "schwächste zuerst" mit ABSOLUTEN Restwunden als
  Term — sonst stand der 2W-Anführer vorn und die erste Wunde wurde ohne Rückfrage auf ihn gelegt.
  Die KI wählt innerhalb der Gruppe das erste NICHT-`squad_leader`-Modell. Regeln schlagen die
  Präferenz (05.04s verwundetes Modell zuerst, 05.03s CHARACTER-Schutz).
- **Save-Schwelle**: `damage_resolution.save_thresholds()` ist die EINE Definition (Rüstung, AP,
  Invuln, Ramshackle) — Auflösung und Würfelanzeige lasen sie vorher getrennt, weshalb ein über den
  Invuln geretteter Würfel rot gezeigt wurde.
- **Ein Save Roll, den niemand bestehen kann, wird gar nicht erst geworfen** (User: "Save Rolls,
  die man gar nicht bestehen kann, sollten auch gar nicht gewürfelt werden. Manchmal werden da
  6en gewürfelt, die dann aber rot sind"). `damage_resolution.save_is_impossible()` ist die eine
  Definition, `AUTO_FAILED_SAVE = 1` der Platzhalter (05.04: eine unmodifizierte 1 scheitert
  immer, also ist das die eine Zahl, deren Ergebnis feststeht — es werden keine Würfel erfunden).
  - **Reproduziert vor der Änderung:** Gauss Destructor (AP-4) gegen Sv4+ Windriders ohne
    Rettungswurf braucht eine **8+**. Jeder Würfel ist rot, bevor er fällt, und das Panel hält
    das Spiel trotzdem für eine Entscheidung an, die es nicht gibt.
  - **Gefragt wird JEDES lebende Modell der Zieleinheit, nicht der Repräsentant** — und das ist
    die einzige Sorgfalt an der ganzen Änderung. Die Wurfstellen bemaßen ihr Panel über
    `displayed_save_threshold()` für EIN Modell (`allocation_target_model()`), aber
    `DamageAllocationSession._advance()` leitet `save_thresholds()` PRO MODELL neu ab. Gemessen
    an Windriders + Warlock Skyrunner: die Leibwache braucht 8+, der Charakter rettet auf seinen
    4+ Invulnerable — auf dem Repräsentanten zu überspringen hätte dessen Rettungswurf still
    gelöscht. Eigene Testzeile mit echter Attached Unit.
  - **VERHALTENSNEUTRAL außer dem Wurf**, A/B belegt: derselbe Ausgang (Modell zerstört), nur
    ohne Panel-Schritt. Die Gegenprobe steht daneben — dieselbe Waffe gegen Warlock Skyrunners
    (4+ Invulnerable gegen AP-4) wirft weiter und rettet; ohne sie bestünde der Abschnitt auch,
    wenn der Fix jeden Save Roll im Spiel entfernt hätte.
  - **[PRECISION] überlebt den Skip.** Wohin die Wunden fallen, ist eine Frage des ANGREIFERS und
    davon unabhängig, ob ein Würfel sie hätte stoppen können — deshalb teilen der bestätigte und
    der übersprungene Pfad EINE Fortsetzung (`_continue_after_save()`, je eine in `shooting.py`
    und `fight.py`), statt den Zweig zu duplizieren.
  - **Das Log lügt nicht**: statt einer erfundenen Würfelliste steht dort
    `save roll (not rolled - no save is possible, needed 8+): 0 saved, 1 failed.` plus eine
    eigene Zeile mit dem Grund. Ein Wurf, der stattfand, listet weiter seine Würfel — die beiden
    lesen sich verschieden, und genau das ist im Test gepinnt.
  - **Alle VIER `roll_kind=SAVE_ROLL`-Stellen** (je zwei in `shooting.py` und `fight.py`, die
    gewöhnliche und die kritische Teilmenge) gehen durch dasselbe Tor; ein Quell-Wächter zählt
    Stellen gegen Tore, ein fünfter kann nicht ungegated dazukommen.
  - **Getestet:** neu `test_impossible_save_skip.py` (**29/29**, fünf Abschnitte) plus zwei
    A/B-Sonden an der QUELLE, jede kippt genau ihre eigenen Prüfungen — das Prädikat
    abgeschaltet 5 von 29, auf den Repräsentanten verkürzt **genau die eine** Mixed-Unit-Zeile.
    Die 6+/7+-Grenze ist von BEIDEN Seiten gemessen, sonst bestünde der Test mit `>= 6` genauso.
  - **Ein fremder Pin wurde dabei zu Recht rot** (`test_aeldari_enhancements.py`): er pinnte den
    Wortlaut `if self._precision_choice_needed(split_weapon, target_squad):`, den der geteilte
    Fortsetzungspfad verschoben hat. Er prüft jetzt die zwei AUFRUFAUSDRÜCKE statt einer
    Anweisungsform — dieselbe Lehre wie bei den früheren Interpunktions-Pins.
- **Molten Form** (Avatar) ist die erste Halbierung: aufgerundet (Kernregel-Konvention), VOR Feel No
  Pain, an beiden Stellen, an denen die Session einen Betrag festlegt. Mortal Wounds sind ausgenommen.
- **Emergency Disembark**: Reihenfolge ist Platzierung → Hazard-Wurf → Deadly Demise (vorher lief der
  Wurf VOR der Platzierung, und seine Mortal Wounds waren prinzipiell unzuteilbar, weil die Modelle
  nicht auf dem Brett standen — ein harter Deadlock). Ein gescheiterter Notausstieg tötet die Modelle
  jetzt wirklich über die normale Todes-Pipeline.

## Terrain / Objectives / Status

Terrain-Kategorien (13.02-13.06), Obscuring (13.10), Deployment Zones, Objectives (14.01-14.03 inkl.
Secured), `game/modifiers.py` für nachvollziehbare Wurf-Anpassungen. Status (`game/status_effects.py`):
Battle-Shocked, Hidden (13.09, Hausregel 12" statt 15" bei Wand auf dem eigenen Footprint), Marked,
plus die Marken GD/DM/WW (Guide/Doom/Whispering Web) — die einzigen Effekte, die dem GEGNER des
Modells gehören, auf dem sie stehen.

- **Die zwei Hälften der Zielwahl müssen von DEMSELBEN Modell erfüllt werden** (User: "warum können
  meine pathfinder beschossen werden hier? die sind doch hidden ... die schießende einheit kann die
  modelle aber nicht sehen, die nicht in der dense area stehen ... in dem moment hatten die doch nur
  line of sight zu modelle die hidden waren", plus das Prinzip per Analogie: "das ist das gleiche
  prinzip, wie wenn es um die ermittlung von benefit of cover geht" — und Benefit of Cover wird in
  dieser Engine wirklich PRO SCHÜTZE gegen das Ziel entschieden, das er sieht).
  - **13.09 wurde EINMAL gefragt, auf EINHEITENEBENE** (`_is_valid_target_squad`: "ist IRGENDEIN
    Modell des Ziels detectable"), Reichweite und Sichtlinie dagegen in `_model_can_reach` über
    `target_squad.models` — die beiden wurden nie geschnitten. Also konnte eine Einheit über
    Modelle ANGEZIELT werden, die der Schütze gar nicht sieht, und dann über Modelle BESCHOSSEN
    werden, die er nicht sehen DARF.
  - **Auf dem gemeldeten Brett nachgerechnet** (Koordinaten aus dem Log des Users, map2): die
    Lokhust Destroyers hatten Sichtlinie ausschließlich zu den Pathfindern 1, 2 und 3 — alle drei
    HIDDEN und 20-22" entfernt, bei 15" Detection Range. Die Modelle, die das Hidden-Tor
    passierten, waren 6 bis 9, außerhalb der Ruine — und zu denen bestand KEINE Sichtlinie. Die
    Schnittmenge aus "darf gesehen werden", "in Reichweite" und "in Sichtlinie" war **leer**, und
    geschossen wurde trotzdem.
  - **`ShootingController._detectable_models()` ist jetzt die EINE Definition** von "welche Modelle
    dieses Ziels darf diese Einheit sehen", gelesen von BEIDEN Hälften: das Einheiten-Tor ist
    `bool(...)` davon, und `_model_can_reach()` iteriert genau diese Liste statt `target_squad.models`.
  - **Der Parameter ist PFLICHT, nicht per Default "alle"** — der Default wäre exakt der Fehler,
    den er verhindern soll. Fünf Aufrufstellen, alle nachgezogen; der Quell-Wächter zählt den
    AUFRUFAUSDRUCK (Fehlerklasse 24) und lehnt die alte Signatur ab.
  - **Die LONE-OPERATIVE-Klausel misst weiter gegen die GANZE Einheit** — ihr gedruckter Text ist
    "within X\" of this UNIT", eine Distanz, keine Sichtbarkeitsfrage. Ausgeschrieben, damit es
    niemand "vereinheitlicht".
  - **Rule 10.02 friert es mit ein**: die sichtbaren Modelle werden im `_snapshot_target_state()`
    berechnet, also gilt für die ganze Aktivierung, was bei der Zielwahl galt.
  - **Gemessen und BENANNT, nicht mitgeändert:** die Detectability wird weiterhin gegen die
    EINHEIT des Schützen gefragt, nicht gegen das einzelne schießende Modell. Auf dem gemeldeten
    Brett macht das keinen Unterschied (gemessen: dieselben vier Modelle). 13.09s Wortlaut ("seen
    by enemy MODELS within its detection range") und die Cover-Analogie des Users sprächen für
    pro-Schütze; `test_hidden.py` pinnt aber die Einheiten-Lesart, also ist das eine eigene
    Entscheidung und keine Nebenwirkung dieses Fixes.
  - **A/B belegt:** `_model_can_reach` zurück auf `target_squad.models` → **4 von 51 Prüfungen
    fallen**, und die Einheit ist wieder anzielbar UND beschießbar — das gemeldete Verhalten.
    **Die Sonde hat dabei zuerst einen Fehler im TEST gefunden**: die erste Bühne benutzte
    Tankbustas (12" Rokkit Pistol), also scheiterte alles an der REICHWEITE statt an der Sicht,
    und zwei Prüfungen bestanden aus dem falschen Grund. Mit einem 30"-Schützen kippt sie.
- **Hidden endet beim Schuss** — `last_ranged_attack_turn` wird jetzt auch aus `cancel()` gesetzt,
  wenn tatsächlich eine Waffengruppe aufgelöst wurde. Der "Next Phase"-Klick ist eine legitime
  "abandon and move on"-Route und übersprang die Buchführung, also blieb die übliche
  Mensch-Nutzung (Hauptwaffe feuern, Pistole weglassen, weiterklicken) dauerhaft hidden.
- **Attached Units (19.01-19.04)**: `attach()` MERGED die Leader-Modelle in `Squad.models` und wirft
  das Leader-Squad weg — damit ist es tatsächlich EINE Einheit, und Reserven, Transporte, Kohärenz,
  Zielwahl, Objective Control und Battle-Shock stimmen ohne Zusatzcode. Provenienz steht in
  `attached_components` (nie gekürzt, weil 19.02/19.04 die STARTmodelle brauchen). 19.03-Keywords
  poolen mit `any()`, 19.04-Fähigkeiten sind quellengebunden inkl. Nachlauf-Fenster. Leader-eigene
  Fähigkeiten über `leader_ability()`, NICHT `unit_wide_ability()` (das fragt, ob JEDES Modell die
  Fähigkeit druckt — bei einer Leader-Fähigkeit tut das kein Bodyguard).
  Zwei-Leader-Ausnahmen existieren in drei Formen: vom Bodyguard aus (Boyz' "Bodyguard"), vom Leader
  aus (Eldrad) und als JOIN, das gar keinen Leader-Slot belegt (Warlock Conclave).
