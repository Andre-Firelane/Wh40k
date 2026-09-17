# Unit Statistics und Toggle-Leiste

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Unit Statistics — das Resümee der Partie (game/battle_stats.py, game/ui/unit_stats_overlay.py)

**Ein großes Overlay mit drei Tabellen pro Spieler** (User: "EIn großes Overlay, dass
eineheitenstatistiken anzeigt wäre cool. Beim echten 40k macht man sich immer gedanken, wie jede
einheit performt hat als resumee"). Knopf **neben dem KI-Schalter**; umschaltbar pro Spieler über
die zwei Fraktions-Badges.

**Vorher sammelte diese Engine GAR KEINE Statistiken** — gemessen: kein Modul unter `game/`, und
die einzigen Buchführungen sind zweckgebunden und schmal (`record_destroyed_squad` für VP,
`moved_distance_this_turn` für [HEAVY] 24.16, pro Zug überschrieben).

### Die drei Zahlen, und warum sie so definiert sind

| Tabelle | Definition |
|---|---|
| **Best Killing** | zugefügte Wunden + Punkte **pro rata**: `(wunden/startwunden_des_ziels) × ziel.points` |
| **Best Tanking** | `(angriffe − gelandete) × max_damage(waffe)` + FNP + Schadensminderung |
| **Fastest** | Zoll, **jeder** bestätigte Zug, gemessen am weitesten gelaufenen Einzelmodell |

- **Punkte pro rata statt „Punkte zerstörter Einheiten"** (User-Entscheidung): dieselbe Rechnung,
  die `observation.damage_value()` schon benutzt (`fraction_of_unit × points`), und sie braucht
  **keine Kill-Attribution** — die diese Engine nachweislich nicht hat
  (`main.py`s Todes-Sweep: *"there is no kill attribution here"*). Wer einen 300-Punkte-Panzer
  weichschießt, bekommt seinen Anteil.
- **Tanking zählt ANGRIFFE, nicht Schadenspunkte.** „Potenzial minus tatsächlich" wäre die
  naheliegende Formel und ist falsch: sie zählt ÜBERSCHUSSSCHADEN mit, und billiges Kanonenfutter
  stünde an der Spitze der Tabelle (eine D6+2-Waffe auf einen 1-Wunden-Guardian „verhindert" dann
  7). FNP und Minderung werden **getrennt und ausdrücklich** gezählt, nie als Restgröße — sonst
  zählte ein D6, der 3 würfelt, als verhindert.
- **`weapons.max_damage()` ist neu und liest die NOTATION, nie den flachen Int daneben.**
  Gemessen: **38 von 56** Waffen mit `damage_notation` speichern einen Platzhalter, der nicht das
  Maximum ist (Bright Lance 8 für D6+2 — richtig; Starshot 3 für D6; Wurrtower 1 für D6). Den zu
  lesen ließe dieselbe gedruckte Charakteristik zwischen 1 und 8 herauskommen.

### Wo aufgezeichnet wird

- **`Token.apply_damage()` ist ein echter Einzeltrichter** — 4 Aufrufstellen, 3 davon die drei
  `_finish_apply()` in `damage_resolution.py`. Dort sind Waffe, Ziel und Betrag bekannt, **der
  Angreifer nicht**.
- **`DamageAllocationSession` und `DevastatingWoundAllocationSession` haben je 2 Bauplätze**, beide
  in den Angriffs-Controllern → sie bekommen ein optionales `attacker_squad=`.
  **`MortalWoundAllocationSession` hat 22 über 21 Module** und bleibt unattributiert (siehe
  Benannte Lücke).
- **Der Tanking-Abschluss liegt bei `_finish_group()`, NICHT bei `_check_allocation_done()`** — und
  das ist der Kern: **eine komplett danebengegangene Salve baut gar keine `DamageAllocationSession`**,
  also läuft jene Methode nie, und das ist der wichtigste Fall überhaupt. `_finish_group()` ist der
  eine Ausgang, den jeder Pfad nimmt.
- **Fehlschläge an der WURFSTELLE zu zählen wäre DOPPELT** (die Reroll-Zweige rechnen neu und
  addieren) — deshalb `attacks` (in `_continue_resolution_with_attacks()`, dem gemeinsamen Schwanz
  beider Pfade) gegen `landed` (aus `damage_session.failed` plus den Devastating-Crits, die den
  Save überspringen und deshalb NICHT verhindert sind).
- **`battle_stats.CURRENT` ist eine MODUL-Ablage**, gesetzt von `main()` — exakt die Begründung, die
  `MortalWoundAllocationSession.on_mortal_wounds` schon trägt: 25 Bauplätze über 20 Module sollen
  nicht lernen, dass es Statistiken gibt. Sie liegt bei `battle_stats`, damit es EINE Antwort auf
  „wohin gehen Statistiken" gibt statt einer Kopie je meldendem Modul.
- **Strecke bei `confirm_move()`**, neben `action_controller.notify_move()` — der Stelle, die im
  Kommentar selbst als *"the one place every confirmed move passes through"* ausgewiesen ist.
  `moved_distance_this_turn` wird bewusst NICHT wiederverwendet (Zuweisung statt Summe, pro
  Spielerzug geleert, absichtlich auf Bewegungsphasen-Züge verengt); die ARITHMETIK ist als
  `MovementController._farthest_moved()` extrahiert und hat jetzt zwei Leser.
- **Gekeyt nach `squad.name`**, dem dokumentierten Identifier — der einzige Schlüssel, der den
  `--load`-Neubau überlebt. `absorbed_into` (19.01) wird verfolgt.

### Das Overlay

Form nach `army_rules_overlay.py`: eigenes `handle_event`, also **NICHT in `_front_notice()`**
(das ist die Ordnung der Klick-weg-Notices mit `.dismiss()`), Scrim, Scrollen per Rad/Tastatur,
Klick oder ESC schließt. **`event.button == 1` ist tragend** — pygame liefert zu jeder Radrastung
zusätzlich MOUSEBUTTONDOWN 4/5, ohne die Prüfung schließt Scrollen das Fenster.
**Die Badges werden VOR dem Dismiss-Zweig getroffen**, sonst schließt ein Armee-Wechsel den Screen.

- **Der Knopf leitet seine Lage aus `ai_mode_toggle_rect()` ab** und setzt sich links daneben —
  „neben" ist damit per Konstruktion wahr. **Ausdrücklich KEIN `avoid_rects`**: der KI-Schalter
  soll stehenbleiben, und `test_game_menu.py` pinnt dessen Abwesenheit im Negativ. Im echten Spiel
  gemessen: Knopf `(614,40,78,26)`, Schalter `(700,40,92,26)`.
- **`game/ui/stat_table.py`** ist die Extraktion am ZWEITEN Konsumenten: `column_layout()`/
  `draw_row()` lagen privat in `UnitDatacardOverlay` (Statblock und Waffentabellen), die drei
  Resümee-Tabellen stellen dieselben zwei Fragen. `unit_datacard.py` DELEGIERT und behält seine
  Konstanten, seine 110 Pixel-Prüfungen sind also per Konstruktion unverändert. **Bewusst NICHT
  absorbiert:** `mission_cards._draw_scoring()` (rechtsbündige VP-Spalte) und `rules_body`s
  `"table"`-Block (zwei Zellen, kein Umbruch) — andere Formen, kein zweiter Konsument.
- **Zahlenspalten haben eine FESTE Breite**, keinen Anteil: sonst landen eine Zwei- und eine
  Drei-Spalten-Tabelle an verschiedenen x, und die drei Abschnitte lesen sich nicht mehr als eine
  Seite.
- **Eigener Fehler, von der Vorhersage-gegen-Gezeichnetes-Prüfung gefunden:** Höhenrechnung las
  `section_font.get_height()` (13), das Zeichnen die gerenderte Fläche (15) — 6 px über drei
  Abschnitte. `_heading_height()` ist jetzt die eine Antwort. Dieselbe Prüfung hat bei den
  Missionskarten schon einmal einen doppelt gezählten Abstand gefunden.

### Am ENDE der Schlacht geht es von selbst auf (2026-09-11)

**Gemeldet:** *"Am ende des spiels soll das Statistik Overlay angezeigt werden."* Reproduziert an
der Quelle: `unit_stats_overlay_view.show()` hatte GENAU EINE Aufrufstelle, den Knopf in der
Brett-Ecke. Die Schlacht endete auf dem Punktekasten, ein Klick legte ihn weg, und das Resümee —
also die Analyse genau des Punktestands, den man gerade gelesen hat — wurde nie angeboten.

- **GEKETTET statt gleichzeitig erhoben, und das ist erzwungen statt gewählt:** die
  Statistik-Overlay wird als LETZTES im Frame gezeichnet (über jeder Notice) und besitzt jedes
  Event aus ihrem eigenen Pre-Chain-Zweig — beide zugleich zu erheben würde den Endstand unter ihr
  begraben. Also Punktestand, dann die Analyse, wie er zustande kam; das ist ohnehin die
  Reihenfolge, in der man sie lesen will. Eine Zeile in `main.py`s Dismiss-Zweig, falls es
  andersherum sein soll.
- **Die drei Argumente sind DIE des Knopfes**, nicht eine zweite Herleitung: zwei Aufrufstellen,
  die sich darüber uneinig werden, welche Armeen oder welches Ledger auf dem Schirm sind, sind
  genau die Drift, die dieses Repo laufend konsolidiert. Eine im Kampf AUSGELÖSCHTE Einheit steht
  weiter auf der Tabelle (das Ledger keyt nach NAMEN und filtert nicht auf Lebende), nur ohne ihre
  Kunst — `state.all_squads()` führt sie nicht mehr, und das ist richtig: sie hat die Zahlen
  verdient.
- **Die HINWEISZEILE des Punktekastens musste mit**, sonst verspricht sie den Schirm, den man ZWEITENS
  erreicht: `battle_end_overlay.DISMISS_HINT` steht jetzt auf "Click for the unit statistics".
  Als KONSTANTE und nicht als `show()`-Argument — der Kasten hat genau einen Aufrufer und der
  kettet immer, ein Parameter wäre nur ein zweiter Ort zum Widersprechen.
- **Der Wächter pinnt SIBLING STATEMENTS, nicht einen Teilstring** (`test_battle_end.py` §4): die
  zwei Aufrufe müssen in DERSELBEN Anweisungsliste stehen, also erreicht jede Bedingung, die den
  Dismiss erreicht, auch die Show — und kein Zweig lässt sich dazwischenschieben. Ein Teilstring
  `unit_stats_overlay_view.show(` ist schon durch die Aufrufstelle des Knopfes wahr, und ein
  AST-Pin, der bloß den Zweig durchläuft, überlebt ein `if False:` eine Ebene tiefer (eigene
  A/B-Sonde dafür).
- **Die Hinweis-Prüfung misst das GEZEICHNETE, nicht die Konstante** — und das ist ein Befund der
  eigenen Sonde: die Fassung, die die Konstante ausliefert und in `draw()` ihr altes Literal
  behält, erfüllte jede Prüfung gegen `DISMISS_HINT` und zeigte weiter den alten Text. Gemessen
  wird jetzt über einen Spion auf `hint_font.render`. **Beide Hälften bleiben** (nennt die
  Statistik UND nennt das Brett nicht mehr): die erste besteht auf einem Hinweis, der beides
  verspricht.
- **Getestet:** `test_battle_end.py` 34 → **50/50** (neuer Abschnitt 4) plus neu
  `ab_battle_end_resume.py` (**8 A/B-Sonden, alle beißend**; die ganze Vor-Fix-Welt kippt 4).
  Volle Regression **224 Suiten, ~20503 Prüfungen, 223 grün / 0 rot / 1 bekannt**, `--smoke`
  komplett grün.
- **Im ECHTEN Spiel belegt** (`verify_battle_end_resume.py`, `runpy` auf `selfplay.py`s echte
  `main()`-Schleife):

  | | gefixt | `--neutralize` |
  |---|---|---|
  | Punktekasten erhoben (durch `_check_battle_end()`) | Frame 501 | Frame 501 |
  | Resümee schon dahinter offen? | **False** | False |
  | **Resümee nach dem ECHTEN Klick geöffnet** | **Frame 501, 5 Zeilen** | **NIE** |
  | Frames, in denen es gezeichnet wurde | **1008** | **0** |

  **EINE Tatsache wird gestellt** — `turn_tracker.battle_over`, das Flag, das `advance_phase()` im
  letzten Zug der letzten Runde setzt. Eine Schlacht sind ~50 Phasenwechsel und ein MockAgent-Lauf
  schafft gemessen ~7 je 3000 Frames (die dokumentierte Harness-Grenze), das letzte Zugende ist
  passiv also unerreichbar, und ein passiver Zähler hätte 0 gemeldet und wie ein Bestehen
  ausgesehen. Alles danach ist echt: `_check_battle_end()` samt seinem Entscheidungs-Tor, die
  echte Event-Kette, die echten Overlays, das von `main()` veröffentlichte Ledger.
  **`--neutralize` blendet NUR die Aufrufstelle des Battle-End-Zweigs aus** (per Zeilennummer aus
  dem AST), der Ecken-Knopf funktioniert weiter — das ist die Vor-Fix-Welt und nicht eine Welt mit
  abgeschaltetem Feature.
  **Zwei eigene Sondenfehler, beide gemessen:** ein stehender Prompt hält `_check_battle_end()` per
  Design auf, wird also über den Pump beantwortet statt umgangen; und selfplay klickt pro Frame
  aufs Brett, sodass die Resümee-Overlay sich in ZWEI Frames wieder schloss — die Sonde hält
  deshalb kurz die Maustasten zurück, sonst misst "es wurde gezeichnet" nichts.

### Speichern

Optionaler `stats`-Abschnitt in `scene_io.capture()` plus `restore_stats()`, **`FORMAT_VERSION`
bleibt 1** (der `armies`/`missions`-Präzedenzfall; nur geschrieben, wenn nicht leer, also sind
unberührte Schlachten byte-identisch). Wiederhergestellt NACH `begin_battle()`.

### Benannte Lücken

1. **Mortal Wounds aus Fähigkeits-Modulen sind unattributiert** — sie zählen in
   `BattleStats.unattributed_wounds` und krediteren keinen Killer. Tanking ist davon UNBERÜHRT
   (es liest keine Wunden). Stufe 2 wäre `source_squad=` über 21 Module, bewacht als
   MENGENDIFFERENZ; `verify_unit_stats.py` misst die Größe, bevor das entschieden wird.
2. **`spirit_of_gork.py:271` schreibt `current_wounds` direkt** und umgeht `apply_damage()`.
3. **[SUSTAINED HITS] untertreibt „verhindert" leicht** — gezählt werden die Angriffe der Waffe,
   nicht die Zusatztreffer des Keywords. Vertretbar: einen Angriff, den es nie gab, hat der
   Verteidiger nicht verhindert.

### Getestet

Neu `test_battle_stats.py` (**61/61**, acht Abschnitte — durch die ECHTEN Controller, Fernkampf
UND Nahkampf, inklusive der komplett danebengegangenen Salve und eines echten `confirm_move()`)
und `test_unit_stats_overlay.py` (**75/75**, auf PIXELN). Neu **`ab_unit_stats.py`: 24 A/B-Sonden,
alle beißend**.
- **DREI Sonden bissen zuerst NICHT, und alle drei waren Befunde über den TEST** (Fehlerklasse 24):
  die Suite fuhr **gar keine Nahkampf-Aktivierung** (`game/fight.py` ist eine zweite Verdrahtung
  derselben Nähte); die Strecke wurde nur am Ledger geprüft und nie durch das echte
  `confirm_move()`; und die Leer-Zustands-Prüfung zählte die **Fußzeile** mit, die dieselbe Farbe
  hat, bestand also auch ohne Leer-Text.
- **Zwei eigene Fixture-Fehler dabei**, beide gemessen: `tk.line_up()` spreizt zehn Boyz über
  09.02s 9"-Grenze (der Confirm scheiterte aus einem Grund, der mit Statistiken nichts zu tun
  hat), und bei lauter Sechsen **rettet** ein 5+-Save — der Nahkampf-Test maß die falsche Sache.
  Dazu: `confirm_move()` gibt gar keinen Wahrheitswert zurück, der Erfolgstest ist `errors`
  (Fehlerklasse 6).
- **Zwei fremde Pins wurden zu Recht rot** und sind nachgezogen; einer von ihnen **stürzte per
  `.index()` ab statt rot zu werden** und degradiert jetzt.

**Im ECHTEN Spiel belegt** (`verify_unit_stats.py`, `runpy` auf `selfplay.py`s echte
`main()`-Schleife):

| | gefixt | `--neutralize` |
|---|---|---|
| Einheiten auf der Killing-Tabelle | **1** | 0 |
| Einheiten auf der Tanking-Tabelle | **1** | 0 |
| Einheiten auf der Fastest-Tabelle | **1** (passiv, 6 bei 8000 Frames) | 0 |
| STATS-Knopf gezeichnet | **1199 Frames, neben dem Schalter** | 0 |

**EINE Tatsache wird gestellt, und die Messung sagt warum:** über **8000** Frames löst ein
MockAgent-Lauf **null** Angriffsgruppen auf (die dokumentierte Harness-Grenze), ein passiver
Zähler hätte also 0 gemeldet und wie ein Bestehen ausgesehen. Gestellt ist der ANGRIFF; alles
danach ist echt — `main()`s eigene Squads, eine echte `DamageAllocationSession`, das echte
`_finish_apply()`, das von `main()` veröffentlichte Ledger. Der verhinderte Schaden kam dabei
ungeplant aus **Molten Form des Avatars**, also wirklich aus der Minderungs-Naht.
Perf-Gegenprobe: `measure_shooting_frame_cost.py` unverändert bei **0.017 ms/Frame**.

## Die Toggle-Leiste unten links (game/ui/button_style.py, game/whole_unit_drag.py)

**Aus drei Text-Knöpfen ist EIN echter Schalter geworden** (User: "anstatt des textes On/Off soll
es einen farblichen unterschied geben, damit man schneller sieht, ob etwas eingeschaltet oder
ausgeschaltet ist. vielleicht grün/grau. noch besser wäre ein richtiger optischer toggle" — plus
"den LOS Check Knopf brauch ich nicht mehr. der soll immer aktiviert sein" und "ich glaube, dass
man Block Deployment und Block Movement zusammenfassen kann. Mir fällt keine Situation ein, wo man
das getrennt bräuchte").

- **Gemessen VOR der Änderung, und das ist der ganze Befund:** mit allen drei Toggles umgelegt
  waren die gezeichneten Zeilen **PIXELIDENTISCH** — der einzige Unterschied im ganzen Streifen
  war das Wort "On" bzw. "Off" im Label. Der Zustand war also ausschließlich durch LESEN zu
  erkennen, obwohl er wie ein Schalter aussah.
- **`button_style.draw_toggle()` trägt den Zustand DREIFACH**, und die Reihenfolge ist die
  Begründung: der KNOB liegt rechts (an) bzw. links (aus) — der einzige Hinweis, der Graustufen
  und Farbenblindheit übersteht, im Test an einer graustufig gerechneten Kopie gepinnt —, das
  TRACK ist grün/grau, und Rahmen plus Text folgen derselben Farbe, damit die Zeile aus der Ferne
  lesbar ist, ohne den Schalter zu suchen. Das Grün ist bewusst die `confirm`-Palette: eine zweite,
  leicht andere grüne Familie läse sich als andere Art von Ding. Grau statt des Default-BLAUS,
  weil Blau in diesem Panel "Knopf" heißt — genau die Verwechslung, die hier behoben wird.
- **`pressed` bekommt KEINE dritte Palette** (anders als `draw_button()`): ein Toggle kippt beim
  Mouse-Up, ein Pressed-Look in der ANDEREN Farbe zeigte also einen Zustand, in dem das Steuer
  noch nicht ist. Es teilt den Hover-Look.
- **Es ist kein `accent`, und das ist der Grund für die eigene Funktion:** ein Accent sagt, was ein
  Druck KOSTET (blau gratis, grün weiter, rot abbrechen, violett CP), ein Toggle sagt, in welchem
  ZUSTAND das Steuer IST. Ein bereits eingeschalteter Knopf ist keine andere Art von Ausgabe.
- **`toggle_height()` gibt allen Zeilen EINE Höhe** — gemessen: bei 200 px umbrach "Move Whole
  Squad" auf zwei Zeilen und "Place as Block" nicht, also standen 38 px neben 32 px, was sich als
  Layout-Unfall liest. Nach dem Zusammenlegen ist das ohnehin moot: "DRAG WHOLE UNIT" misst 133 px
  und passt auf eine Zeile.

### Der LOS-Check ist weg — und der Skip hängt jetzt am DRAG, nicht an der Einstellung

`live_los_highlight_enabled` und `toggle_live_los_highlight()` sind **ersatzlos entfernt**; die
Live-Sichtlinien-Markierung läuft unbedingt. **Im echten Spiel belegt, nicht nur im Quelltext:**
mit einem Drag-Anker durch `main()`s eigene Schleife übergibt sie dem Renderer **17** Feindmodelle,
in der VOLLSTÄNDIG wiederhergestellten Vor-Fix-Welt (Gate in `main.py` UND das Off-by-default-Flag)
**0**. Eine halbe Sonde — nur das Flag, ohne das Gate — meldete 6 gegen 17 und hätte den Fix für
wirkungslos erklärt (Fehlerklasse 16 in Reinform).

**Der Skip für den Gesamttrupp-Drag BLEIBT, aber unter einer anderen Bedingung.** Gemessen: eine
Neuberechnung kostet **8.3 ms** auf einem 142-Modell-map2-Brett, also eine halbe Frame — er ist
begründet. Falsch war, worauf er hörte: auf die EINSTELLUNG (`group_move_enabled`) statt darauf, ob
gerade wirklich gezogen wird. Nach dem Zusammenlegen steht diese Einstellung per Default auf AN,
die zwei User-Entscheidungen hätten sich also gegenseitig aufgehoben — die Markierung wäre per
Default aus gewesen, genau was der User abgeschafft haben wollte. Gelesen wird jetzt
`input_manager.dragging_group`/`dragging_setup_group`, beide auf Mouse-Down gesetzt und auf
Mouse-Up gelöscht. **A/B im echten Spiel:** mit dem Gate zurück auf der Einstellung und dem Toggle
an → **0** markierte Modelle, mit dem Drag-Gate → **6**.

### `game/whole_unit_drag.py` — 25. Extraktion, und die erste, die zwei Flags VERSCHMILZT

`SetupController.block_placement_enabled` (03.02: Trupp als Block ablegen und als Block ziehen) und
`MovementController.group_move_enabled` (09.02: Trupp starr ziehen) waren dieselbe Frage zweimal,
mit zwei Toggles und zwei Defaults. Beide sind jetzt **PROPERTIES auf einen Wert** in diesem Modul.

- **Ein eigenes Modul, nicht ein Flag auf einem der Controller:** keiner besitzt die Frage, und
  einen auf den anderen zu zeigen ließe Set Up von Movement (oder umgekehrt) abhängen für eine
  Einstellung, die keinem von beiden gehört. Die NAMEN bleiben, also sind alle 14 Lesestellen und
  jeder Test, der zuweist, unverändert — und es gibt genau eine Stelle, an der der Wert lebt.
- **Die `__init__`-Zuweisungen MUSSTEN weg**, nicht bloß der Sauberkeit wegen: als Property würde
  `self.block_placement_enabled = True` im Konstruktor die Wahl des Spielers bei jedem neuen
  Controller stillschweigend zurücksetzen. Als eigene Testzeile gepinnt (ein frischer Controller
  darf nichts zurücksetzen) — dieselbe Falle, wegen der beide Flags früher ihren Per-Move-Reset
  verloren haben.
- **DEFAULT AN**, weil es der Default der Hälfte ist, die der User ausdrücklich bestellt hat ("ich
  will oft nicht jedes modell einzeln anfassen beim platzieren"). Der Preis ist benannt:
  Movements alter Default war AUS, ein Bewegungs-Drag zieht jetzt also standardmäßig den ganzen
  Trupp. Sichtbar statt still — der Schalter ist grün/grau mit Knopf.
- **Der Toolbar-Parameter `setup_controller` ist entfallen**, was die stärkste Quellaussage über
  das Zusammenlegen ist: die Leiste braucht den Controller nicht mehr, den ihre zweite Zeile
  gelesen hat.

**Getestet:** neu `test_toggle_switches.py` (**51/51**, fünf Abschnitte — Pixel auf einer echten
Surface, die Graustufen-Probe, die Klickbarkeit, die Verschmelzung in beide Richtungen und die
LOS-Naht) plus **15 A/B-Sonden**, jede kippt genau ihre eigenen Prüfungen; die faithful
Vor-Merge-Welt (zwei echte unabhängige Instanz-Flags, nicht eine umbenannte Property) kippt **15
von 51**. **Vorher gab es zu diesem Streifen GAR KEINEN Test** — deshalb konnten drei Zeilen, die
in beiden Zuständen gleich aussahen, unbemerkt bleiben. Volle Regression **158 Suiten, ~13671
Prüfungen, 157 grün / 0 rot / 1 bekannt**, alle fünf Smokes und `selfplay.py` auf map2 und map3.

### Das Reichweiten-Lineal (game/aura_ruler.py) — zweiter Schalter im Streifen

**Ein Aura-Toggle plus ein Radio aus acht Radien** (User: "es gibt einen Aura toggle. wenn man den
aktiviert erscheinen weitere knöpfe die wie Radio Buttons funktionieren. 3" 6" 9" 12" 15" 18" 24"
36" ... dann wird bei angewählten modellen die entsprechende Aura subtil angezeigt. optisch wie die
deathguard Aura, aber in weiß. das hilft bei Reichweiten"). Das ALT-Lineal beantwortet "wie weit
ist DIESER Punkt von JENEM"; das hier beantwortet es für eine ganze Einheit auf einmal und bleibt
stehen, während man sich umsieht.

- **ZWEI Steuer, aber nur EINE Antwort.** `active_radius()` gibt den Radius oder `None`, und das
  ist die einzige Frage, die Panel und Renderer stellen — sonst könnten die beiden verschiedener
  Meinung darüber sein, ob gerade etwas auf dem Schirm ist. Der Radius ÜBERLEBT das Ausschalten
  (man kehrt zu der Distanz zurück, die man gelesen hat).
- **Modulweit wie `whole_unit_drag.py`** und aus demselben Grund: eine Sitzungs-Vorliebe für die
  ganze Anwendung, bewusst nicht pro Schlacht zurückgesetzt.
- **Das Radio existiert nur, solange der Toggle an ist** — dieselbe Konvention wie Pager und
  Confirm in `tile_screen.py`: kein Chrome für ein Steuer, das nichts tun kann. Acht tote Knöpfe
  unter einem Aus-Schalter wären acht Dinge zum Erklären.
- **Ein GITTER, 4 Spalten × 2 Zeilen.** Gemessen: das breiteste Label (`36"`) misst 23 px, eine
  4-Spalten-Zelle lässt 31 px Textraum, also bricht nichts um. Acht Zeilen voller Breite wären in
  einem 220-px-Panel höher als der restliche Streifen. **Die Zeilenzahl ist ABGELEITET**, damit ein
  neunter Radius nicht still unten herausfällt.
- **Der aktive Knopf wird PRESSED gezeichnet** — genau das, was die Biom-Reihe des Kartenscreens
  für einen Mehrwege-Schalter schon tut, also wird keine zweite Bildsprache erfunden.
- **Die acht Callbacks binden ihren Radius bei der DEFINITION.** Die naheliegende Schleifen-Form
  fängt die Laufvariable ein, und dann setzen alle acht 36 — eigene A/B-Sonde dafür.
- **Gezeichnet wie die Death-Guard-Aura, weil genau das bestellt war:** opake Kreise in EIN
  wiederverwendetes Overlay, das Ganze EINMAL verblendet. Bei zwanzig Modellen stapelten
  transparente Kreise sich sonst zu Hotspots, wo Modelle dicht stehen — und "innerhalb 6\" von
  zwei Modellen" ist dasselbe wie "von einem". Die Vereinigung, flach, IST die Form der Frage.
- **WEISS und schwächer: `RANGE_AURA_ALPHA = 26` gegen die 40 der Contagion-Aura**, gemessen statt
  geraten. Grün heißt Nurgle's Gift und sonst nichts, ein Lineal darf nicht wie eine Regel
  aussehen. Auf dem Arena-Boden (dem Default) kommt Weiß bei 26 auf Kontrast **22.7** — so viel wie
  die grüne Aura auf ihrem BESTEN Untergrund. **Benannte Schwäche: auf dem hellen Wüsten-Biom
  bleibt Weiß mit 3.3 fast unsichtbar** — dort ist Grün mit 22.7 im Vorteil. Weiß war die
  ausdrückliche Vorgabe; falls das Wüsten-Biom in Gebrauch kommt, ist das die Stelle, an der eine
  dunkle Kontur oder ein zweiter Farbwert fällig wird.
- **Der Radius wird von der BASISKANTE gemessen** (`model.radius_in + radius_in`), wie der
  Engagement-Ring und die Contagion-Aura — dieses Spiel misst Basis zu Basis. Dieselbe Näherung wie
  dort, und genauso benannt: die Basis des ZIELmodells macht den echten Abstand noch kürzer.
- **NUR das ANGEKLICKTE MODELL** (User: "die Aura Funktion zeigt momentan für jedes Modell im
  Squad die Aura an. wenn ich ein spezifisches Modell anklicke soll nur die Aura dieses Modells
  angezeigt werden"). Vorher wurde jedes Modell der gewählten Einheit umringt — bei einem
  20-Krieger-Blob eine Decke statt einer Messung. **Die Vereinigung aus zwanzig Ringen beantwortet
  „könnte IRGENDWER von uns das erreichen", und das ist selten die Frage:** eine Waffenreichweite,
  eine Aura, ein Charge gehören EINEM Modell, von dort wo es steht.
  - Gelesen aus `movement_controller.selected_model` — dem Anker, den `game/selection.py` ohnehin
    führt („the exact model clicked") und von dem auch die Sichtlinien-Markierung ausgeht; damit
    können Lineal und Markierung nicht auf verschiedene Modelle zeigen.
  - **`model=None` ringt weiter die EINHEIT, und das ist kein Rest:** die Auswahl kann OHNE Anker
    gesetzt werden (`start_scout_move()` und `torchstar_gambit.py` schreiben `selected_squad`
    direkt), und dann gibt es kein angeklicktes Modell zu ehren. Der Renderer prüft zusätzlich
    `model.squad is squad` — ein Direktschreiber lässt den Anker der VORIGEN Auswahl stehen, und
    den zu ehren setzte das Lineal auf eine Einheit, die niemand angesehen hat. Gemessen, nicht
    angenommen.
  - Tote Modelle zeichnen nichts: `remove_dead_models()` läuft einmal pro Frame, eine Leiche steht
    also noch in `squad.models` (Fehlerklasse 12) — das gilt jetzt auch für einen toten ANKER.
  - **Getestet:** `test_aura_ruler.py` 49 → **59/59** (neuer Abschnitt 4b: die Fläche eines Rings
    gegen die der ganzen Einheit, gemessen AN den Modellen statt als Summe, damit „weniger Tinte"
    nicht als „das richtige Modell" durchgeht; der Stale-Anker-Rückfall; der tote Anker) plus
    **`ab_aura_one_model.py`, 3 A/B-Sonden, alle beißend**.
    **Eine Sonde war ein Befund über den TEST:** mein Verdrahtungs-Pin auf
    `model=movement_controller.selected_model` war durch ein still fehlgeschlagenes `str.replace`
    nie in die Datei gelangt — die Sonde „main.py reicht den Anker nicht weiter" blieb grün,
    obwohl der Pin fehlte. Genau dafür laufen die Sonden.
  - **Im ECHTEN Spiel belegt** (`verify_aura_one_model.py`, `runpy` auf `selfplay.py`s echte
    `main()`-Schleife): ein Modell von `1 Dark Reapers 1` (5 Modelle) über den ECHTEN
    `MovementController.select()` gewählt → **Lineal ringt 1 von 5**; `--neutralize` (Vor-Fix-Welt)
    → **5 von 5**.
    **Zwei eigene Sondenfehler unterwegs, beide gemessen statt geraten:** ein synthetischer
    Brettklick trifft, was gerade auf dem Pixel steht — Modelle bewegen sich zwischen Aufnahme und
    Klick, und `can_select()` lehnt fremde Einheiten außerhalb ihres Zuges ab, sodass BEIDE Läufe
    einen einzelnen Doomsday Ark maßen („1 von 1" ist in beiden Welten wahr). Die Sonde treibt
    jetzt denselben Einstiegspunkt, den der Klick treibt, und meldet einen Ein-Modell-Treffer
    ausdrücklich als INCONCLUSIVE statt als Bestehen.
- **Getestet:** neu `test_aura_ruler.py` (**49/49**, fünf Abschnitte) und `ab_aura_ruler.py`
  (**9 A/B-Sonden, alle beißend** — darunter die Late-Binding-Schleife, die Mitte-statt-Kante-
  Messung und das opake Blitten). `test_toggle_switches.py` wurde zu Recht rot (fünf Zeilen der
  Form "ES GIBT GENAU EINEN Toggle") und ist auf zwei nachgezogen; sein Helfer pinnt das Lineal
  jetzt AUS, sonst hinge seine Zeilenliste an einer modulweiten Vorliebe. Volle Regression
  **169 Suiten, ~14989 Prüfungen, 168 grün / 0 rot / 1 bekannt**, alle acht Smokes.
- **Im ECHTEN Spiel belegt** ("gebaut, aber nie GEFÜTTERT" hat dieses Repo sechsmal getroffen):
  ein Spion an `draw_range_aura` in `main()`s echter Schleife meldet **120 Aufrufe in 121 Frames**,
  der Toggle wurde über den ECHTEN Panel-Callback umgelegt, die Radien 6 und 12 erreichten den
  Renderer, und ein gewähltes 5-Modell-Squad mit 12" tönt **22.9 % des sichtbaren Bretts** — der
  Pixel unter dem Modell geht von (66,19,42) auf (86,43,64), also genau der Weiß-Hub, den Alpha 26
  vorhersagt.
