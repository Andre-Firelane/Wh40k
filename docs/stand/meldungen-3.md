# Meldungen aus Partien (3)

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Fünf Meldungen aus einer Partie (2026-09-09)

Aeldari Warhost gegen Necrons, map4, Biom Arena (`logs/game_20260909_221504.log`). Zwei enge
Fixes, drei Engine-Nähte. **Bei zweien war die naheliegende Diagnose messbar falsch**, und bei
einer dritten war der Fehler gar keine Regel, sondern die Stille.

### 1. Branching Fates setzte das ERGEBNIS auf 6, nicht den Würfel

**Im Log als PAAR reproduziert:** Zeile 282 `Eldritch Storm counts as an unmodified 6 (die 1 -> 6)`,
Zeile 1239 `Bright Lance ... (die 1 -> 4)`. Die Bright Lance ist D6+2, die Eldritch Storm ein
blanker D3 — die alte Lesart setzte also das Ergebnis auf 6 und den Würfel auf 4.

**Der gedruckte Satz entscheidet, und er hat EIN Prädikat für alle drei Wurfarten**
(`rules/aeldari/Farseer.md:40`): "change the result of one Hit roll, one Wound roll **or** one
Damage roll ... to an unmodified 6." Hit und Wound setzen seit jeher den WÜRFEL; Damage tut es
jetzt auch. Zwei Folgen der alten Lesart, beide gemessen: sie **deckelte eine Waffe unter ihr
eigenes Maximum** (D6+2 kann 8, bekam 6) und **verschwieg sich ganz**, sobald das Ergebnis schon
6 oder mehr war (ein Würfel von 5 ist ein Ergebnis von 7 — kein Angebot, obwohl der Würfel noch 8
zahlen könnte). Auf einem Railgun (D6+6) war sie nie anbietbar.

- **Die stärkste Evidenz stand im eigenen Repo:** `game/structural_collapse.py`s Header schreibt
  aus, dass "a Damage roll of 1" den WÜRFEL benennt, nicht das Total — dieselbe Satzform, die
  Branching Fates als Ergebnis las. **Zwei uneinige Lesarten einer Formulierung, nebeneinander
  ausgeliefert.** Beide Header sagen das jetzt.
- **`DiceNotationRoll.face_for_total()` ist ENTFERNT**, nicht liegengelassen: es hatte danach
  keinen Aufrufer mehr. Die Arithmetik geht nicht verloren — `notation_reroll.face_of()` ist
  dieselbe Rechnung und bleibt LIVE (die D-cannon rerollt "a Damage roll of 1"). An seiner Stelle
  steht `DiceNotationRoll.single_die`: mit zwei Würfeln benennt "to an unmodified 6" kein Gesicht
  mehr, also wird das Angebot abgelehnt statt geraten (gemessen: 0 von 56 Damage-Notationen werfen
  mehr als einen Würfel).
- **Das Gate wandert vom ERGEBNIS auf das GESICHT**, damit Hit/Wound und Damage einen Begriff von
  "ist schon eine 6" teilen. Die Log-Zeile nennt jetzt zusätzlich den resultierenden Schaden —
  "unmodified 6" neben 8 Wunden schickt die nächste Untersuchung sonst zurück aufs Brett.
- **Die veraltete Zahl "neun Waffen" stand an fünf Stellen; es sind 22** (12x +1, 9x +2, 1x +6),
  plus drei LAUFZEIT-Quellen ([MELTA] in Halbdistanz, zwei Enhancements).
- **Der Test-Kommentar, der den Fall entschuldigte, war falsch:** er sagte "no rostered weapon here
  prints both a Damage bonus and a Farseer" — die Heavy Weapon Platform der Guardian Defenders
  trägt die Bright Lance, und der Farseer führt genau diese Einheit. Der Fall ist end-to-end
  rosterbar und wird jetzt so gefahren.
- **Getestet:** `test_farseer.py` 106 -> **125/125** (der gemeldete Fall auf der Bright Lance:
  Würfel 1 -> **8 Schaden**, Würfel 5 wird überhaupt erst angeboten, Würfel 6 zu Recht nicht; der
  D3-Fall unverändert), plus `ab_branching_fates_damage.py` (**4 A/B-Sonden, alle beißend**; die
  erste meldet `got 6, want 8`).

### 2. Die Einheiten-Keywords fehlten auf der Hover-Datacard

**Die Daten waren vollständig da, sie wurden nur nirgends gezeichnet.** Die Karte hat zehn
Abschnitte, die Keyword-Leiste war keiner. `rules_text.ABILITY_SECTIONS` filterte `## Keywords`
heraus — **und nicht absichtlich**: der Kommentar daneben zählt die bewussten Ausschlüsse auf
(Profile, Waffen, Points, Wargear) und nennt Keywords nicht.

- **Quelle ist der KORPUS, und das ist gemessen statt Geschmack:** von den 130 gebauten
  Datenblättern haben **66** ein `Datasheet.keywords`, das von der gedruckten Zeile abweicht (meist
  fehlt das Fraktions-Keyword), und **76** ein leeres `faction_keywords` (nur die 54 Aeldari setzen
  es). Der Korpus hat beide Zeilen für alle 160 Dateien. Das deckt sich mit der gepinnten
  Zusicherung der Karte ("gedruckte Regeln, keine selbst generierten Varianten").
- **`UnitProfile`s ~22 Keyword-Booleans sind die dritte Quelle und werden NICHT benutzt** — sie sind
  pro MODELL und absichtlich partiell (nur was eine Regel liest).
- **Kein zweiter Parser:** `rules/aeldari/Corsair Voidscarred.md` druckt `KEYWORDS – ALL MODELS:` mit
  EN-DASH, und der Scrape hat dort zwei gedruckte Zeilen ohne Trenner zusammenlaufen lassen. Der
  geteilte `_classify()` fällt die Zeile auf Prosa zurück, ihr Text erreicht die Karte also
  trotzdem; ein `startswith("KEYWORDS:")` hätte diese Einheit still verloren.
- **Bei einer Attached Unit eine Gruppe pro Komponente** — und hier ist das nicht bloß Konsistenz:
  19.03 POOLT Keywords, welche live sind, ist also wirklich die Vereinigung mehrerer Leisten.
- **Nebengewinn, und er war nötig:** `_content_height()` wurde im TEST von Hand nachgebaut, und die
  Kopie ging beim ersten neuen Abschnitt sofort schief (vier Fixtures rot).
  `UnitDatacardOverlay.card_parts()` ist jetzt die EINE Sammelstelle, gelesen von `draw()` und vom
  Test — ein weiterer Abschnitt kann die Invariante nicht mehr brechen.
- **Benannte Folge:** die Boyz+Warboss+Painboy-Karte (drei Komponenten) überschreitet jetzt 1080 px
  und scrollt. Der Test bildet das ab (`drawn == min(measured, cap)`) statt die Fixture zu
  schrumpfen.
- **Getestet:** `test_unit_datacard.py` 89 -> **110/110** plus `ab_datacard_keywords.py`
  (**6 A/B-Sonden, alle beißend**; die Vor-Fix-Welt kippt 14).

### 3. Insane Bravery "manchmal nicht angeboten" — es war die STILLE

**Kein Regelfehler.** Vier Klauseln können den Knopf je einzeln entfernen, zu vier verschiedenen
Zeitpunkten, und keine sagte etwas: `max_per_battle=1` (15.04), 15.01s `targeted_this_phase` (ein
*anderes* Stratagem auf dieselbe Einheit — **Command Re-roll zählt mit**), CP-Mangel inklusive
Surcharge, und "die Einheit schuldet gar keinen Wurf" (08.03). Im Log des Users war es die erste:
Zeile 213, Runde 2, danach zu Recht nie wieder.

- **User-Entscheidung: nicht die Regel ausweiten, sondern den GRUND nennen.** Drei Explainer in der
  Form von `actions.start_eligibility()` (`(True, None)` / `(False, reason)`) —
  `battle_shock.why_cannot_roll()`, `stratagems.refusal()`, `insane_bravery.why_not()` —, und in
  jedem wird das Boolean AUS dem Explainer abgeleitet, damit eine Regel nie zwei uneinige Leser hat.
- **Eine HINWEISZEILE, kein ausgegrauter Knopf**, und das ist gegen den zuerst erwogenen
  Präzedenzfall entschieden: der Game-Menu-Fall ist **halb weg** (die Notiz unter einem ausgegrauten
  Eintrag wurde auf User-Wunsch entfernt), und `action_panel.py` schreibt an drei Stellen die
  Gegenkonvention aus ("kein Chrome für ein Steuer, das nichts tun kann").
  `button_style.draw_button()` hat keinen Disabled-Zustand — einen zu erfinden wäre eine neue
  Bildsprache in einem Modul, das jeder Screen liest.
- **PERF gemessen, weil `stratagems.py` die Arro'kon-Narbe trägt:** `can_use()` 0.387 us gegen
  `refusal()` 0.369 us — der Wrapper liegt im Rauschen, und `measure_shooting_frame_cost.py` bleibt
  bei 0.014 ms je Frame.
- **Die BENANNTE LÜCKE, mit ihrer gemessenen Ursache gepinnt** (`test_event_chain_wiring.py` §21):
  15.04s WHEN kennt keine Phasen-Einschränkung, aber diese Engine würfelt an **elf** Stellen einen
  Battle-Shock-Test, und Insane Bravery wird an genau einer angeboten. Die **zehn** umgangenen sind
  namentlich gepinnt (sieben `start_forced_roll`-Aufrufstellen, davon eine mit DREI Unterklassen,
  plus Desperate Escape); ein ELFTER wird rot. Der Wächter pinnt den MECHANISMUS an der Quelle
  (das Tor IST `can_roll()`, und `can_roll()` ist Command-Phase-only, per AST aus dem Rumpf gelesen)
  — das ist die Mont'ka-Korrektur angewandt, deren Rechtfertigung veraltete, während die Zusicherung
  grün blieb.
- **`rolled_squad_ids` wurde NICHT umbenannt**, obwohl es Squads hält: es ist eine Familie von fünf
  gleich lügenden Namen (`fought_`/`piled_in_`/`consolidated_`/`observer_`), und alle fünf sind
  SAVE-SLOT-Namen — das Rename ist eine Dateiformat-Änderung. CLAUDE.md führt die Lücke schon.
- **Der erreichbare `rolled_squads`-Fall ist enger als vermutet:** `reset_command_phase()` läuft zu
  Beginn JEDER Command-Phase, ein erzwungener Test aus einer früheren Phase überträgt also nicht.
  Genau EIN Auslöser feuert IN einer Command-Phase — Presentiment of Dread, das "Command phase"
  ausdrücklich wörtlich liest, damit der Gegner es in DEINER benutzen kann.
- **Getestet:** neu `test_insane_bravery.py` (**58/58**) — **zu diesem Stratagem und zu
  `BattleShockController` gab es keinen einzigen Test**, und das ist der Grund, warum es überlebt
  hat. Plus `ab_insane_bravery_reason.py` (**8 A/B-Sonden, alle beißend**). Die tragende Sonde ist
  die, die die zwei Leser DIVERGIEREN lässt: die drei davor kippen nur Quell-Wächter, und der Test
  fragte die Übereinstimmung zuerst auf der falschen Ebene.

### 4. Das linke Panel während einer Mortal-Wound-Zuteilung

**Die naheliegende Diagnose war falsch, und das ist der Kern.** Fire Overwatch ist Zweig **#29 von
30** in `_draw_dispatch()` und steht UNTER beiden Schadenszweigen — es kann sie gar nicht verdecken.
Was es füllte, war das Loch von **25 Controllern ohne jeden Zweig**: `main.py` zeichnet 28
Brett-Highlights, listet 27 Controller in `_any_pending_damage_choice()`, und das Panel fragte
**zwei**. Alles andere fiel durch die ganze Kette auf den nächsten passenden Zweig.

**Reproduzierter Pfad:** `main.py:4103` `flickerjump_controller.end_of_phase()` startet einen
ASYNCHRONEN D6-Wurf, zwei Zeilen später setzt `fire_overwatch_controller.offer()` synchron
`CHOOSING_UNIT`. Nach dem Würfel-Ack öffnet die Session, und der Dispatch fällt 22 Zweige weiter.

- **Neu `game/damage_pick.py` (37. Extraktion)**, modelliert auf `game/unit_pick.py` und nicht auf
  `proactive_stratagems.py`: jenes ist eine REGISTRY von Kaufoptionen, hier braucht es einen RECORD
  der einen offenen Frage, gegen das Brett aufgelöst — mit exakt denselben vier Lesern. **Die Liste
  ist nicht neu**: es ist `_any_pending_damage_choice()`s vorhandenes Tupel, eine Ebene höher als
  `damage_choice_controllers`. Die REIHENFOLGE ist Teil der Antwort (dieselbe Regel, die
  `mortal_wound_sessions.py` treffen musste).
- **Ein VERHALTENSFIX nebenbei:** die KI-Pause filterte auf ein hartkodiertes `!= "Player 2"`. Mit
  `config.AI_PLAYERS = {"Player 1"}` hätte sie auf den EIGENEN Zuteilungen der KI gefeuert und den
  im Docstring beschriebenen Starvation-Deadlock neu erzeugt. Jetzt `human_players`.
- **Der Zweig bleibt im SLOT von #7/#8, nicht darüber**, und das ist nicht Ästhetik: in `main.py`s
  Event-Kette steht `decision_manager.is_pending` **172 Zeilen ÜBER** dem ersten Schadenszweig —
  während eine Entscheidung offen ist, löst ein Brettklick den PICK auf, nicht die Zuteilung. Ein
  Panel, das dort "klick ein markiertes Modell" sagt, beschriebe ein Steuer, das die Kette
  verweigert — derselbe Fehler andersherum.
- **Das PANEL war während einer Zuteilung komplett tot**, Toolbar-Schalter eingeschlossen: alle 27
  Schadenszweige verlangen `board_rect_screen` in ihrem RUMPF, ein Panel-Klick matchte also einen
  Zweig und tat dann nichts. **`_draw_global_toolbar()`s eigener Docstring versprach das Gegenteil**
  ("every left-panel click ... already routes to handle_click() regardless of the current
  phase/controller state") — ein Kommentar, den kein Code einlöste. Ein `elif` über den
  Schadenszweigen, dessen Bedingung `left_panel_rect` nennt: es kann nur ein Event schlucken, das
  ein Schadenszweig gematcht und NICHT behandelt hätte. **Kein Zweig der 27 bewegt sich.**
- **Die Brett-Markierungen sind entwirrt:** sagt das Panel ALLOCATE, stehen die Overwatch-Ringe
  still — sonst bietet das Brett zwei Klicks für eine Frage.
- **Der Text nennt jetzt die EINHEIT** (`Choose which model of "..." takes the wound`), was mehr ist
  als vorher und keine neue Quelle kostet. **Der Fähigkeitsname wird abgelehnt, gemessen:** nur 6
  der 27 Controller haben überhaupt eine Namenskonstante, und `prompt_rule.py` kann nicht helfen —
  CLAUDE.md nennt die Schadenszuteilung als dessen *benannte Grenze*.
- **Wächter:** `test_event_chain_wiring.py` §20 (MENGENDIFFERENZ, damit ein 28. Controller nicht
  wieder durchfällt), und §12s Extraktor liest die Liste jetzt an ihrer neuen Stelle — er hat den
  Umzug korrekt gemeldet, weil sein eigener Kommentar "0 names has to read as a broken extractor"
  dafür vorbereitet war.
- **Getestet:** neu `test_damage_pick_panel.py` (**30/30**), `test_event_chain_wiring.py` 165 ->
  **185/185**, plus `ab_damage_pick_panel.py` (**7 A/B-Sonden, alle beißend**).
- **Im ECHTEN Spiel belegt** (`verify_damage_pick_panel.py`): 27 Controller in der geteilten Liste,
  Panel zeichnet `ALLOCATE: Choose which model of "1 Dark Reapers 1" takes the wound`,
  Overwatch-Ringe **0**, Panel bedienbar (2 Knöpfe). **`--neutralize` zeichnet `_draw_movement_ui`**
  — und das ist ehrlicher als "Overwatch": WELCHER Zweig die Lücke füllt, hängt davon ab, was sonst
  offen ist. Die Partie des Users traf Overwatch; der Defekt ist, dass überhaupt irgendein Zweig
  antwortet.

### 5. Modelle in Basenkontakt: kein Pile In, kein Consolidate

**Die Regel existierte an EINER Stelle** — `ai/agent_driver.py:3632`, als Optimierung getarnt: KI
only, Pile-In only, nur gegen die EINE anvisierte Einheit, bei 0.15" (`PILE_IN_CLEARANCE_IN` 0.1
plus ein nacktes `0.05`, das dieselbe Zeile für einen CHARGE bei 1.05" benutzt). Die Menschenseite
hatte nichts: `clamp_move()` kannte keinen Kontakt-Term. Consolidate hatte auf keiner Seite etwas.

- **Es ist eine HAUSREGEL und steht als solche im Modul-Docstring.** `rules/` enthält keine
  Kernregeltexte; die einzige Transkription von 12.03 im Repo ist ein Kommentar, der sagt "Each
  model **that is moved** must end its move closer" — er erlaubt Stehenbleiben und verbietet
  Bewegen nicht.
- **Neu `game/base_contact.py`**: `BASE_CONTACT_GAP_IN = 0.2` (0.2" existierte vorher NIRGENDS als
  Konzept), `FROZEN_MOVE_MODES = ("pile_in", "consolidate")`, plus `is_frozen()`/`frozen_models()`.
- **RÜCKZÜGE SIND UNBERÜHRT, und das ist die Klausel, auf die zu achten ist** (User: "denke aber
  daran, dass bei einem rückzug models natürlich den base contact verlassen können"). Es gibt ZWEI
  Fall-Back-Modi (`fall_back`, `retro_thrusters_fall_back`), dazu `charge`, `surge`, `scout`, jeden
  Battle-Focus-Modus und den gewöhnlichen Zug (`None`). Eine Fassung, die auf "ist engagiert" statt
  auf den MOVE MODE gatet, würde eine gebundene Einheit für immer festnageln — deshalb ist die
  Menge benannt und der Test läuft **jeden** anderen Modus als Gegenprobe ab.
- **Der Durchsetzungspunkt ist `clamp_move()` — eine Stelle deckt jeden Pfad.** Gemessen: jeder
  menschliche und KI-Bewegungspfad routet dorthin, inklusive `apply_group_drag()`,
  `apply_line_drag()`, der starren KI-Phase 1 und der Objective-Consolidation. **Damit fällt "Front
  steht, Rest zieht" aus dem Clamping heraus, mit NULL Änderungen an `whole_unit_drag.py` und
  `line_drag.py`** — `apply_group_drag()`s eigener Docstring sagt schon, dass der Gruppen-Drag nicht
  starr ist. **Nicht `_instant_violations()`**: das lehnt mit einer Fehlermeldung ab, ein
  Gruppen-Drag würde also pro eingefrorenem Modell eine Fehlerzeile werfen — eine Regel als
  Fehlermeldung. **`is_movable()` zusätzlich**, weil es das Aufnehmen gatet und damit die klarste
  Rückmeldung für den Einzel-Drag ist.
- **ANY ENEMY statt der anvisierten Einheit** — die eine Stelle, an der die Regel strenger ist als
  die Optimierung, die sie ersetzt.
- **Drei Rückmeldungskanäle**, weil ein stillschweigend verweigertes Steuer selbst ein Fehler ist:
  ein orangener Ring (`Renderer.draw_frozen_models()`, unbedingt pro Frame gezeichnet), eine
  Panel-Hinweiszeile, und der Eingefroren-Zähler in der `[pile in]`-Logzeile.
- **Die KI-Zeile ist GESPALTEN**, Regel gegen Optimierung, beide durch `is_frozen()` — der
  Charge-Pfad behält `clearance + 0.05` = 1.05" exakt, und dass `measure_charge_scenes.py`
  unverändert herauskommt, ist die Prüfung, dass die Spaltung nicht geleckt hat.
- **KOLLATERALSCHADEN: NULL, gemessen.** Charge 100/100 mit 447 engagierten Modellen, hart 96/100
  mit 365, Orks crowded **76 % / 232.9"**, Necrons **60 % / 119.9"**, und die gemeldeten
  Bewegungsfälle A/B/C/S1/S2 unverändert — alles identisch zur damals dokumentierten
  Baseline. (Die zwei Crowded-Zahlen sind seither von der Wandhalbierung bewegt worden und
  stehen hier als der Stand, gegen den DIESE Änderung gemessen wurde.) Auch die
  Pile-in-Profile bewegen sich nicht (`[(10,10), (3,8), (3,8)]`), und der gemeldete Warbikers-Fall
  bleibt bei 2 von 3: **dessen Front stand mit 0.01" Abstand ohnehin schon still.** Der Gewinn ist
  die MENSCHENSEITE und der CONSOLIDATE, die beide gar keine Regel hatten.
- **Getestet:** neu `test_base_contact.py` (**52/52**, fünf Abschnitte — die Schwelle bei
  0.0/0.05/0.19/0.2/0.21/5.0 gegen die KONSTANTE statt gegen ein Literal, ANY-Enemy, tote Modelle,
  **die Move-Mode-Gegenprobe über acht Modi**, Clamp und Aufnehm-Gate, und der Gruppen-Drag samt
  Überlappungsfreiheit). Plus `ab_base_contact_freeze.py` (**6 A/B-Sonden, alle beißend**) — die
  vierte legt `fall_back` in die eingefrorene Menge und meldet genau den Rückzugs-Trap.
- **Im ECHTEN Spiel belegt** (`verify_frozen_pile_in.py`): Pile In nicht anfassbar und Clamp hält;
  **dasselbe Modell im selben Kontakt lässt sich für einen Fall Back sehr wohl ziehen**; Brett
  ringt; Panel sagt es. `--neutralize` meldet das gemeldete Verhalten.

### Drei eigene Fehler, die sich wiederholen werden

1. **Die Heredoc-Falle, VIERMAL in einer Sitzung** (Fehlerklasse 21), zuletzt beim Schreiben genau
   dieses Abschnitts. Ein `\b` in einem Regex wurde durch ein Bash-Heredoc zu einem echten
   **BACKSPACE-Byte** — der Wächter suchte ein Steuerzeichen und blieb rot, während derselbe
   Ausdruck isoliert traf; `cat -A` hat es gezeigt. Ebenso wurde `\n` zweimal zu einem echten
   Zeilenumbruch und hat eine Sondendatei syntaktisch zerlegt. **Regex- und escape-haltiger Code
   gehört über Write, nie durch ein Heredoc** — und wo es sein muss, `chr(10)`/`splitlines()` statt
   eines Backslashes. Deutscher Fließtext mit Apostrophen ebenso.
2. **Zwei Bühnen maßen die FIXTURE statt des Gegenstands.** `scene()` setzte den Feind entlang
   derselben Achse, auf der `line_up()` die Einheit aufreiht — er stand also mitten in der
   Formation und überlappte ein eigenes Modell, bevor der Drag begann; die Überlappungsprüfung
   maß danach die Bühne. Und ein "ordinary move" auf einer engagierten Einheit ist nach 09.07 gar
   nicht möglich, die Prüfung bestand also aus dem falschen Grund.
3. **Eine Sonde, die nicht beißt, war viermal ein Befund über den TEST** — und einmal war der
   ehrliche Befund, dass sie die FALSCHE SUITE fuhr (die Panel-Suite ruft das Panel direkt, also ist
   `main.py`s Weitergabe für sie unsichtbar; dafür ist der Quell-Wächter da). Dazu die bekannte
   Lehre in neuer Form: **eine neutralisierte Welt muss VOLLSTÄNDIG sein** — `verify_frozen_pile_in.py`
   neutralisierte zuerst nur `is_frozen()` und meldete ein Brett, das Modelle ringte, die es nicht
   mehr einfror.
## Cleanse bot einen Knopf an, der nicht auszahlen konnte (2026-09-10)

**Gemeldet:** *"Actions wie plunder werden angeboten, obwohl Einheit gar nicht auf einem objective
steht ( muss nach Move aktualisiert werden)"*

**ERST DIE MELDUNG NACHLESEN, DANN MESSEN — und beide Hälften des Satzes waren anders gemeint,
als sie klingen.**

### Plunder war in der gemeldeten Partie nie gezogen

`logs/game_20260909_221504.log` listet die zehn Karten, die Player 1 gezogen hat: Engage on All
Fronts, Centre Ground, **Cleanse**, No Prisoners, A Grievous Blow, A Tempting Target, Bring It
Down, Overwhelming Force, Beacon, Behind Enemy Lines. „Actions **wie** plunder" nennt also die
KLASSE, und auf dem Schirm stand CLEANSE. Ohne diesen Blick ins Log wäre die ganze Untersuchung
an Plunder gelaufen — das genau nichts falsch macht.

- **Plunder selbst ist regelrichtig und bleibt unangetastet.** Seine gedruckte UNITS-Zeile
  verlangt eine TERRAIN AREA außerhalb des eigenen Territoriums, **kein Objective**. Auf map4
  sind 8 von 15 Areas plünderbar und **5 davon tragen gar kein Objective** — der Knopf erscheint
  dort also zu Recht auf einer schlichten Ruine. Das ist die Verwechslung, die die Meldung
  benennt, und sie ist eine Verwechslung, kein Fehler.
- **Die REFRESH-Hälfte war ebenfalls kein Fehler, und das ist gemessen statt angenommen.**
  `available_actions_for()` läuft pro Frame ohne jeden Cache (`action_panel.py`), `_context()`
  baut frisch bei jedem Aufruf, und jedes Ziel-Prädikat liest Modellpositionen live. Eine Einheit
  durch den ECHTEN Pfad hinein → hinaus → hinein bewegt: Angebot erscheint, verschwindet, kommt
  zurück. **Die Laufzeit-Sonde zeigt es sogar in BEIDEN Welten** — „nach 30" weg: keine Angebote"
  gilt auch in der Vor-Fix-Welt.

### Der echte Fehler: EINE Frage, ZWEI Antworten, drei Zoll auseinander

Diese Engine hat zwei Definitionen von „within range of an objective", und sie sind nicht
dieselbe Menge:

| | Definition | gelesen von |
|---|---|---|
| `objectives.is_within_range_of_objective()` | Fußabdruck **+ 3"** (12.08s Objective Consolidation) | Cleanse/Secure Asset **START**-Tor |
| `Objective.level_of_control()` | Fußabdruck-**ÜBERLAPPUNG** (14.02) | `controlled_by`, das die **COMPLETION** verlangt |

Beide Karten drucken dieselben zwei Zeilen — *"UNITS: One friendly unit within range of an
objective (excluding your home objective)"* und *"COMPLETES: End of your turn, if that unit STILL
controls that objective"* — und **beide Module hatten eine eigene Kopie des Tors, beide gleich
falsch**.

**Gemessen bei 0.5" über jedes ausgelieferte Brett** — der Anteil der Angebote, bei dem die
Einheit gar nicht zur Kontrolle beitragen kann:

| Karte | START-Tor deckt | Kontroll-Tor deckt | Fallen-Ring |
|---|---|---|---|
| map1 | 44.8 % | 20.2 % | **55 % jedes Angebots** |
| map2 | 48.8 % | 20.6 % | 58 % |
| map3 | 47.8 % | 18.5 % | 61 % |
| **map4** (gemeldet) | 46.8 % | 19.1 % | **59 %** |

**End-to-end reproduziert bei 0.06" neben dem Fußabdruck** — optisch nicht davon zu
unterscheiden, dass die Einheit darauf steht: Knopf gezeichnet, Aktion gestartet, 16.01 sperrt
Schießen UND Chargen für den Rest des Zuges, `controlled_by` bleibt `None`, **nichts vollendet**.
Der Spieler zahlt den vollen Preis für nichts, und nichts auf dem Schirm sagt warum.

**`is_on_objective()`s eigener Docstring hält GENAU DIESE Meldung schon fest** — aus dem früheren
Breach-and-Clear-Bericht (*"nur wenn Ziel auf Objective steht"*, weil der 3"-Puffer „was
triggering far more often than intended"). Der Fix landete dort und hat diese zwei Aktionen nie
erreicht.

### Der Fix: „STILL" ist das tragende Wort (User-Entscheidung)

`mission_context.objective_action_targets_for()` (38. Extraktion) fügt den KONTROLL-Term hinzu,
den die COMPLETES-Zeile ohnehin impliziert: *"if that unit **STILL** controls"* setzt Kontrolle
beim START voraus.

- **Die 3" BLEIBEN.** Der gedruckte Wortlaut ist „within range", und eine Einheit 3" daneben darf
  weiter auf Boden handeln, den ein SQUADMATE hält — das vollendet einwandfrei. Die Alternative
  (auf den Fußabdruck verengen, wie bei Breach and Clear) war die zweite Option und wurde
  ausdrücklich NICHT gewählt; die A/B-Sonde 4 fährt sie und muss beißen, sonst ist die Zusicherung
  „die Reichweite hat überlebt" weg.
- **Und es IST der Stand nach der Bewegung** — die zweite Hälfte der Meldung, gratis:
  `controlled_by` wird in `advance_turn_phase()` an jeder Phasengrenze neu gerechnet, also ist es
  in der Schussphase (der einzigen, in der beide Aktionen starten dürfen) der Stand vom Ende der
  Bewegungsphase. Kein neuer Sweep nötig.
- **Die Verengung schließt die Falle vollständig**, weil Completion `controlled_by == owner` UND
  Reichweite verlangt: was beim Start beides erfüllt, scheitert am Ende nur noch, wenn die
  Kontrolle wirklich kippt — legitimes Spiel, keine Falle.

### Warum keine der drei Suiten es sah

**Zu `cleanse_targets_for()`/`cleanse_units()` gab es GAR KEINEN Verhaltenstest** —
`test_secondary_missions.py` fasste von Cleanse nur `completes_immediately`, die Redraw-Klausel
und `cleanse_use_limit` an. Deshalb blieb es bei 553/553 grün, während sich das Verhalten
deutlich änderte.

**Zwei fremde Suiten wurden zu Recht ROT** und sind ehrlich nachgezogen statt aufgeweicht:
`test_actions.py` und `test_primary_missions.py` stellten eine Einheit AUF ein Objective und
ließen `controlled_by` auf `None` — **ein Brettzustand, der keine Phasengrenze überlebt**, weil
`update_control()` ihn dort erzeugt hätte. Beide bekommen jetzt ein `refresh_control(tokens)`, das
14.02 vom BRETT ableitet, wie `main.py` es tut, statt „Player 1" hinzuschreiben: stellt eine Bühne
eine Einheit hin, die das Objective gar nicht hält, sagt die Suite das, statt es anders behauptet
zu bekommen. `completes()` startet jetzt, während man hält, und lässt die Kontrolle DANACH kippen
— die Folge, die „STILL controls" beschreibt, und ein besserer Test als vorher.

**Der Wächter ist eine MENGENDIFFERENZ an der Quelle** (`test_actions.py`, Abschnitt 7): das Tor
hat EINE Definition, beide Leser rufen sie per AST nachgewiesen auf, und keiner darf eine private
`is_within_range_of_objective()`-Kopie behalten. Per AST, weil beide Module die Funktion auch in
PROSA nennen — die „Wächter matcht seine eigene Erklärung"-Falle, sechste Instanz. Dazu ein
Gitter-Sweep mit Liveness-Zeile: jedes angebotene Objective muss eines sein, das man kontrolliert.

### Getestet

`test_actions.py` 79 → **108/108**, `test_primary_missions.py` 264 → **268/268**,
`test_secondary_missions.py` **553/553** unverändert. Neu `ab_objective_action_gate.py`
(**6 A/B-Sonden, alle beißend**; die ganze Vor-Fix-Welt kippt beide Suiten). Volle Regression
**208 Suiten, ~18259 Prüfungen, 207 grün / 0 rot / 1 bekannt**.

**Ein eigener Sondenfehler, zwanzigste Instanz derselben Lehre:** Sonde 4 ließ die Suite mit
`NameError` ABSTÜRZEN statt sie rot zu machen (`is_on_objective` ist in `mission_context.py` nicht
importiert). Ein funktionslokaler Import in der Sondenfassung degradiert sie zu ROT — und die rote
Zeile nennt jetzt genau die richtige Zusicherung („aber ein Squadmate hält es, also weiter in
Reichweite und legal").

**Im ECHTEN Spiel belegt** (`verify_objective_action_gate.py`, `runpy` auf `selfplay.py`s echte
`main()`-Schleife, map4 — das gemeldete Brett):

| | gefixt | `--neutralize` |
|---|---|---|
| Angebot, während DU hältst | `['Cleanse: Objective Southeast']` | dasselbe |
| Angebot, während der GEGNER hält | **keins** | **`['Cleanse: Objective Southeast']`** |
| Angebot, während NIEMAND hält | **keins** | **`['Cleanse: Objective Southeast']`** |
| Angebot nach 30" weg | keins | keins |

Die letzte Zeile ist in BEIDEN Welten gleich, und das ist die Aussage: **die Reichweite hat sich
immer aktualisiert**, es fehlte allein die Kontrolle.
**VIER gestellte Tatsachen, jede benannt:** die Deck-Flagge (selfplay leert
`SECONDARY_MISSION_CARD_PLAYERS` beim Import — das dokumentierte Harness-Opt-out, hier auf den von
`game/config.py` AUSGELIEFERTEN Wert zurückgesetzt), Cleanse auf der Hand, Schussphase **und**
eigener Zug, und eine Einheit auf einem Nicht-Home-Objective. Alles danach ist echt.
**Zwei eigene Sondenfehler dabei, beide gemessen statt geraten:** `advance_phase()` wickelt hinter
Fight in den Zug des ANDEREN Spielers, wodurch `available_actions_for()` zu Recht nichts liefert
und die Sonde eine wahrheitsgetreu aussehende Null meldete; und die Sonde MISST die Ablehnung
jetzt (`measured refusal: plays_cards=False`), statt eine Geschichte über den Harness zu erzählen.
