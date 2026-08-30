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
9b. **Eine KETTE darf nicht neu lesen, was ihre eigenen Glieder löschen können.** Wird ein
    Einzel-Slot zu einer Liste ("der erste gewinnt" → "jeder bekommt sein Fenster"), erbt der
    zweite Reaktor NICHT die Prüfungen, auf die sich der erste verlassen hat: dazwischen liegt
    jetzt Code statt der geprüften Fortsetzung. Beim Charge-Deklarations-Haken hat genau das einen
    Absturz erzeugt (Photon Grenades → Combat Embarkation bekam `None`), weil `step()`
    `self.active_squad` je Schritt neu las, während eine Reaktion die Charge beenden darf. Regel:
    den Gegenstand des Fensters EINMAL fangen, und vor jedem Glied fragen, ob das Fenster noch
    steht — nicht darauf hoffen, dass das Ende der Kette schon prüft.

10. **Zwei Stellen, dieselbe Frage, zwei Antworten.** Der häufigste Grund für stille Drift. Daraus
    sind neun Extraktionen entstanden: `invulnerable_save.py`, `crit_hit.py`, `damage_reroll.py`,
    `damage_estimate.py`, `unmodified_six.py`, `psychic_mark.py`, `roll_bonus.py`, `crit_ap.py`,
    `strategic_reserves.py`. Regel: beim ZWEITEN Konsumenten extrahieren, nicht später.
    Seither: `weapon_range.py` (10.), `model_return.py` (11.), `button_style.draw_glow()` (klein),
    `MovementController.can_advance()` (12.), **`combat_focus.py` (13.)**,
    **`game/ui/tile_screen.py` (14.)** — der geteilte Rahmen beider Vorspiel-Screens, siehe
    Kartenauswahl —, **`agent_driver._garrison_fitness()` (15.)** — "wen lassen wir auf diesem
    Objective stehen", von drei Garnisons-Pässen gelesen —, und für den
    Auswahl-Screen zwei kleine: `sprites.models_portrait_paths()` und
    `loadout.model_loadout_lines()` — beide beantworten dieselbe Frage eine Ebene tiefer, für eine
    MODELLMENGE statt für ein Squad, weil eine Kachel die Komponenten einer Attached Unit einzeln
    zeigt. **Achtung bei der ersten:** `portrait_paths()` sortiert bewusst den CHARAKTER nach vorn,
    `models_portrait_paths()` nach Zeilenhäufigkeit — die gemeinsame Hälfte ist nur der
    Dedupe-Teil, und die beiden Ordnungen zusammenzuziehen hätte die dokumentierte
    Charakter-zuerst-Regel still gelöscht.
11. **Lügende Namen umbenennen, sobald ein zweiter Träger da ist.** Ein Aeldari-Effekt in
    `ere_we_go.py`, eine Fernkampfregel in `melee_crit.py`, `weapon_support_system` auf einem Aspect
    Warrior — alle drei umbenannt statt kopiert. Der Lokhust Lord brachte gleich ZWEI weitere:
    `OverlordStaffOfLight*Profile` → `LordStaffOfLight*Profile` (er trägt dieselbe Zeile) und das
    Profil-Flag `harbinger_of_destruction` → `leading_ranged_crit_on_5` (zwei Datenblätter drucken
    denselben Mechanismus unter ZWEI Namen — also wird das Flag nach der WIRKUNG benannt, und jedes
    Datenblatt behält seinen gedruckten Namen in `abilities_text`). **Der Spiegelfall gehört
    daneben:** gleiche Zahlen, ANDERER gedruckter Name → erben und nur `name` überschreiben
    (`LordsBladeProfile(OverlordsBladeProfile)`, wie die fünf Twin-Waffen des Wave Serpent), und im
    Test die beiden GEGENEINANDER pinnen statt gegen Literale.
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
    **Die Kehrseite: ein Zweig, den NIE etwas erreicht, altert unbemerkt weiter.** Die Kette ist
    ~48 Zweige lang, und die hinteren gehören seltenen Fähigkeiten — ein Zweig, dessen Bedingung
    nur bei einer bestimmten offenen Zuteilung wahr wird, kann jahrelang gegen eine Signatur
    stehen, die es nicht mehr gibt. Genau so ist Isha's Fury gegen ein `board_rect` gelaufen, das
    nie existiert hat (siehe unten). Ein VERHALTENStest kann das nicht sehen; dafür gibt es
    `test_event_chain_wiring.py`, das die Kette an der QUELLE prüft.

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
23. **`main()` ist eine 4000-Zeilen-Funktion, in der KONSTRUKTIONSREIHENFOLGE zählt** — und keine
    Suite kann das sehen, weil keine `main()` fährt. Zweimal in einer Sitzung passiert (Death
    Guard): ein `on_squad_finished_shooting`-Listener wurde ~100 Zeilen VOR seinem Controller
    registriert, und ein Stratagem-Block ~160 Zeilen vor `fight_controller`. Beide Male
    `UnboundLocalError` beim ersten echten Start, ein drittes Mal beim Zuweisen eines
    Kollaborateurs 15 Zeilen VOR dessen eigenem Konstruktor. Alle drei nur von den SMOKES gefangen
    und von ~8500 grünen Prüfungen nicht. **Seit dem dritten Mal gibt es dafür einen AST-Wächter**
    (`test_event_chain_wiring.py`, Abschnitt 4): für jedes `a.b = c` auf `main()`s Ebene, bei dem
    `a` und `c` beides dort gebundene Locals sind, müssen beide Zuweisungen VORHER stehen. Genau
    die Form aller drei Fehler, in 20 Sekunden statt in einem Smoke-Lauf; A/B belegt (er nennt
    Zeile und schuldigen Namen). Bewusst eng gehalten — jede Benutzung jedes Namens zu ordnen ist
    bei echtem Kontrollfluss unentscheidbar, und die Fehlalarme machten den Wächter wertlos.
24. **Ein Verdrahtungs-Wächter muss den AUFRUFAUSDRUCK prüfen, nicht den Namen zählen.** Das
    etablierte `_driver.count("_handle_x(") >= 2` blieb grün, nachdem die Aufrufstelle entfernt
    war — eine Erwähnung im Docstring zählte als zweites Vorkommen. Aufgefallen nur, weil die
    eigene A/B-Sonde dazu 126/126 meldete statt rot zu werden. Das Muster ist gut, die Zählung ist
    die schwache Stelle: `"if _handle_x(player, all_tokens, x_controller" in src` prüft, was
    gemeint war. **Eine A/B-Sonde, die NICHT bricht, ist ein Befund über den TEST.**

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
  **`smoke_end_turn_warning.py [map] [--neutralize]`** — die Nahkampf-Warnung als DREI-Klick-Folge
  durch dieselbe echte Schleife (End Turn → Warnung, Zug bleibt; wegklicken → Zug bleibt; End Turn
  → Zug endet). Die Folge ist der Punkt und lässt sich nicht halbweise prüfen. `--neutralize`
  stellt die Vor-Fix-Welt her und MUSS scheitern (4 von 13, und der erste Klick beendet den Zug
  sofort — genau das gemeldete Verhalten). Stellt die 12.04-Bühne selbst: zwei Einheiten dicht
  gepackt in Engagement Range, Pile-In per 12.03 übersprungen (sonst bleibt der Fight-Step in
  `NOT_STARTED` statt `SELECTING` zu erreichen), und räumt alles ab, was in `main.py`s Kette über
  dem Button steht — sonst misst er einen Klick, der den Button nie erreicht hat.
- **`measure_*.py`** — die Messskripte, die Entscheidungen tragen: `measure_crowded_movement.py`
  (Bewegung mit der GANZEN Armee auf dem Brett — die einzige aussagekräftige Welt, siehe unten),
  `measure_movement_fixes.py` (Geometrie EINER Einheit, macht KEINE Aussage über Spielqualität),
  `measure_placement_headroom.py`, `measure_deployment_safety.py` (Regressionsschranke),
  `measure_ard_as_nails.py`, `measure_stim_injectors_gate.py`, `measure_advance_usage.py`,
  `measure_fly_penalty.py` (kostet oder bringt 21.03 einer gemischten Einheit Boden — baut das
  Brett aus den Koordinaten EINES Logs nach, statt eine Einheit isoliert hinzustellen),
  `measure_home_garrison.py` (wer hält das Home Objective — beide Phasen der Entscheidung,
  Aufstellung und Turn-Plan, letzterer gegen das Brett des gemeldeten Logs; `--neutralize`).
- **`verify_damage_estimate_move.py`** (Verhaltensneutralität der Schadensschätzung belegen) und
  **`verify_mark_wiring.py`** (Laufzeit-Sonde: kommt ein Controller wirklich in `main.py` an? Hat eine
  tote Verdrahtung gefunden, die keine Suite sehen kann).
- **`fetch_datasheet_rules.py` / `rules/*.md`** — der GEDRUCKTE Regeltext jedes Datenblatts als
  markdown, damit ein GW-Update per `git diff` sichtbar wird statt durch erneutes Lesen bei
  Wahapedia. Ausführlich unter `## Regeltext-Korpus` weiter unten;
  **`verify_rules_vs_engine.py`** stellt Korpus und Engine nebeneinander (ein BERICHT, keine Suite —
  die transkribierten Werte gewinnen per stehender Entscheidung).
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
- **map3 — "Crucible", 60"×44" Querformat mit ECKAUFSTELLUNG**, gebaut aus dem vom User gelieferten
  `Sprites/Map3.png` (2400×1760 px = exakt 40 px/Zoll). **Es ersetzt das alte 30"×30"-Testbrett**
  (User: "map3 ersetzen"); was daran hing, steht unten. 18 Footprints (9 gemessen, 9 gespiegelt),
  36 Features, 6 Objectives, 1.7 ms je Sichtlinienprüfung.
  - **Die Zonen sind QUADRANTEN MINUS EINER 9"-KREISSCHEIBE um die Brettmitte** — die erste Karte,
    deren Zonen gar keine Rechtecke sind, und der Grund, warum die Formen-Arbeit zuerst kam. Der
    Radius ist gemessen: 355 px in BEIDEN Zonen unabhängig, also 8.88" gegen die im Bild
    annotierten 9"; die Differenz ist die Strichbreite der gestrichelten Linie.
  - **Das Loch ist der Punkt der Karte:** die zwei mittleren Objectives stehen je in einem
    Quadranten, der sonst jemandem gehört, liegen aber IM Loch — und damit im Niemandsland.
  - **Vier der achtzehn Stücke stehen schräg** (37.1° und −52.5°, je ein Spiegelpaar) und werden
    AUCH SO gebaut. Die Begradigung, die map2 nötig hatte, ist kein Preis mehr.
  - **GEDREHT wird nur, was wirklich ein gedrehtes Rechteck IST**, und das ist eine
    User-Korrektur: die erste Messung gab jedem Stück sein MINIMALFLÄCHEN-Rechteck, was bei den
    zwei keilförmigen Mittelstücken einen langen schmalen Block DIAGONAL durch den Keil legte
    (57°) — das engste Rechteck um die Form, aber nicht die Form, als die man sie liest. Der User
    hat die richtigen Lagen als rote Rechtecke ins Bild gezeichnet, alle aufrecht. Unterschieden
    wird jetzt an der FÜLLUNG: ein echtes gedrehtes Rechteck füllt sein Minimalflächen-Rechteck
    (gemessen 102-103%), ein Keil zu zwei Dritteln (66%) — dort gewinnt das aufrechte Rechteck.
    **Gegenprobe: die Objective-Marker der Vorlage liegen bei (36.02, 20.16); die aufrechte
    Fassung trifft (35.87, 20.22), die diagonale lag 1.8" daneben.**
  - **Eine ganze Stückgruppe hatte die erste Messung ÜBERSEHEN** — die grünen Container sind ohne
    graue Grundfläche gezeichnet, und die Maske nahm nur Grau. Sie nimmt jetzt Grün und Gold als
    eigenständiges Terrain.
  - **Jedes Footprint ist EIN sauberes Rechteck** (User: "ignoriere unregelmäßigkeiten wie schutt.
    mache saubere rechtecke draus. und alle footprints sollen rechtecke sein"). Die Vorlage zeichnet
    unregelmäßigen Schutt über die Kanten hinaus; die Messung legt das Rechteck auf das Stück und
    verwirft den Überstand. **Deckungsprobe gegen die Bilddatei: 92% des gezeichneten Terrains
    abgedeckt, 87% der gebauten Fläche liegt auf gezeichnetem Terrain** — die Differenz IST der
    verworfene Schutt.
  - **180°-punktsymmetrisch wie map1 und map2**, also ist nur die Nordwest-Hälfte gemessen. Vor dem
    Schreiben geprüft: jedes gemessene Stück findet sein Spiegelbild auf 0.1" und 1.4°.
  - **Player 2 behält die LOW-Y-Ecke**, wie auf beiden anderen Karten, damit nichts sonst in der
    Szene wissen muss, welche Karte läuft. Die Vorlage tönt diese Ecke blau und die Engine zeichnet
    Player 1 blau — die gerenderten Farben stehen also andersherum als im Bild. Das ist eine
    Palette, kein Layout.
  - **Sie fieldet die ganze Armee**, wie map1 und map2. Damit hat `BattleMap.army_roster` KEINEN
    Nutzer mehr; der Mechanismus bleibt (ein Dict je Liste, `"{p}"` als Platzhalter für die
    Owner-Ziffer, aufgelöst in `roster_for(armies)`) und wird in `test_army_select.py` an einer
    eigens gebauten Karte geprüft statt an einer ausgelieferten.

**Was mit dem alten Testbrett verloren ging — und wohin es umgezogen ist.** Das 30"×30"-Brett war
kein nachgebautes Layout, sondern die gemeldeten Fehlergeometrien nebeneinander (3"-Korridor, nur
zur eigenen Kante offene Bucht, 5"-Tür, 7.2" offene Flanke) plus ein Zug in Sekunden. Drei
Suiten hingen an EIGENSCHAFTEN dieses Bretts, die die neue Karte nicht hat; alle drei sind
SYNTHETISCH neu gebaut statt gestrichen, damit die Abdeckung nicht an einer Karte hängt:
`test_home_garrison.py` (die einzige Karte, auf der beide Spieler VERSCHIEDENE Reichweite
brauchten — genau der Fall, den eine feste Zahl still verfehlt hätte), `test_secondary_missions.py`
(der Dedupe-Fall von `expansion_objectives()`, weil nur ein Nicht-Home-Objective existierte) und
`test_army_select.py` (der Roster-Mechanismus). Was wirklich weg ist: das schnelle kleine
Selbstspiel-Brett.

**Warum map2 begradigt wurde (historisch — seit Stufe 2 nicht mehr nötig):** ein `Obstacle` war
konstruktionsbedingt achsparallel, und
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

## Aufstellungszonen sind FORMEN (game/shapes.py, game/deployment.py)

**Stufe 1 der Karten-Geometrie-Arbeit** (User: "ja zonen müssen auch gedreht werden. sie haben
sogar spezielle shapes wie auf dem screenshot. mit einem kreis in der mitte. und bei schrägen oder
ecken-aufstellungszonen muss die map für die territories auch diagonal geteilt werden"). Terrain
ist noch achsparallel — das ist Stufe 2.

- **Eine Zone wird genau DREI Dinge gefragt, und alle drei sind dieselbe Distanzfrage.** Deshalb
  ist eine Form eine SIGNED DISTANCE (positiv innen, Betrag = Zoll zum Rand), und
  `contains_point` ist `sd >= 0`, `contains_circle` (03.01 "wholly within") ist `sd >= r`,
  `distance_to_point` (24.20 INFILTRATORS) ist `max(0, -sd)`. Eine neue Zonenform kostet damit
  **null Code** in `deployment.py`.
- **Primitiven:** `Rect(x, y, w, h, angle_deg)` (gedreht; `angle_deg=0` nimmt den alten Pfad),
  `HalfPlane` (+`through()` — die Primitive, die Diagonalen ÜBERHAUPT möglich macht, und vier
  davon sind ein gedrehtes Rechteck), `Disc`, `Outside(shape)` (der Kreis in der Mitte, als
  SUBTRAKTION geschrieben statt als `inside=False`-Flag), `Intersection`/`Union`.
- **Warum nicht weiter mit Rechtecken annähern — gemessen, und es ist der entscheidende Befund.**
  Beim Terrain kostete die Treppe 25% Mehrfläche (lebbar). Bei einer ZONE ist sie
  **nicht-monoton kaputt**, weil `contains_circle` verlangt, dass EIN EINZELNES Rechteck die ganze
  Base hält: an einer diagonalen Eckzone (44"×44") bleiben von der legalen Aufstellfläche bei
  4/8/16/32 Streifen für eine 25-mm-Base 101/95/71/**10** %, für 50 mm 96/76/22/**0** %, für einen
  Grav-Panzer 84/33/**0**/**0** %. Verfeinern macht es STRIKT SCHLECHTER, und der Kreis in der
  Mitte ist mit Rechtecken gar nicht darstellbar. Es gibt hier also keinen Rückfallplan.
- **Exaktheit steht pro Kombinator da, nicht als Annahme.** `Union` = `max()` reproduziert die
  alte Lesart BIT FÜR BIT (`max_i sd_i >= r` genau dann, wenn irgendein einzelnes Rechteck die
  ganze Base hält), Naht-Konservatismus inklusive. `Intersection` = `min()` ist innen exakt;
  AUSSERHALB einer ECKE meldet es die Distanz zur näheren Kanten-GERADEN statt zum Eckpunkt,
  unterschätzt also, wie weit draußen ein Punkt ist — was jeder Konsument als "näher an der Zone"
  liest und damit eine Platzierung ABLEHNT statt eine illegale zu erlauben. Sichere Richtung, im
  Test gepinnt.
- **Die dokumentierte Naht-Schwäche ist geschlossen**, aber nur für neue Formen: eine als
  Halbebenen-Schnitt geschriebene Zone hat keine Naht, an der ein Modell zu Unrecht abgelehnt
  würde. Als Rechteck-Union geschrieben bleibt sie bewusst wie bisher.
- **`.rects` ist ab jetzt die AUTOREN-EINGABE, nicht die Form.** Eine formgebaute Zone hat keine.
  Kein Produktivmodul liest es mehr (Quell-Wächter); Tests dürfen es weiter benutzen, um ein
  Modell an eine bekannte Stelle zu setzen.
- **`secondary_missions.zone_distance()` war eine ZWEITE Kopie von `distance_to_point()`**
  (Fehlerklasse 10, identische Arithmetik) und delegiert jetzt. Die beiden widersprachen sich nur
  im Leer-Zonen-Fall (0.0 gegen inf); `inf` gewinnt — eine leere Zone enthält nichts, also ist
  24.20 überall erfüllt statt nirgends. Kein Roster erreicht den Fall.

### Territorien: Mittelsenkrechte statt Achsen-Wahl

`in_own_territory()` leitete die Trennung schon immer aus den Zonen-Zentren ab, konnte aber nur
eine WAAGERECHTE oder SENKRECHTE Linie erzeugen. Jetzt: **mein Territorium ist jeder Punkt, der
meinem Zonen-Zentrum näher ist als dem gegnerischen.** Die Trennlinie dreht sich damit mit den
Zonen. **Verhaltensneutral, gemessen:** 201×201-Raster, drei Karten, beide Spieler, **0 von 40401
Punkten** wechseln die Seite — die ausgelieferten Zonen sind punktsymmetrisch zur Brettmitte, ihre
Mittelsenkrechte IST die alte Mittellinie. Drei Karten hängen dran (Beacon, Outflank, Plunder).
**Testfalle dabei:** die vier BRETTECKEN unterscheiden die zwei Regeln NICHT (bei symmetrischen
Eckzonen stimmen sie dort zufällig überein) — der Test muss Punkte nehmen, die auf verschiedenen
Seiten der Diagonale, aber derselben Seite der Mittellinie liegen.

### Renderer und Aufstellungs-KI ziehen mit

- **`renderer._shape_outline_segments()`** trägt den Umriss per MARCHING SQUARES aus der Signed
  Distance ab (0.25"-Raster, Kreuzungen linear interpoliert, damit ein Bogen glatt wird). Läuft
  auf der GECACHTEN statischen Ebene, also einmal pro Szene. **Eigener Fehler, der dabei auffiel:**
  ein Punkt auf der Grenze zählt als innen (`sd >= 0`), also findet das Verfahren am Rand der
  Bounding Box gar keinen Vorzeichenwechsel — der Umriss verschwand entlang jeder Kante, die bündig
  mit der Box liegt, also jeder Kante eines Rechtecks. Der Sampling-Bereich wird deshalb um zwei
  Zellen VERGRÖSSERT.
- **`renderer.own_board_edges()`** ist eine reine Funktion: eine Brettkante gehört der Zone, wenn
  ihre Außennormale in dieselbe Richtung zeigt wie "von der Brettmitte zu dieser Zone". Das
  verallgemeinert den alten Nord/Süd-Test und ist auf den drei Karten identisch — **das strikte
  `>` ist der Grund**: eine vollbreite Bande berührt West und Ost wirklich, aber deren Normalen
  stehen exakt SENKRECHT (Skalarprodukt 0) und fallen raus. Eine Eckzone behält beide Kanten.
- **Gemessen statt behauptet:** gegen die alte Zeichnung liegen 94% der alten Linie innerhalb von
  2 px der neuen und **0 neue Pixel** ohne Entsprechung; der Rest ist EINE Bildzeile des unteren
  Kanten-Bandes (jetzt symmetrisch zum oberen).
- **`deployment_ai` sampelt die FORM.** `sampling_boxes(inset)` liefert die Boxen, über die das
  Kandidatenraster gelegt wird — für ein achsparalleles Rechteck ist das EXAKT das alte Raster
  (Beweis im Docstring: `sd >= inset` heißt, die ganze Scheibe liegt drin, also liegt der Punkt
  mindestens `inset` von jeder Seite der Bounding Box), und `Union` gibt eine Box PRO TEIL, damit
  eine gestufte Zone weiter pro Rechteck gerastert wird.

### Drei eigene Fehler, alle erst von den Sonden gefunden

1. **Die Randlage kippte, und die erste A/B-Sonde sah es nicht.** 720 000 ZUFÄLLIGE Vergleiche
   meldeten 0 Abweichungen — aber das Kandidatenraster der KI setzt seine Punkte ABSICHTLICH exakt
   eine Basisbreite innerhalb der Kante, und dort rundet die Signed Distance anders als der
   Rechteck-Vergleich: **103 von 210** dieser Punkte kippten von legal auf illegal, also der ganze
   äußere Ring und damit die vorderste Reihe. `test_report_20260824.py` wurde dadurch rot.
   `PLACEMENT_TOLERANCE_IN = 1e-9` behebt es. **Fehlerklasse 16 in Reinform: eine Sonde, die die
   eine Lage nicht herstellt, auf die es ankommt, beweist nichts.**
2. `_zone_probe_points(zone)` OHNE Brettmaße (so rufen `measure_deployment_safety.py` und
   `smoke_pregame.py` es) klemmte die Box auf (0,0,0,0) und lieferte eine LEERE Probenliste — ein
   Default, der zwei Harnesses still entwertet hätte.
3. Der INFILTRATORS-/Kein-Zonen-Pfad in `_candidate_points` bekam den Inset nicht mehr, weil ich
   das rohe Brettrechteck übergab statt es durch `sampling_boxes()` zu schicken.

**Getestet:** neu `test_deployment_shapes.py` (**77/77**, acht Abschnitte) plus **sechs A/B-Sonden**
an der QUELLE, jede kippt genau ihre eigenen Prüfungen. **Drei Sonden bissen zuerst NICHT, und alle
drei waren Befunde über den TEST** (Eckpunkte, die beide Territoriums-Regeln gleich beantworten;
keine ausgelieferte Zone mit zwei Rechtecken, also lief `Union` nie; und ein reiner Quell-Wächter
statt eines Verhaltenstests für die Kantenwahl — deshalb ist `own_board_edges()` jetzt eine
extrahierte reine Funktion). Volle Regression **149 Suiten, ~11748 Prüfungen, 148 grün / 0 rot /
1 bekannt**, alle fünf Smokes, `measure_deployment_safety.py` auf beiden Karten PASS,
`measure_home_garrison.py` unverändert und `selfplay.py map2`.

## Terrain darf sich DREHEN (game/terrain.py, Stufe 2)

`Obstacle` nimmt jetzt `angle_deg`. Damit ist die Begradigungs-Entscheidung von map2 aufgehoben
— sie bleibt für map2 selbst bestehen (die Karte ist so vermessen und getestet), aber eine neue
Karte kann ihre Footprints tragen, wie sie gedruckt sind.

**Zwei Regeln machen das an einer Form sicher, die sechs Subsysteme lesen:**

1. **`min_x/max_x/min_y/max_y` sind die BOUNDING BOX des gedrehten Rechtecks**, nicht mehr die
   Form. Jeder VORFILTER (`line_of_sight._obstacle_relevant`, der A*-Reject) bleibt damit ohne
   jede Änderung korrekt, und alles, was den exakten Test noch nicht kennt, blockiert bloß etwas
   zu viel statt Unsinn zu antworten. Die Umstellung konnte also nicht auf halbem Weg brechen.
2. **Jede EXAKTE Frage beantwortet eine Methode am Hindernis**, im Eigenframe: `overlaps_circle`,
   `contains_point(inflate=)`, `blocks_segment`, `segment_clip`, `segment_entry_fraction`,
   `distance_to_point`, `corners`, `route_waypoints`. Aufrufer fragen das Hindernis, statt vier
   Zahlen an eine freie Funktion zu reichen — EINE Definition von „welche Form ist das" statt
   sechs. `segment_intersects_rect` hat im Produktivcode keinen Aufrufer mehr.

**`angle_deg=0.0` nimmt einen Fast Path, der die ALTE ARITHMETIK WÖRTLICH ist** — nicht die
allgemeine Formel spezialisiert. Das ist die Lehre aus Stufe 1: die beiden sind in exakter
Arithmetik gleich und runden am Rand verschieden, und genau daran ist dort ein ganzer Ring des
Aufstellungsrasters gestorben. Gemessen: über alle drei Karten, alle Hindernisse, inklusive der
Lagen exakt auf der Kante und exakt auf der aufgeblähten Kante — **keine einzige Antwort bewegt
sich um ein letztes Bit**.

- **Der gedrehte Pfad ist gegen BRUTE FORCE geprüft**, nicht gegen eine zweite Kopie derselben
  Formel: Punkt-in-Polygon, Abstand zum Polygonrand und Segment-Schnitt unabhängig nachgerechnet,
  neun Winkel, ~1000 Stichproben je Winkel, **0 Abweichungen**.
- **`route_waypoints()` liegt am Hindernis, weil `ai/agent_driver.py` das Ecken-Routing ZWEIMAL
  enthält.** Eine Drehung, die nur einer der beiden Kopien beigebracht wird, ist genau die Drift,
  die dieses Repo laufend konsolidiert. Die „slide past it"-Punkte werden im Eigenframe gebildet —
  „parallel zu seiner eigenen Kante" bedeutet in Brettachsen nichts, sobald das Stück schräg steht.
- **Der Renderer zeichnet ein POLYGON** (`obstacle_points_px()`), und die Kacheltextur läuft durch
  eine **Polygon-Maske**: `set_clip()` nimmt nur ein `Rect`, also werden die Kacheln auf eine
  Hilfsfläche gelegt und mit `BLEND_RGBA_MULT` maskiert. Die Kachelausrichtung bleibt am URSPRUNG
  DER ZIELFLÄCHE, sonst startet jedes Footprint sein Muster neu. Gemessen: gedrehte Wand belegt
  dieselbe Fläche wie dieselbe Wand gerade (±2%), aber eine mitgedrehte Bounding Box.

### Was Drehung kostet — gemessen, und die Alternative gleich mit

| map2, 500 Sichtlinienprüfungen | Kosten | Features |
|---|---|---|
| heute (begradigt) | 1.24 ms | 29 |
| **echte Drehung** | **1.70 ms (1.37x)** | 29 |
| Treppen-Näherung | 3.30 ms (2.66x) | 109 |

**Meine erste Schätzung von 1.08x war falsch** — sie maß die Transformation isoliert, nicht die
Aufrufkette. Ein Bounding-Box-Reject vor der Transformation bringt fast nichts, weil
`has_line_of_sight()` die Hindernisse ohnehin schon vorfiltert; er steht trotzdem da, weil er in
anderen Aufrufern greift. 1.70 ms liegt in derselben Größenordnung wie map1 heute (1.36 ms bei 43
Features). Die verworfene Treppe wäre mehr als doppelt so teuer gewesen — bei schlechteren
Footprints.

**Getestet:** neu `test_rotated_terrain.py` (**48/48**, fünf Abschnitte) plus **sieben A/B-Sonden**
an der QUELLE, jede kippt ihre eigenen Prüfungen (der Fallback des gedrehten Pfads auf die Bounding
Box kippt 14). **Der entscheidende Prüfbereich ist „innerhalb der Bounding Box, außerhalb des
Stücks"** — nur dort unterscheiden sich „frag das Hindernis" und „frag seine Box", und jeder
Konsument wird genau dort gemessen. **Eigener Testfehler dabei:** die ersten drei Proben lagen auf
der LÄNGSACHSE der Wand, wo Blockieren korrekt ist — sie bewiesen nichts, bis sie auf die wirklich
leeren Ecken der Bounding Box gerückt wurden.

Volle Regression **150 Suiten, ~11799 Prüfungen, 149 grün / 0 rot / 1 bekannt**, alle sechs Smokes,
`measure_deployment_safety.py` beide Karten PASS, `measure_crowded_movement.py` unverändert bei 65%.
**Im ECHTEN Spiel belegt:** alle drei Karten mit JEDEM Terrainstück gedreht durch die echte
`main()`-Schleife (`selfplay.py`, 1200-1800 Frames, exit 0) und `smoke_pregame.py` mit gedrehtem
Terrain (0 API-Calls, beide Deckungs-Schranken halten) — Aufstellung, A*, Sichtlinie,
Bewegungs-Clamp und Renderer laufen dort zusammen, was keine Suite prüfen kann.

### Drei Fehler, die erst die neue Karte sichtbar gemacht hat

Beide sind Folgen von Stufe 1, die auf einer Bandzonen-Karte nicht auftreten können — ein Beleg
dafür, dass eine Form-Erweiterung ihre eigenen Konsumenten erst mit einem echten Träger prüft.

1. **`Intersection.bounding_box()` gab `None`, obwohl vier Halbebenen sehr wohl begrenzen.** Jeder
   einzelne Teil ist unbegrenzt, also fiel `_combine_boxes()` auf None zurück, und jeder Konsument,
   der die Zone SAMPELT, wich aufs ganze Brett aus: die Expositions-Sonde der Aufstellungs-KI fand
   dann **null Punkte** in der Zone und maß still gar nichts. `HalfPlane.bounding_box()` liefert
   jetzt eine HALBUNENDLICHE Box, wenn ihre Kante achsparallel ist (eine schräge weiter `None` —
   eine größere Box ist immer sicher). **Vom Smoke gefangen, von keiner Suite.**
2. **`distance_to_point()` ist außerhalb einer ECKE bewusst konservativ — und
   `expansion_objectives()` RANKT damit.** Auf einer Eckzonen-Karte macht das aus 4.5" und 10.6"
   zwei gleiche Zahlen, der Gleichstand bricht über den Namen, und beide Spieler bekommen dasselbe
   Expansion-Objective. Die konservative Antwort BLEIBT, was die Regeln lesen (sie lehnt nur ab,
   erlaubt nie etwas Illegales); die eine Stelle, die vergleicht statt zu gaten, liest jetzt
   `DeploymentZone.true_distance_to_point()` — echte Euklid-Distanz, aus dem gecachten
   Stichprobenraster der Zone. **map1 und map2 antworten unverändert** (Southwest/Northeast bzw.
   East/West), map3 gibt jedem Spieler das Objective auf seiner Seite.

3. **Der gezeichnete Objective-Umriss kam noch aus der Bounding Box** (User: "die objective zonen
   müssen sich natürlich mit den gelände footprints decken. die müssen ebenfalls rotieren"). Die
   REGEL war schon richtig — 14.02 misst über `TerrainArea.overlaps_model()`, also die gedrehte
   Form —, aber das Bild versprach Boden, den die Regel nicht gibt. `renderer.objective_outline_points()`
   baut den Umriss jetzt aus den ECKEN der Features (jedes im Eigenframe um denselben Rand
   gewachsen, dann konvexe Hülle), und das „i"-Icon hängt an der obersten linken ECKE des Umrisses
   statt an der Box-Ecke — auf einem gedrehten Stück sind das verschiedene Punkte, und die
   Box-Ecke schwebt im freien Gelände. Achsparallele Flächen behalten den gerundeten Rahmen und
   weichen um höchstens 1 px ab.
   **Und darin steckte ein zweiter, feinerer Fehler:** die Wände einer Ruine sind um ihre halbe
   Dicke eingerückt, ihre Außenkante liegt also EXAKT auf der des Footprints — aber über einen
   anderen Rechenweg, also 7e-15 daneben. Das genügt, um zwei Punkte falsch herum zu sortieren:
   die Hülle startete an einer Wandecke und ließ eine echte Ecke fallen, ein Rechteck kam als
   Fünfeck heraus. Die Koordinaten werden vor der Hülle auf ein Millionstel Zoll eingerastet.

**map3 getestet:** neu `test_map3_crucible.py` (**101/101**, sechs Abschnitte) — Brett und Maßstab,
die Zonenform samt Loch und "passt eine Grav-Panzer-Base hinein" (386 sq.in, gegen 0 bei der
Treppen-Näherung), die Drehung samt mitdrehender Wände, die Symmetrie am GEBAUTEN Brett, die sechs
Objectives mit geprüften Himmelsrichtungen, was der Rest der Engine daraus liest, und der
Objective-Umriss an PIXELN gemessen (er muss enger sein als die Bounding Box, darf nicht
achsparallel sein, und der Rand muss auf allen vier Seiten gleich sein — als Flächenvergleich,
weil ein Punkt-zu-Ecke-Abstand kein Rand ist). Volle Regression **152 Suiten, ~12411 Prüfungen,
151 grün / 0 rot / 1 bekannt**, alle sieben Smokes (inkl. `smoke_pregame.py map3`) und
`selfplay.py` auf allen drei Karten.

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
- **Er trägt seit den Biomen auch DEREN drei Knöpfe** (ganz oben im Kopfzeilen-Balken, siehe
  `## Biome` unten) — sie gehören hierher, weil die Kacheln darunter Bilder des Bretts sind
  und ein Biom-Klick sie neu malt.
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

## Biome (game/biomes.py)

**Drei Biome — City, Desert, Forest — als drei Knöpfe ganz oben im Kartenauswahl-Screen** (User:
"ich habe die texturen für die maps in ordner geordnet. es gibt jetzt 3 biome. kannst du bei der map
auswahl bitte ganz oben noch 3 knöpfe reinpacken, über die man sein biom wählen kann?"). Ein Biom
sind genau DREI Bilder: der Boden plus die zwei Cover-Texturen, mit denen ein Terrain-Footprint
gefüllt wird.

- **REIN KOSMETISCH, und das ist gemessen statt angenommen.** Brettmaße, beide Zonen, jedes
  Terrainstück, jedes Objective sind unter allen drei Biomen identisch (im Test als Gleichheit der
  gebauten Szene gepinnt); nur das gerenderte Bild unterscheidet sich (als Hash der drei Karten unter
  drei Biomen: 9 von 9 verschieden). Beide Hälften zusammen, weil jede allein wertlos ist — ein Biom,
  das nichts ändert, ist ein toter Knopf; eines, das das Brett ändert, ist ein Fehler.
- **Das Verschieben in Ordner hatte alle drei Texturen TOT gemacht.** Gemessen vor der ersten
  Änderung: `ground_texture_path()`, `dense_cover_texture_path()` und `normal_cover_texture_path()`
  gaben ALLE `None` zurück, der Renderer war also still auf seine Flat-Color-Fallbacks
  zurückgefallen. Die drei festen Namen in `sprites.py` zeigten auf `Sprites/wüste-boden.jpg` &
  Co., die jetzt in `Sprites/Map Textures/<Biom>/` liegen.
- **Default ist `desert`, und der LOOKUP ist belegt verhaltensneutral:** die drei Dateien im
  Ordner `Dessert` sind BYTE-IDENTISCH mit den drei alten (per sha1 geprüft — `Ground_Desert.jpg`
  IST `wüste-boden.jpg`), und der über das Biom aufgelöste Pfad rendert auf allen drei Karten
  **pixelidentisch** zum direkt gereichten alten Pfad. Die Umstellung der AUFLÖSUNG ist damit
  unsichtbar. **Der Kachel-Blend-Fix darunter ist die eine bewusste Ausnahme** — er hellt jedes
  Terrain-Footprint auf, auch im Desert-Biom (Kontrast dort 80 → 43, weiterhin klar lesbar; im
  Bild geprüft, nicht nur gerechnet).
- **Die TABELLE entscheidet, die DATEINAMEN werden GEFUNDEN.** `BIOMES` trägt nur, was eine
  Entscheidung ist: welche Biome es gibt, wie sie auf dem Knopf HEISSEN und in welcher Reihenfolge.
  Keine Dateinamen — die drei gelieferten Ordner widersprechen sich schon untereinander
  (`Light_Cover-Desert.jpg` mit Bindestrich gegen `Light_Cover_City.jpg` mit Unterstrich), und der
  Desert-Ordner heißt **"Dessert"**, während jede Datei darin "Desert" sagt. Stehende Repo-Regel:
  **DER ORDNER GEWINNT** (wie bei den acht Necron- und vier T'au-Sprite-Namen), also wird die ROLLE
  über ihren Dateinamen-PRÄFIX gematcht (`Ground` / `Dense_Cover` / `Light_Cover`) statt neun Namen
  plus einen Tippfehler zu transkribieren. Ein viertes Biom kostet EINE Zeile plus den Ordner.
  Der ANZEIGENAME wird bewusst NICHT so abgeleitet — sonst stünde "DESSERT" auf dem Knopf.
- **Kein Dateisystem in `biomes.py`.** Es beantwortet "welche Biome / welches ist gewählt / welcher
  Ordner"; `sprites.py` beantwortet "und wo liegt dessen Bodenbild", weil dort `SPRITES_DIR` und
  `_EXTENSIONS` schon einmal definiert sind. Hält den Import einseitig (sprites → biomes).
- **`get()` wirft, `current()` nicht** — und das ist Absicht: `get()` ist die Tabellenabfrage
  (Tippfehler soll laut sein, wie `maps.get()`), `current()` läuft auf dem RENDER-Pfad bei jedem
  Neubau der statischen Ebene, wo ein veralteter Settings-Wert die Karte umfärben soll statt das
  Spiel mitten im Frame zu killen.
- **Die Knöpfe sitzen IM Kopfzeilen-Balken, nicht in einer eigenen Zeile darunter** — die
  Kartenvorschauen rechnen ihre Boxhöhe aus dem, was übrig bleibt, eine Zeile darüber würde also
  jedes Brettbild auf dem Schirm schrumpfen. Gemessen: die Überschrift endet bei 382 px, der Block
  ist rechtsbündig und hält selbst bei 1280 px Fensterbreite ~380 px Abstand.
  `tile_screen.header_bar()` ist die dafür extrahierte gemeinsame Rechteck-Definition (zweiter
  Konsument: `draw_header()` und das Hit-Testing im `layout()`).
- **Sie gehören auf DIESEN Screen, weil die Kacheln darunter Bilder des Bretts sind:** ein Klick
  malt alle drei neu, die Wahl wird also durch Hinsehen getroffen statt durch drei Wörter. Deshalb
  sind BEIDE Caches in `map_preview.py` nach `(Karte, Biom)` gekeyt — nach Karte allein täte der
  erste Klick sichtbar nichts.
- **`map_preview._render()` baut jetzt einen FRISCHEN `Renderer` pro Aufruf.** Der geteilte
  Modul-Renderer cacht seine statische Ebene unter einem Schlüssel, der mit `id(board)` beginnt —
  und `board` ist dort ein Local, das beim Verlassen Müll ist. Dieselbe Karte unter einem zweiten
  Biom kann also eine recycelte id bekommen, den Cache-Eintrag des VORIGEN Bioms treffen und den
  falschen Boden blitten. Echte Kollision (gleiche Karte → gleiche Pixelmaße) und probabilistisch,
  also die schlimmste Sorte.
- **Der Screen schreibt `config.BIOME` beim Klick**, und das ist NICHT die Regel, die
  `map_preview.py`s Docstring aufstellt: verboten ist, dass eine VORSCHAU die Brettmaße schreibt,
  also das Schlachtfeld allein durch Angesehenwerden entscheidet. Hier entscheidet nichts durchs
  Ansehen, nur durchs Klicken — und ein Biom entscheidet ohnehin nichts am Spiel. Live geschrieben
  ist außerdem das, was die Kacheln antworten lässt: es gibt EINE Antwort auf "welches Biom", keine
  gewählte und eine gezeichnete.
- **`--biome` überspringt den Kartenscreen NICHT** (anders als `--map`): `--map` beantwortet dessen
  Frage, ein Biom ist eine zweite, kosmetische Einstellung, die derselbe Screen mitträgt.
- **Der ausgewählte Knopf wird PRESSED gezeichnet** (`button_style`s Active-Palette) — ein
  Drei-Wege-Umschalter, bei dem immer einer an ist, und "pressed" ist genau der Zustand, den der
  geteilte Knopf dafür schon hat. Sonst hat nichts auf diesem Screen einen bleibenden Zustand, es
  kann also nicht mit Hover verwechselt werden.
- **Eine maskierte Kachel wurde ZWEIMAL geblendet — vorbestehender Renderer-Fehler, den erst die
  neue Kunst sichtbar gemacht hat** (User: "Light_Cover_City.jpg sieht man nicht"). Ein GEDREHTES
  Footprint lässt sich nicht per `set_clip()` beschneiden, seine Kacheln laufen deshalb über eine
  Hilfsfläche plus Polygonmaske — und dort wurde `TERRAIN_TILE_ALPHA` erst beim Blitten auf die
  transparente Hilfsfläche (also gegen deren SCHWARZ, was abdunkelt) und dann noch einmal beim
  Zurückblitten angewandt. Gemessen an einer 200-grauen Vollton-Kachel über 60-grauem Boden:
  **154 statt der beabsichtigten 170**, also 16 der 110 Kontrastpunkte verloren. Bei den
  Wüstentexturen jahrelang unsichtbar (Boden 231 gegen Cover 116/167); die City-Kunst liegt in der
  QUELLE nur ~27 Punkte auseinander, dort war es also mehr als die Hälfte. **Der Fix lässt `alpha`
  in der MASKE mitreiten** (Kacheln deckend auf die Hilfsfläche, Maskenpolygon mit `alpha` statt
  255) — ein Schritt, exakt die Arithmetik des Clip-Pfades. Gemessen am Brett: City-Light-Cover
  Kontrast **8.1 → 20.9**, Dense **3.5 → 11.1**. `tile.set_alpha()` wird jetzt pro Pfad EXPLIZIT
  gesetzt bzw. gelöscht, weil die Kachel-Surface zwischen allen Aufrufen desselben Pfades geteilt
  ist. Vier neue Prüfungen in `test_ground_texture.py`, A/B belegt (4 von 38 kippen, und die
  Meldung nennt die 154).
- **Mittlerer Farbabstand ist ein GROBER Näherungswert für "sieht man es"** — Forest-Light-Cover
  misst 6.0 und ist am Bildschirm trotzdem deutlich (dunkles Holz auf moosigem Boden: das MUSTER
  trägt, nicht die mittlere Helligkeit). Deshalb wurde jedes Biom auch angesehen und nicht nur
  gerechnet.
- **Das Log nennt Karte UND Biom in einer `[setup]`-Zeile** (`file_only`): die Karte ist aus den
  Terrain-Koordinaten rekonstruierbar, das Biom aus gar nichts — ohne die Zeile lässt sich ein
  Screenshot in einem Bericht keinem Lauf zuordnen.
- **Getestet:** neu `test_biomes.py` (**87/87**, fünf Abschnitte) plus **neun A/B-Sonden** an der
  QUELLE, jede kippt genau ihre eigenen Prüfungen; dazu vier Prüfungen und eine Sonde für den
  Blend-Fix in `test_ground_texture.py` (**38/38**, neutralisiert 34/38). **Zwei bissen zuerst
  NICHT, beide Fehlerklasse 24
  (Befund über den TEST):** die "der gewählte Knopf ist heller"-Prüfung mittelte über den ganzen
  Knopf und maß damit die TEXTMENGE ("DESERT" hat mehr Tinte als "CITY"), bestand also mit
  fest verdrahtetem `pressed=False`; und die "BIOME steht da"-Prüfung zählte die akzentfarbene
  Trennlinie am Balkenboden mit, die `draw_header()` über die volle Breite zieht. Beide messen jetzt
  einen textfreien HINTERGRUND-Punkt gegen `button_style`s Paletten-Konstanten bzw. nur das
  y-Band des Knopfes. `test_ground_texture.py` wurde zu Recht rot (seine Pins nannten die
  verschobenen Dateien) und ist nachgezogen; es fixiert jetzt ein Biom und prüft weiter nur die
  ZEICHENregeln. Volle Regression **153 Suiten, ~12797 Prüfungen, 152 grün / 0 rot / 1 bekannt**,
  alle sechs Smokes plus drei `--neutralize`-Gegenproben, und `selfplay.py map2` unter JEDEM der drei
  Biome (je 1500 Frames, exit 0).
- **Im ECHTEN Spiel belegt:** `smoke_setup_screens.py` klickt jetzt ZUERST einen Biom-Knopf und dann
  erst die Kartenkachel, durch `main()`s echte Schleife — `forest` gegen das per Default gesetzte
  `desert`, ein Bestehen kann also nicht von den Defaults kommen. Es prüft nicht nur die Einstellung,
  sondern **wo der Renderer sein Bodenbild wirklich herliest** (Ordner `Forest`), und dass der
  Biom-Klick den Screen NICHT beendet — genau das Risiko, zwei Arten von Knöpfen auf einen Screen zu
  legen. 11/11 → **13/13**; `--neutralize` weiterhin rot (0/13).

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
  **Das Detachment gehört zur LISTE und ist ein TUPEL** (`ArmyList.detachments`) — eine Armee kann
  mehrere gleichzeitig fielden und bezahlt jedes in Detachment Points; einen Auswahl-Screen gibt es
  bewusst nicht (siehe `## Detachments gehören zur LISTE`). `detachment_setting` ist von `ArmyList`
  auf den `Detachment`-Record gewandert.
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

- **Player 1 — Aeldari, 12 Einheiten, 1890 pts** (Default; die gelieferte Liste rechnet 1930, siehe
  Punktenotiz unten). 20 Listeneinträge, 74 Modelle. **SECHS** Attached Units (19.01): Farseer +
  Warlock Conclave in Guardian Defenders, Eldrad + Warlock Conclave in Storm Guardians, Jain Zar in
  Howling Banshees, Asurmen in Dire Avengers, Lhykhis in Warp Spiders, **Warlock Skyrunner in die
  Windriders**. Dazu Dark Reapers, Falcon, Rangers, Shining Spears, Striking Scorpions, Wraithguard.
  **Der Warlock Skyrunner steht NICHT MEHR ALLEIN** — seine LEADER-Zeile ist ein JOIN, der nur
  Windriders nennt, und der Shroud-Runner-Tausch hat ihm den einzigen Partner gebracht, den er
  haben kann (siehe den Revisions-Eintrag unten). Wie bei den zwei Warlock Conclaves nennt dieses
  JOIN seine EIGENE Grenze ("nicht mehr als eine WARLOCK SKYRUNNERS-Einheit je Einheit") statt
  19.01s Leader-Slot zu belegen.
  Die Shining Spears sind der einzige Eintrag mit Nicht-Waffen-**Gear** (das Shimmershield des
  Exarchen ist eine reine ERGÄNZUNG, also `Gear` statt `WargearOption` — die zwei Gear-Spalten der
  ARMY-Tabelle werden hier zum ersten Mal überhaupt benutzt).
- **Necrons — 15 Listeneinträge, 9 Einheiten, 68 Modelle, 2020 pts**, Awakened Dynasty. Default für
  Player 2 (`config.PLAYER2_ARMY = "necrons"`). **SECHS** Anbindungen: Overlord in die Lychguard,
  Technomancer in die Necron Warriors, je ein Plasmancer in jede der ZWEI Immortals-Einheiten
  (Gauss / Tesla), Skorpekh Lord in die Skorpekh Destroyers, Lokhust Lord in die Lokhust
  Destroyers. Nur der C'tan Shard steht allein — er hat als einziger Charakter dieser Liste gar
  keine LEADER-Zeile. Vollständig beschrieben im Necron-Abschnitt unter `## Fraktionen`.
- **T'au Empire — 21 Listeneinträge, 19 Einheiten, 94 Modelle, 2030 pts**, **Kauyon + Advanced
  Acquisition Cadre**. Die vom User am 2026-08-30 gelieferte Liste, die den wiederhergestellten
  Retaliation-Cadre-Roster vollständig ersetzt. Beschrieben in `## Die T'au-Liste (2026-08-30)`
  weiter unten; das Wichtigste hier: **die erste Liste überhaupt, die ZWEI Detachments gleichzeitig
  fieldet** (2 + 1 DP gegen ein Budget von 3), und **die einzige, die KEIN Enhancement kauft** — sie
  nennt keins.
  Zwei Anbindungen (User: "die Fireblades in die Breacher", "der ethereal ist solo"): je ein Cadre
  Fireblade in eine der zwei Breacher Teams, beide Paare in je einem Devilfish. Shadowsun und The
  Twin Lance stehen allein, weil ihre Datenblätter gar keine LEADER-Zeile drucken; der Ethereal,
  weil der User es so gesagt hat — er KÖNNTE führen, und der Test schreibt aus, welche Art von
  Alleinstand das jeweils ist.
- **Orks — 14 Einheiten, 103 Modelle, 1935 pts**. Attached: Warboss + Painboy im 20er-Boyz-Mob,
  Beastboss in Beast Snagga Boyz (im Kill Rig), Warboss in Mega Armour bei den Meganobz (im
  Battlewagon). Stormboyz und Deffkoptas in Reserve.
- **Death Guard — 16 Listeneinträge, 14 Einheiten nach zwei Anbindungen, 49 Modelle, 2020 pts**,
  Death Lord's Chosen. Die fünfte wählbare Liste; Defaults unverändert. Vollständig beschrieben im
  Death-Guard-Abschnitt unter `## Fraktionen`. **Mit ihr wird die Paginierung des Auswahl-Screens
  zum ersten Mal im echten Spiel scharf** (`MAX_TILES_PER_PAGE = 4`) — die Maschinerie war gebaut
  und getestet, aber bis dahin nur gegen eine künstliche Fünf-Listen-Registry gemessen.
- **Keine Liste ist gelöscht** — jedes Datenblatt, jede Fähigkeit und jedes Stratagem aller fünf
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

## Die T'au-Liste (2026-08-30)

**Der vom User gelieferte Roster ersetzt die wiederhergestellte Retaliation-Cadre-Liste
vollständig.** 21 Listeneinträge, **19 Einheiten** nach zwei Anbindungen, **94 Modelle**,
Engine-Summe **2030 pts** gegen die 1990 der Liste.

- **ZWEI Detachments gleichzeitig — die erste Liste im Repo, die das tut.** Kauyon (2 DP) +
  Advanced Acquisition Cadre (1 DP) = 3, exakt `DETACHMENT_POINT_BUDGET`. Damit hört die
  DP-Arithmetik auf, Theorie zu sein: sie war gebaut und getestet, aber jede Liste fieldete bis
  hierher genau ein Detachment. Die Tag-Regel erlaubt das Paar (verschiedene Tags), und
  `detachments.validate("tau")` ist leer.
- **KEIN Enhancement, und das ist eine Aussage über die Liste.** Siehe den Absatz in
  `## T'au-Detachment-Enhancements`: der Roster nennt keins, jeder Charakter steht zum Grundpreis,
  also ist `_TAU_LIST_ENHANCEMENTS` leer. Der Mechanismus wird weiter getestet — mit einer eigenen
  Tabelle statt über den Roster.
- **Zwei Anbindungen, beide vom User benannt** ("die Fireblades in die Breacher"): je ein Cadre
  Fireblade in eine der zwei Breacher Teams. **Drei Charaktere stehen allein, aus drei
  verschiedenen Gründen** — und der Test schreibt aus, welcher: der Ethereal per User-Vorgabe
  ("der ethereal ist solo"), obwohl er ein Breacher Team FÜHREN könnte; Commander Shadowsun und
  The Twin Lance, weil ihre Datenblätter gar keine LEADER-Zeile drucken (Shadowsun hat zusätzlich
  LONE OPERATIVE 12", also ist Alleinstand ihr vorgesehener Zustand).
- **Transporte: je ein Breacher-Paar in je einem Devilfish** — 11 von 12 T'AU-EMPIRE-INFANTRY-
  Kapazität. **Die Liste sagt das NICHT**; sie nennt zwei Devilfish und schweigt zu den Passagieren.
  Das ist die Lesart, die der User dem alten Roster ausdrücklich gegeben hat ("den fireblade zu den
  breachern im devilfish"), und die Breacher sind die einzige Einheit hier, deren Waffe (10"
  Pulse Blaster) ohne Transporter unbrauchbar ist. **Im Selbstspiel belegt**, dass der
  Vorspiel-Schritt darauf noch aufbaut statt ersetzt zu werden: die KI legt den Ethereal in
  Devilfish 1 dazu (12/12) und schickt Vespid und Twin Lance in die Reserve — Entscheidungen der
  Declare-Battle-Formations-Stufe, nicht der Liste.
- **Nichts wird in die Reserve deklariert.** Der alte Roster tat das für Coldstar + Starscythes,
  auf ausdrückliche Anweisung; diese Liste sagt dazu nichts, also entscheidet 03.01.

### Was der Roster an der Engine geändert hat

- **Der Stealth Shas'vre trägt den Fusion Blaster — und das war unbaubar.** Der gedruckte Text
  lautet *"2 MODELS can each have their burst cannon replaced with 1 fusion blaster"*; die
  `WargearOption` lag aber nur auf der Shas'ui-ZEILE, mit einem Kommentar, der genau das als
  Ermessensentscheidung auswies. Die Option sitzt jetzt auf BEIDEN Zeilen, was "2 models" sagt.
  **BENANNTE GRENZE:** eine `WargearOption` deckelt PRO ZEILE, also sind 1 (Shas'vre) + 2 (Shas'ui)
  = 3 erreichbar gegen einen gedruckten Deckel von 2 — dieselbe Form wie die Farstalker-Notiz. Die
  Liste fragt nur auf einer Zeile, kann die Lücke also nicht erreichen; **beide Tatsachen sind
  gemessen und gepinnt**, die Lücke inklusive.
- **Die Piranha ist auf zwei Drittel des Devilfish geschrumpft** (User: "die piranhas sind zu groß,
  die sollten in etwa nur 2/3 so groß sein wie devil fish"): `base_radius_in` 2.1 → **1.4**, also
  4.20" → 2.80" Durchmesser. **Beide Datenblätter DRUCKEN dieselbe 60-mm-Flugbase**, die 2.1 war
  also treu — was sie nicht abbildet, ist dass eine Piranha ein Bruchteil des Rumpfes eines
  Devilfish ist. Fünfte Tischgrößen-Entscheidung nach Falcon, Wave Serpent, Defiler und den drei
  MOUNTED-Jetbikes. **Eine GAMEPLAY-Zahl**, keine kosmetische: `edge_distance()` liest den Radius,
  also ziehen Engagement Range, Überlappung, Kohärenz und Formations-Packen mit — die gewünschte
  Richtung, weil eine Piranha auf einem Devilfish-Fußabdruck genau die Form ist, mit der dieses
  Gelände am schlechtesten umgeht. Im Test gegen den DEVILFISH gepinnt statt gegen ein Literal:
  ein Verhältnis, das zweimal als Zahl dasteht, driftet.
- **map3s T'au-Teilroster nannte zwei Einheiten, die es nicht mehr gibt** und hätte sie still nicht
  gefieldet (`fields()` matcht EXAKT). Ersetzt nach der Begründung der Slots, nicht nach
  Namensähnlichkeit: Strike Team → **Pathfinder Team 1** (zehn Modelle auf denselben 1.26"-Basen,
  INFANTERIE, kein Transporter — ein exakter geometrischer Ersatz), Crisis Sunforges + Farsight →
  **Broadside Battlesuits 1** (2.36", quert kein Dense-Gelände, also genau das, wonach
  `_needs_open_ground()` fragt; die Sunforges waren 1.96" und ebenfalls VEHICLE).
- **Punkte: zehn von 21 Einträgen weichen ab, weiter in BEIDE Richtungen** (Engine 2030, Liste
  1990). Sieben Datenblätter sind beteiligt, drei davon doppelt gefieldet: The Twin Lance 220/185,
  Devilfish 75/85, Kroot Hounds 45/40, Pathfinder Team 85/90, Piranhas 65/60, Riptide 215/200,
  Vespid 70/65. Elf stimmen exakt, darunter die zwei, die am leichtesten danebengingen: die
  Broadside-Trias mit 270 (255 für drei plus 5 je High-yield Missile Pods) und beide Stealth-Teams
  mit 100. Die Transkription gewinnt unverändert.
- **`config.BATTLE_SIZE`s Notiz nannte "Player 1 ist 1535 pts"** — eine Zahl, die seit dem
  Aeldari-Tausch keinem Spieler mehr gehörte und mit diesem Tausch auch keiner Liste. Sie nennt
  jetzt die SPANNE aller fünf Listen (1890 bis 2030), was das Strike-Force-Argument trägt, ohne an
  einer einzelnen Liste zu hängen.

**Getestet:** neu `test_tau_army.py` (**138/138**, sieben Abschnitte) — jeder Listeneintrag Modell
für Modell und Waffe für Waffe, die drei Arten von Alleinstand, die Stealth-Grenze in beide
Richtungen, das Piranha-Verhältnis gegen den Devilfish, die Detachment-Arithmetik, "kein
Enhancement" von beiden Seiten, und die Totals **beim ECHTEN Builder erfragt** statt von Hand
nachgebaut (Fehlerklasse 17, die `test_player1_army.py` zweimal getroffen hat). Vier fremde Suiten
wurden zu Recht rot und sind nachgezogen: `test_army_select.py` (die Kachel-Zahlen und map3s
Roster), `test_detachments.py` (es pinnte "tau fieldet Retaliation Cadre" — jetzt zwei),
`test_take_to_the_skies_policy.py` (Shadowsun, ein zweites Stealth-Team und die Vespid hören auf,
21.03 zu deklarieren; die Crisis Battlesuits, für die der Pin geschrieben war, sind aus jedem
Roster verschwunden, also nennt er jetzt den Riptide) und `test_tau_vehicles.py` (die Piranha ist
der eine Grav-Panzer, der NICHT mehr die Devilfish-Größe hat). Volle Regression **139 Suiten,
~10244 Prüfungen, 138 grün / 0 rot / 1 bekannt**, alle fünf Smokes und `selfplay.py map2` mit T'au
auf BEIDEN Seiten (3000 Frames, exit 0). `smoke_pregame.py` mit T'au als KI scheitert weiter an
seiner dritten Schranke — die dokumentierte Prämissen-Lücke, siehe die offenen Punkte.

## Detachments gehören zur LISTE (game/detachments.py)

**Ein Detachment ist Teil der aufgeschriebenen Armeeliste, keine Wahl am Tisch** (User: "das
detachment ist fest mit den listen verbunden. man kann sein detachment vor dem spiel nicht einfach
ändern. das detachment gehört zur liste mit dazu und muss dort auch auftauchen"). Ein
Auswahl-Screen war gebaut und ist **wieder ausgebaut** — der Fehler war, "welche Liste" und
"welches Detachment" als zwei Fragen zu zwei Zeitpunkten zu behandeln, während die zweite Teil der
Antwort auf die erste ist.

Was davon BLEIBT und der Grund, warum das Modul überhaupt existiert: ein Detachment ist aus den
Einheiten NICHT ableitbar (ein Crisis-Suit sieht in jedem Detachment gleich aus). Die Liste
deklariert es also, und `apply_to_config(armies)` schreibt diese Deklaration in die
`config`-Konstanten, die die Regeln lesen.

- **MEHRERE gleichzeitig, bezahlt in DETACHMENT POINTS.** `ArmyList.detachments` ist ein TUPEL.
  Jedes Detachment kostet seine gedruckten DP (die "2DP" an seiner Wahapedia-Überschrift, jetzt auf
  dem `Detachment`-Record), und sie kommen aus EINEM Budget: Kauyon (2) + Advanced Acquisition
  Cadre (1) ist ein legales Paar, Mont'ka (3) + Kauyon (2) nicht.
- **Die KOSTEN sind transkribiert, das BUDGET ist eine ANNAHME** — und das steht im Modul.
  Keine geholte Seite nennt eins; "Detachment Points" kommt im ganzen Korpus null mal vor (er
  trägt Datenblätter, Armeeregeln und Detachments, aber keine Kernregeln). **3 ist die
  User-Entscheidung**, gewählt weil die teuersten Einzel-Detachments genau so viel kosten und weil
  das gelieferte Beispiel (Kauyon + AAC) genau darauf kommt. `DETACHMENT_POINT_BUDGET` ist die eine
  Stelle, die sich ändert, sobald die gedruckte Zahl auftaucht. **Im Test gegen den Korpus
  belegt**, dass dort wirklich nichts steht — statt es nur zu behaupten.
- **Die TAG-Regel ist eine ZWEITE, unabhängige Beschränkung** und sie IST transkribiert: "cannot be
  taken with another BATTLESUIT/AUXILIARIES detachment". Zwei 1-DP-Detachments mit demselben Tag
  sind zusammen illegal, obwohl 1+1 ins Budget passt. Genau die zwei Klauseln lagen seit dem
  Regel-Nachzug als "belegte No-ops" herum, weil ein Spieler nur ein Detachment hatte — jetzt sind
  sie scharf. **T'au druckt je einen Tag genau einmal**, die Regel kann auf den echten Daten also
  nicht beißen; der Test misst sie, indem er einem zweiten Detachment denselben Tag gibt — was ein
  künftiges genau so täte.
- **`validate(army_key)` gibt GRÜNDE zurück, keine Bool** — dieselbe Form wie
  `attached_units.can_attach()`: unbekannter Name, kein Detachment, über Budget, doppelter Tag.
  Ein Tippfehler in `ARMY_LISTS` soll als benanntes Problem auftauchen und nicht als
  Detachment-Regel, die still nie feuert.
- **`game/detachments.py` ist weiter der EINE Schreiber** der Settings, jetzt mit genau einem
  Aufrufer (`army_lists.apply_to_config()`). Von Grund auf gesetzt, sonst hielte ein Spieler zwei
  Detachment-Regeln gleichzeitig.
- **Der Screen ist weg**: `game/ui/detachment_select.py` gelöscht, `config.DETACHMENT_SELECT`,
  `PLAYER1_DETACHMENT`/`PLAYER2_DETACHMENT` und `--detach1/--detach2/--no-detachment-select`
  entfernt, die sechs Harness-Opt-outs ebenso (es gibt nichts mehr abzuschalten), und
  `scene_io.detachments_in()` entfällt — der Snapshot nennt die ARMEEN, und die implizieren die
  Detachments. Ein Test hält fest, dass all das WEG BLEIBT. Mit dem Screen ist auch
  `detachments.configured_choices()` gefallen: es existierte NUR, um seine Kacheln zu füllen,
  und stand danach mit null Aufrufern da — dieselbe Behandlung wie der tote Zweig in
  `battle_round_in()`.
- **Die Armeekachel zeigt sie**, weil sie sonst nirgends stehen: `detachment_summary(entry)` gibt
  "Kauyon + Advanced Acquisition Cadre (3 DP)". EINE Funktion, damit Kopfzeile und Kachel sich
  nicht widersprechen können.
- **Sieben fremde Suiten wurden dabei zu Recht rot** und deklarieren jetzt ihre Vorbedingung: die
  T'au-Stratagem-Tests liefen darauf, dass `RETALIATION_CADRE_PLAYERS` per Default BEIDE Spieler
  enthielt. Das ist jetzt leer — niemand hält ein T'au-Detachment, bis eine T'au-Liste gewählt ist
  —, also setzen die Suiten es selbst, wie `test_death_guard_stratagems.py`s `detachment_on` es
  vormacht.
- **Getestet:** neu `test_detachments.py` (**103/103**, sechs Abschnitte; ersetzt
  `test_detachment_select.py`) plus A/B-Sonden auf Budget und Gating. Volle Regression
  **138 Suiten, ~10101 Prüfungen, 137 grün / 0 rot / 1 bekannt**, alle fünf Smokes (inkl.
  `smoke_setup_screens.py --neutralize` weiterhin rot) und `selfplay.py` — auch mit einer
  T'au-Liste, die Kauyon UND Advanced Acquisition Cadre fieldet, beide gleichzeitig aktiv.

## T'au-Detachment-Regeln: Kauyon und Mont'ka

**Zwei Detachments, EIN Mechanismus** — deshalb gemeinsam gebaut und gemeinsam getestet:
Rundenfenster + armeeweiter Keyword-Grant auf Fernkampfwaffen + eine zweite Klausel, die nur
für einen *Guided*-Angriff gilt.

| | Runden | Grant | Zweite Klausel (nur Guided) |
|---|---|---|---|
| **Kauyon** (Patient Hunter) | 3-5 | [SUSTAINED HITS 1] | Trefferwurf-Modifikatoren ignorieren |
| **Mont'ka** (Killing Blow) | 1-3 | [ASSAULT] | [LETHAL HITS] |

- **`game/tau_detachments.py` ist die Extraktion am ZWEITEN Konsumenten**, wie die Konvention es
  verlangt: `is_tau_unit()`, `has_detachment(player, setting)`, `battle_round_in()`,
  `doctrine_active()`, `is_guided_attack()`. **`is_tau_unit` ist dabei eine Umbenennung in
  Verkleidung** — es lag in `retaliation_cadre.py`, einem DETACHMENT-Modul, beantwortet aber eine
  FRAKTIONS-Frage. Mit einem Detachment war das harmlos, mit sechs ist es genau der lügende Name
  (Fehlerklasse 11). `retaliation_cadre.py` re-exportiert es jetzt, es gibt also weiter EINE
  Definition (im Test daran gepinnt, dass es dasselbe Objekt ist).
- **Die zwei Hälften hängen an ZWEI verschiedenen Nähten, und das ist der Punkt.** Beide
  Keyword-Grants gehören in `_adjusted_weapon()` — und zwar dorthin und nicht in den Wundschritt,
  weil `_crit_note()` zur WURFZEIT wissen muss, ob ein kritischer Würfel ein Sustained- oder
  Lethal-Würfel ist. Kauyons zweite Hälfte gewährt gar kein Keyword, sie ENTFERNT Modifikatoren,
  also sitzt sie in `_hit_modifiers()`.
- **Kauyons "you can ignore any or all" wird AUTOMATISCH aufgelöst**, und das ist kein
  Kurzschluss: der Wortlaut ist wörtlich der von 24.29 [PSYCHIC] und
  `UnitProfile.ignores_hit_modifiers`, und beide bestehenden Filter tun dasselbe — verschlechternde
  Modifikatoren fallen, verbessernde bleiben. Es gibt keine Brettlage, in der man einen
  verschlechternden behalten will, also wäre ein Prompt je Angriff Fehlerklasse 5. **Gemessen durch
  den ECHTEN Controller**: mit Kauyon+Guided in Runde 4 fällt das `+1 Suppressed` und das
  `-1 For the Greater Good (Guided)` bleibt.
- **Der Grant WERTET NIE AB.** "have the [SUSTAINED HITS 1] ability" GEWÄHRT die Fähigkeit, es
  SETZT den Wert nicht — eine Waffe mit gedruckten [SUSTAINED HITS 2] behält ihre 2, und eine mit
  einer Würfel-Notation (D3) wird gar nicht angefasst. Dieselben zwei Wächter wie
  `game/ritual_butchery.py`, das dasselbe Keyword gewährt.
- **Mont'kas zweite Klausel ist enger, als sie aussieht.** "while a unit is a Guided unit, its
  ranged weapons have [LETHAL HITS]" liest sich als Eigenschaft der EINHEIT; die Armeeregel
  definiert Guided aber als *"while targeting one or more Spotted units"*, es ist also eine
  Eigenschaft des ANGRIFFS. Dieselbe Einheit auf ein zweites, unmarkiertes Ziel hat es nicht.
  Eigene Testzeile, weil die Einheits-Lesart isoliert völlig plausibel wirkt.
- **Runde 3 liegt in BEIDEN Fenstern** — gepinnt, weil ein Test, der nur Runde 1 und Runde 4
  prüft, mit einem um eine Runde falsch geschriebenen Fenster bestünde.
- **Jedes liest seine EIGENE Config-Konstante**, und der Test prüft zusätzlich, dass diese
  Konstanten wirklich zu denen gehören, die `game/detachments.py` schreibt — eine Regel, die auf
  eine Konstante hört, die niemand schreibt, wäre inert und sähe von innen richtig aus.
- **Kein KI-Pfad** (stehende T'au-Vorgabe), als Negativraum geprüft: `ai/agent_driver.py` erwähnt
  weder `kauyon` noch `montka`. Ebenso ist geprüft, dass BEIDE die Fight-Phase NICHT erreichen —
  beide Regeln sagen "ranged weapons".
- **Ein toter Zweig wurde von der eigenen A/B-Sonde gefunden und entfernt:** `battle_round_in()`
  hatte ein `if turn_tracker is None: return False`, dessen Löschung keine einzige Antwort
  änderte — `getattr(None, "battle_round", None)` ist bereits None, und None ist nie eine der
  gedruckten Runden. Ein Zweig, den kein Input erreicht, wird irgendwann fälschlich für tragend
  gehalten; der Docstring hält jetzt fest, warum der Default genügt.
- **Getestet:** neu `test_tau_doctrines.py` (**73/73**, sieben Abschnitte) plus **acht A/B-Sonden**
  an der QUELLE — sieben kippen ihre eigenen Prüfungen (Grant aus der Kette → 1-2 rot,
  Modifikator-Klausel aus `_hit_modifiers` → 2 rot, Mont'ka ohne Ziel → 1 rot, No-Downgrade-Wächter
  weg → 1 rot, Ranged-Check weg → 1 rot, `is_tau_unit` entschärft → 1 rot), die achte war der
  Befund über den toten Zweig oben. Volle Regression **135 Suiten, ~9425 Prüfungen, 134 grün /
  0 rot / 1 bekannt**, alle fünf Smokes, und `selfplay.py` mit T'au auf beiden Seiten unter ZWEI
  verschiedenen Detachments (3500 Frames).

### Nebenbefund: das Spiel konnte gar nicht schießen (vorbestehend, behoben)

`KrootPackmatesController` stand in `main()`s `shooting_target_reactions`, implementierte aber nur
`on_targets_selected()` — dessen Docstring behauptete, DAS sei
*"ShootingController.target_reactions' contract"*. Der echte Vertrag ist
`maybe_offer(attacking_squad, target_squad, melee=False)`. **Jedes Spiel starb mit
`AttributeError`, sobald irgendeine Einheit ein Schussziel wählte** — fraktionsunabhängig, weil die
Reaktionsliste bedingungslos durchlaufen wird.

- **Nicht dieser Arbeit zuzuordnen, A/B belegt:** mit der kompletten Etappe-2-Verdrahtung aus
  `shooting.py` entfernt stürzt es identisch ab, und auch mit den Default-Armeen auf map3.
- Warum keine Suite das sah: keine treibt `main()`s Tupel, und die MockAgent-Selbstspielläufe
  erreichen selten eine Schussphase (in CLAUDE.md als bekannte Grenze vermerkt).
- **Ein Kommentar, der einen Vertrag behauptet, den kein Code einlöst** — dieselbe Klasse wie der
  nie gefütterte `VengefulStarsController` und Path of the Outcasts fehlende Würfelbestätigung.
- **Der Wächter gegen die KLASSE** ist neu: `test_event_chain_wiring.py` Abschnitt 5 löst per AST
  die in beiden Reaktions-Tupeln genannten Variablen zu ihren KLASSEN auf und verlangt von jeder
  `maybe_offer`. A/B belegt (Methode entfernt → genau diese Zeile rot), plus ein Live-Wächter, der
  verhindert, dass der Abschnitt durch Nichtstun besteht.

## Die drei übrigen T'au-Detachment-Regeln

Anders als Kauyon/Mont'ka haben diese drei nichts miteinander gemein — jede hängt an einer anderen
Naht, und genau das ist der Inhalt.

### Experimental Prototype Cadre — Superior Craftsmanship

*"Friendly BATTLESUIT CHARACTER units' ranged attacks have +6" Range."*

- **Dritte Quelle in `game/weapon_range.py`**, nach der Pulse Accelerator Drone und Fuegans Burning
  Lance. Genau dafür wurde das Modul extrahiert, und der Gewinn ist nicht Kosmetik: die Regel
  erreicht damit ALLE DREI Reichweitenfragen, also auch die zwei HALBdistanzen ([MELTA X],
  [RAPID FIRE X]). **Gemessen an Commander Shadowsun**: Fusion Blaster 18" → 24", Melta-Halbdistanz
  **9" → 12"**. Das ist kein hypothetischer Fall — drei T'au-CHARAKTER-Battlesuits tragen [MELTA]
  (Shadowsun, Enforcer per Option, The Twin Lance).
- **Nimmt das MODELL, nicht das Squad** — dieselbe Begründung, die beide Geschwister ausschreiben:
  `game/shooting.py` misst pro Schütze auf dem heißen Pfad, und ein Modell ohne Squad fällt auf
  "kein Bonus" zurück statt zu werfen. Der im Plan erwogene `squad=`-Parameter war damit unnötig.
- **"BATTLESUIT CHARACTER units" läuft über 19.03**: zwei getrennte Any-Model-Fragen, nicht "gibt es
  ein Modell, das beides ist" — das ist, was Keyword-Pooling bedeutet. Der gedruckte Text sagt
  **units**, also bekommen die Bodyguards einer angebundenen Commander-Einheit die +6" mit. Eigene
  Testzeile, weil es wie ein Versehen aussieht, bis man nachsieht, welches Substantiv dasteht.
- Die zweite Textzeile ("nicht mit einem anderen BATTLESUIT-Detachment") ist ein **belegter No-op**
  — ein Spieler fieldet hier per Konstruktion genau ein Detachment.

### Advanced Acquisition Cadre — Expert Fieldcraft

*"In your Shooting phase, when a friendly PATHFINDER TEAM/STEALTH BATTLESUITS unit is selected to
shoot, those ranged attacks do not prevent your unit from being hidden."*

- **Ein Loch in EINER Buchführung, kein neuer Zustand.** Hidden (13.09) entscheidet sich an
  `last_ranged_attack_turn`, und die Regel ist schlicht "für diese Einheiten nicht schreiben".
- **Die Unterdrückung sitzt IM Trichter** (`_note_ranged_attack()`), nicht an seinen Aufrufern —
  der hat ZWEI, und dessen eigener Docstring hält den Fehler fest, der das gelehrt hat (`cancel()`
  übersprang die Buchführung, also blieb "Hauptwaffe feuern, Pistole lassen, Next Phase" dauerhaft
  hidden). Eine Regel, die nur den normalen Weg gated, wäre exakt die HÄLFTE dieses Fehlers.
- **"In YOUR Shooting phase" schließt reaktives Feuer aus**: Fire Overwatch (15.08/15.09) läuft im
  Gegnerzug, also nimmt so ein Schuss Hidden weiterhin weg. `shooting.py` führt diese Unterscheidung
  schon als `_reactive`; das Flag wird ÜBERGEBEN, damit die Lesart beim Regelmodul bleibt.
- **"STEALTH BATTLESUITS" wird als Keyword STEALTH gelesen** — gemessen trägt es genau ein
  Datenblatt, Keyword und benanntes Datenblatt sind hier also dieselbe Menge (im Test gepinnt, weil
  ein zweites STEALTH-Datenblatt die Regel still verbreitern würde).

### Auxiliary Cadre — Integrated Command Structure

Zwei Fähigkeiten, zwei Nähte.

- **Harnessed Alien Instincts ist die FÜNFTE Feindmarke** dieser Engine (nach Guide, Doom,
  Whispering Web, Advanced Scouting) und wie sie pro Spieler im Controller gehalten, weil sie dem
  GEGNER der markierten Einheit gehört. Form nach `game/whispering_web.py`.
  - **Die Richtung von "+3" detection range" ist ausgeschrieben, weil sie sich umdrehen lässt:**
    Detection Range gehört in dieser Engine dem VERSTECKTEN Modell (`is_detectable()` fragt, ob ein
    Beobachter innerhalb der Reichweite des versteckten Modells steht). Einem prey-marked FEIND +3"
    zu geben macht ihn also von WEITER WEG sichtbar — eine Strafe, was Beutemarkierung auch sein
    soll. Andersherum gelesen würde sie den Feind schützen.
    **Gemessen in beiden Bändern:** 15" → 18" im Normalfall, und 12" → 15" unter der
    Hauswand-Hausregel. Beide, weil ein Bonus, der nur eines bewegt, nur in Deckung wirkte.
  - **Sie beißt nur, solange die Einheit HIDDEN ist** — `is_detectable()` kürzt für alles andere
    auf True ab. Eine sichtbare Einheit zu markieren ist legal und tut nichts, was der gedruckte
    Text auch erlaubt.
  - **DAUER: eine ENTSCHEIDUNG, keine Transkription.** Der gedruckte Text nennt KEINE Dauer.
    User-Entscheidung auf Nachfrage: **bis zum Ende des Zuges** — dieselbe Lebensdauer, die die vier
    bestehenden Marken schon haben, damit es EINE Geschichte darüber gibt, wie lange eine Marke lebt.
  - **ZWEI Lebensdauern, getrennt gelöscht**: die Marke ist zug-, das Einmal-pro-Einheit-Memo
    phasengebunden. In einen Reset gefaltet würde die Marke still auf eine Phase verkürzt (A/B
    belegt).
  - **Angeboten am ANFANG der Schussphase**, weil der Text "IN your Shooting phase" sagt und nicht
    "nachdem diese Einheit geschossen hat" — eine Einheit, die nie feuert, darf trotzdem markieren.
    Derselbe Moment, in dem For The Greater Good seine Observer wählt. Gemessen an der
    vordefinierten T'au-Liste: **eine** KROOT-Einheit, also ein Prompt pro Schussphase, kein Genörgel.
- **Localised Stealth Projectors ist der ZWEITE Konsument** derselben Frage wie Expert Fieldcraft
  ("verhindert das Schießen dieser Einheit ihr Hidden?"), nur über eine Aura statt über ein Keyword
  → **`game/hidden_after_shooting.py`**, benannt nach der FRAGE statt nach einem Detachment, damit
  nicht wieder ein Modul den Namen der zuerst angekommenen Fähigkeit trägt. `shooting.py` stellt
  seither EINE Frage, und eine dritte Quelle ändert dort nichts.
- **Zwei eigene Fehler, beide vom Werkzeug gefunden:**
  1. Der AST-Wächter in `test_event_chain_wiring.py` fing ein `obstacles`, das in `main()` gar nicht
     gebunden ist (es heißt `state.obstacles`) — **und `selfplay.py` lief davor trotzdem sauber
     durch**, weil das Lambda nur feuert, wenn eine Kroot-Einheit markiert. Genau die Klasse, für
     die dieser Wächter existiert.
  2. `_squads()` las `game_state.tokens` (eine Liste pro MODELL) ohne Dedupe, also stand eine
     10-Modell-Einheit zehnmal in `eligible_units()`.
- **Zwei A/B-Sonden bissen zuerst NICHT, beide ein Befund über die SONDE bzw. den TEST**: der
  Strike-Team-Gegenfall stand außerhalb der Aura, scheiterte also aus dem falschen Grund (dieselbe
  Falle wie zweimal in der Kroot/Vespid-Etappe), und die Dedupe-Sonde stellte gar nicht die
  Vor-Fix-Welt her — ein Dict dedupliziert von selbst, die echte Vorfassung war eine LISTE.

**Getestet:** neu `test_tau_detachment_rules.py` (**102/102**, drei Abschnitte) plus **13 A/B-Sonden**
an der QUELLE (6 für Etappe 3/4, 7 für Etappe 5), jede kippt ihre eigenen Prüfungen. Volle
Regression **136 Suiten, ~9526 Prüfungen, 135 grün / 0 rot / 1 bekannt**, alle fünf Smokes, und je
ein echter `selfplay.py`-Lauf unter JEDEM der drei Detachments. **Kein KI-Pfad** (stehende
T'au-Vorgabe), als Negativraum geprüft.

## T'au-Detachment-Stratagems

**19 Stratagems über die fünf neuen Detachments** (Kauyon 6, Mont'ka 6, Advanced Acquisition 3,
Auxiliary 3, Experimental Prototype 1). Der gedruckte WHEN/TARGET/EFFECT-Text aller 19 liegt seit
Etappe 0 in `rules/tau_empire/detachments/*.md`.

### `game/proactive_stratagems.py` — EIN Panel-Parameter statt neunzehn

**Die wichtigste Entscheidung dieser Etappe, und sie ist eine Vermeidung.** `ActionPanel.draw()`
nimmt schon vierzig Controller entgegen, durch eine DREISTUFIGE Kette, die über weite Strecken
POSITIONELL ist — die Datei trägt die Narbe genau dieses Fehlers (ein Parameter in zwei von drei
Signaturen ergänzt, Absturz in jedem Frame). Neunzehn weitere Parameter wären neunzehn Gelegenheiten
für denselben Fehler, und das nächste Detachment machte zwanzig daraus.

Das Panel bekommt deshalb EINE Liste. Ein Controller tritt ihr bei, indem er drei Methoden anbietet
(`can_use(squad)`, `use(squad)`, `panel_label(squad)`) — **das Panel braucht dafür keine Änderung
mehr**. Der Phasen-Gate liegt wie bei jedem bestehenden Stratagem in `can_use()`, also rendert EINE
Schleife die richtigen Knöpfe in der richtigen Phase, ohne dass das Panel wüsste, welche Phase wozu
gehört. Bewusst KEINE Basisklasse: geteilt ist nur die FORM des Aufrufs, nicht Verhalten — eine
Vererbungswurzel würde einladen, eine Regel hineinzulegen.

### Etappe 6 — die ersten vier

- **Experimental Ammunition** (EPC, 1CP): "+1 S" **ODER** "+1 S, AP und [HAZARDOUS]". Das "OR" ist
  eine echte Wahl mit Nachteil ([HAZARDOUS] kann den Träger töten), also **zwei Panel-Knöpfe statt
  Knopf plus Folge-Prompt** — dieselbe Begründung, die `unmodified_six_controller.py` für Command
  Re-roll festhält. **EIN `Stratagem`-Objekt für beide**, damit 15.01s Einmal-pro-Phase greift;
  im Test daran gepinnt, dass der Kauf des einen Modus den anderen sperrt.
- **Experimental Modifications** (Auxiliary, 1CP): +1 AP, und zwar in BEIDEN Ketten — der Text sagt
  "attacks", nicht "ranged attacks". **Die Asymmetrie im WHEN ist gedruckt und eigens geprüft:**
  "YOUR Shooting phase" aber "THE Fight phase" — die Fight-Phase gehört niemandem, eine Kroot-Einheit
  im Gegnerzug ist also abgedeckt.
- **Alien Expertise** (Auxiliary, 1CP): die **VIERTE Quelle** der "Advanced und trotzdem chargen"-
  Ausnahme; sie tritt `charge.py`s bestehendem `advance_ok`-Fold bei, statt eine vierte Bedingung
  woanders aufzumachen. **Läuft am ZUGENDE ab, nicht am Phasenende** — 09.06s Verbot gilt den ganzen
  Zug, und gelesen wird es erst in der Charge-Phase; phasengebunden kaufte es gar nichts.
- **Guided Fire** (Auxiliary, 1CP): [LETHAL HITS] gegen Ziele in 9" einer befreundeten
  KROOT/VESPID-Einheit. **Die 9" werden bei der AUFLÖSUNG gemessen, nicht beim Kauf** — es ist eine
  Eigenschaft des ZIELS, dieselbe Einheit bekommt es also gegen ein Ziel und gegen ein anderes nicht.
  **"excluding KROOT/VESPID" ist der Kern des Stratagems** (die Kroot sind die Späher, nicht die
  Schützen) und als eigener Check geschrieben.
- **Konstruktionsreihenfolge, real gestolpert** (Fehlerklasse 23): der Block stand hinter
  `arrokon_controller` und damit VOR `fight_controller`, den Experimental Modifications braucht —
  `UnboundLocalError` beim ersten echten Start. **Vom Smoke gefangen, von keiner Suite**, und der
  AST-Wächter sieht es nicht (er prüft `a.b = c`, nicht Konstruktor-kwargs). Jetzt hinter
  `fight_controller`, mit Testzeile auf die Reihenfolge.
- **Ein fremder Pin ist zu Recht rot geworden:** `test_tau_kroot_and_vespid.py` pinnte
  `"or loping_pounce.is_active(squad))"` INKLUSIVE schließender Klammer — die wandert, sobald die
  Disjunktion einen vierten Term bekommt. Prüft jetzt den AUFRUF ohne Interpunktion, dieselbe
  Lehre wie beim Einrückungs-Pin in `test_datasheet_rules.py`.
- **Getestet:** neu `test_tau_detachment_stratagems.py` (**83/83**, fünf Abschnitte) plus **acht
  A/B-Sonden**, jede kippt ihre eigenen Prüfungen. Volle Regression **137 Suiten, ~9651 Prüfungen,
  136 grün / 0 rot / 1 bekannt**, alle fünf Smokes und echte `selfplay.py`-Läufe unter den
  betroffenen Detachments. **Kein KI-Pfad** (stehende T'au-Vorgabe), als Negativraum geprüft.

### Etappen 7-9 — die übrigen fünfzehn

**Alle 19 sind gebaut.** Was dabei an neuer Mechanik entstand, und warum:

- **`ChargeController.on_charge_declared` ist jetzt eine VERKETTUNG.** Es war ein Einzel-Slot mit
  Rückgabewert-Protokoll ("True heisst: ich besitze jetzt das resume"), und Kauyon druckt ZWEI
  Reaktionen auf denselben Moment. "Der erste gewinnt" hätte die zweite verschluckt; jetzt bekommt
  jeder Reaktor ein `resume`, das zum NÄCHSTEN weiterläuft. Der alte Einzel-Slot geht weiter zuerst,
  also musste Grav-Inhibitor Field nicht angefasst werden. Im Test wird die Kette direkt gefahren.
  - **Und genau diese Verkettung hat eine INVARIANTE gebrochen, die ihre Nachbarn ausgeschrieben
    hatten** (Absturz-Meldung "absturz bei photon grenades stratagem",
    `AttributeError: 'NoneType' object has no attribute 'owner'`). Vorher lief ein `resume` DIREKT
    nach `_start_declared_move()`, und das prüft seine Vorbedingungen neu — `grav_inhibitor_field`s
    `_finish()` sagt in seinem Docstring wörtlich, dass es sich darauf verlässt ("used, declined,
    or resolved to nothing"). Die Kette hat zwischen resume und diese Prüfung weitere Reaktoren
    gesetzt, und `step()` las `self.active_squad` bei JEDEM Schritt neu. Eine Reaktion, deren
    Auflösung die Charge BEENDET (Grav-Inhibitors Mortal Wounds können die chargende Einheit
    töten), räumt `active_squad` auf None — und der nächste Reaktor bekam None gereicht.
  - **Zwei Korrekturen, beide in `_offer_declaration_reactions()`:** die chargende Einheit wird
    EINMAL gefangen (alle Reaktoren beantworten DIESELBE Deklaration, das ist eine feste Tatsache
    des Fensters, kein pro Schritt neu zu lesendes Feld), und vor jedem Schritt wird gefragt, ob
    das Fenster überhaupt noch steht (`window_is_open()`: dieselbe Einheit, weiter
    `DECLARING_TARGETS`). Ist die Charge vorbei, endet die Kette — ihr gedrucktes Fenster ist
    "just after an enemy unit has selected its charge target", und einem Spieler dort noch CP
    anzubieten wäre eine Reaktion auf etwas, das es nicht mehr gibt.
  - **Ein ZWEITER Absturz derselben Form lag eine Zeile weiter** und ist mitbehoben:
    `_start_declared_move()`s `if self.active_squad is None or not any(...)` schrieb im Rumpf
    `self.active_squad.name` — der Kurzschluss auf None führte also direkt in denselben
    AttributeError. Jetzt zwei getrennte Prüfungen.
  - **A/B belegt:** die GANZE Vor-Fix-Welt wiederhergestellt (Pro-Schritt-Lesen UND der
    kombinierte Wächter) → **5 von 319 Prüfungen fallen**, darunter eine, die den REALEN
    `CombatEmbarkationController` durch die Kette fährt und wörtlich
    `'NoneType' object has no attribute 'owner'` zurückmeldet — die gemeldete Zeile, nicht ein
    Stellvertreter dafür.
- **`shaken`** (Pulse Onslaught) ist ein Status mit DREI Wirkungen an drei Nähten (-2 Move, -2
  Advance, -2 Charge) und EINER Frage (`is_shaken()`). **"Bis Ende des NÄCHSTEN Gegnerzuges" wird
  als DEADLINE gespeichert**, nicht auf einer Grenze gelöscht — zwei Grenzen liegen dazwischen, ein
  gewöhnlicher End-of-turn-Reset hätte ihn halbiert.
- **Aggressive Mobility teilt Jain Zars No-Roll-Advance-Zweig.** "do not make an Advance roll.
  Instead ... add 6 inches" steht wörtlich zweimal im Repo; der zweite Träger bekommt denselben
  Zweig statt eines eigenen.
- **Combat Embarkation überschreibt WANN man einsteigen darf, nicht OB man hineinpasst.**
  `can_embark()` bekam ein `require_move`-Flag, hinter dem NUR 18.02s "nach einer Bewegung diese
  Phase" liegt — die 3", die Kapazität und die Keyword-Verbote des Transporters gelten weiter aus
  ihrer einen Definition. **BENANNTE GRENZE:** "your opponent can select NEW targets for that
  charge" ist nicht gebaut. Die Engine prüft beim Fortsetzen die Vorbedingungen neu, eine
  eingestiegene Einheit ist also kein legales Ziel mehr — was fehlt, ist die Erlaubnis, ANDERE
  Ziele zu wählen. Das benachteiligt den Spieler, der das Stratagem NICHT gekauft hat, also die
  falsche Richtung; ausgeschrieben statt zum Selberfinden gelassen.
- **Marker Beacon ist der erste Aufrufer von `Objective.secure_for()`** — 14.03 war gebaut und der
  Docstring sagte "not called by anything yet ... here for when one exists". Jetzt existiert einer.
- **Microdrone Support hebt NUR die Schuss-Hälfte von 16.01 auf**, nicht die Charge-Hälfte; die
  beiden sind dort schon getrennte Methoden, also ist das eine Zeile und kein neuer Begriff.
- **Counterfire Defence Systems ist der VIERTE Konsument von `_reduced_damage()`** und erbt dessen
  Mindest-1-Schranke; Autoreactive Camouflages "+1 Sv" landet in `save_thresholds()` als MINUS 1
  auf die Schwelle, spiegelbildlich zur Plague-Strafe direkt darüber.
- **Focused Fire ist Bonus UND Kosten auf EINER Marke**: "+1 AP" und "darf nur dieses Ziel
  beschiessen" hängen an demselben Feld, damit das eine nicht ohne das andere auftreten kann.
- **Zwei eigene Fehler, beide von der Regression gefangen:** ein Import-Zyklus (`tau_detachments`
  zog über `game.factions` zurück auf `game.squad`, seit `coldstar.py` sehr früh dorthin greift —
  der Faction-Import ist jetzt funktionslokal), und ZWEIMAL derselbe Einfügefehler: ein Term auf
  `base` statt auf `total` bzw. auf `amount` statt auf den zurückgegebenen Wert, beide dadurch
  wirkungslos. Beide wurden von den eigenen Prüfungen sofort sichtbar.
- **Zwei fremde Pins sind zu Recht rot geworden:** `"or loping_pounce.is_active(squad))"` pinnte die
  schliessende Klammer einer Disjunktion, die einen vierten Term bekam; und
  `"montka" not in fight_src` verwechselte die REGEL mit ihren Stratagems, sobald ein Mont'ka-
  Stratagem die Fight-Phase zu Recht erreichte. Beide prüfen jetzt den Aufruf statt der
  Interpunktion bzw. das Modul statt des Präfixes.
- **Zwei A/B-Sonden bissen zuerst nicht.** Eine war der dokumentierte `__pycache__`-Rennfall (die
  Sonde schreibt und startet im selben Millisekundenfenster; von Hand wiederholt kippt sie). Die
  andere war ein echter TESTfehler derselben Klasse wie zweimal zuvor: der Negativfall für
  Autoreactive Camouflages "if that unit is hidden" lief mit `decision_manager=None`, und der
  Controller lehnt dann ohnehin ab — die Hidden-Bedingung war verdeckt. Jetzt mit echtem
  DecisionManager und einem Positivfall davor, und die Sonde kippt.
- **Getestet:** `test_tau_detachment_stratagems.py` **313/313** (neun Abschnitte) plus insgesamt
  **21 A/B-Sonden**. Abschnitt 9 zählt die neunzehn Module und verlangt von JEDEM, dass es auf sein
  Detachment gated und seinen gedruckten Regeltext zitiert — ein zwanzigstes kann nicht dazukommen,
  ohne dass diese Zeile sich bewegt. Volle Regression **137 Suiten, ~9882 Prüfungen, 136 grün /
  0 rot / 1 bekannt**, alle fünf Smokes, und ein echter `selfplay.py`-Lauf unter JEDEM der sechs
  Detachments. **Kein KI-Pfad**, für alle neunzehn als Negativraum geprüft.

## T'au-Detachment-Enhancements (game/enhancements.py + game/enh_*.py)

**Alle 19 Enhancements der sechs T'au-Detachments sind engine-verdrahtet** (User: "lets build all
tau detachment enhancements except kroot hunting pack"). Achtzehn neu; das neunzehnte (Starflare
Ignition System) gab es schon und ist auf die geteilte Registry umgestellt.

### `game/enhancements.py` — die Registry, und was sie verhindert

`game/factions/detachment.py`s `Enhancement` war die BESCHREIBENDE Hälfte; seine eigene Docstring
sagt, wie die verdrahtete aussehen soll ("das passende Feld auf der eigenen `UnitProfile`-Instanz
dieses Modells setzen"). `starflare_ignition.py` war die einzige Instanz davon und schrieb ~80
Zeilen Träger-Eignung, Punkte und Logging um EINE Attributzuweisung.

- **Neunzehn Kopien dieser achtzig Zeilen wären genau die Drift, die dieses Repo am ZWEITEN
  Konsumenten konsolidiert** — und die Hälften, die driften würden, sind die leicht falschen: die
  19.04-Lesart (ein Modell, das in DIESEM Frame gestorben ist, steht noch in `Squad.models`, weil
  `remove_dead_models()` einmal pro Frame läuft — genau der Fehlerbericht, für den Starflare
  repariert wurde), die "None ist ansteckend"-Konvention bei `Squad.points`, und das LAUTE Ablehnen
  einer mehrdeutigen Vergabe.
- **Die REGISTRY ist der Punkt**: `ENHANCEMENTS` ist die eine Liste aller neunzehn — Punkte,
  Detachment, das gelesene `UnitProfile`-Feld und die gedruckte BEARER-Zeile als Prädikat. Ein Test
  zählt sie, ein zwanzigstes kann nicht auftauchen, ohne dass diese Zählung sich bewegt. Punkte und
  Detachment sind gegen `game/factions/tau_empire.py`s beschreibenden Record GEPINNT statt gegen
  Literale.
- **Die REGEL jedes Enhancements liegt in seinem eigenen Modul**, genau wie eine Datenblatt-
  Fähigkeit. Kein generisches `apply(model)`, das so tut, als könnte es beliebige Effekte gewähren.
- **`unit_level=True` für die zwei, die eine EINHEIT bekommen** ("STEALTH BATTLESUITS unit only"):
  `grant()` markiert jedes Modell, und die 19.04-Lesart ("ein lebendes Modell trägt es noch") heißt
  dann "die Einheit existiert noch" — die richtige Lebensdauer. Beide Datenblätter haben gar keinen
  CHARACTER, ein CHARACTER-Zwang machte sie unbaubar.

### Die benannte Limitation von `starflare_ignition.py` ist GESCHLOSSEN

Das Modul schrieb ausführlich aus, warum es als einziges Retaliation-Cadre-Modul NICHT auf sein
Detachment gated: ein Enhancement ist eine LISTENBAU-Wahl, und einen Armeebau-Schritt gibt es nicht
— die vordefinierte T'au-Liste gab es dem Coldstar bedingungslos, also trug er es mitsamt 20
Punkten auch unter jedem anderen T'au-Detachment.

Seit ein Detachment zur LISTE gehört (`game/detachments.py`), gibt `army_lists.build_tau()` je
DEKLARIERTEM Detachment ein Enhancement aus, und `enhancements.is_active()` lehnt eines ab, dessen
Detachment nicht gefieldet wird. **Gelesen wird die ArmyList, nicht `config`** — `preview_squads()`
baut die Kachel des Armee-Screens, bevor irgendetwas in `config` geschrieben ist, ein
config-basiertes Tor ließe also Preview und Schlacht auseinanderlaufen.

**Die Liste vergibt seit dem 2026-08-30-Tausch NICHTS**, und das ist eine Tatsache ÜBER DIE LISTE,
keine Lücke: der gelieferte Roster nennt kein Enhancement, jeder Charakter darin ist zum
Grundpreis notiert (Shadowsun 100, beide Fireblades 50, der Ethereal 50), und ein Enhancement
trüge — wie das Detachment — seine eigene Zeile und seine eigenen Punkte. `_TAU_LIST_ENHANCEMENTS`
ist deshalb LEER, mit der Begründung darüber; eins zurückzuholen ist ein Eintrag, und der Kommentar
nennt den legalen Kandidaten samt Preis (Exemplar of the Kauyon auf einem Cadre Fireblade, +20).
Ungefragt vergeben würde es 35 Punkte kaufen, die der User nicht ausgegeben hat.

**Der MECHANISMUS ist davon unberührt und wird weiter getestet** — nur nicht mehr durch den Roster:
`test_tau_enhancements.py` Abschnitt 9 und `test_detachments.py` treiben ihn mit einer EIGENEN
Tabelle (Detachment deklariert → Enhancement, Träger per Datenblatt gefunden, Punkte auf dem Squad,
und das alles zur PREVIEW-Zeit, bevor irgendetwas in `config` steht). Ein Abschnitt, der nur noch
"die Liste vergibt nichts" behauptete, wäre genau dort still geworden, wo der Grant früher geprüft
wurde. Was die Tabelle vergäbe, ist unverändert gemessen: Kauyon → Exemplar of the Kauyon,
Mont'ka → Exemplar of the Mont'ka, Advanced Acquisition → Negation Emitters auf den Stealth
Battlesuits, Auxiliary → Admired Leader auf dem Cadre Fireblade, Retaliation Cadre → Starflare.
**Experimental Prototype Cadre bekäme NICHTS**, und das ist gemessen: alle drei seiner Enhancements
verbessern eine benannte Waffe, und kein Modell dieser Liste trägt T'au Flamer, Plasma Rifle oder
Airbursting Fragmentation Projector. Benannt wie Signal Pox, nicht durch Umschreiben der
User-Liste "behoben".

### Wo die neunzehn landen — und die zwei Extraktionen, die sie erzwangen

- **`game/detection_range.py` — SIEBZEHNTE Extraktion, am zweiten UND dritten Konsumenten
  gleichzeitig.** 13.09s Detection Range hatte genau eine Anpassung, und `is_detectable()` nahm sie
  als benanntes Argument (`prey_marks`). Negation Emitters (−3") und Unmasking Suite (+9") sind zwei
  weitere. Drei nach Fähigkeiten benannte Argumente, an der Aufrufstelle summiert, sind die Form, in
  der das vierte an nur EINER der zwei Aufrufstellen landet. **Richtung ausgeschrieben:** Detection
  Range gehört dem VERSTECKTEN Modell, ein POSITIVER Beitrag macht also von weiter weg sichtbar.
  Beide Bänder gemessen (15" Default und die 12"-Hauswandregel), weil ein nur gegen den Default
  geprüfter Bonus auf der falschen Basis bestehen kann.
  **Benannt, nicht nebenbei behoben:** `greater_good.eligible_targets()` ruft `is_detectable()` ohne
  jede dieser Quellen, misst also die gedruckte Distanz, während `shooting.py` die angepasste misst.
  Das ist ÄLTER als diese Extraktion (galt schon für `prey_marks` allein) und ändert, welche
  Einheiten Spotted werden dürfen — eine Verhaltensänderung an der Armeeregel, kein Refactor-
  Nebenprodukt.
- **`objective_control.effective_oc()` bekommt `objective=`** (optional, wie `all_tokens`): Strategic
  Conqueror gilt nur "within range of THAT objective marker". **REIHENFOLGE ausgeschrieben:**
  Hunting Hounds SETZT, Scabrous Soulrot VERSCHLECHTERT, die zwei Enhancements ADDIEREN zuletzt —
  die einzige Ordnung, in der 15 Punkte für +1 immer +1 kaufen.
- **`StratagemController.on_targets_chosen`** ist eine neue Listener-LISTE (Form wie
  `cost_discounts`). `on_stratagem_used` war unbrauchbar: es trägt Spieler und Stratagem, aber
  NICHT die Ziele — und "targeted the bearer's UNIT" ist ganz eine Frage über die Ziele.
- **`PregameController.prebattle_steps`** ist eine GEORDNETE Liste statt weiterer benannter
  Attribute, und die Ordnung ist der Inhalt: Strike Swiftly gewährt Scouts 6", und eine Einheit, die
  es NACH `ScoutsStep` bekommt, trägt eine Fähigkeit, die sie nie benutzen kann — im Unit-Test
  perfekt, im Spiel wirkungslos. `redeploy_step` ist ein EIGENER Haken an `_finish_deployment()`,
  weil Solid-image "after both players have deployed" feuert, also VOR Determine First Turn.
- **`shooting.py`s `_attack_key()` bekommt zwei Einträge**, aus demselben Grund wie
  `psychic_communion_bonus`: Precision of the Patient Hunter und Prototype Weapon System sind
  PRO-MODELL, und die Ein-Repräsentant-Abkürzung ist nur exakt, was im Schlüssel steht. Beide 0/""
  für jedes andere Modell, also spaltet sich keine bestehende Gruppe.
- **Die zwei aktivierungsgebundenen** (Prototype Weapon System, Unmasking Suite) öffnen und
  schließen auf DEMSELBEN Paar Nähte wie `targeting_array.py` — weil das genau das gedruckte
  Fenster ist ("selected to shoot" / "until those attacks are resolved" bzw. "until this unit has
  shot").

### Was an den neunzehn wirklich unterschiedlich ist

- **Zwei Paare teilen ein Modul, weil sie EIN Mechanismus sind**: `enh_exemplars.py` (beide
  Exemplars WEITEN das Rundenfenster ihres Detachments für die geführte Einheit — deshalb sitzt die
  Weitung in `tau_detachments.doctrine_active()`, dem einen Trichter, durch den beide Regeln und
  alle vier Grant-Stellen gehen, und NICHT an den Grant-Stellen: Kauyon hat zwei Hälften in zwei
  Dateien, eine halb verdrahtete Weitung wäre eine halbe Regel) und `enh_guided_keyword_grants.py`
  (Through Unity / Coordinated Exploitation sind derselbe Satz mit getauschtem Keyword).
  **"instead of from the third" ist ein ERSATZ des Fensters, "during the fourth as well" eine
  ERGÄNZUNG** — heute dieselbe Menge, aber getrennt gepinnt, weil ein geteiltes "eine Runde weiter"
  die beiden austauschbar aussehen ließe.
- **Die zwei Observer-Enhancements brauchen KEINEN neuen Zustand**: `GreaterGoodController.
  observer_squad_ids` ist bereits "wer hat diese Phase markiert" und wird in
  `reset_shooting_phase()` geleert — genau "until the end of the phase". Der Grant ist ARMEEWEIT und
  nicht an die eigene Marke gebunden (Gegensatz zu Forward Observers, das ausdrücklich "their
  Spotted unit" auf den markierenden Observer verengt): sonst wäre "until the end of the phase"
  redundant.
- **Internal Grenade Racks ist Wraith Form pro MODELL**: dieselbe "moved over"-Geometrie
  (`wraith_form.units_moved_over()`, wiederverwendet statt neu hergeleitet), aber "each time THE
  BEARER ends a Normal move" — der Pfad eines Bodyguards darf kein Ziel finden, dem der Commander
  nie nahe kam. Und sechs D6 FLACH statt einer je Modell. Die GRENADES-Hälfte wird über
  `has_grenades_keyword()` beantwortet, das `explosives.py`s eine Stelle jetzt fragt — kein
  zweites Profil-Flag, das dasselbe bedeutet.
- **Puretide Engram Neurochip ist NICHT Farsights "Puretide's Teachings"** (`game/puretide.py`, ein
  CP-RABATT). Zwei Regeln unter ähnlichem gedruckten Namen, je ein Modul, jedes nach seiner Wirkung
  benannt. Sie können gleichzeitig live sein und tun dann Verschiedenes zu verschiedenen Zeitpunkten.
  Der D6 wird nur geworfen, solange `bonus_cp_remaining()` Kopfraum meldet — dieselbe "nie einen
  Würfel werfen, der nichts zahlen kann"-Regel wie Coordinated Leadership.
- **Admired Leader ist ein SQUAD-FLAG**, nach dem Vorbild von `plagues.py`s Afflicted: `Ld` und `OC`
  werden über `leadership_threshold()` und `effective_oc()` gelesen, die zusammen über ein Dutzend
  Aufrufstellen haben und keinen Controller nehmen. **"+1 Ld" ist eine BESSERE Charakteristik, also
  ein NIEDRIGERER Schwellwert** — verkehrt herum machte ein 20-Punkte-Enhancement die
  Battle-Shock-Tests seines Ziels schwerer, und "+1" und "+1" ist dasselbe Wort für zwei
  Charakteristiken, die sich hier gegenläufig bewegen. Eigene Testzeile.
- **Strategic Conqueror hängt am OBJECTIVE**, nicht in einem Controller: gelesen wird es aus
  `Objective.level_of_control()`, das keinen Controller im Scope hat und nie einen haben wird —
  dieselbe Ablage, die 14.03s Secured schon benutzt.
- **Student of Kauyon nennt zwei DATENBLÄTTER, kein Keyword**: KROOT deckt auch Hounds, Krootox und
  die drei Shaper ab, und ihnen Deep Strike zu geben wäre eine viel weitere Regel als die gedruckte.
  Gegen das Keyword gepinnt, damit der Unterschied nicht still zusammenfällt.
- **Die drei EPC-Waffen-Upgrades werden IN PLACE angewandt**, einmal, im Declare-Battle-Formations-
  Schritt, und sind IDEMPOTENT (Marker auf der Waffe) — ein zweiter Durchgang darf +2 S nicht
  stapeln. **Gematcht an der Profil-KLASSE**, und dass die Twin-/High-intensity-Varianten KEINE
  Unterklassen der drei genannten sind, ist gepinnt: ein Refactor, der eine zur Unterklasse machte,
  würde alle drei still verbreitern. "+1 AP" ist eine VERBESSERUNG, also `ap - 1`.
- **Solid-image Projection Unit benutzt den Aufstellungs-Flow wieder**, statt ihn nachzubauen: die
  Einheit kommt vom Brett zurück in `PregameController._pending`, der Controller geht auf DEPLOYING,
  und das erneute Platzieren läuft durch dieselbe Validierung. `_redeploy_done` ist der Flag, der
  den zweiten Besuch in `_finish_deployment()` am zweiten Roll-off vorbeiführt.

### Kein KI-Pfad, aber auch kein Hänger

Stehende T'au-Vorgabe, als NEGATIVRAUM geprüft: keiner der neunzehn Namen kommt in
`ai/agent_driver.py` vor, und kein `enh_*`-Modul wird dort importiert. Weil ein Prompt, den niemand
beantwortet, die Schleife anhielte, beantwortet jede Regel mit einem "you can" ihre eigene Frage für
einen Owner in `auto_players` — dieselbe Form wie 'Ard as Nails und die sechs
Awakened-Dynasty-Protokolle. Solid-image LEHNT dabei ausdrücklich ab: Umstellen ist ein
Gesamtarmee-Urteil, die Aufstellungs-KI hat gerade platziert, wo sie wollte, und drei Einheiten
danach zufällig zu verschieben machte ihre eigene Aufstellung schlechter.

**Getestet:** neu `test_tau_enhancements.py` (**246/246**, zehn Abschnitte) plus **38 A/B-Sonden**
an der QUELLE, von denen jede genau ihre eigenen Prüfungen kippt. **Zwei Sonden waren Befunde über
den TEST**, nicht über den Code: die Würfelzahl war gegen die MODUL-KONSTANTE geprüft statt gegen
die gedruckte 6 (eine Tautologie — die Sonde bewegte beide Seiten des Vergleichs), und zwei
Reihenfolge-Wächter benutzten `str.index()`, das beim Verschwinden der Nadel WIRFT statt rot zu
werden und damit verbarg, welche Prüfung gebrochen war (jetzt `before()`). Dazu der dokumentierte
`__pycache__`-Rennfall: die Sonden schreiben und stellen im selben Sekundenfenster wieder her, also
leert der Sondenlauf den Cache zwischen den Durchgängen — ohne das meldete der nächste Durchgang die
Fehler des vorigen. Volle Regression **138 Suiten, ~10101 Prüfungen, 137 grün / 0 rot / 1 bekannt**,
alle fünf Smokes (inkl. `smoke_setup_screens.py --neutralize`, plus `smoke_pregame.py` auf map1 UND
map2) und `selfplay.py map2`.

**Im ECHTEN Spiel belegt, nicht nur im Test:** je ein `selfplay.py map2`-Lauf mit T'au auf BEIDEN
Seiten unter JEDEM der sechs Detachments (2500 Frames, alle exit 0), und das Log jedes Laufs nennt
genau das Enhancement seines Detachments für beide Spieler — `Player 1: Commander in Coldstar
Battlesuit in 1 Crisis Starscythe Battlesuits 1 + Commander in Coldstar Battlesuit carries the
Exemplar of the Mont'ka Enhancement (10 pts).` Der Experimental-Prototype-Cadre-Lauf nennt
erwartungsgemäß KEINES — das ist die gemessene Limitation oben, im Log sichtbar statt behauptet.

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
- **Take to the Skies (21.03): NUR FLY-Modelle zahlen, und eine reine INFANTERIE-Einheit
  deklariert es NIEMALS.** Beide Hälften sind User-Entscheidungen, erfragt nachdem die Messung
  ergab, dass die zwei Hälften der Regel VERSCHIEDENE Modellmengen trafen.
  - **Wer zahlt** (User: "es fliegen nur fly modelle"): `clamp_move()`s Bypass war immer schon
    pro Modell an `token.profile.fly` gegated — richtig; falsch war `take_to_the_skies()`s
    Preisschleife über das GANZE Squad. Gemeldet als "die necron krieger sind hinten nicht
    rausgekommen. sie hatten enorme schwierigkeiten nach vorne zu laufen": ein Technomancer (FLY)
    in 20 Necron Warriors (kein FLY), 19.01 merged beide, **21 von 21 zahlten, 1 von 21 flog** —
    5" auf 3", also 40%, jede Bewegungsphase des ganzen Spiels (im Log 1.63"/1.23"/1.19"
    Fortschritt). Jetzt zahlt nur der Technomancer; der Krieger behält seine 5", durch
    `clamp_move()` gemessen und nicht nur am Budget. **HOVER (24.17) bleibt bewusst eine
    squad-weite Ausnahme** — das ist die bestehende Lesart, kein Datenblatt der vier Roster
    druckt HOVER, und das Verengen war nicht Teil der Entscheidung.
  - **Wer deklariert** (User: "einheiten, die ausschließlich aus infanterie modellen bestehen
    sollten niemals take to the skies benutzen, weil sie ja eh durch wände laufen können"):
    13.06 lässt INFANTERIE Dense-Gelände ohnehin queren, die WERTVOLLE Hälfte von 21.03 kauft
    ihnen also nichts. Übrig bliebe das Durchqueren von MODELLEN, und das ist 2" je Modell nicht
    wert. `game/movement.py`s `take_to_the_skies_pays(squad)` ist die eine Definition, gelesen
    von `ai/agent_driver.py` UND `measure_crowded_movement.py` (der trug eine eigene Kopie —
    sein Header zählt auf, dass genau solche Kopien ihn dreimal von seinem Messgegenstand haben
    abdriften lassen). Vorher stand an beiden Stellen `any(m.profile.fly ...)`, begründet damit,
    die Deklaration "can only ever help this squad's own mobility" — wahr für die Crisis
    Battlesuits, für die sie geschrieben wurde, falsch für einen Leader-Flieger.
    **"Niemals" ist wörtlich genommen: die INFANTERIE-Prüfung steht VOR dem HOVER-Zweig**, als
    Testzeile gepinnt, weil sich die zwei Reihenfolgen nur in diesem einen Fall unterscheiden.
    Bewusst das INFANTRY-Keyword und nicht `can_move_through_dense_terrain()` (das deckt vier
    Keywords ab): die Entscheidung nennt Infanterie, und BEASTS sind ein anderer Fall — die
    Canoptek Wraiths queren Wände per 13.06 UND fliegen, und niemand hat verlangt, sie zu erden.
  - **Betroffen sind VIER Einheiten über alle vier Roster** (alle rein INFANTERIE): Necron
    Warriors + Technomancer, Stormboyz, Warp Spiders + Lhykhis, Stealth Battlesuits. **Sechzehn
    behalten es**, und keine davon ist reine Infanterie — Fahrzeuge, Walker, Beasts, Monster.
  - **Gemessen, nicht behauptet.** Der Fortschritt der gemeldeten Einheit
    (`measure_fly_penalty.py`, Brett aus den Log-Koordinaten rekonstruiert): **+0.93"/Zug** im
    Gedränge. Und die dokumentierte Bewegungs-Baseline wird durch die INFANTERIE-Regel BESSER,
    nicht schlechter — A/B in `measure_crowded_movement.py`: erreichter Fortschritt
    **60% → 65%**, Gesamtboden **202.1" → 209.1"**, Einheiten unter 60% **50.0% → 42.9%**. Die
    Stormboyz, die der Harness-Header als einen seiner zwei schlimmsten Fälle führt, stehen
    danach nicht mehr unter den fünf schlechtesten; der Header ist entsprechend nachgezogen.
  - **Getestet:** `test_take_to_the_skies_policy.py` (**33/33**), mit den zwei Hälften EINZELN
    neutralisiert (Engine-Hälfte → 27/33, INFANTERIE-Regel → 28/33), sodass keine die andere
    deckt.
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
    Würfelauswahl: "change the result of one Damage roll to an unmodified 6" meint das ERGEBNIS,
    und neun Waffen im Repo drucken einen Bonus (D6+1, D6+2) — den Würfel auf 6 zu setzen ergäbe
    7 oder 8. `DiceNotationRoll.face_for_total()` rechnet deshalb das Gesicht aus, das das
    gewünschte ERGEBNIS erzeugt (D6+2 → eine 4), und lehnt einen mehrwürfeligen Wurf LAUT ab,
    statt zu raten. Damit bleibt die Regellesart exakt die, auf die sich `game/branching_fates.py`
    festgelegt hatte. Ein Auswahlschritt entfällt (ein Würfel — gemessen über jede
    Damage-Notation im Repo), dieselbe Abkürzung wie bei Command Re-roll.
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

## Regelengine — Nahkampf

12.01-12.06 (`game/fight.py`, `game/pile_in.py`), inkl. Split Fire, Pass, echtem Pile-In/Consolidate
für die KI.

- **Die Zielwahl friert 12.02 ein — alle Nahkampfwaffen schlagen in EINER Aktivierung zu** (User:
  "im nahkampf. alle nahkampfwaffen schlagen gleichzeitig zu. das heißt waffen eines squads können
  in einer aktivierung nicht außer reichweite geraten, wenn models vom gegner entfernt werden.
  ähnlich wie beim schießen"). Das "ähnlich wie beim schießen" ist wörtlich: `game/shooting.py`
  trägt genau diesen Fix seit derselben Meldung als 10.02s `_snapshot_target_state()`, die
  Nahkampfphase hatte ihn nie — `weapon_eligibility()` und `choose_weapon()` maßen 12.02s
  Pro-Modell-Prüfung für JEDE verbleibende Gruppe neu, gegen die noch stehenden Feindmodelle.
  - **Reproduziert vor jeder Änderung**: Warp Spiders gegen ein Ziel, dessen einziges nahes Modell
    vor dem Rest stand — drei Gruppen mit 3/4, 1/1 und 1/1 berechtigten Modellen, danach **0/4, 0/1
    und 0/1**, sobald dieses eine Modell als Verlust entfernt war. `choose_weapon()` baute eine
    leere Paarliste, die restlichen Nahkampfwaffen des Trupps verloren ihre Angriffe ersatzlos.
  - **`_snapshot_engagement()`/`_engaged_with()` an DREI Punkten**, weil drei Stellen den
    Zielauswahl-Schritt ausmachen: die explizite Wahl, der Ein-Ziel-Auto-Pick (den die meisten
    Einheiten wirklich nehmen — ein Schnappschuss nur in `choose_target_squad()` ließe den
    gewöhnlichen Fall ungefroren) und Split Fires `assign_current()`, dort VOR der
    Engagement-Prüfung, die die Zuweisung selbst gatet. Gekeyt an `(model, target_squad)` statt an
    `id(weapon)` wie im Fernkampf: Engagement Range ist reine Geometrie und hängt nicht davon ab,
    welche Waffe schwingt.
  - **Ein KOMPLETT ausgelöschtes Ziel bleibt ausgenommen** — dieselbe Grenze wie `_can_reach()`.
    Der Lebendigkeitstest ist `any(not m.is_dead() ...)`, nicht `not squad.models` (Fehlerklasse
    12); die Vor-Fix-Welt ließ einen Trupp auf eine ausgelöschte Einheit einschlagen (A/B: 3 statt
    0 Modelle).
  - **Der KI-Pfad las dieselbe Frage doppelt**: `ai/agent_driver.py`s `_melee_group_pairs()`
    versprach im eigenen Docstring "exactly what `weapon_eligibility()` counts" und filterte
    daneben live mit `model_engaged_with()` — Fehlerklasse 10 im Kleinen. Liest jetzt
    `fight_controller._engaged_with()`.
  - **Getestet:** neues `test_melee_simultaneous.py` (**44/44**), inkl. der gemeldeten Folge
    end-to-end durch den echten Controller (Gruppe 2 schwingt wirklich mit 1 Modell statt 0), der
    Aktivierungsgrenzen in beide Richtungen (eine NEUE Aktivierung misst frisch), der
    Live-Rückfall für nie geschnappte Squads, KI-Parität und Quell-Wächter. **Fünf A/B-Sonden**,
    jede kippt Prüfungen (Lesestellen zurück auf live → 9, Auto-Pick-Schnappschuss entfernt → 8,
    KI zurück auf live → 3, `not squad.models` als Lebendigkeitstest → 2, Reset entfernt → 2).
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
- **Ein Modell mit ZWEI Nahkampfwaffen bekommt eigene Gruppen** (User: "beispiel warpspider. alle
  close combat weapons des squads werden gruppiert. wenn ich jetzt zuerst auf den knopf close
  combat weapon klicke, handelt jede einheit die angriffe ab. auch der exarch, der aber noch ein
  power blade array hat ... kann ich danach nicht mehr mit dem powerblade array zuschlagen").
  Reproduziert: der Exarch teilte die "Close Combat Weapon"-Gruppe des Trupps (gleiche WS/S/AP/D),
  der Klick auf den Trupp-Button schwang also auch seine Waffe, und 04.01 sperrte danach sein
  Array. **Die Wahl wurde ihm von einem Knopf über eine FREMDE Waffe abgenommen.**
  - **`_melee_choice_owner()` hängt am Gruppierungsschlüssel**: hat ein Modell mehr als eine
    wählbare Nahkampfwaffe, bekommt es eigene Gruppen. Das ist die minimale Form des ZWEITEN
    User-Vorschlags ("gruppen mit waffen loadouts"); der erste ("characters, leader und rest
    trennen") hätte genau diesen Fall verfehlt — ein Aspekt-Exarch ist bewusst KEIN CHARACTER und
    auch nicht `squad_leader`.
  - **Gemessen über alle 72 Datenblätter: 14 Modell-Loadouts** tragen mehr als eine wählbare
    Nahkampfwaffe, in ALLEN vier Fraktionen (jeder Exarch mit Melee-Upgrade, die Ork-Boss-Nobs,
    Beastboss, Skorpekh Lord, Deff Dread). Kein Warp-Spider-Sonderfall.
  - **[EXTRA ATTACKS] bekommt nie einen eigenen Owner** — 24.11 macht sie unbeschränkt, sie nimmt
    also keine Wahl weg, und sie abzuspalten würde die Liste nur zerfasern.
  - **Das LABEL ist Teil des Fixes**, nicht Kosmetik: ohne es stünden zwei Knöpfe "Close Combat
    Weapon" nebeneinander, was schlimmer wäre als der Fehler. `_melee_group_label()` hängt den
    Modellnamen an, wenn die Gruppe ein Modell mit Wahl ist.
  - **Zweiter, kleinerer Fehler aus demselben Bericht:** war jedes Modell einer Gruppe nach 04.01
    gesperrt, wurde sie WEITER angeboten — mit `_group_label()`s Leerlisten-Platzhalter, also als
    Knopf mit der Aufschrift "Weapon", der nichts tat. Leere Gruppen werden jetzt nicht mehr
    gelistet.
  - **04.01 gilt unverändert:** hat der Exarch einmal geschwungen, ist seine andere Nahkampfwaffe
    gesperrt. Der Fix stellt die WAHL wieder her, er hebt die Regel nicht auf — eigene Testzeile.
  - **Getestet:** neues `test_melee_weapon_groups.py` (**31/31**, inkl. der gemeldeten Klickfolge
    in beiden Reihenfolgen und einer Ork-Gegenprobe) plus vier A/B-Sonden.
- **Fights First (24.13) entscheidet die REIHENFOLGE, nicht die Berechtigung** — es als dritte Art
  von "kampfberechtigt" zu lesen ließ Einheiten 18" vom Gegner am Ende jedes Zuges eine Auswahl
  verlangen.
- **Eine ausgelöschte Einheit ist nicht kampfberechtigt** (die klebrigen Marker `engaged_at_start`/
  `fights_first` wussten nichts von ihrem Tod) — sonst hängt der Fight-Step dauerhaft.
- **"End Turn" warnt, wenn 12.04 dem Menschen noch Angriffe schuldet** (User: "gib mal bitte ine
  warnung aus, die ich wegklicken muss, wenn ich auf end turn klicke, obwohl ich noch mit einheiten
  im nahkampf kämpfen könnte"). Reproduziert vor der Änderung: NICHTS hielt den Klick auf —
  `_has_unresolved_declaration()` deckt `CHOOSING_TARGET`/`CHOOSING_WEAPON`/`ASSIGNING` ab (eine
  halbfertige Aktivierung), ausdrücklich aber nicht `SELECTING`, den gewöhnlichen "du bist dran,
  wähle eine Einheit"-Zustand. Der Zug endete, die Angriffe waren weg, eine Logzeile war die
  einzige Spur.
  - **`squads_that_could_still_fight(player)` ist die eine Definition** und STRENGER als
    `is_eligible_to_fight()`: 12.04s zweite Bedingung hält eine Einheit berechtigt, deren einziger
    naher Feind inzwischen gestorben ist — die hat nichts zu schlagen, und sie zu nennen wäre
    Lärm. Plus der Lebendigkeits-Filter auf der Feindseite (Fehlerklasse 12: `remove_dead_models()`
    läuft einmal pro Frame) und `DONE` als Kurzschluss. Nach Namen sortiert, weil `_all_squads()`
    ein SET ist und die Warnung Namen druckt.
  - **Eine WARNUNG, keine Sperre.** Diese Engine zwingt niemanden zu kämpfen; der Klick wird auf
    die Warnung verbraucht, der nächste geht durch. Einmal pro PHASE, mit dem Wiedervorlage-Punkt
    in `advance_turn_phase()` (Fehlerklasse 14) — ohne den warnte sie einmal pro SCHLACHT.
  - **BEIDE Menschklick-Routen in `advance_turn_phase()` sind gegated**, nicht nur der Button: ein
    wegen 09.02-Kohärenz blockierter Klick setzt nach dem Entfernen des Modells in denselben
    Aufruf fort. Deshalb `_fight_warning_intercepts_end_turn()` als geteilte Frage, aus demselben
    Grund, aus dem `_has_unresolved_declaration()` eine ist. `ai_advance_phase()` bleibt bewusst
    UNGEGATED — ein Overlay dort stallt die KI auf einer Warnung, die niemand wegklickt.
  - Der Dismiss-Zweig steht ÜBER dem Button, der sie auslöst (Fehlerklasse 15): ein Klick darf
    nicht zugleich die Warnung wegklicken und den Zug beenden, vor dem sie warnte.
- **Das linke Panel NENNT die Einheiten, die noch einen Pile In schulden** (User: "ich finde es
  manchmal schwierig zu erkennen, dass ich noch mit allen einheiten pile in machen muss, bevor die
  KI weitermacht"). Gemessen vor der Änderung: dort stand EIN Satz — "Both players must resolve
  Pile In (move or skip) for every eligible unit before the Fight step can begin." Wahr und
  nutzlos: keine Einheit, keine Seite, kein nächster Schritt, also liest sich ein Spiel, das auf
  den MENSCHEN wartet, genau wie eines, das auf die KI wartet.
  - **`PileInController.squads_pending_pile_in(player=None)`** ist die eine Definition;
    `has_pending_squads()` liest denselben Generator und behält seinen Kurzschluss.
  - **Nach Owner GRUPPIERT statt auf "meine" gefiltert.** Das Panel hat keinen Begriff davon, wer
    der Mensch ist, und einen zu erfinden wäre eine zweite Kopie einer Tatsache, die `main.py`
    schon besitzt. Ein Squad-NAME beginnt mit der Spielerziffer — derselbe Identifier, den
    Zug-Banner, Turn-Plan und jede Logzeile benutzen —, also beantwortet "Player 1: 1 Storm
    Guardians 1" die Frage "bin ich das?" ohne Annahme, und bleibt richtig, falls der Mensch je
    Player 2 spielt.
  - In einem Kasten mit eigenem Orange, nicht als loser Text: es ist etwas zu TUN und stand vorher
    im selben Grau wie das Phasen-Geplauder daneben. Namensliste bei 4 gedeckelt (`+N more`), die
    GESAMTZAHL bleibt immer ehrlich.
  - **Getestet:** `test_pile_in_panel.py` (**35/35**, inkl. echtem `ActionPanel` und Pixelprüfung)
    plus sieben A/B-Sonden, jede kippt die Suite.
  - **Getestet:** `test_fight_end_turn_warning.py` (**44/44**, drei Abschnitte: die Frage an ihren
    Grenzen, das Overlay auf einer echten Surface, der Quell-Wächter auf `main.py`) plus SIEBEN
    A/B-Sonden, jede kippt die Suite. Dazu `smoke_end_turn_warning.py` (**13/13**), weil ein
    Quell-Wächter nicht beweist, dass der Klick ankommt.

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
- **Der Stapel teilt siebzehn Karten aus**: Centre Ground, Bring It Down, A Grievous Blow,
  Assassination, A Tempting Target, Beacon, Behind Enemy Lines, Cleanse, Defend Stronghold, Display
  of Might, Engage on All Fronts, Forward Position, No Prisoners, Outflank, Overwhelming Force,
  Plunder, Secure No Man's Land. Zwei je Runde, ohne Nachmischen — man sieht also höchstens zehn
  davon pro Schlacht.
  - **Burden of Trust ist GEBAUT, aber bewusst NICHT im Stapel** (User: "lass Burden of Trust
    erstmal weg"). Ihre Ökonomie ging nicht auf: man verpflichtet jede Runde neu Wächter, aber
    abgerechnet wird nur der Stand am Ende der Schlacht — vier der fünf Verpflichtungen sind also
    unsichtbar. Alles, was sie braucht, steht weiter da und wird weiter getestet (Karte,
    Zuweisungsfenster, und die Brett-Klick-Auswahl, die sie überhaupt erst eingeführt hat), also
    ist das Zurückholen EIN Name in `ALL_CARDS`. Im Test von beiden Seiten gepinnt. Eine neue
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
- **Getestet:** neu `test_secondary_missions.py` (**543/543**), `test_mission_cards_ui.py`
  (**54/54**, gegen eine echte Surface gemessen statt gegen Konstanten) und
  `test_one_modal_at_a_time.py` (**44/44**, Quell-Wächter). Neu `test_actions.py` (**79/79**) und `test_mission_unit_pick.py` (**60/60**). Volle
  Regression **112 Suiten, ~7432 Prüfungen, 111 grün / 0 rot / 1 bekannt**, dazu alle vier Smokes und `selfplay.py map2` 2000
  Frames (0 API-Calls). Vorher gab es zu Missionen **gar keinen Test**.

## Fraktionen

`game/factions/` (Datasheet/Detachment/Faction + `build_squad()`) ist das generische Gerüst.

- **T'au Empire** — Strike Team, Breacher Team, Kroot Carnivores, Stealth Battlesuits, Ghostkeel,
  Devilfish, Crisis Starscythe, Crisis Sunforge, Riptide, Pathfinder Team, The Twin Lance, Commander
  Farsight, Commander in Coldstar, Cadre Fireblade, **Kroot Flesh Shaper, Kroot Trail Shaper,
  Kroot War Shaper, Ethereal, Darkstrider, Firesight Team, Kroot Lone-Spear, Commander in
  Enforcer Battlesuit, Commander Shadowsun, Kroot Hounds, Kroot Farstalkers, Vespid
  Stingwings, Krootox Riders, Krootox Rampagers, Broadside Battlesuits, Crisis Fireknife
  Battlesuits, Hammerhead Gunship, Sky Ray Gunship, Piranhas** (33 von 40 aktuellen
  Datenblättern). Armeeregel
  "For The Greater Good",
  Detachment "Retaliation Cadre" (Bonded Heroes + 6 Stratagems).
  **Sechs Detachments sind angelegt, wählbar und ihre REGELN sind alle engine-verdrahtet**:
  Retaliation Cadre (Bonded Heroes), Kauyon (Patient Hunter), Mont'ka (Killing Blow), Experimental
  Prototype Cadre (Superior Craftsmanship), Advanced Acquisition Cadre (Expert Fieldcraft) und
  Auxiliary Cadre (Integrated Command Structure) — siehe die drei Abschnitte oben. **Auch alle
  STRATAGEMS sind gebaut**: Retaliation Cadre 6, Kauyon 6, Mont'ka 6, Advanced Acquisition 3,
  Auxiliary 3, Experimental Prototype 1 — 25 insgesamt. **Und alle 19 ENHANCEMENTS**: Retaliation
  Cadre 4, Kauyon 4, Mont'ka 4, Experimental Prototype 3, Advanced Acquisition 2, Auxiliary 2 —
  siehe `## T'au-Detachment-Enhancements`. Damit ist der T'au-Detachment-Nachzug vollständig:
  sechs Regeln, 25 Stratagems, 19 Enhancements. (Kroot Hunting Pack ist auf User-Vorgabe
  ausgenommen — es gibt es weder als Detachment-Record noch mit Enhancements.)
  Komplette Punkteliste (43 Einträge).
  **Alle 19 engine-nativen fehlenden Datenblätter sind gebaut** (Etappen 1a bis 4).
  Aircraft, Titanic und
  Fortifications bleiben draußen,
  weil AIRCRAFT/FORTIFICATION/TITANIC belegte No-ops sind und es keine Vertikalität gibt.
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
  sechs Stratagems; die vier Enhancements bleiben reine Daten — anders als die T'au, deren
  neunzehn alle verdrahtet sind).
  Punkteliste bewusst NUR für gebaute Einheiten. **Die erste Fraktion, die die KI spielen soll und
  die nicht Player 2s Default ist** — umschaltbar über `config.PLAYER2_ARMY` / `--army2 necrons`.
  Dazu **Skorpekh Lord** und **Lokhust Lord** — angelegt, getestet, in KEINER Demo-Armee (siehe
  unten).

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

- **Death Guard** — Plague Marines, Poxwalkers, Typhus, Malignant Plaguecaster, Daemon Prince of
  Nurgle, Chaos Spawn, Deathshroud Terminators, Defiler, Foetid Bloat-drone, Myphitic
  Blight-hauler, Plagueburst Crawler (11 Datenblätter, 52 Waffen). Armeeregel **Nurgle's Gift**
  (`game/nurgles_gift.py` + `game/plagues.py`), Detachment **Death Lord's Chosen** mit der Regel
  **Deadly Vectors** (`game/deadly_vectors.py`) und allen sechs Stratagems (`game/dlc_*.py`).
  Fünfte wählbare Liste; `PLAYER1_ARMY`/`PLAYER2_ARMY` bleiben unverändert.

  - **Afflicted ist ein SQUAD-FLAG, einmal pro Frame aufgefrischt** — nicht ein Live-Prädikat, und
    das aus zwei unabhängigen Gründen. (1) KOSTEN: `attached_unit_toughness()` hat neun Leser und
    läuft einmal pro Waffengruppe pro Angriff; die Aura dort zu messen hieße, dieselbe Geometrie
    dutzendfach pro Frame neu abzuleiten und an neun Stellen ein `all_tokens` zu ergänzen.
    (2) KORREKTHEIT: „Afflicted" hat eine ZWEITE, KLEBENDE Quelle — Plague Marines' eigene
    Fähigkeit und Signal Pox setzen es „bis zum Beginn deines nächsten Zuges", ganz ohne ein Death
    Guard-Modell in der Nähe. Ein Distanztest kann die nie sehen; ein Flag ist die Vereinigung.
    Dieselbe Anordnung, die `status_effects.targeting_range_limit()` für `ard_as_nails_active`
    dokumentiert. `Squad.afflicted_plague` wird im SELBEN Pass gestempelt — das ist, was alle sechs
    Plague-Trichter die EINHEIT lesen lässt, statt einen Parameter zu wachsen (`effective_movement_in()`,
    `leadership_threshold()` und `level_of_control()` haben zusammen über ein Dutzend Aufrufstellen,
    genau die Gefahr, die `coldstar.py`s Docstring benennt).
  - **Contagion Range 3"/6"/9"** (Runde 1 / 2 / 3+). **Erst falsch gebaut als 6"/9"/12"** — und
    das ist die Lehre, nicht die Zahl: Wahapedia druckt die Progression als drei BILDER
    (`ContagionRange1.png` …), ein Text-Fetch liefert dort die Dateinamen und keine Zahlen, und der
    Zusammenfasser hat sie *abgeleitet* statt gelesen. Erst die präzise Nachfrage hat das gezeigt;
    die richtigen Werte kamen vom User. **Fehlerklasse: eine Zahl, die nur in einer Grafik steht,
    ist über diesen Weg nicht transkribierbar — dann fragen.**
    Der 12"-Deckel ist mit diesen Zahlen INERT (9" + der einzige Modifikator 3" = genau 12") und
    steht ausdrücklich NICHT im gelieferten Kartentext; er bleibt als Schranke stehen, ist aber als
    unbestätigt markiert.
  - **Per-Frame-Kosten gemessen und optimiert:** 3.56 ms → **0.36 ms** auf einem 192-Modell-Brett
    durch einen Bounding-Box-Reject (0.28 ms im pathologischen Fall, wo alles auf einem Haufen
    steht). Weil das eine reine Optimierung ist, pinnen **400 Fuzz-Bretter** sie gegen die
    Brute-Force-Fassung; eine zu enge Reject-Schwelle kippt 18 davon.
  - **Die −1 Toughness sitzt in `attached_unit_toughness()`**, nicht an dessen neun Aufrufern. Genau
    das lässt sie `damage_estimate` und `ai/observation` erreichen: die KI zielt gegen die echte
    Toughness, nicht die gedruckte.
  - **Die drei Plagues sitzen an bestehenden Trichtern** (Hit ×2, Save, Move, Leadership, OC).
    Skullsquirm Blight liest sich rückwärts: es sind die EIGENEN Angriffe der afflicted Einheit,
    die −1 bekommen, nicht die gegen sie. **Auch das war erst falsch gebaut** — der Zusammenfasser
    lieferte „Fernkampf gibt dem Ziel Deckung, Nahkampf −1 Hit", also zwei Effekte an zwei Stellen;
    der gedruckte Text sagt schlicht „each time a model in this unit makes AN ATTACK, subtract 1
    from the Hit roll" — ein Effekt, zwei Trichter, keine Deckungs-Klausel. Scabrous Soulrots
    OC-Untergrenze ist eine Grenze fürs VERSCHLECHTERN — ein Modell mit gedruckter OC 0 bleibt 0,
    statt auf 1 angehoben zu werden.
  - **Deadly Vectors feuert am START der Command-Phase**, nicht am Ende. Reanimation Protocols
    dräniert dort seine eigene Würfel-Queue, und Necrons gegen Death Guard ist eine gewöhnliche
    Paarung — zwei Queues auf einer Naht stritten um `DiceManager.pending_values`. Seine Schwelle
    ist INVERTIERT (6 oder weniger), deshalb bleibt `success_threshold` leer: das Würfelpanel
    färbte sonst exakt verkehrt herum, und die Zahl steht stattdessen im LABEL.
  - **Zwei Basisgrößen sind Tischgrößen, keine Transkriptionen** (User-Entscheidungen, dritte und
    vierte ihrer Art nach Falcon und den Jetbikes): der Defiler druckt 160 mm (r 3.15") und spielt
    auf 2.1" wie Battlewagon/Falcon; der Plagueburst Crawler druckt **gar keine** Base (FRAME) und
    bekommt denselben Wert. Beide Zahlen stehen an der Zeile, damit niemand „korrigiert".
  - **Tank Hunters existiert jetzt ZWEIMAL unter einem Namen.** Der Myphitic Blight-hauler druckt
    dieselben +1/+1 gegen MONSTER/VEHICLE wie die Tankbustas, aber mit „in your Shooting phase",
    das die Ork-Fassung nicht hat. Deshalb zwei Flags und ein `melee=`-Argument an
    `tank_hunters_modifiers()` — geteilt hätte der Blight-hauler den Bonus still auch mit seinem
    Gnashing Maw bekommen. Die engere Lesart ist außerdem die sichere.
  - **Punkte: 2020 gegen die 2015 der Liste**, vier benannte Abweichungen in beide Richtungen.
    14 Einheiten / 49 Modelle nach zwei Anbindungen (Typhus → Deathshroud 1, Plaguecaster → Plague
    Marines; **User-Entscheidung**, weil Raten still entschieden hätte, welche Fähigkeiten
    überhaupt wirken).
  - **Sprites: elf Dateien, acht mit abweichender Schreibweise** — der Ordner gewinnt, inklusive
    `Demon Price of Nurgle.png` (zwei Tippfehler in einem Dateinamen). **Fraktionslogo fehlt** und
    ist gepinnt.
  - **Die Aura wird als grüner Layer gezeichnet** (`renderer.draw_contagion_aura()`, User-Wunsch
    „ganz subtiler grüner Layer, ähnlich der gegnerischen Engagement Range"). Anders als jenes
    Overlay werden die Kreise **DECKEND gezeichnet und der ganze Layer EINMAL mit Alpha geblittet**:
    jenes malt eine Handvoll 2"-Kreise, dieses bis zu 49 Kreise à 12", und übereinandergelegte
    Transparenz ergäbe ein Flickenmuster aus Hotspots — obwohl zweimal drin dasselbe ist wie
    einmal drin. Alpha 58 ist an einem echten map2-Frame GEMESSEN: 34 war unsichtbar, 90 las sich
    als Farbwäsche. `reach_of` kommt vom Controller, damit der gezeichnete Kreis der ist, den die
    Regel liest.
  - **Die sechs Stratagems und ihre KI** (User-Vorgabe: „GRIM REAPERS – erste Gelegenheit /
    UNDYING SPITE – wenn rechnerisch ein Terminator im Nahkampf sterben würde / SICKENING IMPACT –
    erste Gelegenheit; der Rest ist irrelevant für die KI"). Fünf von sechs zielen auf TERMINATOR-
    Einheiten, also auf die zwei Deathshroud-Trupps und Typhus.
    - **Blooming Pestilence ist mit den richtigen Reichweiten NIE wertlos** (3→6, 6→9, 9→12) —
      der 12"-Deckel existiert gerade dafür. Mit der falschen Tabelle wäre es ab Runde 3 wertlos
      gewesen, was nach einer schönen Entscheidungsgrenze aussah und ein Artefakt war.
    - **UNDYING SPITE ist das einzige mit wirklich neuer Sequenzierung**: ein Modell, das TOT ist,
      auf dem Brett bleibt, eine Aktivierung bekommt und danach entfernt wird. Beide Momente gab es
      schon (`target_reactions`, `on_unit_finished_fighting`); neu ist der Zustand dazwischen. Der
      Tod wird im SWEEP abgefangen, weil `remove_dead_models()` das Modell sonst wegnimmt —
      Fehlerklasse 12.
      **Sein Verdict musste umformuliert werden:** sein WHEN liegt *vor* jedem Modelltod, „ist
      gestorben" ist zum Kaufzeitpunkt also nicht messbar. Gelesen als ERWARTETE Verluste
      (`expected_kills ≥ 1`), injiziert wie bei Vengeful Stars, weil `game/` nicht von `ai/` abhängt.
      Das Verdict-Tor gilt NUR der KI — ein Mensch wird gefragt, also darf die Engine ihm nicht
      vorgreifen.
    - **SIGNAL POX ist ein belegter No-op**: kein Datenblatt dieses Rosters trägt LORD OF
      VIRULENCE. Vollständig ausgeschrieben, Inertheit gepinnt — faktisch setzt die KI **fünf von
      sechs** ein.
    - **GRIM REAPERS ist der exakte Spiegel von Monster Hunters** und hängt an derselben Naht;
      ihre Ziel-Tests sind Komplemente, sie können nie beide auf einen Angriff wirken.
    - **Drei Reihenfolge-Fehler in `main.py`, alle nur vom END-TO-END-Lauf gefunden**: Listener
      bzw. Controller wurden vor ihren Abhängigkeiten registriert (`UnboundLocalError` beim ersten
      echten Start). Keine Suite konnte das sehen — sie treiben die Controller direkt. Seither
      gibt es dafür den AST-Wächter in `test_event_chain_wiring.py` (Fehlerklasse 23).
    - **Und ZWEI Controller waren gebaut, aber nie GEFÜTTERT** — Lethal Ichor und Spore-laced
      Shock Waves. Beide hatten grüne Prädikat-Tests und konnten im echten Spiel nie feuern, weil
      `notify_melee_allocation()` bzw. `notify_target_selected()` nirgends aufgerufen wurde. Die
      Seams existierten längst (`_begin_damage_allocation()` zählt Zuteilungen — eine ABGEWEHRTE
      Attacke zählt mit und ist danach nicht mehr rekonstruierbar; `_begin_resolution()` ist der
      Moment, in dem Ziel UND Waffe zum ersten Mal beide feststehen). Beide werden jetzt END-TO-END
      durch die echten Controller getestet, was die einzige Testform ist, die das gefunden hätte.
    - **Ein zu schwacher Verdrahtungs-Wächter, an der eigenen A/B-Sonde aufgefallen**:
      `count("_handle_grim_reapers(") >= 2` blieb grün, nachdem der Aufruf entfernt war — eine
      Erwähnung im Docstring zählte mit. Ein Namenszähler reicht für diese Fehlerklasse nicht; es
      muss der AUFRUFAUSDRUCK geprüft werden.
  - **Bewusst offen:** kein Fraktionslogo; Signal Pox inert; die vier Enhancements bleiben reine
    Daten; Deadly Vectors ist durch seine Suite belegt, im Selbstspiel aber noch nicht live gesehen
    (es braucht Runde 2 mit afflicted Gegnern, was der MockAgent-Lauf in der Framezahl selten
    erreicht).
  - **Getestet:** `test_nurgles_gift.py` (**123/123**), `test_deadly_vectors.py` (**75/75**),
    `test_death_guard_datasheets.py` (**193/193**), `test_death_guard_stratagems.py` (**128/128**),
    dazu ~22 A/B-Sonden an der QUELLE, jede bricht ihre Suite. Volle Regression **127 Suiten,
    ~8584 Prüfungen, 126 grün / 0 rot / 1 bekannt**, alle fünf Smokes, und Death Guard durch die
    echte `main()`-Schleife auf BEIDEN Seiten und auf map2 wie map3.

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

## Regeltext-Korpus (`rules/*.md`, `fetch_datasheet_rules.py`)

**Der gedruckte Regeltext jedes Datenblatts, eine Datei je Einheit** (User: "zieh dir den kompletten
regeltext jedes einzelnen datasheets ... und speichere den regeltext in eigenen md dateien ab. so
können wir später leichter überprüfen, ob sich regeln geändert haben für updates"). 113 Dateien:
die **84 gebauten** Datenblätter aller fünf Fraktionen plus die **29 noch nicht gebauten T'au**.

**Seit der Detachment-Erweiterung auch ARMEEREGELN und DETACHMENTS** (User: "speichere auch bitte
detachment regeln und armeeregeln ab. nicht nur datasheets"). Drei Dateiarten, 175 Dateien:
`rules/<fraktion>/<Datenblatt>.md`, `rules/<fraktion>/army_rules.md` (5) und
`rules/<fraktion>/detachments/<Name>.md` (**56** — alle Detachments aller fünf Fraktionen, nicht
nur die gebauten, aus demselben Grund, aus dem die 29 ungebauten T'au-Datenblätter dabei sind).

- **Die zweite URL ist nicht bequem, sondern nötig — gemessen:** `datasheets.html` enthält
  ÜBERHAUPT KEINE Armeeregel ("For The Greater Good" kommt dort null mal vor) und wiederholt nur
  die Detachments, die ein Datenblatt zufällig nennt — drei von T'aus sieben kamen mit
  abgeschnittener Stratagem-Liste zurück. Die Fraktions-Indexseite `factions/<slug>/` trägt beides
  vollständig. Also zehn Requests statt fünf.
- **Drei Seitenformen, die eine naive Fassung still falsch liest** — jede real, jede A/B-belegt:
  1. **Ein h3 "Errata" INNERHALB eines Stratagem-Abschnitts** darf ihn nicht beenden. `chunks()`
     läuft deshalb bis zur nächsten Überschrift GLEICHER ODER HÖHERER Ebene; bis zur nächsten
     beliebigen gerechnet, behält Kauyon 1 von 6 Stratagems (A/B: 6 → 5, Regelteile 2 → 0).
  2. **Die Enhancement-Überschrift heißt nicht immer "Enhancements"** (Aeldari "Corsair
     Enhancements", Necrons "Necrodermal Binding Abilities"), also werden sie an ihrem MARKUP
     erkannt (`ul.EnhancementsPts`), nicht am Titel. Ein Suffix-Test auf den Titel reicht für die
     Corsair-Paare und verliert trotzdem ALLE VIER von Pantheon of Woe — deshalb nennt der Test
     genau dieses Detachment.
  3. **Death Guard legt seine Armeeregel in ein GESCHWISTER-h2** ("Nurgle's Gift (Aura)") nach der
     leeren "Army Rules"-Überschrift, wo die anderen vier h3-Kinder benutzen. Wer nur die h3s
     liest, bekommt für Death Guard NICHTS zurück (A/B: 3 → 0).
- **Ein Detachment wird von seinem Stratagem-Abschnitt GESCHLOSSEN**, nicht von "irgendein anderes
  h2 kam". Beides zählt: ein unbekanntes h2 mittendrin darf die Abschnitte danach nicht verwaisen
  lassen (Form 2), und der Block "Boarding Actions" weiter unten hat ein eigenes h2 "Stratagems",
  das NICHT beim letzten Detachment landen darf.
- **Der Errata-"Show"/"Hide"-Umschalter steht INNERHALB des Errata-Blocks** und landet sonst
  mitten im Regeltext. `SKIP_CLASSES` verwirft das ganze Bedienelement, nach TAG-NAME gezählt —
  es enthält weitere `<div>`s, ein flaches "bis zum nächsten `</div>`" endet zu früh.
  **A/B belegt, dass die Datenblätter davon unberührt sind:** neutralisiert ändern sich 24 Dateien,
  davon **0 Datenblätter**.
- **`--detachment NAME`** ist das Gegenstück zu `--only`. Jede Flagge verengt auf ihre eigene
  Dateiart und schaltet die andere ab, damit keine die Seiten der anderen neu lädt.
- **Byte-Stabilität weiter belegt:** zwei Läufe erzeugen 175 identische Dateien.

- **Warum überhaupt:** `abilities_text` kann die Frage nicht beantworten, weil seine Treue je
  Fraktion verschieden ist — Orks und T'au sind nahezu wörtlich, Necrons zitieren wörtlich aber
  teils ohne Überschrift, **Aeldari und Death Guard sind Paraphrase plus `see game/...`-Verweis**.
- **WebFetch scheidet aus, gemessen:** sein Zusammenfasser VERWEIGERT die wörtliche Wiedergabe
  eines Datenblatts (Copyright-Filter) und bietet eine Paraphrase an — also genau das, was in
  `abilities_text` schon nicht reicht. Der Scraper liest rohes HTML und hat diese Meinung nicht.
- **Fünf Requests, nicht 84:** `factions/<slug>/datasheets.html` enthält ALLE Datenblätter einer
  Fraktion inline (62 bei T'au, 99 bei Aeldari). Nebeneffekt: ein Lauf ist EIN konsistenter
  Schnappschuss statt 84 zu 84 verschiedenen Zeitpunkten geholten Seiten.
- **Namensabgleich braucht keine Alias-Tabelle:** reine Normalisierung (NFKD, `’`→`'`, lowercase,
  nicht-alphanumerisch weg) matcht **84/84**. Ein Datenblatt ohne Treffer bricht den Lauf LAUT ab.
- **Die Byte-Stabilität IST das Produkt, und sie war nicht gratis.** Zwei Abrufe derselben
  unveränderten Seite unterscheiden sich um ~10 kB Werbe-Markup **und um vereinzelte CRs** — die
  liefen bis ins Markdown durch und ließen 60 Dateien "sich ändern", ohne dass eine Regel anders
  war. Deshalb: Newlines werden beim Abruf normalisiert, und **in keiner Datenblatt-Datei steht ein
  Zeitstempel** (das Abrufdatum lebt allein in `rules/README.md`). Belegt: zwei unabhängige Abrufe
  (curl und urllib, 35 Minuten auseinander) erzeugen **byte-identische** 113 Dateien.
- **Drei Strukturen, die ein naiver Parser still falsch liest** — jede war real, jede ist mit
  A/B-Sonde gepinnt:
  1. **Waffen-Keywords sind GESCHACHTELTE Spans** in der Namenszelle; ein nicht-gieriges `</span>`
     macht aus "rapid fire 1" das Keyword "rapid" und den Waffennamen "Fireblade pulse rifle fire 1".
     Deshalb ein `HTMLParser` statt Regex (auch die Wargear-Unterlisten hingen daran).
  2. **Der Rettungswurf steht NICHT in der Charakteristik-Zeile**, sondern in einer eigenen
     `dsInvulWrap`-Box — und zwar **PRO MODELLZEILE**: 14 Blöcke (jeder Aspekt-Krieger-Trupp, wo der
     Exarch abweicht) tragen zwei. Die erste Fassung des Korpus verzeichnete für **alle 204**
     Datenblätter mit Rettungswurf keinen.
  3. **`LED BY` / `SUPPORTED BY` stehen UNTERHALB der Keyword-Leiste**, mitten in der
     Fraktions-Möblierung (Stratagem-Liste, Detachment, Enhancements), die sonst abgeschnitten
     wird — die Gegenstücke zu `LEADER`, das oberhalb steht. Alles Übrige dort wird verworfen.
  Dazu zwei kleinere: der Damaged-Abschnitt trägt `<span class="dsSkull2">` statt eines
  `...Icon`-Spans, und Wahapedia schreibt `dsLeftСolKW`/`dsRightСolKW` mit einem **kyrillischen С**
  (U+0421) — mit lateinischem C matcht das Muster lautlos nichts und die Fraktions-Keywords fehlen.
- **`--only "<Name>"` ist der Weg für ein EINZELNES Datenblatt.** **Stehende User-Vorgabe:** "bei
  zukünftigen datasheets, die du anlegst, bitte auch immer abspeichern parallel" — die `.md` gehört
  in dieselbe Sitzung wie das Datenblatt, als Schritt 7 des Datenblatt-Rezepts.
- **`rules/.cache/` (das rohe HTML, ~16 MB) ist gitignoriert**, das Markdown NICHT — dessen Diff ist
  ja der ganze Zweck. `--offline` parst nur den Cache neu.
- **Getestet:** `test_datasheet_rules.py` (**83/83**, ohne Netzzugriff — Abschnitt 5 deckt
  Armeeregeln und Detachments ab) plus **elf A/B-Sonden**, jede stellt eine Vor-Fix-Welt an der
  QUELLE her und kippt genau ihre eigenen Prüfungen (Keyword-Regex → 47/51, Newlines → 49,
  Rettungswurf → 49, LED BY → 49, Punkte-Tiers → 49, kyrillisches C → 49, Damaged-Icon → 50,
  Listen-Einrückung → 50; dazu die drei Seitenformen oben).
  **Zwei bestehende Prüfungen sind dabei zu Recht rot geworden und nachgezogen:** "keine
  Streudateien" zählte `rules/*/*.md` und sah die fünf neuen `army_rules.md` als Streu, und der
  Quell-Wächter auf die Abbruchmeldung pinnte deren EINRÜCKUNG — die sich änderte, als der Code in
  einen Helfer wanderte. Er matcht jetzt einrückungsfrei, also weiter den AUFRUFAUSDRUCK und nicht
  seine Formatierung.
- **Was der Abgleich gefunden hat** (`verify_rules_vs_engine.py`, 49 Differenzen): die meisten sind
  dokumentierte Entscheidungen (Tischgrößen für Falcon/Wave Serpent/Devilfish/Defiler/Jetbikes/
  Destroyer, und die durchgehend zugunsten der Transkription benannten Punkte-Abweichungen). **Zwei
  sind es nicht:** die gedruckten Datenblätter geben **Windriders einen 6+ und Striking Scorpions
  einen 5+ Rettungswurf, den die Engine nicht gewährt** — beim Windrider sagt der Profil-Docstring
  sogar ausdrücklich, ein 6+ sei "spurious" gewesen, was die Seite widerlegt. Benannt, nicht
  ungefragt geändert.

**Datenblatt-Rezept** (Details in der Memory-Datei `new-datasheet-recipe.md`): Werte per Wahapedia
holen — Slug nach Muster raten ist die billigere erste Wette, der Fraktions-Index nur der Rückfall,
und mit PRÄZISEN Sachfragen abfragen ("welche Phase? welcher unmodifizierte Würfelwert? Trefferwurf
oder Wundwurf?") statt "fasse zusammen". **Bekanntes Rendering-Artefakt (12× aufgetreten):** Keywords
hängen am NAMEN, während die Keyword-Spalte leer bleibt — der Namensspalte folgen. Eine Waffe mit
BS "N/A" ist [TORRENT]. Bei "gleicher Name, andere Zahlen" eine eigene Klasse anlegen; sonst teilen.
Eine bloße Paraphrase ist NICHT implementierungswürdig — dann als fehlend in `abilities_text`
markieren (im Spiel sichtbar) und im Test ASSERTIEREN, damit das Nachrüsten eine sichtbare Änderung ist.
**Seit dem Regeltext-Korpus ist der erste Griff `rules/<fraktion>/<Name>.md`** statt eines neuen
Abrufs — dort steht der Text schon wörtlich, inklusive Basisgröße, Rettungswurf und Punkte-Tiers;
und ein neu angelegtes Datenblatt bekommt seine `.md` per `--only` in derselben Sitzung.

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
- **Der Garnisons-Tausch sortiert nach ROLLE, dann erst nach Punkten**
  (`_cheaper_garrison_candidates()`, Schlüssel `(is_assault_unit, cost, gap)`). Billigstes-zuerst
  allein hat den Job dem billigsten Trupp gegeben — und die Nahkämpfer einer Armee sind regelmäßig
  ihre billigsten, **also hat ausgerechnet die Korrektur, die verhindern soll, dass gute Einheiten
  auf leerem Boden verschwendet werden, selbst ausgewählt, welche gute Einheit verschwendet wird**.
  Gemeldet als "die lych guard waren sehr passiv. die sollten eher weiter nach vorne pushen"; der
  stärkste Fall im Log ist nicht die gemeldete Einheit, sondern die, die dieser Pass ZUGEWIESEN
  hat: er nahm die 270-Punkte-Necron-Warriors von P2 Home und gab den Job den 85-Punkte-Skorpekh
  Destroyers (0.0x Fernkampf/Nahkampf, gar keine Fernkampfwaffen), die danach **vier von fünf
  Zügen** auf Boden standen, dem kein Feind auf 12" nahe kam. Auf dem gemeldeten Brett gemessen:
  der Job geht jetzt an die Lokhust Destroyers (6.7x), **obwohl die teurer sind** — Rolle schlägt
  Punkte.
  **Die Lychguard selbst waren davon zunächst NICHT betroffen** (ihr `hold` kam dreimal in Folge
  direkt aus dem Plan, auf einem UMKÄMPFTEN Objective, das der Over-Garrison-Pass zu Recht
  ausnimmt) — bis dieselbe Form auf dem HOME Objective wiederkam, siehe den nächsten Punkt.
- **Home-Garnison: Fernkampf schlägt Punkte, an ALLEN DREI Stellen, die das entscheiden** (User:
  "die ki soll fernkampfeinheiten stark bevorzugen, wenn es darum geht das home objective zu
  halten. sie hat im letzten spiel dafür die lychguard benutzt, was völliger quatsch ist. die
  immortals wären perfekt. starke fernkämpfer mit hoher reichweite").
  - **Der Sortierschlüssel oben war die halbe Antwort, und die andere Hälfte war der FILTER.**
    "Strikt billiger als der Holder" war die ganze Definition eines lohnenden Tausches, also
    konnte der Pass eine Garnison nur die Punkteliste ABWÄRTS bewegen — die Immortals kamen als
    Kandidat gar nicht erst in Betracht, weil sie mehr kosten. Im gemeldeten Spiel
    (`logs/game_20260826_234856.log`, Zeilen 124-125) nahm er P2 Home den 270-Punkte-Necron-Warriors
    ab und gab es den 170-Punkte-Lychguard. Das Tor ist jetzt dasselbe `(Band, Punkte)`-Paar wie
    die Ordnung: **ein Trupp, der für den Job SCHLECHTER wäre, ist kein Kandidat dafür, wie billig
    er auch ist.** Die alte Begründung dagegen ("eine Garnison, die nicht stattfindet, verliert
    das Objective") gilt hier nachweislich nicht — es ist der EIN-Holder-Fall, ein abgelehnter
    Tausch lässt den Holder stehen. Als Invariante gepinnt statt behauptet.
  - **Die eigentliche Ursache lag aber eine Phase FRÜHER**, und der Turn-Plan-Pass hat sie nur
    bestätigt: `deployment_ai.home_garrison_squad()` wählte rein nach Punkten, und in der
    Necron-Liste ist die BILLIGSTE Einheit der ganzen Armee die Lychguard mit 170 — also bekam
    der Nahkampf-Amboss den Job in jedem Spiel. Deshalb standen die Immortals im gemeldeten Log
    auch 12" und 20" vom Objective entfernt: für den Turn-Plan-Pass unerreichbar. **Eine Sonde,
    die eine Immortals-Einheit neben das Objective gestellt hätte, hätte einen Fix gemeldet, den
    das echte Spiel nicht hätte nutzen können.**
  - **BEIDE HÄLFTEN DER USER-AUSSAGE SIND EIGENE TERME**, und das ist der Befund, der die Form
    bestimmt hat: "Fernkämpfer" und "hohe Reichweite" wählen NICHT dieselben Einheiten. Die
    Aeldari-Wraithguard lesen sich als Fernkampfeinheit (Ratio 2.00) auf einer 12"-Waffe — vom
    Home Objective aus tragen sie exakt so wenig bei wie die Lychguard. `home_garrison_rank()`
    setzt eine Einheit deshalb nur dann ins oberste Band, wenn ihr Schaden aus dem Schießen kommt
    UND dieses Schießen von dort hinten überhaupt etwas erreicht.
  - **DREI BÄNDER statt eines Scores** (`game/combat_focus.py`, vierter Konsument derselben
    Messung nach Charge-Sperre, `assault`-Aufstellungsrolle und Garnisons-Tausch): SHOOTER /
    neutral / ASSAULT, und die Punkte entscheiden INNERHALB eines Bandes. Ein kontinuierlicher
    Score hätte den Punkte-Term überall überstimmt — bei den Orks hätte er den Job von den
    45-Punkte-Gretchin auf den 160-Punkte-Battlewagon verschoben. Gemessen und deshalb verworfen.
  - **Die Reichweiten-Schranke wird am BRETT gemessen, nicht gesetzt**
    (`observation.garrison_reach_needed_in()`): Abstand zum NÄCHSTEN anderen Objective, also zum
    nächsten Boden, um den überhaupt gekämpft wird — 17.1" (map1), 14.8" (map2), 11.6"/13.8"
    (map3, und dort als einziges pro Spieler VERSCHIEDEN). Eine feste Zahl hätte auf allen drei
    zufällig gestimmt und genau diesen letzten Fall still verfehlt. **Bewusst NICHT der Abstand
    zum Niemandsland** — der beträgt vom Home Objective aus nur 3.8-5.2" und hätte jede
    12"-Waffe durchgelassen.
  - **Fünfzehnte Extraktion: `agent_driver._garrison_fitness()`.** Drei Stellen beantworten
    "wen lassen wir hier stehen" — der Over-Garrison-Pass (Keeper aus zwei oder drei), sein
    planner-seitiger Zwilling und der Lone-Swap-Pass. Zwei Ordnungen hätten den ersten genau die
    Einheit behalten lassen, die der dritte nicht mehr wählen soll. Quell-Wächter prüft, dass es
    genau eine Definition und drei Leser gibt.
  - **Gemessen, nicht behauptet** (`measure_home_garrison.py`, A/B über `--neutralize`):
    Aufstellung auf allen drei Karten Lychguard → **Immortals 1**; Orks (**Gretchin**) und
    Aeldari (**Warlock Skyrunners**) unverändert, also trifft die Änderung genau die gemeldete
    Liste. Auf dem gemeldeten Brett findet der Turn-Plan-Pass **keinen Tausch mehr**. Im ECHTEN
    Selbstspiellauf: `2 Immortals 1 + Plasmancer (shooter) deployed at (30.0,6.0) (fully hidden,
    rule 13.09) ... 11/11 models` — auf dem Home Objective, während die Lychguard an der Flanke
    stehen.
  - **Der Preis ist gemessen und benannt:** die Skorpekh Destroyers waren im alten Test-Roster
    die Home-Garnison (85 Punkte, die billigste Einheit) und hatten ihre 13.09-Deckung genau
    dort. Freigestellt gehen sie **+0.97" → +2.98"** nach vorn und verlieren **3/3 → 0/3**
    Deckung; die Immortals gehen dafür **0/11 → 11/11**, und die Armee insgesamt von **15 auf 25**
    verdeckten Modellen. Vorwärts zuerst ist die vom User selbst gesetzte Reihenfolge der beiden
    Klauseln. `measure_deployment_safety.py` bleibt auf beiden Karten PASS.
  - **Auch im Planner-Prompt**, weil eine Regel nur in der Durchsetzung jeden Zug eine Korrektur
    erzeugt: die alte Zeile "Garrison with the cheapest unit that holds it" ist ersetzt durch die
    Fernkampf-Regel samt Begründung ("a gun on a home objective keeps firing every turn it stands
    there") und der Gegenrichtung für ein UMKÄMPFTES Objective.
  - **Getestet:** neu `test_home_garrison.py` (**79/79**) plus drei A/B-Sonden, jede kippt genau
    ihre eigenen Prüfungen; `test_over_garrison.py` von 61 auf **71/71** (Abschnitte 9 und 10
    ehrlich umgeschrieben, siehe unten); `test_report_20260824.py` **65/65**.
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
  spielt**: "AI's heavy units deploy in the front row" meldet **heavy 9.92" gegen screen 15.59"**
  auf map2 (vor dem 2026-08-30-Listentausch 13.94" gegen 15.12"). **Betrifft die Default-Paarung
  NICHT** (aeldari/necrons ist grün, und bei jeder Paarung ohne T'au auf Player 2 wird die Schranke
  mangels `screen`-Einheiten gar nicht erst gerechnet). Beide DECKUNGS-Schranken halten unverändert.
  Die Ursache ist die PRÄMISSE der Schranke, nicht die Aufstellung: sie prüft "ein paar große
  Modelle vor vielen billigen Körpern", und der neue Roster spielt genau dagegen — `heavy` sind
  jetzt sechs Einheiten, davon **zwei Devilfish, die per Konstruktion hinten parken, weil sie die
  Breacher tragen**, plus die Broadsides als statische Geschützplattform; `screen` sind unter
  anderem **zwei Stealth Battlesuits, die als INFILTRATORS (24.20) 8" vorn aufstellen** — eine
  andere Regel als der Scorer bestimmt ihren Platz. Die Schranke vergleicht damit Transporter gegen
  Infiltratoren. Braucht eine eigene Messreihe (welche Rolle ein Transporter und ein Battlesuit
  verdienen, und ob Infiltratoren aus dieser Schranke gehören) — bewusst NICHT durch Aufweichen der
  Zusicherung erledigt, weil genau diese Schranke schon einmal einen echten Mangel angezeigt hat,
  als sie zu streng aussah.
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
  Karten- und Listenauswahl auch zwei Screens davor existieren; es fehlt weiter der Schritt,
  der damit eine Armee ZUSAMMENSTELLT. Daran hängen: das 50%-Reserve-Limit als Bau-Regel, EPIC
  HEROs "nur einmal" und Farsights "Independent Power". **Enhancements sind KEIN offener Punkt
  mehr** — alle 19 der sechs T'au-Detachments sind engine-verdrahtet, `game/enhancements.py` ist
  die Registry, und die Liste vergibt je deklariertem Detachment eines (siehe
  `## T'au-Detachment-Enhancements`). Was fehlt, ist nur die WAHL: welches Enhancement auf welches
  Modell, statt der Tabelle, die die vordefinierte Liste dafür führt. **Der Auswahl-Screen ist ausdrücklich
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

- **Das Variant-Sprite hing an einer LIVE-Mehrheit statt an einer statischen Tatsache — die Fusion-Gun-Storm-Guardians verloren ihre Kunst mitten in der Schlacht** (User: "die fusion gun storm guardians haben gerade das falsche sprite").
  - **Reproduziert, bevor irgendetwas angefasst wurde, und die Verdrahtung war NICHT das Problem:** bei voller Stärke löst jedes der 10 Modelle korrekt auf (Flamer/Fusion/Power Sword/plain, alle vier Dateien vorhanden und inhaltlich richtig, im Bild geprüft). Der Fehler braucht VERLUSTE. `_unusual_weapon_names()` fragte, ob die Ladung von der LEBENDEN Mehrheit der Einheit abweicht — sobald 2 plain-Gardisten und 1 Flamer tot sind, stehen Fusion/Sword/plain bei je 2, `Counter.most_common()` bricht den Gleichstand nach MODELLREIHENFOLGE, kürt die Fusion-Ladung zur "Mehrheit" — und die beiden Fusion-Gardisten galten damit als normal und fielen auf `Assault Guardian.png` zurück.
  - **Die Frage war die falsche.** Die Kunst zeigt die Waffe in der Hand des Modells; ein Tod anderswo in der Einheit kann nicht ändern, welches Bild richtig ist. Ein Dateiname `<key> - <Waffe>.png` beantwortet "dieses Modell trägt eine Waffe, die sein Datenblatt nicht druckt" — eine STATISCHE Tatsache. Neues `_printed_weapon_names()` liest sie am Datenblatt (Komponente bei einer Attached Unit, sonst `squad.datasheet`), gekeyt an der Profil-KLASSE statt am Zeilennamen (der ist freier Text, die Klasse ist die Identität). **Über alle 71 Datenblätter und 140 Modellzeilen geprüft statt angenommen: kein Datenblatt hat zwei Zeilen, die sich eine Profilklasse teilen und verschiedene Waffen drucken** — die Antwort ist also eindeutig. Gecacht, weil `sprite_for()` pro Token pro Frame läuft, und über die Waffen-KLASSEN gelesen (`name` ist Klassenattribut), also wird dabei nichts instanziiert.
  - **`Squad.unusual_loadout_models()` bleibt unangetastet, und das ist Absicht** — es sind jetzt bewusst zwei verschiedene Fragen, nicht Fehlerklasse 10: der TINT sagt "dieses Modell fällt neben seinen Squadmates auf" (eine lebende, relative Aussage, für ein Highlight richtig), das SPRITE sagt "dieses Modell trägt eine Waffe, die sein Datenblatt nicht druckt". Der frühere Kommentar band beides ausdrücklich aneinander; die Trennung steht jetzt ausgeschrieben. **Der Tint trägt den Gleichstands-Zufall weiterhin** — benannt, nicht ungefragt mitgeändert.
  - **Rückfall auf die alte Mehrheitswahl, wenn das gedruckte Loadout gar nicht lesbar ist** (eine handgebaute `Squad` hat kein Datenblatt) — jede `testkit.py`-Szene verhält sich unverändert.
  - **Getestet:** `test_storm_guardians.py` von 83 auf **92/92**, neuer Abschnitt 7b — der exakt gemeldete Zustand, dazu JEDE Verlusttiefe (ein Gleichstand ist von beiden Seiten erreichbar, also hätte das Pinnen nur der gemeldeten Zahl die Nachbarfälle frei driften lassen), der Zustand NACH `remove_dead_models()` (die andere Hälfte derselben Drift, weil ein nicht-angebundenes Squad seine Peers aus `squad.models` las), und die Quelle selbst. **A/B belegt:** den Datenblatt-Pfad entfernt → **88/92**, und die vier roten Zeilen nennen genau `Fusion Gun -> Assault Guardian.png`. Volle Regression **112 Suiten, ~7450 Prüfungen, 111 grün / 0 rot / 1 bekannt**, dazu `smoke_pregame.py map2`, `smoke_log_input.py map2` und `selfplay.py map2` 2000 Frames — die Smokes hier nicht aus Gewohnheit, sondern weil `game/sprites.py` in der Renderkette pro Frame läuft.
  - **Nebenbefund:** die Weichen-Mechanik bedient heute genau EIN Datenblatt — die drei `Assault Guardian - *.png` sind die einzigen Variant-Dateien im Ordner, und `- Leader` hat gar keine. Das hält das Risiko der Umstellung klein und ist der Grund, warum die Drift so lange unbemerkt blieb.

- **Vierzehntes und fünfzehntes Necron-Datenblatt: Skorpekh Lord und Lokhust Lord** (User: "Lege die einheit an / Skorpekh Lord" … "danach / Lokhust Lord"). Beide sind DESTROYER CULT, beide führen genau die Einheit, deren größere Ausgabe sie sind, und beide stehen in KEINER Demo-Armee — wie die siebenundzwanzig Aeldari-Datenblätter davor.
  - **Beide nehmen die Destroyer-Tischgröße 0.984" (50 mm) statt ihrer gedruckten 60 mm**, nach der stehenden User-Regel "alle Destroyer sollen die gleiche Größe haben". Hier wiegt sie schwerer als bei den zwei Lokhust-Trupps: ein Lord wird per 19.01 in seine Bodyguards GEMERGT, eine 60-mm-Base mitten in einem 50-mm-Trupp ist also genau die Stelle, an der der Unterschied auffiele. Im Test sind jetzt **alle fünf** Destroyer-Cult-Datenblätter gegeneinander gepinnt, nicht gegen ein Literal.
  - **Der Skorpekh Lord ist das erste Datenblatt mit einer echten 04.01-WAHL zwischen zwei Nahkampfwaffen.** Flensing Claw (A8/S6/AP-1/D1) und Hyperphase Harvester (A4/S10/AP-3/D3) tragen BEIDE kein [EXTRA ATTACKS] — geprüft statt angenommen, weil eine Viele-Angriffe-Klaue neben einer schweren Waffe fast immer [EXTRA ATTACKS] IST. Ohne das Keyword sind es acht leichte Schwünge ODER vier schwere, und genau das ist die Waffenwahl dieses Datenblatts.
  - **United In Destruction** ist Spirit of Gorks zweite Hälfte minus einem Grant: [LETHAL HITS] auf die Nahkampfwaffen der GANZEN Einheit, solange er sie führt. Chain-Eintrag in `FightController._adjusted_weapon()` — dort und nicht im Wundschritt, weil `_crit_note()` schon zum WURFZEITPUNKT wissen muss, ob ein kritischer Würfel ein [LETHAL HITS]-Würfel ist. Gelesen über `leader_ability()`, NICHT `unit_wide_ability()` (kein Bodyguard druckt sie), was 19.04s Nachlauffenster gratis mitbringt.
  - **Crimson Harvest ist die erste Fähigkeit, die an "ends a Charge move" hängt** — und dieser Moment existierte in der Engine nirgends. Neuer Haken `ChargeController.on_charge_move_finished` (eine LISTE, anders als das Einzel-Callable `on_charge_declared` daneben: das hat ein Rückgabewert-Protokoll und braucht genau einen Besitzer, dies ist eine reine Benachrichtigung).
    - **Er sitzt in `confirm_charge_move()` und ausdrücklich NICHT in `_finish_charge()`** — letzteres läuft auch für einen ABGELEHNTEN Charge und für eine vor dem Zug zerstörte Einheit, und keins von beidem beendet einen Charge-Zug. Gefeuert NACH `_finish_charge()`, damit der Charge abgeschlossen ist, bevor ein Zuhörer einen Würfelwurf darauf öffnet.
    - **Gemessen an der NAHT, nicht an der Fähigkeit** — und das war nötig: `decline_charge_move()` ruft zuerst `cancel_move()`, der Lord steht dann wieder außer Engagement Range, und die Fähigkeit fiele aus dem FALSCHEN Grund aus. Die erste Fassung des Tests bestand deshalb unter dem Rückschritt; mit mitschreibenden Zuhörern an beiden Pfaden fällt sie. **A/B belegt:** Haken nach `_finish_charge()` verschoben → 2 Prüfungen fallen (vorher nur 1, nämlich der Quell-Wächter).
    - **Sein D6 hat DREI Ausgänge, nicht zwei** (1 nichts / 2-5 D3 / 6 D3+3), also entscheidet der erste Wurf die GRÖSSE des zweiten und nicht nur, ob es einen gibt. Alle drei Bänder einzeln gemessen — ein Test, der nur 1 und 6 wirft, besteht auch mit der Schwelle als "6+" geschrieben.
    - **Kein Once-per-Phase-Ledger, und das ist Absicht:** eine Einheit bekommt höchstens einen Charge-Zug pro Phase (`charged_squad_ids`) plus höchstens eine Heroic Intervention (15.11). Der Trigger IST die Grenze; ein Ledger obendrauf würde still den 15.11-Fall abschalten.
    - Dritter Konsument von `game/mortal_wound_abilities.py`s geteilter Maschinerie (Zielwahl, Prompt/Auto-Split, `MortalWoundAllocationSession`) — die Datei heißt jetzt "drei Fähigkeiten, ein Modul".
  - **Der Lokhust Lord brachte DREI Zweitträger und damit drei Umbenennungen** — siehe Fehlerklasse 11 oben. Sein Staff of Light ist die Zeile des Overlords bis auf die letzte Charakteristik, sein "Destroyer Cult" ist wörtlich die "Harbinger of Destruction" des Plasmancers, und seine Lord's Blade sind die Zahlen der Overlord's Blade unter anderem Namen.
  - **Driven by Hatred ist die vierte DESTROYER-CULT-Wiederholung und unterscheidet sich in DREI Dingen gleichzeitig** von ihren drei Geschwistern — jedes davon verschwindet, wenn man das Prädikat wie seine Nachbarn schreibt:
    - **beide Würfe** (Hit UND Wound), was sonst keine Quelle dieser Engine tut — sie steht deshalb an VIER Stellen (`_hit_reroll_reason`/`_wound_reroll_reason` in beiden Phasen), und eine Verdrahtung, die nur zwei erreicht, sähe von jeder einzelnen aus vollständig richtig aus. Als Zählung gepinnt (`.count(...) == 2` je Datei).
    - **pro MODELL** ("each time THIS MODEL makes an attack"), nicht pro Einheit. Das Angebot gilt aber einer GRUPPE, also gewährt `driven_by_hatred_applies_to_group()` nur, wenn JEDES Modell der Gruppe sie trägt — bewusst konservativ, denn andersherum würfelte man die Würfel eines Bodyguards auf dem Anspruch des Lords neu.
    - **KEINE Automatik-1en-Klausel**, also ist sie NICHT in `game/reroll_scope.py` einzutragen. Sie dort zu listen würde dem Spieler ein Nur-1en-Angebot machen, das der gedruckte Text nie gibt. Im Test als ABWESENHEIT geprüft — die einzige Stelle, an der sich das zeigt.
    - **"Below Half-strength" ist `is_below_half_strength()`** (Appendix, STRIKT kleiner), ausdrücklich nicht `is_at_half_strength()` (at-or-below, das Battle-Shock und Ard as Nails benutzen). Am GRENZFALL gemessen — genau bei der Hälfte greift sie nicht —, weil das die einzige Stelle ist, an der die zwei Definitionen sich unterscheiden. **A/B belegt:** auf die at-or-below-Fassung umgestellt → genau diese Prüfung fällt.
  - **Nanoscarab Amulet ist die erste FNP-Quelle, die ein reiner Pro-TOKEN-Wargear-Grant ist** ("the BEARER has Feel No Pain 5+"). Ein Lokhust Lord in sechs Destroyers gibt FNP an genau sich selbst — der Unterschied zu Rites of Reanimation nebenan, das "while this model is leading a unit" sagt und jeden Bodyguard deckt. Genau ein weiterer Fold in `current_feel_no_pain()`, wie dessen Docstring es einlädt.
  - **"One of the following" wird über `gear_slots = 1` erzwungen**, nicht über eine Bedingung in einem der beiden Items — gemessen, indem der Test BEIDE anfordert und einen bekommt. Und der Resurrection Orb bekam eine ZWEITE Effektfunktion: die des Overlords ist auf "hat den Tachyon Arrow abgegeben" gegated, diese nicht. Zwei Funktionen statt einer mit Flag, damit kein Datenblatt still die Bedingung des anderen erbt.
  - **"This model's staff of light can be replaced with 1 Lord's blade"**: der Staff ist EINE gedruckte Waffe mit einer Fernkampf- UND einer Nahkampfzeile, der Tausch gibt also BEIDE auf — diese Variante hat gar keine Fernkampfwaffe mehr. Gleiche Form wie der Voidscythe-Tausch des Overlords, und als eigene Testzeile ausgeschrieben.
  - **Beide Sprites lagen schon im Ordner** (`Skorpekh Lord.png`, `Lokhust Lord.png`) — die einzigen zwei Necron-Dateien OHNE das `Necron `-Präfix der anderen dreizehn. Der Ordner gewinnt, wie überall in dieser Tabelle. Die Verschattungsgefahr ist geprüft statt angenommen (`_key_for_name()` liefert beim ERSTEN Substring-Treffer zurück): weder enthält "Skorpekh Lord" den Schlüssel "Skorpekh Destroyers" noch umgekehrt, "Overlord" ist kein Teilstring von "Skorpekh Lord", und "Lokhust Lord" enthält keinen der beiden Lokhust-Trupp-Schlüssel.
  - **Punkte:** Skorpekh Lord 90 (1.-2. Einheit) / 100 (ab der 3.), Lokhust Lord flach 70. Keiner von beiden steht in der 13-Einträge-Liste des Users, es gibt hier also keine Listenspalte, der man widersprechen könnte.
  - **Getestet:** neu `test_skorpekh_lord.py` (**72/72**) und `test_lokhust_lord.py` (**66/66**), zusammen mit **acht** A/B-Sonden, von denen jede genau die Prüfungen kippt, die sie soll. Die drei Datenblatt-Zählpins in `test_necron_datasheets.py` (13 → 15) sind genau die sichtbare Einzeiler-Änderung, für die sie gesetzt wurden. Volle Regression **120 Suiten, ~7871 Prüfungen, 119 grün / 0 rot / 1 bekannt**, dazu alle vier Smokes und `selfplay.py map2` 2500 Frames — die Smokes hier nicht aus Gewohnheit, sondern weil `main.py`, `game/charge.py`, `game/fight.py`, `game/shooting.py`, `game/crit_hit.py` und `game/feel_no_pain.py` angefasst wurden, also die Angriffs- und die Schadenskette selbst.
  - **Arbeitshinweis:** die parallel laufende zweite Sitzung legte mittendrin `test_melee_weapon_groups.py` an (Nahkampf-Waffengruppen, Warpspider-Exarch), das kurzzeitig an einer noch fehlenden Ork-Konstante scheiterte — **nicht dieser Arbeit zuzuordnen**, null Überschneidung, und inzwischen von ihr selbst grün gemacht.
  - **Offen und bewusst so:** beide stehen in keiner Demo-Armee, und die KI hat für sie keinen eigenen Pfad — Crimson Harvest läuft über `auto_players` (die Zielwahl ist deterministisch nach `damage_value`), die zwei Reroll-/Krit-Grants brauchen gar keine Entscheidung.

- **Player 2s Necron-Liste revidiert: Illuminor Szeras und Lokhust Heavy Destroyers raus, Lokhust Lord / zweiter Plasmancer / Skorpekh Lord rein, eine ZWEITE Immortals-Einheit auf Tesla Carbines** (User lieferte die vollständige neue Liste). **15 Listeneinträge, 9 Einheiten nach SECHS Anbindungen, 68 Modelle**, Engine-Summe **2020 pts** gegen die 2050 der Liste.
  - **Sechs von sieben Charakteren führen jetzt etwas** (vorher drei von fünf): Overlord → Lychguard, Technomancer → Necron Warriors, Plasmancer → Immortals 1, Plasmancer → Immortals 2, Skorpekh Lord → Skorpekh Destroyers, Lokhust Lord → Lokhust Destroyers. **Nur der C'tan Shard steht allein**, und das ist eine Aussage: er ist der einzige Charakter dieser Liste ohne gedruckte LEADER-Zeile. Damit zahlt **Command Protocols an sechs der neun Einheiten** statt an dreien — die Detachment-Regel ist der eigentliche Gewinner dieser Revision.
  - **Die zwei Immortals-Einheiten sind der erste Fall im Repo, in dem zwei Kopien EINES Datenblatts verschiedene Wargear tragen.** "10 with Tesla carbine" ist der GANZE Trupp, also ist die Anzahl die Einheitengröße und nicht 1 — der Gegensatz zum Enmitic-Exterminator-Eintrag der alten Liste, wo genau EIN Modell tauschte. Damit leistet `unit_name()`s Kopiennummer zum ersten Mal echte Arbeit: die beiden unterscheiden sich in nichts anderem als ihrem Namen und ihrer Waffe.
  - **Der Lokhust Lord BEHÄLT seinen Staff of Light** ("Nanoscarab amulet, Staff of light"). Eigene Testzeile, weil seine einzige Waffenoption ihn gegen die Lord's Blade tauschen würde — und der Staff ist EINE gedruckte Waffe mit einer Fernkampf- UND einer Nahkampfzeile, der Tausch ließe ihn also ganz ohne Fernkampfwaffe.
  - **Die Skorpekh Destroyers nehmen jetzt EINEN Plasmacyte**, wo die alte Liste keinen nahm — also eine Nutzung des [DEVASTATING WOUNDS]-Grants über die ganze Schlacht (die Erlaubnis ist pro Plasmacyte, nicht pro Schlacht).
  - **Drei fremde Suiten sind daran zerbrochen, und alle drei zu Recht** — genau die sichtbaren Einzeiler-Änderungen, für die ihre Pins gesetzt wurden:
    - `test_army_select.py` pinnte `(10, 59, 2000)` → `(9, 68, 2020)`; und seine Zeile "ein allein stehender Charakter wird als Charakter geführt" nannte Szeras, der nicht mehr antritt.
    - `test_over_garrison.py` griff auf `"2 Skorpekh Destroyers 1"` und `"2 Lokhust Destroyers 1"` zu — beide heißen nach der Anbindung anders, und beide sind ein Modell größer. **Nebenbefund, der die Zeile ehrlicher gemacht hat:** ihr Kommentar behauptete, die Skorpekh Destroyers seien ein Assault-Trupp, weil sie "gar keine Fernkampfwaffen" hätten. Der Skorpekh Lord bringt einen Enmitic Annihilator mit — `is_assault_unit()` ist aber eine RATIO und keine Anwesenheitsprüfung, und eine 18"-Waffe auf einem von vier Modellen macht aus Hyperphase-Klingen keine Gunline. Der Trupp bleibt korrekt `assault=True`, die Begründung im Test war nur bis eben nicht von der falschen Lesart unterscheidbar.
    - `test_take_to_the_skies_policy.py` zählte "sechzehn behalten es" → **fünfzehn**: Szeras war eine eigene FLY-Einheit. Der neu hinzugekommene Lokhust Lord ersetzt sie NICHT, weil er in die Lokhust Destroyers merged, die ohnehin schon flogen — eine Einheitenzahl ist hier also genau das Falsche zum Raten.
  - **map3s Roster musste mitgezogen werden**: `"{p} Lokhust Destroyers 1"` heißt jetzt `"{p} Lokhust Destroyers 1 + Lokhust Lord"`. `BattleMap.fields()` matcht EXAKT, ein veralteter Name fieldet also nichts.
    - **Dabei ist eine echte Harness-Schwäche aufgefallen und behoben worden:** `main.py`s Roster-Wächter wirft `SystemExit` mit einer erklärenden Meldung, aber `selfplay.py` fing JEDES `SystemExit` ab und druckte danach "no exception" — über einen Lauf mit **0 Frames**. Ein lauter Wächter, den ausgerechnet der Harness stumm schaltet, der ihn sichtbar machen soll. `selfplay.py` lässt jetzt alles außer seinem EIGENEN `SystemExit(0)` durch (das ist sein MAX_FRAMES-Stopp). **Gemessen:** mit dem veralteten Namen jetzt Exit 1 plus die Wächter-Meldung, vorher Exit 0 und "no exception".
  - **`test_player2_necron_army.py` fragt die Totals jetzt den ECHTEN Builder** (`army_lists.get("necrons").build(...)`) statt seinen eigenen Roster nachzubauen. Die alte Fassung schrieb die Arithmetik der LISTE aus, um Fehlerklasse 17 zu entgehen — das hilft gegen eine veraltete ZAHL, lässt aber die FORM der Armee als zweite Kopie stehen, die man mitpflegen muss. Die handgebaute Hälfte bleibt für die Pro-Eintrag-Loadouts und wird gegen den Builder verglichen, aber über die FORM (welches Datenblatt führt welches, wie viele Modelle) statt über Namen — die Kopiennummern müssen dort zwangsläufig andere sein.
  - **Punkte: 10 von 15 Einträgen weichen ab, weiter in BEIDE Richtungen** (Engine 2020, Liste 2050). Fünf stimmen überein (beide Plasmancer, Skorpekh Lord, Technomancer, Canoptek Wraiths). Die Transkription gewinnt unverändert; die Abweichung ist benannt, nicht angeglichen. Der Lokhust Lord ist neu auf der billigeren Seite (70 gegen 80).
  - **Getestet:** `test_player2_necron_army.py` von 62 auf **76/76** neu geschrieben, `test_army_select.py` **236/236**, `test_over_garrison.py` **61/61**, `test_take_to_the_skies_policy.py` **33/33**. Volle Regression **120 Suiten, ~7886 Prüfungen, 119 grün / 0 rot / 1 bekannt**, dazu alle fünf Smokes und `selfplay.py` auf map2 (2000 Frames) UND map3 (800 Frames) — map3 hier keine Formalie, weil sein Teilroster angefasst wurde.

- **Absturz bei Isha's Fury: `NameError: name 'board_rect' is not defined` — ein Zweig der Event-Kette, den nie etwas erreicht hat, war gegen eine Signatur von vorgestern gebaut** (User: "spiel abgestürzt bei ishas fury").
  - **Reproduziert, bevor irgendetwas angefasst wurde, und zwar an der QUELLE:** ein AST-Lauf über die ~4000 Zeilen von `main()` sammelt jeden gelesenen freien Namen und vergleicht ihn gegen alles, was dort (oder auf Modulebene) je gebunden wird. Ergebnis: **genau EIN Treffer im ganzen `main()`**, `('board_rect', 3021)` — der gemeldete Absturz, ohne Rateanteil. Der Name der Brettfläche heißt überall sonst `board_rect_screen`.
  - **Es waren DREI Defekte in ZWEI Zweigen, und der gemeldete war nur der erste, der feuert.** Hinter dem NameError lag ein `token_at_event(state.tokens, event, board, board_rect)` — die alte VIER-Argument-Signatur (heute `(tokens, board, event_pos)`), also der nächste Absturz nach Behebung des ersten. Und beide Zweige hatten **gar keinen Event-Typ-Wächter**, griffen also auch auf einer KEYDOWN nach `event.pos`. Der Nachbarzweig (Grenade Pack Flyover) trug dieselbe Fäule in eigener Ausprägung: `token_at_event(state.tokens, event, camera)` — drei Argumente, aber die falschen, was als `AttributeError: 'Event' object has no attribute 'to_in'` endet statt als TypeError. Beide gemessen, nicht vermutet.
  - **Die Ursache ist die Unerreichbarkeit selbst, nicht ein Tippfehler.** Diese zwei Zweige laufen NUR, solange genau diese eine Fähigkeit eine Mortal-Wound-Zuteilung schuldet — kein Test im Repo fuhr sie je an (`grep token_at_event test_*.py` war leer, und für keine der beiden Fähigkeiten gab es eine Suite). **Vierte Instanz der "gebaut, aber nie GEFÜTTERT/erreicht"-Klasse** nach `VengefulStarsController`, der Mark-Verdrahtung und Path of the Outcasts fehlender Würfelbestätigung — und wie diese drei nur durch einen QUELL-Wächter zu fangen.
  - **Der Fix ist die kanonische Form ihrer fünf funktionierenden Geschwister**, nicht eine vierte Variante: Event-Typ + Taste, `board_rect_screen.collidepoint(event.pos)`, dann `token_at_event(state.tokens, board, event.pos)`. Damit sind alle sieben Mortal-Wound-Zweige buchstabengleich.
  - **Getestet:** neu `test_event_chain_wiring.py` (**11/11**) in drei Abschnitten — (1) der allgemeine, der den Absturz reproduziert: KEIN freier Name in `main()` darf ungebunden sein, plus die Zusicherung, dass `board_rect_screen` der eine Name der Brettfläche ist; (2) jeder `token_at_event()`-Aufruf hat die kanonische FORM, nicht nur die richtige Stelligkeit (`(tokens, event, camera)` ist auch dreistellig und scheitert anders); (3) jeder `pending_damage_choice`-Zweig, der `event.pos` liest, hat seinen MOUSEBUTTONDOWN-Wächter und seine Brett-Prüfung. Abschnitt 1 deckt jede künftige Zeile dieser Funktion ab, nicht nur diese zwei Zweige. **A/B mit der GANZEN Vor-Fix-Welt: 5/11**, und die erste rote Zeile nennt den gemeldeten Absturz wörtlich (`got [('board_rect', 3021)]`); sechs Prüfungen kippen, je zwei pro Defekt. Volle Regression **123 Suiten, ~8031 Prüfungen, 122 grün / 0 rot / 1 bekannt**, dazu alle vier Smokes und `selfplay.py map2` 4000 Frames — hier keine Formalie, weil `main.py`s Event-Kette selbst der geänderte Gegenstand ist.
  - **Benannt, nicht ungefragt behoben:** die Sperre "starte keinen neuen Deadly-Demise-Wurf / Emergency Disembark, solange noch ein Prompt offen ist" führt eine EIGENE, kürzere Liste als die Phasenwechsel-Sperre daneben (die über `is_busy` vollständig ist). Vier Controller fehlen ihr: `ishas_fury`, `grenade_pack`, `crushing_impact`, `fall_back` — zwei Stellen, dieselbe Frage, zwei Antworten (Fehlerklasse 10). Ein Modell, das an Isha's Fury stirbt, kann damit einen Deadly-Demise-Wurf öffnen, während die Zuteilung noch aussteht. Anderer Fehler als der gemeldete, und er ändert die Prompt-Reihenfolge — deshalb hier vermerkt statt nebenbei mitgeändert.

- **Player 1s Liste erneut revidiert: Shroud Runners raus, Windriders rein — und der Warlock Skyrunner steht zum ersten Mal nicht mehr allein** (User: "tausche bei der aeldari liste die shroud runner mit diesen windridern und packe den warlock skyrunner rein / 3x Windriders (80 pts): 3 with Close Combat Weapon, Shuriken Cannon"). Weiterhin 20 Listeneinträge und **74 Modelle**, aber **12 Einheiten** statt 13 und **1890 pts** statt 1900.
  - **Die zweite Hälfte der Bitte war schon vorbereitet, ohne dass es jemand geplant hatte.** Die LEADER-Zeile des Skyrunners ist ein JOIN, der ausschließlich WINDRIDERS nennt — er stand bisher allein, weil die Liste keine fieldete, und `test_player1_army.py` hielt genau das als geprüfte Tatsache an der PAARUNGSTABELLE fest ("steht allein da" statt "Anbindung vergessen"). Der Tausch bringt ihm den einzigen Partner, den er überhaupt haben kann; `attach()` würde jeden anderen ablehnen, ein falscher Griff wäre also gescheitert statt still gebaut worden. Wie die zwei Warlock Conclaves nennt dieses JOIN seine EIGENE Grenze statt 19.01s Leader-Slot zu belegen.
  - **Ein Eintrag weniger auf dem Tisch ist, wie eine Anbindung AUSSIEHT** — nicht eine verlorene Einheit. Die Modellzahl bleibt 74 (3 raus, 3 rein, und `attach()` merged, es fügt nichts hinzu und nimmt nichts weg). Genau diese Verwechslung ist an drei Stellen aufgeschlagen, und alle drei sind dieselbe Lehre: **eine EINHEITENZAHL ist das Falsche zum Raten, wenn gemergt wird.**
  - **"3 with Close Combat Weapon, Shuriken Cannon" ist die GANZE Einheit, nicht ein Modell-Upgrade** — die 3 ist die Truppgröße. Die Kanone ist einer der zwei Täusche gegen den Twin Shuriken Catapult; der andere (Scatter Laser) teilt sich mit ihm den Cursor, "3 von jedem" hätte sie also über verschiedene Modelle verteilt statt gestapelt. Im Test ist die NICHT genommene Alternative als eigene Zeile geprüft, weil genau daran die falsche Lesart sichtbar würde.
  - **Der Punkte-Mismatch ist von 12 auf 11 gefallen, und das ist der erste Eintrag dieser Liste, bei dem Engine und User-Liste ÜBEREINSTIMMEN**: beide sagen 80 für 3 Windriders. Die Shroud Runners, die sie ersetzen, waren einer der zwölf Abweichler (Liste 80, Transkription 90) — daher auch die 10 Punkte Differenz in der Armeesumme. Die Transkription wird weiterhin nicht überschrieben.
  - **`test_player1_army.py` ist zum DRITTEN Mal von Fehlerklasse 17 getroffen worden, und diesmal war die Gegenmaßnahme selbst zu schwach.** Es baut seinen eigenen Roster und blieb GRÜN, während es Shroud Runners und einen allein stehenden Skyrunner prüfte — eine Armee, die es nicht mehr gibt. Beim letzten Mal wurden dagegen die TOTALS als Rechnung der Liste ausgeschrieben; das fängt eine veraltete ZAHL, lässt aber die FORM der Armee als zweite, handgepflegte Kopie stehen — und stale wurde jedes Mal die Form. Abschnitt 5 fragt jetzt den ECHTEN Builder (`army_lists.get("aeldari").build(...)`), genau die Behandlung, die `test_player2_necron_army.py` für dieselbe Falle bekam: die handgebaute Hälfte bleibt für die Pro-Eintrag-Loadouts und wird gegen den Builder über die FORM verglichen (welches Datenblatt führt welches, wie viele Modelle) statt über Namen — die Kopiennummern müssen zwangsläufig andere sein. **Zwei Normalisierungen, und sie sind nicht dieselbe zweimal:** die führende Ziffer ist `unit_name()`s OWNER-Präfix, die nachlaufende die Kopiennummer. **A/B belegt:** mit dem Vor-Tausch-Builder und dem neuen Test fallen zwei Prüfungen (die Form UND die Summe) — die alte Fassung war in genau dieser Welt vollständig grün. Die Modellzahl bleibt in der neutralisierten Welt zufällig richtig, was der Grund ist, warum die FORM die tragende Prüfung ist.
  - **Drei fremde Pins sind gefallen, alle drei zu Recht:**
    - `test_army_select.py`: `(13, 74, 1900)` → `(12, 74, 1890)`.
    - `test_take_to_the_skies_policy.py`: "fünfzehn behalten es" → **vierzehn**. **Zum zweiten Mal aus demselben Grund** — beim Lokhust Lord stand schon im Kommentar, dass eine Einheitenzahl hier das Falsche zum Raten ist. Shroud Runners und Windriders fliegen BEIDE (netto 0), der Skyrunner war eine eigene FLY-Einheit und ist jetzt in ihnen aufgegangen. Der Kommentar führt jetzt beide Schritte auf.
    - `smoke_setup_screens.py`: "Player 2 fieldet die ganze Aeldari-Liste (13 Einheiten)" → 12. Dieser Smoke spielt die Aeldari als Player **2**, belegt also nebenbei weiter, dass die Liste für jeden Spieler baut. `--neutralize` scheitert unverändert.
  - **Eine echte VERHALTENSänderung, gemessen statt weggestimmt: die Aeldari-Home-Garnison ist jetzt die RANGERS.** Der Skyrunner war mit 55 Punkten die billigste Einheit im SHOOTER-Band und damit die Wahl; gemergt ist er gar kein designierbarer Kandidat mehr. Gemessen auf map2 (nötige Reichweite 14.8"): die Rangers sind mit 60 Punkten das, was am Boden desselben Bandes übrig bleibt — **5 Punkte teurer für 12" mehr Reichweite** (36" Long Rifle gegen 24"), auf genau dem Objective, für das diese Regel existiert. Die Regel selbst ist unverändert; nur ihr billigster Kandidat ist weg. Auf allen drei Karten dasselbe Ergebnis. **Der Ork-Pin bleibt unberührt**, was weiterhin die Gegenprobe ist.
    - **Benannt, nicht ungefragt behoben:** die Rangers sind INFILTRATORS (24.20), werden in der Aufstellung also ZULETZT sortiert und geben ihre Sonder-Aufstellung faktisch auf, um auf dem Home Objective zu sitzen. Legal (eine eigene Zone ist für einen Infiltrator ein zulässiger Ort) und kein Fehler, aber eine Qualitätsfrage, die niemand gestellt hat — eine eigene Messreihe wert, kein Nebenbei-Fix.
  - **Die Basisgrößen-Notiz hat ihre PRÄMISSE verloren und ist deshalb neu geschrieben, nicht stillschweigend eingelöst.** Als die drei Jetbike-Einheiten auf 45 mm gebracht wurden, hielt die Notiz ausdrücklich fest, die Windriders blieben auf ihren gedruckten 32 mm, weil sie "in keiner Demo-Armee" stünden — der Skyrunner passte damit erstmals nicht zu dem Jetbike, dem er sich anschließt, aber nur theoretisch. Jetzt sitzt eine 45-mm-Base wirklich in einem Trupp aus 32-mm-Basen, also genau die Form, die die Skorpekh-Lord-Notiz "die Stelle, an der der Unterschied auffiele" nennt. Das ist eine GAMEPLAY-Zahl (`edge_distance()` liest den Radius, also ziehen Engagement Range, Überlappung, Kohärenz und Formations-Packen mit), deshalb wird sie BENANNT statt aufgeräumt: gemessen funktioniert es (alle 4 Modelle werden aufgestellt, Kohärenz hält über einen ganzen Selbstspiellauf). Der Pin in `test_warlock_skyrunners.py` trägt die neue Lage jetzt im Klartext.
  - **map3 ist unberührt** — sein Aeldari-Teilroster nennt weder Shroud Runners noch Windriders (Guardian Defenders + Farseer + Conclave, Dark Reapers, Falcon, Wraithguard), geprüft statt angenommen, weil `BattleMap.fields()` EXAKT matcht und ein veralteter Name still nichts fieldet.
  - **Getestet:** `test_player1_army.py` **89/89** (neu geschrieben, siehe oben), `test_army_select.py` **236/236**, `test_home_garrison.py` **79/79**, `test_take_to_the_skies_policy.py` **33/33**, `test_warlock_skyrunners.py` **55/55**. Volle Regression **123 Suiten, ~8058 Prüfungen, 122 grün / 0 rot / 1 bekannt**, dazu alle fünf Smokes (`smoke_pregame.py` auf map1 UND map2, `smoke_setup_screens.py` inkl. `--neutralize`, `smoke_log_input.py`, `smoke_measure_tool.py`, `smoke_end_turn_warning.py`) und `selfplay.py map2` 2000 Frames. Die Smokes hier keine Formalie: eine Anbindung fasst Aufstellung, Kohärenz und Zielwahl an. **Im echten Spiel belegt:** `[deploy] 1 Windriders 1 + Warlock Skyrunners (shooter) deployed at (9.9,35.9)`, `ist eine Attached Unit (19.01)`, und der Trupp taucht in der Bedrohungsrechnung der KI als Schussbedrohung auf (2.8-4.2/Zug), die Kanonen leisten also wirklich Arbeit.

## Die restlichen Aeldari-Datenblätter (27 Stück, sieben Etappen)

**Aeldari geht von 27 auf 54 Datenblätter** (User: "ziel restliche aeldari datasheets holen,
abspeichern und einbauen. in etappen / keine ki pfade nötig / keine legends / keine titanischen";
Aircraft, Harlequins und die Ynnari-Drukhari-Einträge auf Nachfrage ebenfalls ausgeschlossen).
Damit ist die Fraktion die zweite nach T'au, deren engine-native Abdeckung vollständig ist.

**Der Umfang ist GEMESSEN, nicht geschätzt.** Aus `rules/.cache/aeldari.html`: 99 Datenblöcke,
minus 27 gebaute, 23 Legends (`sLegendary`), 2 Forge World (`FW_logo2`), 2 TITANIC
(`tooltip_contentTitanic` in der Keyword-Leiste), 2 Aircraft, 8 Harlequins, 8 Ynnari-Drukhari
= **27**. **Stonesinger und D-cannon Platform sind NICHT titanisch** — eine naive Textsuche meldet
sie, weil ihr REGELTEXT "excluding TITANIC units" enthält. Das Keyword steht nur bei den zwei
Wraithknights wirklich in der Leiste.

| Etappe | Einheiten | Warum zusammen |
|---|---|---|
| 1 | Wraithlord, Wraithblades | geteiltes Wraith-Vokabular, einziges vorhandenes Sprite |
| 2 | D-cannon / Shadow Weaver / Vibro Cannon Platform | EIN Chassis, drei Datenblätter → EINE Suite (Kroot-Shaper-Muster) |
| 3 | Fire Prism, Night Spinner, Vypers | Falcon-Rumpf bzw. Windrider-Waffenmenü |
| 4a/4b | Warlock, Spiritseer, Farseer Skyrunner / Autarch, Autarch Wayleaper, Maugan Ra | schließt die Reverse-Leader-Lücken des Rosters |
| 5 | Dragon Knights, Clanblade, Leystalker, Stonesinger | geschlossene Sub-Fraktion EXODITE |
| 6 | Voidreavers, Voidscarred, Skyreavers, Starfangs, Kharseth, Prince Yriel | alle ANHRATHE |
| 7 | Yvraine, The Visarch, The Yncarne | YNNARI |

### Etappe 0 — der Korpus musste zuerst verallgemeinert werden

`fetch_datasheet_rules.py`s Dedupe war ein IDENTITÄTSTEST auf ein einziges Faction-Objekt
(`if faction is tau_empire.TAU_EMPIRE`). `MISSING_BY_FOLDER` ist jetzt eine `folder`-gekeyte
Tabelle — und das ist der Mechanismus, der **jedes gebaute Datenblatt null Wartung kosten lässt**:
der Name wandert von `MISSING_*` nach `faction.datasheets`, die Gesamtzahl bleibt gleich. Am Ende
von Etappe 7 belegt: die drei Ynnari stehen genau EINMAL im Korpus, `rules/aeldari/` trägt 74
Datenblätter plus `army_rules.md`, und zwei `--offline`-Läufe erzeugen **222 byte-identische**
Dateien.

### Sechs Extraktionen, alle am ZWEITEN Konsumenten

`fight_after_death.py` (18., geteilt von Undying Spite 4+ und Malevolent Souls 3+ — inklusive der
vier Hälften von "zurück auf dem Brett"), `activation_reroll.py` (19., Targeting Array und Crystal
Matrix, die sich nur in `shared_use` unterscheiden), `cp_discount.py` (20., am VIERTEN Konsumenten:
Puretide, My Will Be Done, War Leader), `battle_shock_after_shooting.py` (21.),
`conditional_devastating_wounds.py`, `objective_control.py`-Nachbarn. Dazu
`game/detection_range.py`-Stil-Umbenennungen, wo ein Name log.

### Was diese Etappen an ECHTEN Fehlern gefunden haben

- **`protocol_sudden_storm.maybe_offer_advance_reroll()` war gebaut, unit-getestet und wurde
  von `main.py` NIE aufgerufen** — und sein eigener Docstring platzierte es NACH `acknowledge()`,
  wo `DiceManager.reroll_die()` grundsätzlich ablehnt (es braucht `pending_values`). Fünfter Fall
  der "gebaut, aber nie GEFÜTTERT"-Klasse. Jetzt aus EINER Stelle VOR `acknowledge()` angeboten,
  für Sudden Storm und Superlative Strategist zusammen.
- **`MissilePodProfile` trug die BS des DROHNEN-Datenblatts fest verdrahtet** — unsichtbar,
  solange nur Drohnen ihn benutzten, falsch ab dem ersten BATTLESUIT-Träger.
- **`UnitProfile.support_weapon` wurde von KEINEM Datenblatt gesetzt**, obwohl Etappe 2 die drei
  SUPPORT-WEAPON-Plattformen mit dem Keyword in der `keywords`-Leiste gebaut hat. Damit konnte
  `branching_fates.py`s "excluding SUPPORT WEAPON models"-Klausel auf genau den Einheiten nicht
  feuern, für die sie geschrieben war — sie stand als "kein SUPPORT-WEAPON-Datenblatt existiert
  hier" im Kommentar, was seit Etappe 2 falsch war. Gefunden, weil Word of the Phoenix der ZWEITE
  Leser derselben Klausel ist. Beide sind jetzt scharf.
- **Sechs Aeldari-EPIC-HEROes setzten `epic_hero` nicht** (Asurmen, Avatar, Baharroth, Eldrad,
  Jain Zar, Lhykhis), obwohl ihre Datenblätter das Keyword drucken — also war **Regel 15.03 (Epic
  Challenge) für sie still inert**. Dieselbe Klasse wie die CHARACTER-Lücke, die dieselbe Fraktion
  schon einmal hatte. Aufgefallen, weil die Mythic Stance des Visarch die erste Waffe im Repo ist,
  die `[ANTI-EPIC HERO]` druckt. Als **fraktionsweite Invariante** gepinnt (jedes Datenblatt, das
  das Keyword druckt, setzt die Flagge), nicht als sechs Einzelzeilen.
- Ein `.index()` in einem Reihenfolge-Wächter **stürzte ab, statt rot zu werden** — ersetzt durch
  einen `find()`-Helfer, dieselbe Lehre wie bei den zwei `str.index()`-Wächtern der T'au-Etappe.
- Der AST-Wächter fing zweimal einen freien Namen in `main()` (`strategic_reserves_controller`,
  das gar kein Controller ist sondern ein MODUL; und ein `random`, das dort nie gebunden ist).
  Beide genau die Klasse, für die er existiert.

### Etappe 7 — die drei Ynnari, und warum sie ein Satz sind

Alle drei drucken **Servant Of The Whispering God** ("deine Armee darf keine Nicht-YNNARI-EPIC-
HEROes enthalten") — eine **LISTENBAU-Beschränkung, also ein belegter No-op**: es gibt keinen
Armeebau-Schritt, die Liste steht beim Schlachtbeginn fest, es gibt keinen Moment, in dem sie
feuern könnte. Benannt und gepinnt statt weggelassen. Ebenso **Disparate Paths**, die YNNARI-
ARMEEREGEL, die als zweite FACTION-Zeile auf dem Datenblatt steht — Armeeregeln baut diese Engine
aus der `ArmyList`, nicht aus einem Datenblatt.

- **Der Asu-var des Visarch hat DREI Stances**, wo jede andere Mehrprofilwaffe des Repos zwei hat.
  `overcharge_profile` ist EIN Link, also werden sie VERKETTET (quicksilver → duellist → mythic),
  und nur die erste wird vergeben — sonst führte er drei Schwerter.
- **Way of the Blade ist die DRITTE Quelle von Fights First** und die erste, die weder die eigene
  gedruckte 24.13-Fähigkeit noch 11.04s Nachcharge-Grant ist. Sie faltet deshalb in
  `squad_has_fights_first()`, die eine Stelle, die das beantwortet — irgendwo sonst hätte
  `FightController`s AKTIVIERUNGSREIHENFOLGE eine zweite Meinung bekommen, und die Reihenfolge ist
  der ganze Inhalt von 24.13.
- **Yvraine's Champion: drei Wörter tun echte Arbeit** ("OTHER" schließt den Visarch selbst aus,
  "CHARACTER models" die Bodyguards, "while LEADING" ist 24.22). Jedes einzeln gemessen, weil das
  Weglassen jedes einzelnen eine Fähigkeit ergibt, die weiter feuert und bloß weiter ist.
  **Rückgabewert ist `"-"`, nicht `None`** — der No-FNP-Sentinel, den jede andere Quelle liefert;
  mit `None` kollabierte `_better_threshold()` acht fremde Suiten.
- **Word of the Phoenix ist der sechste Modell-Rückholer** und der mit den meisten
  Danebengriff-Möglichkeiten: vier Qualifikatoren, alle vier Beschränkungen. "BODYGUARD models"
  wird aus `AttachedComponent.role` gelesen — der Provenienz, die `attach()` ohnehin führt —, nicht
  aus dem Aussehen der Modelle. **ZWEI Würfel, also zwei Fenster**: `DiceManager` hält einen Wurf,
  der D6-Gate und der D3+1-Zähler können sich keins teilen.
- **Inevitable Death ist Fuegans Unquenchable Resolve mit umgedrehtem Pfeil**: derselbe
  Ringlauf, dieselbe Engagement-Range-Pflicht — aber es ist der Tod eines ANDEREN, der ein die
  ganze Zeit lebendes Modell bewegt, also geht nichts auf oder von der `destroyed_models`-Liste.
  **"once in each OPPONENT'S turn"** ist nach Zugbesitzer gekeyt; als "einmal pro Zug" gelesen
  hätte es jede Runde einen zweiten Teleport verschenkt.
- **Ethereal Forms D3 wird IM MODUL geworfen, nicht über den DiceManager** — bewusste Ausnahme
  von der Sichtbarkeitsgewohnheit: es feuert im Todes-SWEEP, wo Deadly Demise und die
  Notausstiegs-Queue schon um das eine Wurffenster streiten (genau die Kollision, die
  `deadly_vectors.py` festhält und dort durch eine andere Naht gelöst wurde — hier gibt es keine
  andere Naht). Das LOG trägt Wurf und Heilung getrennt.
- **Zwei Wächter waren gegenseitig maskiert**: `ethereal_form_applies()` und der Pro-Modell-Filter
  können auf einem gebauten Roster nie widersprechen, weil kein Datenblatt den Yncarne mit
  irgendetwas anderem in eine Einheit bringt. Die gemischte Einheit wird deshalb von Hand gebaut —
  die einzige Art zu fragen, welcher der beiden die Arbeit tut, und die Antwort muss der
  Pro-Modell-Filter sein, weil das gedruckt ist.

**Getestet:** sieben neue Suiten — `test_wraith_constructs.py` (139), `test_support_weapon_platforms.py`
(120), `test_aeldari_gun_tanks.py` (102), `test_aeldari_psykers.py` (100),
`test_autarchs_and_maugan_ra.py` (129), `test_exodites.py` (128), `test_corsairs.py` (135),
`test_ynnari.py` (**153**). Für Etappe 7 **23 A/B-Sonden an der QUELLE, alle beißend** — vier
bissen zunächst nicht, und alle vier waren Befunde über den TEST (Fehlerklasse 24): eine Klausel,
die kein gebautes Paar erreichen kann, ein "up to", das mit mehr Würfeln als Leichen nichts
beschränkt, ein voll geheilter Statist, der einen Filter nicht beweisen kann, und eine Sonde, die
hinter einer Docstring einfügte. Volle Regression **147 Suiten, ~11264 Prüfungen, 146 grün /
0 rot / 1 bekannt**, alle fünf Smokes, `selfplay.py` auf map2 UND map3, und
`python run_tests.py --smoke` komplett grün.

**Bewusst offen:** keines der 27 steht in einer Demo-Armee, keines hat einen KI-Pfad (User-Vorgabe,
als Negativraum geprüft: kein Name taucht in `ai/agent_driver.py` auf), und außer `Wraithlord.png`
hat keines ein Sprite — alle Abwesenheiten sind am MODELL gepinnt, damit späteres Hinzufügen eine
sichtbare Änderung ist.

## Die sieben Aeldari-Detachment-REGELN

**Aeldari geht von einem auf acht modellierte Detachments** (User: "jetzt folgende detachment
regeln in Etappen: Aspect Host, guardian battle host, warhost, Windrider hist, spirit conclave,
armoured warhost, path of the outcast"). Der Korpus trägt 15 Aeldari-Detachments; diese sieben
sind gebaut.

**Umfang ist auf User-Entscheidung die REGEL, nichts sonst.** Die sieben drucken zusammen 36
Stratagems und 24 Enhancements (hier stand zuerst 30 — nachgezählt am Korpus sind es
6+6+6+6+6+3+3; die falsche Zahl hatte ausgerechnet die beiden Detachments übersprungen, die
weniger als sechs drucken); die bleiben Daten und sind die nächste Arbeit — dieselbe
Dreiteilung wie beim T'au-Nachzug (6 Regeln → 25 Stratagems → 19 Enhancements). `stratagems=`
und `enhancements=` sind deshalb LEER, mit dem Grund darüber. **Die Aeldari-Liste fieldet
weiter Seer Council** (User-Entscheidung): die sieben sind deklariert und einzeln per
`selfplay.py` verifiziert, aber nichts am Default-Spiel ändert sich — dieselbe Behandlung wie
die 27 Datenblätter, die in keiner Demo-Armee stehen.

| # | Detachment | DP | Regel | Naht |
|---|---|---|---|---|
| 1 | Armoured Warhost | 1 | Skilled Crews | Adjuster-Kette + `coldstar.weapon_has_assault()` |
| 2 | Path of the Outcast | 1 | Far-Reaching Doom | `detection_range.py` (vierte Quelle) |
| 3 | Guardian Battlehost | 2 | Defend at All Costs | `_hit_modifiers()` ×2 |
| 4 | Aspect Host | 3 | Path of the Warrior | automatische 1er-Rerolls ×4 + Wahl |
| 5 | Warhost | 3 | Martial Grace | `battle_focus.py`, drei Klauseln |
| 6 | Windrider Host | 2 | Ride the Wind | zwei Ankunfts-Tore + Zugende-Rückzug |
| 7 | Spirit Conclave | 2 | Shepherds of the Dead | neunte Feindmarke + Battle-Focus-Aura |

### Etappe 0 — drei Voraussetzungen

- **`ASURYANI` ist ein eigenes Feld, kein `battle_focus`-Ersatz.** `Datasheet` hat jetzt
  `faction_keywords` — die ZWEITE gedruckte Keyword-Zeile. Gemessen: **54** Aeldari-Datenblätter
  setzen `battle_focus`, aber nur **51** drucken ASURYANI; das Ynnari-Triumvirat druckt die
  Armeeregel und gehört zu YNNARI. Genau zwei davon sind PSYKER — also die Menge, die Spirit
  Conclaves "ASURYANI PSYKER" ausschließen muss. Mit dem Flag als Stellvertreter wäre die Klausel
  an der EINZIGEN Stelle falsch gewesen, an der sie beißt.
  - **Die Zeile ist NICHT ein Keyword pro Datenblatt** — 41 drucken BEIDE (die meisten
    Craftworld-Einheiten dürfen in einer Ynnari-Armee stehen). Erste Transkription war falsch und
    wurde vom Korpus-Vergleich sofort gefangen.
  - **Die zehn ASURYANI-only sind kein Zufall: sie sind Servant Of The Whispering God in den
    Daten.** Ein Ynnari-Heer darf keine EPIC HEROes ohne YNNARI enthalten, also können diese zehn
    das Keyword nicht tragen — und es sind exakt die zehn, die `epic_hero` setzen. Daraus
    abgeleitet statt von Hand gelistet, gegen den Korpus gepinnt.
- **`game/detachment_gate.py` (22. Extraktion).** `has_detachment()` lag in
  `game/tau_detachments.py`, liest aber nur eine `config`-Konstante und weiß von keiner Fraktion.
  Mit dem ersten Nicht-T'au-Konsumenten ist das der lügende Name (Fehlerklasse 11).
  `tau_detachments.py` re-exportiert, also weiter EINE Definition; im Test als Identität gepinnt.
  Dazu **`game/aeldari_detachments.py`** als Spiegel: `is_aeldari_unit` kam aus
  `psychic_guidance._is_aeldari` — einem PRIVATEN Namen in einem DATENBLATT-Modul, in den
  **dreizehn** andere Module hineingriffen.
- **Nebenbefund mitgefixt: die sechs Seer-Council-Stratagems waren ungegatet.** Solange Seer
  Council das EINZIGE Aeldari-Detachment war, waren "eine Aeldari-Armee" und "eine
  Seer-Council-Armee" dieselbe Menge, also waren sie zufällig richtig. Mit acht wäre eine
  Warhost-Armee im Besitz von Strands-of-Fate-Stratagems. Alle sechs lesen jetzt
  `strands_of_fate.has_detachment()`. **Isha's Fury fragt den REAKTOR, nicht den Beweger** —
  eigene Testzeile, weil die andere Lesart sich gut liest.

### Was die sieben an echter Mechanik gekostet haben

- **Skilled Crews muss an ZWEI Stellen ankommen.** [ASSAULT] in die Adjuster-Kette ist die
  Hälfte, die man sieht; die Hälfte, für die das Detachment gekauft wird, ist
  `coldstar.weapon_has_assault()` — Advance-und-Schießen (24.04). Ein Grant nur in der Kette
  sähe verdrahtet aus und täte genau das Falsche nicht.
- **Far-Reaching Doom heißt nach der REGEL, nicht nach dem Detachment.** `game/path_of_the_outcast.py`
  ist die RANGERS-DATENBLATT-Fähigkeit gleichen Namens und teilt kein Wort Text. Von beiden Seiten
  gepinnt. **Richtung ausgeschrieben:** Detection Range gehört dem VERSTECKTEN Modell, +6" auf die
  Feinde macht sie von WEITER WEG sichtbar; in BEIDEN Bändern gemessen (15" und die 12"-Hauswandregel).
- **Defend at All Costs: "and/or" ist ein ODER** — drei der vier Brettlagen zahlen, jede eine
  eigene Testzeile. **Und die Granularität ist die KOMPONENTE, nicht die Einheit**: der eigene
  Test hat gefangen, dass ein Farseer, der Guardian Defenders führt, das GUARDIANS-Keyword seiner
  Leibwache geerbt hätte. Jetzt über `AttachedComponent.starting_models` gelesen, mit genau
  diesem realen Paar als Testfall.
- **Path of the Warrior ist eine ECHTE Wahl** (zwei exklusive Optionen), also ein Prompt — der
  Gegenfall zu Herald of Ynnead, dessen eine Option reiner Gewinn war. Gelesen an **vier**
  Stellen, und zwar in den `automatic_ones`-Disjunktionen, NICHT in den Reroll-Reason-Methoden:
  jede Klausel ist eine schlichte Pflicht-1er-Wiederholung ohne "you can" und ohne "instead".
  Kein `reroll_scope`-Eintrag, als Abwesenheit gepinnt.
- **Martial Grace' drei Klauseln liegen alle in `battle_focus.py`** — das Detachment fügt keine
  Mechanik hinzu, es dreht an der vorhandenen. **Welche Manöver wirklich einen D6 werfen, ist
  GEMESSEN**: von sechs nur Opportunity Seized und Fade Back, beide durch EINEN Aufruf. Sudden
  Strike ist der Beinahe-Treffer — seine "up to 6"" ist eine Distanz, kein Würfel.
- **Ride the Winds Rundenklausel gilt NUR fürs Aufstellen** und erreicht deshalb BEIDE
  Ankunfts-Tore in `ingress.py` (20.03s Runde-2-Sperre und die Runde-3-Zonenlockerung). Der
  Zähler selbst bleibt unberührt — VP, Missionen und die Zerstörung übriger Reserven lesen weiter
  die echte Zahl. **Zwei der vier Klauseln sind gemessene No-ops**: 20.01 lässt ohnehin jede
  Einheit in Reserve, und BATTLELINE liest bei Aeldari kein Modul.
- **Shepherds of the Dead ist die NEUNTE Feindmarke und die erste, die ein TOD setzt** — also
  kein `offer_*`, sondern der Todes-Sweep. Zwei Dinge, die keine der acht anderen hat: sie ist
  KUMULATIV ("one or more tokens") und sie LÄUFT NIE AB (kein `reset_turn`/`reset_phase`) — genau
  die Abwesenheit, die ein späterer Leser "repariert", deshalb gepinnt.

### A/B-Sonden: 85, alle beißend — und fünf Befunde über den TEST

Je Etappe eine Sondendatei, jede neutralisiert EINE Klausel an der QUELLE.
**Fünf bissen zunächst nicht, und alle fünf waren Fehlerklasse 24** — eine ZWEITE Bedingung
verdeckte die geprüfte:

1. 19.03-Pooling bei `faction_keywords`: jedes BODYGUARD-Datenblatt druckt beide Keywords, die
   eigene Zeile des Squads antwortet also immer zuerst — der Komponenten-Lauf entscheidet nie.
2. Ride the Winds ASURYANI-Hälfte: nichts MOUNTED ist Ynnari, die Prüfung kann auf dem gebauten
   Roster nicht diskriminieren.
3. Spirit Guides' Keyword-Filter: der Nicht-Wraith-Testfall stand ausserhalb der Aura und wurde
   aus dem falschen Grund abgelehnt.
4. Aspect Hosts Reroll-Reason-Wächter war eine TAUTOLOGIE (`... or True`).
5. Der Etappe-6-Sondenlauf hatte eine um eins zu hohe BASELINE, wodurch jede Sonde trivial "biss".

Die ersten drei sind jetzt von Hand isoliert (ein konstruierter Fall, weil der Roster keinen
hergibt) — dieselbe Behandlung wie die zwei sich gegenseitig maskierenden Ethereal-Form-Wächter.

**Getestet:** neu `test_aeldari_detachment_rules.py` (**369/369**, acht Abschnitte) plus **85
A/B-Sonden**. Volle Regression **148 Suiten, ~11671 Prüfungen, 147 grün / 0 rot / 1 bekannt**,
alle fünf Smokes, `python run_tests.py --smoke` komplett grün, und **ein echter
`selfplay.py map2`-Lauf je Detachment** (alle exit 0, alle innerhalb des 3-DP-Budgets legal).

**Bewusst offen:** die 24 Enhancements der sieben. Die 36 Stratagems sind gebaut — siehe den
eigenen Abschnitt darunter. Kein KI-Pfad (stehende Aeldari-Vorgabe, als Negativraum geprüft — kein
neuer Name in `ai/agent_driver.py`); und keine Demo-Armee ändert sich.

**KORREKTUR eines Befundes aus dieser Sitzung:** `test_report_20260824.py` wurde hier zeitweise
als bekannter Fehlschlag (61/65) eingetragen. **Das war ein `__pycache__`-Artefakt, kein echter
Fehlschlag.** Nach `find . -name __pycache__ -exec rm -rf {} +` meldet die Suite dreimal
hintereinander **65/65**. Die Fehldiagnose entstand, weil die A/B-Sondenskripte dieser Sitzung den
Cache im Sekundentakt löschen und neu schreiben — genau die Rennbedingung, die dieses Repo als
Fehlerklasse 19 führt ("ein Fehlschlag direkt nach vielen Edits erst WIEDERHOLEN, dann suchen").
Die Wiederholung war deterministisch und hat mich deshalb in die falsche Richtung geschickt: vier
gezielte Reverts und ein HEAD-Worktree-Lauf später stand fest, dass keine meiner Änderungen
schuld war — der Cache war es. **Lehre: bei einem Fehlschlag nach einem Sondenlauf zuerst den
Cache löschen, nicht bisecten.** Der HEAD-Worktree-Lauf (58/64) misst eine ÄLTERE Fassung der
Suite und sagt über den heutigen Stand nichts.

## Die 36 Aeldari-Detachment-STRATAGEMS (sieben Etappen)

**Alle 36 sind gebaut** (User: "jetzt die stratagems jedes detachment eine Etappe / keine KI
pfade"), eine Etappe je Detachment, aufsteigend nach Aufwand. **35 Dateien für 36 Stratagems**:
Skyborne Sanctuary steht in Warhost UND Aspect Host, WHEN/TARGET/EFFECT byte-identisch, also EIN
Modul mit zwei Controller-Instanzen — der Gate ist ein Konstruktorargument, kein zweites File.

| Etappe | Detachment | Präfix | # |
|---|---|---|---|
| 1 | Armoured Warhost | `armoured_` | 3 |
| 2 | Path of the Outcast | `outcast_` | 3 |
| 3 | Guardian Battlehost | `guardian_` | 6 |
| 4 | Windrider Host | `windrider_` | 6 |
| 5 | Warhost | `warhost_` | 5 (+ das geteilte) |
| 6 | Spirit Conclave | `conclave_` | 6 |
| 7 | Aspect Host | `aspect_` | 5 (+ das geteilte) |

**`game/proactive_stratagems.py` ist der Grund, warum 36 tragbar sind.** `ActionPanel.draw()`
nimmt 81 `=None`-Parameter durch eine dreistufige, streckenweise POSITIONELLE Kette — 36 weitere
wären 36 Gelegenheiten für genau den Fehler, dessen Narbe die Datei trägt. Ein proaktives
Stratagem tritt der Registry mit `can_use`/`use`/`panel_label` bei; das Panel wurde für die 36
**zweimal** angefasst, beide Male für MOVE-Routing und nie für einen Knopf (Overflight und
Warhosts Fire and Fade brauchen einen eigenen Confirm-Zweig, weil sie Konsequenzen "if it does"
tragen bzw. `active_player` zurückgeben müssen).

### Die vier Extraktionen dieser Etappen

| # | Modul | Am wievielten Konsumenten |
|---|---|---|
| 21 | `game/move_exceptions.py` | 09.06/09.07s Ausnahmen lagen als DREI hartkodierte Ketten in zwei Dateien |
| 22 | `game/detachment_gate.py` | `has_detachment()` lag in einem T'au-Modul und kannte keine Fraktion |
| 23 | `game/engagement.py` | 03.04s "within Engagement Range", dreimal ausgeschrieben, mit zwei weiteren Konsumenten |
| 24 | `game/ignore_characteristic_modifiers.py` | Seer's Eye (AP+D), dann Warrior Focus (+S) |

- **`move_exceptions` führt VIER Fragen, nicht eine**, und das ist gedruckt: Vectored Engines hebt
  einen Bann auf, Time to Strike zwei, Feigned Retreat zwei ANDERE, Wind of Blades alle vier. Vier
  Mengen, jede mit eigener Quellliste; eine Pauschale hätte Wind of Blades' Umfang still an alle
  verteilt. **Die vierte Frage hat keine Datenblatt-Quelle:** [ASSAULT] ist, wie eine WAFFE nach
  einem Advance feuert (24.04) — diese Stratagems befreien die EINHEIT, also wäre ein Keyword-Grant
  eine stillschweigende Verbreiterung dessen, was [ASSAULT] bedeutet.
- **`engagement.is_engaged()` unterscheidet sich GEMESSEN von `Squad.is_engaged()`**: letzteres
  filtert keine Toten, weil `remove_dead_models()` einmal pro Frame läuft. Beide Einheiten leben →
  gleich; der Feind gerade ausgelöscht → **True gegen False**; die eigene Einheit ausgelöscht →
  ebenso. Für eine Ende-der-Phase-Klausel ist das der Unterschied zwischen Angebot und Ablehnung.
  **`Squad.is_engaged()` ist bewusst NICHT geändert** — Schussberechtigung, Charge und Fall Back
  lesen es, das ist eine eigene Messreihe. Benannt und gegeneinander gepinnt.
- **`ignore_characteristic_modifiers` löst das Problem, das AP und Damage KEINE Modifikatorliste
  haben.** Der Trefferwurf hat eine (`game/modifiers.py`, drei Filter darauf); S/AP/D entstehen als
  flache Werte auf einer Kopie, mit jeder Quelle bereits überschrieben. Also **per VERGLEICH**: die
  angepasste Waffe gegen ihre eigene GEDRUCKTE Klasse, das Bessere je Charakteristik. Kein Ledger,
  und es kann nicht aus dem Takt geraten, weil es die Ausgabe der Kette selbst liest.
  **"Besser" läuft in zwei Richtungen** (S höher, AP negativer, D höher) — ein einzelnes
  `min()`/`max()` wäre für die Hälfte richtig. Eine gewürfelte Damage-Notation bleibt unangetastet.
  "Any or all" wird AUTOMATISCH aufgelöst, dieselbe Lesart, die Kauyon und 24.29 [PSYCHIC] schon
  ausschreiben.

### Neue Nähte, die es vorher nicht gab

- **`ChargeController.on_charge_move_finished`** — Etappe 3 (Crushing Strides ist der vierte Nutzer).
- **`FallBackController` veröffentlicht ZWEI Momente**, und die zwei Karten stehen ein Wort
  auseinander: `on_fall_back_declared` ("is SELECTED to Fall Back", Khaine's Vengeance) in
  `declare()`, `on_fall_back_finished` ("just after it FALLS BACK", Feigned Retreat) in `confirm()`
  — letzteres NUR bei geglücktem Zug, und VOR dem Desperate-Escape-Wurf, weil der eine Folge EINER
  Art Fall Back ist und nicht Teil davon.
- **`IngressController.ingressed_this_turn`** — "set up from Reserves THIS TURN" (Death from on
  High). `Squad.set_up_this_turn` setzt JEDE Platzierung inkl. Aufstellung; `ingressed_this_phase`
  ist die richtige TATSACHE auf der falschen UHR (sie stimmt in Schuss/Nahkampf nur, weil
  `reset_movement_phase()` noch nicht wieder lief — ein Ordnungszufall).
- **`crit_hit_threshold(weapon=)`** — Blitzing Firepowers zweite Klausel ist eine Eigenschaft der
  WAFFE; jede Quelle davor gehörte dem Modell oder seiner Einheit.
- **`weapon_range` bekommt einen ÜBERSCHREIBUNGS-Term**, seinen ersten: sein Docstring sagte "THE
  TERMS ADD" (drei Quellen, alle +6"). Doom Inescapable SETZT 18".
- **`FightAfterDeath(bonus_for=)`** — To Their Final Breaths +1 variiert PRO EINHEIT innerhalb
  einer Phase, kann also nicht in die feste Schwelle gefaltet werden.
- **`can_embark(range_in=, require_move=)`** und **`Squad.embark_locked_until_end_of_turn`** — das
  Gegenstück zu `charge_locked_until_end_of_turn`, das es seit fünf Regeln gibt.
- **`MortalWoundOfferController` hat den Unterstrich verloren** — privat, solange alle fünf
  Subklassen im selben Modul wohnten; Crushing Strides ist der sechste und wohnt woanders.

### Was diese Etappen an ECHTEN Fehlern gefunden haben

1. **`move_exceptions.clear_turn_flags()` wurde von NIRGENDS aufgerufen** — sechster Fall der
   "gebaut, aber nie GEFÜTTERT"-Klasse, und meiner aus Etappe 1. Jede "bis zum Ende des Zuges"-
   Ausnahme hätte den Rest der Schlacht gelaufen; ein Kommentar in `main.py` behauptete den Sweep.
   Beide Suiten waren grün, weil sie ihn selbst rufen. **Gefegt wird über JEDE Einheit**, nicht über
   `ending_squads`: ein Zug ist EINES Spielers Zug, also beendet jedes Zugende ein solches Latch.
2. **`overflight_controller` wurde nie an das Panel ÜBERGEBEN** — Etappe 4 ergänzte den Parameter,
   Etappe 5 fand die tote Verdrahtung. Ein Panel-Wächter sieht das nicht; die AUFRUFSTELLE muss
   geprüft werden.
3. **Die WRAITH CONSTRUCTs hatten Battle Focus, das sie nicht drucken** — siehe den eigenen
   Abschnitt darunter.

### Vier Regel-ENTSCHEIDUNGEN, die keine Transkription sind

- **Blitzing Firepowers "if such a weapon ALREADY has that ability"** wird am GEDRUCKTEN Profil
  entschieden, nicht an der Instanz aus der Kette. Sonst zählte eine Dire-Avenger-Katapult in
  Halbdistanz als "hat bereits", weil Bladestorm es gerade gewährt hat — und die Antwort hinge
  davon ab, welcher Adjuster zuerst lief. Die andere Lesart ist vertretbar und im Modul benannt.
- **Seer's Eye liest AELDARI PSYKER**, wie gedruckt (User-Entscheidung), obwohl Soul Bridge daneben
  ASURYANI sagt — in dieser Engine zwei verschiedene Mengen.
- **Doom Inescapable ist als OVERRIDE geschrieben, obwohl "+6" heute dasselbe ergäbe.** Gemessen:
  die Wailing Doom druckt **12"**, nicht 24" (ich hatte 24 angenommen und lag falsch), also ist 18"
  eine VERLÄNGERUNG. Sobald eine der drei bestehenden +6"-Quellen dieselbe Waffe erreicht, läse ein
  Bonus 24", wo die Karte 18" sagt.
- **"You can remove one Aspect Shrine token" wird GEFRAGT, nicht aufgelöst** (Preternatural
  Precision, To Their Final Breath) — anders als "any or all modifiers", wo kein Zweig je schlechter
  ist. Hier sind beide Zweige lebendig: der Token ist ein Einmal-pro-Schlacht-Würfeltausch.

### A/B-Sonden: 259 über sieben Etappen, alle beißend

Je Etappe eine Sondendatei, jede neutralisiert EINE Klausel an der QUELLE (31 / 39 / 46 / 40 / 42
plus die früheren). **Etwa 20 bissen zuerst NICHT**, und fast alle waren Befunde über den TEST
(Fehlerklasse 24). Die wiederkehrenden Formen, weil sie sich wiederholen werden:

- **Eine ZWEITE Quelle desselben Effekts verdeckte die geprüfte.** Death from on High gegen eine
  [TWIN-LINKED]-Waffe; Blitzing Firepower auf Dire Avengers, die BLADESTORM drucken; Warrior Focus
  auf Dark Reapers, die INESCAPABLE ACCURACY drucken. Jedes Mal hätte die Prüfung mit UNVERDRAHTETEM
  Stratagem bestanden.
- **Rule 15.01s Einmal-pro-Phase verdeckte den zweiten Kauf** — derselbe `StratagemController`
  wiederverwendet, also lehnte `can_use()` aus dem falschen Grund ab. Fünfmal aufgetreten; jetzt
  bekommt jeder zweite Kauf einen frischen Controller.
- **Der Wächter matchte seine eigene ERKLÄRUNG.** `"aspect_shrine.usable(" not in src` fand den
  Docstring, der ausschreibt, warum es NICHT gerufen wird — dieselbe Form wie der
  `max_per_battle`-Fall der T'au-Etappe. Jetzt wird der AUFRUF geprüft.
- **`str.index()` in einem Reihenfolge-Wächter STÜRZT AB statt rot zu werden**, zum dritten Mal in
  diesem Repo. Es gibt jetzt `before(src, first, second)` in der Suite, und der Docstring nennt die
  drei Vorfälle.
- **Eine falsche BASELINE macht jede Sonde trivial "beißend"** — zweimal passiert (BASE um eins zu
  hoch, dann um 23 zu niedrig). Die Zahl gehört nach jedem Suite-Zuwachs nachgezogen.
- **Zwei Sonden waren GEMESSENE No-ops**, kein Testfehler: Soul Bridges drei Datenblattnamen SIND
  auf diesem Roster exakt die WRAITH-CONSTRUCT-Menge, und die zwei Nahkampf-Wailing-Doom-Zeilen sind
  eigene Klassen (keine Unterklassen der Fernkampfzeile), sodass der `isinstance`-Test sie ohnehin
  ausschließt. Beide Tatsachen sind jetzt gepinnt, statt als Testlücke dazustehen.

**Getestet:** `test_aeldari_detachment_stratagems.py` (**965/965**, acht Abschnitte) plus die
Sonden. Der Abschnitt-7-Zählsweep zählt die Module je Präfix und verlangt von jedem, dass es auf
sein Detachment gatet und seinen gedruckten Regeltext zitiert — ein 37. kann nicht auftauchen, ohne
dass diese Zeile sich bewegt. Volle Regression **153 Suiten, ~12980 Prüfungen, 152 grün / 0 rot /
1 bekannt**, `python run_tests.py --smoke` komplett grün, und **ein echter `selfplay.py map2`-Lauf
je Detachment** mit dieser Liste temporär gefieldet.

**Kein KI-Pfad** (User-Vorgabe), für alle 36 als Negativraum geprüft. **Keine Demo-Armee ändert
sich** — die Aeldari-Liste fieldet weiter Seer Council.

## WRAITH CONSTRUCTs hatten Battle Focus, das sie nicht drucken

**Vom User beim Lesen von Spirit Conclave bemerkt** ("wraith constructs wie zum beispiel
wraithguard haben gar kein battle focus. sie dürfen also außerhalb von dieser detachment regel gar
keine agile manouver benutzen. das ist jetzt noch nicht so oder?"). Richtig, und die Folge war
größer als die Frage.

**Gemessen gegen den Korpus:** SECHS Datenblätter setzten `battle_focus`, obwohl ihr gedrucktes
Blatt **gar keine FACTION-Zeile** trägt, während jedes Aeldari-Blatt MIT der Armeeregel
`FACTION: **Battle Focus**` druckt — die drei WRAITH CONSTRUCTs (Wraithguard, Wraithblades,
Wraithlord) und die drei SUPPORT-WEAPON-Plattformen. Es ist **nicht** "Wraith Constructs haben es
nie": der Wraithknight DRUCKT es. Pro Datenblatt, deshalb ist der Korpus die Instanz und keine
Faustregel.

**Die eigentliche Folge:** `battle_focus.has_battle_focus()` hat seit dem Bau von Spirit Conclave
eine TEMPORÄRE Quelle — Spirit Guides, "while a WRAITHBLADES, WRAITHGUARD or WRAITHLORD unit is
within 12" of this model, that unit HAS the Battle Focus ability". Die Aura gewährte also, was ihre
Ziele bereits dauerhaft besaßen: **die halbe Detachment-Regel war inert.** Nach der Korrektur
gemessen: Wraithguard allein `False` → in 12" eines Spiritseers `True` → Psyker geht weg `False`.

**Fünf Suiten wurden zu Recht rot**, alle Pins auf das falsche Flag. Der bezeichnendste stand in
`test_aeldari_detachment_rules.py` und stammte von mir: *"all three named datasheets already print
Battle Focus"*, mit dem Kommentar, die Aura sei "a near-no-op on the built roster, measured". **Ein
Pin, der den Fehler als Regel protokolliert hatte.** Alle fünf behaupten jetzt die korrigierte
Tatsache samt Grund.

**Lehre für die nächste Fraktion:** ein Armeeregel-Flag gehört gegen die FACTION-Zeile des Korpus
geprüft, nicht gegen die Fraktionszugehörigkeit — `test_aeldari_detachment_stratagems.py`s
Abschnitt 6z tut das jetzt für JEDES gebaute Aeldari-Datenblatt und würde ein siebtes sofort nennen.
