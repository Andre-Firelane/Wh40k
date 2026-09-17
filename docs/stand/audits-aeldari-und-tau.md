# Stratagem-Prüfungen Aeldari und T'au

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Werden die Aeldari-Stratagems überhaupt ANGEBOTEN? (Prüfung, 2026-09-07)

**Auftrag:** *"Teste ob alle Stratagems der Aeldari auch wirklich zum korrekten
Zeitpunkt dem Spieler als Button angeboten werden und ob sie dann auch korrekt
funktionieren. Gleiches für Enhancements."* Anlass war die T'au-Charge, bei der
genau das reihenweise schiefging (`## Elf Meldungen aus drei Partien`).

**Die Prüfung hat FÜNF echte Fehler gefunden, vier davon in der Aeldari-Seite
und einen darunter, der vier Fraktionen betrifft.**

### Die strukturelle Lücke, aus der alles folgte

**KEINE Testdatei des Repos hat je `proactive_stratagems=` an
`ActionPanel.draw()` gereicht.** Die 19 Aeldari-Panel-Buttons — die größte
Gruppe im Spiel — waren ausschließlich per `"proactive_stratagems.add(X(" in
_main` und per direktem `can_use()` belegt. Beide Formen gelten unverändert,
während das Panel gar nichts zeichnet. `test_aeldari_detachment_stratagems.py`
war 17 % Quell-Grep, 26 % Prädikat, **0 % UI**.

### Die fünf Fehler

| # | Fehler | Wirkung |
|---|---|---|
| 1 | **Skyborne Sanctuary** las `turn_tracker.phase != PHASE_FIGHT` live, wird aber am Übergang NACH `advance_phase()` angeboten — und Fight ist die letzte Phase, die Uhr steht dann auf Command | **nie angeboten**, beide Instanzen (Warhost + Aspect Host) |
| 2 | **Overflight** dreifach tot: dasselbe Live-Tor; `reset_phase()` LÖSCHTE das Killer-Register, das das Angebot gleich lesen will (der Reset-Block läuft VOR den Angeboten); und `notify_unit_destroyed` bekommt regelmäßig `killer_squad=None` | nie angeboten, und selbst repariert ohne die dritte Klausel blind für die meisten eigenen Auslöser |
| 3 | **Khaine's Vengeance**: `is_busy` steht im Phasen-Tor, aber weder `on_dice_acknowledged()` noch `pending_damage_choice` war irgendwo verdrahtet | **harter Deadlock** — einmal gekauft, kein Phasenwechsel mehr |
| 4 | **Crushing Strides**: `on_dice_acknowledged()` nie gerufen | wirkungslos, und `_pending` sperrt es danach für die ganze Schlacht |
| 5 | **`MortalWoundOfferController` leerte seine Session nie** — keine `pending_damage_choice`, kein `choose_damage_model`, kein Drain | Mortal Wounds von **sechs** Fähigkeiten über **vier** Fraktionen landen gegen Mehr-Modell-Ziele **nie** |

**1, 2 und 4 sind exakt der Fehler, für den `game/phase_window.py` bzw. der
Dice-Ack-Wächter schon existieren** — Cost of Victory und Webway Tunnel wurden
so repariert, diese zwei nicht. Fix ist wörtlich deren Vorlage.

**Overflights `reset_phase()` ROTIERT jetzt statt zu löschen** (`_killers_this_phase`
→ `_killers_ending_phase`), und die Owner-Regel ist ins ANGEBOT gewandert, wo
die Grenze bekannt ist (`offer_at_end_of_phase(squads, phase_before,
ending_player)`) — `can_use()` wird Frames später beantwortet und darf die Uhr
gar nicht mehr lesen. Die aufgeschobene Gutschrift (`credit_owed_kills()`)
folgt `game/montka_pinpoint_counter_offensive.py`.

**Befund 5 ist der teuerste und war ohne die Aeldari-Arbeit unsichtbar.**
`MortalWoundAllocationSession` parkt bei mehr als einem berechtigten Zielmodell
auf `pending_choice` und wartet — und **nichts** hat je gedrainiert. Gegen ein
EIN-Modell-Ziel landen die Wunden korrekt, weshalb es so lange überlebt hat;
gegen alles andere gar nicht. Träger: Living Lightning, Matter Absorption,
Crimson Harvest, Eater Plague, Kroot Linebreakers, Crushing Strides.
Die drei Methoden stehen jetzt EINMAL in der Basisklasse (dritte Kopie nach
`crushing_impact.py` und `deadly_demise.py`), plus die FNP-Etappe in allen
SECHS `if self._pending is None:`-Wächtern — jeder Subklassen-Wächter lief
sonst am eigenen offenen Session-Wurf vorbei.

### Zwei Suiten waren um Befund 5 herum geschrieben

`test_aeldari_detachment_stratagems.py` prüfte `remaining in (2, 1, 0)`,
`test_skorpekh_lord.py` definierte `inflicted(ctrl)` als `inflicted +
remaining` — beides misst, wie viel **BESTELLT** wurde, nicht wie viel
**LANDETE**, und beide Summen sind identisch, ob die Session auflöst oder
verwaist. Beide messen jetzt die Differenz am Trupp; der Helfer heißt
`wounds_rolled()`, weil das der Name für das ist, was er wirklich zählt.

### Zwei Testsektionen parkten die Uhr auf einem Moment, den es nie gibt

Fehlerklasse 24, Präzedenz Cost of Victory: §4f (Overflight) und §5b (Skyborne)
setzten `turn_at(PHASE_FIGHT)` und riefen `reset_phase()` selbst — genau
deshalb haben beide Fehler überlebt. Beide fahren jetzt **main()s echte
Reihenfolge**: `mover_before` fangen → `advance_phase()` → `reset_phase()` →
Angebot mit der Uhr auf Command.

### Neu: `test_aeldari_stratagem_ui.py` (85 Prüfungen)

Die fehlende UI-Hälfte, eigene Datei (die Regel-Suite ist nach Detachment
geschnitten, dies ist eine Matrix über alle 19 und braucht ab Zeile eins eine
andere Bühne). Der Kern ist die **19×5-Phasenmatrix**: jeder Name genau in den
Phasen seines gedruckten WHEN, also **vier Negative je Stratagem** — die
Prüfung, die „in der falschen Phase" fängt.

Drei Dinge, ohne die die Datei nichts wert wäre, jedes mit eigenem Abschnitt:
- **§0 Liveness** — jeder Render zeigt einen bekannten Nicht-Stratagem-Button.
  Ein Render, der in einen anderen Zweig fällt, zeichnet NULL Buttons und
  besteht jede Abwesenheitsprüfung, indem er nichts misst.
- **§3 das Detachment-Tor am Panel** — Flagge aus, und keiner der 19 erscheint
  in irgendeiner Phase. Das macht §2 nicht-vakuum.
- **§8 die Abwesenheit der 23 Reaktiven** als Mengendifferenz; ein 20. Button
  kann nicht auftauchen, ohne dass diese Zeile sich bewegt.

**Die Bühne wird PRO SPEC neu gebaut.** Einen Stratagem zu kaufen WENDET ihn
an, und mehrere hinterlassen eine Marke auf ihrem Trupp — Abschnitte, die
klicken, vergifteten sonst jeden späteren, der denselben Trupp rendert (zuerst
sichtbar als „der Button ist weg", drei Abschnitte weiter, an einer Stelle, die
mit dem Klick nichts zu tun hatte).

**Zwei Befunde über den TEST, beide von den Sonden:** die Owner-Klausel ist
**pro PHASE**, nicht pro Stratagem (die vier Zwei-Phasen-Stratagems drucken „your
Shooting phase or the Fight phase" — je eines von beiden); und im Gegnerzug
zeichnet das Panel in den meisten Phasen **gar nichts**, weil
`MovementController.select()` die Einheit ablehnt — eine dort gemessene
Abwesenheit misst die Auswahl, nicht das Stratagem. §4 fragt die Owner-Klausel
deshalb bei `can_use()`, wo sie lebt, und pinnt die Panel-Folge daneben.

### Enhancements: alle 28 verdrahtet, 27 davon DORMANT

`test_aeldari_enhancements.py` 496 → **515**. §7 vergibt jede der 28 über
`enhancements.grant()` und misst Aktivierung, Punkte, das Detachment-Tor
(`has()` bleibt wahr, `is_active()` nicht — zwei Fragen, sonst besteht der Test
mit gelöschtem Tor) und 19.04 im SELBEN Frame. **Der Träger wird GESUCHT**
(`spec.can_bear`), nicht transkribiert — eine Tabelle wäre die zweite Kopie.

**§9 die Dormanz, gemessen und benannt:** damals vergab keine ausgelieferte
Liste eines der 28 — „dormant by construction" wie das EPC-Trio vor der dritten
T'au-Liste, und **nicht durch erfundenen Roster-Inhalt behoben** (welche
Enhancements eine Liste kauft, ist die Aussage der Liste). Die zweite,
schwerere Hälfte: die ausgelieferten Listen deklarieren nur einen Teil der acht
Detachments, der Rest ihrer Stratagem-Controller ist im echten Spiel
unerreichbar — Suite und Sonden setzen die Flagge deshalb selbst.

**STAND SEIT DEN ZWEI LISTEN VOM 2026-09-08: 1 von 28 gekauft, 5 von 8
Detachments deklariert, 16 von 28 gehören zu einem gefieldeten Detachment.**
Timeless Strategist ist das erste Aeldari-Enhancement, das eine ausgelieferte
Liste wirklich kauft — und der Abstand zwischen 16 und 1 ist die eigentliche
Aussage: eine Liste kann ein Detachment auf den Tisch stellen und trotzdem
nichts für dessen Enhancements ausgeben. **Und beide Zeilen waren auf
`get("aeldari")` verengt, blieben also GRÜN, während ihre Begründung veraltete**
— dieselbe Form wie Mont'kas [ASSAULT]-Lücke, deren Rechtfertigung ebenfalls
unter einer grünen Zusicherung ablief. Beide sweepen jetzt über JEDE
ausgelieferte Aeldari-Liste und pinnen die Zahl statt der Erzählung; A/B belegt
(Liste entfernt → beide Suiten rot mit den alten Zahlen).

**Nebenbefund:** der AST-Zähler musste sein, weil `army_lists.py`
`enhancements.grant()` in seinem eigenen DOCSTRING erwähnt — ein Teilstring-Zähler
meldet zwei. Vierte Instanz der „Wächter matcht seine eigene Erklärung"-Falle.

### Zwei neue Quell-Wächter (`test_event_chain_wiring.py` 67 → **87**)

- **§10 — was das Phasen-Tor blockiert, muss AUFLÖSBAR sein.** Die Umkehrung
  von §6, die §6 strukturell nicht leisten kann: §6 startet bei „wen FRAGT
  main.py nach `pending_damage_choice`", und Khaine's Vengeance wurde nie
  gefragt. Gelesen wird jetzt der Rumpf von `_has_unresolved_declaration()`
  gegen alle Auflösungs-Aufrufe in `main.py` **und im Panel** (ein reaktiver
  Zug übergibt Confirm/Cancel als CALLBACK, ohne Klammern). Dokumentierte
  Lücke: `secondary_mission_controller`, das über die geteilte
  DecisionManager-Queue blockiert und gar keine eigene Methode hat.
- **§11 — jeder würfelgetriebene Controller wird bestätigt.** Der Wächter, der
  Crushing Strides gefangen hätte: jede in `main()` gebaute Controller-KLASSE
  wird aufgelöst, und wer ein `on_dice_acknowledged` besitzt, braucht den
  AUFRUFAUSDRUCK in `main.py`. Faktions-blind, deckt die nächste Charge gratis.
- **§8 erweitert** um die zwei fehlenden Angebote. **Achtung:** der
  Ordnungs-Anker stand auf `_END_OF_PHASE_OFFERS[0]`, und Overflights Angebot
  liegt DAVOR — er nimmt jetzt das früheste, sonst vergleicht die Prüfung still
  gegen den falschen Aufruf.

### `settings_as` nach `testkit.py` (achtfacher Konsument)

Es stand **byte-gleich in acht** Suiten und wäre hier die neunte geworden. Alle
acht delegieren; die eine abweichende Kopie (ohne `return self`) ist
verhaltensneutral, weil keine Datei die `as`-Form benutzt.

### Getestet

`test_aeldari_stratagem_ui.py` neu **85**, `test_aeldari_detachment_stratagems.py`
995 → **998**, `test_aeldari_enhancements.py` 496 → **515**,
`test_event_chain_wiring.py` 67 → **87**, `test_skorpekh_lord.py` **75**,
`test_necron_abilities.py` **101**. Volle Regression **187 Suiten, ~16516
Prüfungen, 186 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett grün.

**23 A/B-Sonden über drei Dateien, ALLE beißend** — `ab_aeldari_stratagem_ui.py`
(5, greifen den Panel-Pfad an, den keine bestehende Sonde berührt),
`ab_aeldari_offer_windows.py` (10, je Hälfte einzeln UND die ganze Vor-Fix-Welt),
`ab_aeldari_dice_resolution.py` (8).
**Drei Sonden bissen zuerst nicht, alle drei Befunde über den TEST:** die
Reset-Prüfung war von 15.01 maskiert (nach `use()` lehnt der Kauf ohnehin ab —
sie steht jetzt DAVOR); die Crushing-Strides-Ack ist für die Suite unsichtbar,
die den Controller selbst treibt (nur der Wächter sieht sie); und die
FNP-Etappe existiert in **sechs** Kopien, von denen die erste Sondenfassung
fünf zurückdrehte. Dazu eine Sonde, die die neue Suite ABSTÜRZEN ließ statt sie
rot zu machen — `press()` gibt jetzt False zurück statt zu werfen.

### Im ECHTEN Spiel belegt

**`verify_aeldari_stratagem_buttons.py`** — Spion auf `button_style.draw_button`
durch `selfplay.py`s echte `main()`-Schleife, mit allen acht Detachments an,
einer jeden Frame neu gewählten Einheit und einer gestellten Phasenrotation
(gemessen: ein passiver Lauf erreicht Shooting/Fight praktisch nie).

    DRAWN 13/19, off-WHEN sightings: 0
    NOT DRAWN: 6, jedes mit seiner TARGET-Klausel benannt
    --neutralize (Registry erreicht das Panel nicht): 0/19

**Die Phase wird BEIM ZEICHNEN gelesen, nicht aus einem Schnappschuss** — die
erste Fassung meldete 139 Phantom-Verstöße, weil `main()` die Phase mitten im
Frame weiterschalten kann. Und unter 3000 Frames meldet sie INCONCLUSIVE statt
Fehlschlag: Seer's Eye erscheint erst bei Frame 1481, Wind of Blades bei 2041.

**`verify_aeldari_no_deadlock.py`** — der schwerste Befund, mit einem ECHTEN
Klick aufgelöst:

| | gefixt | `--neutralize` |
|---|---|---|
| Brett zeichnet die wählbaren Modelle | 2 Frames | **0** |
| echte Klicks auf eines davon | 1 | **0** |
| Frames blockierend | 5 | **1909** |
| aufgelöst | Frame 605 | **NIE** |
| Phasenwechsel danach | 1 | **0** |

**Drei Harness-Tatsachen mussten dafür gestellt werden, jede mit ihrem Grund:**
das Detachment; der Hazard-Step selbst (ein MockAgent-Lauf erzeugt keinen Fall
Back in 6" von Howling Banshees); und ein STEHENDER Entscheidungs-Prompt muss
abgeschlagen werden, weil `main()`s Kette ihn vor den Würfeln bedient und
selfplay außerhalb des Vorspiels keinen Mensch-Prompt beantwortet — bleibt er
stehen, schluckt er jeden weiteren Klick, und die Sonde meldete 1900 folgenlose
Würfelklicks.

## Werden die T'au-Stratagems überhaupt ANGEBOTEN? (Prüfung, 2026-09-07)

**Auftrag:** dieselbe Prüfung wie für die Aeldari, für die T'au — *„Teste ob alle
Stratagems auch wirklich zum korrekten Zeitpunkt dem Spieler als Button
angeboten werden und ob sie dann auch korrekt funktionieren. Gleiches für
Enhancements."*

**Vier echte Fehler**, und zwei davon sind deutlich größer, als der Auftrag
annahm. Alle vier standen an der Quelle fest, BEVOR eine Zeile Test existierte.

### Die strukturelle Lücke, aus der es folgte — dieselbe wie bei den Aeldari

**Keine Testdatei hat je die ECHTE T'au-Registry an `ActionPanel.draw()`
gereicht.** `test_tau_detachment_stratagems.py` (384 Prüfungen) belegt den
Panel-Mechanismus mit einer **FAKE**-Registry (`ProactiveStratagems([yes, no])`)
und die Verdrahtung per Quell-Grep. Beides hält, während das Panel gar nichts
zeichnet. Und `test_tau_enhancements.py` (1705 Zeilen) importiert **kein**
pygame und instanziiert **keinen** `ShootingController`.

**Der Umfang war größer als angenommen: 15 Zeichnungen, 14 gedruckte Namen, auf
ZWEI Panel-Screens.** 11 über die Registry plus `arrokon_controller` und
`torchstar_controller` (eigene kwargs, sie gehen der Registry voraus) in
`_draw_movement_ui()` — **und The Shortened Blade in `_draw_setup_ui()`**
(`action_panel.py:1365`, während einer Deep-Strike-Ankunft). Die Aeldari-Rig
erreicht diesen zweiten Screen nie; durch sie gemessen wäre das Stratagem in
allen fünf Phasen abwesend, was sich als Fehler liest, wo nur der falsche
Screen gemessen wurde.

### Die vier Fehler

| # | Fehler | Wirkung |
|---|---|---|
| 1 | **VIER Controller** mit `pending_damage_choice`, Klick-Zweig, Highlight und Phasen-Tor fehlten in `_any_pending_damage_choice()` | die KI handelt im selben Frame weiter, in dem der Mensch noch eine Zuteilung schuldet |
| 2 | **ZWÖLF** außerhalb der Bewegungsphase geöffnete `move_mode`s, nur **zwei** vom Phasen-Tor abgewartet | „Next Phase" verwaist einen bezahlten Zug: CP weg, Modelle stehen, wo sie hingezogen wurden |
| 3 | Mont'kas Killing Blow erreicht 10.05s Advance-Tor nicht | **102 von 151** Fernkampfwaffen der `tau_montka`-Liste in den Runden 1-3 abgelehnt |
| 4 | Retro-thrusters' Fall-Back-Hälfte öffnete **nie** einen Zug | die Hälfte hat nie funktioniert, und setzte trotzdem einen `move_mode` |

**F1 — drei Listen, dieselbe Frage, drei Antworten.** `main.py` beantwortet „ist
eine Zuteilung offen?" an drei Stellen: dem Phasen-Tor, der KI-Pause
(`_any_pending_damage_choice()`, ein Frame Aufschub, damit der Render die
Leiche zeigt, bevor die KI weiterhandelt) und dem Deadly-Demise-Starttor. §6 des
Wiring-Wächters prüft, dass alles im ERSTEN klickbar und gezeichnet ist; das
dritte ist als bekannter offener Punkt notiert; **das zweite stand nirgends
geschrieben** und war um vier zu kurz: `ishas_fury`, `grenade_pack`,
`grav_inhibitor` (T'au), `flickerjump`. Gemessen: `_ASKED` = 23, das Tupel = 19.
Die Folge ist kein Deadlock — dafür ist das Phasen-Tor da, und es hatte sie —
sondern die Ein-Frame-Race, für die der Schnappschuss existiert. Kein
Verhaltenstest und kein Smoke kann eine Ein-Frame-Ordnung sehen.

**F2 — der Torchstar Gambit war nur der Anfang.** Ein AST-Sweep über die drei
Erweiterungstüren (`start_post_shooting_move`, `start_battle_focus_move`,
`start_retro_thruster_move`) findet **12 Modi aus 11 Modulen, 0 unauflösbar**.
`_has_unresolved_declaration()` enthielt **gar keinen
`movement_controller`-Term**, und der Next-Phase-Zweig ruft danach
`select(None)` — das `state` löscht, aber **weder `move_mode` noch die
Modellpositionen**. Zwei Besitzer standen zufällig schon im Tor, beide aus einem
ANDEREN Grund (sie halten `active_player`, und ihre Kommentare sagen genau das).

**F3 — die Begründung war veraltet, nicht die Lücke neu.** Beide Kommentare
(`coldstar.py`, `test_event_chain_wiring.py` §7) rechtfertigten den benannten
Gap mit *„No shipped army list fields Mont'ka, so it is dormant"*. Das hörte auf
zu stimmen, als `tau_montka` dazukam — **die Rechtfertigung veraltete, während
die Zusicherung grün blieb**, was die Ausfallart eines BENANNTEN Gaps ist und
die einer Mengendifferenz nicht.

**F4 — ein Kommentar, den kein Code einlöste.** `game/retro_thrusters.py`s
`eligible_moves()` schreibt aus: *„Fall Back is the half that WORKS there, and
is exactly why the ability offers two."* Gemessen in beiden Phasen: im Fight
(wo die Fähigkeit feuert) blieb `state` auf `SELECTED` und kein Zug öffnete,
weil `start_fall_back_move()` über `can_move()` auf die BEWEGUNGSPHASE gegatet
ist — genau der Grund, den der eigene Docstring der Methode vier Absätze weiter
oben für die Normal-Hälfte gibt. **Das ist zugleich, warum F2s Tor-Term ein
`state == MOVING` braucht**: ein `move_mode` ohne offenen Zug ist erreichbar,
und ohne den Term wäre das Tor ein Deadlock statt eines Wächters.

### Die Fixes

- **F1** — die vier ins Tupel. Die Comprehension filtert schon auf
  `.squad.owner != "Player 2"`, ein Name kann die KI also nur über eine
  MENSCHEN-Wahl pausieren; genau dieser Filter macht die Liste
  vervollständigbar.
- **F2** — **EIN** Tor-Term über **eine** benannte Menge,
  `MovementController.OUT_OF_PHASE_MOVE_MODES`. Elf Terme wären elf Chancen,
  den zwölften zu vergessen; `action_panel.py` protokolliert schon, was mit
  einer handgepflegten Modus-Liste passiert („`scout` was missing from it").
  Die Menge ist eine echte OBERMENGE von `REACTIVE_MOVE_MODES` und beantwortet
  eine andere Frage: jene „kann das im GEGNERzug offen sein" (was die KI
  braucht), diese „wurde dieser Zug außerhalb der Bewegungsphase bezahlt".
  **Kein Deadlock möglich:** `action_panel.py:2059` hängt unter
  `state == MOVING` bedingungslos Confirm und Cancel an.
- **F3 — per SQUAD-FLAG, nicht durch Fädeln.** `weapon_has_assault(weapon,
  squad)` bekommt die Einheit schon, das Flag lebt also auf dem Squad und keine
  der elf `_attack_groups()`-Aufrufstellen wird angefasst.
  `Squad.montka_killing_blow` steht neben `star_engines_active` — dieselbe Frage
  ([ASSAULT] fürs 10.05-Tor) eine Fraktion weiter.
  - **Berechnet über `is_active()` → `doctrine_active()`, nicht gegen ein
    Literal `(1,2,3)`**: `enh_exemplars.rounds_for()` WEITET das Fenster auf
    vier Runden für den Träger von *Exemplar of the Mont'ka*. Ein Literal
    löschte das still, und zwar **nur am Advance-Tor** — eine Regel mit zwei
    uneinigen Lesern.
  - **Refresh im Per-Phasen-Block**, aus der LEBENSDAUER begründet:
    Detachment-Flag statisch nach `apply_to_config()`, Fraktions-Keyword eine
    Datenblatt-Referenz, Runde wechselt in `advance_phase()` direkt darüber. Ein
    Per-Frame-Sweep wie Nurgle's Gift wäre reine Mehrarbeit — dort ist der Grund
    GEOMETRIE, hier liest nichts eine Koordinate.
  - `montka.grants_assault(squad)` ist die **erzwungene** Schreibweise: §7
    akzeptiert wörtlich `"%s.grants_assault(squad)"`, ein anderer Parametername
    lässt den Wächter fallen, obwohl die Verdrahtung stimmt.
  - **`Squad.montka_killing_blow` wird NICHT gespeichert** (`activation_state`s
    Ausschlussliste, neben `afflicted`): abgeleiteter Zustand, den der nächste
    Phasenwechsel ohnehin überschreibt — anders als `star_engines_active`, das
    ein bezahlter Grant ist und gespeichert wird.
- **F4** — `_begin_move()` direkt, wie die Normal-Hälfte daneben, plus
  `desperate_escape_this_move = False`. **`fell_back_this_turn` bewusst NICHT**:
  09.07s Folgen (nicht schießen, nicht chargen) sind von dort aus unerreichbar,
  die Fähigkeit feuert nach beidem.

### Neu: `test_tau_stratagem_ui.py` (135 Prüfungen)

Die fehlende UI-Hälfte, eigene Datei — die Regeln-Suite hat in 1702 Zeilen kein
pygame. Kern ist die **15×5-Phasenmatrix**: jeder Name genau in den Phasen
seines gedruckten WHEN, also **vier Negative je Stratagem**.

Drei Dinge, die eine kopierte Aeldari-Suite still nichts hätten messen lassen:
- **ZWEI Render-Formen** (Bewegungs-Screen und Setup-Screen), weil The
  Shortened Blade auf dem anderen liegt.
- **EIN NAME, ZWEI KNÖPFE**: Experimental Ammunition sind zwei Controller mit
  EINEM `Stratagem`-Objekt (15.01 bindet sie). Die Matrix vergleicht NAMEN,
  §6 drückt volle LABELS — nach Namen zu greifen drückte denselben Modus zweimal
  und meldete beide als gekauft.
- **Alle elf Registry-Stratagems lesen `active_player`**, also misst §4 die
  Owner-Klausel bei `can_use()`: im Gegnerzug zeichnet das Panel in den meisten
  Phasen gar nichts, weil `select()` die Einheit ablehnt.

Dazu §0 Liveness (beide Screens einzeln), §3 das Detachment-Tor am PANEL (erst
das macht §2 nicht-vakuum), §5 Regel 15.01 (die Reset-Prüfung **vor** dem Kauf,
sonst maskiert 15.01 sie), §6 der Klick zahlt wirklich (mit `drain()` für die
drei, die eine zweite Frage stellen), §7 Label → Korpus, §8 Mengendifferenz an
`main.py`s AST.

**Gemessener Nebenbefund, gepinnt statt geglättet:** die Arro'kon-Beschriftung
lässt das führende „The" fallen, das ihr eigenes `Stratagem`-Objekt und die
Korpus-Überschrift beide tragen — die zwei Nachbarn behalten ihres. Heute
harmlos, weil `rules_text.stratagem_named()` auf einen eindeutigen SUFFIX
zurückfällt; beide Hälften sind gepinnt, damit ein Rename, der den Rückfall
bricht, hier auffällt statt als leerer Tooltip im Spiel.

**Und die drei vor-Registry-Knöpfe kommen POSITIONELL beim Panel an** — genau
die Gefahr, gegen die die Registry gebaut wurde und für die `action_panel.py`
eine Narbe trägt. §8 pinnt sie deshalb per AST **an ihrem INDEX** gegen
`draw()`s eigene Signatur, nicht an ihrer Erwähnung.

### `test_tau_enhancements.py` 334 → 374

- **§11 durch einen ECHTEN `ShootingController`.** Zwei der neunzehn waren nur
  per Teilstring gepinnt, und ein Teilstring hält, während der Aufruf hinter
  einer nie wahren Bedingung sitzt oder sein Ergebnis verworfen wird. *Precision
  of the Patient Hunter* wird jetzt an `_hit_modifiers()`, am Wundschritt und
  an der `_attack_key()`-SPALTUNG gemessen — die letzte kann ein Teilstring gar
  nicht sehen. **Die entscheidende Zeile vergleicht denselben Träger mit und
  ohne Detachment**: der Vergleich mit einem Squadmate bestünde auch, weil ein
  Fireblade und ein Fire Warrior verschiedene Waffen tragen.
- **§12 Datei gegen Wirklichkeit** — durch den Armeelisten-Rework neu möglich:
  `ArmyList.enhancement_names()` (was die JSON KAUFT) gegen
  `E.granted_names()` (was auf einem Modell LANDET), pro Liste als
  Mengengleichheit. Vorher nur für EINE der vier Listen.
- **§13 die sieben ohne Träger**, und die Menge ist **ABGELEITET** (Registry
  minus §12), nicht abgeschrieben: eine handgeschriebene Namensliste wäre eine
  zweite Kopie und würde beim ersten Kauf veralten. Jede der sieben wird
  zusätzlich per Hand vergeben, um zu zeigen, dass sie **dormant by roster** ist
  und nicht kaputt.

### Zwei neue faction-blinde Wächter (`test_event_chain_wiring.py` 87 → 105)

- **§12** — jeder Controller mit `pending_damage_choice` steht auch in der
  KI-Pause-Menge. Die Umkehrung von §6, die §6 strukturell nicht leisten kann
  (es startet bei „wen FRAGT main.py", eine fehlende Mitgliedschaft ist ihm
  unsichtbar). **Per AST, aus drei benannten Gründen**: die Funktion hat einen
  44-zeiligen Docstring ÜBER Controller (heute zufällig ohne `_controller`-Token
  — Fehlerklasse 24 in Reinform), das Tupel trägt Kommentare ZWISCHEN seinen
  Elementen, und eine Regex über den Rumpf hat keine ehrliche rechte Kante. Der
  AST scheitert außerdem in die SICHERE Richtung: eine kaputte Extraktion gibt
  die leere Menge, die Differenz wird zu ganz `_ASKED`, der Test wird ROT.
- **§13** — jeder außerhalb der Phase geöffnete Zug wird vom Tor abgewartet.
  **Die Controller-Variante wurde gemessen und VERWORFEN**, mit benannten
  Fehlalarmen: 9 von 11 Besitzern lägen am ersten Tag in der Differenz;
  `battle_focus_pool` heißt nicht `*_controller` und könnte sie nie verlassen;
  `retro_thrusters_controller` wäre ein echter Fehlalarm (`ai/agent_driver.py`
  hält sein Zugende über `has_pending_for_opponent_of()`); und vier der elf
  Modul→Variable-Zuordnungen bräuchten eine handgepflegte Tabelle. **Also über
  MOVE-MODES**: Türen per AST aus `MovementController` gelesen, jeder Aufruf in
  `game/*.py` aufgelöst (Literal ODER modulweite Konstante), Mengendifferenz in
  **beide** Richtungen. Drei Wächter über dem Wächter: ein unauflösbarer Aufruf
  ist ein BEFUND, jede `start_*`-Methode ist klassifiziert (Tür oder
  Bewegungsphase), und der Tor-Term wird als `in`-Vergleich per AST geprüft,
  damit eine Erwähnung im Kommentar nicht zählt.
  - **Nebenbei gepinnt:** der Docstring-Vertrag von `start_battle_focus_move()`
    („jeder Modus hier muss auch in `REACTIVE_MOVE_MODES` stehen") — **zweimal
    gemeldet, in denselben Worten**. Er hält heute; diese Zeile macht die dritte
    Meldung unmöglich.

### 26 A/B-Sonden über drei Dateien, ALLE beißend

`ab_montka_assault.py` (5), `ab_tau_wiring_gaps.py` (10),
`ab_tau_stratagem_ui.py` (11).

**Drei Befunde über den TEST, alle von den Sonden:**
1. Die „ganze Vor-Fix-Welt"-Sonde für F3 biss gegen §7 **nicht** — und das ist
   wahr: mit zurückgesetztem Gap-Eintrag ist §7 per DESIGN grün, das ist ja, was
   ein deklarierter Gap bedeutet. Genau deshalb konnte er so lange veralten, und
   genau deshalb brauchte der Fix einen VERHALTENStest: ein Quell-Wächter kann
   „geschlossen" nicht von „entschuldigt" unterscheiden. Die Sonde zielt jetzt
   auf die Verhaltens-Suite.
2. Die Experimental-Ammunition-Sonde biss nicht, weil die Suite ihr Paar SELBST
   baut und `main.py`s Modus-Schleife nie las — §8 zählt jetzt die Modi aus der
   COMPREHENSION per AST (die Registrierung steht einmal in der Quelle und
   passiert zweimal zur Laufzeit, was ein Namenszähler falsch bekommt).
3. Die Sonde „raid_and_run aus `REACTIVE_MOVE_MODES`" traf den falschen Check,
   weil `OUT_OF_PHASE_MOVE_MODES` als Vereinigung MIT jener Menge gebildet wird.
   Eine zweite, isolierte Sonde legt den Modus in die explizite Hälfte zurück,
   sodass nur der Vertrags-Check fallen kann.

### Im ECHTEN Spiel belegt

**`verify_tau_montka_assault.py`** — Spione auf `weapon_has_assault()`,
`available_shooting_types()` und `refresh_killing_blow()` durch `selfplay.py`s
echte `main()`-Schleife:

| | gefixt | `--neutralize` |
|---|---|---|
| Einheiten auf dem Brett | 14 | 14 |
| Fernkampfwaffen | 151 | 151 |
| **am Advance-Tor abgelehnt** | **0** | **102** |
| nach einem Advance ohne Assault-Option | 0 | **3** |

`--neutralize` blendet den Grant NUR im Tor aus (die Adjuster-Kette gewährt
weiter, wie in der echten Vor-Fix-Welt) und reproduziert die Meldung genau.
**Der Verdikt-Test ist NICHT „nichts wird angeboten"**: elf der vierzehn tragen
eine GEDRUCKTE Assault-Waffe und behalten ihre Option ohnehin — was Killing Blow
kauft, sind die anderen 102, und genau deshalb sah die Lücke überlebbar aus.

**`verify_tau_stratagem_buttons.py`** — Spion auf `button_style.draw_button`:
`DRAWN 6/14, off-WHEN sightings: 0`; `--neutralize` (Registry erreicht das Panel
nicht) → kein Registry-Knopf mehr, nur die drei kwarg-Knöpfe.

**Zwei eigene Sondenfehler, beide gemessen statt geraten:**
- Rotation und Phase teilten sich `frames // 40`, koppelten also Einheit *i* an
  Phase *i*%5 — eine Einheit, deren WHEN eine Phase nennt, in der sie nie
  gewählt wird, wäre als „nicht gezeichnet" gemeldet worden. Jetzt teilerfremde
  Perioden.
- Zwei Undrawn hatten zuerst eine ERFUNDENE Begründung. Nachgemessen: ihr Träger
  wird sehr wohl in der Schussphase gewählt, die Vermutung war also falsch. Die
  Sonde MISST die ablehnende Klausel jetzt und druckt sie
  (`measured refusal: ...`); eine `UNREACHED`-Erklärung, die niemand geprüft
  hat, ist eine Geschichte über den Harness.

### Bewusst nicht gebaut, und warum

- **Kein `verify_tau_no_deadlock.py`.** F1s Folge ist eine Ein-Frame-Race, kein
  Deadlock (das Phasen-Tor hatte alle vier) — ein echter Klick kann eine
  Frame-ORDNUNG nicht zeigen. §12 fängt sie an der Quelle, und die A/B-Sonde
  kippt fünf Prüfungen mit allen vier namentlich.
- **Kein KI-Pfad** (stehende T'au-Vorgabe), als Negativraum geprüft.

### Benannte Grenzen

- **`tau_montka` erreicht in `selfplay.py` keinen einzigen Phasenwechsel** (0 in
  4000 Frames, wo die Default-Armeen 7 in 3000 schaffen). **A/B belegt, dass es
  nicht an F2s Tor-Term liegt** — mit entferntem Term stallt es identisch. Die
  Sonden lesen das Brett deshalb über `MovementController.__init__` statt über
  den Per-Phasen-Stamp und melden getrennt, ob der Stamp von `main()` kam. Eine
  eigene Messreihe wert, hier nur benannt.
- **Der Armeelisten-Rework** (Listen als JSON in `armies/`) lief während dieser
  Arbeit in einer PARALLELEN Sitzung. Alle Messungen wurden danach
  nachgemessen und sind unverändert (dieselben 8 Listen, dieselben 12 vergebenen
  Enhancements, dieselben 151/102). Ein zwischenzeitlicher Fehlschlag in
  `test_tau_enhancements.py` §9b (Coldstar-Drohnen) gehörte deren
  Datenblatt-Arbeit — Fehlerklasse 20, vor der Ursachensuche per mtime geprüft.

### Und daraus DREI Wächter, damit es kein Merkzettel bleibt

Auf Nachfrage („zieh die Lehren für zukünftige Datenblätter") sind die drei
Formen, die sich über beide Audits WIEDERHOLT haben, jetzt faction-blinde
Mengendifferenzen statt Prosa. Alle drei sind heute GRÜN und nicht vakuum-grün
— jede hat ihre Liveness-Zeile und eine beißende A/B-Sonde:

- **§14 — jeder Controller, der `panel_label()` definiert, erreicht das Panel**
  (Registry oder eigenes Argument). Gemessen: 31 Module fragen nach einem Knopf,
  0 unerreichbar. **Alias-fest**, weil `targeting_array.py` seine Klasse unter
  einem anderen Namen importiert — ein Namensvergleich hätte sie als
  unerreichbar gemeldet.
- **§15 — kein `offer_at_end_*` entscheidet aus der LIVE-UHR.** Das ist die
  Form von SECHS Fehlern über zwei Fraktionen (Wall of Mirrors, Cost of
  Victory, Webway Tunnel, Elemental Ensnarement, Skyborne Sanctuary,
  Overflight). Gemessen: 14 solche Controller, 0 Verstöße.
  **Nur `offer_at_end_*`, und das ist der Kern:** ein START-of-phase-Angebot
  liest die Uhr RICHTIG, weil sie gerade zu dieser Phase geworden ist — von 24
  Controllern mit irgendeinem `offer_at_*` tut genau einer das
  (`grot_orderly.py`), und ein breiterer Sweep hätte ihn falsch gemeldet.
- **§16 — jedes registrierte Enhancement wird von irgendeiner Regel gelesen.**
  Die Enhancement-Fassung von „gebaut, nie gefüttert": eine Registry-Zeile gibt
  Punkte, Träger-Bedingung und ein `UnitProfile`-Feld, und jedes davon ist
  einzeln testbar, während NICHTS das Feld liest. 47 geprüft, 0 ungelesen.

Dazu ein verdichtetes **Rezept in Teil 1** (`## Rezept: eine neue Fähigkeit,
ein Stratagem, ein Enhancement anlegen`), das die Nähte aufzählt und bei jeder
sagt, welcher Wächter sie hält — und welche drei Dinge weiterhin Kopfarbeit
bleiben (ein NEUES Keyword mit eigenem Eignungs-Tor, die zweite Hälfte einer
Regel in einem anderen Trichter, und ob eine Liste die Sache überhaupt fieldet).

**Ein Befund über die SONDE dabei, der die Lehre selbst illustriert:** die
§15-Sonde setzte zuerst `PHASE_FIGHT` als Vor-Fix-Welt ein — ein in dem Modul
gar nicht importierter Name. Sie biss, aber gegen §1b (freie Namen), nicht
gegen §15. Eine Sonde kann aus dem FALSCHEN Grund beißen, und das ist genauso
wertlos wie eine, die gar nicht beißt; ein String-Literal isoliert sie.

**Getestet:** neu `test_tau_stratagem_ui.py` (**135**),
`test_tau_enhancements.py` 334 → **374**, `test_tau_doctrines.py` 74 → **95**,
`test_event_chain_wiring.py` 87 → **113**. **29 A/B-Sonden über drei Dateien,
alle beißend.** Volle Regression **189 Suiten, ~16771 Prüfungen, 188 grün /
0 rot / 1 bekannt**, `run_tests.py --smoke` komplett grün (alle neun schweren
Skripte).
