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
  Mecha-Orks-Etappen `mecha_sheets`, `mecha_characters`, `green_tide`), alle nach demselben
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
