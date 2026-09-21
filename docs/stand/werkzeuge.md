# Werkzeug-Katalog

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Smokes, Messskripte und Laufzeit-Sonden (aus „Tests und Werkzeuge“ ausgelagert)

- **`smoke_pregame.py <map>`** — Vorspiel end-to-end durch `main()`, prüft 0 API-Calls und beide
  Deckungs-Schranken. **`smoke_log_input.py`** — echte Maus-Events in die echte Event-Kette.
  **`smoke_setup_screens.py [--neutralize]`** — klickt durch die ECHTEN Vorspiel-Screens in
  `main()`: erst eine Kartenkachel, dann je eine Armeekachel pro Spieler, und fragt danach das
  gebaute Schlachtfeld, worauf und womit gespielt wird. Jeder Klick ist bewusst etwas, das KEINE
  Konfiguration erzeugt (map1 gegen `config.MAP = "map2"`, Player 1 Orks / Player 2 Aeldari gegen
  aeldari/necrons), also kann ein Bestehen nicht von den Defaults kommen. Er pinnt zusätzlich die
  REIHENFOLGE, die sonst nirgends sichtbar wird: Karte vor Brettbau, Brett vor Armeen.
  `--neutralize` stellt die Vor-Fix-Welt her und MUSS scheitern (11/11 gegen 0/11). Sechs Frames,
  deshalb im `--smoke`-Lauf das billigste Stück.
  **`smoke_measure_tool.py [map] [--neutralize]`** — das ALT-Lineal in den drei Zuständen, die es
  früher geschluckt haben (Fire Overwatch, Decision-Prompt, Würfelwurf), durch dieselbe echte
  Schleife; `--neutralize` stellt die Vor-Fix-Welt her und MUSS scheitern (18 von 21 Prüfungen
  kippen). Das Muster für jede künftige Ansichts-Steuerung in dieser Kette (Fehlerklasse 15).
  **`smoke_end_turn_warning.py [map] [--neutralize]`** — die Nahkampf-Warnung als DREI-Klick-Folge
  durch dieselbe echte Schleife (End Turn → Warnung, Zug bleibt; wegklicken → Zug bleibt; End Turn
  → Zug endet). Die Folge ist der Punkt und lässt sich nicht halbweise prüfen. `--neutralize`
  stellt die Vor-Fix-Welt her und MUSS scheitern (4 von 13, und der erste Klick beendet den Zug
  sofort — genau das gemeldete Verhalten). Stellt die 12.04-Bühne selbst: zwei Einheiten dicht
  gepackt in Engagement Range, Pile-In per 12.03 übersprungen (sonst bleibt der Fight-Step in
  `NOT_STARTED` statt `SELECTING` zu erreichen), und räumt alles ab, was in `main.py`s Kette über
  dem Button steht — sonst misst er einen Klick, der den Button nie erreicht hat.
  **`smoke_unit_pick.py [map] [--neutralize]`** — eine Entscheidung, deren Optionen EINHEITEN
  nennen, durch dieselbe echte Schleife: Panel-Screen, Brett-Ringe, das schweigende Overlay und
  ein ECHTER Klick auf die Einheit, der sie auflöst. Er STAGET die Entscheidung selbst und sagt
  warum (jeder solche Prompt ist reaktiv, ein MockAgent-Lauf erreicht keinen zuverlässig — ein
  passiver Zähler hätte 0 gemeldet und wie ein Bestehen ausgesehen); alles danach ist echt.
  `--neutralize` kippt alle sechs Prüfungen.
- **`measure_*.py`** — die Messskripte, die Entscheidungen tragen: `measure_crowded_movement.py`
  (Bewegung mit der GANZEN Armee auf dem Brett — die einzige aussagekräftige Welt, siehe unten),
  `measure_movement_fixes.py` (Geometrie EINER Einheit, macht KEINE Aussage über Spielqualität),
  `measure_placement_headroom.py`, `measure_deployment_safety.py` (Regressionsschranke),
  `measure_stim_injectors_gate.py`, `measure_advance_usage.py`,
  `measure_fly_penalty.py` (kostet oder bringt 21.03 einer gemischten Einheit Boden — baut das
  Brett aus den Koordinaten EINES Logs nach, statt eine Einheit isoliert hinzustellen),
  `measure_home_garrison.py` (wer hält das Home Objective — beide Phasen der Entscheidung,
  Aufstellung und Turn-Plan, letzterer gegen das Brett des gemeldeten Logs; `--neutralize`),
  **`measure_reported_moves.py`** (die gemeldeten Bewegungs- und Charge-Fälle aus ECHTEN Logs,
  MIT Terrain nachgebaut — Fälle A/B Charges, C der 21-Modell-Blob, S1/S2 die gemeldeten Splits;
  läuft durch dieselbe `_run_charge_attempts()`-Leiter wie die KI; `--neutralize=<helper>`),
  **`measure_charge_scenes.py [--hard] [--diagnose]`** (Charge-Vollendung und engagierte Modelle über
  100 synthetische, per Brute-Force mögliche Szenen auf echtem map2-Gelände; A/B per
  `--neutralize=_charge_slot_first|old_ring` und `--ring-edge=`; `--diagnose` nennt die DECKE — wie
  viele Fehlschläge per legalem PFAD überhaupt erreichbar wären), und
  `measure_crowded_movement.py --army=necrons` als zweite Bewegungs-Baseline neben den Orks.
- **`verify_damage_estimate_move.py`** (Verhaltensneutralität der Schadensschätzung belegen) und
  **`verify_mark_wiring.py`** (Laufzeit-Sonde: kommt ein Controller wirklich in `main.py` an? Hat eine
  tote Verdrahtung gefunden, die keine Suite sehen kann).
  **`verify_sudden_storm_wiring.py [map] [--neutralize]`** — dieselbe Sorte Sonde für einen
  KEYWORD-Grant statt für einen Controller: sie fährt `selfplay.py`s echte `main()`-Schleife per
  `runpy` und fragt beim Kauf des Stratagems die ECHTE `available_shooting_types()` gegen die
  ECHTE Tokenliste, ob die Einheit nach einem Advance schießen dürfte. **Warum sie die
  Advance-Tatsache selbst herstellt:** über 14 000 MockAgent-Frames kommt „gekauft UND advanced
  UND geschossen" nie zusammen — die dokumentierte Harness-Grenze —, ein passives Mitzählen hätte
  also 0 gemeldet und wie ein bestandener Test ausgesehen. `--neutralize` blendet den Grant NUR im
  Tor aus (die Adjuster-Kette gewährt weiter, wie in der echten Vor-Fix-Welt) und meldet `[]`
  statt `['Assault']`.
  **`verify_army_rules_links.py [map] [--neutralize]`** — dieselbe Sorte Sonde für einen
  KLICKPFAD: sie fährt `selfplay.py`s echte `main()`-Schleife und klickt beide Regel-Links GENAU
  DA, wo das Panel sie gezeichnet hat, prüft welche Armee der Leser daraufhin zeigt, schickt ihm
  das echte Mausrad-PAAR und misst, ob er offen bleibt. `--neutralize` stellt den
  Alles-schließt-Zweig wieder her und meldet „geschlossen, Scroll 0".
  **`verify_aura_one_model.py [map] [--neutralize]`** — belegt, dass das Reichweiten-Lineal nur
  das angeklickte Modell ringt: es wählt in der echten `main()`-Schleife ein Modell einer
  Mehr-Modell-Einheit über den ECHTEN `MovementController.select()` und meldet, wie viele Modelle
  der Renderer wirklich umringen sollte (1 von 5 gegen 5 von 5 unter `--neutralize`). **Es klickt
  bewusst NICHT aufs Brett** — ein synthetischer Klick trifft, was gerade auf dem Pixel steht, und
  maß zweimal einen Ein-Modell-Panzer, was in beiden Welten „1 von 1" ergibt.
  **`verify_ai_offline.py [map] [frames] [--neutralize]`** — ein Agent, der beim ersten
  Aufruf `anthropic.APIConnectionError` wirft, in derselben echten Schleife. Meldet, ob
  `main()` überlebt hat, ob der Ausfall mit lesbarem Grund gelatcht wurde, ob die Meldung
  GENAU EINMAL kam — und wie viele Frames danach noch liefen, weil "stürzt nicht ab" und
  "spielt weiter" zwei verschiedene Behauptungen sind (919 gegen 0).
  **`verify_necron_stratagem_buttons.py` / `verify_necron_wraith_form.py`** —
  dieselbe Sorte für die Necrons, und beide fielden sie als **PLAYER 1**:
  `config` liefert `PLAYER2_ARMY = "necrons"` aus, eine Frage über die Knöpfe
  des MENSCHEN misst sonst die Armee der KI und meldet eine wahrheitsgetreu
  aussehende Null. Die zweite postet einen ECHTEN Klick in `main()`s Pump auf
  ein Modell, das das Spiel selbst für wählbar erklärt (3 Wunden gelandet gegen
  `--neutralize`s 1815 Frames blockierend und NIE aufgelöst).
  **`verify_stratagem_tooltip.py [map] [--neutralize]`** — der Stratagem-Tooltip durch dieselbe
  echte Schleife. Sie muss DREI Tatsachen liefern, die dieser Harness nicht selbst herstellt (eine
  gewählte Einheit, ein diese Phase nutzbares Stratagem, und ein Dwell ohne offenen Prompt — die
  KI öffnet alle paar Frames einen, was den Tooltip zu Recht unterdrückt); alles danach ist echt.
  Meldet `'Sudden Storm' (NECRONS) -> 6 printed blocks, drawn=True`, `--neutralize` `never opened`.
  **`verify_phase_autosave.py [map] [frames] [--neutralize]`** — der Autosave durch zwei echte
  `main()`-Läufe: erreichte Phasen gegen geschriebene Autosaves (jede Datei zurückgelesen), dann
  Resume aus dem letzten und ob der Load ihn sofort überschreibt. Lenkt `scene_io.SCENES_DIR` in
  einen Wegwerf-Ordner und schaltet `selfplay.py`s Opt-out beim Bau der Kante wieder ein;
  gefixt 8 Phasen / 8 Autosaves, `--neutralize` 7 / 1 plus Überschreiben beim Load.
  **`verify_ork_*.py [map] [frames] [--neutralize]`** — je Ork-Codex-Etappe eine Laufzeit-Sonde
  (`army_rules`, `war_horde`, `mobs`, `characters`, `specialists`, `vehicles`, `kill_rig`, und für die
  Mecha-Orks-Etappen `mecha_sheets`, `mecha_characters`, `green_tide`, `blitz_brigade`), alle nach demselben
  Muster: Orks als PLAYER 1, gebaute Träger statt der Liste, `main()`s Locals per Frame-Walk,
  `--neutralize` per Import-Hook auf `main.py`. Was jede belegt und stellt, steht in ihrer Etappe in
  `orks-codex-2026-09*.md`. **`verify_ork_vehicles.py`** ist die erste, die eine Platzierung des
  MENSCHEN im Zug der KI offen hält und misst, ob die KI wartet — nicht an „Phase unverändert“,
  sondern an den Positionen der Player-2-Modelle (0 bewegt; ohne `_is_blocked()`s
  Fremd-Platzierungs-Zweig 38). **`verify_ork_kill_rig.py`** treibt als erste
  `agent_driver._handle_fight()` an `main()`s Live-Objekten und prüft, welche Würfe INNERHALB des
  Aufrufs fielen - ein zweiter Wurf ersetzt im Ein-Slot-`DiceManager` den ersten spurlos, und nur
  die Wurf-Etiketten zeigen es. Ihr Zugende-Check fragt die UHR (neuer Runde/Zug-Slot,
  Command-Phase), nicht „Player 2 ist dran": wem der gestellte Zug gehörte, hängt am zufälligen
  Aufstellungswurf. **`verify_ork_mecha_sheets.py`** lässt als erste die KI eine Panel-Fähigkeit
  über `main()`s ECHTES Auto-Play nutzen (Da Jump: Sprung, Quittung durch `main()`, Landung im selben
  Zug) und misst, ob es sich lohnt (Abstand zum Feind vorher/nachher). Zwei Lehren daraus: (a) eine
  Phasengrenzen-Stufe muss im SELBEN Frame starten, in dem die Stufe davor fertig wird — selfplay
  klickt in Player 1s Zug in jedem freien Frame „Next Phase", und eine echte Grenze hatte den zu
  messenden Grant sonst schon gelöscht; (b) erzwungene Würfel so wählen, dass der Angriff OHNE
  Rettungswurf endet (alle Wunden 1), sonst wartet der Lauf auf eine Zuteilung, die niemand gibt.
  **`verify_ork_green_tide.py`** stellt als erste eine ECHTE Engagement-Lage auf `main()`s Brett
  (jedes Infanterieziel der Reihe nach, bis eines Platz daneben hat) und unterscheidet zwei Regeln
  mit demselben sichtbaren Ergebnis am LOG: ein Battle-shock-Test ohne Würfel kann Mob Mentality
  oder Insane Bravery sein - neutralisiert hat die KI genau Letzteres gekauft.
  **`verify_ork_blitz_brigade.py`** ruft `main()`s eigene Quittungstür (`_acknowledge_pending_roll`)
  und feuert `main()`s Charge-Ende-Hakenliste, wie `confirm_charge_move()` es tut. Drei Lehren:
  `testkit` darf NICHT importiert werden (es setzt jeden Würfel des Laufs auf 1 - der erste Lauf
  würfelte nur Einsen), Würfel werden nur um den einen Aufruf getauscht; eine gestellte Charge, die
  zufällig ans Ziel kommt, bleibt offen und hält das Panel auf dem Charge-Bildschirm (flakig 1 von 3,
  bis die Stufe sie nach der Messung ablehnt); und ein Preis an der Fight-Grenze wird NACH der Grenze
  gemessen, weil sie den Kern-CP der nächsten Command-Phase schon gezahlt hat.

  **`verify_ork_da_big_hunt.py`** (G5) treibt zwei Momente, die ein MockAgent-Lauf nicht
  produziert, mit `main()`s eigenen Methoden an: `fall_back_controller.declare()` (die Methode, die
  der Fall-Back-Knopf ruft) für eine Necron-VEHICLE in Ork-Engagement, und das
  Aktivierungs-Ledger des ShootingControllers, gestempelt wie `_handle_hit_results()` es stempelt,
  bevor `main()`s eigene `on_squad_finished_shooting`-Liste gefeuert wird. Danach gehört alles der
  Engine, bis hin zu `main()`s Quittungstür, die den D6 in einen offenen `"surge"`-Zug verwandelt.
  Die Lehre dieses Harness: **an einer Phasengrenze können mehrere Prompts gleichzeitig offen
  sein** — wer auf seinen eigenen wartet, statt die vorderen abzulehnen, misst „angeboten, aber nie
  gepickt" und hält es für einen Engine-Fehler.

  **`verify_mecha_orks_list.py`** (G6) ist das Gegenstück zu jeder anderen Laufzeitsonde hier: sie
  BAUT nichts und STELLT keine Detachment-Config, sondern fragt `main()`s Objekte, was die
  ausgelieferte LISTE allein erzeugt hat (Einheiten, Punkte, Settings, Enhancements, Warlord, die
  drei Transporte, und dass die gekauften Regeln an `main()`s Controllern wirken). `--neutralize`
  nimmt genau das eine weg, was die Liste tut und Config nicht kann: `detachments.apply_to_config()`.
  Drei Lehren stecken in ihr: ein Teilstring-Name misst die falsche Einheit; der Messzeitpunkt ist
  der erste Frame NACH dem Vorspiel (die KI steigt danach wieder aus); und die Transport-Hints einer
  Liste gelten für die AUFSTELLUNGS-KI, also muss die Sonde die Liste auf der KI-Seite fielden.
  **`measure_crowded_movement.py`** hat dazu ein drittes Ziel bekommen: `--army=mecha` misst
  `armies/orks.json`, während `--army=orks` die eingefrorene Messvorlage bleibt, an der die ganze
  Reihe hängt (gedrängt 78 % gegen 62 % — eine Folge der kleineren Liste, kein Fix).

  **`measure_key_melee_deployment.py`** (2026-09-21, aus der Ghazghkull-Meldung) deployt beide
  echten Listen über `deployment_ai` auf ALLEN VIER Karten und fragt die fertige Tabelle: wo steht
  der Nahkampf-Charakter, auf welchem Rang der Armee nach Vorwärtsfortschritt, und ist seine
  BEDINGTE Lone Operative dort an? A/B im selben Lauf — die `fixed=False`-Welt tauscht BEIDE
  Hälften gleichzeitig (`_deployment_role` auf die Fassung vor der Nahkampf-Ausnahme, plus
  `conditional_lone_operative.would_grant_at` auf `False`), weil eine halbe Vor-Fix-Welt hier
  gemeldet hätte, der Fehler habe nie existiert. Drei Dinge, die es bewusst so macht:
  - **Die KONTROLLE läuft mit**, nicht nur der gemeldete Fall: der Daemon Prince of Nurgle trägt
    dieselbe Art Quelle (Death Guard Defenders), behält aber die Rolle „heavy" — ein Term, der IHN
    verschoben hätte, wäre eine Regression und keine Behebung gewesen. Er bewegt sich auf keiner
    der vier Karten.
  - **Der RANG ist die Zahl, nicht die Koordinate.** „−3,39" Vorwärtsfortschritt" sagt nichts ohne
    die Armee daneben; „Rang 9 von 9" ist die gemeldete Beschwerde in einer Zahl.
  - **Ein bewusster Tausch ist von einer Regression getrennt.** Verliert die Einheit ihre Lone
    Operative UND gewinnt Boden, wird das als `traded:` gedruckt und der Lauf bleibt grün; verliert
    sie sie ohne Gegenwert oder geht rückwärts, ist es eine Regression und der Exit-Code ist 1. Die
    Zusicherung wurde damit BENANNT statt aufgeweicht.
