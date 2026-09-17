# Würfelpanel und Einheiten-Auswahl

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Das Würfelpanel: nichts fliegt mehr heraus, und Crit-Labels sind Plaketten

**Gemeldet:** *"die würfel fliegen optisch aus dem würfelpanel wenn es zu viele werden. die größe
des würfelpanels muss sich anpassen. außerdem hätte ich die Labels für crits bei lethal oder
sustained gerne etwas auffälliger."*

**EINE Zahl, zweimal ausgerechnet** — die häufigste Fehlerform dieses Repos, hier sichtbar auf dem
Bildschirm. `draw()` zählte die Würfel pro Reihe mit `DICE_GAP` (12), `_draw_dice_row()` setzte sie
mit dem breiteren Crit-Label-Abstand (26). Zehn Würfel maßen damit **734 px in einem 640-px-Panel**
und hingen **47 px über JEDE Seite** — und weil Crit-Labels genau bei den großen Salven auftreten
(Sustained/Lethal), trifft es die Fälle, in denen ohnehin viele Würfel liegen.
Reproduziert gegen die EIGENE Backdrop-Rect des Panels (`last_backdrop_rect` und `_die_rects` sind
beide schon aufgezeichnet), also gefragt, wo es die Dinge wirklich hingelegt hat, statt das Layout
nachzurechnen.

- **`_row_gap()` ist jetzt die eine Definition**, gelesen von der Zählung UND vom Setzen. Sie ist
  außerdem **an der Plakette GEMESSEN** statt eine Konstante zu sein: ein Label ist so breit wie
  seine Wörter, und `CRIT_LABEL_DICE_GAP = 26` war ein Schätzwert, der mit der Schriftgröße nicht
  mitwuchs — zwei Plaketten standen dadurch 10 px auseinander. Jetzt
  `Plakettenbreite − Würfelbreite + CRIT_LABEL_SEPARATION`, also passt sich die Reihe an
  „SUSTAINED HIT" (Abstand 37) und „DEVASTATING WOUND" (65) unterschiedlich an.
- **Der Abstand verrät weiterhin nichts, solange die Würfel rollen.** Das war schon so und bleibt
  eine eigene Prüfung: welche Würfel kritisch sind, darf nicht über die Spationierung durchsickern,
  bevor das Ergebnis aufgedeckt ist.
- **Das Panel wächst, aber nur wenn es muss.** `MAX_PANEL_WIDTH = 640` bleibt die BEVORZUGTE Breite,
  weil sie eine User-Entscheidung ist („das panel sollte vielleicht nicht über die gesamte breite
  gehen") — bei einer gewöhnlichen Salve bewegt sich nichts. Sie hört nur dann auf, eine harte
  Grenze zu sein, wenn die Würfel sonst in mehr Reihen stapeln würden, als Platz ist: **60 Würfel
  liefen 11 px unter den Brettbereich**, und in die Breite zu gehen ist die einzige Art, dieselben
  Würfel auf weniger Reihen zu verteilen. Gemessen: 40 Würfel bleiben bei 640, 60 gehen auf 944,
  80 auf 1248 — und keiner verlässt den Brettbereich, was die ältere Zusicherung ist, die dabei
  nicht brechen durfte („das würfel overlay darf nicht über die seiten panels gehen").
  Gewachsen wird in ganzen Würfeln, nicht in Pixeln: ein Bruchteil eines Würfels kauft nichts.
- **Crit-Labels sind PLAKETTEN.** Lose 11-px-Goldschrift auf dunklem Grund war das Leiseste auf dem
  Schirm und markierte ausgerechnet die Würfel, die am meisten bedeuten. Jetzt eine gefüllte,
  angefaste Platte in kräftigem Gold mit **DUNKLER** Schrift darauf — derselbe Kontrastgriff, den
  die Erfolgswürfel schon benutzen (dunkle Augen auf heller Fläche); Schrift 11 → 13 fett.
  **EINE Plakette pro Würfel, nicht pro Zeile:** ein zweizeiliges Label ist EINE Aussage, zwei
  gestapelte Platten läsen sich als zwei.

**Getestet:** `test_crit_labels.py` 24 → **55/55** (neu: Abschnitt 4 misst jeden Würfel gegen die
Backdrop-Rect bei 6/10/20/30/40 Würfeln × drei Labellängen, dazu die Panelbreite in beide
Richtungen; Abschnitt 5 die Plakette auf PIXELN — gefüllt, dunkle Schrift, hellere Kante, und der
Kontrast gegen das Panel als Zahl). Neu `ab_dice_panel.py`: **8 A/B-Sonden, alle beißend**, die
erste meldet den gemeldeten Fehler wörtlich (`10 dice WITH a crit label stay inside the panel: got
38`).
**Ein Befund über den TEST** (Fehlerklasse 24): die Sonde „eine Platte pro ZEILE" biss zuerst
nicht, weil JEDES gedruckte Label bei dieser Schriftgröße auf eine Zeile passt — der zweizeilige
Fall kam im Test gar nicht vor. Er wird jetzt mit einem eigens konstruierten langen Label erzwungen,
und die Prüfung „trotzdem EINE Plakette, nur höher" ist die, die die Sonde kippt.

**Im ECHTEN Spiel geprüft, mit benannter Grenze:** ein Spion über `selfplay.py map2` (3000 Frames)
sieht 14 Panel-Zeichnungen mit Würfeln, **0 px Überstand und 0 px unter dem Brettbereich** — aber
**keine** davon mit Crit-Labels und die größte mit einem einzigen Würfel: der MockAgent erreicht die
großen Salven nicht (die dokumentierte Harness-Grenze). Der gemeldete Fall ruht deshalb auf der
Suite, die dafür das ECHTE Panel auf eine echte Surface mit echten Schriften zeichnet — bei einer
reinen ANSICHT ohne Engine-Kopplung ist das die richtige Ebene, anders als bei einer
Verdrahtungsfrage.

### Titel, Modifikatoren und Reroll-KNÖPFE (2026-09-12)

**Gemeldet:** *"Niemand liest lange Sätze mit Zahlen drin im Spielgeschehen. Bei jedem Roll muss groß
und fett drüber stehen was das für ein Wurf ist ... Unten im Panel Buttons je nach Situation: Wurf
akzeptieren / 1en wiederholen / alles wiederholen / Fehlschläge wiederholen. Dann poppen nicht so
viele Overlays hintereinander auf."* User-Entscheidungen: Klick irgendwohin bestätigt NUR ohne
Reroll-Option (ACCEPT-Knopf plus Space/Enter immer); der Satz verlässt das Panel (bleibt im Log).
Command Re-roll, Aspect Shrine/Branching Fates und Targeting Array sollten zuerst im linken Panel
bleiben — **revidiert**, sie stehen jetzt im Würfelpanel (siehe unten).

- **Kopf:** `DiceManager.roll(title=, subtitle=, shown_modifiers=)`, pro Wurf geleert;
  `display_title()` fällt zurück auf Label-Name (vor `": "`/`" - "`) → `TITLE_BY_KIND` → "Roll".
  **`label` bleibt unverändert** — ~20 Tests pinnen Teiltexte, `dice_notation.py` loggt es,
  `action_panel.py` zeigt es; das Panel liest nur die neuen Felder.
- **`modifiers.for_display()` rechnet in SPIELER-Vorzeichen**: Schwellen-Modifier (positiv =
  schlechter) werden negiert, additive Würfe (Charge/Advance) nicht. Helfende zuerst (grün ▲),
  dann schadende (rot ▼), Dreiecke als Polygon statt Glyph. Charge liest dafür
  `_charge_roll_modifiers()` — dieselbe Liste speist `_capped_roll()`, also können Anzeige und
  Summe nicht auseinanderlaufen; Advance `movement.advance_roll_modifiers()`, Save
  `damage_resolution.save_heading()` (AP, außer der Invulnerable zählt).

**Die FRAGE wird vorgezogen, die Arithmetik bleibt — die tragende Entscheidung.** Hit/Wound-Rerolls
entstehen erst in `on_dice_acknowledged()` (ein neuer `roll(is_reroll=True)` mit eigenem
`pending_step`, getragene Treffer addiert). Ein Umbau auf In-place-Rerolls hätte diese Arithmetik
und ~150 gepinnte Prüfungen umgeworfen. Stattdessen:

- **Plan/Execute-Split**: die Rümpfe stehen WÖRTLICH in `_hit_step`/`_wound_step` (shooting und
  fight) mit `preview=False`; `pending_roll_choice()` ruft DIESELBEN Methoden mit `preview=True`.
  Vorschau und Angebot können per Konstruktion nicht auseinanderlaufen. Die Re-roll-Schritte fragt
  die Vorschau gar nicht (siehe den nächsten Abschnitt).
- **Die Antwort reitet auf dem Wurf**: `choose_reroll()`/`take_chosen_reroll()`, geleert von
  `roll()` und NICHT von `acknowledge()` (das Angebot liest sie danach). Jede Hit/Wound-Angebotsstelle
  geht durch `_raise_reroll_offer()` → `roll_choice.take()`; passt kein Key, öffnet der Prompt wie
  bisher. **Der Overlay-Pfad bleibt Fallback** — kein Deadlock für Harnesses, die `acknowledge()`
  selbst rufen.
- **`game/roll_choice.py`**: `RollChoice.accept_allowed` ist False bei einer Pflicht-1er-Quelle mit
  1en (dort gibt es weder ACCEPT noch Klick-irgendwohin). `RollChoiceView` fragt EINMAL pro Wurf
  (Fingerabdruck: Listen-Identität, Augen, `already_rerolled`, geclaimte Angebote — ein Command
  Re-roll ändert die Zählungen) und reicht nur einem MENSCHEN eine Wahl (lebende
  `human_players`-Sicht); KI-Angebote laufen unverändert über die Queue.
- **Zwei Formen**: `acknowledges=True` (Hit/Wound/Damage/Attacks/Reanimation: Key setzen,
  bestätigen) und `acknowledges=False` (Advance/Charge würfeln schon VOR dem Bestätigen in place:
  `apply()`, Wurf bleibt liegen). ACCEPT claimt `choice.claims`, sonst öffnete das Advance-/Charge-
  Angebot beim Bestätigen doch noch seinen Prompt.
- **Damage/Attacks nehmen die Antwort SYNCHRON** (`DamageRerollOffer.panel_answer()` VOR
  `maybe_offer()`): dessen True heißt "Antwort kommt später" und hält die Session busy — eine schon
  vorliegende Antwort darf das nicht behaupten.
- **`main.py`: `_acknowledge_pending_roll()` ist die EINE Tür** (Klick, ACCEPT, Space/Enter) und die
  einzige `dice_manager.acknowledge()`-Stelle; ein Panel-Knopf wird VOR dem Klick-irgendwohin
  gefragt; ein Key wird nur gespeichert, wenn die Frame-Wahl ihn wirklich anbietet (sonst könnte ein
  Accept einen KI-Prompt beantworten), und die Tür verwirft eine ungenutzte Antwort.
  `selfplay.py` drückt den ersten gezeichneten Knopf.

**Getestet:** neu `test_dice_panel_header.py` (**58**, auf PIXELN) und `test_roll_choice.py`
(**114** — tragend: Vorschau == Prompt, UNABHÄNGIG gelesen: die Knöpfe aus der `RollChoice`, das
Angebot aus den Prompt-LABELS), `test_event_chain_wiring.py` §24 (**235**). `ab_dice_panel_buttons.py`:
**15 A/B-Sonden, alle beißend**. Befunde über den TEST: Damage/Attacks und Reanimation waren
zunächst ungedeckt (Abschnitt 7 kam dazu), `main.py`s Accept-Claims-Schleife war nur durch NACHBAU
in der Suite gedeckt (jetzt ein §24-Pin), und zwei Sonden ließen ihre Suite ABSTÜRZEN statt sie rot
zu machen (Dict-Index, `min()` auf leerer Knopfliste) — beide degradieren jetzt.
**Im ECHTEN Spiel belegt** (`verify_dice_panel_buttons.py`): gezeichnet `accept / failures 9 /
whole 24`, ein Klick irgendwohin lässt den Wurf liegen, der Druck auf RE-ROLL FAILURES wirft 9 Würfel
ohne einen einzigen "Keep result"-Prompt; `--neutralize` → kein Reroll-Knopf, Klick bestätigt,
Prompt öffnet. GESTELLT: der Schuss (live `_begin_resolution()`), Grim Reapers (bis Orks E3a Monster Hunters) als Quelle, drei
Würfel auf 1, ein offener Mensch-Prompt beantwortet (selfplay beantwortet keinen — offen auf 2251
von 2500 Frames) und eine Notice weggeklickt. **Harness-Falle:** mit einem Ein-Würfel-Schützen sind
"failures" und "all" derselbe Würfel — die Sonde nimmt den größten Pool.

#### Ein Re-roll trägt nie einen Re-roll-Knopf

**Gemeldet** (Screenshot: "RE-ROLL 1S TO WOUND" mit "RE-ROLL FAILURES (6)" darunter): *"bei rerolls,
sollte es keine reroll option geben. man darf rerolls nicht rerollen."*

- **Der Knopf meinte nicht den Würfel auf dem Tisch**, sondern die 6 übrigen Fehlschläge des Wurfs
  DAVOR. `shooting.py` warf die automatischen 1er einer Quelle (Forward Observers u. a.) ZUERST und
  fragte das optionale Re-roll ([TWIN-LINKED], damals Monster Hunters …) erst DANACH — also landete die
  Frage auf dem 1er-Re-roll. Die Engine hat nie einen Würfel zweimal geworfen, aber die Frage stand
  am falschen Wurf, und mit dem Panel wurde das sichtbar.
- **Gefragt wird jetzt auf dem Wurf, wie er GEWORFEN wurde.** "Re-roll failures" zählt die 1er mit
  (so gewürfelt haben sie ihr eines Re-roll gehabt — mehr verlangt die automatische Klausel nicht),
  und ACCEPT — das Ablehnen — ist genau das, was die 1er ihrem automatischen Wurf übergibt. Das
  Prompt-Label sagt es: "Keep result (the 1s are still re-rolled)". `fight.py` fragt seit jeher in
  dieser Reihenfolge.
- **Die 1er-Re-roll-Schritte laufen DURCH** (`_hit_reroll_ones_step`/`_wound_reroll_ones_step`
  rufen direkt `_apply_sustained_hits`/`_resolve_wounds`), und `pending_roll_choice()` fragt in
  BEIDEN Controllern nur noch `("hit", "wound")` — kein Re-roll-Schritt kann Knöpfe tragen, per
  Konstruktion statt per Zählung (Abschnitt 8 in `test_roll_choice.py` liest das Tupel per AST).
- **Mitgefunden im Nahkampf, und die Kehrseite derselben Reihenfolge:** `fight.py` fragte zwar
  zuerst, aber "Keep result" sprang direkt in die Auflösung und **ließ die Pflicht-1er einer
  anderen Quelle (Path of the Warrior, Whirling Onslaught, Phaeron of the Stars, Prophet …) still
  fallen.** `_hit_without_optional_reroll()`/`_wound_without_optional_reroll()` sind jetzt der
  Schwanz BEIDER Wege (kein Angebot / Angebot abgelehnt).
- `test_reroll_once.py` §4 pinnte die alte Reihenfolge ("[TWIN-LINKED] only gets the failures
  Forward Observers left alone") und STÜRZTE ab statt rot zu werden; umgeschrieben auf beide Wege,
  die Kernaussage (kein Würfel zweimal) bleibt. Die erste Fassung von Abschnitt 8 hatte eine falsche
  Bühne (die Snazzgun verwundet die Strike Team auf 2+, eine 2 ist also kein Fehlschlag) — mit
  (1,1,1) trennt die Zeile trotzdem, weil die alte Reihenfolge dann gar nichts anbot.

#### Fähigkeits- und Stratagem-Knöpfe im Würfelpanel

**Gemeldet:** *"ich habe es mir anders überlegt. buttons für fähigkeiten und stratagems sollen doch
mit in das würfel panel rein, statt links in die spalte."*

- **`roll_choice.ability_actions(command_reroll, activation_reroll, unmodified_six)`** ist die EINE
  Liste, gelesen vom Zeichnen UND vom Klick-Routing in `main.py` (`_frame_dice_actions()`): Command
  Re-roll (Stratagem-Violett), Targeting Array / Crystal Matrix (Label vom Controller), je ein Knopf
  pro Unmodified-6-Quelle. Alle `acknowledges=False` — keiner bestätigt den Wurf, sie ändern ihn in
  place oder öffnen die Würfelwahl. **Die FORM bleibt** (Knopf, dann Würfel wählen); umgezogen ist
  nur der Ort.
- **Eine eigene Zeile UNTER den Knöpfen des Wurfs**, eigene Liste `DicePanel._action_rects` mit
  `action_at()`: `button_at()` beantwortet weiter nur die Optionen des Wurfs, auf die sich
  Klick-irgendwohin und `selfplay.py` verlassen. `RollOption.accent` ist neu (Stratagem/Cancel).
- **Während einer Würfelwahl** stehen die Knöpfe des Wurfs beiseite, das Panel zeigt den Hinweis
  des Modus ("Click a die to make it an unmodified 6.") und ein Cancel. `main.py` fragt
  `dice_panel.action_at()` ZUERST im Würfelzweig — vor den drei Würfelwahl-Zweigen, sonst gewinnt
  kein Cancel.
- **Das Höhenbudget kennt die Zeile** (eine Reihe je zwei Knöpfe), sonst läuft eine große Salve
  unten aus dem Brett.
- **Das linke Panel zeichnet keinen dieser Knöpfe mehr** — nur noch Label und "Decide the roll in
  the dice panel."; die drei Controller bekommt es weiter (positionelle Kette, Fehlerklasse 22).
  Wächter: §24 zählt `_draw_button(` im Rumpf von `_draw_command_reroll` (0).
- **Farbwahl, benannt:** die zwei Fähigkeitsknöpfe tragen die Standardfarbe (blau wie die
  Re-roll-Knöpfe des Wurfs), nicht mehr "confirm" wie links — im Würfelpanel ist Grün ACCEPT.

**Getestet (beide Nachträge):** `test_roll_choice.py` 114 → **169/169** (Abschnitte 8 und 9),
`test_dice_panel_header.py` 58 → **71/71** (Abschnitt 6 auf PIXELN und Rects, inklusive 40 Würfeln
mit zwei Knopfreihen im Brett), `test_unmodified_six_ui.py` **65/65** (Abschnitt 2 aufs echte
DicePanel umgeschrieben, samt echter Presse und Cancel und der Gegenprobe links),
`test_event_chain_wiring.py` §24 **240/240**, `test_reroll_once.py` **74/74**; zwei Label-Pins in
`test_tau_vehicles.py`/`test_aeldari_gun_tanks.py` zeigen jetzt auf `roll_choice.py`.
`ab_dice_panel_buttons.py` → __PROBES__.
**Im ECHTEN Spiel belegt** (`verify_dice_panel_buttons.py`, jetzt mit Forward Observers GESTELLT):
gezeichnet `accept / failures 13 / whole 24` (die 13 zählen die drei 1er), der Druck auf FAILURES
wirft 13 Würfel, **der Re-roll selbst zeigt nur `accept`**, im Würfelpanel stehen
`Command Re-roll (1 CP)` und `Aspect Shrine (1 token(s) left)`, links **0** solcher Knöpfe.
`--neutralize` reproduziert weiter die Vor-Fix-Welt.
Volle Regression __REGRESSION__.

## Einheiten-Auswahl ist erstklassig (game/selection.py)

**Es gab einen Auswahl-ZUSTAND, aber keine Auswahl-GESTE** (User beim Planen des
Total-War-Drags: "wie ist das denn jetzt eigentlich mit der auswahl von einheiten … bisher gibt
es ja nur direkte dragen kein anwählen", und danach "aber man muss sie auch wieder abwählen
können"). Vorstufe für den Rechts-Drag, weil dessen Geste einen GEGENSTAND braucht, den ein
einzelner Zug nicht mittragen kann.

- **`MovementController.selected_squad` WAR längst die phasenübergreifende Auswahl** — ein
  lügender Name mit ~25 Lesern: das ganze linke Panel hängt daran
  (`action_panel.py:1620` → Shoot, Charge, Fight, Pile In, Consolidate, Fall Back, jedes
  Stratagem), sechs Controller verlangen hart `selected_squad is <ihr Squad>`, und
  `can_select()` trägt einen ausdrücklichen `PHASE_FIGHT`-Sonderfall. Also **verlegt statt neu
  gebaut**: `game/selection.py` hält das Paar, `selected_squad`/`selected_model` sind
  **weiterleitende Properties** — dieselbe Re-Export-Idiom wie bei `is_tau_unit`, damit jeder
  Leser UND die zwei Direktschreiber (`start_scout_move`, `torchstar_gambit.py`) **per
  Konstruktion** unverändert sind. `select()` bleibt auf dem Controller, weil es zusätzlich
  `_clear_move_state()` und `errors = []` tut — und dieser Errors-Reset ist tragend für die KI,
  die `movement_controller.errors` als Erfolgstest liest.
  **Bewusst NICHT absorbiert:** `PregameController.selected_unit` ("welche Karte aus dem Pool",
  eine andere Frage) und `FiringDeckController.selected_models` (die einzige Modell-MEHRfachwahl).
- **Der eigentliche Ärger war das Schwenken, nicht der Fehlklick.** Ein Linksdruck auf leeren
  Boden rief `select(None)` SOFORT und startete danach den Kamera-Schwenk — **jedes Schwenken
  verlor also die Auswahl**. Jetzt entscheidet das LOSLASSEN: unter `DRAG_START_THRESHOLD_PX`
  war es ein Klick (abwählen), darüber ein Schwenk (Auswahl bleibt). Dieselbe Schwelle und
  dieselbe Form wie `pending_move_token` — ein Druck, zwei Bedeutungen, entschieden daran, ob
  der Cursor gereist ist.
- **ESC ist eine LEITER**: Auswahl vorhanden → abwählen, sonst die unterste Sprosse.
  **Die unterste Sprosse ist seit dem Game Menu das MENÜ, nicht mehr der Vollbild-Quit** — siehe
  `## Game Menu` unten; die aufgezeichnete Entscheidung ("im vollbild modus beendet ESC das
  spiel") ist damit in den Quit-Eintrag des Menüs gewandert und gilt jetzt auch im Fenster.
  Der Zweig sitzt schon im frühen event-typ-gegateten Teil, ist also unverschluckbar. **Abwählen darf FAIL-OPEN sein** (wird es geschluckt, behält man die Auswahl)
  — anders als eine Geste, die Positionen schreibt.
- **Gezeichnet wird jetzt die EINHEIT.** `draw_coherency_removal_highlight()` war wörtlich
  dieselbe Schleife → `draw_squad_outline(squad, color, bump_px, width_px)` als Extraktion am
  zweiten Konsumenten, plus `_ring_bump()` neben `_ring_width()` (eigene Methode: ein Bump 0 ist
  legal, eine Strichbreite 0 nicht). **Gemessen:** der cyanfarbene Ring ging NICHT durch
  `_ring_width()` und landete bei **~1.2 Bildschirmpixeln**, dünner als der Base-Rand, außerhalb
  dessen er sitzen soll — derselbe Defekt wie bei den Aufstellungszonen. Der Anker-Ring BLEIBT
  und ist der hellere: die Sichtlinie wird von ihm aus gemessen.
- **DER NAME STEHT IM LINKEN PANEL, NICHT AUF DEM BRETT** (User: "Entferne das Label, das den
  Squad namen anzeigt, wenn man eine Einheit auswählt. das label stört auf dem spielfeld.
  Verlagere die info stattdessen ganz oben in die linke spalte mit Sprite + name in einen
  abgeschlossenen kasten"). Das Namensschild über der Einheit ist weg; `ActionPanel.
  _draw_selection_header()` zeichnet stattdessen einen geschlossenen Kasten ganz oben in der
  Spalte, mit Porträt LINKS und dem umbrochenen Namen daneben — **derselben** Zeichenkette
  (`{name} ({n})`), die das Panel schon druckte, also ist es ein Umzug und keine zweite Quelle.
  - **Gerufen aus `draw()`, ÜBER dem Dispatch, nie darin** — dieselbe Begründung, aus der
    `_draw_global_toolbar()` dort steht: `_draw_dispatch()` ist ~40 Zweige mit Early Returns, und
    eine Tatsache, die über alle gilt, darf nicht in einem davon wohnen. Die Auswahl ist genau so
    eine (`movement_controller.selected_squad` ist die phasenübergreifende).
  - **Der Dispatch bekommt einen VERKÜRZTEN Rect.** Jeder Zweig legt sich ab `rect.y` aus (meist
    `rect.y + 40`), also verschiebt diese eine Kante alle vierzig auf einmal; die Alternative wäre
    gewesen, vierzig Aufrufstellen auf einen neuen Ursprung zu einigen — die Form, von der diese
    Datei ihre Narbe hat. Die Toolbar behält den VOLLEN Rect (sie hängt an der Unterkante, im Test
    als "der Streifen bewegt sich nicht" gemessen).
  - **OHNE Auswahl wird gar nichts gezeichnet** — die stehende Konvention dieser Screens ("kein
    Chrome für ein Steuer, das nichts tun kann"); ein leerer Kasten kostete jeden Zweig darunter
    dieselben ~54 px, um nichts zu sagen. Der Kein-Auswahl-Fall erklärt sich schon in Worten.
  - **Die Bewegungs-Zweig-Dopplung ist raus**: er zeichnete Porträtreihe plus Namen für DASSELBE
    Squad, also ~70 px einer 220-px-Spalte, um zu wiederholen, was direkt darüber steht. Die
    anderen DREI `_draw_unit_portrait()`-Aufrufe bleiben — sie nennen je eine ANDERE Einheit
    (Formations-Warteschlange, gepickte Pool-Karte, die gerade aufgestellte), als Zählung gepinnt.
  - **`draw_placement_identity()` BEHÄLT sein Schild**, und das ist kein Vergessen: es beantwortet
    eine andere Frage (eine Einheit, die der SEQUENZER nennt, nicht eine, die der Spieler gewählt
    hat), und im Vorspiel zeigt die linke Spalte den Platzierungs-Flow statt einer Auswahl. **Im
    echten Spiel geprüft:** über 1200 Frames tritt "Kasten offen, während eine Einheit platziert
    wird" **null mal** auf — es gibt also keinen Doppel-Einheiten-Moment.
  - **Farben gegen den Renderer gepinnt** (`SELECTED_MODEL_COLOR` / `SELECTION_LABEL_BG_COLOR`):
    Ring auf dem Brett und Kasten in der Spalte sind eine Aussage an zwei Orten.
- **Ein toter Anker wird UMGEHÄNGT, nicht weggeworfen** (`Selection.reanchor()`): stirbt das
  Anker-Modell, rückt die Auswahl auf ein überlebendes; nur eine ausgelöschte Einheit löscht sie.
  Vorher warf `main.py` die ganze Auswahl weg, was mit einem Einheiten-Umriss aussieht, als
  verschwände der Zug grundlos. Lebendigkeitstest ist `not m.is_dead()`, **nicht** `not
  squad.models` (Fehlerklasse 12).
- **Drei Stellen sagten nicht, WELCHE Einheit gemeint ist**, alle mit denselben Helfern
  geschlossen: das linke Panel ohne Auswahl war 220 px Leere (jetzt ein Hinweis, gleiche
  Begründung wie `_draw_fight_step_status`); die Reserven-Leiste kannte nur die GEZOGENE Karte,
  nicht die angeklickte; und während der Aufstellung stand auf dem Brett nur die grüne
  Legalitätsmaske (jetzt `draw_placement_identity`, nur für eine Einheit, deren Modelle wirklich
  auf dem Brett stehen).
- **Getestet:** neu `test_unit_selection.py` (**75/75**, sieben Abschnitte) plus **elf
  A/B-Sonden**, jede kippt ihre eigenen Prüfungen. **Zwei bissen zuerst NICHT, beide
  Fehlerklasse 24:** die Namensschild-Prüfung sampelte ein Band, in das die Ringe hineinragten,
  und die Panel-Prüfung zählte den 2-px-RAHMEN des Panels mit (4 px je Zeile — allein genug, um
  jede Schwelle zu reißen). Beide isolieren jetzt wirklich. **Vorher gab es zu dieser Zeichnung
  GAR KEINEN Test** — `draw_selected_model` kam in keiner Testdatei vor.
- **Getestet (Panel-Hälfte):** neu `test_selection_header.py` (**29/29**, fünf Abschnitte — der
  Kasten auf PIXELN, Sprite und Name einzeln, der lange Attached-Unit-Name der umbrechen MUSS,
  drei unabhängige Dispatch-Zweige, und der verkürzte Rect) plus `ab_selection_header.py`
  (**10 A/B-Sonden, alle beißend**; die ganze Vor-Fix-Welt kippt 15 von 29). Die zwei alten Pins in
  `test_unit_selection.py` sind UMGEDREHT und behalten ihre schwer erkaufte Geometrie: das Band
  muss STRIKT über dem obersten Ringpixel liegen, sonst lecken die Ringe hinein und "da ist nichts"
  besteht auch mit Schild — genau der Befund, den die alte Fassung als 66/66 gemeldet hatte. Dazu
  die Gegenprobe, dass die RINGE noch da sind: sonst bestünde die Zeile auch bei einer Auswahl, die
  gar nichts zeichnet.
- **Zwei eigene Testfehler, beide von den Sonden gefunden, beide alte Bekannte:** eine Prüfung
  indizierte in eine Liste, die in der Vor-Fix-Welt LEER ist (die Suite stürzte ab, statt rot zu
  werden — vierte Instanz), und ein Reihenfolge-Wächter benutzte `str.index()` statt `find()`
  (fünfte Instanz). Beide degradieren jetzt zu ROT.
- **`smoke_selection.py` ist der Ketten-Beweis** und läuft in `--smoke` mit: ein echter Klick in
  `main()`s echter Schleife, und ein Spion am Renderer belegt, dass main.py die LEBENDE Auswahl
  wirklich weiterreicht — genau die "gebaut, aber nie gefüttert"-Klasse, die dieses Repo sechsmal
  getroffen hat. `--neutralize` scheitert (6 von 9 überleben, und die drei fallenden sind genau
  das, was der Fix kauft; die zwei ESC-Prüfungen sind von hier aus nicht stubbar, dafür gibt es
  die A/B-Sonde in der Suite). **Zwei eigene Harness-Fehler dabei, beide echt:** der erste Klick
  wurde vom Zug-Banner geschluckt, und die KI räumte per `ai_advance_phase` → `select(None)`
  zwischen "gemerkt" und "ESC" die Auswahl weg — deshalb wird Auto-Play nach dem Vorspiel wieder
  abgeschaltet. Standalone grün, im Sweep rot: eine echte Flake, keine Codedifferenz.
- Volle Regression **159 Suiten, ~13746 Prüfungen, 158 grün / 0 rot / 1 bekannt**, `run_tests.py
  --smoke` komplett grün, dazu `smoke_pregame.py` map1+map2, `smoke_setup_screens.py`
  (+`--neutralize` weiter rot), `smoke_measure_tool.py`, `smoke_log_input.py`,
  `smoke_end_turn_warning.py` und `selfplay.py map2`.
