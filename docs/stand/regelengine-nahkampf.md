# Regelengine: Nahkampf

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

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
- **Counteroffensive (15.12) war ein 2-CP-No-op: das Reaktionsfenster feuert NACH der
  Entscheidung, auf die es wirken soll** (User: "ich habe gerade counter offinsive benutzt, aber
  die ki hat dann trotzdem zugeschlagen. cp wurden abgezogen").
  - **Reproduziert am gemeldeten Brett, bevor irgendetwas angefasst wurde**
    (`logs/game_20260901_142406.log` Z. 440-447): CP abgezogen ✓, `fights_first` gesetzt ✓,
    `forced_next_fighter["Player 1"]` gesetzt ✓ — und `whose_turn` stand auf **Player 2**, also
    war die einzige wählbare Einheit die der KI. Der Grant tat buchstäblich nichts.
  - **Die Ursache ist eine REIHENFOLGE im Trichter, nicht ein fehlendes Feld.**
    `_actually_finish_current_fight()` ruft `_settle_turn_state()` **vor**
    `on_unit_finished_fighting()`. 12.04s Alternation ist also entschieden, bevor der Grant
    existiert — und niemand rechnete sie danach neu. `eligible_to_select_now()` liest
    `forced_next_fighter.get(self.whose_turn)`, fragt also den FALSCHEN Spieler. Ausgelöst wird
    es genau dann, wenn der Gegner noch eine Fights-First-Einheit hat und der Reagierende keine:
    dann gibt der Settle den Zug direkt zurück. Im gemeldeten Spiel hatten beide KI-Einheiten
    gechargt (11.04).
  - **`FightController.force_next_fighter(player, squad)` ist die eine Definition** und tut BEIDE
    Hälften: die Einschränkung setzen UND die Alternation an den Reagierenden übergeben.
    `counteroffensive.py` schrieb direkt ins Dict und konnte die zweite deshalb vergessen — die
    Form, die dieses Repo laufend konsolidiert. **Der Klassen-Docstring behauptete ausdrücklich,
    die zweite Hälfte sei unnötig** ("with no extra bookkeeping needed here"); er ist korrigiert
    statt gelöscht, weil die falsche Annahme der eigentliche Fehler war.
  - **`sub_step` wird bewusst NICHT auf FIGHTS_FIRST zurückgedreht.** "Must be the next unit you
    select to fight" ist die stärkere der zwei gedruckten Klauseln und narrowt ohnehin; ein
    Rückspulen gäbe jeder ANDEREN Fights-First-Einheit einen zweiten Durchgang durch einen
    bereits beendeten Sub-Step. Als Testzeile im REMAINING-Fall gepinnt.
  - **`_settle_turn_state()` bleibt jetzt bei einem Spieler mit offener Einschränkung** — sonst
    könnte der FIGHTS_FIRST-Durchgang den Zug gleich wieder weggeben. Dort geprüft statt sich
    darauf zu verlassen, dass der Grant vorher `fights_first` gesetzt hat: die beiden sind damit
    nicht reihenfolgeabhängig.
  - **`_forced_fighter_for()` ist die geteilte LESE-Definition** (Fehlerklasse 10), gelesen von
    Auswahl, Announce und Settle. Ohne sie sagte die Announce "select a unit (A, B)", während nur
    A wählbar war — genau die Diagnosezeile, die die strittige Zahl auslässt.
  - **Nebenbefund:** die Optionsliste des Prompts kam aus einem SET, ihre Reihenfolge war also
    lauf-instabil. Jetzt nach Namen sortiert.
  - **Getestet:** neu `test_counteroffensive.py` (**38/38**, acht Abschnitte) — **vorher gab es zu
    15.12 GAR KEINEN Test**, und das ist der Grund, warum es überlebt hat: ein Test, der den
    Controller direkt treibt, sieht jedes Feld korrekt gesetzt; nur die ALTERNATION zeigt die
    fehlende Hälfte. **A/B mit der GANZEN Vor-Fix-Welt: 26/38**, und die roten Zeilen nennen das
    gemeldete Verhalten wörtlich. **Zwei eigene Testfehler, beide Fehlerklasse 24:**
    `wounds_remaining` statt `current_wounds` (das Modell blieb lebendig, der Lapse-Fall prüfte
    nichts) und `Log.find()` liefert die ERSTE Zeile, also die Announce der KI vom Phasenbeginn.
- **Fights First (24.13) entscheidet die REIHENFOLGE, nicht die Berechtigung** — es als dritte Art
  von "kampfberechtigt" zu lesen ließ Einheiten 18" vom Gegner am Ende jedes Zuges eine Auswahl
  verlangen.
- **Battle Focus' Sudden Strike hat ZWEI Fenster, und das zweite ist eine User-Entscheidung**
  (User: "bei dem battle focus Sudden Strike stimmt was nicht ... ich kann mich ja auch 6"
  consolidaten. das wird mir aber nicht angeboten beim consolidate"). Der gedruckte TRIGGER ist ein
  einziger Moment ("when an eligible unit is selected to fight"), der EFFEKT nennt aber **zwei
  Züge** — Pile-in UND Consolidation.
  - **Der Grund ist die Schrittfolge dieser Engine, nicht Laxheit.** 12.03 Pile In ist ein eigener
    Schritt VOR jeder Kampfauswahl, 12.07/12.08 Consolidation ein eigener Schritt DANACH. Der
    gedruckte Triggermoment liegt also ZWISCHEN den zwei Zügen, die der Effekt nennt: wörtlich
    genommen kommt er für die Pile-in-Hälfte zu spät und zwingt die Consolidate-Hälfte, blind
    bezahlt zu werden. Fenster 1 (vor dem Kampf, Form des mit Orks E2 stillgelegten Unbridled Carnage) gab es genau für die
    erste Hälfte schon; Fenster 2 (vor dem Consolidation-Zug) ist derselbe Fix für die zweite.
  - **Reproduziert vor der Änderung:** Gegner zerstört, der nächste 4.5" entfernt, Fight-Step
    fertig — `determine_mode()` gab **None**, es wurde also gar keine Consolidation angeboten, und
    `can_sudden_strike()` war schon zu (die Einheit steht in `fought_squad_ids`, was
    `can_consolidate()` ja gerade verlangt: die zwei können sich nie gleichzeitig zeigen). Die 6"
    hätten den Modus geöffnet, waren aber nicht mehr kaufbar.
  - **"Schuldet noch einen Consolidation-Zug" wird `ConsolidateController.can_consolidate()`
    gefragt**, nicht neu abgeleitet — das IST die eine Definition davon, und eine zweite Kopie ist
    die Drift, die dieses Repo laufend konsolidiert.
  - **Das Relevanz-Tor fragt `determine_mode(squad, reach=SUDDEN_STRIKE_RANGE_IN)`** — also
    wörtlich "würde dieser Token überhaupt eine Consolidation öffnen". Der Reach wird als PARAMETER
    übergeben statt `sudden_strike_active` probeweise zu setzen: das läuft pro Frame aus dem Panel,
    und eine Sonde, die das Squad mutiert, lässt den Grant stehen, wenn dazwischen etwas wirft.
  - **Zwei Absagen, beide "nie anbieten, was nichts kauft"** (Fehlerklasse 5): ein Consolidation-Zug,
    der schon LÄUFT (das Budget ist bei `start_consolidate()` vergeben, ein Token danach setzt nur
    ein Flag, das niemand mehr liest), und ein Brett, auf dem auch bei 6" nichts erreichbar ist.
  - **Verdrahtung:** `battle_focus_pool.consolidate_controller` wird in `main()` NACH dem
    `ConsolidateController`-Konstruktor gesetzt (Fehlerklasse 23; der AST-Wächter in
    `test_event_chain_wiring.py` prüft genau diese Reihenfolge). Das Panel behält EINE Zeichenstelle
    für beide Fenster: der Knopf steht über "Fight", und weil "Fight" im Consolidation-Schritt weg
    ist, landet derselbe Knopf dort direkt über "Consolidate".
  - **Getestet:** `test_battle_focus.py` von 150 auf **168/168** (Abschnitt 9b: der gemeldete Fall
    end-to-end durch die echten Controller bis auf 6.0" gemessen, der Ongoing-Fall wo das Manöver
    den MODUS nicht ändert und die Distanz doch, beide Absagen, Fenster 1 unverändert, die
    Nebenwirkungsfreiheit von `determine_mode(reach=)`, und ein echter `ActionPanel`-Render im
    Consolidation-Schritt, bei dem genau ein Knopf einen Token ausgibt). **Fünf A/B-Sonden an der
    QUELLE, alle beißend** (Fenster 2 ganz entfernt → 165/168 und die Meldung wörtlich zurück;
    Relevanz-Tor auf 3" → 166; Lauf-Absage weg → 167; Fenster 1 entfernt → 166; `determine_mode`
    ignoriert den Reach → 166).
- **Die drei Movement-Manöver werden an EINER Stelle gezeichnet, gelesen von BEIDEN
  Bewegungszuständen.** Gemeldet: *"battle focus +2 Movement wurde beim unteren guardian trupp
  nicht angeboten, obwohl ich noch tokens hatte. diese fähigkeit kann mehrmals angewendet werden
  pro phase."*
  - **Die REGEL war richtig, und das ist der Kern.** `REPEATABLE_PER_PHASE` setzt
    `army_rules.md:23` („more than once per phase, provided a different unit performs it each
    time") korrekt um, `test_battle_focus.py:128-133` pinnt es seit Langem. **Im Log der
    gemeldeten Partie reproduziert** (`logs/game_20260911_100813.log:303`): der Avatar gibt einen
    Token aus, danach ziehen in DERSELBEN Phase sieben weitere Einheiten — beide
    Guardian-Trupps darunter, einer mit Advance — und kein zweites Swift as the Wind, bei 3
    Token in der Hand.
  - **Das PANEL war der Fehler:** der Manöver-Block lag nur im `else`-Arm von
    `_draw_movement_ui()`, also verschwanden alle drei Knöpfe beim Druck auf „Move", und nach
    dem Confirm schloss `moved_squad_ids` Swift as the Wind endgültig. Der Docstring des
    Controllers versprach seit jeher das Gegenteil (*"Offered until the unit's move is
    CONFIRMED"*), und `use_swift_as_the_wind()` legt die +2" wirklich mitten im Zug nach — es
    fehlte nur der Knopf. Der Test pinnte das **auf Pool-Ebene**; der Panel-Test rief nur
    `select()`. Das ist das strukturelle Loch.
  - **Star Engines war schlechter dran als das gemeldete Manöver:** sein Gate verlangt
    `advance_bonus_by_squad`, gesetzt erst von `start_run()` — und `start_run()` ist nur aus dem
    MOVING-Arm erreichbar. Sein gedruckter Trigger-Moment war also GAR NIE anbietbar.
    **Sudden Strike gehört ausdrücklich NICHT dazu** und bleibt, wo es ist:
    `_before_consolidating()` lehnt eine laufende Consolidation selbst ab und sagt warum.
  - **Der Explainer musste BEIDE Hälften decken.** `refusal_reason()` ist NICHT die Negation von
    `can_*()` — die TRIGGER-Prüfungen (Phase, Zugbesitzer, `moved_squad_ids`, VEHICLE) stehen in
    den `can_*` und fehlen dort. Ein direkter Insane-Bravery-Port druckte eine Battle-Focus-Zeile
    auf JEDER Einheit JEDER Nicht-Aeldari-Armee, jeden Frame. `why_not()` gibt deshalb
    `(False, None)` für „hatte die Regel nie" und „der Trigger ist gar nicht offen"; die drei
    `can_*` sind seither ABLEITUNGEN daraus, also kann eine Regel keine zwei uneinigen Leser
    haben. Der Move-Typ wird über `MovementController.NORMAL_ADVANCE_FALL_BACK_MODES` gelesen
    (Extraktion am zweiten Konsumenten — dieselbe Prosa stand in `confirm_move()`), sonst böte
    ein künftiger `start_surge_move()` das Manöver auf einem Trigger an, den die Regel nicht nennt.
  - **Getestet:** `test_battle_focus.py` 195 → **231/231** (§14 rendert bei `state == MOVING`,
    mit einem Spion als Liveness — ein Render, der in einen anderen Dispatch-Arm fällt, zeichnet
    null Knöpfe und erfüllt jede Abwesenheitsprüfung), `test_event_chain_wiring.py` §23 (die
    SYMMETRIE per AST), plus `ab_battle_focus_mid_move.py` (**9 A/B-Sonden, alle beißend**).
    **Zwei eigene Testfehler dabei, beide gemessen:** §14 benutzte zuerst §8s GETEILTEN
    ShootingController, der seit einem früheren Abschnitt in `choosing_target` steckt — der
    Render fiel damit auf den Schuss-Screen und maß gar nichts; und der Fall-Back-Fall ohne
    Feind lässt `start_fall_back_move()` still ablehnen (09.07 verlangt Engagement), sodass der
    `else`-Arm zeichnete und die Prüfung aus dem falschen Grund bestand.
  - **Im ECHTEN Spiel belegt** (`verify_battle_focus_mid_move.py`): **2 Manöver-Knöpfe während
    eines laufenden Zuges** (`Swift as the Wind - +2" Move this phase (4 token(s))`) gegen
    `--neutralize`s **0**, bei identischem Staging. **Zwei gestellte Tatsachen, beide benannt:**
    der laufende Zug (`ai/agent_driver.py` fährt `start_move()`, Sweep und `confirm_move()`
    synchron in EINEM `take_one_action()`, also wird kein MockAgent-Frame je mit `MOVING`
    gerendert), und Aeldari auf BEIDEN Seiten — gemessen verbringt der Lauf sonst alle 2813
    gerenderten Frames in PLAYER 2s Bewegungsphase, weil selfplay nur Player 2 auto-spielt.
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

### [ASSAULT] wird an ZWEI Stellen gelesen, und drei von vier Grants kannten nur eine

**Gemeldet: "Stratagem 'Protocoll of the sudden storm' scheint nicht funktioniert zu haben. ich
konnte nach dem vorrücken nicht mehr schießen mit den necron kriegern."** Fehlerklasse 10 in
ihrer teuersten Form — die zweite Stelle beantwortet nicht bloß anders, sie beantwortet gar nicht.

- **Die zwei Leser sind verschieden weit auseinander, als man denkt.**
  `ShootingController._adjusted_weapon()` ist die SCHADENS-Mathematik — leicht zu verdrahten,
  leicht zu testen, und genau das, was jeder Unit-Test eines solchen Stratagems prüft.
  `coldstar.weapon_has_assault()` — erreicht aus `shooting.available_shooting_types()` — ist das
  EINZIGE, was entscheidet, ob eine Einheit nach einem Advance überhaupt schießen darf (10.05).
  Das ist der ganze Grund, warum [ASSAULT] gewährt wird. Ein Grant, der nur die Kette erreicht,
  sieht fertig aus und tut das eine nicht, wofür bezahlt wurde.
- **`weapon_has_assault()`s eigener Docstring hatte das für Skilled Crews AUSGESCHRIEBEN** ("a
  grant that reached only the chain would look wired while failing to do the one thing the
  detachment is bought for") — und drei der vier ausgelieferten Grants standen trotzdem nicht
  darin. Eine Warnung, die nur an einem Träger steht, wird beim nächsten nicht gelesen.
- **Reproduziert vor jeder Änderung**, am gemeldeten Log (`game_20260903_212846.log` Z. 652-655:
  gekauft, `advance (D6: 6)`, danach feuert in der Schussphase nur der Doomsday Ark — 20 Würfel
  = 2 Gauss Flayer Arrays × (5 + 5 Rapid Fire), nicht die 20 Krieger) und an der Quelle: eine
  Necron-Warriors-Einheit, die Advanced ist, bekommt `[]` statt `['Assault']`, WÄHREND
  `protocol_sudden_storm.adjusted_weapon()` das Keyword korrekt gewährt.
- **Behoben für Sudden Storm und Mortarion's Teachings** (beide sind ein Squad-Flag, also je ein
  Term). **Mont'kas Killing Blow blieb zunächst als benannte Lücke draußen** — seine Bedingung
  ist `doctrine_active(..., turn_tracker)`, und diese Funktion bekommt keinen Tracker. Ihn
  nachzureichen heißt, ein Argument durch `_attack_groups()`s elf Aufrufstellen auf dem heißesten
  Schusspfad zu fädeln; **eine HALBE Fädelung wäre schlimmer als der Status quo** (Zeile 578
  böte Assault Shooting an, `_weapon_eligible_for_type()` ließe dann null Waffen durch — eine
  Sackgasse statt einer verpassten Gelegenheit).
  - **KORREKTUR (2026-09-06): hier stand „kein ausgeliefertes Roster fieldet Mont'ka, es ist also
    dormant statt falsch" — das stimmt seit dem 2026-09-05 nicht mehr.** `tau_montka` fieldet
    Mont'ka, und Killing Blow gewährt [ASSAULT] JEDER Fernkampfwaffe dieser Armee in den Runden
    1-3. Die Lücke ist also LIVE und nicht dormant: die Liste kann in ihren ersten drei Runden
    nicht advancen und schießen, obwohl ihre Detachment-Regel genau das kauft. Die Abwägung gegen
    eine halbe Fädelung bleibt unverändert; nur „kostet heute nichts" ist falsch geworden. Der
    Wächter unten nennt sie weiterhin namentlich.
  - **GESCHLOSSEN am 2026-09-07** (T'au-Stratagem-Audit, Fund F3) — **ohne die Fädelung, gegen die
    hier zweimal argumentiert wurde**: die Bedingung wird EINMAL je Phasenwechsel ausgewertet und
    als `Squad.montka_killing_blow` gestempelt (`montka.refresh_killing_blow()`, aus DERSELBEN
    `is_active()`, die die Adjuster-Kette liest — nie gegen ein Rundenliteral, sonst löschte ein
    Literal das von *Exemplar of the Mont'ka* geweitete Fenster still und NUR am Advance-Tor).
    `weapon_has_assault()` endet damit auf `montka.grants_assault(squad)`, und
    `_ASSAULT_GRANT_GAPS` unten ist **leer**. Der Eintrag steht als vollständige Geschichte da,
    weil die Lehre nicht der Fix ist: die Rechtfertigung dieser Lücke ist ZWEIMAL abgelaufen,
    während die Zusicherung grün blieb — was ein BENANNTER Gap tut und eine Mengendifferenz nicht.
- **Der Wächter ist eine MENGENDIFFERENZ an der QUELLE** (`test_event_chain_wiring.py`
  Abschnitt 7), nicht ein Verhaltenstest: jedes `game/*.py`, das zur Laufzeit `.assault = True`
  vergibt, muss in `weapon_has_assault()`s Rumpf genannt sein. Ein Verhaltenstest kann einen
  FÜNFTEN Grant nicht sehen, der noch gar nicht existiert. Mont'ka steht als dokumentierte
  Ausnahme drin und muss dort trotzdem NAMENTLICH vorkommen, sonst verschwindet die Lücke
  stillschweigend. Der Sweep sieht heute vier Module und verlangt ≥4, ist also nicht vakuum-grün.
- **Getestet:** `test_awakened_dynasty.py` 82 → **89/89** (Abschnitt 4b: der gemeldete Fall
  end-to-end, BEIDE Leser einzeln, plus die Gegenproben Melee und Zugende — Abschnitt 4 maß
  ausschließlich `adjusted_weapon()` und war durchgehend grün, genau deshalb hat das überlebt);
  `test_death_guard_stratagems.py` 129 → **135/135**. **A/B an der QUELLE:** Vor-Fix-Welt
  wiederhergestellt → 87/89 bzw. 133/135, und die roten Zeilen nennen das gemeldete Verhalten
  (`got [], want ['Assault']`).
- **Im ECHTEN Spiel belegt** (`verify_sudden_storm_wiring.py`, `runpy` auf `selfplay.py`s echte
  `main()`-Schleife): die Einheit des Berichts — `2 Necron Warriors 1 + Technomancer` — kauft das
  Stratagem auf dem echten Brett und beantwortet die Advance-Frage danach mit **`['Assault']`**;
  mit der faithful Vor-Fix-Welt (nur der GATE ist blind, die Kette gewährt weiter) mit **`[]`**.
  **Die MockAgent-Grenze greift hier wörtlich:** über 14 000 Frames kommt die Kombination
  „gekauft UND advanced UND geschossen" nie zustande, die Sonde stellt die Advance-Tatsache
  deshalb selbst her und fragt die ECHTE Modulfunktion gegen die ECHTE Tokenliste.

### +A in der Nahkampfkette erreichte die Würfel nicht (Mecha Orks G3, 2026-09-19)

`FightController._begin_resolution()` zählte die Attacken von den ROHEN `pairs`
(`attacks_for(m, w)`, und die Würfelnotation von `pairs[0][1]`), während jeder +A-Grant auf der
Kopie aus `_adjusted_weapon()` lebt: Might Is Right (+3), Rokkit Charge (+1), The Stars Are Right
(×3) - jede Suite prüfte die Kopie. Gemessen: ein gechargter Warboss warf dieselben 10 Trefferwürfel
wie ein ungechargter; nach dem Fix 13. Die Zählstelle liest jetzt die angepasste Waffe (fest UND
Notation), die weitergereichte bleibt die rohe (keine Doppelanwendung) - die Form, die
`shooting.py` für Psychic Communion an SEINER Zählstelle schon hatte. `test_event_chain_wiring.py`
**§31** pinnt die Zählstelle und nennt jedes Modul, das `attacks` auf einer Kopie schreibt, mit dem
Leser, der es zählt. Gefunden beim Bau von Unbridled Carnage und Ferocious Show-off, siehe
`## Mecha Orks G3: Green Tide`.
