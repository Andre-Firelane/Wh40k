# Regelengine: Schießen

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Regelengine — Schießen

Shooting-Typen (10.02/10.04-10.07): Normal, Assault, Close-Quarters, Indirect, Snap Shooting (nur
reaktiv). Split Fire, und die Weapon Abilities [ANTI-X]/[ASSAULT]/[BLAST]/[CLEAVE]/[CLOSE-QUARTERS]/
[DEVASTATING WOUNDS]/[EXTRA ATTACKS]/[HAZARDOUS]/[HEAVY]/[IGNORES COVER]/[LANCE]/[LETHAL HITS]/
[MELTA X]/[ONE SHOT]/[PISTOL]/[PRECISION]/[PSYCHIC]/[RAPID FIRE X]/[SUSTAINED HITS X]/[TORRENT]/
[TWIN-LINKED] sind implementiert.

- **MONSTER/VEHICLE schießen aus dem Nahkampf HERAUS (10.06)** — gemeldet: *"monster und
  fahrzeuge können aus dem nahkampf rausschießen auf eine andere einheit. im letzten spiel konnte
  ich das mit dem voiddragon nicht."*
  - **Reproduziert vor jeder Änderung**, an der Quelle und am Log: `_is_valid_target_squad()` lehnte
    unter `CLOSE_QUARTERS_SHOOTING` JEDES Ziel ab, mit dem die Einheit nicht selbst engagiert ist —
    der engagierte C'tan Shard bekam genau EIN Ziel angeboten, das er gechargt hatte
    (`logs/game_20260904_214656.log` Z. 585: der Spear feuert mit Close-Quarters-Malus in genau
    diese Melee, der einzige Schuss, den er hatte).
  - **Die Engine widersprach sich selbst, und das war der Beleg vor der Regelfrage:**
    `_hit_modifiers()`s Malus lautet "+1, außer ([CLOSE-QUARTERS]-Waffe UND engagiertes Ziel)" —
    der zweite Term war UNERREICHBAR (immer wahr), solange nur engagierte Ziele wählbar waren. Ein
    Term, den kein Input erreicht, ist entweder tot oder die andere Stelle ist falsch; hier war es
    die andere Stelle.
  - **Nur MONSTER/VEHICLE, und das ist die Grenze der Meldung.** Eine INFANTERIE-Einheit mit
    [PISTOL]/[CLOSE-QUARTERS] bleibt auf die Einheit beschränkt, mit der sie ficht — die zwei sind
    ohnehin die einzigen, denen `_weapon_eligible_for_type()` hier eine Nicht-CQ-Waffe erlaubt.
  - **03.04 gilt für das andere Ziel unverändert**: eine Einheit, die in einer FREMDEN Melee steckt,
    bleibt tabu. Deshalb wiederholt der neue Zweig die `is_engaged()`-Prüfung des `elif` daneben,
    statt an ihr vorbeizulaufen.
  - **Der Malus hat jetzt ZWEI Labels**, weil die zweite Hälfte lebt: ein Würfel, der
    "non-[CLOSE-QUARTERS] weapon" sagt, während die Waffe sichtbar eine ist, schickt die nächste
    Untersuchung zurück aufs Brett (Diagnose-Logging-Regel).
  - **Zu 10.06 gab es GAR KEINEN Test** — `CLOSE_QUARTERS_SHOOTING`/"Close-Quarters" kam in NULL
    Testdateien vor, und genau deshalb konnte eine Zielwahl-Regel, die **19 Einheiten über alle fünf
    Listen** betrifft, falsch dastehen. Neu `test_close_quarters_shooting.py` (**32/32**, fünf
    Abschnitte) plus `ab_close_quarters_shooting.py` (**5 A/B-Sonden, alle beißend**; die ganze
    Vor-Fix-Welt kippt 5 von 32 und meldet die Meldung wörtlich).
  - **Im ECHTEN Spiel belegt** (`verify_close_quarters_targeting.py`, `runpy` auf `selfplay.py`s
    echte `main()`-Schleife, Necrons gegen Death Guard — die gemeldete Paarung): der LIVE von
    `main()` gebaute Controller bietet dem `1 C'tan Shard of the Void Dragon 1` **beide** Einheiten
    an, das Brett-Highlight zeigt beide, und der Klick auf die ferne nimmt. `--neutralize` meldet
    **nur die engagierte** — das gemeldete Verhalten. Die Lage wird GESTELLT (ein MockAgent-Lauf
    erreicht sie im Framebudget nicht), die Sichtlinie dafür unabhängig über
    `game/line_of_sight.py` geprüft statt über den Controller, der gemessen wird.
  - **BENANNT, nicht mitgeändert: der [BLAST]-Halbsatz von 10.06 ist VERLETZT, und zwar
    vorbestehend.** `CLAUDE.history.md` zitiert ihn wörtlich ("If that attack is made with a [BLAST]
    weapon, it still cannot target a unit your unit is engaged with") und hält ihn für "strukturell
    erfüllt" — die Begründung dort steht auf dem Kopf: verboten ist BLAST auf das ENGAGIERTE Ziel,
    und genau das ist möglich. Gemessen: der Void Dragon darf seine Voltaic Storm ([BLAST 1]) in
    seine eigene Melee feuern, und **6 der 19 betroffenen Einheiten** tragen eine BLAST-Waffe
    (Defiler, Plagueburst Crawler, Doomsday Ark, Kill Rig, Deffkoptas, Void Dragon). Ein eigener
    Fix — er macht die gemeldete Einheit SCHWÄCHER und war nicht die Bitte.

- **Ein reaktiver Schuss muss ÖFFNEN — und das Öffnen überleben** (gemeldeter Absturz aus `main()`,
  `necrons_hypercrypt`: `TypeError: 'Squad' object is not iterable` in `start_reactive_shooting()`, als die KI
  eine Einheit neben dem Hexmark des Menschen beschoss). **Zwei Fehler, der zweite hinter dem ersten:**
  - **Ein Vertrag, zwei Lesarten, beide ausgeliefert** (Fehlerklasse 10, dritte Form). Die Methode nahm seit
    2026-08-26 nur eine LISTE (`list(restrict_to)`); Vengeful Stars und Vaul's Vengeance reichen `[killer]`,
    Kroot Packmates, Multi-threat Eliminator und Hyperspace Hunters die Einheit selbst. Die drei waren nie in
    einem echten Spiel gelaufen (Hexmark erst seit der Hypercrypt-Liste gefieldet, Krootox Riders und
    Deathmarks gar nicht), und ihre Suiten fuhren STUBS, die jede Form schluckten. Der TREIBER nimmt jetzt
    beide (`pregame.Resume`-Präzedenz) und gibt `True`/`False` zurück statt immer `None`.
  - **Im Listener-Loop gestartet, wurde die Aktivierung sofort gelöscht.** Jedes gedruckte "after that enemy
    unit has finished making its attacks" antwortet aus `on_squad_finished_shooting`, also aus
    `_actually_finish_squad()`, das direkt nach dem Loop `active_squad`/`state` leert. Mit umgangenem
    TypeError gemessen: der Reaktor schoss nie, und jeder SPÄTERE Listener bekam den REAKTOR als die Einheit,
    die gerade geschossen hatte. Traf genauso Vaul's Vengeance und Vengeful Stars' KI-Pfad (CP bezahlt, kein
    Schuss). Jetzt steht `_closing_activation` für den Loop (try/finally); ein Start währenddessen landet in
    `_deferred_reactive` und wird von `_open_deferred_reactive()` am Ende von `_finish_activation()` geöffnet —
    NACH dem Completion-Callback, einer nach dem anderen, Tote übersprungen (`_attack_groups()` prüft keine
    Wunden).
  - **Nebenbefund, mitbehoben:** ein mangels Schusstyp abgelehnter Start ließ die Einheit in `active_squad`
    stehen — für `_foreign_activation_in_progress()` eine laufende fremde Aktivierung, auf die die KI ewig
    gewartet hätte, und in der Queue ein Stopper. Die Ablehnung räumt jetzt vollständig ab.
  - **Die eigene Sonde fand einen HÄNGER, mitbehoben:** ein Listener, der die schließende Aktivierung selbst
    beendet (`cancel()` mitten im Loop), erreichte den Drain mit gehobener Flagge — der Start queute das gerade
    Gepoppte neu, die `while`-Schleife endete nie. Kein heutiger Listener tut das; der Drain kehrt jetzt zurück,
    solange der Loop läuft. **Und der Sondentreiber lief dabei selbst fest:** er bekam die Kontrolle nie zurück,
    `game/shooting.py` blieb im Sondenzustand, bis die Prozesse von Hand beendet und die Markerzeile
    zurückgesetzt waren. Seither hat jeder Suite-Lauf dort eine Frist (ein HÄNGER zählt als Befund), die Ausgabe
    ist zeilengepuffert, und §7b läuft in einem Daemon-Thread mit `join(timeout)` — rot statt hängend.
  - **Getestet:** neu `test_reactive_shooting_start.py` (**70/70**, echter `ShootingController`; §2-§4 durch
    den echten Trichter, §6 die Queue, §7/§7b die Flagge) plus `ab_reactive_shooting_start.py`
    (**9 A/B-Sonden, alle beißend**, byte-identisch zurückgestellt; die ganze Vor-Fix-Welt kippt 33 von 70).
    Volle Regression **233 Suiten, ~22258 Prüfungen, 232 grün / 0 rot / 1 bekannt**, alle neun schweren
    Skripte von `run_tests.py --smoke` grün (im Wiederholungslauf fiel einmal die dokumentierte
    `test_ere_we_go.py`-Flake, einzeln 3 von 3 grün; die Suite ist seit Orks E2 gelöscht). **Im ECHTEN Spiel**
    (`verify_reactive_shooting_start.py`, Hexmark des Menschen gegen eine KI-Doomsday-Ark): kein Absturz,
    Aktivierung offen und auf die Ark beschränkt, **0 KI-Aktionen in 240 Frames**, ein echter Klick nimmt das
    Ziel, die KI setzt 3 Frames nach dem Stopp fort. `--neutralize` reproduziert den TypeError,
    `--neutralize-wipe` die gelöschte Aktivierung (die KI spielt dabei in 238 der 240 Frames weiter). GESTELLT:
    der Moment (die KI schießt passiv nie verlässlich auf die richtige Einheit), der Stopp-Knopf des
    Menschen, und die Lage der Ark — Sichtlinie allein reichte nicht, das Brett bot dann gar kein Ziel an,
    also fragt die Bühne `has_valid_target()`, bevor irgendeine Aktivierung offen ist.
- **Zielwahl friert den Zustand ein (10.02).** `_snapshot_target_state()` hält Reichweite,
  Sichtlinie, Deckung und "nächstes zulässiges Ziel" für die ganze Aktivierung fest — Verluste sind
  eine FOLGE der Sequenz und können eine legale Zielwahl nicht rückwirkend aufheben. Ein KOMPLETT
  ausgelöschtes Ziel bleibt bewusst ausgenommen. **Nicht** eingefroren wird, was der gedruckte Text
  pro Angriff auswertet (Modellzahl für Arro'kon, Halbdistanz für Bladestorm).
- **[LETHAL HITS] fragt nicht mehr** — jeder kritische Treffer wundet automatisch (der Prompt bot
  0..crits an und unterbrach jede Aktivierung).
- **Kritische Würfel tragen ihr Label** ("LETHAL HIT" / "SUSTAINED HIT" / "DEVASTATING WOUND"),
  gebildet aus der ADJUSTIERTEN Waffe — fast jedes dieser Keywords ist ein bedingter Grant, das
  gedruckte Profil wäre die falsche Quelle. Dafür ist die Adjuster-Kette in `_adjusted_weapon()`
  extrahiert (stand vorher doppelt da).
- **Split Fire kann eine Waffe AUSLASSEN**: `skip_current()` (bewusst nicht feuern) und
  `finish_assignment()` (das Zugewiesene feuern, den Rest lassen) — das fehlende Gegenstück zu
  `stop_shooting()`. Zusätzlich `_prune_unassignable()`: eine Waffe ohne legales Ziel wird gar nicht
  erst gefragt, damit die gemeldete Sackgasse strukturell unmöglich ist. Front-only, weil sich während
  des Assignment-Schritts nichts bewegt (gemessen: 11 ms je Probe, ein Vorab-Sweep 126 ms). In der
  Fight-Phase war dieselbe Sackgasse garantiert (12.02 filtert pro Modell, die Queue nicht).
- **Feuer-Modi** über `WeaponProfile.overcharge_profile` — der generische Alternativmodus-Haken, nicht
  speziell Hazardous-Overcharge (der Pathfinder-Granatwerfer hat zwei gleichrangige Modi). Bei Split
  Fire pro MODELL wählbar, und der Tausch passiert bei der ZUWEISUNG, weil `_attack_key()` nach
  S/AP/D gruppiert.
- **Benefit of Cover (13.08)** wird pro Schütze geprüft; bei Uneinigkeit wird die Gruppe in zwei
  unabhängige Sequenzen geteilt.
- **Performance**: `has_line_of_sight()`/`model_fully_visible()` filtern Obstacles/Modelle vorab per
  Bounding-Box (mathematisch identische Ergebnisse); `valid_target_models()` dedupliziert pro SQUAD;
  mehrere UI-Caches. Dazu seit der T'au-Lag-Meldung ein zweiter, verlustfreier Hebel im
  Punktpaar-Loop selbst — siehe `## Die Schussphase war mit T'au unspielbar`. **Die hier früher
  behauptete Belegung "per 400 Fuzz-Vergleichen" hatte keine Datei**: zu `game/line_of_sight.py`
  gab es überhaupt keine Suite, bis `test_line_of_sight.py` sie angelegt hat.
- **"Change a die to an unmodified 6" ist ein PANEL-BUTTON, kein Prompt** (User: "momentan werde
  ich bei aeldari jedes mal gefragt, ob ich aspect shrine tokens verwenden will ... nach jedem
  wurf. kann das nicht eine option im linken panel sein, statt eines overlays? command reroll
  funktioniert ja auch so. ich klicke aspect shrine button an und waehle dann den wuerfel aus, den
  ich aendern will. genau das gleiche mit branching fates vom farseer").
  - **Gemessen vor der Änderung:** der Prompt ging in EXAKT dem Frame auf, in dem der Wurf
    weggeklickt wurde (dice pending → acknowledge → decision pending, in einem Schritt). Also zwei
    Klicks pro Wurf, und mit einem ungenutzten Token die ganze Schlacht lang.
  - **`game/unmodified_six_controller.py` ist EIN Controller für ALLE solchen Fähigkeiten**, nicht
    einer je Fähigkeit: Eignung, Würfelauswahl und Panel-Verdrahtung sind identisch, nur die
    RESSOURCE unterscheidet sich — und die besitzt jedes Fähigkeitsmodul schon. Form exakt nach
    `game/command_reroll.py`, weil der User sie beim Namen genannt hat: `can_use` → `start` →
    `choose_die`, mit `selecting_die` als Treiber für Panel UND Klick-Routing. Bei genau EINEM
    änderbaren Würfel entfällt der Auswahlschritt (dieselbe Abkürzung, die Command Re-roll nimmt).
  - **Der Effekt ist jetzt der WÜRFEL, nicht ein Zähler.** Vorher wurden Treffer-/Krit-ZÄHLER
    nachträglich korrigiert; jetzt wird der gewählte Würfel eine 6 und die gewöhnliche Auflösung
    liest ihn — also sehen [SUSTAINED HITS], [LETHAL HITS], [DEVASTATING WOUNDS], [ANTI-X]s
    gesenkte Krit-Schwelle und jeder künftige Leser ihn automatisch. Modifikatoren justieren in
    dieser Engine die SCHWELLE, nie den Würfel, also IST ein auf 6 gesetzter Würfel eine
    unmodifizierte 6. Damit sind `hit_change`/`wound_change`/`prompt_for`/`describes` in drei
    Modulen ersatzlos entfallen.
  - **Das "lohnt es sich"-Gate BLEIBT**, obwohl sein ursprünglicher Grund (Unterbrechung) mit dem
    Button entfällt: "niemals anbieten, was nichts kauft" (Fehlerklasse 5) ist ein zweiter,
    unabhängiger Grund. Es wird jetzt an den Würfeln AUF DEM TISCH gerechnet, über
    `DiceManager.is_success()/is_critical()` — die alte Fassung musste die Fehlschlagzahl aus einem
    durch neun Signaturen gefädelten Würfel-ZÄHLER rekonstruieren, weil die Würfel zu ihrem
    Zeitpunkt längst weg waren.
  - **Der Kontext-Hook liefert die ANGEPASSTE Waffe** (`unmodified_six_context()` in beiden
    Angriffs-Controllern). Bladestorm gewährt den Dire Avengers [SUSTAINED HITS] nur in
    Halbdistanz; das gedruckte Profil zu lesen hieße, dass der Button genau dort fehlt, wo der
    Token sich lohnt. A/B belegt.
  - **Der DAMAGE-Zweig von Branching Fates ist ebenfalls ein Button** (User-Nachtrag: "branching
    fate für den damage roll war gerade noch ein overlay"), geht aber NICHT durch die
    Würfelauswahl — ein Damage-Wurf ist EIN Würfel ohne Fehlschlag zum Umwandeln, also gibt es
    nichts auszuwählen (dieselbe Abkürzung wie bei Command Re-roll). **Was er mit dem Würfel tut,
    ist seit dem 2026-09-09 identisch zu Hit und Wound: er wird eine 6.** Die frühere
    Ergebnis-Lesart ist gemeldet und umgedreht — siehe `## Fünf Meldungen aus einer Partie`.
  - **Nebenbei geschlossen:** `BranchingFatesDamageOffer` sagte in seinem Docstring, es werde "by
    game/shooting.py and game/fight.py" gebaut — `fight.py` baute es nie, die Damage-Hälfte wirkte
    also nur im Fernkampf. Über den DiceManager gilt sie jetzt in beiden Phasen, ohne Zusatzcode.
    Die Klasse, `damage_override` und `_after_damage_override()` sind ersatzlos entfallen;
    `damage_change()` — die Regellesart — bleibt.
  - **Getestet:** neues `test_unmodified_six_ui.py` (**58/58**: Controller-Fluss samt der Zustände,
    die NICHT anbieten dürfen; das echte `ActionPanel`; Quell-Wächter auf `main.py`), dazu
    `test_aspect_shrine.py` **72/72** und `test_farseer.py` **106/106** auf den neuen Weg
    umgeschrieben. Sieben A/B-Sonden, jede kippt mindestens eine Suite.
- **Hausregel**: befreundete Modelle blockieren keine Sichtlinie — am BEOBACHTER festgemacht (beide
  Enden auszunehmen würde Modell-Blockade ganz abschaffen). Gegnerische blockieren unverändert,
  Screening funktioniert also weiter.

## Die Schussphase war mit T'au unspielbar (2026-09-08)

**Gemeldet:** *"wenn man tau spielt ist die shooting phase sehr laggy. ich denke es liegt an for
the greater good. da diese fähigkeit eine unendliche reichweite hat, müssen alle gegnerischen
einheiten auf LOS geprüft werden."* **Die Vermutung stimmt und war untertrieben.**

- **Reproduziert vor jeder Änderung**, map2, `armies/tau.json` gegen `armies/orks.json`, 179
  Modelle: `GreaterGoodController.eligible_targets()` für "1 Breacher Team 1 + Cadre Fireblade"
  (11 Modelle) kostet **4732 ms** — 1048 Sichtprüfungen à 4.52 ms. Und das lief **pro Frame**:
  `action_panel.py:2322` fragt im `_draw_movement_ui()`-Zweig jeden Frame
  `greater_good_controller.can_use()`, und das endete auf `bool(self.eligible_targets(squad))`.
  Der teure Fall ist genau der gemeldete: zu einer Einheit, die NIEMAND sieht, bricht `any()` nie
  ab, und das sind zwölf von vierzehn.
- **Die Regel hat wirklich keine Reichweitengrenze** ("an enemy unit that is visible"), es fehlt
  also der Vorfilter, den `shooting.py`s `_model_can_reach()` vor jedem LoS-Aufruf hat.
- **Warum es überlebt hat, und das ist Fehlerklasse 10 in einer eigenen Form:** in `main.py` stand
  seit einem früheren Bericht ein Cache dafür, samt der gemessenen Zahl ("~0.8s per
  eligible_targets() call"). Er ist auf `CHOOSING_TARGET` gekeyt — das Brett-Highlight NACH dem
  Knopfdruck. Der `can_use()`-Pfad läuft im IDLE-Zustand, dort gibt er ein leeres Set zurück.
  **Eine Zahl gemessen, einen Cache gebaut — für einen der zwei Aufrufpfade.**
- **Und deshalb traf es nur den MENSCHEN:** `ai/agent_driver.py` merkte sich sein Nein in
  `memory.declined_greater_good` und fragte einmal pro Einheit.

### Der stärkste Hebel liegt in `line_of_sight.py` und hilft der ganzen Engine

`has_line_of_sight()` prüft 576 Punktpaare und lief für JEDES die Hindernis-, Blocker- und
Area-Listen von vorne durch. Steht eine Wand dazwischen, blockiert sie fast jedes Paar — und wird
jedes Mal erst an ihrer Listenposition gefunden. **`_first_blocker()` merkt sich den zuletzt
erfolgreichen Blocker und testet ihn zuerst.**

- **Verlustfrei per Konstruktion:** pro Punktpaar ist das Ergebnis ein ODER über drei
  seiteneffektfreie Prädikate, und ein ODER darf umsortiert werden. Gemessen, mit zufälligen
  Positionen, Basisgrößen und Blockern: **map1 4.56x, map2 5.00x, map3 7.75x, je 0/150
  Abweichungen** — map3 mit seinen acht gedrehten Stücken profitiert am stärksten und ist die
  teuerste Karte. In beiden Fällen schneller, **nie langsamer** (blockiert 5.08x, gemischt 1.67x).
- **8 Module, 35 Aufrufstellen** lesen `has_line_of_sight`/`model_fully_visible` — auch
  `ai/observation.py` und `ai/agent_driver.py`, also profitieren die KI-Zugzeiten mit.
- **DIE FALLE, und sie steht namentlich im Docstring:** das Memo darf NICHT über
  `has_line_of_sight()`-Aufrufgrenzen hinweg geteilt werden, obwohl das der offensichtliche
  nächste Schritt ist (`eligible_targets()` fragt tausendmal nach derselben Wand).
  `_blocking_models()` schließt PAARABHÄNGIG aus (beide Einheiten, und per Hausregel die ganze
  Armee des Beobachters), `_obscuring_areas_between()` ebenso. **Nur OBSTACLES sind
  paarunabhängig.** Ohne diesen Satz löscht die nächste Optimierungsrunde still die Hausregel
  "befreundete Einheiten blockieren nicht" — zwei A/B-Sonden halten die Grenze.

### `greater_good.py`: drei verlustfreie Änderungen plus ein Cache

- **`is_detectable` vorziehen und pro DEFENDER einmal rechnen.** Es hängt nur vom Defender und vom
  beobachtenden Squad ab, nie vom einzelnen `friendly` — wurde aber je Paar neu gerechnet und stand
  rechts vom `and`, also erst NACH der teuren Hälfte. Gemessen **0.0023 ms je Modell gegen 4.52 ms
  je Sichtprüfung, 2000x billiger**.
- **Ein Generator, zwei Sichten** (`eligible_targets()` und `any_eligible_target()`), Muster
  `army_rule_text()`/`army_rule_blocks()`. `can_use()` braucht nur ein `bool` und baute die ganze
  Liste.
- **Feindeinheiten NACH DISTANZ**, nächste zuerst. Für ein `any()` verlustfrei, und nebenbei
  behoben: `enemy_squads` war ein SET, die Rückgabereihenfolge also lauf-instabil.
- **Der Cache liegt im CONTROLLER**, nicht in `main.py` — Vorbild ist
  `ShootingController.weapon_eligibility()` ("called every frame to render"), nicht Muster A. Ein
  Panel-Argument wäre Fehlerklasse 22 durch eine dreistufige positionelle Kette gewesen, und die
  Panel-Suiten bauen das Panel selbst, hätten also einen zweiten Antwortpfad gebraucht. So
  profitieren Panel, Klickvalidierung und KI-Pfad zugleich.
- **Der Schlüssel ist EXAKT, nicht heuristisch.** `len(state.tokens)` als "das Brett hat sich
  geändert"-Proxy (wie die vier main.py-Caches) verpasst Bewegungen, und in der Schussphase bewegen
  die reaktiven Züge des Gegners und die eigenen `OUT_OF_PHASE_MOVE_MODES` sehr wohl Modelle.
  **`game/board_epoch.py` ist der geteilte Fingerabdruck** (Position + `current_wounds` + Länge),
  gelesen von Greater Good und Arro'kon; gemessen **0.099 ms je Frame** gegen den 4732-ms-Sweep.
  Gecacht wird NUR die teure letzte Klausel — die sieben billigen Tore bleiben live, damit der Knopf
  verschwindet, sobald die Einheit markiert oder geschossen hat.
- **Ein echter KI-Fehler fiel mit:** `agent_driver.py`s Kommentar behauptete "positions are frozen
  until the next Movement phase" und cachte darauf ein "can_use() sagte nein". Mit den reaktiven
  Zügen ist das falsch — eine Einheit, die zu Beginn der Phase nichts sah, fragte nach einem
  gegnerischen Fade Back nie wieder. `declined_greater_good` hält jetzt nur noch das EXPLIZITE
  "no_mark" des Modells.

### Zweiter Verursacher, beim Messen gefunden: Arro'kon rechnete zweimal

`action_panel.py` fragte `arrokon_controller.can_use(squad)` und danach `best_available_tier(squad)`
— und `can_use()` ENDET in `best_available_tier()`. Derselbe `has_valid_target()`-Sweep zweimal pro
Frame, gemessen bis **660 ms** je Aufruf (Broadside Battlesuits). `offer_tier()` ist jetzt die eine
Frage (`can_use()` ist `offer_tier(squad) > 0`), plus Tier-Kurzschluss (Kandidaten absteigend, der
erste Treffer IST das Maximum, weil `ARROKON_TIERS` nur 2 und 1 kennt) und derselbe Cache.

### Ergebnis, im ECHTEN Spiel gemessen

`measure_shooting_frame_cost.py` (neu — im Repo gab es **kein** Skript, das Schussphasen- oder
Sichtlinienkosten misst) fährt `selfplay.py`s echte `main()`-Schleife mit T'au als **Player 1**:

| gestellt, auf der gemeldeten Einheit | gefixt | `--neutralize` |
|---|---|---|
| erster Aufruf (kalt) | **320 ms** (440 Sichtprüfungen) | **2020 ms** (737) |
| jeder Folgeframe | **0.015 ms** | **2026 ms** |
| `ActionPanel.draw` in der Schussphase | 1.6 ms Mittel | max 295 ms |

2026 ms je Frame sind 0.49 FPS — genau "sehr laggy". Im Dauerbetrieb Faktor ~135 000.

**Warum die gemeldete Einheit GESTELLT wird und das benannt ist:** über 1600 Frames landet die
Rotation etwa EINMAL auf der teuren Klausel (die sieben billigen Tore fangen den Rest ab), eine
passive Zahl ruhte also auf einer einzigen Stichprobe. Gemessen wird der ECHTE Controller gegen das
Brett, das `main()` gebaut hat; gestellt ist nur, WELCHE Frage gestellt wird — dieselbe Begründung
wie bei `verify_sudden_storm_wiring.py`. Arro'kon erreicht in diesem Lauf seine eigenen Tore nie und
meldet das als benannten Grund statt als stille Null; die Ein-Sweep-Behauptung hält stattdessen ein
ZÄHLER in `test_arrokon_protocol.py` Abschnitt 8.

### Getestet

- **Neu `test_line_of_sight.py` (21/21)** und **`test_greater_good.py` (20/20)** — zu BEIDEN
  Modulen gab es vorher gar keine Suite, und genau deshalb konnte ein 4.7-Sekunden-Sweep pro Frame
  unbemerkt bleiben. Beide fahren eine Vor-Fix-Referenz IM TEST gegen die neue Fassung (400 bzw.
  120 Fuzz-Bretter, 0 Abweichungen), beide mit einer LIVENESS-Zeile: ein Fuzz, der 400-mal dasselbe
  liefert, hat nichts gemessen.
- `test_arrokon_protocol.py` 67 → **80/80** (Abschnitt 8: der Sweep-ZÄHLER, ein Brett mit ZWEI
  Tiers, und ein AST-Wächter auf das Panel).
- **21 A/B-Sonden über drei Dateien, alle wie deklariert.** Zwei sind ausdrücklich als
  NICHT-beißend deklariert, mit gemessener Begründung: eine verlustfreie Umsortierung darf eine
  Korrektheitssuite nicht rot machen, und eine Sonde, die das erzwingen wollte, wäre eine Suite,
  die auf richtigem Code scheitert.
- **SECHS Sonden bissen zuerst nicht, und alle sechs waren Befunde über den TEST**
  (Fehlerklasse 24): die Cache-Mutationen bewegten Modelle um ±9" auf offenem Boden, wo das Ziel
  durchgehend sichtbar blieb — vier Sonden, die den Schlüssel ausweideten, kamen glatt durch.
  Abschnitt 4 MISST jetzt zwei Positionen, die die Antwort wirklich trennen, und verlangt ≥15
  Flips. Dazu: der Panel-Doppelaufruf ist hinter dem Cache für jeden Verhaltenstest unsichtbar
  (jetzt ein AST-Wächter), und die Tier-Reihenfolge ist auf einem Brett mit EINEM Ziel bedeutungslos
  (jetzt zwei Tiers). **Lehre: ein Cache-Test beweist nichts, solange nicht gezeigt ist, dass seine
  Mutationen die Antwort ändern.**
- **Ein Wächter matchte seinen eigenen Kommentar** — die `detection_range`-Abweichung wird per AST
  auf den Aufrufausdruck geprüft, weil der erklärende Kommentar daneben beide Keywords nennt.
  Fünfte Instanz dieser Falle.
- Volle Regression **195 Suiten, ~17258 Prüfungen, 194 grün / 0 rot / 1 bekannt**, alle neun
  schweren Skripte, `selfplay.py` auf map2 und map3.
- **BEWUSST NICHT MITGEÄNDERT:** `game/detection_range.py:35-49`s dokumentierte Abweichung
  (`eligible_targets()` ruft `is_detectable()` ohne `prey_marks`/`unmasking`). Die neue Zeile sieht
  `shooting.py`s `_detectable_models()` jetzt zum Verwechseln ähnlich, deshalb steht die Lücke als
  Kommentar am Aufrufort UND als Testzeile — eine bewusst offene Lücke, die nur ein Kommentar hält,
  ist keine.

## Hit- und Wound-Modifikatoren: ±1-Deckel und 2+-Untergrenze (game/modifiers.py, 2026-09-19)

**Gemeldet:** *"wenn etwas +1 oder -1 auf hit oder wound gibt, dann kann diese modifikation maximal
1 vom ursprungswert abweichen. es stackt also nicht ... aber modifikatoren können sich gegenseitig
neutralisieren ... 1+ gibt es nicht, das beste mögliche ist immer 2+"*, und nachgeschoben: *"das
betrifft hit und wound roll, aber modifikationen auf werte zb. Ballistic Skill werden extra
behandelt. Zb Cover"*.

- **Vorher:** `apply_modifiers()` summierte schlicht. Zwei -1 auf den Trefferwurf machten aus 3+ ein
  5+, ein Guided-+1 auf 2+ druckte `needed 1+`. Die AUFLÖSUNG war an der 1 schon richtig
  (`_resolve_roll()` wertet den rohen Würfel: 1 scheitert, 6 ist kritisch). Falsch war die
  SCHWELLE, und die lesen Würfelpanel, Log und jede Crit-Regel, die gegen sie vergleicht.
- **`Modifier.kind`:** `ROLL` ("add/subtract 1 to/from the Hit/Wound roll", "+1 to hit rolls",
  Default) oder `CHARACTERISTIC` ("improve/worsen the Ballistic Skill characteristic"). Die ROLL-
  Einträge werden erst summiert (sie heben sich auf) und dann auf ±1 gedeckelt; die CHARACTERISTIC-
  Einträge zählen voll daneben; das Ergebnis ist nie besser als 2+. Nach oben gibt es keine
  Grenze: 7+ bleibt stehen, eine unmodifizierte 6 trifft trotzdem.
- **Die acht Kennwert-Stellen**, alle in `shooting.py`/`fight.py`: Benefit of Cover (13.08), die
  zwei Close-Quarters-Mali (10.06 — laut Docstring derselbe "worsen the characteristic"-Wortlaut
  wie Cover; der gedruckte Kernregeltext liegt nicht im Repo), For the Greater Good (Guided),
  Target Uploaded, Coordinate to Engage und die Wraithlord-Hälfte von Psychic Guidance (Schuss +
  Nahkampf). Die übrigen 54 Konstruktionen drucken ROLL-Wortlaut, einzeln geprüft.
- **Psychic Guidance läuft jetzt WIRKLICH auseinander:** der Docstring behauptete, die zwei
  Lesarten könnten hier kein anderes Ergebnis geben. Mit dem Deckel stimmt das nicht mehr
  (korrigiert, mit Beispiel).
- **Anzeige:** das Log hängt `; roll modifiers +2 capped at +1` an, wenn der Deckel greift; das
  Würfelpanel zeigt die Korrektur als LETZTE Zeile ("+1 (roll modifiers capped at ±1)" unter zwei
  -1), sonst stünden dort -1, -1 neben einer Schwelle, die sich um eins bewegt hat.
- **KI-Schätzung:** `damage_estimate.attack_modifiers()` faltet jetzt über dieselben Funktionen,
  statt `.amount` selbst zu summieren.
- **Die „Ignore modifiers"-Filter bleiben unverändert** (Riptide/Dark Reapers, Kauyon, Warrior
  Focus, Weapon Sentinels, [PSYCHIC]): jeder nennt „BS characteristic UND Hit roll“ und wirft die
  verschlechternden Einträge beider Sorten weg. Das bleibt auch mit Deckel die beste Wahl.
- **Wächter, `test_roll_modifier_cap.py` §6:** (a) JEDE `Modifier(...)`-Konstruktion in `game/`,
  `ai/`, `main.py` steht in genau einer von zwei Listen (8 CHARACTERISTIC, 54 ROLL), als
  Multimengen-Differenz in beide Richtungen: eine neue Stelle wird rot, bis jemand ihren gedruckten
  Text gelesen hat, und eine entfernte Stelle hinterlässt einen toten Eintrag, der ebenfalls rot
  wird. (b) Das `.amount` eines Modifikators wird außerhalb von `game/modifiers.py` nur VERGLICHEN
  (die Filter), nie summiert.
- **Getestet:** `test_roll_modifier_cap.py` **52/52**: die Beispiele des Users, eine echte Schuss-
  und eine echte Nahkampfszene mit A/B auf denselben Würfeln (Ghostkeel „Damaged“ + Lightning-Fast
  Reactions: 5+ statt 6+, die zwei 5er treffen; Kroot in Deckung: 6+, die Deckung zählt voll; Boyz
  gegen Forewarned + LFR: 4+ statt 5+), die KI-Schätzung und die Wächter. Sechs A/B-Sonden, alle
  beißen: alte Summe, kein Deckel, keine Untergrenze, „alles ist ROLL“, Cover ohne `kind`, eine von
  Hand gerollte Summe in einem neuen Modul. Volle Regression 238 Suiten / ~23213 Prüfungen, 237 grün
  / 0 rot / 1 bekannt; `--smoke` grün inkl. `selfplay.py map2 1500`. Keine bestehende Suite kippte
  — keine hatte je zwei gleichgerichtete Wurf-Modifikatoren gestapelt.
