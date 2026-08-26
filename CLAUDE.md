# CLAUDE.md

Projektkontext und Hinweise für Claude Code in diesem Repository.

**Diese Datei ist der verdichtete STAND plus die Entscheidungen, die man nicht erneut herleiten soll.**
Die chronologische Historie jeder Sitzung — voller Kontext, Messreihen, Irrwege, Korrekturverläufe —
liegt in `CLAUDE.history.md`. Dort nachschlagen, wenn diese Fassung nicht reicht; ein Fund dort ist
oft die Begründung für eine Zeile hier.

**Pflege:** neue Erkenntnisse gehören VERDICHTET in den passenden Abschnitt unten, nicht als weiterer
Eintrag ans Ende. Die Sitzungserzählung (was gemeldet wurde, was gemessen, was verworfen) gehört nach
`CLAUDE.history.md`. Genau durch das Anhängen ist diese Datei zweimal auf ~1 MB gewachsen.

---

# Teil 1 — Arbeitsweise

## Konventionen (projektweit)

- **Messen statt vermuten.** Jede größere Behauptung in diesem Repo ist eine Messung. Vor einem Fix
  wird der gemeldete Fall REPRODUZIERT (echte Koordinaten aus dem Log, echte Controller); nach dem Fix
  wird die Wirkung beziffert. Mehrfach hat die Messung die naheliegende Diagnose widerlegt — inklusive
  meiner eigenen. Vier Bewegungs-"Verbesserungen" einer Sitzung wurden nach Messung wieder ausgebaut.
- **Kein Reparatur-Retry bei fehlgeschlagenen KI-Bewegungen** (Charge/Pile-In-Kern): scheitert eine
  Platzierung endgültig, wird abgelehnt/übersprungen statt repariert. Ausnahmen sind die echten
  Retry-LEITERN (Winkel-/Distanz-Sweep, Ecken-Routing, A*, Facing-Sweep) — siehe Bewegungsabschnitt.
- **AIMemory-Pattern**: die Engine kennt kein "abgelehnt" (ein Mensch klickt einfach nicht).
  `ai/agent_driver.py`s `AIMemory` (pro `(battle_round, phase, active_player)` zurückgesetzt) trackt
  `declined_*`-Sets selbst, damit dieselbe Einheit nicht jeden Frame erneut (kostenpflichtig) gefragt
  wird. Wo das fehlte, entstanden echte Endlosschleifen (Pile-In, Consolidate, Grav-Inhibitor Field).
- **`turn_owner` vs. `active_player`** (`game/turn.py`): `active_player` ist ein transientes "wessen
  Entscheidung ist das gerade"-Flag (flippt bei Verteidiger-Saves, reaktiven Stratagems),
  `turn_owner` ändert sich NUR in `advance_phase()`. Wer "wem gehört diese Phase" braucht, liest
  `turn_owner`. Mehrere echte Bugs kamen genau daher.
- **Waffen-Instanzen werden nie geteilt mutiert**: jedes Modell hat eigene `WeaponProfile`-Instanzen.
  Effekte kopieren (`copy.copy()`) statt die Basis-Instanz zu verändern. Gleiches gilt für
  `UnitProfile` in Tests — es ist ein KLASSEN-Attribut, ein Flag dort zu setzen schaltet es für jede
  andere aus demselben Datenblatt gebaute Einheit mit.
- **Ein-Repräsentant-Vereinfachung**: einige Mechaniken ([HEAVY], [CLOSE-QUARTERS], [MELTA]) werten
  nur das erste Modell einer `_attack_key()`-Gruppe aus. Bei Cover und bei Psychic Communion wurde das
  korrigiert (echte Pro-Modell-Aufteilung bzw. Bonus im Gruppierungsschlüssel); anderswo bewusst
  belassen, weil die Gruppe sich ohnehin BS/Reichweite teilt.
- **Reaktive Stratagems/Aktivierungen** (Rapid Ingress 15.07, Fire Overwatch 15.08/15.09, Heroic
  Intervention 15.11, Counteroffensive 15.12, Battle Focus' Fade Back/Opportunity Seized, Rangers'
  Path of the Outcast) laufen AUSSERHALB der Phase des reagierenden Spielers.
  **Ein reaktiver ZUG hinterlässt nach seinem Entscheidungsfenster nur einen offenen `move_mode`** —
  `decision_manager.is_pending` ist dann schon False und `turn_owner` gehört der KI, also sieht sie
  ohne eigene Prüfung nichts. Die Menge dieser Modi ist `MovementController.REACTIVE_MOVE_MODES`
  (an `start_battle_focus_move()`, der einzigen Tür dorthin); `_is_blocked()` liest sie. Eine neue
  Fähigkeit mit reaktivem Zug MUSS sich dort eintragen — sonst läuft die KI darüber hinweg, zweimal
  gemeldet. `_is_blocked()`/`take_one_action()` haben dafür
  Sonderfälle; ein offener reaktiver Zug des GEGNERS blockiert die KI, ein eigener nicht.
- **DRITTE Meldung derselben FORM, aber mit ganz anderer URSACHE** (User: "die KI lässt mich immer
  noch nicht den reaktiven Move für die Scouts machen. Sie macht einfach weiter"): SCOUTS (24.31)
  hat mit `REACTIVE_MOVE_MODES` nichts zu tun. `deployment_ai.resolve_scouts()` gibt für eine
  fremde Einheit `False` zurück und sagt im eigenen Docstring, das heiße "dem Menschen überlassen"
  — **die andere Hälfte hat nie jemand gebaut**. `ScoutsStep._resolve_next()` las `False` als
  "abgelehnt", warf die Einheit aus der Warteschlange und leerte diese in EINER synchronen
  Schleife; die Striking Scorpions des Menschen wurden also protokolliert, wie sie einen Zug
  ablehnen, der ihnen nie angeboten wurde. **Ein Kommentar, der ein Verhalten verspricht, das kein
  Code einlöst — dieselbe Klasse wie ein Controller, der gebaut, aber nie gefüttert wird.** Vor der
  nächsten Meldung dieser Form also BEIDE Möglichkeiten prüfen: fehlt der Modus in der Menge, oder
  fehlt der Menschenpfad überhaupt?
- Echte Claude-API-Calls (`ClaudeAgent`) kosten Geld — nur nach explizitem User-Go, nie in Tests.

## Wiederkehrende Fehlerklassen

Das Destillat aus ~2400 Zeilen Historie. Fast jeder gemeldete Fehler fiel in eine dieser Klassen.

**KI / Beobachtung**

1. **Beobachtungslücke, nicht Modellfehler.** Die mit Abstand häufigste Diagnose: die ENGINE kennt
   die Regel und setzt sie durch, aber `ai/observation.py` meldet sie nie — der Planner schreibt
   folglich systematisch Befehle, die nicht ausführbar sind. So aufgetreten bei Sichtlinien, LONE
   OPERATIVE, Reserverunde, Disembark-Zeitpunkt, Nahkampfwaffen, WAAAGH, Hidden, gegnerischen
   Waffenprofilen, Charge-Bedrohung. Vor "das Modell entscheidet schlecht" immer prüfen: **steht die
   Tatsache überhaupt in der Beobachtung?**
2. **Vorgerechnete Zahl statt Rohdaten.** Jede Größe, die das Modell selbst ableiten muss, leitet es
   schlecht ab. Deshalb liefert die Beobachtung Wund-Schwellen statt S/T, Charge-Prozente statt
   Distanzen, `turns_to_reach` statt Zoll, `damage_value` in Punkten statt Anteilen,
   `reachable_this_turn` als Kreis statt "vergleiche mit deiner Bewegung".
3. **Eine vom Modell ERFUNDENE Zahl ist unbewertet.** Ein ausgewählter Gegner trägt seine Bewertung
   mit, eine selbst geschriebene Koordinate nicht. Solche Felder brauchen einen prüfbaren Rahmen
   (`reachable_this_turn`), einen Rückweg an den Planner UND einen deterministischen Backstop.
4. **Eine Regel, die nur im Prompt steht, bleibt optional.** Durchsetzung gehört in
   `_validate_turn_plan()` — dieselbe Quelle, die die Regel ohnehin erzwingt. Der Prompt sorgt dafür,
   dass von vornherein bessere Pläne entstehen; er macht einen Plan nicht legal.
   **Und eine Korrektur DORT muss jedes Feld mitziehen, das dieselbe Frage beantwortet.** Der
   Planeintrag ist kein Datensatz mit einem maßgeblichen Feld: `_handle_movement()` reicht ihn
   KOMPLETT als `plan_context` an die taktische Schicht weiter, `reason` inklusive. Die
   Over-Garrison-Korrektur schrieb `role` und `position` um und ließ den Fließtext stehen — die
   Necron Warriors bekamen `role='advance'` neben "leave this big blob here as garrison ... stay
   Hidden and do not fire" und blieben stehen. Alle sechs Rollen-Umschreibungen setzen jetzt ihren
   `reason` mit; ein Quell-Wächter in `test_report_20260824.py` prüft das für künftige Korrekturen.
   `ai/planner_prompt.py` warnte den PLANNER vor genau dieser Falle ("on the role, not on your
   reason") — nur die Korrekturen, die diese Datei selbst macht, hielten sich nicht daran.
5. **Die Engine darf nicht anbieten, was sie nicht gewählt haben will.** Eine Liste mit einem
   schlechten Eintrag plus der Hoffnung, das Modell lese das Vorzeichen, funktioniert nicht
   (rückwärtige Staging-Punkte, drei Charge-Odds zum Aussuchen). Ehrliche Eligibility statt Filtern
   im Kopf des Modells.

**Engine / Geometrie**

6. **Falsch-Erfolg.** "confirm() meldet keinen Fehler" ist nicht "es hat sich bewegt": werden alle
   Modelle auf ihre Ausgangsposition zurückgeclampt, steht der Trupp legal und meldet Erfolg bei null
   Bewegung. Dreimal auf drei Ebenen aufgetreten (per-Modell, bulk, creep). Immer die TATSÄCHLICH
   zurückgelegte Größe bewerten, nicht die angefragte.
7. **Ein-Schuss-Pfade.** Jeder Platzierungs-/Bewegungspfad braucht eine begrenzte Retry-Leiter
   (8 Facings, Winkel-Sweep, Distanz-Bisektion, Step-over). Ein einziger Versuch scheitert an der
   ersten Wand — beim Disembark kostet das die Einheit.
8. **Kandidaten müssen ALLE Bedingungen kennen, die der Confirm prüft.** Dreimal aufgetreten
   (Gelände, Engagement Range, Brettkante): ein einziger schlechter Slot lässt die GANZE Platzierung
   scheitern, weil `confirm_setup()` am fertigen Trupp urteilt.
9. **Der Trichter ist nicht immer der, der so aussieht.** `_finish_hit_roll()` wird vom
   Monster-Hunters-Zweig umgangen, `_apply_feel_no_pain()` hat nur einen Aufrufer,
   `choose_target_squad()` wird vom Ein-Ziel-Auto-Pick übersprungen, `cancel()` umging die
   13.09-Buchführung. Vor dem Einhängen: alle Aufrufer zählen.
10. **Zwei Stellen, dieselbe Frage, zwei Antworten.** Der häufigste Grund für stille Drift. Daraus
    sind neun Extraktionen entstanden: `invulnerable_save.py`, `crit_hit.py`, `damage_reroll.py`,
    `damage_estimate.py`, `unmodified_six.py`, `psychic_mark.py`, `roll_bonus.py`, `crit_ap.py`,
    `strategic_reserves.py`. Regel: beim ZWEITEN Konsumenten extrahieren, nicht später.
    Seither: `weapon_range.py` (10.), `model_return.py` (11.), `button_style.draw_glow()` (klein),
    `MovementController.can_advance()` (12.), **`combat_focus.py` (13.)**,
    **`game/ui/tile_screen.py` (14.)** — der geteilte Rahmen beider Vorspiel-Screens, siehe
    Kartenauswahl —, und für den
    Auswahl-Screen zwei kleine: `sprites.models_portrait_paths()` und
    `loadout.model_loadout_lines()` — beide beantworten dieselbe Frage eine Ebene tiefer, für eine
    MODELLMENGE statt für ein Squad, weil eine Kachel die Komponenten einer Attached Unit einzeln
    zeigt. **Achtung bei der ersten:** `portrait_paths()` sortiert bewusst den CHARAKTER nach vorn,
    `models_portrait_paths()` nach Zeilenhäufigkeit — die gemeinsame Hälfte ist nur der
    Dedupe-Teil, und die beiden Ordnungen zusammenzuziehen hätte die dokumentierte
    Charakter-zuerst-Regel still gelöscht.
11. **Lügende Namen umbenennen, sobald ein zweiter Träger da ist.** Ein Aeldari-Effekt in
    `ere_we_go.py`, eine Fernkampfregel in `melee_crit.py`, `weapon_support_system` auf einem Aspect
    Warrior — alle drei umbenannt statt kopiert.
12. **Reihenfolge pro Frame.** `remove_dead_models()` läuft EINMAL pro Frame; jeder Trigger davor
    sieht noch Leichen in `squad.models` und `state.tokens`. Daraus: Starflare bot einem toten Träger
    an, eine ausgelöschte Einheit galt als kampfberechtigt, Crewed Platform muss im SELBEN Sweep
    schleifen, und Fade Back wurde einer Einheit angeboten, die genau diese Aktivierung ausgelöscht
    hatte (`battle_focus.is_on_the_battlefield()`). **`not squad.models` ist dafür der FALSCHE Test** —
    er stimmt erst einen Frame später; vor dem Sweep braucht es
    `any(not m.is_dead() for m in squad.models)`, was beide Zeitpunkte abdeckt.
13. **Der gedruckte Regeltext ist die Quelle, nicht die ähnlichste Engine-Hilfsfunktion.** Regel
    11.04 nennt DREI verschiedene Distanzen (Wurf / 1" WHILE MOVING / 2" Engagement) — sie
    zusammenzuziehen hat zweimal einen falschen Fix erzeugt. Bei einer user-gelieferten Regel den
    WORTLAUT erfragen, nicht zwei Lesarten zur Auswahl stellen.
14. **"Zurückgestellt bis X" braucht einen Wiedervorlage-Punkt bei X.** Viermal überlebte ein
    Vermerk seine eigene Bedingung (drei Leader-Fähigkeiten, `scouts`, `infiltrators_clear_of_enemies()`,
    Psychic Guidance). Vor einem neuen Flag prüfen, ob die Regel schon unter einem anderen
    Flavour-Namen existiert (Fieldcraft/Get Da Good Bitz/Stormblades teilen EIN Flag; Acrobatic ist
    Full Throttle; Inescapable Accuracy ist das Weapon Support System).
15. **Eine ANSICHT gehört nicht in die zustandsgegatete Event-Kette.** `main.py`s `for event`-Schleife
    ist ein langes `if/elif` über CONTROLLER-STATE, und fast jeder dieser Zweige behandelt in seinem
    Rumpf NUR Mausklicks. Alles, was weiter hinten hängt, wird vom ersten passenden Zustandsgate
    still geschluckt — der Zweig matcht, tut nichts, und der Rest der Kette läuft nie. Fünfmal so
    aufgetreten: "A", Mausrad-Zoom, ESC im Vollbild, die Log-Filter und zuletzt das ALT-Lineal.
    Regel: was KEINE Entscheidung auflöst (Zoom, Scroll, Hover, Messen) steht VOR der Kette oder
    ganz außerhalb der Schleife. Ein gehaltener Modifikator wird dabei GEPOLLT statt als
    KEYDOWN/KEYUP-Paar geführt — ein Poll kann nicht geschluckt werden, und ALT+TAB kann ihn nicht
    auf "gedrückt" stranden lassen. **Und: die Zustandsfelder, aus denen eine Ansicht GEZEICHNET
    wird, hängen an derselben Kette** — beim Lineal war das die zweite Hälfte des Fehlers.

**Prozess / Test**

16. **Eine A/B-Sonde muss die GANZE Vor-Fix-Welt herstellen**, nicht die eine Zeile. Fünf Instanzen,
    in denen eine halbe Sonde meldete, der Fehler habe nie existiert.
17. **Ein Test, der seinen eigenen Roster baut, bleibt grün, während er die falsche Armee prüft.**
    Zweimal passiert (`test_player1_army.py`, `test_player2_army.py`) — bei jedem Armeewechsel
    mitziehen.
18. **Nur dem EXIT-CODE trauen.** Mindestens drei Suiten druckten "FAILED" und gaben 0 zurück.
    Und: beim Backgrounden nie durch `tail` pipen, wenn der Exit-Code zählt.
19. **`__pycache__`-Rennbedingung** unter dem Parallel-Runner: ein Fehlschlag direkt nach vielen
    Edits erst WIEDERHOLEN, dann suchen. Mehrfach als Scheinfehler bestätigt.
20. **Parallele Claude-Sitzungen auf demselben Repo** kommen vor: vor der Ursachensuche prüfen
    (mtime, A/B), ob ein Fehlschlag überhaupt der eigenen Änderung gehört.
21. **Bash-Heredocs zerlegen Prompt-/Codetexte** (Apostrophe, `\n`, `\"`) — mehrfach passiert.
    Solche Texte über Write/Edit schreiben.
22. **Positionelle Aufrufe**: `action_panel.draw()` und `game_status_panel.draw()` werden positionell
    aufgerufen. Neue Parameter ANHÄNGEN und per Keyword übergeben, sonst verschiebt sich alles.
    Das Panel ist eine dreistufige Kette (`draw` -> `_draw_dispatch` -> `_draw_*_ui`).

## Diagnose-Logging

Wiederholt war der eigentliche Defekt nicht der Fehler, sondern dass er im Log unsichtbar war — die
Untersuchung musste dann aus rohen Koordinaten rekonstruiert werden. Vorhandene `file_only`-Zeilen:
`[move detail]`, `[move choice]` (gewählter Optionstyp + Zielpunkt + Plan-Koordinate), `[charge]`
(Ziel, Wurf, erreichte Kantendistanz, Engagement — auch bei Ablehnung mit den Odds), `[coherency]`
(welche Modelle, wie weit daneben, an jeder Phasengrenze, entprellt), `[threat]`, `[turn plan]`
(inkl. `@(x,y)`), `[ingress]` (der TATSÄCHLICHE Landeplatz), `[regroup]`, `[pile in]` (vorher ->
nachher engagierte Modelle), `[deploy]`, `[charge reroll]`, `[disembark]`.

Wurf-Zeilen tragen ihre Schwelle und die Modifikatoren (`needed 4+: base 5+, -1 (Target Uploaded)`)
sowie die beteiligten Einheiten. **Regel: eine Diagnosezeile, die genau die strittige Zahl auslässt,
schickt die nächste Untersuchung zurück aufs Brett.**

## Tests und Werkzeuge

- **`run_tests.py`** — volle Regression in EINEM Aufruf (alle `test_*.py` parallel, nur Fehlschläge
  gedruckt). Substring-Filter für eine Teilmenge (`python run_tests.py painboy`), `--smoke` hängt die
  schweren Läufe an. Vertraut ausschließlich dem Exit-Code. `KNOWN_FAILURES` trägt einen bekannten
  Fehlschlag samt ERWARTETER Zahl, damit ein NEUER Bruch in derselben Datei nicht mitversteckt wird.
- **`testkit.py`** — geteilter Headless-Harness (gescriptete Würfel über `game.dice.random.randint`,
  fertige Fight-/Shooting-Szenen, `Checks`-Reporter). Sein Docstring listet die Fallen, die früher den
  Großteil der Kosten eines neuen Datenblatts ausmachten.
- **`selfplay.py`** — treibt die ECHTE `main()`-Schleife mit `MockAgent` (0 API-Calls). Bedient die
  Wartefenster, an denen ein naiver Harness stallt und die alle wie ein Engine-Hänger aussehen:
  Auto-Play treibt nur Player 2; "Next Phase" muss geklickt werden und NUR in Player 1s Zug; ein
  anstehender Würfelwurf blockiert alles (und der Klick darf nicht ins linke Panel gehen); die vier
  modalen Overlays; Fire Overwatch; Retro-thrusters. **Bekannte Grenze:** außerhalb des Vorspiels
  beantwortet er keinen Prompt, der dem MENSCHEN gehört — ein stilles Log ist deshalb zuerst
  `decision_manager.is_pending` zu prüfen, nicht ein Engine-Hänger.
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
- **`measure_*.py`** — die Messskripte, die Entscheidungen tragen: `measure_crowded_movement.py`
  (Bewegung mit der GANZEN Armee auf dem Brett — die einzige aussagekräftige Welt, siehe unten),
  `measure_movement_fixes.py` (Geometrie EINER Einheit, macht KEINE Aussage über Spielqualität),
  `measure_placement_headroom.py`, `measure_deployment_safety.py` (Regressionsschranke),
  `measure_ard_as_nails.py`, `measure_stim_injectors_gate.py`, `measure_advance_usage.py`.
- **`verify_damage_estimate_move.py`** (Verhaltensneutralität der Schadensschätzung belegen) und
  **`verify_mark_wiring.py`** (Laufzeit-Sonde: kommt ein Controller wirklich in `main.py` an? Hat eine
  tote Verdrahtung gefunden, die keine Suite sehen kann).
- **`game/scene_io.py` / F9 / `--load`** — Szenen-Snapshot. Positionen, Restwunden, Reserve/Transport,
  Rundenstand, CP; NICHT Terrain/Armeen (die kommen aus Kartenschlüssel und Szene). Ersetzt die
  Handrekonstruktion aus `[move detail]`-Koordinaten, die systematisch die 14 anderen Einheiten
  wegließ — also genau den dominanten Faktor.
- **Testkonvention**: jede Änderung isoliert (echte Controller-Objekte, kein `main()`) UND per
  headless `main()`-Smoke verifiziert. Bei KI-Verhaltensfragen zusätzlich `selfplay.py`.

**Umfangsregel (User-Vorgabe):** ein neues Stratagem/Datenblatt braucht Regel + Panel-Button +
knappen Test, KEINEN KI-Pfad, und wird auf EINER Karte verifiziert. Die volle Matrix (beide Karten ×
beide Deployment-Modi) nur, wenn eine Änderung wirklich Geometrie/Terrain/Aufstellung berührt.

## Harness-Fallen (kosteten wiederholt Zeit)

- `DecisionManager.request()` nimmt **`(label, callback)`-Tupel**, `.options` liefert **Dicts**. Die
  Falle greift in beide Richtungen.
- `TurnTracker.phase` ist eine Property ohne Setter — Phase über `advance_phase()` erreichen.
- Schadenszuteilung MUSS über `ShootingController.choose_damage_model()` laufen, nicht über
  `damage_session.choose_model()` — nur der Controller-Weg ruft `_check_*_done()`. Sonst bleibt eine
  fertige, nicht geleerte Session liegen und maskiert die nächste Wahl.
- `DiceManager`: `pending_values` wird von `acknowledge()` genullt, `already_rerolled` überlebt es
  absichtlich, `last_values` ist der zuletzt bestätigte Wurf. `DiceNotationRoll` liest `last_values`.
- Ein einzelnes Modell zu bewegen bricht 09.02s Kohärenz — Testzüge als starre Translation.
- Ein Ziel innerhalb 2" ist nach 03.04 ENGAGED und damit gar kein legales Schussziel.
- Überschussschaden läuft nicht über: gegen W1-Modelle sind Damage 2 und 6 nicht unterscheidbar —
  für Schadensmessungen ein mehrwundiges Ziel wählen.
- `_squad_key()` matcht den Datenblattnamen als TEILSTRING des Squad-NAMENS; `main.py` benennt Squads
  nach dem Datenblatt, Tests müssen das auch tun.
- Der Turn-Plan-Grund `(test plan)` bzw. `(mock plan)` unterscheidet einen Selbstspiel-Lauf von einer
  echten Partie des Users im selben `logs/`-Ordner.

---

# Teil 2 — Stand

## Karten und Szene

Drei Karten (`game/maps.py`), Auswahl über `config.MAP` (steht auf `map2`) oder `python main.py --map 1`.
Ein `BattleMap` trägt Brettmaße, Deployment-Zonen, Terrain+Objectives, optional ein `roster` (welche
Einheiten diese Karte fieldet) und die handgesetzten Alt-Positionen. Die Armeelisten selbst leben in
`main.py`. `maps.apply_to_config()` schreibt die Brettmaße einmalig beim Start in `config` (~24
Stellen lesen sie zur Laufzeit; kein `from game.config import` im Repo — geprüft).

- **map1** — 44"×60" Hochformat, Terrain nach dem offiziellen "Take Cover"-Layout, per Pixelvermessung
  der Bilddatei nachgebaut. 43 Features (28 sichtblockierend), 5 Objectives.
- **map2** — 60"×44" Querformat, aus `map2 layout.png` gemessen (20 px/Zoll, Zonen je 12" tief,
  180°-Rotationssymmetrie, also Nord/West gemessen und Süd/Ost gespiegelt). **Schräge Footprints
  werden BEGRADIGT gebaut** (User-Vorgabe), jedes an der Achse, an der seine Längsseite ohnehin näher
  lag, bei gemessener Mitte und Größe. 35 Features (20 sichtblockierend), 1.17 ms je Sichtlinienprüfung
  gegen map1s 1.36 ms.
- **map3** — 30"×30" Testbrett mit kleinen Rostern (je 4 Einheiten). **Der Roster hängt an der
  LISTE, nicht am Spieler** (`BattleMap.army_roster`, ein Dict je Liste, mit `"{p}"` als Platzhalter
  für die Owner-Ziffer, aufgelöst in `roster_for(armies)`): ein Roster nennt Einheiten bei ihrem
  exakten Squad-NAMEN, und der beginnt mit dem Owner — sobald JEDER Spieler JEDE der drei Listen
  fielden kann, konnte eine feste Namensmenge nur für eine Paarung stimmen; bei jeder anderen hätte
  kein Name gepasst und die Karte hätte still eine halbe Schlacht gefieldet (was der Wächter in
  `main.py` laut ablehnt). Die vier SLOTS sind für alle drei Listen dieselben, weil sie das sind,
  wofür map3 existiert: der große Attached-Blob, eine Elite-/Gunline-Einheit, ein VEHICLE, und eine
  Einheit, die offenen Boden braucht OHNE das VEHICLE-Keyword (Warbikers bzw. Lokhust Destroyers —
  genau die Form, für die `_needs_open_ground()` existiert). Kein nachgebautes Layout, sondern
  die gemeldeten Fehlergeometrien nebeneinander: 3"-Korridor, nur zur eigenen Kante offene Bucht,
  5"-Tür, 7.2" offene Flanke.

**Warum begradigt statt rotiert:** ein `Obstacle` ist konstruktionsbedingt achsparallel, und
Sichtlinie, Bewegungs-Clamp, A*-Gitter, Platzierungs-Overlay und Renderer lesen `min_x/max_x/...` als
die FORM selbst. Die einzige Stelle mit echtem Umbaubedarf wäre `_route_around_waypoints()`, deren
Korrektheitsargument wörtlich auf Achsparallelität beruht. Eine Treppen-Approximation war gebaut und
getestet, kostete aber 105 Features gegen 35 und ~25% Mehrfläche — wieder ausgebaut.

### Objective-Namen

**Sprechend, und die Himmelsrichtungen sind gegen die gemessene Mitte geprüft** (User: "Dafür
brauchen die Objectives auch sinnvolle Namen, wie z. B. HomeObjective oder CentralObjective oder
Objective East, West oder Northeast"). Aus `No Man's Land (NE/SW/W/E)` wurde
`Objective Northeast/Southwest/West/East`; `Central Objective` und `P1/P2 Home Objective` waren schon
brauchbar und bleiben — bei zwei Home-Objectives ist die Spielerziffer das, was sie unterscheidet.
Der Anlass war Burden of Trust: sein Prompt NENNT das Objective, und "No Man's Land (W)" ist als
Frage an einen Spieler unbrauchbar. Ein Test prüft für jede Karte, dass ein Name mit
Himmelsrichtung auch wirklich auf dieser Seite der Brettmitte liegt, und dass "Central" das der
Mitte nächste ist — ein falsch zeigender Name wäre schlimmer als der alte.

**Die Umbenennung ist gefahrlos, weil nichts nach Namen SUCHT**: No Man's Land wird geometrisch
bestimmt (Mitte in keiner Aufstellungszone), Home ebenso. In `ai/` stehen die alten Namen nur in
Kommentaren und Beispieltexten.

## Kartenauswahl (game/ui/map_select.py)

**Der erste Screen des Spiels** (User: "Vor der Fraktion würde ich jetzt allerdings gerne noch die
Map auswählen. Da wäre es cool, wenn ein Screenshot der Map angeboten werden würde"). Er läuft vor
der Listenauswahl und lange vor dem Vorspiel, weil alles Weitere daran hängt: Brettmaße, Zonen,
Terrain — und auf map3 sogar, WELCHE Einheiten überhaupt antreten (`BattleMap.army_roster`).

- **Die Vorschau ist GERENDERT, kein Screenshot** (`game/ui/map_preview.py`). Ein von Hand
  gespeichertes PNG wäre eine zweite Kopie der Karte, und das Erste, was es täte, wäre veralten —
  das Terrain beider großen Karten ist mehrfach nachgemessen, begradigt und neu gewählt worden.
  Gezeichnet wird die statische Ebene durch denselben `Renderer`, den das Spiel benutzt: Boden,
  jedes Terrain-Footprint samt Wänden, beide Deployment-Zonen und die Objective-Marker. Keine
  Modelle — es ist ja noch nichts aufgestellt.
- **Die Vorschau darf `config` NICHT anfassen.** Der Screen läuft VOR `maps.apply_to_config()`, also
  steht dort noch das Brett des letzten Laufs. Eine Vorschau, die die Maße ihrer Karte hineinschriebe,
  würde das Schlachtfeld allein dadurch entscheiden, dass man sie ANGESEHEN hat. Sie muss es auch
  nicht: `Renderer` bekommt sein `Board` als Argument und `BattleMap.build()` liest die eigenen Maße.
  Als Prüfung festgehalten, nicht als Zusage.
- **Alle Karten werden in DIESELBE Box letterboxed** (gleiche Breite, gleiche Höhe, Seitenverhältnis
  erhalten). Die drei Bretter haben drei Formen (44×60 hoch, 60×44 quer, 30×30) — Kacheln mit je
  eigener Bildhöhe läsen sich als Layout-Unfall, in einer gemeinsamen Box ist die Form des Bretts
  selbst Teil der Aussage. Genau dafür ist ein Bild besser als eine Beschreibung.
- **Die Textzeile wiederholt die Brettgröße NICHT** — die steht schon im Kartennamen ("Take Cover
  (44"x60", portrait)"). Stattdessen Zonentiefe und Niemandsland (map1 18"/24", map2 12"/20", map3
  8"/14") plus Terrain- und Objective-Zahlen, alles am GEBAUTEN Brett gezählt statt danebengeschrieben.
- **`config.MAP_SELECT`** schaltet ihn; `--map` ist eine ANTWORT und überspringt ihn deshalb,
  ebenso `--no-map-select` und ein `--load`-Szenario (der Snapshot nennt sein Brett selbst).
- **`pygame.display.set_mode()` ist in `main()` nach oben gewandert**, vor `apply_to_config()` — ein
  Screen braucht ein Fenster. Zwischen beiden liest nichts eine Brettdimension, was den Tausch
  sicher macht; die Reihenfolge (Fenster → Karte → Brett → Armeen → Einheiten) ist als Quell-Wächter
  in `test_map_select.py` festgenagelt.

**`game/ui/tile_screen.py` ist das geteilte Gerüst beider Screens** — vierzehnte Extraktion, am
ZWEITEN Konsumenten wie die Konvention es verlangt: Seitenrechnung, Kachelrechtecke, Kopf- und
Fußzeile, Kachelrahmen und die Event-Schleife. NICHT darin: was in einer Kachel steht, wie hoch sie
sein muss und was ein Klick bedeutet — genau das ist der ganze Unterschied, und eine Basisklasse, die
das mitbesitzen wollte, wäre nur eine abstrakte Methode pro Unterschied gewesen. Deshalb Funktionen
plus ein kleiner `Paged`-Mixin, und jeder Screen behält seine eigene Klasse. Ein Quell-Wächter
verlangt von BEIDEN, dass sie wirklich hindurchgehen.

## Armeen (game/army_lists.py) und Listenauswahl

**Die VIER Listen liegen in `game/army_lists.py`, nicht mehr in `main()`, und jede baut für JEDEN
Spieler.** Vorher WAR Player 1 die Aeldari und Player 2 eine von zwei — drei Blöcke geradeaus, mit
dem Owner in jedem `build_squad()`-Aufruf und in jedem Squad-NAMEN. Ein Screen, der eine Liste
BEIDEN Spielern anbietet, lässt sich darauf nicht bauen, also ist jede Liste eine Funktion ihres
Owners geworden. Parameterisiert ist NUR der Owner (`owner=` plus der Namenspräfix über
`unit_name()`); Zusammensetzung, Wargear, Anbindungen und Transportzusagen sind die vom User
gelieferten Listen, wörtlich mitsamt ihren Begründungskommentaren umgezogen.

- **Der Squad-NAME ist ein Identifier**, keine Dekoration: `ai/agent_driver.py`s Planbefehle
  adressieren Einheiten über den exakten Namen, `game/maps.py`s Teilroster nennen sie, und ein
  Szenen-Snapshot schlüsselt darauf. Deshalb ist die Form `"<Spielerziffer> <Datenblatt> <Kopie>"`
  tragend und `army_lists.unit_name()` die eine Stelle, an der sie gebildet wird. Ein Spiegelmatch
  funktioniert genau deswegen: dieselbe Liste zweimal teilt keinen einzigen Namen.
- **Was eine `ArmyList` außer ihrem Builder trägt**: Fraktions-Keyword (damit `sprites.py` das Badge
  über denselben Namen findet, den die Regeln benutzen), Name der Armeeregel und des Detachments.
  Die letzten beiden sind LISTENBAU-Erklärungen und aus den Einheiten NICHT ableitbar — derselbe
  Grund, aus dem `SEER_COUNCIL_PLAYERS`/`AWAKENED_DYNASTY_PLAYERS` existieren, und genau deshalb ist
  `apply_to_config()` das, was aus einer Wahl diese Settings macht. **Es setzt sie NEU statt zu
  ergänzen** — sonst liefe ein Spieler Seer Council weiter, ohne Aeldari auf dem Tisch (im Test in
  beide Richtungen belegt). Die Orks brauchen nichts davon: War Horde gatet am ORKS-Keyword.
- **`game/ui/army_select.py` ist der Auswahl-Screen vor dem Vorspiel** (User: "bevor das Pre game
  losgeht, eine Auswahlmöglichkeit für die Völker/listen ... in großen Kacheln ... Volk
  name/logo/detachment und dann die Porträts der einheiten darin ... wenn man über die Porträts
  hovert, sieht man noch mal im Detail, was in dem Squad drin steckt").
  - **ZWEI SCHRITTE, EIN MENSCH.** User: "Aber ich wähle für die KI. Die KI soll nicht selber
    wählen." Also kein Spieler-Schritt und ein KI-Schritt: die Person am Rechner beantwortet beide,
    Player 2s Liste wird der KI ZUGEWIESEN. Der Screen läuft, bevor überhaupt ein Agent existiert,
    und importiert nichts aus `ai/` — als Quellprüfung festgehalten, weil das stärker ist als ein
    Aufrufzähler.
  - **Die Listen bleiben VORDEFINIERT.** User: "Die Listen sollen auch erstmal predefined sein. Also,
    wir brauchen noch keine Listenbaukosten. Das kommt erst viel später." Der Screen wählt, WER
    WELCHE der drei Listen spielt — er ist nicht der Army-Building-Flow der Später-Liste.
  - **Eine Kachel wird GEBAUT, nicht beschrieben**: die Einheiten kommen aus
    `army_lists.preview_squads()`, das denselben Builder ruft wie `main()`. Eine Kachel mit
    handgeschriebenen Einheitennamen wäre eine zweite Kopie der Armeeliste, und das Erste, was sie
    täte, wäre davon abzudriften.
  - **CHARAKTERE UND SQUADS STEHEN IN GETRENNTEN, BESCHRIFTETEN ABSCHNITTEN** (User: "hier würde
    ich tatsächlich in diesem Screen die Charaktere von den Squads trennen, weil jetzt sieht man
    auf dem ersten Blick schlecht, welche Squads da in der Liste sind"). Ein Porträt pro Einheit
    war genau deswegen zu wenig: eine Attached Unit (19.01) ist EINE Einheit, und ihr Porträt ist
    per `sprites._portrait_model_order()` der CHARAKTER — die Aeldari-Liste zeigte also fünf
    Charaktere und keine der fünf Einheiten, die sie führen. Eine Kachel listet jetzt
    KOMPONENTEN: die Leader/Support-Komponenten links oben unter `CHARACTERS`, die Bodyguards und
    alle übrigen Einheiten unter `SQUADS`, jeweils mit Anzahl. Eine nie angebundene Einheit
    entscheidet über das CHARACTER-Keyword ihrer Modelle (so steht ein allein stehender Illuminor
    Szeras oben, ein Doomsday Ark unten). Beschriftet wird mit dem DATENBLATTnamen, nicht dem
    Squad-Namen — der trägt Spielerziffer und Kopiennummer, was auf einer Kachel niemandem hilft.
    Die Abschnittsköpfe liegen über alle Kacheln auf DERSELBEN Höhe (die Charakterzeilen der Seite
    werden reserviert), damit die Squad-Blöcke der drei Listen vergleichbar untereinander stehen.
  - **Der Hover zeigt `loadout.model_loadout_lines()`** — dieselbe Beschreibung wie die
    Transport-Buttons des Vorspiels, nur für die Modellmenge dieser Komponente. Für eine Hälfte
    einer Attached Unit nennt die Karte zusätzlich die andere ("Leads Guardian Defenders,
    Warlock Conclave - one unit (19.01)"): die Trennung würde sonst genau die Information
    verlieren, die die ungetrennte Fassung noch hatte.
  - **Paginierung, sobald nicht mehr alle Listen nebeneinander passen** (User: "was machen wir,
    wenn es mehr als drei Listen sind? Kann man dann weiterschalten? Gibt es eine Paginierung?").
    **Wie viele Kacheln eine Seite trägt, wird aus der FENSTERBREITE abgeleitet**, nicht fest
    gesetzt: gemessen passen bei 1920 px vier Kacheln zu 446 px, bei 1366 px drei zu 418 px — eine
    feste Drei würde den breiten Bildschirm verschenken, eine feste Vier den schmalen quetschen.
    `MIN_TILE_WIDTH = 400` ist die Untergrenze, `MAX_TILES_PER_PAGE = 4` die Obergrenze (ab da
    vergleicht man leichter durch Blättern als durch Hinüberschauen). Vor/Zurück-Buttons,
    Seitenanzeige, Pfeiltasten UND Mausrad — drei Wege hinein, weil ein Screen, der nur auf eine
    Art blätterbar ist, ein geschlucktes Event von unblätterbar entfernt ist; umlaufend, damit kein
    Knopf je tot ist; die Chrome erscheint nur bei mehr als einer Seite. Die ZELLGRÖSSE wird über
    ALLE Listen bestimmt (Blättern soll die Porträts unter dem Cursor nicht umskalieren), die
    KACHELHÖHE nur über die aktuelle Seite. Ein Seitenindex aus einem breiteren Fenster wird beim
    Verkleinern GEKLAMMERT, sonst zeigt der Screen nichts. Getestet mit einer künstlichen
    Fünf-Listen-Registry (`lists=`) und an drei Auflösungen.
  - **Zellgröße und Kachelhöhe sind ABGELEITET, nicht konfiguriert**, und für alle Kacheln
    DIESELBEN — die Listen haben verschieden viele Einträge, pro Kachel gerechnet stünden
    150-px-Porträts neben 88-px-Porträten auf demselben Bildschirm. Erste Fassung deckelte bei
    88 px und ließ das untere Drittel einer 900 px hohen Kachel leer; gemessen und behoben, als
    Prüfung festgehalten ("die Porträts der vollsten Kachel reichen bis an ihre Unterkante").
  - **Eigene Event-Schleife, bewusst**: `main()`s Kette ist ein langes `if/elif` über
    Controller-State und hat fünfmal eine Eingabe geschluckt (Fehlerklasse 15). Dieser Screen
    beantwortet genau eine Frage, bevor es einen dieser Controller gibt, also nimmt er die Events
    selbst. Alles Entscheidende ist eine reine Methode (`layout`/`tile_at`/`portrait_at`/`choose`),
    `run()` fügt nur die Pumpe hinzu. Rahmen, Seiten und Schleife teilt er sich seit der
    Kartenauswahl mit dieser — siehe `game/ui/tile_screen.py` im Abschnitt darüber.
  - **Eine Seite bekommt nie mehr Slots als es Einträge gibt.** Drei Karten auf einem Bildschirm,
    der vier Kacheln trüge, ließen sonst ein Viertel der Breite leer und machten alle drei ein
    Viertel zu klein. Gezählt über ALLE Einträge, nicht über die aktuelle Seite — sonst zöge eine
    angebrochene LETZTE Seite ihre Kacheln breiter als eine volle.
  - **`config.ARMY_SELECT`** schaltet ihn (CLI: `--no-army-select`, `--army1`, `--army2`). Die vier
    Headless-Harnesses stellen ihn AUS — sie beantworten keinen Klick — und ein Quell-Wächter in
    `test_army_select.py` verlangt das von allen vieren, damit ein neuer Harness nicht hängt.
  - **`--load` überspringt ihn**: ein Snapshot hält jetzt fest, welche Listen auf dem Tisch standen
    (`scene_io.armies_in()`), und `main()` baut GENAU die — ohne das würde jeder Einheitenname im
    Snapshot danebengreifen. Optional beim Lesen: ältere Dateien haben die Zeile nicht und laufen
    wie bisher gegen die Settings.

- **Player 1 — Aeldari, 13 Einheiten, 1900 pts** (Default; die gelieferte Liste rechnet 1930, siehe
  Punktenotiz unten). 20 Listeneinträge, 74 Modelle. Fünf Attached Units (19.01): Farseer + Warlock
  Conclave in Guardian Defenders, Eldrad + Warlock Conclave in Storm Guardians, Jain Zar in Howling
  Banshees, Asurmen in Dire Avengers, Lhykhis in Warp Spiders. Dazu Dark Reapers, Falcon, Rangers,
  Shining Spears, Shroud Runners, Striking Scorpions, Warlock Skyrunners, Wraithguard.
  **Der Warlock Skyrunner steht ALLEIN** — seine LEADER-Zeile ist ein JOIN, der nur Windriders nennt,
  und die Liste fieldet keine: eine legale Einzeleinheit, keine gescheiterte Anbindung.
  Die Shining Spears sind der einzige Eintrag mit Nicht-Waffen-**Gear** (das Shimmershield des
  Exarchen ist eine reine ERGÄNZUNG, also `Gear` statt `WargearOption` — die zwei Gear-Spalten der
  ARMY-Tabelle werden hier zum ersten Mal überhaupt benutzt).
- **Necrons — 13 Listeneinträge, 10 Einheiten, 59 Modelle, 2000 pts**, Awakened Dynasty. Default für
  Player 2 (`config.PLAYER2_ARMY = "necrons"`). Vollständig beschrieben im Necron-Abschnitt unter
  `## Fraktionen`.
- **T'au Empire — 14 Listeneinträge, 11 Einheiten, 59 Modelle, 1535 pts**, Retaliation Cadre. Drei
  Anbindungen: Cadre Fireblade in die Breacher (beide im Devilfish), Coldstar-Commander bei den
  Crisis Starscythes (beide in Reserve), Farsight bei den Crisis Sunforges. Der Coldstar trägt das
  Starflare-Ignition-Enhancement — das einzige, das diese Engine wirklich GEWÄHRT statt nur zu
  notieren. **WIEDERHERGESTELLT, nicht neu geschrieben** (User: "wo ist die Tau-Liste?"): die
  FRAKTION war nie weg (14 Datenblätter, Retaliation Cadre samt sechs Stratagems, 43-Einträge-
  Punkteliste, jede Fähigkeit von For The Greater Good bis zur Nova Charge — alles gebaut und
  getestet), gelöscht hatte der Listentausch nur den ROSTER. Er kam Eintrag für Eintrag aus dem
  Initial Commit zurück, mit dem Owner als einzigem parameterisierten Teil. Die 1535 pts sind
  genau die Zahl, die `config.BATTLE_SIZE`s eigene Notiz für Player 1 immer noch nennt — was das
  Ganze als Wiederherstellung ausweist und nicht als Nachbau.
- **Orks — 14 Einheiten, 103 Modelle, 1935 pts**. Attached: Warboss + Painboy im 20er-Boyz-Mob,
  Beastboss in Beast Snagga Boyz (im Kill Rig), Warboss in Mega Armour bei den Meganobz (im
  Battlewagon). Stormboyz und Deffkoptas in Reserve.
- **Keine Liste ist gelöscht** — jedes Datenblatt, jede Fähigkeit und jedes Stratagem aller vier
  wird weiter gebaut und weiter getestet. Geändert hat sich nur, wer standardmäßig antritt und dass
  es wählbar ist. Ein unbekannter Schlüssel scheitert LAUT (`army_lists.get()`) statt still auf eine
  Default-Liste durchzufallen.
- **Punkte weichen pro Einheit von den App-Werten ab** — die transkribierten offiziellen Punktelisten
  gewinnen, die Abweichung ist benannt und nicht angeglichen (bei Player 1 aktuell 12 von 19
  Einträgen). Die ZUSAMMENSETZUNG ist Modell für Modell geprüft (`test_player1_army.py`,
  `test_player2_army.py`). **Seit der Listenrevision laufen die Abweichungen in BEIDE Richtungen** —
  die alte Liste war durchgehend teurer als die Transkription, was "die App rundet auf" zu einer
  verlockenden Erklärung machte; die fünf neuen Einträge widerlegen sie.
- Aufgestellt wird über die **Vorspiel-Sequenz** (03.01, siehe unten). Der alte Modus
  `--no-deployment` nutzt die handgesetzten Tabellen in `maps.py` und bricht mit erklärender Meldung
  ab, wenn sie die gewählte Liste nicht abdecken (statt per `zip()` still Einheiten zu verlieren) —
  der Wächter sitzt jetzt in `army_lists._check_positions()` und gilt damit für jede Liste, nicht
  nur für die eine, die früher fest an Player 1 hing. Er greift auf allen drei Karten: die Tabellen
  wurden für eine seither zweimal revidierte Aeldari-Liste geschrieben.

## Vorspiel (Regel 03.01)

`game/pregame.py` ist ein SEQUENZER, keine zweite Platzierungs-Engine — jede Platzierung geht durch
`SetupController.start_setup()` wie Ingress und Disembark auch. Ablauf: Declare Battle Formations
(Transporter füllen, Reserven deklarieren, 20.01 hart erzwungen) → Roll-off → abwechselnd aufstellen →
zweiter Roll-off (erster Zug) → SCOUTS. **`TurnTracker` bekam `deferred_start=`/`start_battle()`**
statt einer neuen Konstruktionsreihenfolge für ~35 Controller; Battle Round 0 macht Ingress gratis
tot. Beweisbar API-frei (0 Agent-Calls, per Stub-Zähler im Smoke erzwungen).

- **INFILTRATORS (24.20) ist kein eigener Schritt**, sondern ein anderes `position_valid`-Prädikat
  während des normalen Aufstellzugs — und wird deshalb ZULETZT sortiert (früh platziert gewinnt es
  nichts). Distanz 8" (User-bestätigt).
- **Die Aufstellungs-Overlay malt den Modell-Überlappungs-Term NICHT** (User: "ich finde es sinnlos
  bei der aufstellung. ich sehe ja, wenn sich modelle überlappen"). `PregameController.
  overlay_position_valid()` ist das volle Prädikat minus genau diesem einen Term — dem einzigen, den
  man mit eigenen Augen vom Brett ablesen kann, weil dort eine Base gezeichnet steht. Alles Übrige
  bleibt, weil es UNSICHTBARE Information ist: Zonenkante (03.01), Dense-Gelände (13.05),
  Brettkante, die 8"-INFILTRATORS-Blasen (24.20). Gemessen auf map2 mit 32 bereits aufgestellten
  Modellen: **230 → 132 sq.in rot** in der eigenen Zone (31.9% → 18.3%), 98 sq.in verschwinden.
  **Aus dem echten Prädikat NICHT entfernt** — die Regel wird weiter doppelt erzwungen
  (`clamp_drag()`/`apply_group_drag()` rutschen an die Grenze, `confirm_setup()` prüft
  `check_model_overlap()`), was hier verborgen wird, kann also nicht COMMITTET werden. Damit ist die
  gemalte Fläche etwas GRÖSSER als die legale, und diese Richtung ist die sichere: ein Zug dort
  hinein stoppt, und der Grund steht sichtbar davor. Nur die Aufstellung — Ingress (20.04) und
  Disembark (18.04/18.05) behalten das volle Bild, weil dort ein an eine fremde Base verlorener Platz
  weder offensichtlich noch billig ist (ein gescheiterter Emergency Disembark tötet die Einheit).
  Die KI ist unberührt: `deployment_ai` ruft `pregame_ctrl.position_valid()` direkt, nicht über den
  Overlay-Pfad. Getestet in `test_pregame.py` (Abschnitt 6b/6c, **125/125**), A/B in beide Richtungen
  (Relaxation an der Quelle zurückgebaut → 2 rot; `main.py`s Zweig entfernt → 2 rot).
- **SCOUTS (24.31/24.32)** in allen drei Zweigen; der DEDICATED-TRANSPORT-Zweig ist als WÄCHTER gebaut
  (gibt `[]` plus eine Logzeile, welche Vorbedingung fehlte) statt spekulativ.
- **KI-Formationen sind deterministisch**: DEEP STRIKE zieht in die Reserve (in PUNKTEN gerechnet,
  nicht als flacher Bonus — der erste Versuch war ein Skalierungsfehler), Transporter füllen nach
  einer expliziten Prioritätstabelle je Transportertyp (`TRANSPORT_PASSENGER_PRIORITY`, erschöpfend;
  Gretchin stehen zusätzlich auf `TRANSPORT_NEVER_EMBARK`).
- **KI-Aufstellung misst Exposition gegen die gegnerische ZONE**, nicht gegen Modelle (beim
  abwechselnden Aufstellen steht der Gegner nur teilweise). Rollenabhängiger Scorer (key/screen/
  shooter/heavy/assault) plus ein HIDDEN-Term (13.09): die ganze EINHEIT muss verdeckt sein, also
  wird der PACKER auf Dense-Areas eingeschränkt, statt nur den Abwurfpunkt zu bewerten. Gemessen
  2/9 → 9/9 (map1) bzw. 7/9 (map2) vollständig verdeckte Einheiten, Preis ~1.3" Vormarsch.
- **`assault` ist die fünfte Rolle und nimmt nur Einheiten, die sonst ein `screen` wären.** User:
  "die skorpekh destroyer standen sehr weit hinten und sind nicht durch die warrior durchgekommen
  ... nahkämpfer sollten eher weiter vorne starten, aber möglichst versteckt." Der SCORER war nie
  das Problem — ein Screen-Schlüssel beginnt bereits mit `-forward_bucket`. Falsch waren die
  WARTESCHLANGE (nach `-len(models)` sortiert, also wählte ein 3-Modell-Elitetrupp aus dem, was ein
  21-Modell-Blob übrig ließ) und der HIDDEN-PASS, den `_wants_hidden_pass()` einem Screen
  vorenthält. Gemessen auf der gemeldeten Aufstellung: Skorpekh **−3.04" → +0.97" vorwärts und
  1/3 → 3/3 verdeckt** (map1: −2.04" → +3.98", 0/3 → 3/3), Canoptek Wraiths und Lychguard
  0/6 → 6/6.
  - **Der Preis ist benannt:** die großen Fernkampf-Blobs verlieren die Dense-Fläche an die
    Nahkämpfer (Necron-Armee 32/59 → 20/59 verdeckte Modelle auf map1). Die MITTLERE Exposition
    bleibt praktisch gleich (0.0 → 0.2), es geht also der 13.09-Schutz verloren, nicht die Deckung
    — und der Shooter-Scorer wählt dann eine Schusslinie (Exposition 3 von 33, innerhalb
    `SHOOTER_IDEAL_EXPOSURE`), was seine Aufgabe ist. Bei den Orks geht es umgekehrt aus
    (30/79 → 38/79). Der Vormarsch-Mittelwert der Armee steigt leicht auf 3 von 4 Szenarien.
  - **Der Rollen-Test ist derselbe wie bei der Charge-Sperre** (`combat_focus.is_assault_unit()`),
    aber bewusst die STRENGE Fassung statt "lehnt nach Nahkampf": Gretchin lehnen auch nach Nahkampf
    (0.97) und sind genau der billige Screen, den der frühere Report auf dem Home Objective haben
    will. Band 0.16..0.97, Schwelle 1/1.4 = 0.71.
  - **Nebenbefund:** `_hidden_pass_points()`s Vorwärts-Bucket-Einschränkung nannte `"screen"` und
    war damit UNERREICHBAR (`_wants_hidden_pass()` schließt Screens vorher aus). Die Messung dahinter
    wurde gemacht, das Ergebnis behalten — und der Code, der es trug, blieb beim nächsten Umbau
    stehen. `assault` ist die Rolle, die diesen Handel wirklich will; damit lebt der Fund wieder.

## Regelengine — Bewegung

Move-Typen (09.02): Remain Stationary, Normal, Advance (09.06), Fall Back (09.07), Charge (11.04),
Pile-In (12.03), Consolidate (12.07/12.08), Surge (21.02), Ingress (20.04)/Strategic Reserves,
Transport Embark/Disembark (18.x inkl. Rapid/Tactical/Combat/Emergency + Hazard-Rolls), Take to the
Skies (21.03). Dazu Sonderzüge außerhalb der Bewegungsphase: Scout Move, Retro-thrusters, Torchstar
Gambit, Tactical Acumen, Battle Focus' reaktive Züge, Path of the Outcast — alle über
`start_post_shooting_move()`/eigene Starter, bewusst NICHT über `can_move()` gegated (das fragt "ist
das der Bewegungsphasen-Zug dieser Einheit", die falsche Frage) und mit eigenem `move_mode`, der den
Confirm-Button an den zuständigen Controller routet.

- **Sofort-Prüfung pro Segment**: Terrain/Überlappung/Engagement werden beim Committen jedes
  Modell-Segments geprüft (`try_commit_segment()`), nicht erst bei `confirm_move()`. Ein abgelehntes
  Modell springt nur selbst zurück. Coherency und "muss das Ziel erreichen" bleiben squad-weite
  Confirm-Prüfungen (nicht einem Modell zuordenbar).
- **Ein abgelehnter Versuch kostet nichts** — `try_commit_segment()` zieht nur bei Erfolg ab. Deshalb
  ist Hartnäckigkeit billig: `_advance_model_toward()` weicht bei Ablehnung erst SEITLICH aus (±45°,
  kleinste Winkel zuerst — cos(45°) behält 71% Vorwärtsanteil) und kürzt erst danach.
- **Kohärenz-Buchführung**: die 9"-Spannweitengrenze gilt nur noch für `config.SPREAD_LIMIT_PLAYERS`
  (= Player 1) — für die KI aufgehoben (User: sie würde Screens nicht über die Karte ziehen). Die
  2"-Zusammenhangs-Hälfte gilt für alle; sie ist die eigentliche Anti-Missbrauchs-Regel.
- **Eine gebrochene Einheit kann sich reparieren**: `_regroup_move()` packt sie mit
  `formation_layout.pack_positions()` neu (Zusammenhang per KONSTRUKTION), bevor der gewöhnliche
  Sweep läuft. Ohne das war sie dauerhaft eingefroren, weil `confirm_move()` 09.02 absolut erzwingt,
  während die KI-Seite gegen eine Baseline misst. Gemessen 20/90 → 2/90 eingefrorene Szenarien.
- **Regaining Coherency (09.02) entscheidet die KI selbst** (`_coherency_removal_pick()`): Charaktere
  zuletzt, dann Sergeant, dann wenigste Wunden. Vorher konnte nur ein Mensch die Wahl beantworten —
  auch für Einheiten der KI.
- **`_place_packed()` ist ein KANDIDAT, kein Ersatz**: eine Einheit scheitert oft an ihrer eigenen
  FORM, nicht am Boden (starr blockiert / gepackt passt). Packen läuft deshalb durch dieselbe
  `consider()`-Bewertung wie jeder andere Kandidat. Gemessen +2 Punkte Median, +5.5" Gesamtboden,
  Stillstände 2 → 0.
- **Der innerste Packungs-Ring wird ZUSÄTZLICH angeboten, nicht verschoben** (`ring_candidates`s
  `inner_radius`, gesetzt von `pack_positions()`). `step` kommt aus der KLEINSTEN Basis, auf dem
  Abwurfpunkt steht aber per Widest-First die GRÖSSTE — der erste Ring fällt dann an
  `_first_legal_slot()`s Überlappungsschranke KOMPLETT aus, nicht nur um einen Slot. Gemeldet an den
  Necron Warriors ("so viel Abstand zu ihrem Character ... Footprint unnötig groß"): Ring 1 mit NULL
  Modellen, Technomancer allein in einem 1.39"-Graben, während seine Krieger 0.29" auseinander
  standen. Mit dem Extra-Ring: Graben 0.05", Ring 1 trägt 6, Spread 7.20" → 6.24", bbox 8.33×7.50 →
  6.00×7.50. **Addieren statt Ersetzen ist der Kern:** innerhalb EINER Einheit ist der nötige Abstand
  paarweise verschieden, ein einzelner Radius kann nicht allen dienen — ein zusätzlicher Ring nimmt
  keinem Modell einen Platz weg, ein verschobener schon. Nur wenn er WEITER AUSSEN liegt als der
  erste reguläre; sonst bekäme jede homogene Einheit einen zweiten, engeren Ring, den sie nie
  brauchte (2r+0.05 gegen einen 2r+0.1-Pitch). **Nicht gratis, und das ist gemessen:** ein dichterer
  Block ist ein anderer Block, `measure_crowded_movement.py` bewegt sich pro Einheit in beide
  Richtungen (Boyz+Warboss+Painboy +6 auf map1, Gretchin 2 −10 auf map2), Mediane 64→65 / 62→59 /
  29→28. Betroffen sind ausschließlich Einheiten mit gemischten Basen; die großen Einzelausschläge
  bei homogenen Einheiten (Tankbustas −20) sind belegte KOPPLUNG, sie bekommen nie einen Ring.
- **`_creep_toward()`** als letztes Netz: größte noch legale starre Translation per Bisektion. Sie
  bewertet die GEMESSENE Strecke, nicht die angefragte, und verwirft einen Versuch, der nicht wirklich
  starr blieb (Step-over und Friendly-Clamp können einzelne Modelle abweichend weit bewegen).
- **Raumbedürftige Einheiten**: `_needs_open_ground()` fragt "kann diese Einheit Dense-Gelände
  durchqueren" (13.06) statt nach dem VEHICLE-Keyword — Warbikers haben alle Probleme eines Fahrzeugs
  und keines seiner Keywords. Bewegungsreihenfolge in Stufen: (0) räumt einem Fahrzeug den Korridor
  ODER steht in einer Ausladezone, (1) raumbedürftig, (2) Rest. Stufe 0 verdient sich ein Trupp nur,
  wenn er den Korridor durch seinen eigenen Zug SEITLICH verlässt; ein Fahrzeug, das auf dem
  ausdrücklichen Plan-Platz eines anderen parken würde, fällt auf Stufe 2.
- **`find_route()`** weicht bei blockierter START-Zelle auf die nächste brauchbare aus (der
  Zellmittelpunkt kann in einer Wand liegen, während die Einheit legal davor steht) — vorher gab es
  für eine wandnah geparkte Einheit dauerhaft `None`. Der geroutete Kandidat wird an der ROUTENLÄNGE
  gemessen, nicht am Luftlinien-Fortschritt (der erste Schenkel eines Umwegs steht fast senkrecht zum
  Ziel), plus `_place_rigid_route()` als starre Variante.
- **Charge**: `_CHARGE_STEP_OVER_IN`-Leiter (Modell auf einer dünnen Wand rückt entlang derselben
  Linie weiter, statt zurückzuspringen), `_engagement_slots()` verteilt Standplätze RINGS UM das Ziel
  (Charge 5 → 9 Modelle im Nahkampf), 11.04s 1"-Pflicht wird über die Ringtiefe erzwungen (Pile-In
  bekommt sie per 12.03 ausdrücklich NICHT), Baseline-Fehler werden vor Phase 1 gemessen (eine schon
  gebrochene Einheit muss den geerbten Zustand nicht reparieren).
- **Disembark**: KLUMPEN statt Ring (Kandidaten nach Abstand zu einem Abwurfpunkt am ÄUSSEREN Rand
  der Zone, greedy kohärent gefüllt) — die Ringform erzeugte Ketten mit Single-Point-of-Failure.
  Gemessen 0 Bridge-Kanten und ≥95% Drift-Überleben gegen vorher 5 bzw. 73%. Acht Facings,
  Pro-Modell-Prüfung gegen `position_valid()` (inkl. Engagement Range — das Fehlen kostete einmal
  einen ganzen Trupp im Emergency Disembark), gemischte Basen: dichte Kandidaten aus der KLEINSTEN
  Basis, Vergabe breitestes Modell zuerst.
- **Front Rank**: Nahkampf-Charaktere werden ZUERST platziert (aus einer vorne-zuerst sortierten
  Kandidatenliste), nicht nachträglich getauscht — ein Tausch scheitert bei größerer Basis am Raster.
  Gilt für Aufstellung, Ausstieg und die Engagement-Slot-Vergabe. Übernommen wird nur, wenn die
  Variante nicht MEHR Kohärenz-Einzelpunkte hat (`bridge_count()`/`no_worse_than()`).

## Regelengine — Schießen

Shooting-Typen (10.02/10.04-10.07): Normal, Assault, Close-Quarters, Indirect, Snap Shooting (nur
reaktiv). Split Fire, und die Weapon Abilities [ANTI-X]/[ASSAULT]/[BLAST]/[CLEAVE]/[CLOSE-QUARTERS]/
[DEVASTATING WOUNDS]/[EXTRA ATTACKS]/[HAZARDOUS]/[HEAVY]/[IGNORES COVER]/[LANCE]/[LETHAL HITS]/
[MELTA X]/[ONE SHOT]/[PISTOL]/[PRECISION]/[PSYCHIC]/[RAPID FIRE X]/[SUSTAINED HITS X]/[TORRENT]/
[TWIN-LINKED] sind implementiert.

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
  Bounding-Box (mathematisch identische Ergebnisse, per 400 Fuzz-Vergleichen belegt);
  `valid_target_models()` dedupliziert pro SQUAD; mehrere UI-Caches.
- **Hausregel**: befreundete Modelle blockieren keine Sichtlinie — am BEOBACHTER festgemacht (beide
  Enden auszunehmen würde Modell-Blockade ganz abschaffen). Gegnerische blockieren unverändert,
  Screening funktioniert also weiter.

## Regelengine — Nahkampf

12.01-12.06 (`game/fight.py`, `game/pile_in.py`), inkl. Split Fire, Pass, echtem Pile-In/Consolidate
für die KI.

- **Waffenwahl (04.01)**: die Engine sperrt nach dem ersten Schwung jede weitere
  nicht-[EXTRA ATTACKS]-Nahkampfwaffe DIESES Modells. Die KI wählt jetzt bewertet
  (`expected_wounds()` mit `effective_weapon_skill()` — die Power Klaw druckt WS4+, "größtes S" wäre
  die falsche Regel) und fragt den Agenten NUR, wenn die stärkste Gruppe einem Modell wirklich etwas
  verbaut.
- **Zwei Hänger-Klassen behoben**: ein blockierter Pile-In wurde endlos wiederholt (jetzt: illegale
  Platzierung zurücknehmen + `skip_pile_in()`, 12.03 macht ihn optional), und die
  `CHOOSING_TARGET`/`CHOOSING_WEAPON`-Behandlung war nur INNERHALB desselben Aufrufs erreichbar
  (jetzt Resume-Zweig vor dem SELECTING-Gate). Consolidate verlangt zusätzlich
  `fight_controller.state == DONE` — vorher konnte eine Einheit konsolidieren, während der Nahkampf
  noch lief.
- **Pile-In holt Modelle nach vorn**: `_ranked_free_slots()` liefert eine Rangliste statt eines
  Platzes, besetzte Plätze werden LIVE gelesen, Modelle in Basenkontakt bleiben stehen (12.03), und
  bewertet wird "wie viele Modelle sind danach in Engagement Range" statt der zurückgelegten Strecke.
- **Fights First (24.13) entscheidet die REIHENFOLGE, nicht die Berechtigung** — es als dritte Art
  von "kampfberechtigt" zu lesen ließ Einheiten 18" vom Gegner am Ende jedes Zuges eine Auswahl
  verlangen.
- **Eine ausgelöschte Einheit ist nicht kampfberechtigt** (die klebrigen Marker `engaged_at_start`/
  `fights_first` wussten nichts von ihrem Tod) — sonst hängt der Fight-Step dauerhaft.

## Regelengine — Command-Phase / Stratagems / Schaden

- Battle-Shock (01.07/08.03), Command Points (08.02), alle Core-Stratagems mit Anwendungsfall:
  Command Re-roll (15.02), Insane Bravery (15.04), Explosives (15.05), Crushing Impact (15.06),
  Rapid Ingress (15.07), Fire Overwatch/Snap Shooting (15.08/15.09), Heroic Intervention (15.11),
  Counteroffensive (15.12), Epic Challenge (15.03). `StratagemController` trägt die 15.01-Buchführung
  (einmal pro Phase/Ziel, optional `max_per_battle`, optional `allow_battle_shocked_target`).
  `_cost_for()` ist die EINE Definition des Preises, gelesen von `can_use()` UND `use()`; Rabatte
  hängen als Liste `cost_discounts` dran (Puretide, Strands of Fate).
- **Ein Würfel wird NIE zweimal neu geworfen.** `DiceManager.already_rerolled` ist das Gedächtnis
  dafür (überlebt `acknowledge()` absichtlich); Command Re-roll, [TWIN-LINKED], Forward Observers,
  Breach and Clear und jede Ability-Quelle lesen es. Vier illegale Paarungen waren vorher möglich.
  Breach and Clear behält beim Vollwurf die Wunden zurückgehaltener Würfel.
- **Reroll-Umfang folgt dem Wortlaut**: "re-roll the Wound roll" = GANZER Wurf (Breach and Clear,
  Sunforge, Assured Destruction, Storm of Silence), "re-roll FAILED" = nur Fehlschläge
  ([TWIN-LINKED] — ausdrückliche User-Korrektur). Wo ein Vollwurf angeboten wird, gibt es zusätzlich
  die Nur-Fehlschläge-Teilmenge; Swift Demise ist der einzige Offer ohne Abwählen (seine 1en sind
  nicht optional).
- **Deadly Demise (24.08)** würfelt die Schadensmenge PRO EINHEIT (ein geteilter Wurf machte aus
  ~14 erwarteten 24 Mortal Wounds).
- **Wundzuteilung**: Allocation-Groups sortieren "schwächste zuerst" mit ABSOLUTEN Restwunden als
  Term — sonst stand der 2W-Anführer vorn und die erste Wunde wurde ohne Rückfrage auf ihn gelegt.
  Die KI wählt innerhalb der Gruppe das erste NICHT-`squad_leader`-Modell. Regeln schlagen die
  Präferenz (05.04s verwundetes Modell zuerst, 05.03s CHARACTER-Schutz).
- **Save-Schwelle**: `damage_resolution.save_thresholds()` ist die EINE Definition (Rüstung, AP,
  Invuln, Ramshackle) — Auflösung und Würfelanzeige lasen sie vorher getrennt, weshalb ein über den
  Invuln geretteter Würfel rot gezeigt wurde.
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

## Aktionen (Regel 16.01, game/actions.py)

**Diese Engine hatte bis Cleanse überhaupt keinen Aktions-Begriff** (`game/fall_back.py` schrieb das
selbst aus, CLAUDE.md führte es als benannte Lücke). Der User lieferte den Kernregeltext von 16.01
wörtlich; `game/actions.py` ist dessen Transkription plus genau die Haken, die die erste Karte
braucht — kein spekulatives System.

- **`ActionDefinition` sind die sechs gedruckten Felder und nichts weiter** (STARTS / UNITS /
  USE LIMIT / COMPLETES / EFFECT plus Zusatzbeschränkungen), also ist eine neue Aktion ein Objekt
  und keine neue Mechanik.
- **EIN `ActionController` für ALLE Aktionen**, nicht einer pro Aktion: Eignung, die zwei Sperren
  und der Bewegungs-Abbruch sind geteilt, und *"it started another action this turn"* ist eine
  Frage über alle gleichzeitig.
- **Die zwei Sperren liegen NICHT als Squad-Flags herum**, sondern werden bei diesem einen
  Controller erfragt — `shooting.can_shoot()` und `charge.can_declare_charge()` beantworten diese
  Fragen schon, ein zweiter Merker wäre die Drift, die dieses Repo laufend konsolidiert.
  - **Die Asymmetrie ist gedruckt und einzeln gepinnt:** die Schuss-Sperre nimmt TITANIC aus, die
    Charge-Sperre NICHT.
  - **Beide Sperren überleben den ABBRUCH der Aktion.** Wer eine Aktion begonnen hat, hat sie
    begonnen — eine Bewegung nimmt die Vollendung, nicht die Sperre.
- **Der Bewegungs-Abbruch bekommt die Bewegungs-ART übergeben** (`notify_move(squad, move_mode)`),
  gemeldet aus `confirm_move()` — der einen Stelle, durch die jede bestätigte Bewegung läuft. Die
  zwei gedruckten Ausnahmen (Pile-In, Consolidate) werden damit BEIM NAMEN erkannt statt geraten,
  und eine neue Bewegungsart muss sagen, welche sie ist.
- **AIRCRAFT, FORTIFICATION und TITANIC sind belegte No-ops** (keines der Keywords existiert hier,
  dieselbe Ausnahme, die `rapid_ingress.py` schon dokumentiert) — trotzdem ausgeschrieben und die
  Profil-Flags gelesen, damit die Transkription vollständig bleibt.
- **`start_eligibility()` gibt einen GRUND zurück**, nicht nur False: ein Angebot, das lautlos nicht
  erscheint, ist genau die Form, in der sich ein Eignungsfehler versteckt.
- **`reset_for_turn()` läuft NACH `begin_end_of_turn()`** — vorher zu löschen würfe die Aktionen
  dieses Zuges unvollendet weg, und der Quell-Wächter prüft die Reihenfolge.

## Missionen (game/missions.py, game/secondary_missions.py)

Primary **"Hold the Line"** (3 VP je kontrolliertem Objective, zu Beginn der eigenen Command-Phase)
gilt für BEIDE Spieler und ist unverändert. Die Secondary **"No Mercy"** (1 VP je zerstörter
Feindeinheit) gehört jetzt nur noch der KI: wer in `config.SECONDARY_MISSION_CARD_PLAYERS` steht
(= Player 1, der Mensch), spielt STATTDESSEN einen **Tactical-Secondary-KARTENSTAPEL**. Der Flag ist
eine Listenbau-Erklärung, aus dem Brett nicht ableitbar — dieselbe Begründung wie
`SEER_COUNCIL_PLAYERS`. `BATTLE_ROUNDS = 5` liegt weiter in `missions.py`, weil Missionen die
Spiellänge definieren.

- **Der Ablauf** (User-Vorgabe, keine Kernregel): zu Beginn der EIGENEN Command-Phase zwei Karten
  ziehen → Klick-weg-Overlay zeigt sie → sie landen in der Leiste links. Handkartenzahl ist
  **unbegrenzt**. Ist die Bedingung einer Karte an ihrem eigenen Zeitpunkt erfüllt, wird GEFRAGT
  ("jetzt einlösen oder behalten") — **nie automatisch gutgeschrieben**. Am Ende des eigenen Zuges
  kann stattdessen eine Karte für **+1 CP** abgeworfen werden. Höchstens **15 Secondary-VP pro
  Schlachtrunde**.
- **Der Stapel wird NICHT nachgemischt** (User-Entscheidung): jede Karte einmal pro Schlacht, danach
  läuft er leer. Mit den bisher zwei Karten heißt das: Runde 1 zieht beide, ab Runde 2 nichts mehr.
- **Der +1-CP-Deckel ist NICHT nachgebaut** — `CommandPointManager.gain_cp()` trug ihn schon
  (`BONUS_CP_PER_ROUND_CAP = 1`, geteilt über ALLE Bonus-Quellen). Neu ist nur
  `bonus_cp_remaining()`, gelesen von `gain_cp()` UND vom Angebot, damit ein Abwurf nicht angeboten
  wird, der 0 CP brächte (Fehlerklasse 5). Zweiter Konsument → eine Definition.
- **Die 15-VP-Grenze KLAMMERT statt abzulehnen**, und das Prompt-Label sagt es
  ("Score 3 VP (this round's 15 VP cap)"). Ist die Runde ganz ausgeschöpft, wird gar nicht erst
  gefragt.
- **Der Kartenstreifen ist BEWUSST reine Anzeige.** Die Karten liegen bei
  x ≥ `left_panel_rect.right`, also INNERHALB `board_rect_screen` — ein Klick fiele durch die
  zustandsgegatete Kette auf den Board-Zweig (Kamera-Schwenk). Ein neuer Zweig davor wäre genau
  Fehlerklasse 15. Deshalb läuft JEDE Wahl über `DecisionManager`, den Overlay, der ohnehin jede
  andere Entscheidung des Spiels zeichnet. Nebeneffekt: `_maybe_resolve_decision()` könnte die Karten
  ohne Zusatzverdrahtung für einen KI-Spieler beantworten.
- **Layout: Akkordeon statt Schlitze** (User: "nicht vertikal an der Leiste hängen, sondern
  horizontal übereinander geschichtet … fahren sie aus wie ein Akkordeon-System"). Eine Karte ist ein
  volle Breite hoher **Balken (28 px)** mit Kategorie, Namen und STATUS. Hover öffnet die HÖHE genau
  einer Karte.
  - **Der Status einer Secondary nennt IHREN Zeitpunkt ("end of your turn"), keine Live-Erfüllung.**
    Die erste Fassung zeigte eine Momentaufnahme ("würde das punkten, wenn der Zug jetzt endete") als
    `READY` — und damit stand Centre Ground schon in der Bewegungsphase auf erfüllt (User: "mir ist
    aufgefallen, dass ich gerade Center Ground mitten im Zug schon erfüllt habe … Center Ground wird
    erst am Ende meines Zuges erfüllt"). Eine Karte wird an IHREM gedruckten Zeitpunkt gemessen und
    an keinem anderen; die Mitte zu halten ist bis dahin eine Stellung, kein Punktestand — und ein
    Balken, der etwas anderes behauptet, lädt genau zu dem Zug ein, der sie vor Zugende wieder
    hergibt. `READY - n VP` (grün) erscheint jetzt ausschließlich, solange der Einlöse-Prompt DIESER
    Karte offen steht; die Quelle dafür ist `offered_now()`, nicht `achieved()`. Der alte Aufbau war die andere
  Achse (150-px-Karten, Breite 26→250, Titel um 90° gedreht) und skalierte nicht: vier Karten
  brauchten schon 648 px. **Player 2s Karten sind ganz raus** (User-Vorgabe).
  - **Überlauf = SCHINDELN**: passt die Hand nicht mehr, wird der Abstand negativ und die Balken
    überlappen, geklammert auf `MIN_BAR_OVERLAP_STEP = 12` sichtbare Pixel je Karte. Gemessen: 42
    Karten passen exakt bis `TOP_MARGIN`. Genau das macht die unbegrenzte Hand ohne Paginierung
    möglich.
  - **Das VORZEICHEN des Bottom-up-Akkumulators ist die Stolperstelle**: nach oben gebaut liegt die
    Unterkante der nächsten Karte einen Abstand ÜBER der Oberkante dieser — ein negativer Abstand muss
    also SUBTRAHIERT werden. Falsch herum spreizt es die Balken, statt sie zu schindeln, und der
    Stapel läuft still oben aus dem Bild (gemessen: `top = -472`). Mit drei Karten sieht das gesund
    aus, mit dreißig nicht. **A/B belegt:** Vorzeichen zurückgedreht → 4 Prüfungen fallen.
  - **Trefferprüfung von OBEN nach unten** (zuletzt gezeichnete Karte zuerst): geschindelte Balken
    überlappen, und die obenauf gezeichnete ist die, auf die der Cursor zeigt.
  - Hover wird wie bisher GEPOLLT (`pygame.mouse.get_pos()` in `draw()`) — nichts hängt in der
    Event-Kette. Kosten gemessen: 0.21 ms/Frame bei 2 Karten auf einem 130-Modell-Brett
    (40 Karten: 3.2 ms, mit dem Zwei-Karten-Stapel unerreichbar).
- **`game/ui/mission_draw_overlay.py`** ist das Klick-weg-Overlay, nach `StratagemNoticeOverlay`
  gebaut (QUEUE, nicht Slot). Es steht in der Kette ÜBER dem Stratagem-Hinweis: die Karten sind ab
  dem Ziehen auf der Hand, also soll man sehen WAS man gezogen hat, bevor irgendetwas daraus zu
  entscheiden ist. Es gatet die KI an denselben drei Stellen wie sein Geschwister — im Test daran
  gepinnt, dass beide Zählungen GLEICH sind.
- **NUR EIN MODAL GLEICHZEITIG** (`main.py`s `_front_notice()`, `test_one_modal_at_a_time.py`).
  User: "Ich möchte keine gleichzeitigen Overlays. Das soll wieder nacheinander kommen: erst das
  Overlay, wer am Zug ist, und danach die Secondaries." Ursache war ein Auseinanderfallen von
  EINGABE- und ZEICHEN-Priorität: die Event-Kette ist ein `if/elif`, also besitzt genau EIN Overlay
  die Klicks — der Renderer zeichnete aber alle fünf bedingungslos übereinander. Die hinteren
  lugten unbeantwortbar hervor. Sichtbar wurde es erst durch das Missions-Overlay, weil Zug-Banner
  und Kartenzug BEIDE zu Beginn der Command-Phase feuern. `_front_notice()` ist jetzt die eine
  Definition der Reihenfolge (Zug-Banner → Turn-Plan → Missionen → Stratagem → WAAAGH!); gezeichnet
  wird nur das vorderste, und der Decision-Overlay wartet ebenfalls, weil er unter einem Notice
  ohnehin nicht anklickbar ist. Das `suppressed=`-Argument des Würfelpanels liest jetzt dieselbe
  Funktion, statt eine eigene handgepflegte Viererliste zu führen — die war schon veraltet, sie
  kannte das Missions-Overlay nicht. **A/B belegt:** Vor-Fix-Welt wiederhergestellt → 9 von 44
  Prüfungen fallen.
- **`_announce()` PUFFERT**, wenn das Overlay noch nicht existiert. Kein hypothetischer Fall: auf dem
  Legacy-Instant-Pfad (`PREGAME_DEPLOYMENT` aus) startet `main()` die Schlacht — und zieht damit
  Runde 1 — hunderte Zeilen bevor die UI gebaut ist. `flush_announcements()` läuft direkt nach dem
  Anhängen.
- **Ziehen ist IDEMPOTENT pro Schlachtrunde** (`_drawn_round`), weil `draw_at_command_phase()` von
  DREI Stellen erreichbar ist: beide Schlachtstart-Pfade und der Command-Phasen-Haken — und die
  allererste Command-Phase ist von zweien davon abgedeckt.
- **Der Stapel hält achtzehn Karten** (`ALL_CARDS`), der vom User gelieferte Satz vollständig:
  Centre Ground, Bring It Down, A Grievous Blow, Assassination, A Tempting Target, Beacon, Behind
  Enemy Lines, Burden of Trust, Cleanse, Defend Stronghold, Display of Might, Engage on All Fronts,
  Forward Position, No Prisoners, Outflank, Overwhelming Force, Plunder, Secure No Man's Land.
  Zwei je Runde, ohne Nachmischen — man sieht also höchstens zehn davon pro Schlacht. Eine neue
  Karte ist EIN Eintrag in `ALL_CARDS` plus ihr Prädikat; im Test sind die Schlüssel als Liste
  gepinnt, damit ein Zuwachs eine sichtbare Einzeiler-Änderung ist. **Die Decktests bauen sich
  eigene Karten**, statt gegen `ALL_CARDS` zu prüfen — die erste Fassung schrieb "der Zwei-Karten-
  Stapel ist jetzt leer" und wurde von der dritten Karte sofort ungültig (Fehlerklasse 17 im
  Kleinen).
- **A Grievous Blow zählt EINHEITEN, Bring It Down MODELLE** — die zwei Karten sehen fast gleich
  aus und hängen deshalb an ZWEI verschiedenen Haken desselben Todes-Sweeps:
  `record_destroyed_squad()` an `main.py`s eigenem `attached_units.unit_is_destroyed()`-Zweig,
  `record_destroyed_model()` pro entferntem Modell. "Unit destroyed" aus den Modellen neu
  abzuleiten wäre eine zweite Meinung zu einer Frage, die die Engine schon beantwortet (19.01
  merged den Leader ins Squad). Der Unit-Haken dedupliziert nach `id()`, weil der Sweep dasselbe
  geleerte Squad im selben Frame mehrfach erreicht.
  - **"Starting Strength" ist `starting_model_count`, NICHT die aktuelle Stärke**: ein auf zwei
    Modelle geschossener 21er-Blob ist beim Sterben immer noch eine 13+-Einheit. Bei einer Attached
    Unit wird der Wert aus den gemergten Komponenten neu abgeleitet — genau das lässt Guardian
    Defenders + Farseer + Warlock Conclave (14) überhaupt qualifizieren.
  - **Gemessen, welche Listen betroffen sind:** Aeldari 2 Einheiten, Orks 1, Necrons 1, **T'au
    KEINE**. Gegen T'au ist die Karte also ab dem Ziehen tot — und genau dafür hat sie ihre
    WHEN-DRAWN-Klausel. Als Testzeile an der echten Liste festgehalten, nicht als Literal.
- **Assassination hat ZWEI Zweige mit demselben Wert** (5 VP), also Alternativen statt Stufen: "ein
  oder mehr feindliche CHARACTER-Modelle diesen Zug zerstört" ODER "alle feindlichen
  CHARACTER-Modelle im Lauf der Schlacht zerstört". Der zweite ist die Nachzügler-Klausel für den
  Zug NACH dem letzten Kill.
  - **"Alle zerstört" ist NICHT "keiner auf dem Schlachtfeld".** Ein Charakter in Strategic Reserves
    ist vom Brett und quicklebendig. Deshalb bekommt der Controller eine ZWEITE Quelle,
    `set_squads_source(state.all_squads)` (Brett + Reserven + Transporte), getrennt von der
    Token-Quelle — die beiden beantworten verschiedene Fragen. **Gemessen:** mit dem letzten
    Charakter in Reserve zahlt die Karte 0; läse sie nur das Brett, zahlte sie fälschlich 5.
  - **Plus eine Nicht-Leerheits-Bedingung**: mindestens ein feindlicher Charakter muss wirklich
    gestorben sein, sonst erfüllt ein Gegner, der nie einen gefieldet hat, die Klausel jeden Zug
    vakuum-wahr.
  - **Die battle-lange Liste überlebt die Zuggrenze**, anders als alles andere in
    `_destroyed_*` — eigene Testzeile.
- **A Tempting Target ist die erste Karte mit GEDÄCHTNIS** — ihre WHEN-DRAWN-Klausel wählt ein
  Objective, und das bleibt für den Rest der Schlacht ihres. Zwei neue Bausteine dafür:
  - **Der Zustand liegt im CONTROLLER, nie auf der Karte** (`self.card_state`, nach Karten-Key,
    durchgereicht als `ctx.card_state`). Die `SecondaryMissionCard`-Objekte sind modulweite
    SINGLETONS, die jede Schlacht teilt — Zustand auf eine zu schreiben ist exakt die
    geteilte-Klassenattribut-Falle, die dieses Repo für `UnitProfile` schon dokumentiert.
    `achieved()` baut deshalb einen Kontext PRO KARTE statt einen für die ganze Hand.
  - **`on_draw` ist NICHT `when_drawn_may_redraw`**: das eine richtet die Karte ein, das andere ist
    die "abwerfen und neu ziehen"-Klausel. Zwei Haken, zwei Bedeutungen.
  - **`detail()` plus `detail_for()`**: die gedruckte Zeile sagt "your tempting target" und nie
    WELCHES — ohne die Detailzeile in Streifen und Zieh-Overlay ist die Karte unspielbar. Sie wird
    als eigener Block gerendert, nicht an den Text gehängt: `wrap_text()` trennt an LEERZEICHEN,
    ein eingebettetes `
` würde also gar keine neue Zeile beginnen.
  - **Die Wahl der KI ist deterministisch und vom User geliefert** ("eines der Objectives, die die
    KI kontrolliert. Wenn sie keins kontrolliert, dann das, was am weitesten weg von meiner
    Aufstellungszone ist") — also 0 API-Calls. Gleichstände brechen über den Namen, sonst flackerte
    das Ziel zwischen zwei gleich guten Objectives und die Karte wäre unspielbar.
  - **"No Man's Land" und "excl. home objectives" sind DIESELBE Menge**, geometrisch geprüft: ein
    Objective, dessen Mitte in KEINER Aufstellungszone liegt. Auf allen drei Karten fallen die
    beiden Formulierungen zusammen (Home-Objectives liegen immer in ihrer eigenen Zone), also wird
    nach Geometrie gefiltert und nicht nach dem String "Home" — im Test ist beides gegeneinander
    gepinnt, damit eine künftige Karte, die die Deckung bricht, hier auffällt.
  - Gemessen auf map2: drei No-Man's-Land-Objectives, Abstände zur P1-Zone 13.2" / 10.0" / 6.8" —
    ohne Kontrolle wird das ferne W gewählt, sobald die KI das nahe E hält, wird E gewählt.
- **Beacon ist die erste Karte mit EINEM EINZIGEN Zeitpunkt in der ganzen Schlacht.** Das gedruckte
  Badge `END OPP TURN · R5` hat der User ausgeschrieben als **"END OF OPPONENTS TURN - ROUND 5"**:
  also am Ende des GEGNERZUGES in der LETZTEN Schlachtrunde, einmal. Man pflanzt den Beacon früh und
  er muss am Schluss noch stehen. Dritter `TIMING_*`-Wert; `BATTLE_ROUNDS` wird aus
  `game/missions.py` gelesen statt die 5 erneut hinzuschreiben.
  - **Die Rundennummer MUSS von VOR `advance_phase()` kommen.** `begin_end_of_turn()` läuft danach,
    und wenn der ZWEITE Spieler einer Runde fertig ist, hat der Zähler schon hochgezählt — gemessen:
    Runde 5 endet, `turn_tracker.battle_round` steht auf **6**. Ein Kartentest "ist das Runde 5"
    sähe also nie seinen eigenen Moment. `main.py` reicht deshalb `battle_round_before` durch, und
    ein Quell-Wächter verlangt genau das.
  - **"Territory" ist die eigene Brett-HÄLFTE** (User: "Territory heißt einfach außerhalb meiner
    Spielfeldhälfte") — deutlich größer als die Aufstellungszone darin, was die 3-VP- von der
    5-VP-Stufe trennt. Welche Hälfte wem gehört, wird aus den Aufstellungszonen ABGELEITET (Achse,
    auf der die beiden sich trennen; alle drei Karten teilen auf y), nicht angenommen — im Test für
    BEIDE Spieler gespiegelt geprüft, sonst wäre die Ableitung eine hartkodierte Seite.
  - **"Outside" heißt: KEIN Modell der Einheit ist drin.** Gemessen mit einem einzelnen
    zurückgezogenen Modell: eins wieder in der Zone kostet die 3 VP, eins wieder in der eigenen
    Hälfte drückt 5 VP auf 3.
  - **"On the battlefield" trägt beide Stufen**: ein Beacon im Transporter oder zerstört zahlt 0.
    Geprüft wird das BRETT (`tokens`), nicht die All-Squads-Liste.
- **Die WHEN-DRAWN-Einrichtung gibt es in ZWEI Formen**, und der Unterschied ist, WER wählt:
  `on_draw` entscheidet selbst (A Tempting Target — der Gegner wählt, deterministisch nach
  User-Regel), `draw_choices` fragt den Menschen (Beacon — "Choose one friendly unit"). Beides ist
  von `when_drawn_may_redraw` getrennt, der "abwerfen und neu ziehen"-Klausel. Die interaktive Form
  läuft als ZWEITER Durchgang NACH den Redraw-Angeboten — sonst könnte eine Karte eingerichtet und
  danach weggetauscht werden, und die Wahl wäre verschenkt.
  - Beacons Kandidaten sind Brett-Einheiten PLUS eingestiegene (18.02), aber **nicht** die in
    Strategic Reserves — die nennt die Karte nicht. Dafür gibt es `set_embarked_source()`, weil
    weder die Token- noch die All-Squads-Quelle eingestiegen von reserviert unterscheiden kann.
- **Behind Enemy Lines misst "WHOLLY within"** mit 03.01s eigenem Test
  (`DeploymentZone.contains_circle`, die ganze BASE drin, nicht nur der Mittelpunkt) — nicht neu
  hergeleitet, die Aufstellung besitzt diese Definition schon. Gemessen: ein einziges
  zurückgelassenes Modell kostet die vollen 3 VP der Einheit, und ein Modell mit dem Mittelpunkt
  exakt auf der Zonenkante zählt ebenfalls nicht. 3 VP je Einheit mit Deckel 5 heißt: eine Einheit
  3, zwei oder mehr 5.
  - **Seine WHEN-DRAWN-Klausel ist die einzige, die nach der RUNDE fragt** statt nach der
    Feindarmee ("During the first battle round"), und die einzige, die die Karte **ZURÜCK IN DEN
    STAPEL MISCHT** statt sie abzuwerfen. Dafür gibt es `when_drawn_shuffles_back`.
  - **Die REIHENFOLGE im Redraw ist die Stolperstelle, und sie wurde gemessen:** wird die Karte
    erst zurückgemischt und dann gezogen, gibt ein kleiner Stapel sie sofort wieder aus — die
    Klausel wird zum No-op, der wie ein Fehler aussieht (im Selbsttest genau so passiert: Karte
    landete wieder auf der Hand). Jetzt wird ZUERST die Ersatzkarte gezogen, DANN die alte
    zurückgemischt; "draw a NEW Secondary Mission" ist genau das, was die andere Reihenfolge nicht
    garantiert.
- **Burden of Trust ist die erste Karte mit einem LAUFENDEN Zustand, der jede Runde neu gesetzt
  wird.** "WHEN DRAWN / START OF YOUR TURN" ist EIN Fenster mit zwei Auslösern, also teilen sie
  sich `_offer_guard_gate()`. Die Zuweisungen halten "until your next turn", das Fenster LÖSCHT
  also erst und bietet dann neu an.
  - **"Guarded" wird LIVE geprüft, es gibt keine zweite Buchführung**: die Einheit in Reichweite
    (`objectives.is_within_range_of_objective()`, dieselbe 3" wie 12.08) UND `controlled_by ==
    Spieler` (14.02). Ein Wächter, der wegläuft, stirbt oder dessen Objective gekippt wird, hört
    von selbst auf zu zählen. Alle drei Ausfälle einzeln gemessen.
  - **Ein Ja/Nein-Tor vor der Kette**, weil map2 fünf Objectives hat: fünf Fragen zu Beginn JEDES
    eigenen Zuges für eine "you may"-Klausel wären schlimmer als die Karte wert ist. Ablehnen ist
    eine legale Antwort und lässt alles unbewacht.
  - Die Kandidatenliste nennt zuerst die Einheiten **in Reichweite** (mit `(in range)`
    markiert) — eine Einheit, die nirgends in der Nähe steht, kann per Definition nicht bewachen.
  - **`start_of_turn()` läuft in `main.py` VOR `draw_at_command_phase()`**: in der Runde, in der
    die Karte gezogen wird, findet es sie noch nicht auf der Hand und tut nichts, sodass nur das
    Zieh-Fenster feuert. Sonst würde zweimal gefragt.
  - **Die Zuweisung läuft über einen BRETT-KLICK, nicht über eine Namensliste** (User: "Bei Burden
    of Trust muss immer links in der Spalte das Objective genannt werden, um das es gerade geht,
    und ich muss auf der Map mein Einheit anklicken"). `SecondaryMissionController.pending_pick`
    ist die eine offene Anfrage; sie trägt ihr `subject` — das Objective — weil genau das die
    Frage ausmacht.
    - **Der Klick MUSS vor dem generischen Board-Zweig gefangen werden**, sonst schluckt ihn die
      Kamera-Behandlung: Fehlerklasse 15, fünfmal im Repo verzeichnet. Der Zweig steht deshalb
      hinter den Notices/Decision/Würfeln und VOR jedem Controller-State-Zweig; ein Quell-Wächter
      prüft beide Seiten dieser Klammer. **A/B belegt:** Zweig entfernt → 7 Prüfungen fallen.
    - **Der Panel-Zweig steht als ERSTER im `_draw_dispatch`**, weil das Panel die einzige Stelle
      ist, die sagen kann, WELCHES Objective gerade dran ist — jeder Zweig davor könnte ihn
      verdecken, und dann wartet das Brett auf einen Klick, den niemand erklärt hat.
    - **Nur Einheiten IN REICHWEITE sind klickbar**, ein Klick auf etwas anderes wird ignoriert
      statt geraten. Und es werden nur noch Objectives gefragt, für die es überhaupt eine
      Einheit in Reichweite gibt — die Kette überspringt den Rest, statt fünfmal "kein Wächter"
      zu verlangen.
    - Die eligible Einheiten stehen zusätzlich als NAMEN im Panel: sonst sucht man sie auf dem
      Brett durch Ausprobieren.
- **Cleanse ist die erste Karte mit einer AKTION** (Regel 16.01, siehe den Abschnitt darüber). Ihre
  fünf Zeilen: STARTS in der eigenen Schussphase, UNITS eine Einheit in Reichweite eines Objectives
  **außer dem eigenen Home-Objective**, USE LIMIT unbegrenzt aber jede Einheit an einem ANDEREN
  Objective, COMPLETES am Zugende falls die Einheit das Objective kontrolliert, EFFECT das Objective
  ist gecleanst. 2 VP für eins, 5 VP für zwei oder mehr.
  - **"excl. your home objective" ist SINGULAR und POSSESSIV** — das Home-Objective des GEGNERS ist
    ein legales Ziel. Eigene Testzeile, weil "excl. home objectives" (A Tempting Target) daneben
    steht und das Gegenteil bedeutet.
  - **Das USE LIMIT ist eine Eindeutigkeitsregel am ZIEL, keine Obergrenze für die Anzahl.** Die
    Kandidatenkette wird deshalb bei JEDEM Schritt neu abgeleitet statt vorab eingesammelt: einer
    Einheit ein Objective anzubieten, das gerade vergeben wurde, wäre sonst der Normalfall.
  - **EFFECT hat bewusst KEINEN Callback.** Vollenden IST der Effekt: `resolve_end_of_turn()` gibt
    die vollendeten States zurück, und die darin genannten Objectives sind genau die gecleansten.
    Eine Liste, in die ein Effekt hineinschreibt, wäre eine zweite Aufzeichnung derselben Tatsache.
  - **Die WHEN-DRAWN-Klausel nennt "Plunder"** — eine Karte, die dieser Stapel nicht enthält, also
    ein belegter No-op. Ausgeschrieben statt weggelassen, damit Plunder später eine
    Einzeiler-Änderung ist; im Test ist gepinnt, dass keine Karte diesen Schlüssel trägt.
- **Defend Stronghold ist die erste Karte mit einer VERPFLICHTENDEN WHEN-DRAWN-Klausel.** Ihr Text
  lautet "During the first battle round, **shuffle** this card back" — **ohne "you may"**, das
  Behind Enemy Lines in genau demselben Satz hat. Die eine ist ein Angebot, die andere eine
  Anweisung: `when_drawn_is_mandatory` löst sie ohne Prompt auf. Der Unterschied steht als eigene
  Testzeile für BEIDE Karten da, weil ein flüchtiger Vergleich sie für identisch hält.
  - **"no enemy units are WITHIN your deployment zone"** — nicht "wholly within". Ein Feindmodell,
    das die Zone nur BERÜHRT, kostet schon die 5 VP und lässt 3 übrig. Das ist die umgekehrte
    Strenge zu Behind Enemy Lines' "wholly within", darum sind es zwei verschiedene Tests; im Test
    mit einer Base gemessen, die genau auf der Zonenkante steht.
  - **"2ND ROUND ONWARD"** ist als `min_battle_round` modelliert und in `scores_at()` geprüft. Bei
    dieser Karte kann es nie greifen (sie punktet ohnehin nur in Runde 5), es ist trotzdem
    ausgeschrieben statt weggelassen.
  - Das eigene Home-Objective wird geometrisch gefunden (`own_home_objective()`), und der Test
    prüft die Gegenrichtung mit: für Player 2 ist es das ANDERE.
- **Display of Might ist die erste Karte, deren WERT vom ZEITPUNKT abhängt statt vom Erfüllungsgrad**
  — dieselbe Bedingung, 2 VP am Ende des eigenen Zuges, 5 VP am Ende des gegnerischen. Das Halten
  des Niemandslands durch den Feindzug ist die schwerere Hälfte, und genau das ist das Design der
  Karte. `score()` liest dafür `ctx.ending_player`; `scores_at()` bleibt "Ende EINES Zuges".
  - **"wholly within No Man's Land"** = jede Base ganz außerhalb BEIDER Aufstellungszonen
    (`zone_distance() > radius`). Beide Zonen einzeln getestet — ein Modell zurück in der EIGENEN
    Zone zählt genauso wenig wie eins in der gegnerischen.
  - **Die Klammer "(excl. AIRCRAFT & battle-shocked)" steht gedruckt hinter "enemy units", wird
    aber auf BEIDE Seiten angewandt** — sie liest sich als Qualifier darauf, was für diese Karte
    als Einheit zählt, und es ist die STRENGERE Lesart, kann also keine VP verschenken, die die
    Karte nicht meinte. Als Entscheidung im Modul ausgeschrieben.
  - **"MORE friendly than enemy" — gleich ist nicht mehr.** 1:1 zahlt nichts, 2:1 schon.
- **Engage on All Fronts bringt TISCHVIERTEL** (`table_quarters()`): das Brett an der Mitte auf
  BEIDEN Achsen geteilt — die schlichte Lesart von "table quarter" und die einzige, die auf allen
  drei Brettern (44×60, 60×44, 30×30) ohne Sonderfall funktioniert. Sie werden aus `config` zur
  LAUFZEIT gebildet, ein Hochformat-Brett bekommt also andere; als Testzeile festgehalten.
  - **Die 6"-Mittenklausel ist das, was die Karte schwer macht**: eine Einheit kann ganz in einem
    Viertel stehen und trotzdem keine Presence geben, wenn sie zu nah an der Brettmitte steht.
    Auf beiden Seiten der Linie im GLEICHEN Viertel gemessen, damit nur die Distanz den
    Unterschied macht.
  - "Wholly within it" wird per Base geprüft: eine Einheit auf einer Mittellinie zählt für KEIN
    Viertel, nicht für eines von beiden.
  - **Gegnerische Einheiten sind irrelevant** — die Karte fragt nur nach den eigenen. Eigene
    Testzeile, weil die Nachbarkarte (Display of Might) genau das Gegenteil tut.
  - **Die Karte druckt KEINEN Zeitpunkt** — in dem Feld, in dem jede andere Karte ihren Moment
    trägt, steht hier FIXED bzw. TACTICAL. Vom User bestätigt: "engage on all fronts triggered am
    Ende des Zuges", also derselbe Ende-des-eigenen-Zuges-Moment wie bei jeder anderen
    Brettzustands-Karte dieses Stapels.
- **Forward Position** zahlt 5 VP für das Home-Objective des GEGNERS **und/oder** jedes
  Expansion-Objective. "and/or" macht die beiden zu Alternativen, nicht zu einer Summe: eines
  allein zahlt die eine 5-VP-Box. "EACH expansion objective" ist ALLE — genau das verhindert, dass
  die Karte auf einem Brett mit zweien trivial wird.
  - **"Expansion objective" ist eine User-Definition** ("das Objektiv, was an meiner
    Aufstellungszone am nächsten ist, außer natürlich das Home-Objektiv"): das der eigenen Zone
    NÄCHSTE Objective, Home ausgenommen — also EINES pro Spieler, und "each expansion objective"
    meint das Paar. Home wird geometrisch ausgeschlossen (es läge in der eigenen Zone, Abstand 0,
    und gewänne immer), deshalb liefert `no_mans_land_objectives()` die Kandidaten.
  - **Gemessen, und auf beiden großen Karten symmetrisch:** map1 P1→Southwest / P2→Northeast (je
    4.2"), map2 P1→East / P2→West (je 6.8") — das Central liegt auf beiden Brettern weiter weg
    (12.0" bzw. 10.0") und ist deshalb nie Expansion. Der Test prüft nicht nur WELCHES, sondern
    dass jedes andere Objective wirklich weiter weg ist.
  - **map3 hat nur EIN Nicht-Home-Objective**, also ist für beide Spieler dasselbe das nächste und
    die Menge fällt auf einen Eintrag zusammen — `expansion_objectives()` dedupliziert deshalb,
    sonst verlangte "each expansion objective" dasselbe Objective zweimal.
- **WITHIN gegen WHOLLY WITHIN ist die Falle dieses Kartensatzes** (User-Warnung: "Within: da
  reicht, wenn ich nur den kleinen Zeh mit einem Modell reinhalte. Wholly within dagegen muss die
  Einheit wirklich vollständig drin sein"). Beide Formen kommen vor, oft auf benachbarten Karten,
  und eine verwechselte Lesart besteht JEDEN Test, der eine Einheit klar drinnen oder klar draußen
  stellt. Deshalb prüft `test_secondary_missions.py`s Abschnitt 3m jede räumliche Klausel am
  GRENZFALL — eine Einheit mit einem Modell auf der einen und dem Rest auf der anderen Seite:
  - **WITHIN (ein Modell reicht):** Centre Ground (3"/6" zur Mitte), Defend Stronghold (Feind in
    meiner Zone), Outflank (6" zur Brettkante), Burden of Trust und Cleanse (Objective-Reichweite).
  - **WHOLLY WITHIN (ein Modell draußen kippt alles):** Behind Enemy Lines (Feindzone), Display of
    Might (Niemandsland), Engage on All Fronts (Tischviertel).
  - **NOT WITHIN / OUTSIDE ist der Spiegel von WITHIN**, nicht von WHOLLY WITHIN: ein Modell drin
    kippt es. Betrifft Beacon (eigene Hälfte/Zone), Engage (6" zur Mitte) und Outflanks
    "not within your territory".
- **Outflank ist die erste Karte, deren höhere Stufe eine SCHWÄCHERE Bedingung an die einzelne
  Einheit stellt.** 3 VP verlangen, dass DIE Einheit außerhalb der eigenen Hälfte steht; 5 VP
  verlangen zwei Einheiten an gegenüberliegenden Kanten, aber nur EINE davon muss draußen sein. Die
  reichere Stufe ist also nicht die ärmere zweimal — eine in der eigenen Hälfte festhängende
  Einheit kann Hälfte der 5-VP-Stufe sein, obwohl sie allein nichts zahlt. Eigene Testzeile, weil
  ein "beide müssen raus" hier naheliegt und falsch wäre.
  - "Opposite edges are the ones that run parallel to each other" steht auf der Karte, also sind
    die Paare (Nord, Süd) und (West, Ost); benachbarte Kanten und zwei Einheiten an DERSELBEN Kante
    zahlen nur die 3 VP.
- **No Prisoners ist A Grievous Blow ohne den Starting-Strength-Filter** — 2 VP je zerstörter
  Feindeinheit, Deckel 5 (drei Einheiten zahlen 5, nicht 6). Wird aus demselben Pro-EINHEIT-Haken
  gefüttert.
- **Overwhelming Force braucht einen SNAPSHOT ZUM ZUGBEGINN.** "each enemy unit that STARTED THE
  TURN within range of one or more objectives and is destroyed" — das ist eine Tatsache über einen
  Moment, der beim Punkten vorbei ist, und über Einheiten, die es dann nicht mehr gibt. Weder vom
  Brett ablesbar noch nachträglich rekonstruierbar. `snapshot_turn_start()` läuft deshalb zu
  Beginn JEDES Zuges (auch des gegnerischen — die Karte punktet am Ende EINES Zuges) und merkt
  sich `id(squad)` jeder Feindeinheit in Objective-Reichweite. Billig und bedingungslos: ob die
  Karte nächste Runde gezogen wird, ist jetzt nicht bekannt.
- **Plunder ist die erste Aktion mit "COMPLETES: Immediately"** — sie ist in dem Moment fertig, in
  dem sie beginnt. Dafür bekam `ActionDefinition` ein `completes_immediately` und `ActionState` ein
  `completed`; `resolve_end_of_turn()` meldet sofort abgeschlossene Aktionen mit, damit jeder
  Konsument EINE Liste liest.
  - **16.01s Bewegungs-Abbruch erreicht sie nicht mehr** (sie ist ja fertig), **die zwei Sperren
    aber schon** — die hängen am STARTEN, nicht am Vollenden. Beides einzeln gemessen: nach einer
    Bewegung ist `broken=True` UND `completed=True`, und sie zählt am Zugende trotzdem.
  - **"One unit within a terrain area not within your territory"** — der Zusatz hängt an der
    TERRAIN AREA, nicht an der Einheit: man plündert fremden Boden. Gemessen an der Mitte der Area,
    wie ein Objective als Home klassifiziert wird. Auf map2 sind 7 der 15 Areas plünderbar.
  - **USE LIMIT "once per turn"** — EINE Plunder-Aktion pro Zug, nicht eine je Einheit. Gegensatz
    zu Cleanse, dessen Limit "unbegrenzt, aber je Einheit ein ANDERES Objective" ist; beide
    Lesarten stehen im Test nebeneinander.
  - **Cleanses "If you have Plunder active"-Klausel ist damit scharf** — sie war ein belegter
    No-op, und der Pin in `test_actions.py` war ausdrücklich dafür gesetzt, dass das Hinzufügen von
    Plunder eine SICHTBARE Änderung wird. Genau das ist passiert: die Zeile wurde rot und ist jetzt
    umgedreht. Beide Karten drucken die Klausel spiegelbildlich, eine Hand muss also nie beide
    Objective-Action-Karten tragen.
- **Secure No Man's Land** ist die einfachste Karte des Satzes: zwei oder mehr
  No-Man's-Land-Objectives kontrolliert → 5 VP. Das gedruckte "(excl. your home objective)" ist
  doppelt gemoppelt — ein Home-Objective liegt in einer Aufstellungszone und ist damit nie in No
  Man's Land; `no_mans_land_objectives()` schließt es ohnehin geometrisch aus.
- **Bring It Down zählt MODELLE, nicht Einheiten**, und wird deshalb aus dem Pro-Modell-Todes-Sweep
  gefüttert (`record_destroyed_model()`), nicht aus `record_destroyed_squad()`: ein Squadron, das zwei
  von drei Rümpfen verliert, punktet zweimal, während seine EINHEIT weiterlebt und der
  Squad-Haken nie feuert. Und es punktet am Ende **EINES** Zuges (auch dem der KI) — Centre Ground
  dagegen nur am Ende des EIGENEN. Der gedruckte Unterschied ("end of a turn" gegen "end of your
  turn") ist als `TIMING_*` modelliert und einzeln getestet.
- **Centre Ground hat DREI Ausgänge, nicht zwei.** 5 VP braucht die Mitte bis 6" frei, 3 VP nur bis
  3". Die mittlere Bande ist die, die man beim Testen verliert; gemessen mit einem Feind 4.44" von der
  Mitte (innerhalb 6", außerhalb 3"). "excl. AIRCRAFT" ist ein belegter **No-op** — dieses Keyword
  gibt es hier nicht, dieselbe Ausnahme, die `rapid_ingress.py` schon dokumentiert.
- **Die VP-Beträge werden EAGER berechnet**, bevor irgendetwas gefragt wird: die Prompts lösen sich
  asynchron auf (der Zug ist zu dem Zeitpunkt längst umgeschlagen, genau wie bei
  `starflare_controller.offer()` an derselben Stelle), das Brett, gegen das gemessen wurde, darf also
  nicht später neu gelesen werden. Deshalb kann `_destroyed_this_turn` sofort geleert werden.
- **Die fünf Headless-Harnesses setzen den Flag auf `()`** — der Stapel fragt den Menschen am Ende
  JEDES seiner Züge etwas, und keiner von ihnen beantwortet außerhalb des Vorspiels einen
  Mensch-Prompt (dokumentierte Grenze). **Belegt statt vermutet:** mit eingeschaltetem Flag zieht
  `selfplay.py map2` die zwei Karten korrekt und bleibt danach in Player 2s Zug stehen, weil
  `_is_blocked()` auf dem offenen Prompt hält. Quell-Wächter verlangt es von allen fünf.
- **`ai/planner_prompt.py` sagt der KI jetzt, dass die Secondary des GEGNERS eine andere ist** und
  nicht vom Brett ablesbar. Ihre eigene Beschreibung stimmt unverändert.
- **Bewusst offen:** ACTIONS gibt es in dieser Engine überhaupt nicht (siehe `fall_back.py`), und
  keine der zwei Karten braucht eine — `SecondaryMissionCard.requires_action` ist der benannte Haken,
  mehr nicht (kein spekulatives System). `scene_io` sichert weiterhin keine VP, also auch weder Hand
  noch Stapel. Kein KI-Pfad: die KI behält ihre Standard-Missionen.
- **Getestet:** neu `test_secondary_missions.py` (**537/537**), `test_mission_cards_ui.py`
  (**54/54**, gegen eine echte Surface gemessen statt gegen Konstanten) und
  `test_one_modal_at_a_time.py` (**44/44**, Quell-Wächter). Neu `test_actions.py` (**79/79**) und `test_mission_unit_pick.py` (**60/60**). Volle
  Regression **112 Suiten, ~7426 Prüfungen, 111 grün / 0 rot / 1 bekannt**, dazu alle vier Smokes und `selfplay.py map2` 2000
  Frames (0 API-Calls). Vorher gab es zu Missionen **gar keinen Test**.

## Fraktionen

`game/factions/` (Datasheet/Detachment/Faction + `build_squad()`) ist das generische Gerüst.

- **T'au Empire** — Strike Team, Breacher Team, Kroot Carnivores, Stealth Battlesuits, Ghostkeel,
  Devilfish, Crisis Starscythe, Crisis Sunforge, Riptide, Pathfinder Team, The Twin Lance, Commander
  Farsight, Commander in Coldstar, Cadre Fireblade. Armeeregel "For The Greater Good", Detachment
  "Retaliation Cadre" (Bonded Heroes + 6 Stratagems). Komplette Punkteliste (43 Einträge).
- **Orks** — Boyz (10/20), Warbikers, Stormboyz, Trukk, Gretchin, Battlewagon, Kill Rig, Deff Dread,
  Deffkoptas, Flash Gitz, Tankbustas, Meganobz, Beast Snagga Boyz, Beastboss, Warboss (Fuß + Mega
  Armour), Painboy. Armeeregel Waaagh!, Detachment "War Horde" (Get Stuck In + Stratagems). Komplette
  Punkteliste (58 Einträge).
- **Aeldari** — Guardian Defenders, Storm Guardians, Striking Scorpions, Howling Banshees, Warp
  Spiders, Dire Avengers, Fire Dragons, Dark Reapers, Shining Spears, Windriders, Warlock Skyrunners,
  Rangers, Shroud Runners, Swooping Hawks, Wraithguard, Falcon, Warlock Conclave, Farseer, Eldrad
  Ulthran, Avatar of Khaine, Asurmen, Jain Zar, Lhykhis, Baharroth. Armeeregel **Battle Focus**
  (eigenes Token-Konto, 6 Agile Manoeuvres), Detachment **Seer Council** (Strands of Fate + 6
  Stratagems). Punkteliste bewusst NUR für gebaute Einheiten (ein KeyError heißt "noch nicht
  transkribiert", nicht "kostenlos").

- **Necrons** — Necron Warriors, Immortals, Lychguard, Skorpekh Destroyers, Lokhust Destroyers,
  Lokhust Heavy Destroyers, Canoptek Wraiths, Doomsday Ark, Overlord, Plasmancer, Technomancer,
  Illuminor Szeras, C'tan Shard of the Void Dragon. Armeeregel **Reanimation Protocols**
  (`game/reanimation_protocols.py`), Detachment **Awakened Dynasty** (Command Protocols + alle
  sechs Stratagems; die vier Enhancements bleiben reine Daten).
  Punkteliste bewusst NUR für gebaute Einheiten. **Die erste Fraktion, die die KI spielen soll und
  die nicht Player 2s Default ist** — umschaltbar über `config.PLAYER2_ARMY` / `--army2 necrons`.

  - **Reanimation Protocols ist die erste Mechanik, die MEHRERE Modelle in ein stehendes Squad
    zurückholt.** Der Datenblatt-Text ("heals D3 wounds") ist nur die Hälfte; die eigentliche
    Mechanik steht in den KERNREGELN und wurde von dort transkribiert: **02.02.04** (pro Wunde erst
    ein beschädigtes Modell heilen; erst wenn ALLE voll sind, ein zerstörtes wiederbeleben — mit
    **einer** Wunde, **CHARACTER-Modelle ausgenommen**) und **01.02.03** (nie über
    `starting_model_count`; Platzierung in Kohärenz mit den Modellen, die die Phase auf dem Brett
    begonnen haben; engaged nur gegen Feinde, die ohnehin schon engaged waren). **Der
    CHARACTER-Ausschluss ist der Grund, warum es das Stratagem "Protocol of the Eternal Revenant"
    überhaupt gibt.**
  - **Der Controller ist eine WARTESCHLANGE**, nicht ein Pending-Slot wie bei Grot Orderly: die
    Regel betrifft JEDE Einheit JEDE Command-Phase. Nach User-Entscheidung bekommt **jede Einheit
    ihren eigenen beschrifteten Wurf** — aber **nur Einheiten, die schon Schaden erlitten haben**
    (`UNITS_MUST_HAVE_SOMETHING_TO_GAIN`, User nach dem Spieltest: "nur triggern, wenn die Einheit
    auch schon Schaden erlitten hat. Jetzt feuert das jedes Mal auch am Anfang"). Das ändert KEIN
    Ergebnis, nur was bestätigt werden muss: `recoverable_wounds()` ist genau dann 0, wenn nichts
    fehlt und nichts zerstört ist, und `reanimate()` gibt in diesem Zustand `(0, [])` zurück — der
    übersprungene Wurf ist also exakt der Wurf, der nichts bewirkt hätte. Gemessen: im
    Selbstspiellauf 12 Würfelfenster pro Command-Phase vorher, 0 auf einer unversehrten Armee
    nachher, und weiterhin genau eines für eine Einheit, die ein Modell verloren hat.
  - **`recoverable_wounds(squad)` ist das GEMEINSAME Gate** von Resurrection Orb, Undying Legions
    und jedem deterministischen KI-Urteil — eine Frage, eine Antwort.
  - **Elfte Extraktion: `game/model_return.py`.** Grot Orderly und Fuegan trugen dieselbe
    vierteilige "zurück auf dem Brett"-Sequenz doppelt (Tokenliste, Squad, von `destroyed_models`
    herunter, Wunden), und der Engagement-Test steckte nur in Fuegans Datei — obwohl
    `SetupController.position_valid()` ihn laut eigenem Docstring NICHT abdeckt. Neu gegenüber
    beiden Vorlagen ist `wounds=`: beide setzten hart auf volle Wunden, Reanimation braucht 1.
    Verhaltensneutralität belegt durch unverändert grüne `test_painboy.py`/`test_fuegan.py`.
  - **`Gear` kann jetzt eine ganze Modellzeile bekleiden** (`all_models=True`). Vorher traf ein
    Gear-Item hart nur `line_tokens[0]` — bei den Lychguard hätten vier von fünf Modellen still
    keinen Rettungswurf gehabt. Additiv, Default unverändert, kein bestehendes Datenblatt betroffen.
  - **`DamageAllocationSession._molten()` heißt jetzt `_reduced_damage()`** — mit Necrodermis und
    Implacable Resilience kam der zweite Träger, und ein nach der ersten Fähigkeit benannter
    Trichter ist genau der lügende Name, den dieses Repo umbenennt statt kopiert. Reihenfolge:
    halbieren VOR subtrahieren (Kernregel-Konvention), Untergrenze 1, Mortal Wounds ausgenommen.
  - **`game/reroll_scope.py` benennt eine ZWEITE Reroll-Form.** Beide Angriffsschritte entschieden
    sie vorher mit einem hartkodierten `reason == swift_demise.SWIFT_DEMISE_LABEL`, weil die
    Windriders der einzige Träger waren; die Necrons bringen drei weitere. **Genau die Fehlerform
    der Fade-Back/Path-of-the-Outcast-Meldung** (ein Einzelwert an einer Stelle, an der es eine
    MENGE ist). Die Form ist "die 1en ODER der ganze Wurf, nie nur die Fehlschläge" — "instead"
    macht die beiden zu Alternativen, und mit 1en auf dem Tisch ist "Keep result" keine legale
    Antwort. **`game/fight.py` hatte gar keinen automatischen 1er-Reroll** und hat ihn jetzt
    (`_begin_ones_reroll` + zwei Pending-Steps), gespiegelt von `game/shooting.py`.
  - **Guardian Protocols ist mechanisch der Wave Serpent Shield** (S > T → −1 auf den Wundwurf) und
    teilt sich deshalb `_wound_modifiers(target_squad, strength=)`. Zwei Unterschiede, beide
    gedruckt: "an attack" statt "a ranged attack" (also AUCH `fight.py`), und das
    NOBLE-Leader-Gate über `attached_units.leader_ability()`.
  - **Szeras' Mechanical Augmentation ist die erste Aura, deren REICHWEITE über die Schlacht
    wächst** (3" → max 12", +3" je Fight-Phase mit einem Kill). Der Zuwachs liegt am TOKEN, nie am
    Profil — `UnitProfile`-Subklassen sind geteilte Klassenobjekte. Kill-Attribution gibt es in
    dieser Engine nicht; sie ist hier auch nicht nötig, weil Szeras keine LEADER-Zeile hat und
    seine Einheit deshalb immer genau er ist. **Beide Hälften der Aura liegen in der
    `_adjusted_weapon()`-Kette**, weil der Rettungswurf die AP von genau dieser Waffe liest.
  - **Zwei Namensfallen im Waffenblock**, beide vom Rezept vorhergesagt: `Staff of Light` trägt auf
    Overlord und Technomancer verschiedene Zahlen (BS/WS 2+ gegen 4+, A4 gegen A2 im Nahkampf), und
    `Close Combat Weapon` kommt in zwei verschiedenen Ausprägungen. Im Test **gegeneinander**
    gepinnt, nicht gegen Literale — die Zusicherung ist, dass sie VERSCHIEDEN sind.
  - **Die Lychguard-Kopplung erzwingt sich selbst**: das Dispersion Shield lehnt ab, wenn das Modell
    das Hyperphase Sword nicht genommen hat, weil Gear NACH den Waffentäuschen läuft. Beim
    Resurrection Orb genauso mit dem Tachyon Arrow. Dieselbe Mechanik wie beim bedingten
    Shimmershield der Dire Avengers.
  - **Punkte: 10 von 13 Einträgen weichen von der User-Liste ab, in BEIDE Richtungen** (Engine 2000,
    Liste 2005). Zweite unabhängige Widerlegung von "die App rundet auf". Transkription gewinnt,
    Abweichung benannt.
  - **Bewusst offen:** die "for every 3 models"-Ratio des Plasmacyte ist eine LISTENBAU-Grenze und
    wird vom Scaffold nicht erzwungen (es gibt keinen Armeebau-Schritt); "cannot be your WARLORD"
    ist ein belegter No-op; die fünf Charaktere stehen ALLEIN, weil die Liste keine Anbindungen
    nennt und Raten still ändern würde, worauf Command Protocols wirkt; **Sprites und Fraktionslogo sind da** (13 Datenblätter,
    alle geprüft), siehe den Sprite-Absatz unten.
  - **Getestet:** `test_reanimation_protocols.py` (**46/46**, inkl. A/B an der Quelle und einer
    Gegenprobe, die den CHARACTER-Filter entfernt und die Suite rot macht),
    `test_necron_datasheets.py` (**144/144**), `test_necron_abilities.py` (**99/99**),
    `test_player2_necron_army.py` (**51/51** — die Totals als die Rechnung der LISTE ausgeschrieben,
    was sofort einen eigenen Zählfehler gefangen hat). Volle Regression **97 Suiten, ~5839
    Prüfungen, 96 grün / 0 rot / 1 bekannt**, dazu `smoke_pregame.py`, `smoke_log_input.py` und
    `selfplay.py` auf map2 für **beide** Armee-Varianten.
  - **Etappe 2 — Awakened Dynasty ist gebaut**: die Detachment-Regel **Command Protocols**
    (`game/awakened_dynasty.py`) und alle sechs Protokolle (`game/protocol_*.py`). Die vier
    Enhancements bleiben reine Daten (Enhancements sind im Repo kein System).
    - **`game/awakened_dynasty.py` hält die geteilten Prädikate**, nicht nur die Regel: alle sechs
      Stratagems beginnen mit "One NECRONS unit from your army", und **fünf** haben zusätzlich die
      Klausel "if a NECRONS CHARACTER is leading your unit". Sechs Kopien davon wären genau die
      Drift, die dieses Repo laufend konsolidiert — und die Leader-Hälfte ist die, die man leicht
      falsch macht (`leader_ability()` statt `unit_wide_ability()`). `is_led_by_character(squad)`
      ist schlicht `leader_ability(squad, "character")`.
    - **Wer das Detachment hat, steht in `config.AWAKENED_DYNASTY_PLAYERS`** — ableitbar ist es
      nicht, denn ein Detachment ist eine Listenbau-Erklärung und eine Necron-Einheit sieht in jedem
      Detachment gleich aus. Dieselbe Begründung wie bei `SEER_COUNCIL_PLAYERS`.
    - **Command Protocols' Vorzeichen ist NEGATIV**, wie jeder Bonus hier: `game/modifiers.py`
      justiert die SCHWELLE, und "add 1 to the Hit roll" macht sie leichter. Verkehrt herum wäre es
      ein armeeweiter Dauermalus gewesen. Wirkt in BEIDEN Phasen ("an attack", nicht "a ranged
      attack"), und liegt in `shooting.py` VOR den beiden Ignore-Modifier-Filtern, damit das per
      Konstruktion so bleibt.
    - **`start_reactive_shooting()` ist neu in `game/shooting.py`** und nicht `start_snap_shooting()`:
      Vengeful Stars sagt "shoot as if it were your Shooting phase", also die GEWÖHNLICHE
      Aktivierung, während Snap Shooting (15.09) der bewusst schwächere Modus ist. Es trägt
      `restrict_to` für "it must target only that enemy unit", erzwungen in
      `_is_valid_target_squad()` — der EINEN Stelle, die entscheidet, worauf geschossen werden darf,
      damit keine zweite Filterung driften kann. `_restrict_targets_to` wird an jedem
      Aktivierungsende geleert (auch bei `cancel()`, das über `_finish_activation()` läuft).
    - **Vengeful Stars misst die 6" im MOMENT DES TODES**, nicht bei der Auflösung — "was within 6"
      of that unit WHEN IT WAS DESTROYED". Wenn das Stratagem angeboten wird, stehen die Modelle
      der toten Einheit längst nicht mehr auf dem Brett. Falsch herum gebaut wäre die Bedingung
      unmessbar, und das zeigt sich nur als "der Knopf erscheint nie".
    - **Undying Legions ist fast nur ein Aufruf von `reanimate()`** — die Stratagem-Datei
      wiederholt nichts von Heilen/Wiederbeleben/Platzierung. Das "+1" bei Leader-Führung liegt auf
      dem WÜRFELERGEBNIS, nicht auf einem anderen Würfel: "D3+1" ist ein D3 plus 1, kein D4. Und es
      setzt **`allow_repeat_target=True`**, weil jede feindliche Einheit ihr eigenes "just after
      that unit resolved its attacks"-Fenster hat — 15.01s einmal-pro-Ziel-pro-Phase wäre hier
      falsch. Es hängt an den NACH-Auflösungs-Haken, nicht an `target_reactions` (die feuern bei
      "just after it has SELECTED its targets" — ein anderer Moment).
    - **Eternal Revenant ist strukturell Fuegans Unquenchable Resolve** (Sweep-Notiz +
      Phasengrenze + `ring_candidates()` + der Engagement-Test) und unterscheidet sich nur dort, wo
      der gedruckte Text es tut: **halbe** Startwunden statt volle (genau das `wounds=`-Argument,
      das `model_return.set_up_model()` dafür bekam), und "its unit has a starting strength of 1" —
      er kehrt NICHT in seine alte Einheit zurück, wo Fuegan genau das tut. Beide Module schreiben
      diesen Unterschied aus.
    - **Sudden Storm hat ZWEI Uhren**, und das ist gedruckt: [ASSAULT] bis zum Ende des ZUGES, der
      Advance-Reroll nur bis zum Ende der PHASE. Zwei Flags, jedes nach seiner Lebensdauer benannt,
      damit niemand sie an einer Stelle zusammen löscht.
    - **Conquering Tyrant trägt sich in `game/reroll_scope.py` ein** — dieselbe
      "1en ODER ganzer Wurf"-Form. Seine Bedingung ist als einzige eine DISTANZ (Halbdistanz), und
      sie wird so gemessen, wie [RAPID FIRE X] und [MELTA X] es schon tun (`pairs` × Zielmodelle,
      Halbdistanz über `game/weapon_range.py`), statt ein zweites Mal.
    - **KI-Pfade sind für die drei reaktiven schon da** (`auto_players`, Muster `'Ard as Nails`):
      Undying Legions ab `recoverable_wounds ≥ 2`, Eternal Revenant immer (ein Charakter ist 1 CP
      wert), Vengeful Stars nur bei positivem `damage_value`. Sudden Storms Advance-Reroll ist
      ebenfalls deterministisch (unter 4 neu werfen — ein D6 mittelt 3.5). Die drei PROAKTIVEN
      (Hungry Void, Sudden Storm, Conquering Tyrant) bekamen ihren KI-Pfad in Etappe 3, siehe unten.
    - **Eine tote Verdrahtung gefunden und geschlossen, genau der Klasse, für die
      `verify_mark_wiring.py` existiert:** `VengefulStarsController.notify_unit_destroyed()` war
      gebaut, unit-getestet und wurde von NIRGENDS in `main.py` aufgerufen — das Stratagem hätte im
      echten Spiel nie feuern können, weil seine Kandidaten nie erfasst wurden. Ein Controller, der
      konstruiert, aber nie GEFÜTTERT wird, ist für jeden Test unsichtbar, der ihn direkt treibt.
      Jetzt aus dem Todes-Sweep gefüttert (einmal pro ausgelöschtem Squad, nicht pro Leiche), und
      `test_awakened_dynasty.py`s Abschnitt 10 prüft für alle sechs Protokolle, dass ihre
      Fütterungs- und Ablauf-Aufrufe wirklich in `main.py` stehen. **A/B belegt:** den einen Aufruf
      entfernt, und genau diese Prüfung wird rot.
      Nebenbefund dabei: die 6" müssen gegen `destroyed_models` gemessen werden, nicht gegen
      `models` — beim Sweep ist `models` schon leer, aber die Koordinaten der Tokens überleben
      (dieselbe Eigenschaft, auf der Reanimation Protocols beruht).
    - **Getestet:** `test_awakened_dynasty.py` (**82/82**) — die Prädikate, Command Protocols in
      beiden Trefferschritten samt A/B an der Quelle, jedes Stratagem an seiner WHEN/TARGET-Grenze
      (falsche Phase, zweiter Kauf, fehlender Leader), Sudden Storms zwei Uhren einzeln, und die
      15.01-Buchführung mit einem echten CP-Konto, plus die Verdrahtungssonde. Volle Regression
      **98 Suiten, ~5921 Prüfungen, 97 grün / 0 rot / 1 bekannt**, dazu alle sechs Smokes (beide Armeen).
  - **Sprites, Fraktionslogo und die drei Anbindungen** (User: "Sprites und Logo sind da / Overlord
    in die Lychguard / Technomancer in die Warriors / Plasmancer in die immortals").
    - **Die dreizehn "kein Sprite"-Pins sind umgedreht** — genau der Zweck, zu dem sie gesetzt
      wurden. Sie prüfen jetzt das Gegenteil, und zwar **am MODELL statt an der Tabelle**: ein
      Schlüssel, der auf keine Datei auf der Platte auflöst, ist genau der Fehler, den ein Blick in
      die Map nicht sieht. `NECRONS` ist die vierte Zeile in `FACTION_LOGO_KEYS`.
    - **Der Ordner gewinnt an ACHT Stellen**, dieselbe Entscheidung, die `Warpspider`, `JainZar`,
      `Eldrad Ultran` und `Warlock Sky Runner` schon festhalten: fünf Dateien sind SINGULAR, wo das
      Datenblatt plural ist (`Necron Warrior`, `Necron Immortal`, `Necron Wraith`), drei benennen
      das MODELL statt der Einheit (`Necron Destroyer` für Lokhust Destroyers, `Necron Heavy
      Destroyer` für Lokhust Heavy Destroyers, `Necron Shard of the Void Dragon`), und
      `Necron IlluminorSzeras` hat kein Leerzeichen. Alle acht sind einzeln als Testzeile
      ausgeschrieben, damit ein späteres Umbenennen als Änderung sichtbar wird.
    - **Die einzige Verschattungsgefahr geprüft, nicht angenommen:** `_key_for_name()` liefert beim
      ERSTEN Substring-Treffer zurück, und die zwei Destroyer-Datenblätter sind das einzige Paar,
      das sich decken könnte. Sie können es nicht — `"Lokhust Heavy Destroyers"` enthält
      `"Lokhust Destroyers"` nicht (das Wort "Heavy" steht dazwischen) — und der Test belegt es,
      indem er zeigt, dass die beiden VERSCHIEDENE Dateien bekommen.
    - **Ein fremder Test ist daran zerbrochen, und das war richtig so:** `test_faction_badges.py`
      benutzte `"NECRONS"` als Beispiel für "eine Fraktion ohne Badge". Jetzt gibt es eins. Der
      Platzhalter ist auf ein ERFUNDENES Keyword umgestellt (`"NO SUCH FACTION"`) statt auf die
      nächste kunstlose echte Fraktion — sonst bricht dieselbe Zeile beim nächsten Logo wieder.
    - **Die drei Anbindungen schalten vier Fähigkeiten scharf**, die bis dahin gedruckt und
      wirkungslos waren, und genau daran werden sie im Test gemessen (an der FÄHIGKEIT, nicht an
      der Anbindung): Command Protocols zahlt nur einer geführten Einheit — vor diesen drei Merges
      hatte die Detachment-Regel armeeweit nichts, worauf sie wirken konnte; Guardian Protocols
      braucht einen NOBLE, und der Overlord ist der einzige im Roster; Rites of Reanimation gibt
      den Warriors FNP 5+; Harbinger of Destruction senkt die Krit-Schwelle der Immortals auf 5+.
    - **Aus 13 Listeneinträgen werden 10 EINHEITEN**, die Modellzahl bleibt 59 — `attach()` merged,
      es fügt nichts hinzu und nimmt nichts weg. Punkte und Starting Strength addieren sich, beides
      als eigene Testzeile.
    - **Getestet:** `test_necron_datasheets.py` **153/153**, `test_player2_necron_army.py`
      **62/62**, `test_faction_badges.py` **47/47**. Volle Regression **99 Suiten, ~5985 Prüfungen,
      98 grün / 0 rot / 1 bekannt**, dazu alle sechs Smokes — hier keine Formalie, weil eine
      Anbindung Aufstellung, Kohärenz und Zielwahl anfasst und ein Sprite die Renderkette.
  - **Etappe 3 — die KI spielt die Fraktion deterministisch.** **Null API-Calls** für jede
    Necron-Entscheidung, belegt durch einen werfenden Agenten.
    - **Zwei Mechanismen, und die Wahl ist nicht beliebig.** Alles REAKTIVE antwortet über
      `auto_players` im eigenen Controller (Muster `'Ard as Nails`) und braucht in `ai/`
      **gar nichts** — Menschprompt und KI-Antwort teilen dort ein Urteil. Die drei PROAKTIVEN
      Protokolle brauchen ein `_verdict()`/`_handle_*()`-Paar in `ai/agent_driver.py`, weil 15.01
      nur EINE Nutzung pro Phase erlaubt: die Frage ist nicht "soll diese Einheit kaufen", sondern
      "welche meiner Einheiten" — und das ist ein Vergleich über die ganze Armee.
    - **Keines der drei nimmt ein `memory.declined_*`-Memo**, aus demselben Grund, den
      `_unbridled_carnage_verdict` und `_ere_we_go_gain` dokumentieren: ein Urteil ist eine reine
      Funktion des Bretts, ein "nein" bleibt diese Frame ein "nein", und Neuableiten ist gratis.
      Ein "ja" kann sich nicht wiederholen, weil `can_use()` nach dem Grant ablehnt.
    - **Hungry Void MISST statt anzunehmen**, und das ist der Punkt: +1 Stärke ist mal viel und mal
      exakt nichts wert, je nachdem, wo sie relativ zur Toughness landet. S7→S8 gegen T8 kreuzt
      5+ auf 4+; gegen T9 sind beide 5+ und das CP kauft buchstäblich nichts. Das Verdict fragt
      `expected_wounds_against()` einmal mit und einmal ohne den Grant.
      - **Eigener Fehler, den die Suite gefangen hat:** die erste Fassung setzte nur das Flag
        `hungry_void_active` — aber `game/damage_estimate.py` liest `model.weapons` DIREKT und
        kennt keine Adjuster-Kette, also maß die A/B exakt die unveränderte Einheit und jedes
        Verdict kam als 0 zurück. Jetzt werden die angepassten Waffen über dasselbe
        `protocol_hungry_void.adjusted_weapon()` eingesetzt, das der echte Fight-Schritt ruft
        (und damit die AP-Hälfte gratis mit). **A/B belegt:** die Flag-only-Fassung
        wiederhergestellt → genau drei Prüfungen fallen.
    - **Conquering Tyrants Tor ist die HALBDISTANZ**, nicht das Volumen: das Stratagem rerollt nur
      "an attack that targets a unit within half range", eine Einheit ohne Ziel in Halbdistanz
      gewinnt nichts. Gemessen über `applies()` des Stratagems selbst, das die Halbdistanz schon
      über `game/weapon_range.py` liest.
    - **Sudden Storms Tor ist "würde diese Einheit überhaupt advancen"**, gelesen als "erreicht sie
      ohne Advance nichts" — die einzige Fassung der Frage, die zu diesem Zeitpunkt beantwortbar
      ist, und bewusst konservativ: wer schon schießen kann, geht und schießt, und das CP wäre weg.
    - **Beide Sonden räumen hinter sich auf** (`finally`), sonst bliebe der Grant nach einer
      blossen Messung stehen — als Testzeile festgehalten.
    - **Beobachtung**: `reanimation_protocols` als Feld PRO EINHEIT, nicht als Meta-Feld wie
      `waaagh` — Reanimation ist ein stetiges Rinnsal, kein Moment, um einen Plan darum zu bauen.
      Und als VORGERECHNETE Zahl (`wounds_you_could_recover`), zweite wiederkehrende Fehlerklasse:
      was das Modell selbst ableiten muss, leitet es schlecht ab — hier bräuchte es dafür den
      CHARACTER-Ausschluss und den Starting-Strength-Deckel. Für Nicht-Necrons fehlt der Schlüssel
      ganz, also zahlt keine andere Armee dafür.
    - **Im ECHTEN Spiel belegt, nicht nur im Test:** ein 9000-Frame-Selbstspiellauf zeigt
      `Player 2 spends 1 CP` → `Player 2 uses Protocol of the Sudden Storm` →
      `[sudden storm] 2 Immortals 1 - 10 ranged weapon(s) gain [ASSAULT], so it can Advance and
      still shoot`, neben zwölf `[reanimation]`-Zeilen. Hungry Void und Conquering Tyrant erreicht
      der MockAgent-Lauf erwartungsgemäss nicht (er kommt selten in Schuss-/Nahkampfphasen — die
      bekannte Grenze, die CLAUDE.md schon nennt); dafür sind die Suiten die Evidenz.
    - **Getestet:** neues `test_necron_ai.py` (**43/43**) — jedes Verdict an seiner
      ENTSCHEIDUNGSGRENZE (der Fall, der kaufen soll, und der Nachbarfall, der es nicht soll), die
      Sauberkeit beider Sonden, die reaktiven drei über ihre eigenen Controller, das
      Beobachtungsfeld, und ein Verdrahtungsabschnitt, der prüft, dass die Aufrufe wirklich in
      `main.py` und `ai/agent_driver.py` stehen. Die Null-API-Garantie ist an der SIGNATUR
      festgemacht (die drei Handler nehmen gar keinen `agent`), was stärker ist als ein Zähler.
      Volle Regression **99 Suiten, ~5964 Prüfungen, 98 grün / 0 rot / 1 bekannt**, dazu alle
      sechs Smokes (beide Armeen).

**Datenblatt-Rezept** (Details in der Memory-Datei `new-datasheet-recipe.md`): Werte per Wahapedia
holen — Slug nach Muster raten ist die billigere erste Wette, der Fraktions-Index nur der Rückfall,
und mit PRÄZISEN Sachfragen abfragen ("welche Phase? welcher unmodifizierte Würfelwert? Trefferwurf
oder Wundwurf?") statt "fasse zusammen". **Bekanntes Rendering-Artefakt (12× aufgetreten):** Keywords
hängen am NAMEN, während die Keyword-Spalte leer bleibt — der Namensspalte folgen. Eine Waffe mit
BS "N/A" ist [TORRENT]. Bei "gleicher Name, andere Zahlen" eine eigene Klasse anlegen; sonst teilen.
Eine bloße Paraphrase ist NICHT implementierungswürdig — dann als fehlend in `abilities_text`
markieren (im Spiel sichtbar) und im Test ASSERTIEREN, damit das Nachrüsten eine sichtbare Änderung ist.

**`build_squad()`-Eigenheiten:** ein Cursor pro ERSETZTER Waffenmenge (zwei Optionen, die dieselbe
Waffe aufgeben, teilen ihn; überschneidende Mengen verschmelzen); reine Ergänzungen starten bei
Modell 0; ein Tausch wird übersprungen, wenn das Modell die Waffe gar nicht trägt; `choices` darf
statt einer ANZAHL eine Liste von Modell-INDIZES tragen (das ist eine Aussage der Armeeliste, nicht
des Datenblatts). Gear läuft NACH den Waffentäuschen, deshalb funktionieren bedingte Optionen.

## KI-Architektur

`ai/agent_driver.py`, `ai/claude_agent.py`, `ai/observation.py`, `ai/planner_prompt.py`,
`ai/tactical_prompt.py`. Enumerierte Optionen statt Freitext-Tools (`choose_action(index)`), ein
API-Call nur bei echter Wahl. **Die KI spielt die Orks; Aeldari-Regeln haben per User-Vorgabe keinen
KI-Pfad.**

- **Zwei Schichten.** Der taktische Layer bekommt seine Optionen von der ENGINE — eine regelwidrige
  Aktion taucht gar nicht erst auf. Der Planner schreibt Freitext und kann jede Regel verletzen;
  deshalb existiert `_validate_turn_plan()` als deterministischer Backstop (Reserverunde 20.03,
  Disembark-Zeitpunkt, LONE OPERATIVE, verschwundene Ziele, unerreichbare Positionen mit
  3"-Toleranz, Über- und Ein-Einheiten-Garnison, kollidierende Positionen, unbeschießbare
  Zielorte). Jede künftige Planungs-Regelverletzung gehört DORTHIN, nicht in den Prompt.
- **Ein Retry-Kanal zurück an den Planner** für Probleme, die nur er beheben kann (eine Koordinate
  wird für eine EIGENSCHAFT gewählt; ein Punkt daneben erbt keine davon). Läuft im
  Hintergrund-Thread, genau EINMAL, und wird nur übernommen, wenn er messbar weniger Probleme hat
  UND mindestens so viele echte Squads abdeckt — sonst ist "alle Befehle löschen" die billigste Art,
  perfekt zu punkten (genau so ist einmal ein ganzer Zug ohne Plan gelaufen).
- **Ereignisgesteuerte Neuplanung** (gegnerische Einheit stirbt, Charge scheitert), gedeckelt auf 2
  pro Zug, plus Revalidierung an jeder Phasengrenze (reine Arithmetik, kein API-Call). Der alte Plan
  bleibt in Kraft, während der neue entsteht — der Zug friert nie ein.
- **Modelle**: `config.AI_MODEL` (Haiku) für Einzelentscheidungen, `config.AI_PLANNING_MODEL`
  (Sonnet) für den einen Plan-Call pro Zug. Haiku-Pläne waren gemessen zu passiv/regelwidrig.
- **"Planner vor jeder Aktion" wurde gemessen und abgelehnt**: 15-25 Sonnet-Calls pro Zug, und der
  Nutzen eines Plans ist gerade die Zuteilung ÜBER Einheiten hinweg (Greedy-vs-Global). Der taktische
  Layer IST die reaktive Schicht.
- **Beide Prompts sind aufgeräumt** und in eigenen Modulen (Planner 19.4k → 11.2k Zeichen, taktisch
  15.2k → 11.4k), mit benannten Abschnitten und `HOW TO DECIDE` bei 2-6% statt 66%. Neue Regeln
  gehören in den passenden Abschnitt, nicht ans Ende — beide waren durch reine Anlagerung gewachsen,
  und einmal kam ein Plan als Tool-Call-Markup zurück. **Eine Taktik als ZAHL an einer Option wird
  befolgt; dieselbe Taktik als Prosa konkurriert mit allem anderen.**
- **Bewertung**: `game/damage_estimate.py` (`expected_wounds`/`expected_kills`/`damage_value`) ist die
  EINE Schätzung, gelesen von Bedrohungszahlen, Zielwahl, Reserve-Landeplatz, Nahkampf-Waffenwahl und
  drei Stratagem-Gates. Sie rechnet Punkte statt Anteile (ein Spezialist wird sonst auf Massen
  gelenkt), deckelt Überkill, liest RESTwunden, und berücksichtigt Modifikatoren, die nur vom
  angreifenden Modell und der Zieleinheit abhängen (Tank Hunters, Guardian Drone).
  **Bekannte Untererfassung, bewusst:** Re-rolls, [SUSTAINED HITS]/[LETHAL HITS]/[DEVASTATING WOUNDS],
  Deckung, Granaten und die meisten Fähigkeiten (Volley Fire, Waaagh!, Might is Right) fehlen — die
  Schätzung ist durchgehend eine UNTERGRENZE. Positionsabhängige Effekte bleiben draußen, weil sie
  auch für HYPOTHETISCHE Positionen aufgerufen wird.
- **Beobachtung** liefert u.a.: Waffen beider Seiten, `defensive_profile`, `threat_assessment`
  (Bedrohung + Handel, getrennt nach `best_to_shoot`/`best_to_charge`), `charge_threats` (Wurf +
  Odds, auch für einen geplanten ZIELORT), `staging_positions` (nur was nach der GEGNERbewegung noch
  hält und Boden GEWINNT), `reachable_this_turn` (mit `if_you_advance`), `if_you_disembark` /
  `if_you_stay_aboard`, Terrain, Hidden-Status, `waaagh`, `charge_now` inkl.
  `chance_if_you_advance_first` (exakte gemeinsame Verteilung über beide Würfe, nicht "Mittelwert
  dann Charge").
- **Deterministische Entscheidungen ohne API-Call** (jeweils weil es ein VOLLSTÄNDIGES Verfahren ohne
  Restermessen gibt, und ein Test mit werfendem Agenten belegt die 0 Calls): Command Re-roll auf einen
  verfehlten Charge (verfehlt + Nahkampfeinheit + Lücke ≤7"), War Hordes Unbridled Carnage,
  'Ere We Go im WAAAGH-Zug, 'Ard as Nails, Ammo Runt, Grot Orderly, Spirit of Gork — und die
  **gesamte Necron-Fraktion**: Reanimation Protocols samt Warriors-Reroll, Resurrection Orb,
  Technomancer, Matter Absorption, Living Lightning, Wraith Form, Plasmacyte und alle sechs
  Awakened-Dynasty-Protokolle. Die drei proaktiven davon (Hungry Void, Sudden Storm, Conquering
  Tyrant) über `_verdict()`/`_handle_*()`-Paare, alles übrige über `auto_players`.
- **Fernkampfeinheiten bekommen den Charge gar nicht erst angeboten** (`game/combat_focus.py`,
  gelesen von `_shooting_specialist_charge_block()`). User: "havey destroyer - die sollten nicht
  chargen. das sind fernkampf einheiten ... baue gerne eine charge sperre ein, wenn die
  fernkampfwaffen so extrem viel stärker sind als die nahkampfwaffen. aber ... shard of the void
  dragen. da soll die sperre nicht greifen." WITHHELD statt begründet (Fehlerklasse 5) und spart den
  API-Call; der Vermerk läuft über `memory.declined_charge`, also genau eine Logzeile pro Phase, mit
  BEIDEN Schadenszahlen darin.
  - **Die Messung ist bewusst ZIELFREI, obwohl im Charge-Moment ein Ziel vorliegt.** Die
    Pro-Ziel-Ratio wurde zuerst gebaut und gemessen und trennt NICHT: gegen 1-Wunden-T2-Gretchin
    wundet alles, also stehen die Immortals dort bei 1.03, während die Necron Warriors — die frei
    bleiben müssen — gegen ein Deff Dread 1.19 erreichen. Die beiden Mengen überlappen, und eine
    Schwelle in einer Überlappung entscheidet danach, welcher Feind zufällig am nächsten steht.
    Das eigene Profil trennt sauber (Band 1.09..1.70, Schwelle 1.4).
  - **Der Void Dragon verfehlt die Sperre um den Faktor sechs** (0.23) — kein Grenzfall. Die
    einzige Einheit nahe der Linie sind die Ork Warbikers (1.00 gegen diesen Referenzverteidiger,
    1.50 gegen einen T8/3+/8W-Vergleich); benannt statt weggestimmt. Kein Ork-Datenblatt wird
    von der Sperre erfasst.

## Bewegungsqualität — was gemessen ist

Die wichtigste Einsicht dieses Repos zur KI-Bewegung, weil sie erklärt, warum Fixes lange nicht hielten:

- **`measure_crowded_movement.py` misst weiterhin die ORK-Armee, und zwar absichtlich.** Es baut
  seinen eigenen Roster und liest `config.PLAYER2_ARMY` nicht — beim Armeetausch also NICHT
  mitgezogen. Das ist hier richtig und nicht Fehlerklasse 16: es ist eine BASELINE, keine Suite.
  Jede Zahl im Abschnitt unten (54% → 64%, 185" → 206", "perfekte Reihenfolge ist ~3% wert", der
  verworfene Formations-Solver) wurde gegen genau diese Armee auf genau diesem Gelände gemessen;
  sie auf eine andere Armee umzuhängen würde die Zahlen nicht aktualisieren, sondern
  unvergleichbar machen. **Die Zahlen sagen also, wie gut die KI-Bewegung ist — nicht, wie gut die
  Bewegung der aktuellen Default-Armee ist.** Bis zum Armeetausch war das dieselbe Aussage.
- **`measure_movement_fixes.py` misst ein LEERES Brett** (`state.tokens = list(sq.models)`) —
  Blockierung durch eigene Einheiten kann darin per Konstruktion nicht auftreten. Jedes "300/300 ohne
  Stehenbleiben" stammt aus dieser Welt. `measure_crowded_movement.py` ist die ehrliche Welt.
- **Gemessen (map2, ganze Armee, 3 Züge):** allein 81%, mit der GEGNER-Armee 77% (kostet also nichts),
  mit der EIGENEN 54%. Der gesamte Verlust kommt daher, dass sich die eigenen Einheiten im Weg stehen.
- **Perfekte Bewegungsreihenfolge ist ~3% wert** (beste von 15 zufälligen gegen die eigene Heuristik)
  — eine Reservierungs-/Sortier-Umstellung wurde deshalb NICHT gebaut.
- **Der Formations-Solver ("erst eine legale Zielformation, dann hineinlaufen") ist gebaut, gemessen
  und ausgebaut worden**: 51% → 26%, nach zwei Reparaturen 37%. Die Winkelfreiheit der Sweep ist mehr
  wert als eine Kohärenz-Garantie, und die Sweep verwandelt bereits 89% ihres verbrauchten Budgets in
  Fortschritt — sie geht nicht in die falsche Richtung, sie kommt nur nicht weit genug.
- **Die "bewertete Platzierungs-Alternativen"-Umstellung ist ebenfalls gemessen und abgelehnt**
  (`measure_placement_headroom.py`): beim Vorrücken liegt die Decke auf dem, was die KI erreicht;
  Verstecken kostet auf diesem Gelände IMMER Boden (0 Plätze, die eine Einheit als FLÄCHE verdecken
  und einen halben Zug gewinnen); die vermeintliche Schussfeld-Lücke war fast vollständig ein
  Messfehler (jedem Modell wurde die beste Waffe der EINHEIT zugerechnet). Was die Messung
  STATTDESSEN fand — Einheiten scheitern an ihrer eigenen FORM — ist als `_place_packed()` umgesetzt.
- **Aktueller Stand (map2, Gedränge):** ~64% erreichter Fortschritt, ~206" Gesamtboden, 0 Rückwärts,
  0 gebrochene Kohärenz. Ausgangslage der Messreihe war 54% / 185".
- **Verbleibende Grenze ist teils physisch**: ein 3.5"-Schlitz nimmt keine drei 0.98"-Basen kohärent
  auf, und der Umweg ist länger als eine Zugbewegung. Das richtig zu lösen bräuchte
  formationsbewusste Pfadsuche plus Mehrzug-Planung — die naive Version davon ist gemessen und
  verworfen.

## Bekannte offene Punkte

- Ein von allen Seiten umstelltes Fahrzeug kann steckenbleiben (Ein-Wegpunkt-Heuristik + A*, keine
  formationsbewusste Pfadsuche).
- Keine explizite Right-of-Way-Koordination zwischen Einheiten im selben Zug (nur implizit über
  `priority` und die Korridor-/Ausladezonen-Stufen).
- `GreaterGoodController.choose_target()` kann bei einer (nie auftretenden) ungültigen Zielwahl in
  `CHOOSING_TARGET` hängen bleiben.
- `TransportController`s Rapid-Disembark-Pfad prüft 20.04s Zonen-Sperre nicht.
- Die UI sagt nicht deutlich, dass eine Platzierung/ein Pile-In des MENSCHEN ansteht (nur Panel-Text,
  kein Hinweis auf dem Brett). Das Zeitfenster für ein menschliches Consolidate im KI-Zug ist eng.
- Battle-Shock-Würfe werden im Panel pro Würfel gefärbt, obwohl 2W6 kombiniert gewertet wird.
- Der MockAgent-Selbstspiellauf erreicht selten Schuss-/Nahkampfphasen — für diese Bereiche sind die
  Suiten und reproduzierte Fälle die Evidenz, nicht ein Selbstspiel-Lauf.
- **`smoke_pregame.py` scheitert an EINER seiner zwei Aufstellungs-Schranken, wenn die KI die T'au
  spielt**: "AI's heavy units deploy in the front row" meldet heavy 13.94" gegen screen 15.12" auf
  map2. **Betrifft die Default-Paarung NICHT** (aeldari/necrons ist grün, ebenso jede Paarung ohne
  T'au auf Player 2). Die Ursache ist die PRÄMISSE der Schranke, nicht die Aufstellung: sie prüft
  "ein paar große Modelle vor vielen billigen Körpern", und `_deployment_role()` stuft in dieser
  Liste SECHS Einheiten als `heavy` ein (jeden Battlesuit) gegen drei `screen` — bei den anderen
  Listen sind es ein bis drei. Dazu infiltrieren auf beiden Seiten der Rechnung Einheiten (24.20),
  deren Platz eine andere Regel bestimmt als der Scorer. Braucht eine eigene Messreihe (welche
  Rolle ein Battlesuit verdient, und ob Infiltratoren aus dieser Schranke gehören) — bewusst NICHT
  durch Aufweichen der Zusicherung erledigt, weil genau diese Schranke schon einmal einen echten
  Mangel angezeigt hat, als sie zu streng aussah.
- ~~**Kein Aeldari-Datenblatt setzt `character = True`**~~ — **erledigt.** User-Korrektur: "Das ist
  ja Quatsch, da gibt es viele Charaktere: Avatar, Farseer, alle Phoenix Lords." Richtig — es war
  eine DATENLÜCKE der Datenblätter, keine Eigenschaft der Fraktion. Neun Profile tragen das Keyword
  jetzt: Avatar of Khaine, Farseer, Eldrad, Warlock (Conclave), Warlock Skyrunner, Asurmen, Jain
  Zar, Lhykhis, Baharroth (Fuegan hatte es schon). **Die Aspekt-Exarchen bekommen es NICHT** — ein
  Exarch der 10. Edition ist Teil seiner Einheit und druckt kein CHARACTER.
  Damit werden vier Regeln scharf, die für Aeldari still wirkungslos waren: 05.03s
  Zuteilungsschutz (gemessen: Eldrad steht jetzt als LETZTE Allocation-Gruppe, die Storm Guardians
  fangen zuerst), Epic Challenge, Heroic Intervention und Precision. Assassination zahlt gegen
  Aeldari jetzt 5 statt 0 (10 Charakter-Modelle in der Liste).
  - **Ein vorbestehender Layout-Fehler wurde dadurch AUFGEDECKT, nicht verursacht.**
    `army_select._cell_size()` maß jede Kachel an ihren EIGENEN zwei Abschnitten, während
    `_lay_out_sections()` die CHARAKTER-Zeilen am Seiten-MAXIMUM für JEDE Kachel reserviert. Die
    Kachel mit wenigen Charakteren und vielen Squads (Orks: 4/14) braucht also
    `reservierte + eigene Squad-Zeilen` und lief unten aus der Kachel heraus (gemessen 68 px bei
    1600×900). Latent war das schon vorher: mit 7 Aeldari-Charakteren und 13 Squads ergab deren
    Eigenrechnung zufällig dieselbe Zahl wie der echte Ork-Bedarf. Das Keyword verschob eine
    Einheit zwischen die Abschnitte und die Koinzidenz brach. `_cell_size()` reserviert jetzt
    dieselben Zeilen wie das Layout; **A/B: 9 Prüfungen fallen mit der alten Formel**, an vier
    Auflösungen geprüft.
- **Ein bekannter, vorbestehender Suite-Fehlschlag**: zwei A/B-Zeilen in `test_formation_coherency.py`
  ("used to keep its spread frozen") — die Sonde stellt nicht die ganze Vor-Fix-Welt her (ihr fehlt
  die inzwischen für die KI aufgehobene 9"-Spannweitengrenze). Als vorbestehend belegt.
- ~~`measure_deployment_safety.py` meldet auf map2 `safer=False`~~ — **erledigt** mit der
  `assault`-Aufstellungsrolle: beide Karten PASS. A/B belegt (ohne die Rolle kippt map2 wieder auf
  `safer=False`), also war die Zusicherung nicht zu streng, sondern hat einen echten Mangel
  angezeigt.

## Später-Liste (bewusst zurückgestellt)

- **Army-Building-Flow gegen ein Punktelimit.** Die Punktedaten, die Vorspiel-Sequenz und seit der
  Listenauswahl auch ein Screen davor existieren; es fehlt weiter der Schritt, der damit eine Armee
  ZUSAMMENSTELLT. Daran hängen: das 50%-Reserve-Limit als Bau-Regel, EPIC HEROs "nur einmal",
  Farsights "Independent Power", Enhancements als System. **Der Auswahl-Screen ist ausdrücklich
  NICHT dieser Schritt** (User: "Die Listen sollen auch erstmal predefined sein. Also, wir brauchen
  noch keine Listenbaukosten. Das kommt erst viel später") — er wählt nur, wer welche der drei
  fertigen Listen spielt.
- **Missionsstand im Szenen-Snapshot.** `scene_io` sichert schon bisher keine VP; jetzt auch nicht
  Hand und Kartenstapel. Ein F9-Speicherstand verliert also den Missionsfortschritt.
- **Generisches Keyword-/Ability-/Wargear-System** — aktuell benannte Boolean-/Wert-Felder pro
  tatsächlich gebrauchter Fähigkeit. Nachziehen, sobald ein Datenblatt es wirklich braucht.
- **Vertikalität/Höhe** (deshalb auch kein Plunging Fire 22.05) — bewusste Vereinfachung. Fähigkeiten,
  die "ignore vertical distance" sagen, sind hier belegte No-ops.
- Kamera-Scrolling/Viewport; Armeefarben-Auswahl; KI-Decision-Log mit `reasoning` pro
  Einzelentscheidung; Aufspalten einer Attached Unit, wenn die Bodyguards fallen.
- **Rotationsfähige `Obstacle`s** — siehe Kartenabschnitt; nur bei echtem Bedarf, dann als eigener
  Schritt mit allen sechs Konsumenten.
- **Aeldari-Punkteliste vollständig transkribieren**; die vier Alternativwaffen der
  Guardian-Defenders-Plattform (Keyword-Spalte unbestätigt); Crisis Fireknife (kein Datenblatt,
  wird aber von zwei Leader-Listen genannt).
- **Formationen rotieren nicht mit der Marschrichtung** (`_formation_slot()` bewahrt Versätze in
  Brett-Koordinaten) — ein nach Norden aufgestellter Trupp trägt seinen Charakter beim Ostzug auf der
  Flanke.

- **Sprites für alle zehn bis dahin kunstlosen Einheiten verdrahtet, plus fünfundzwanzigstes und sechsundzwanzigstes Aeldari-Datenblatt: War Walkers und Wave Serpent** (User: "habe mittlerweile sprites für alle neuen einheiten hochgeladen / jetzt / war walker / wave serpent").
  - **Die zehn Sprites sind zehn Tabellenzeilen, und die acht "kein Sprite"-Pins sind umgedreht** — genau der Zweck, zu dem sie gesetzt wurden: jede der acht Suiten hielt ausdrücklich fest, dass keine Kunst gemappt ist, damit ein späteres Hinzufügen eine SICHTBARE Änderung ist. Sie prüfen jetzt das Gegenteil, und zwar **am Modell statt an der Tabelle** — ein Schlüssel, der auf keine Datei auf der Platte auflöst, ist genau der Fehler, den ein Blick in die Map nicht sieht. Wo Dateiname und Datenblattname auseinandergehen, gewinnt die DATEI (`Warlock Sky Runner` gegen `Warlock Skyrunners`, `Windrider`/`Ranger` singular gegen den pluralen Datenblattnamen, `War Walker` gegen `War Walkers`) — dieselbe Entscheidung, die `Warpspider`, `JainZar` und `Eldrad Ultran` schon festhalten: dieses Modul beugt sich dem Ordner, statt Umbenennungen zu verlangen.
    - **A/B gemessen statt behauptet:** mit einer entfernten Mapping-Zeile fallen genau die zwei Prüfungen dieses Datenblatts (`76/78`), mit ihr wieder `78/78`.
    - Die drei Exarch-Linien (Dark Reapers, Shining Spears, Swooping Hawks) teilen sich die Kunst ihrer Einheit — als eigene Testzeile festgehalten, weil "der Exarch bekommt dieselbe Datei" sonst wie ein Versehen aussieht statt wie das Fehlen einer eigenen.
    - **Die Storm-Guardian-Waffenvarianten brauchten NULL Codeänderung** und wurden nur nachgeprüft (User: "storm guardians passen so von den sprites her. das wurde in einer anderen session schon erledigt."): die `"<key> - <waffe>"`-Konvention greift von selbst, sobald die Dateien da sind — Flamer, Fusion Gun und Power Sword lösen alle drei auf, jeweils nur auf den Modellen, die die Waffe tatsächlich tragen. `Fuegan.png` liegt ebenfalls im Ordner und bleibt ungenutzt: dafür gibt es kein Datenblatt.
  - **Vorbestehende Lücke, die dieses Paar erst live gemacht hat:** `MissileLauncherSunburstProfile` trug kein `blast`, obwohl der gedruckte NAME "missile launcher - sunburst **blast**" lautet — und die Namensspalte ist bei Wahapedia die verlässliche Hälfte (die Keyword-Zelle kommt für diese Zeile auf jedem Datenblatt leer zurück, inzwischen der ~13. Fall desselben Rendering-Artefakts). Die eigene Kopie der Dark Reapers setzte das Keyword bereits, die beiden hätten sich also widersprochen. Jetzt fielden **drei** Datenblätter diese Zeile.
  - **Sechs neue Waffen, und fünf davon sind Unterklassen statt Wiederholungen:** JEDE Waffe des Wave Serpent ist eine Waffe, die es schon gab, plus [TWIN-LINKED] — `TwinBrightLance`, `TwinScatterLaser`, `TwinShurikenCannon`, `TwinStarcannon` und das `TwinMissileLauncher`-Modus-Paar erben deshalb, damit eine Änderung an den geteilten Zahlen die Twin-Version erreicht. Im Test paarweise gegen die Basisklasse geprüft (gleiche S/AP/D/Reichweite, Keyword nur oben), weil eine kopierte Klasse einen reinen "hat sie das Keyword"-Test genauso bestünde. Der War Walker brauchte gar keine neue Fernkampfwaffe — seine sechs Zeilen sind die geteilten, unverändert; neu ist nur `WarWalkerFeetProfile` (A3/WS3+/S5), das sich vom Wraithbone Hull (A3/WS4+/S6) in zwei Charakteristiken unterscheidet, also der "gleicher Zeilentyp, andere Zahlen"-Zweig des Rezepts.
  - **Wave Serpent Shield: der erste verteidigerseitige Wundmodifikator, dessen Bedingung die ATTACKE betrifft statt den Schützen.** Guardian Drone, 'Ard as Nails, Protect und Forewarned fragen alle "wer greift an" oder "wer wird angegriffen"; dieser fragt "ist die Stärke DIESES Angriffs größer als meine Toughness". `_wound_modifiers(target_squad)` bekam dafür ein optionales `strength`, durchgereicht an den drei Aufrufstellen aus derselben `_effective_strength(weapon)`, mit der die Schwelle selbst gebildet wird — eine zweite Quelle für dieselbe Zahl wäre genau die Drift, die dieses Repo laufend konsolidiert. Optional, damit die Aufrufer ohne Angriff in der Hand unverändert dasselbe bedeuten.
    - **Vorzeichen positiv**, wie jeder Malus hier: `game/modifiers.py`s Konvention justiert die SCHWELLE, und "subtract 1 from the Wound roll" macht den Wurf schwerer.
    - **Die Toughness kommt aus `attached_unit_toughness()`** und nicht vom Profil — dieselbe Quelle wie die Schwelle, die er modifiziert (19.02). Heute unmöglich relevant (ein VEHICLE ist nicht anschließbar), aber die zwei können sich damit nicht uneinig werden.
    - **Fernkampf-only ist der gedruckte Text**, nicht eine Vereinfachung: der Test belegt es an der Quelle (`game/fight.py` liest das Modul nirgends) statt eine Nahkampfszene zu konstruieren.
    - **Gemessen an beiden Seiten der S>T-Linie durch den ECHTEN Controller:** S12 gegen T9 wundet normal auf 3+ und hinter dem Schild auf **4+**; S9 gegen T9 bleibt 4+ (9 ist nicht größer als 9); S4 bleibt 6+. Dazu eine A/B-Sonde, die die Fähigkeit an ihrer Quelle neutralisiert und dieselbe Rechnung auf 3+ zurückfallen lässt — ein reiner Prädikat-Test hätte offen gelassen, ob der Modifikator den Wurf je erreicht.
  - **Crystalline Targeting ist Target Acquisition in anderer Währung** — siebter Konsument von `on_squad_finished_shooting` und der zweite, dessen Wirkung eine MARKE AUF DEM ZIEL ist statt eines Grants auf dem Schützen ("each time a friendly AELDARI unit makes an attack that targets that enemy unit", also armeeweit). Zwei Unterschiede zum Vorbild, beide im gedruckten Text: kein Waffen-Qualifikator (es braucht also keine Pro-Waffen-Trefferbuchführung), und **"each unit can only be selected for this ability once per turn" ist eine Grenze am ZIEL, nicht an den War Walkers** — ein zweiter War-Walker-Trupp darf seine eigene Fähigkeit weiterhin nutzen, nur nicht auf einer diesen Zug schon gewählten Einheit (eigener Testfall).
    - **Zwei Lebensdauern, absichtlich verschiedene Uhren:** der AP-Effekt läuft am PHASENENDE ab, das Auswahl-Ledger am ZUGENDE. Beide einzeln gepinnt, weil sie sich leicht zu einer verschmelzen ließen.
    - "Improve the AP by 1" heißt MEHR negativ (dieselbe Arithmetik wie `game/crit_ap.py`), angewandt als Kopie in der Adjuster-Kette — die geteilte Instanz wird nie mutiert. **Und die Kette ist der richtige Ort und nicht der Wundschritt:** der Rettungswurf liest die AP von genau dieser zurückgegebenen Waffe.
  - **War-Walker-Wargear: bewusst als MATCHED PAIRS, mit gemessener Begründung.** Der gedruckte Text ist per Kanone ("each model can have EACH shuriken cannon it is equipped with replaced"), ein Walker darf also ein gemischtes Paar tragen. `build_squad()` adressiert MODELLE, nicht Waffenkopien, und ein Tausch gibt jede Kopie der genannten Waffe auf — die vier Optionen sind deshalb als "beide Kanonen für zwei derselben Waffe" geschrieben. Alle vier Ergebnisse sind legale gedruckte Builds, der Default (zwei Kanonen) ebenso; verloren ist nur das gemischte Paar.
    - **Der Blast Radius der Alternative wurde GEMESSEN, bevor sie verworfen wurde:** über alle 55 Datenblätter beider anderer Fraktionen gibt es genau **zwei** Fälle, in denen eine Option eine Waffe ersetzt, die ein Modell mehrfach trägt (Devilfish 2× Twin Pulse Carbine, Tankbustas' Boss Nob 2× Rokkit Pistol) — Pro-Waffenkopie-Adressierung im Scaffold hätte also den Pfad angefasst, durch den jedes Datenblatt läuft, für genau eine Build-Form. Dieselbe Entscheidung, die Wraithguards Alles-oder-Nichts-Notiz festhält.
  - **Punkte:** War Walkers flach 85/160 (keine Kopien-Tiers), Wave Serpent gestaffelt 115 für die 1.-3. Einheit und 125 ab der 4. — die Form, die Warp Spiders und Swooping Hawks schon nutzen. Alle Wargear-Optionen beider Datenblätter sind gratis.
  - **Erwartete Regression, sauber nachgezogen:** `test_avatar_of_khaine.py` pinnte "die größte Base der Fraktion außer dem Falcon", und der Wave Serpent teilt dessen Radius (2.1", der an den Devilfish angeglichene Wert — beide sind derselbe Grav-Panzer-Rumpf). Die Zeile nimmt jetzt BEIDE Grav-Panzer aus, und zwar namentlich statt über ein Keyword: der War Walker ist ebenfalls VEHICLE und behält seine gedruckte 60-mm-Base, gehört also in den Vergleich.
  - **Getestet:** neues `test_war_walkers.py` (**79/79**) und `test_wave_serpent.py` (**99/99**) — Statlines (inkl. der Base-Umrechnung als nachgerechnete Arithmetik und der Zusicherung, dass der Walker die Grav-Panzer-Größe NICHT nimmt), alle Waffen paarweise gegen ihre Basisklassen, jede Wargear-Form samt Gegenseitigkeit und Trimm-Fall, die Punkte-Tiers, der Transport in fünf Richtungen (5 Fire Dragons passen, 5 Wraithguard belegen 10 von 12 Slots, ein zweiter Trupp obendrauf passt nicht mehr, JUMP PACK und ein zweites Fahrzeug werden abgelehnt), Crystalline Targeting vollständig plus End-to-End durch den echten `ShootingController`, und der Schild wie oben. Volle Regression **89 Suiten, ~5287 Prüfungen, 88 grün / 0 rot / 1 bekannt**, dazu `smoke_pregame.py map2` (0 API-Calls, beide Deckungs-Schranken halten), `smoke_log_input.py map2` und `selfplay.py map2` 2000 Frames — nötig, weil `main.py`, `game/shooting.py`s Wundschritt und `game/sprites.py` angefasst wurden.
  - **Vier eigene Fehler, alle vom Werkzeug gefangen:** der Import von `attached_unit_toughness` zeigte auf `game.attached_units` statt auf `game.squad` (der Import scheiterte sofort); `Checks` hat nur `eq` und `true`, mein `truthy`/`contains` gab es nie; `tk.shooting_scene()` nimmt zwei Positionsargumente und liefert `shooting`/`target`, nicht `controller`/`defender`; und `choices` ist `{Linie: {Optionsname: Anzahl}}`, kein Liste-von-Namen. Dazu **zum wiederholten Mal die Heredoc-Falle** (Apostrophe in `Wraithguard's`/`model's` zerlegen ein `cat <<'PYEOF'`) — Code- und Prompttexte gehören über Write/Edit, nicht über Bash-Heredoc.
  - **Arbeitshinweis, gleiche Lage wie in früheren Einträgen:** parallel lief eine zweite Sitzung auf demselben Repo — `smoke_log_input.py` scheiterte einmal mit `NameError: GROUND_TILE_SIZE_IN` in `game/renderer.py`, einer Datei, die diese Arbeit nie angefasst hat und deren Zeitstempel zehn Sekunden alt war. Wiederholung grün. Vor der Ursachensuche prüfen, ob ein Fehlschlag überhaupt der eigenen Änderung gehört.
  - **Offen und bewusst so:** die gedruckte YNNARI-Hälfte des Transport-Ausschlusses ist nicht modelliert (kein Pro-Modell-Fraktions-Tracking — dieselbe dokumentierte Lücke, die Falcon und Devilfish tragen); das gemischte War-Walker-Waffenpaar, siehe oben; und wie die vierundzwanzig davor stehen beide in keiner Demo-Armee.

- **Siebenundzwanzigstes Aeldari-Datenblatt: Fuegan — eine zehnte Extraktion, und die zweite Fähigkeit überhaupt, die ein Modell ZURÜCKHOLT** (User: "Fuegan").
  - **`game/weapon_range.py` ist die zehnte Extraktion, und sie war fällig**: "wie weit reicht diese Waffe gerade" gehörte `game/pulse_accelerator.py`, solange nur die Drohne fragte. Burning Lance ist der zweite Konsument derselben Frage — also extrahieren statt sich an ein nach der ersten Fähigkeit benanntes Modul anzuhängen (Fehlerklassen 10 und 11 in einem).
    - **Und die Extraktion hat einen vorhergesagten Fehler geschlossen.** `game/shooting.py` rief die Drohnenfunktion an GENAU EINER Stelle (dem "erreicht diese Waffe das Ziel"-Test) und trug dort den Kommentar, die beiden HALBdistanz-Stellen ([RAPID FIRE X], [MELTA X]) läsen bewusst weiter die gedruckte Reichweite, *"because no pulse carbine has either keyword — **if one ever does, they need the same treatment**"*. Burning Lance betrifft **[MELTA]-Waffen**. Also ist genau dieser Fall eingetreten, und alle drei Stellen lesen jetzt `weapon_range`. Die Alternative wäre gewesen, den Kommentar stehen zu lassen und den nächsten Leser ihn erneut entdecken zu lassen.
    - **Gemessen statt behauptet:** ein Ziel auf **6.38"** liegt außerhalb der gedruckten Halbdistanz (6") und innerhalb der verlängerten (9"). Ohne Fuegan Schaden **3**, mit ihm **6** — dieselbe Waffe, dieselbe Szene, durch das echte `melta_adjusted_weapon()`. Ein reiner "ist die Reichweite jetzt 18" -Test hätte die eigentliche Wirkung gar nicht berührt.
  - **Burning Lance ist die Pulse Accelerator Drone mit zwei Unterschieden, beide im gedruckten Text:** die Drohne nennt eine WAFFE ("pulse carbines", deshalb Namensabgleich, und sie dokumentiert diese Lesart als unsicher), Fuegan nennt ein KEYWORD ("Melta weapons", deshalb `weapon.melta`, nichts zu raten). Und die Bedingung ist 24.22s "while this model is LEADING a unit", gelesen über `attached_units.leader_ability()` — nicht `unit_wide_ability()`, das fragt, ob JEDES Modell die Fähigkeit druckt. Bringt 19.04s Nachlauffenster gratis mit, was hier mehr zählt als sonst: Unquenchable Resolve stellt ihn wieder hin, die Fähigkeit ist also nicht dauerhaft weg.
    - **Seine eigene Searsong wächst mit** — beide Feuermodi sind [MELTA], und er ist ein Modell dieser Einheit. Das steht so im Text und ist als eigene Zeile gepinnt, weil "models in that unit" leicht als "die Bodyguards" gelesen wird.
  - **Unquenchable Resolve ist die zweite Fähigkeit, die ein zerstörtes Modell zurückholt** — nach Painboys Grot Orderly, und deshalb lagen beide nötigen Teile schon bereit: `Squad.destroyed_models` (das Token überlebt `remove_dead_models()`, und weil niemand seine Koordinaten zurücksetzt, überlebt auch "wo es zerstört wurde") und `formation_layout.ring_candidates()`, das von einem Punkt aus in konzentrischen Ringen nach außen läuft — also wörtlich "as close as possible".
    - **Der Unterschied zu Grot Orderly ist die Platzierungsregel: DISTANZ, nicht Kohärenz.** Grot Orderly stellt Bodyguards in eine stehende Einheit zurück und hält 09.02 per Konstruktion; hier nennt der Text einen Ort, und die Form der Einheit hat kein Mitspracherecht. Eine dadurch gebrochene Kohärenz wird auf dem gewöhnlichen Weg beim nächsten Zug repariert.
    - **"not within Engagement Range" MUSSTE das Modul selbst prüfen.** `SetupController.position_valid()` sagt in seinem eigenen Docstring, dass es Engagement und Kohärenz NICHT abdeckt (die hängen an den Endpositionen eines ganzen Trupps, nicht an einem Punkt). Sich allein darauf zu verlassen hätte ihn direkt in den Nahkampf gestellt — dieselbe Falle, die einmal einen ganzen Trupp im Emergency Disembark gekostet hat (Fehlerklasse 8). Gemessen: mit Feinden auf dem Todesfeld kommt er zurück, außerhalb Engagement Range jedes Feindes, und nicht weiter weg als nötig.
    - **Am ZUGENDE der Phase, nicht im Moment des Todes** — `remove_dead_models()` läuft einmal pro Frame, und jeder Trigger davor sieht noch Leichen (Fehlerklasse 12). Die Phasengrenze heißt: der Sweep ist fertig, die Feindpositionen, die sein Engagement-Test liest, stehen, und ein Modell, das dieselbe Attacke wie der Rest seiner Einheit getötet hat, wird nach allen anderen behandelt. Der TOD wird trotzdem im Sweep vermerkt und nicht erst an der Grenze — sonst wüsste "the first time this model is destroyed" nicht, in welcher Phase gestorben wurde.
    - **Vier Hälften von "zurück", alle einzeln geprüft:** in der Tokenliste, in seinem Squad, VON der destroyed-Liste herunter, und mit vollen Wunden. Jede einzelne weggelassen ergibt ein halblebendiges Modell, und nur manche davon fallen sofort auf.
    - **Nicht optional und niemand zu fragen:** der Text hat kein "you can". Also kein `DecisionManager`-Prompt — der D6 geht beschriftet und mit seiner Schwelle durch den Dice Manager (der Mensch sieht den Wurf, der es entscheidet), die Platzierung ist deterministisch.
    - **Er kommt in seine EIGENE Einheit zurück.** Unter 19.01 merged diese Engine den Leader in ein Squad, das gestorbene Modell war also ein Modell dieses Squads, und der gedruckte Text sagt nur "set this model back up on the battlefield" — nichts vom Verlassen. Steht die Einheit noch, führt er sie wieder (und Burning Lance läuft weiter); ist sie ausgelöscht, ist er ihr einziges Modell und damit genau das, was "set this model back up" beschreibt.
  - **"Searsong – lance" ist ein PROFILNAME, nicht [LANCE].** Die Keyword-Zellen kamen wieder durchgehend leer zurück (~14. Fall des Rendering-Artefakts), also gilt die Namensspalte — und dort steht "lance" in derselben Position wie "beam", das eindeutig ein Name ist (und wie "sunburst"/"starshot" beim Missile Launcher). Als eigene Testzeile gepinnt, samt Begründung, damit eine spätere Korrektur eine sichtbare Einzeiler-Änderung ist statt einer stillen.
  - **T3 wurde gegen VIER Vorgänger geprüft, nicht gegen ein Bauchgefühl.** T3 auf einem Phoenix Lord liest sich wie ein Transkriptionsfehler; Asurmen, Jain Zar, Baharroth und Lhykhis drucken alle dasselbe Chassis (T3/Sv2+/W5/Ld6+/OC1/Inv4+). Der Test vergleicht deshalb mit ihnen statt mit einer Literalzahl — das ist die Zusicherung, die auch bei einer künftigen Änderung noch etwas aussagt.
  - **Drei neue Waffen:** Searsong Beam (12"/A3/BS2+/S8/AP-3/D2, [ASSAULT] [MELTA 1] [SUSTAINED HITS 2]) mit der Lance (18"/A1/S14/AP-4/D6, [ASSAULT] [MELTA 6]) als Feuermodus — EIN Datenblatteintrag, also wird nur der Beam vergeben, sonst hätte er zwei Kanonen — und die Fire Axe (A6/WS2+/S5/AP-4/D3, keine Keywords). 130 Punkte, führt ausschließlich Fire Dragons, keine Wargear-Optionen.
  - **`Fuegan.png` lag seit dem letzten Sprite-Schwung ungenutzt im Ordner** — im Wave-Serpent-Eintrag ausdrücklich als "dafür gibt es kein Datenblatt" vermerkt. Jetzt gibt es eins.
  - **Getestet:** neues `test_fuegan.py` (**90/90**) — Statline gegen die drei anderen Fuß-Phoenix-Lords, alle drei Waffen inkl. der Feuermodus-Struktur und der [LANCE]-Entscheidung, Punkte und die LEADER-Paarung in beide Richtungen, Burning Lance durch den ECHTEN `attach()` (geführt/ungeführt/allein stehend, Melta gegen Nicht-Melta, seine eigene Waffe) plus die Halbdistanz-Wirkung end-to-end durch `melta_adjusted_weapon()`, Unquenchable Resolve vollständig (Wurf 1 gegen 2, die vier Hälften von "zurück", "as close as possible" auf leerem Boden, der Engagement-Ausschluss mit Feinden auf dem Todesfeld, "the first time" beim zweiten Tod, und dass eine Einheit ohne die Fähigkeit nichts schuldet), dazu A/B-Sonden für beide Fähigkeiten. `test_pathfinders.py` (die Pulse-Accelerator-Seite der Extraktion) unverändert **80/80**. Dazu `smoke_pregame.py map2` (0 API-Calls, beide Deckungs-Schranken halten) und `selfplay.py map2` 2000 Frames — nötig, weil `main.py` und `game/shooting.py`s Reichweiten-Stellen angefasst wurden.
  - **Arbeitshinweis, zum zweiten Mal in Folge:** die parallel laufende zweite Sitzung baut gerade am Renderer. Ihr neues `test_token_base_fill.py` (Datei existierte zu Beginn dieser Arbeit nicht) meldet `nothing is drawn in the band just inside the rim`, während `game/renderer.py` sekundenaktuelle Zeitstempel trägt — **nicht dieser Arbeit zuzuordnen**, keine der beiden Dateien referenziert irgendetwas hiervon. Alle Suiten, die die hier geänderten Dateien berühren, sind einzeln nachgefahren und grün.
  - **Offen und bewusst so:** wie die sechsundzwanzig davor steht er in keiner Demo-Armee; und die KI hat für ihn keinen Pfad (Aeldari-Vorgabe des Users).

- **Player 1s Liste revidiert: Avatar of Khaine und Fire Dragons raus, Dark Reapers / Rangers / Shining Spears / Shroud Runners / Warlock Skyrunners rein** (User lieferte die vollständige neue Liste). 20 Listeneinträge, **13 Einheiten** nach den fünf Anbindungen, **74 Modelle**, Engine-Summe **1900 pts** gegen die 1930 der Liste.
  - **Die fünf Anbindungen sind unverändert** und wurden nicht neu erfragt: dieselben fünf Charaktere stehen wieder in der Liste, und die Reihenfolge Farseer-vor-Conclave ist weiterhin regelgetrieben (siehe den Guardian-Defenders-Block). Nur der Bestand drumherum hat sich geändert.
  - **Der Warlock Skyrunner steht ALLEIN, und das ist eine Aussage, keine Panne.** Seine LEADER-Zeile ist ein JOIN, der ausschließlich Windriders nennt — die Liste fieldet keine. Als eigene Testzeile an der PAARUNGSTABELLE festgehalten (`can_attach()` lehnt ihn bei Guardian Defenders ab), damit "steht allein da" als geprüfte Tatsache dasteht und nicht als vergessene Anbindung.
  - **Die Shining Spears sind der erste Roster-Eintrag mit Nicht-Waffen-Gear.** Der Exarch listet "Shimmershield, Shuriken Cannon, Star Lance" — drei gedruckte Sätze, aber nicht dreimal dasselbe: Star Lance und Shuriken Cannon sind Waffentäusche (sie geben VERSCHIEDENE Waffen auf, deshalb zusammen nehmbar), das Shimmershield ist eine reine ERGÄNZUNG und liegt als `Gear` vor. Es gehört also in die andere Spalte, und die zwei Gear-Spalten der ARMY-Tabelle werden damit zum ersten Mal überhaupt benutzt — der bisherige Kommentar dort ("kein Aeldari-Datenblatt hier hat Nicht-Waffen-Gear") war ab dieser Liste falsch und ist mitgezogen.
    - **"Star Lance" steht zweimal im gebauten Loadout und das ist richtig:** die Lanze ist EINE gedruckte Waffe mit einer Fernkampf- UND einer Nahkampfzeile, genau wie die Laser Lance, die sie ersetzt. Im Test als Doppelnennung ausgeschrieben, weil es sonst wie ein Duplikat aussieht.
  - **Vier der fünf neuen Einheiten sind der gedruckte Default** — Dark Reapers (Reaper Launcher auf allen fünf inklusive Exarch), Rangers und Shroud Runners (die beiden haben überhaupt keine Wargear-Optionen), Warlock Skyrunners (Witchblade, NICHT die Singing Spear der zwei Fuß-Conclaves). **Geprüft statt angenommen:** bei den Dark Reapers ersetzen alle drei Optionen genau den Launcher des Exarchen, ein Irrtum hätte also bedeutet, eine davon zu nehmen; bei Rangers und Shroud Runners assertiert der Test zusätzlich, dass die Optionsliste wirklich leer ist.
  - **map3s Roster nannte `"1 Fire Dragons 1"` und wäre still leer gelaufen** — ein Name, der auf keine gebaute Einheit passt, fieldet nichts, statt zu krachen. Die Anti-Panzer-Rolle erben die **Dark Reapers**, und zwar nach MESSUNG statt nach Namensähnlichkeit: gegen einen T10-Battlewagon ist ihr Reaper Launcher (S10/AP-2) die stärkste im Roster verbliebene Fernkampfantwort — Shining Spears kommen auf S6, Shroud Runners auf S5, Rangers auf S4. Die Begründung steht bei der Zeile.
  - **`test_player1_army.py` zum ZWEITEN Mal von genau derselben Falle getroffen** (Fehlerklasse 17): es baut seinen eigenen Roster und meldete nach dem Listenwechsel weiterhin fröhlich "10 units / 63 models / 1865 pts" — grün, während es eine Armee prüfte, die es nicht mehr gibt. Beim ersten Mal (T'au → Aeldari) war es dasselbe. Die Totals sind deshalb jetzt als die Rechnung der LISTE ausgeschrieben (28 Modelle aus den acht einfachen Einheiten plus 46 aus den fünf Attached Units) statt als eine Zahl aus einem früheren Lauf — eine veraltete Erwartung, die bloß widerspricht, wird gefangen; eine, die vom letzten Durchlauf abgeschrieben wurde, nicht.
    - **Und genau das hat sofort einen eigenen Fehler gefangen:** ich hatte 69 Modelle in den Kommentar geschrieben, es sind 74. Der Test meldete `[74]`, die ausgeschriebene Rechnung zeigte, wo ich mich verzählt hatte.
  - **Punkte: 12 von 19 Einträgen weichen ab**, und anders als bisher **in beide Richtungen** — Dark Reapers 90 gegen 100, Rangers 55 gegen 60, Shroud Runners 80 gegen 90 und Warlock Skyrunners 45 gegen 55 sind BILLIGER als die Transkription, während Eldrad/Jain Zar/Guardian Defenders/Howling Banshees/Striking Scorpions/Wraithguard/Farseer/Shining Spears teurer sind. Die alte Liste war einseitig teurer, was "die App rundet auf" plausibel machte; das ist damit widerlegt und in der Punktenotiz benannt. Die Transkription wird weiterhin NICHT überschrieben.
  - **Getestet:** `test_player1_army.py` von 69 auf **81/81** erweitert (die fünf neuen Einheiten Modell für Modell, das Shimmershield am MODELL statt in der Waffenliste, die Gegenprobe dass Rangers/Shroud Runners wirklich optionslos sind, der Alleinstand des Skyrunners an der Paarungstabelle, und die beiden Totals als ausgeschriebene Rechnung). Volle Regression **92 Suiten, ~5410 Prüfungen, 90 grün / 0 eigene rot / 1 bekannt**, dazu `smoke_pregame.py map2` (0 API-Calls, beide Deckungs-Schranken halten), `selfplay.py map2` 2000 Frames und `selfplay.py map3` 400 Frames — letzteres nötig, weil dessen Roster angefasst wurde.
  - **Arbeitshinweis, dritter Eintrag in Folge:** die parallel laufende zweite Sitzung baut weiter am Renderer und ist mitten in einer Umbenennung (`COVER_TILE_SIZE_IN` → `DENSE_COVER_TILE_SIZE_IN`); `test_ground_texture.py` und `test_token_base_fill.py` fielen deshalb während dieser Läufe durch, `game/renderer.py` trug jeweils sekundenaktuelle Zeitstempel. **Nicht dieser Arbeit zuzuordnen** — alle Suiten, die die hier geänderten Dateien berühren, sind einzeln nachgefahren und grün.

- **Die drei MOUNTED-Jetbike-Einheiten des Rosters auf EINE gemeinsame Tischgröße gebracht: 45 mm** (User: "die shining spears und die shroud runners sind zu groß. 1/4 kleiner. und dann den warlock skyrunner genau so groß machen. der ist zu klein.").
  - **Shining Spears und Shroud Runners von 60 mm auf 45 mm** (`base_radius_in` 1.181 → 0.886, exakt drei Viertel), **Warlock Skyrunner von 32 mm auf dieselben 45 mm** — also von der anderen Seite auf denselben Wert. 45 mm ist zufällig selbst eine echte Basisgröße, was den Wert nicht bloß als Bruchrechnung dastehen lässt.
  - **Das ist eine Gameplay-Zahl, nicht nur eine optische.** `edge_distance()` liest den Radius, also verschieben sich Engagement Range, Überlappung, Kohärenz und das Packen der Formation mit. Bei diesen drei ist die Richtung erwünscht: es sind Jetbikes auf einem 60-mm-Fußabdruck gewesen, also genau die Form, die durch dieses Gelände am schlechtesten passt (vgl. den Bewegungsabschnitt: die verbleibende Grenze ist teils physisch). Beim Skyrunner geht es in die andere Richtung, aber von 32 mm aus und für ein einzelnes Modell.
  - **Zweiter Fall, in dem eine Base von ihrer gedruckten Größe abweicht** — der erste ist der Falcon, den der User an den Devilfish angeglichen haben wollte (und der Wave Serpent, der dessen Wert dann geerbt hat). Dieselbe Art Entscheidung, dieselbe Behandlung: der Kommentar an der Zeile sagt gedruckte Größe UND Tischgröße, damit niemand später "korrigiert".
  - **Im Test gegen EINANDER gepinnt statt gegen ein Literal** — jede der drei Suiten prüft ihren eigenen Wert und zusätzlich, dass er mit den beiden anderen übereinstimmt. Eine gemeinsame Größe, die nur dreimal separat als Zahl dasteht, driftet beim nächsten Anfassen auseinander; so ist genau die Gemeinsamkeit die Zusicherung.
  - **Die Windriders wurden NICHT mitgezogen** und behalten ihre gedruckten 32 mm: sie waren nicht Teil der Bitte und stehen in keiner Demo-Armee. Damit passt der Skyrunner erstmals nicht mehr zu dem Jetbike, dem er sich anschließt — die zwei teilten den Wert bis eben. Als eigene Testzeile festgehalten, gerade WEIL eine spätere Angleichung wie eine Aufräumarbeit aussähe.
  - **Getestet:** `test_shining_spears.py` **71/71**, `test_shroud_runners.py` **68/68**, `test_warlock_skyrunners.py` **55/55**, `test_windriders.py` **59/59** unverändert. Volle Regression **92 Suiten, ~5447 Prüfungen, 91 grün / 0 rot / 1 bekannt**, dazu `smoke_pregame.py map2` (beide Deckungs-Schranken unverändert bei 0.00 gegen 1.80), `selfplay.py map2` 2000 Frames und `smoke_log_input.py map2` — die Smokes hier nicht aus Gewohnheit, sondern weil eine Basisgröße Aufstellung, Platzierung und Bewegung anfasst.

- **Der Fade-Back-Fehler ein zweites Mal, unter anderem Namen: die KI lief über den offenen Path-of-the-Outcast-Zug der Rangers hinweg** (User: "ranger / gleiches problem, wie damals bei fade back. die ki lässt mich nicht bewegen und macht gleich weiter"). **Der User hat die Diagnose gleich mitgeliefert, und sie war exakt richtig.**
  - **Reproduziert, bevor irgendetwas angefasst wurde** — mit einem offenen Zug des MENSCHEN im Bewegungszug der KI: `battle_focus` → `_is_blocked()` = **True**, `path_of_the_outcast` → **False**. Genau das gemeldete Verhalten, in einer Zeile.
  - **Die Ursache ist die Form des ersten Fixes, nicht sein Fehlen.** `_is_blocked()`s sechster Fall SAH den offenen Zug bereits — er verglich `move_mode` nur gegen den einen String `"battle_focus"`. Path of the Outcast ist derselbe Zug unter eigenem Modusnamen (der Modus ist ja gerade das, was den Confirm-Button an den zuständigen Controller routet), fiel also durch. Ein hartkodierter Einzelwert an einer Stelle, an der es eine MENGE ist — dieselbe Klasse wie die neun Extraktionen, nur eine Ebene kleiner.
  - **`MovementController.REACTIVE_MOVE_MODES` ist jetzt die eine Definition**, und sie steht bewusst an `start_battle_focus_move()`: diese Methode ist die EINZIGE Tür, durch die reaktive Züge kommen (Battle Focus' Fade Back/Opportunity Seized und Path of the Outcast rufen sie, Torchstar Gambit und Tactical Acumen gehen über `start_post_shooting_move()` und gehören ausdrücklich NICHT dazu — geprüft, nicht angenommen). Jeder Modus, der dort hineingereicht wird, ist per Konstruktion reaktiv; der Docstring sagt das jetzt als Pflicht.
  - **Der Wächter gegen eine DRITTE Meldung prüft die QUELLE, nicht das Verhalten:** ein Sweep über `game/*.py` sammelt jeden `move_mode`, der irgendwo an `start_battle_focus_move()` übergeben wird (benannte Konstanten werden aufgelöst, der Default mitgezählt) und verlangt, dass er in der Menge steht. Eine künftige vierte Fähigkeit, die sich nicht einträgt, fällt hier durch statt im Spiel. **A/B belegt:** mit `path_of_the_outcast` aus der Menge entfernt fallen zwei Prüfungen — die Verhaltensprüfung UND der Sweep, der den fehlenden Modus beim Namen nennt (`got ['path_of_the_outcast']`).
  - **Die Gegenrichtung ist mitgeprüft:** der EIGENE reaktive Zug der KI darf sie nicht blockieren (sie treibt ihn selbst) — sonst wäre der Fix ein Deadlock statt einer Behebung. Gilt für beide Modi.
  - **Warum nicht pauschal "jeder fremde offene Zug blockiert":** das wäre robuster gegen Vergessen, aber `move_mode` deckt auch Pile-In/Consolidate ab, die in der Fight-Phase beiden Spielern gehören und über einen eigenen Pfad (`_foreign_activation_in_progress()`) laufen. Eine Pauschale hätte dort einen Deadlock riskiert — schlimmer als der gemeldete Fehler. Die benannte Menge plus Quell-Sweep gibt dieselbe Sicherheit ohne das Risiko.
  - **Getestet:** `test_rangers.py` von 63 auf **72/72** (Abschnitt 5b: nichts offen → KI handelt, Menschzug offen → KI wartet, nach Auflösung wieder frei, eigener Zug der KI blockiert nicht, plus der Quell-Sweep). Volle Regression **92 Suiten, ~5455 Prüfungen, 91 grün / 0 rot / 1 bekannt**, dazu `selfplay.py map2` 2500 Frames und `smoke_pregame.py map2` — die KI-Schleife ist genau das, was geändert wurde, also ist der Selbstspiellauf hier keine Formalie.
  - **Nebenbefund:** `ai/agent_driver.py` importierte `MovementController` bisher gar nicht (es nannte ihn nur in Kommentaren). Der Import ist ergänzt und erzeugt keinen Zyklus.

- **Der Charge-Wurf zeigt jetzt das Sprite der chargenden Einheit — und das Panel nennt sie nicht mehr "Target"** (User: "wenn charge overlay kommt, also wenn angesagt wird, wer den charge roll macht. da will ich auch ein sprite haben").
  - **Warum dort bisher kein Sprite stand:** `charge.py` setzte nur `target_name=squad.name`, nie `target_squad` — die Matchup-Zeile des Würfelpanels braucht aber die Einheit selbst, um ihre Kunst aufzulösen. Ein kwarg an zwei Stellen (der normale Wurf und der von Heroic Intervention, 15.11).
  - **Dabei fiel eine vorbestehende Falschbeschriftung auf, die durch das Sprite erst sichtbar wurde:** die Einheit auf einem Charge-Wurf ist die, die CHARGT, nicht ein Ziel — ihre Ziele sind zu diesem Zeitpunkt noch gar nicht gewählt (sie werden danach aus dem gefiltert, was der Wurf erreicht). Das Panel schrieb trotzdem "Target: 2 Boyz 1". Dasselbe gilt für den Battle-Shock-Test (die Einheit, die ihn ABLEGT).
    - Neues `DiceManager.subject_label` (Default `"Target"`, also für jeden bestehenden Aufrufer unverändert): das Panel druckt `"{subject_label}: {name}"`. Charge setzt `"Charging"`, Battle-Shock `"Testing"`. Bewusst ein Feld am Wurf statt einer Ableitung aus `roll_kind` im Panel — `target_name` bedeutet je nach Aufrufer etwas anderes, und nur der Aufrufer weiß was.
  - **Sieben weitere Würfe bekommen ihr Sprite gratis mit**, weil sie ohnehin eine Einheit benennen und ihnen nur `target_squad` fehlte: Isha's Fury, Grav-inhibitor Field, Explosives, Crushing Impact, Flickerjump, Grot Orderly, Battle-Shock. Damit ist die frühere Zusage "Portraits überall, wo von Einheiten gesprochen wird" auch für das Würfelpanel eingelöst und nicht nur für Overlays.
  - **Getestet:** `test_dice_matchup.py` um Abschnitt 4 erweitert (**45/45**) — der Charge-Wurf über den ECHTEN `ChargeController` (mit der Vorbedingung "der Charge ist wirklich ansagbar", sonst prüfte der Test einen Wurf, der nie stattfand), die Einheit wird mitgeführt, das Label lautet "Charging", es gibt korrekt KEIN Angreifer/Ziel-Paar, und die Zeile erreicht mit Kunst den Bildschirm. Dazu die A/B in die andere Richtung: ein Wurf, der nichts sagt, behält "Target" — sonst wäre der Default stillschweigend mitgeändert worden.
  - **Regression:** 92 Suiten, ~5465 Prüfungen, 91 grün / 0 rot / 1 bekannt; `smoke_pregame.py map2`, `smoke_log_input.py map2`, `selfplay.py map2`.

- **Das ALT-Lineal war in den meisten Zuständen unerreichbar — fünfte Instanz derselben Verdrahtungsfalle in `main.py`s Event-Kette** (User: "ich kann oft keine entfernungen messen. zb bei overwatch. sorge bitte dafür, dass ich immer entfernungen messen kann. mit alt"). Neue **Fehlerklasse 15** oben, weil dieselbe Falle jetzt "A", Mausrad-Zoom, ESC, die Log-Filter und das Lineal getroffen hat.
  - **Statisch reproduziert, bevor irgendetwas angefasst wurde:** die ALT-Zweige standen an **43. Stelle** einer `if/elif`-Kette mit 48 Zweigen, hinter 36 Gates auf CONTROLLER-STATE, deren Rümpfe ausschließlich Mausklicks behandeln. Ein solcher Zweig matcht, tut nichts, und die Kette läuft nie weiter — die Taste war weg. Genau die Momente, in denen man misst (Abwehrfeuer, Schadenszuteilung, Entscheidungs-Prompt, offener Würfelwurf), sind die, in denen eines dieser Gates aktiv ist.
  - **Und das war nur die halbe Ursache.** `InputManager.handle_event()` ist der ALLERLETZTE Zweig derselben Kette und der einzige Schreiber von `mouse_pos_in` und `hovered_token` — den zwei Feldern, aus denen `renderer.draw_measure_tool()` das Lineal zeichnet. In genau denselben Zuständen fror also auch die Zeiger-Verfolgung ein. Nur die Tasten hochzuziehen hätte ein Lineal ergeben, das an der Stelle klebt, an der die Maus zuletzt verfolgt wurde — ein halber Fix, der sich beim Testen wie ein ganzer anfühlt.
  - **Zwei neue Einstiegspunkte, beide außerhalb der Kette:**
    - **`InputManager.track_pointer()`** — die eine Definition von "wo ist der Zeiger, worüber schwebt er". `main.py` ruft sie für JEDES `MOUSEMOTION` als schlichtes `if` VOR der Kette; `handle_event()` ruft sie weiterhin selbst, bleibt also allein lauffähig (`test_block_placement.py` treibt die Klasse direkt). **Bewusst kein Zweig IN der Kette:** würde der Vorab-Aufruf das Motion-Event konsumieren, fröre das Ziehen in jedem Zustand ein, in dem die Kette es zu Recht will. Der Doppelaufruf ist gratis, weil die Methode nur zwei Ansichtsfelder schreibt — als Feld-Diff gepinnt statt als Argument stehengelassen (`dragging_token`, `drag_offset`, `pending_move_token`, `group_drag_start_in` bleiben unberührt).
    - **`InputManager.update_measuring(alt_held)`** — einmal pro Frame, NACH der Event-Schleife, aus `pygame.key.get_mods()`. **Ein Poll statt eines KEYDOWN/KEYUP-Paars, und das ist die eigentliche Antwort auf "immer":** ein Poll kann von keinem Zweig geschluckt werden. Er schließt zusätzlich den Spiegelbild-Fehler, den das Paar hatte — ALT+TAB stellt den KEYUP an ein anderes Fenster zu, das Lineal blieb hängen. Die Flagge wird übergeben statt drinnen gelesen, damit der ÜBERGANG testbar ist: `start_measuring()` macht einen Schnappschuss des Ursprungs, dürfte also nicht jeden Frame neu laufen (sonst zöge der Anker mit dem Cursor mit und das Lineal zeigte dauerhaft 0").
  - **Gemessen durch die ECHTE `main()`-Schleife, nicht an der Klasse vorbei** (`smoke_measure_tool.py`): in Fire Overwatch, bei anstehendem Decision-Prompt und bei anstehendem Würfelwurf jeweils sieben Zusicherungen — ALT startet, der Zeiger wird überhaupt verfolgt, der Ursprung rastet auf dem Modell unter dem Cursor ein, das ferne Ende folgt, der Ursprung bleibt dabei stehen, es misst weiter solange gehalten wird, Loslassen beendet es. **A/B mit `--neutralize`** (beide Einstiegspunkte stillgelegt = die ganze Vor-Fix-Welt, nicht eine Zeile davon): **18 von 21 Prüfungen kippen**. Die drei, die auch dort bestehen, sind "Loslassen beendet es" — es hatte nie angefangen. Eine Sonde an der Klasse selbst hätte grün gemeldet und nichts über die Verdrahtung ausgesagt, die der ganze Fehler war.
  - **Der Quell-Wächter ist der Teil, der in jeder Regression mitläuft** (`test_measure_tool.py`, Abschnitt 4): er liest `main.py` und verlangt, dass die Zeiger-Verfolgung VOR dem ersten Zustandsgate steht, der ALT-Poll GANZ AUSSERHALB der Schleife und auf der Einrückung des Frame-Rumpfs (also nicht in eine Bedingung gerutscht), dass beide genau einmal aufgerufen werden, dass in der Kette weder `start_measuring()`/`stop_measuring()` noch `K_LALT`/`K_RALT` zurückkehren, und dass `draw_measure_tool()` unbedingt pro Frame gezeichnet wird. **A/B in beide Richtungen belegt:** den Poll in die Kette zurückgeschoben → 32/33 mit `got 16, want 8`; die Verfolgung zurückgeschoben → 32/33 mit `pointer tracking runs BEFORE the first state gate`.
  - **Getestet:** neues `test_measure_tool.py` (**34/34**) und `smoke_measure_tool.py map2` (**21/21**, neutralisiert 3/21). Volle Regression **93 Suiten, ~5499 Prüfungen, 92 grün / 0 rot / 1 bekannt**, dazu `smoke_pregame.py map2` (0 API-Calls, beide Deckungs-Schranken halten), `smoke_log_input.py map2` und `selfplay.py map2` 2000 Frames — die Smokes hier nicht aus Gewohnheit, sondern weil `main.py`s Event-Kette selbst der geänderte Gegenstand ist.
  - **Offen und bewusst so:** das Lineal misst weiterhin nur Mittelpunkt/Kante zweier Punkte auf der Ebene (keine Vertikalität, siehe Später-Liste), und der Zeiger wird auch außerhalb des Bretts in Zoll umgerechnet — die Linie läuft dann eben ins Leere, unverändert zu vorher.

- **Das "Claude is thinking"-Vollbild-Overlay ist weg; die KI-Meldung sitzt jetzt als Eck-Badge auf dem Brett, gedimmt werden die Seitenleisten** (User: "kein dunkles Overlay ... nur links oben in der Ecke ... noch ein bisschen auffälliger ... meinetwegen kann ein Overlay über die Seitenleisten sein, damit man nicht in die Versuchung kommt, irgendwelche Knöpfe drücken zu wollen").
  - **Die Deckung ist umgedreht**: das BRETT bleibt unangetastet (das ist das Einzige, was man während des KI-Zuges anschauen will), verdeckt werden die zwei Seitenleisten — genau die Flächen, die nichts als Knöpfe sind. `PANEL_DIM_ALPHA = 185`, nicht opak: eine Leiste, die ganz verschwindet, sieht aus wie ein Absturz. Die untere Reserves-Leiste bleibt bewusst frei ("Seitenleisten"), und der Test pinnt die Dim-Menge auf genau `left_panel_rect`/`right_panel_rect`.
  - **`game/ui/ai_busy_badge.py` ist die EINE Definition** für die Momente, die vorher drei handgezeichnete Rechtecke an derselben Ecke waren (Denk-Flash, Planungswarten, AUTO-PLAY). "Auffälliger" ist als MESSUNG festgehalten statt als Behauptung: gegen eine zur Laufzeit gerenderte Kopie des alten Looks, 41 px gegen 29 px Höhe.
  - **`pulse=` nur für den Planungs-Badge**, weil nur der jeden Frame neu gezeichnet wird. Der Denk-Flash ist EIN geblitzter Frame vor einem blockierenden Netzaufruf — ein Puls fröre dort auf einer zufälligen Phase ein und bliebe sekundenlang so stehen.
  - **AUTO-PLAY ist gar kein Badge mehr, sondern ein kleiner roter Punkt in der GEGENÜBERLIEGENDEN Ecke** (`draw_auto_play_dot()`, Brett oben rechts) — User-Folgemeldung: "jetzt überlagern sich die beiden Labels ... dieses AutoPlay-enabled Label kannst du eigentlich weglassen. Ersatz: ein kleiner roter Punkt ... als Riesenlabel brauchen wir nur das Claude is thinking". **Die Ursache der Überlagerung ist strukturell und nicht kosmetisch:** der Denk-Flash wird auf einen FERTIGEN Frame geblittet, und das breitere AUTO-PLAY-Label (414 px) schaute hinter dem schmaleren "Claude is thinking..." (251 px) hervor. Ein kleineres Badge in derselben Ecke hätte das wiederholt; gegenüberliegende Ecken können es per Konstruktion nicht. Der Punkt blinkt bewusst NICHT (er steht ganze Züge lang) und dimmt nichts — mehrere Fenster im KI-Zug gehören wirklich dem Menschen (reaktive Stratagems, Fire Overwatch, Wundzuteilung).
  - **Dieselbe Überlagerung konnte auch zwischen den zwei GROSSEN Badges auftreten** (Planung und Denken teilen sich die linke Ecke), deshalb steht `show_thinking_overlay()` still, solange `ai_memory.is_planning` läuft: das Planungs-Badge sagt bereits dasselbe, und ein schmaleres Badge über einem breiteren lässt dessen Rest stehen.
  - **`avoid_rects` löst den Fehler, den die Ecke sonst selbst erzeugt hätte**: das Würfelpanel ist im SELBEN Brettrechteck oben verankert (y=32), und 15.02s Command Re-roll wird entschieden, WÄHREND der Wurf steht — gemessen 56 px Überlappung bei 1920×1080, erheblich mehr bei schmalerem Fenster. Das Badge rutscht dann an der linken Kante nach unten unter den Blocker; nur nach unten, "links oben in der Ecke" beschreibt weiter, wo man hinschaut. Blocker-Quelle ist das neue `DicePanel.last_backdrop_rect`, das **am Anfang jedes `draw()` auf `None` zurückgesetzt** wird (gleiche Lebensdauer wie `_die_rects`) — sonst schiebt ein veralteter Rahmen das Badge um einen Wurf herum, der gar nicht mehr da ist.
  - **`show_loading_overlay()` behält sein Vollbild-Dim**, und das ist kein Versehen: es ist kein KI-Warten, sondern die direkte Antwort auf einen Klick des MENSCHEN (LOS-Sweeps, Bruchteil einer Sekunde bis ~1 s) — da gibt es nichts zu verfolgen und niemanden auszusperren. Als eigene Testzeile gepinnt, damit ein späteres "Vereinheitlichen" eine sichtbare Änderung ist.
  - **Elfte Extraktion, klein: `button_style.draw_glow()`** (der Halo stand inline in `draw_button()`, das Badge ist der zweite Konsument); `_chamfer_points()` dabei öffentlich geworden.
  - **Getestet:** neues `test_ai_busy_badge.py` (**44/44**) in zwei Hälften — Abschnitt 1-3 misst PIXEL auf einer echten Surface, Abschnitt 4 ist der Quell-Wächter auf `main.py`. **A/B in drei Richtungen** (Vollbild-Overlay zurückgebaut → 39/44, Ausweich-Logik entfernt → 43/44, `DicePanel`s Meldung entfernt → 42/44). **Durch die ECHTE `main()`-Schleife belegt** (Sonde über `selfplay.py map3`, 0 API-Calls): 1204 Badge-Aufrufe, in JEDEM davon Brettpixel an drei Stellen unverändert und beide Leisten bei den gedimmten Aufrufen nachweislich dunkler. Volle Regression **101 Suiten, ~6061 Prüfungen, 100 grün / 0 rot / 1 bekannt**, dazu `smoke_log_input.py map2`.
  - **Arbeitshinweis, vierter Eintrag in Folge:** die parallel laufende zweite Sitzung baut gerade am SCOUTS-Schritt (`game/scouts.py`, `game/movement.py`, neues `test_scouts_human.py`, minutenaktuelle Zeitstempel). `smoke_pregame.py map2` und `smoke_measure_tool.py map2` hängen deshalb in `prebattle_abilities` fest. **Als NICHT dieser Arbeit zugehörig belegt:** mit vollständig zurückgebauter Änderung scheitern beide identisch. `selfplay.py map3` läuft durch, weil map3s Roster keine Scouts-Einheit fieldet.

- **Der Scout Move des MENSCHEN hatte keinen Bestätigen-Knopf — das Vorspiel-Panel schluckte den ganzen Bildschirm** (User: "nach meinem scout move kann ich nicht bestätigen. es gibt keinen knopf").
  - **Alles andere an diesem Ablauf funktionierte schon**, und genau das machte den Fehler von der Engine-Seite unsichtbar: `game/scouts.py` stellt die Frage, `MovementController` führt den Zug, das Ziehen läuft über `InputManager`, und `main.py`s Event-Kette routet Linksklicks im linken Panel längst an `action_panel.handle_click()`. Es fehlte allein ein GEZEICHNETER Knopf. `_draw_dispatch()`s allererstes Gate übergibt das ganze Panel an `_draw_pregame_ui()`, solange 03.01 läuft, und dessen `PREBATTLE_ABILITIES`-Zweig druckt "Resolving pre-battle abilities..." und sonst nichts — der Zug ließ sich also machen und nie abschließen, und das Vorspiel kam nicht weiter. **Reproduziert, bevor irgendetwas angefasst wurde:** vier Knöpfe im Normalfall gegen zwei (nur die globale Toolbar) mit aktivem Vorspiel.
  - **Der Fix steht am GATE, nicht im `PREBATTLE_ABILITIES`-Zweig**: "das Vorspiel weicht, solange ein Zug läuft" (`movement_controller.state != movement.MOVING`). Damit ist jeder künftige Vorspiel-Schritt, der einen Zug startet, per Konstruktion abgedeckt. Der Aufstell-Schritt setzt dasselbe Muster von der anderen Seite: er delegiert an `_draw_setup_ui()`, statt Platzierung nachzubauen.
  - **`MovementController.can_advance()` ist die zwölfte Extraktion, und sie war der Grund, warum der Fix nicht allein reichte.** Der Advance-Knopf hing an einer HANDGEPFLEGTEN Liste verneinter Modi (`not is_charge and not is_pile_in and ...`) — `"scout"` fehlte darin, also hätte das Freilegen des Panels sofort einen Advance angeboten, den 24.32 nicht gewährt (gemessen: der Scout Move wächst von 6.0" auf 7.0"). `move_mode is None` ist die ganze Regel: ein Advance ist eine Entscheidung INNERHALB des eigenen Bewegungsphasen-Zuges, und das ist der einzige Modus ohne Namen. `start_run()` liest dieselbe Antwort, damit die Regel nicht UI-only ist (Fehlerklasse 4). **Nebenwirkung, bewusst und benannt:** damit verlieren auch `battle_focus`, `tactical_acumen`, `path_of_the_outcast` und `retro_thrusters` ihren Advance-Knopf — alle vier drucken "a Normal move", hatten ihn also nie verdient.
  - **Getestet:** neues `test_scout_move_ui.py` (**30/30**) — der gemeldete Fall durch das ECHTE `ActionPanel` (Confirm und Cancel vorhanden, Advance nicht, und der Confirm feuert wirklich `on_scout_move_finished`, also das, was die Warteschlange fortsetzt), die Gegenprobe dass ohne laufenden Zug keine Bewegungsknöpfe ins Vorspiel lecken, und `can_advance()` für alle elf benannten Modi einzeln plus den Normalfall. **A/B in zwei Richtungen:** das alte Gate zurückgebaut → 24/30; `move_mode is None` aus `can_advance()` entfernt → 16/30. Volle Regression **102 Suiten, ~6099 Prüfungen, 101 grün / 0 rot / 1 bekannt**, dazu `smoke_pregame.py map2`, `smoke_measure_tool.py map2`, `smoke_log_input.py map2` und `selfplay.py map2` — **alle grün, inklusive der beiden, die während der vorigen Sitzungshälfte am SCOUTS-Schritt hingen** (die parallele Sitzung hat `smoke_pregame.py` inzwischen beigebracht, die Frage zu beantworten).

- **Path of the Outcast war TOT VERDRAHTET — der Controller wurde gebaut und nie GEFÜTTERT** (User: "die KI lässt mich mit den Rangern immer noch nicht bewegen. schaust du an der richtigen stelle?" — nein, tat ich nicht: der frühere `REACTIVE_MOVE_MODES`-Fix war richtig, saß aber hinter einem Zug, der nie beginnen konnte).
  - **Reproduziert vor jeder Änderung:** die Frage erscheint, der D6 wird geworfen, der Mensch bestätigt — und `main.py` sagt es dem Controller nie. `path_of_the_outcast_controller.on_dice_acknowledged()` fehlte in der Bestätigungskette (24 Controller standen dort, dieser nicht), also wurde `_start_move()` nie erreicht und die Einheit nie beweglich. **Dritter Fall dieser Klasse** (nach `VengefulStarsController` und der Mark-Verdrahtung) und genau der, für den `verify_mark_wiring.py` existiert: `test_rangers.py` war grün, weil es `ctrl.on_dice_acknowledged()` selbst aufruft.
  - **Drei weitere fehlende Enden derselben Verdrahtung**, alle mitgezogen: das Panel kannte den Modus `path_of_the_outcast` gar nicht, also fiel Confirm/Cancel auf den generischen `movement_controller.confirm_move()` durch — `_finish()` lief nie, und `turn_tracker.active_player` wäre auf dem reagierenden Spieler gestrandet; `is_busy` fehlte in der Phasenwechsel-Sperre; und "once per turn" hatte keinen Rücksetzpunkt.
  - **Der gedruckte Text des Users ersetzt die alte Transkription:** **9"** statt 8" (gemessen, was das öffnet: ein Gegner, der zwischen 8" und 9" endet, wurde vorher ignoriert) und **"Once per turn"**, vorher gar nicht modelliert. Verbraucht wird die Nutzung beim ANNEHMEN, nicht beim Angebot — "Stay put" ist eine Antwort, keine Nutzung. **Eine Klausel der alten Transkription ist bewusst STEHENGEBLIEBEN und im Modul-Docstring markiert:** "not within Engagement Range" fehlt im gelieferten Text, aber ohne sie dürfte eine gebundene Einheit einen NORMAL move aus dem Nahkampf machen, was Kernregel 09.02 niemandem erlaubt (dafür gibt es Fall Back).
  - **Getestet:** `test_rangers.py` von 72 auf **85/85** — neuer Abschnitt 4b (die 8-9"-Bande gemessen, once-per-turn samt Rücksetzung und "Ablehnen verbraucht nichts") und **4c, der Quell-Wächter auf `main.py`** (Würfelbestätigung, Panel-Übergabe, `is_busy`-Sperre, Rundenreset). Ein Verhaltenstest kann diese Klasse nicht sehen — das ist ja der Punkt.

- **Forewarned wurde angeboten, während der Trefferwurf schon lief** (User: "das ist zu früh. das muss ich davor entscheiden").
  - **Die Engine-Sequenz war schon richtig**: `FightController` feuert seine `target_reactions` im Zielauswahl-Schritt (12.02), vor jedem Wurf. Falsch war `ai/agent_driver.py`s `_handle_fight()`: es rief `select_to_fight()` und `_resolve_fight_choices()` in EINEM synchronen Aufruf, und der zweite wirft den Trefferwurf. Prompt und Würfel erschienen im selben Frame, und die Antwort konnte den Wurf, für den sie erhoben wurde, nicht mehr erreichen.
  - **Die Schussphase hatte genau diesen Fix schon** — eine Meldung früher, für Psychic Shield ("bei psychic shield kann ich erst entscheiden, wenn der hit roll schon gewürfelt wird"). Die Nahkampfphase, also Forewarneds Phase, bekam ihn nie. `_defender_is_deciding(fight_controller)` ist jetzt die eine Frage, gestellt an BEIDEN Stellen, die den Zielauswahl-Schritt ausmachen: dem Auto-Pick bei genau einem gebundenen Gegner (der gemeldete, gewöhnliche Fall) und der expliziten Mehrfachauswahl.
  - **Zurückkehren genügt und lässt nichts halb fertig**: `_is_blocked()` behandelt einen offenen Prompt als harten Stopp, und der bereits vorhandene `CHOOSING_TARGET`/`CHOOSING_WEAPON`-Wiedereinstieg nimmt dieselbe Einheit danach wieder auf.
  - **Gemessen wird die REIHENFOLGE gegen die Würfel, nicht "ein Prompt kam"**: vor der Antwort null Würfe; nach der Antwort genau einer — und er trägt `[+1 (Forewarned)]`, die Entscheidung hat den Wurf also wirklich erreicht. **A/B:** ohne den Wächter landet der Trefferwurf bei noch offenem Prompt und ohne den Modifikator.
  - **Getestet:** neues `test_forewarned_timing.py` (**25/25**), inkl. Quell-Wächter für beide Aufrufstellen und dafür, dass die Schussphase ihren eigenen behält.

- **Zwei gemeldete Punkte, die nach Messung KEINE Änderung brauchten** — beide hier festgehalten, damit sie nicht erneut untersucht werden.
  - **Canoptek Wraiths queren Wände bereits** (User: "lass die Wraiths durch Wände bewegen. als Hausregel."): sie sind `beasts`, also ist `can_move_through_dense_terrain` (13.06) True und `blocks_movement_for()` gibt False zurück — eine Sonde zieht ein Modell durch eine 3" dicke Wand und der Commit wird angenommen. Nicht möglich ist nur das ENDEN auf Dense-Gelände (13.05, gilt für jedes Modell). Nach Rückfrage bestätigt: **Durchlaufen reicht, 13.05 bleibt**.
  - **Der Advance-Würfelwurf ist nicht verschwunden** (User: "ich sehe den advance würfel wurf nicht mehr"). Drei unabhängige Messungen: ein Differenztest über alle 13 `move_mode`-Werte × `run_used` × Bonus × Würfelmanager findet für einen GEWÖHNLICHEN Zug (`move_mode is None`) keinen erreichbaren Zustand, in dem `can_advance()` und die alte Panel-Bedingung sich unterscheiden; `measure_advance_usage.py` meldet unverändert "units offered an Advance afterwards: 0 -> 6 of 8"; und durch die ECHTE `main()`-Schleife in Player 1s echter Bewegungsphase steht der Knopf da und ein Klick wirft (`label='Advance' values=[5]`). **Was der Fix WIRKLICH entfernt hat**, sind Advance-Knöpfe auf GEWÄHRTEN Zügen — Scout Move, Path of the Outcast, Fade Back/Opportunity Seized, Tactical Acumen, Retro-thrusters. Alle fünf drucken "a Normal move"; ein Advance gehört regeltechnisch nicht dazu.
