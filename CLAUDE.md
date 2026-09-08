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
- **Was fertig ist, wird GEPUSHT** (User-Vorgabe): jede Sitzung, in der etwas fertig geworden ist,
  endet mit `git add -A && git commit && git push`. **Das Repo hat keine Entwicklungsfunktion — es
  ist ein reines BACKUP**, falls lokal etwas kaputtgeht; getestet wird ausschließlich lokal.
  Daraus folgt, was hier NICHT gilt: keine Feature-Branches, keine PRs, kein Review-Gate vor dem
  Push. Ein Commit muss nichts "Vorzeigbares" sein — **ungepusht ist ungesichert**, und das ist der
  einzige Maßstab; ein Zwischenstand gehört also eher hinein als draußen gelassen. **`-A` ist
  Absicht, nicht Bequemlichkeit:** ein Backup, das nur die eigenen Dateien der Sitzung mitnimmt,
  sichert genau das nicht, was daneben liegt — inklusive der Arbeit einer PARALLELEN Sitzung
  (Fehlerklasse 20), die dieses Repo regelmäßig sieht. Das ist gewollt und kein Versehen.

## Rezept: eine neue Fähigkeit, ein Stratagem, ein Enhancement anlegen

**Destillat aus vier Prüfungen** (Elf Meldungen, Aeldari-Audit, T'au-Audit) und
der Grund, warum es dieses Rezept gibt: **alle vierzehn dort gefundenen Fehler
hatten DIESELBE Form.** Die Regel war richtig, der Controller war richtig, der
Unit-Test war grün — und der Knopf war nie auf dem Schirm, der Prompt nie
auflösbar, der Grant nie am Tor. Eine Regel zu BAUEN ist in diesem Repo der
kleinere Teil; sie ANZUBIETEN ist der, an dem es viermal gescheitert ist.

Die meisten Punkte hier sind inzwischen WÄCHTER, kein Merkzettel — genau nach
Fehlerklasse 4 („eine Regel, die nur im Prompt steht, bleibt optional").
Was ein Wächter fängt, steht mit seiner Nummer dabei; der Rest ist das, was
noch von Hand geprüft werden muss.

### 1. Die Regel bauen (unverändert)

Wie im Datenblatt-Rezept: gedruckten Text aus `rules/<fraktion>/*.md` nehmen,
bei „gleicher Name, andere Zahlen" eine eigene Klasse, eine bloße Paraphrase
NICHT implementieren sondern in `abilities_text` als fehlend markieren und im
Test assertieren. Neu angelegte Datenblätter bekommen ihre `.md` per `--only`
in derselben Sitzung.

### 2. WIRD ES ANGEBOTEN? — die Hälfte, an der es viermal scheiterte

**Ein Panel-Knopf** → Controller bekommt `can_use`/`use`/`panel_label` und wird
in `main.py` auf `proactive_stratagems` registriert. Das Panel braucht KEINE
Änderung; ein neuer Parameter dort ist Fehlerklasse 22 und wird nicht gebraucht.
→ **§14** fängt einen Controller, der `panel_label()` definiert und weder auf
der Registry noch als Panel-Argument ankommt.

**Ein Angebot an einer PHASENGRENZE** → `game/phase_window.py`, niemals ein
Live-Test auf `turn_tracker.phase` in `can_use()`. Die Uhr steht dort schon auf
der NÄCHSTEN Phase, und wenn ein Mensch antwortet, noch weiter.
→ **§15** fängt jedes `offer_at_end_*`, dessen `can_use()` die Uhr liest. Sechs
Fehler dieser Form über zwei Fraktionen.
**Ausnahme, die kein Fehler ist:** ein START-of-phase-Angebot liest die Uhr
RICHTIG — sie ist gerade zu dieser Phase geworden (`grot_orderly.py`).

**Ein Angebot NACH `advance_phase()`** bekommt `mover_before`, nie
`turn_tracker.turn_owner` — der ist an dieser Naht schon geflippt.
→ **§8**.

### 3. WIRKT ES? — die vier Nähte, an denen ein Grant hängenbleibt

**Ein KEYWORD-Grant wird an ZWEI Orten gelesen**: der Adjuster-Kette (die
Schadensmathematik, leicht zu testen, und was jeder Unit-Test prüft) UND einem
EIGNUNGS-Tor, das der Kette nicht ähnlich sieht. Wer nur die Kette verdrahtet,
bekommt eine grüne Suite und eine Fähigkeit, die genau das nicht tut, wofür sie
gekauft wird. Vier von fünf [ASSAULT]-Grants standen so da — und der EINZIGE
[PISTOL]-Grant ebenso — obwohl die Warnung dafür seit dem Sudden-Storm-Fix
wörtlich in `weapon_has_assault()`s Docstring steht: sie galt nur nicht fürs
Nachbar-Keyword, und die zwei Zeilen standen NEBENEINANDER in derselben Funktion.
→ **§7** für [ASSAULT], **§19** für [PISTOL]. Beide sind dieselbe
MENGENDIFFERENZ: wer das Keyword zur Laufzeit vergibt, muss im RUMPF des Tors
genannt sein. Ein DRITTES Keyword mit eigenem Eignungs-Tor kostet einen
weiteren solchen Abschnitt — die Frage von Hand lautet *wer liest dieses
Keyword ausser der Kette?*, und die Antwort ist fast nie „niemand".

**Braucht die Bedingung etwas, das der Leser nicht bekommt** (eine Runde, einen
`turn_tracker`)? Dann ein **SQUAD-FLAG**, einmal pro Phase gestempelt — nicht
das Argument durch elf Aufrufstellen fädeln. Muster:
`Squad.montka_killing_blow` / `Squad.star_engines_active` / `afflicted`.
Das Flag **aus derselben Funktion berechnen, die die Kette liest** (nie gegen
ein Literal), sonst haben eine Regel zwei uneinige Leser. Und: ein abgeleitetes
Flag gehört in `activation_state.SQUAD_FLAGS_EXCLUDED`, ein bezahlter Grant in
`SQUAD_FLAGS`.

**Würfel** → `on_dice_acknowledged` muss aus `main.py` gerufen werden.
→ **§11**.

**Schadenszuteilung** → `pending_damage_choice` braucht DREI Dinge: einen
Klick-Zweig, ein `draw_damage_choice_highlight()` und einen Eintrag in der
KI-Pause `_any_pending_damage_choice()`.
→ **§6** (klickbar + gezeichnet), **§12** (KI-Pause).
**Und wer eine `MortalWoundAllocationSession` ÖFFNET, muss sie LEEREN können**
(`pending_damage_choice` + `choose_damage_model` + die FNP-Etappe VOR dem
`_pending is None`-Early-return) — sonst parkt sie gegen jedes Mehr-Modell-Ziel
für immer und die Wunden landen nie. → **§17**, das als einziges beim MODUL
startet statt bei `main.py`, weil §6/§10/§12 einen nie gefragten Controller
nicht sehen können. **§17b** prüft dazu, dass ihr `log=` ein CALLABLE ist: das
GameLog-Objekt kracht, sobald eine Wunde auf einem Ein-Modell-Ziel landet.
**§17d ist der Spiegel** — eine Klasse, die dieses Callable speichert, darf es
nicht als Objekt behandeln (`self.log.add(...)`). Genau daran ist das Feuern
der D-cannon abgestürzt; siehe `## Diagnose-Logging` für die zwei Konventionen.

**Ein Zug außerhalb der Bewegungsphase** → der Modus gehört in
`MovementController.OUT_OF_PHASE_MOVE_MODES`, und ein REAKTIVER zusätzlich in
`REACTIVE_MOVE_MODES`.
→ **§13**, beide Richtungen.

**Blockiert es den Phasenwechsel?** Dann muss es auflösbar sein — sonst ist es
kein Wächter, sondern ein Deadlock.
→ **§10**.

**Ein Enhancement** → das `UnitProfile`-Feld muss von irgendeiner Regel gelesen
werden.
→ **§16**.

### 4. Was der Test können muss

**Ein Panel-Knopf ist erst belegt, wenn das ECHTE Panel ihn gezeichnet hat.**
`"proactive_stratagems.add(X(" in main_src` und ein direkter `can_use()`-Aufruf
halten beide perfekt, während das Panel gar nichts zeichnet — das war die
strukturelle Lücke in BEIDEN Audits. Vorlagen:
`test_aeldari_stratagem_ui.py`, `test_tau_stratagem_ui.py`.
Die Matrix rendert jede Phase, nicht nur die richtige: **vier Negative je
Stratagem**, sonst ist „korrekt angeboten" nicht von „immer angeboten" zu
unterscheiden.

Drei Dinge, ohne die so eine Suite nichts misst und trotzdem grün ist:
- **§0 Liveness** — ein Render, der in einen anderen `_draw_dispatch`-Zweig
  fällt, zeichnet NULL Knöpfe und erfüllt jede Abwesenheitsprüfung.
- **Das Detachment-Tor am PANEL** — sonst beweist die Matrix nur, dass Knöpfe
  erscheinen, nicht dass sie WEGEN des Detachments erscheinen.
- **Die Bühne pro Abschnitt neu bauen** — ein Kauf WENDET das Stratagem an und
  vergiftet jeden späteren Abschnitt, der dieselbe Einheit rendert.

**Und der Klick muss WIRKLICH zahlen.** Mehrere Stratagems stellen nach dem
Knopf eine zweite Frage und zahlen erst danach; ein Test, der beim Klick
aufhört, meldet sie als „gekauft und tat nichts" — ununterscheidbar von einem
der gemeldeten Fehler. Dafür ist `drain()` da.

**Reihenfolge-Falle:** eine 15.01-Reset-Prüfung gehört VOR den Kauf, sonst
maskiert 15.01 sie.

### 5. Was danach noch von Hand zu prüfen ist

Die Wächter decken die vierzehn gefundenen Formen ab. Nicht abgedeckt und
deshalb weiterhin Kopfarbeit:

- **Ein neues Keyword mit einem eigenen Eignungs-Tor** (§7 deckt [ASSAULT] ab,
  §19 [PISTOL] — ein drittes braucht seinen eigenen Abschnitt).
- **Die zweite Hälfte einer Regel**, die ein anderer Trichter liest — „ein
  KEYWORD-Grant wird regelmäßig an zwei ganz verschiedenen Orten gelesen".
- **Ob eine Liste die Fähigkeit überhaupt fieldet.** Eine Regel kann
  vollständig verdrahtet und trotzdem unerreichbar sein — die 28 Aeldari- und
  7 T'au-Enhancements sind das, und das ist eine Aussage über den ROSTER, die
  man BENENNT statt sie durch erfundenen Listeninhalt zu „beheben".

### 6. Die Sonden-Doktrin, kurz

Jeder Fund wird REPRODUZIERT, dann gefixt, dann per A/B-Sonde an der QUELLE
belegt. **Eine Sonde, die nicht beißt, ist ein Befund über den TEST** — und im
T'au-Audit waren drei von 26 genau das. Zwei weitere Fallen, beide dort
bezahlt:
- Eine Sonde kann aus dem FALSCHEN Grund beißen. Die §15-Sonde setzte zuerst
  `PHASE_FIGHT` ein, ein in dem Modul nicht importierter Name — sie kippte §1b
  (freie Namen) statt §15. Ein String-Literal isoliert sie.
- Eine Sonde muss ROT machen, nicht ABSTÜRZEN. Siebzehnmal in diesem Repo
  passiert; `find()` statt `.index()`, `.get()` statt `[...]`.

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
    Objective stehen", seit dem 2026-09-08 von ZWEI Garnisons-Pässen gelesen (der
    Over-Garrison-Korrektur und ihrem planner-seitigen Bericht ist
    `_garrison_surplus()` gemeinsam geworden; der dritte ist der Lone-Swap-Pass) —, und für den
    Auswahl-Screen zwei kleine: `sprites.models_portrait_paths()` und
    `loadout.model_loadout_lines()` — beide beantworten dieselbe Frage eine Ebene tiefer, für eine
    MODELLMENGE statt für ein Squad, weil eine Kachel die Komponenten einer Attached Unit einzeln
    zeigt. **Achtung bei der ersten:** `portrait_paths()` sortiert bewusst den CHARAKTER nach vorn,
    `models_portrait_paths()` nach Zeilenhäufigkeit — die gemeinsame Hälfte ist nur der
    Dedupe-Teil, und die beiden Ordnungen zusammenzuziehen hätte die dokumentierte
    Charakter-zuerst-Regel still gelöscht.
    Seither **`game/ui/rules_body.py` (27.)** — „wie werden gedruckte Regeln gesetzt", vom
    Army-Rules-Leser und vom Stratagem-Tooltip gelesen; der Leser behält Panel, Scrollen und
    Blockbau und re-exportiert die Farb-/Abstandskonstanten, damit jeder Pixel-Test per
    Konstruktion unverändert bleibt.
    Seither **`game/unit_pick.py` (28.)** — „wird diese Entscheidung auf dem BRETT beantwortet",
    gelesen von main.pys Klick-Zweig, dem linken Panel, dem Brett-Highlight und dem
    Decision-Overlay; und die erste Extraktion, die einen Mechanismus verallgemeinert, den das
    Repo für GENAU EINE Fähigkeit ausgeliefert hatte (siehe `## Einheiten auf dem Brett wählen`).
    Seither **`game/ui/faction_badge.py` (29.)** — „wie sieht eine Fraktionskachel aus", gelesen
    vom Game-Status-Panel und vom Zug-Banner. Das Panel RE-EXPORTIERT jede Konstante und
    delegiert seine eigene Methode, seine Pixel-Tests sind also per Konstruktion unverändert.
    **Die Kachel-RECT ist die des Aufrufers, nicht eine Größe** — die 58 px des Panels sind für
    eine 200-px-Spalte bemessen, ein Banner in der Bildschirmmitte hat diese Schranke nicht.
    Seither **`game/per_unit_offer.py` (32.)** — „biete diese Wahl JEDER berechtigten
    Einheit an, eine nach der anderen“, gelesen von Airborne Agility, Ride the Wind und
    Cloudstrider; siehe `## Zwei Meldungen aus einer Partie`.
    Seither **`game/unit_choice_offer.py` (33.)** — „der Spieler waehlt EINE der berechtigten
    Einheiten", also EIN Prompt mit einer GETAGGTEN Option je Kandidat; gelesen von Cost of
    Victory, Webway Tunnel, Skyborne Sanctuary und Overflight. **Nicht zu verwechseln mit
    `per_unit_offer` eine Zeile darueber** — das ist „JEDE Einheit bekommt ihr eigenes Angebot",
    und der FALSCHE Code fuer beide sieht gleich aus (alle vier hatten ihn). Siehe
    `## "TARGET: One <X> unit from your army" wurde NICHT gewaehlt`.
    Seither **`geometry.convex_hull()` / `point_inside_hull()` (34.)** — „stehen diese Modelle
    UM diesen Punkt herum", gelesen vom Objective-Umriss des Renderers und von
    `_validate_turn_plan()`s Prüfung, ob ein Plan eine Einheit auf ihre eigene Mitte befiehlt.
    Es liegt in `game/geometry.py`, weil `ai/` den Renderer nicht importieren kann (pygame,
    Renderpfad); der Renderer RE-EXPORTIERT es unter dem alten privaten Namen `_convex_hull`,
    also bewegt sich kein Pixel-Test. Siehe
    `## Der Avatar-Charge und der Home-Objective-Klumpen`.
    Seither **`agent_driver._garrison_surplus()` (35.)** — „welche der auf einem Objective
    geparkten Einheiten werden gebraucht, welche sind übrig", gelesen von der
    Over-Garrison-Korrektur UND ihrem Bericht an den Planner, die dieselben sechs Zeilen doppelt
    hatten. Sie wären in dem Moment gedriftet, in dem eine der beiden Seiten von Bedrohungen
    erfahren hätte — was genau die Änderung war, die sie zusammengelegt hat.
    Seither **`game/mortal_wound_sessions.py` (32.)** — „wie leert man eine LISTE
    offener Mortal-Wound-Sessions", gelesen von `drakolithe.py` und
    `harvester_of_souls.py`, den einzigen zwei mit dieser Form. Dort ist die
    REIHENFOLGE Teil der Antwort: die erste geparkte Session in
    Einfüge-Reihenfolge wird angeboten UND beantwortet, sonst teilen zwei
    Replays einer Schlacht dieselben Wunden verschieden zu.
    **Die VIERTE Ausprägung von Fehlerklasse 10, und sie ist die teuerste
    Variante von „eine Stelle antwortet gar nicht":** ein Wächter, der bei
    `main.py` STARTET, kann einen Controller nicht sehen, den `main.py` gar
    nichts fragt. §6/§10/§11/§12 tun genau das, und alle vier waren blind für
    vier Module, die eine Zuteilung ÖFFNETEN und nie leeren konnten. Der
    Gegenwächter muss beim MODUL starten (§17) — dieselbe Umkehrung wie
    §6-gegen-§10, eine Schicht weiter außen.
    Seither **`weapons.anti_entries()` (31.)** — „wie liest man `WeaponProfile.anti`", gelesen von
    `shooting._wound_crit_threshold()` und von `weapons.printed_keywords()`; es liegt jetzt bei
    dem Feld, das es liest, und `shooting.py` re-exportiert es unter dem alten privaten Namen,
    also bewegt sich keine Aufrufstelle (siehe `## Die Waffentabelle druckte auch die KEYWORDS
    nicht`).
    **Die teuerste Ausprägung ist NICHT "zwei Antworten", sondern "eine Stelle antwortet gar
    nicht".** Ein KEYWORD-Grant wird in dieser Engine regelmäßig an zwei ganz verschiedenen Orten
    gelesen: in der Adjuster-Kette (die Schadens-Mathematik — leicht zu verdrahten, leicht zu
    testen, und das, was jeder Unit-Test prüft) UND an einem EIGNUNGS-Tor, das der Kette gar nicht
    ähnlich sieht. Wer nur die Kette verdrahtet, bekommt eine grüne Suite und eine Fähigkeit, die
    genau das eine nicht tut, wofür sie gekauft wird. Drei von vier [ASSAULT]-Grants standen so da
    (siehe `## Regelengine — Schießen`), **und der einzige [PISTOL]-Grant genauso** — obwohl die
    Warnung dafür seither wörtlich in `weapon_has_assault()`s Docstring stand; sie galt nur nicht
    fürs Nachbar-Keyword, und die zwei Zeilen standen NEBENEINANDER in derselben Funktion (siehe
    `## Blades of Asuryan`). **Ein Verhaltenstest kann den nächsten Fall nicht sehen,
    weil es ihn noch nicht gibt** — dagegen hilft nur eine MENGENDIFFERENZ an der Quelle: wer den
    Effekt vergibt, muss bei jedem Leser genannt sein (`test_event_chain_wiring.py` Abschnitt 7
    für [ASSAULT], Abschnitt 19 für [PISTOL]).
    Und eine bekannte, bewusst offene Lücke gehört NAMENTLICH in denselben Wächter, sonst
    verschwindet sie still.
    **Die dritte Ausprägung: EIN Vertrag, ZWEI Lesarten, beide ausgeliefert.** Das Vorspiel-Protokoll
    `step.start(controller, on_done)` wurde in einem Modul als "on_done UND False ist verboten"
    ausgeschrieben und in einem Test als genau dieses Paar GEPINNT — vier ausgelieferte Schritte
    folgten der zweiten Lesart, und jeder ließ seinen Treiber die Sequenz zweimal laufen (bis hin zu
    einem dreifachen Schlachtstart, siehe `## Vorspiel`). Ein Vertrag, den nur ein Kommentar hält,
    ist keiner: wo zwei Lesarten möglich sind, muss der TREIBER beide richtig machen
    (`pregame.Resume`), nicht jeder künftige Schritt-Autor die eine erraten.
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
    **Und `main.py` war daran nie das Besondere — der Zweig ist es.** Zweite Meldung derselben
    Form aus einer ganz anderen Datei: `NameError: name 'rect' is not defined` aus
    `Renderer.draw_objectives()`, ausgelöst NUR, solange der Cursor auf dem Info-Icon eines
    Objectives steht (User: "beim hovern über das objective info icon"). Der Umbau auf gedrehte
    Umrisse hatte das Local zu `outline_rect` umbenannt und zwei Lesestellen im Hover-Zweig
    stehenlassen. Deshalb ist der Freie-Namen-Sweep jetzt **`test_event_chain_wiring.py`
    Abschnitt 1b** und läuft über JEDES Modul in `game/` und `ai/` (456 Dateien, ~1 s, 0
    Fehlalarme). **Dafür musste der Modulnamen-Sammler strenger werden:** die alte Fassung lief
    per `ast.walk()` in Funktionsrümpfe hinein, ein Local EINER Funktion galt also als „definiert"
    für jede andere derselben Datei — und `rect` ist ein Local von `_render_static_layer()`, der
    Sweep wäre also genau an diesem Fehler vorbeigelaufen. Gemessen: die permissive Fassung
    verzieh in `main.py` 441 zusätzliche Namen. A/B belegt (Meldung wiederhergestellt → beide
    Zeilen namentlich rot).

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
    **NEUE, schlimmere Form: ein `git add -A` der einen Sitzung kann den
    TRANSIENTEN Zustand eines A/B-Sondenlaufs der anderen einfangen.** So ist
    `if False: return False` an die Stelle des gedruckten TARGET-Ledgers von
    Hungry Void in Commit `412dc4a` geraten — eine Sonde hatte die Datei für
    zwei Sekunden neutralisiert. Die `-A`-Regel bleibt (sie ist Absicht), aber:
    **ein Sondenlauf und ein Commit dürfen sich nicht überlappen**, und nach
    einem Commit, der neben einem Sondenlauf lag, ist `git grep "if False:"`
    über HEAD die billige Gegenprobe.
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
25. **"Gebaut, aber nie GEFÜTTERT" hat eine Variante, die schlimmer ist: gebaut, BLOCKIERT AUF,
    nie anklickbar.** Die Klasse ist hier mehrfach dokumentiert (`VengefulStarsController`,
    Path of the Outcasts Würfelbestätigung, Lethal Ichor und Spore-laced Shock Waves'
    Fütterung, `move_exceptions.clear_turn_flags()`, `overflight_controller`, Sudden Storms
    Advance-Reroll) und jedes Mal war die Folge ein stiller No-op. Gemeldet als **"die ki hat
    nach der schussphase in ihrem zug 2 einfach aufgehört zu agieren"** ist sie zum ersten Mal
    ein echter DEADLOCK.
    - **Die Form:** ein Controller mit `pending_damage_choice` stand in BEIDEN Toren von
      `main()` — `_has_unresolved_declaration()` (die Phase kann nicht weiter) und
      `_any_pending_damage_choice()` (`run_ai_action()` wird übersprungen) — und hatte in der
      ~48-Zweige-Kette **gar keinen Klick-Zweig**. Nichts konnte je die Wahl auflösen, auf die
      beide Tore warteten. Drei Controller gleichzeitig betroffen (`lethal_ichor`,
      `spore_laced`, `sickening_impact`), alle drei Death Guard — deshalb überlebte es bis zur
      ersten Partie gegen diese Fraktion.
    - **Warum kein Test es sah:** ein Unit-Test treibt den Controller DIREKT und ist grün; die
      Smokes und `selfplay.py` erreichen die Fähigkeit nie (MockAgent kommt selten in eine
      Schussphase — die dokumentierte Grenze). Nur die QUELLE kann die Frage beantworten.
    - **Der Wächter ist eine MENGENDIFFERENZ, kein Namenszähler** (`test_event_chain_wiring.py`
      Abschnitt 6): jeder Controller, den `main.py` nach `pending_damage_choice` FRAGT, muss
      auch einen `choose_damage_model(...)`-Zweig UND ein `draw_damage_choice_highlight(...)`
      haben. A/B belegt (Vor-Fix-Welt: 8 von 40 Prüfungen fallen, die erste nennt alle drei
      Controller namentlich). Ein achter Controller kann nicht dazukommen, ohne dass diese
      Zeile sich bewegt.
    - **Die ZWEITE Hälfte gehört dazu:** vier Controller wurden zwar blockiert, aber nie
      GEZEICHNET (`internal_grenade_racks` zusätzlich zu den drei) — die Wahl stand offen, die
      KI wartete, und das Brett zeigte nicht, welche Modelle wählbar sind. Ein auflösbarer, aber
      unsichtbarer Prompt ist derselbe Hänger mit besserem Ausgang.

## Diagnose-Logging

Wiederholt war der eigentliche Defekt nicht der Fehler, sondern dass er im Log unsichtbar war — die
Untersuchung musste dann aus rohen Koordinaten rekonstruiert werden. Vorhandene `file_only`-Zeilen:
`[move detail]`, `[move choice]` (gewählter Optionstyp + Zielpunkt + Plan-Koordinate), `[charge]`
(Ziel, Wurf, erreichte Kantendistanz, Engagement — auch bei Ablehnung mit den Odds), `[coherency]`
(welche Modelle, wie weit daneben, an jeder Phasengrenze, entprellt), `[threat]`, `[turn plan]`
(inkl. `@(x,y)`), `[ingress]` (der TATSÄCHLICHE Landeplatz), `[regroup]`, `[pile in]` (vorher ->
nachher engagierte Modelle), `[deploy]`, `[charge reroll]`, `[disembark]`.

**ZWEI Konventionen, unterschieden allein am FELDNAMEN — und das ist die einzige Trennung, die es
gibt:** `self.game_log` ist das GameLog-OBJEKT und wird `self.game_log.add(msg)` geschrieben (~90
Controller); `self.log` ist ein CALLABLE und wird `self.log(msg)` geschrieben (vier Module:
`damage_resolution`, `dice_notation`, `feel_no_pain`, `hazard`). Wer die eine Schreibweise gegen
das andere Feld setzt, baut keinen Tippfehler, sondern einen Absturz — und zwar einen, der erst
feuert, wenn die Zeile das erste Mal wirklich LÄUFT. `test_event_chain_wiring.py` §17b/§17d hält
beide Richtungen. Einzige Ausnahme:
`strategic_reserves.withdraw_to_reserves(log=...)`, dessen Parameter `log` wirklich das OBJEKT ist
(alle neun Aufrufer reichen `log=self.game_log`).

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
  `measure_ard_as_nails.py`, `measure_stim_injectors_gate.py`, `measure_advance_usage.py`,
  `measure_fly_penalty.py` (kostet oder bringt 21.03 einer gemischten Einheit Boden — baut das
  Brett aus den Koordinaten EINES Logs nach, statt eine Einheit isoliert hinzustellen),
  `measure_home_garrison.py` (wer hält das Home Objective — beide Phasen der Entscheidung,
  Aufstellung und Turn-Plan, letzterer gegen das Brett des gemeldeten Logs; `--neutralize`).
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
- **`fetch_datasheet_rules.py` / `rules/*.md`** — der GEDRUCKTE Regeltext jedes Datenblatts als
  markdown, damit ein GW-Update per `git diff` sichtbar wird statt durch erneutes Lesen bei
  Wahapedia. Ausführlich unter `## Regeltext-Korpus` weiter unten;
  **`verify_rules_vs_engine.py`** stellt Korpus und Engine nebeneinander (ein BERICHT, keine Suite —
  die transkribierten Werte gewinnen per stehender Entscheidung). Es vergleicht Statlines, Basen,
  Rettungswürfe, Punkte **und seit dem Schadenswert-Bericht jede WAFFE** (Range/A/BS oder WS/S/AP/D,
  3732 Werte). Die Waffen-Hälfte ist zusätzlich als SUITE einklagbar — `test_weapon_characteristics.py`,
  siehe `## Die Waffentabelle druckte den PLATZHALTER` —, weil es für Waffenwerte anders als für
  Punkte und Basen keine stehende Abweichungs-Entscheidung gibt: dort sind es null Differenzen.
  **Seit dem Keyword-Bericht gilt dasselbe für die `Keywords`-SPALTE** (627 Waffen, Abschnitt 5
  derselben Suite): sie lag seit dem Bau des Korpus da und hatte keinen einzigen Leser, und der
  erste Vergleich fand fünf echte Engine-Fehler — siehe `## Die Waffentabelle druckte auch die
  KEYWORDS nicht`.
- **`game/scene_io.py` / F9 / `--load`** — Szenen-Snapshot. Positionen, Restwunden UND WELCHES
  Modell (siehe `_match_models()`), Reserve/Transport, Rundenstand, CP, Missionsstand und wer schon
  gehandelt hat (`game/activation_state.py`); NICHT Terrain/Armeen (die kommen aus Kartenschlüssel
  und Szene) und nie eine halbfertige Aktivierung. Ersetzt die
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
- **Eine Radrastung ist ZWEI Events.** pygame liefert aus 1.x-Kompatibilität neben `MOUSEWHEEL`
  zusätzlich ein `MOUSEBUTTONDOWN` mit **Button 4 (hoch) / 5 (runter)**. Wer auf „irgendein
  MOUSEBUTTONDOWN" reagiert, reagiert also auch auf jedes Scrollen — genau so schloss der
  Army-Rules-Leser beim Scrollen. **Ein Test mit einem NACKTEN `MOUSEWHEEL` kann das nicht sehen**
  (58 grüne Prüfungen taten es nicht); wer ein Scroll-Verhalten prüft, muss das PAAR schicken.
  Jeder dismiss-on-click gehört auf `event.button == 1` gegated, wie es jeder andere Screen des
  Repos tut.
- **`selfplay.py` ERSETZT `pygame.event.get` beim Import** (nicht: ergänzt es). Eine Sonde, die
  den Pump vor `runpy.run_module("selfplay")` umhängt, wird stillschweigend überschrieben und
  meldet wahrheitsgetreu aussehende Nullen — sie muss sich in einem Frame-Hook einklinken, wenn
  selfplays Pump schon steht. Und sie sollte die Events der gemessenen Frames ERSETZEN statt sie
  zu ergänzen: selfplay klickt pro Frame selbst mit Button 1 aufs Brett, was ein Overlay schließt,
  das man gerade misst.
- **Ein Smoke, der `main.main()` treibt, MUSS `config.MAP_SELECT`/`ARMY_SELECT` abschalten.** Die
  zwei Vorspiel-Screens fahren EIGENE Event-Schleifen, deren Frames kein `turn_tracker` haben —
  der Pump wird dann von der Kartenauswahl leergesaugt und `main()` nie erreicht, während der
  Harness wahrheitsgetreu aussehende „6000 Frames" und ein leeres `_main_locals()` meldet.
  Ebenso `main.ClaudeAgent = lambda *a, **k: MockAgent()` — sonst kostet der Lauf Geld.
- Der Turn-Plan-Grund `(test plan)` bzw. `(mock plan)` unterscheidet einen Selbstspiel-Lauf von einer
  echten Partie des Users im selben `logs/`-Ordner.

---

# Teil 2 — Stand

## Karten und Szene

Drei Karten (`game/maps.py`), Auswahl über `config.MAP` (steht auf `map2`) oder `python main.py --map 1`.
Ein `BattleMap` trägt Brettmaße, Deployment-Zonen, Terrain+Objectives, optional ein `roster` (welche
Einheiten diese Karte fieldet) und die handgesetzten Alt-Positionen. Die Armeelisten selbst liegen
in `armies/*.json` (die Zeile sagte bis 2026-09-07 `main.py` und war schon lange davor falsch —
sie waren zwischendurch in `game/army_lists.py`). `maps.apply_to_config()` schreibt die Brettmaße einmalig beim Start in `config` (~24
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
  - **Und sie liegen jetzt GANZ darin** (User: "die beiden mittleren objectives ragen in die
    austellungszonen hinein. das ist schlecht für manche Missionen, die als Bedingung 'outside of
    your deployment zone' haben"). Gemessen vor der Änderung: **15.3 % der Fläche jedes der beiden
    Stücke lagen in einer Aufstellungszone**, die ferne Ecke 12.01" von der Brettmitte gegen die
    9" des Lochs. Eine Einheit konnte das mittlere Objective halten und dabei in der eigenen Zone
    stehen — genau das, was diese Missionen verbieten.
    - **Der Zeile, die es hätte fangen müssen, fehlte die FLÄCHE.** map3s Suite prüfte schon, dass
      die zwei Niemandsland sind — aber am MITTELPUNKT des Objectives, und der lag immer im Loch.
      Worauf eine Einheit steht und was 14.02 misst, ist die Fläche.
    - **1.2" ZUR BRETTMITTE GESCHOBEN und auf Skala 0.675 gebracht** → Mitte (34.72, 20.57),
      5.05 × 7.32. **Schrumpfen allein reichte nicht und war zu brutal**: die erste Fassung ließ die
      Mitte stehen und kam damit auf 0.481 (ein Viertel der Fläche), was der User zu Recht
      zurückwies ("die objectives sind jetzt sehr klein. die können gerne wieder etwas größer
      sein"). Der Grund ist die LAGE, nicht die Größe: das Stück steht 6.13" vom Mittelpunkt eines
      9"-Kreises entfernt, seine ferne Ecke liegt bei gemessener Breite **allein in X schon 9.61"
      draußen**, und — gemessen — schafft bei DIESER Mitte kein Seitenverhältnis mehr als ~21 sq.in,
      weil die bindende Ecke von BEIDEN Kanten zugleich hinausgeschoben wird. Platz muss aus der
      Position kommen.
    - **Warum 1.2" und nicht mehr: der KORRIDOR** (User: "es soll aber noch ein corridor zwischen
      den objectives bleiben"). Weiter hineinschieben kauft schnell Größe — 2.0" erlaubte 80 % des
      gemessenen Stücks —, schließt aber die Gasse zwischen dem Paar; bei 3.0" überlappen sie
      einander. **Die Gasse der KUNST ist 4.26" breit, und das ist die Zahl, die gehalten wird:**
      1.2" hinein lässt 4.39", weiterhin breiter als die 4.2"-Base eines Falcon oder Wave Serpent,
      also des breitesten Dings, das da durchfahren muss. Damit ist der Korridor die Schranke, die
      die Größe deckelt — nicht das Loch.
    - **Ergebnis: doppelte Fläche gegenüber der Nur-Schrumpf-Fassung, 68 % des gemessenen Stücks**,
      Fläche 8.85" und gezeichneter Ring 8.97" (beide im 9"-Loch), keine Überlappung mit anderem
      Gelände, Seitenverhältnis 1.4495 gegen gemessene 1.4505.
    - **Der Ring ist der Grund für 0.675 statt eines Hauchs mehr**: `objective_outline_points()`
      wächst um 5 BILDSCHIRM-Pixel, bei Spielzoom 0.08". Eine Fassung, deren Fläche frei ist und
      deren Ring den Bogen kreuzt, hätte ungefixt AUSGESEHEN. **Auf der Kartenvorschau (~17 px/Zoll)
      kann der Ring den Bogen weiter berühren** — das ist die feste Pixelbreite der Dekoration,
      nicht das Objective, und deshalb benannt statt weiterverfolgt.
    - **Das Paar bleibt spiegelbildlich**, also weiter exakt gleich weit von der Brettmitte — was
      beide erst zu „zentralen" Objectives für Secure Asset und Unstoppable Force macht.
    - **Es ist außerdem die ehrlichere Größe für das, was die Kunst zeichnet:** diese zwei sind
      KEILE, per aufrechtem Rechteck angenähert, und ein Keil füllt sein Rechteck zu zwei Dritteln
      (unten gemessen) — ein Rechteck, das aus dem Loch ragt, ist zum Teil die Näherung, die
      herausragt. 0.675 liegt genau in dieser Größenordnung.
    - **Eine gemessene Brettzahl ist mitgewandert und ist nachgezogen statt gepinnt geblieben:**
      `observation.garrison_reach_needed_in()` liest den Abstand vom Home Objective zum NÄCHSTEN
      anderen — und das nächste ist eines dieser beiden. map3 geht damit von 15.9" auf **16.8"**
      (in `test_map3_crucible.py` und `test_home_garrison.py`). Die Aussage, für die die Zahl
      steht, bleibt: eine 12"-Waffe kann das Home Objective weiterhin nicht sinnvoll halten, und
      genau das prüft die Zeile jetzt zusätzlich, statt nur die Zahl festzuhalten.
    - **Die Invariante ist jetzt KARTENÜBERGREIFEND gepinnt** (`test_deployment_shapes.py`
      Abschnitt 9): ein Objective ist entweder HOME (ganz in der Zone seines Besitzers, per Design)
      oder Niemandsland (ganz außerhalb BEIDER Zonen) — nichts steht mit einem Bein drin. map1 und
      map2 erfüllten das schon, map3 war der einzige Verstoß; eine vierte Karte erbt die Prüfung
      gratis. **A/B belegt:** mit der gemessenen Größe zurück fallen beide Suiten und nennen die
      Zahlen des Berichts wörtlich (15.5 % der Fläche, ferne Ecke 12.01"). Der KORRIDOR ist
      zusätzlich gepinnt (map3s Suite), gegen die 4.26" der Kunst UND gegen die 4.2"-Grav-Panzer-
      Base — sonst wäre „größer machen" beim nächsten Mal wieder eine Einladung, die Gasse
      zuzuschieben.
    - **Nebenbefund, und ein hübscher:** `test_primary_missions.py` pinnte, dass map3s zwei
      Mittel-Objectives BIT-IDENTISCH gleich weit von der Brettmitte stehen, mit dem Vermerk, die
      0.001"-Toleranz von `central_objectives()` sei auf den ausgelieferten Karten „nachweislich
      INERT ... nur das Netz für eine künftige Karte, deren Spiegelung durch andere Arithmetik
      läuft". **map3 ist diese Karte geworden:** die kleineren Stücke verschieben die Wände, aus
      denen der Mittelpunkt gemittelt wird, und das Spiegelpaar liegt jetzt ~7e-15 auseinander —
      dieselbe Größenordnung, die schon einmal aus einem Rechteck ein Fünfeck gemacht hat. Die
      Prüfung fragt jetzt die Toleranz, die die Regel selbst benutzt, und zusätzlich, dass wirklich
      noch BEIDE als zentral zurückkommen.
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
  - **BERÜHRENDE STÜCKE werden auch gebaut, wie sie sich berühren — die einzige Stelle, an der
    eine Koordinate hier NICHT die rohe Messung ist** (User: "bei map 3 gibt es kleine lücken,
    durch die man durchschießen kann zwischen den geländestücken ... schiebe sie so zusammen,
    dass da keine lücken sind, wenn geländestücke sich berühren sollten"). **Der Perzentil-Fit
    IST die Ursache**: er trimmt an JEDEM Stück eines berührenden Paares eine Scheibe ab, also
    wurde aus einer gezeichnet geschlossenen Naht ein Schlitz von bis zu 0.43".
    - **WELCHE Paare sich berühren, ist an der Vorlage GEMESSEN, nicht angenommen**: die
      gezeichneten Stücke der vier betroffenen Paare kommen sich auf **0.05–0.15"** nahe (die
      Breite der Trennlinie), während das eine Paar, das genauso aussieht und NICHT berührt
      (Quer-Bar gegen die −52.5°-Barrikade), im Bild **2.35"** auseinandersteht und offen
      bleibt. Ohne diese Gegenprobe bestünde die Zusicherung auch auf einem Brett, das alles zu
      einem Klumpen schiebt.
    - **Verschoben wird, nie vergrößert, und nur Barrikaden bzw. mauerlose Trümmer** — kein
      objective-tragendes Stück bewegt sich, also stehen alle sechs Objectives unverändert da,
      wo sie gemessen wurden. Drei Stücke der Mittellinie stehen in EINER REIHE: das mittlere
      behält seine Messung, die zwei äußeren kommen zu ihm — die einzige Zuteilung, die beide
      Nähte gleichzeitig schließt, und die mit der geringsten Bewegung.
    - **Nur EINE der vier Lücken war wirklich eine Schusslinie**, und das ist die Trennung, die
      man hier nicht übersehen darf: die anderen drei betreffen eine Barrikade, und eine
      Barrikade ist LIGHT und hat Sicht noch nie blockiert. Das Paar an der Mittellinie sind
      dagegen zwei RUINEN, deren WÄNDE 0.15" auseinander und einander zugewandt standen — ein
      Schlitz, den eine Sichtlinie einfädelt. **Durch die echte `line_of_sight`-Kette gemessen:
      21 senkrechte Schüsse quer durch den alten Schlitz, vorher 4 von 21 geblockt, nachher
      21 von 21.**
    - **Getestet:** `test_map3_crucible.py` Abschnitt 7 (101 → **109/109**) — kein Paar liegt
      zwischen 0 und 1" voneinander (entweder bündig oder klar getrennt), acht exakte Kontakte
      (vier plus Spiegel), das offene Paar bleibt offen, die Wände berühren sich, und die
      Sichtlinie ist zu (mit Gegenprobe auf offenem Boden, sonst bestünde die Zeile auch auf
      einem Brett, das alles blockt). **A/B an der QUELLE** (alle vier Paare zurück auf die rohe
      Messung): **105/109**, und die erste rote Zeile nennt alle acht Schlitze mit ihrer Breite.
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

## Game Menu (game/ui/game_menu.py, main.py's run())

**Der Rahmen um das Spiel** (User: "momentan startet das spiel direkt mit der map auswahl und
endet mit ESC. baue ein spieletypisches game menu ... im spiel öffnet ein druck auf ESC das menü.
außerdem muss noch irgendwo ein kleiner menu knopf sein. vielleicht links oben neben dem rechten
panel"). Vorher fiel `main()` direkt in die Kartenauswahl, und der einzige Ausgang war ESC im
Vollbild — es gab keinen Weg, eine Partie zu verlassen ohne das Programm zu beenden, und keinen,
eine zweite zu beginnen.

- **`main()` ist EINE SCHLACHT, `run()` ist die ANWENDUNG.** Das ist die Entscheidung, aus der alles
  Übrige folgt. Board, GameState, die ~40 Controller, `game_log`, der Agent — alles sind Locals von
  `main()` und sterben mit ihr; ein echter Neustart ist deshalb schlicht „`main()` verlassen und
  wieder aufrufen", und es gibt nichts abzuräumen.
  - **ALLE ZEHN Harnesses rufen `main.main()` direkt.** Das Menü eine Ebene höher zu legen heißt:
    ein Screen, der auf einen Klick wartet, liegt gar nicht auf ihrem Weg. Anders als `MAP_SELECT`
    und `ARMY_SELECT` braucht `START_MENU` deshalb **kein Opt-out in zehn Dateien und keinen
    Quell-Wächter**, der einen künftigen Harness daran erinnert. `--no-menu` ist reine CLI.
  - **Zurückzusetzen ist nur `config.LOAD_SCENE` und der Kartenschlüssel** — sonst öffnete „New
    Game" ewig denselben Spielstand. Alles andere wird von `maps`/`army_lists`/`detachments`
    `.apply_to_config()` je Lauf VON GRUND AUF neu geschrieben. `config.BIOME` und die zwei
    Armee-Settings überleben ABSICHTLICH: sie sind die Defaults, auf denen die Picker öffnen.
  - **`set_mode()` läuft genau EINMAL pro Prozess** (in `run()`); `main()` nimmt per
    `pygame.display.get_surface()` das vorhandene Fenster. Ein zweiter `set_mode()` je Schlacht
    zöge das Display unter jeder `convert_alpha()`-Fläche weg, die `game/sprites.py` modulweit
    cacht — und die sollen eine Schlacht überleben.
  - **Der `id(board)`-Cache ist gemessen ungefährlich:** `Renderer._static_cache_key` ist eine
    INSTANZ-Variable und `renderer` ein Local von `main()`, jede Schlacht bekommt also einen
    frischen Cache. Die dokumentierte Recycling-Falle betraf den modulweit geteilten Renderer in
    `map_preview`, der dort längst pro Aufruf neu gebaut wird. **Im echten Spiel belegt:** zwei
    `main()`-Läufe hintereinander in EINEM Prozess auf map1 und map3, der zweite zeichnet sein
    eigenes Brett (`smoke_game_menu.py`).
- **EINE Klasse, ZWEI Wirte.** Startbildschirm (eigener Screen über `tile_screen.run_screen()`) und
  ESC-Overlay sind dasselbe `GameMenu`. Geteilt: Panel-Rechteck, Eintrags-Rechtecke, Hit-Testing,
  Tastatur, Malen. Genau ZWEI Dinge verzweigen auf `in_game`: der HINTERGRUND (Scrim über dem
  laufenden Frame gegen gefüllter Screen mit Kopfzeile) und die EINTRÄGE.
  - Start: New Game / Resume / Quit. Im Spiel: Resume / **Save** / New Game / Quit.
  - **„Resume" bedeutet an beiden Orten etwas anderes, und das ist bestellt** (User: "Beides, je
    nach Ort"): im Spiel zurück zur Schlacht, beim Start der neueste Spielstand.
  - **Ein DEAKTIVIERTER Resume-Eintrag bleibt stehen**, ausgegraut, mit dem Grund darunter — das
    Gegenteil von `tile_screen`s „kein Chrome für ein totes Steuer"-Regel, und absichtlich: ihn
    wegzulassen änderte still die FORM des Menüs zwischen den Wirten.
  - **EIN Klick = eine Aktion**, kein Zwei-Takt wie bei Karte/Armee: die Rückfrage wurde
    ausdrücklich abgelehnt. **Benannte Folge:** ein Fehlklick auf „Start New Game" im Spiel
    verwirft die Partie; der Autosave ist, was das überlebbar macht.
  - **Accents sagen, was ein Druck KOSTET** (die schon geltende `button_style`-Semantik): Resume
    grün, Quit rot, New Game **blau beim Start und ROT im Spiel** — dort kostet es die Schlacht.
  - **`run()` gibt NIE `None` zurück**, anders als die zwei Picker: dieser Screen HAT einen
    Quit-Eintrag, ESC und das Fensterkreuz beantworten ihn also, statt einen vierten Zustand zu
    erfinden.
- **Verdrahtung im Spiel — alles VOR der ~48-Zweige-Kette** (Fehlerklasse 15): der
  `is_pending`-Zweig mit `continue`, und der Knopf-Hit-Test als eigenes `if`. Beide über dem
  Regel-Leser bzw. so geordnet, dass ein offener Leser den Klick zuerst bekommt.
  - **Die Antwort wird per `take_action()` EINMAL pro Frame gepollt** (Idiom von
    `take_pending_placement()`): ein Overlay kann keine `main()`-Locals schreiben, und das Löschen
    beim Übergeben ist, was einen Druck nicht zweimal bedient werden lässt.
  - **NICHT in `_front_notice()`** — das ist die Ordnung der Klick-irgendwohin-Notices mit
    `.dismiss()`; dies hat echte Knöpfe und ein eigenes `handle_event`, wie `army_rules_overlay`,
    das aus demselben Grund nicht drinsteht. `test_one_modal_at_a_time.py` bleibt unberührt.
  - **Die KI hält an, und zwar über EINEN Term:** `ai_action_paused_this_frame` bekommt
    `or game_menu.is_pending` an seiner Saat. Diese Flagge lesen beide KI-Einstiege schon, und der
    Auto-Play-Tick läuft AUSSERHALB der Event-Schleife — der `continue` des Zweigs deckt ihn also
    gar nicht ab.
  - `_open_game_menu()` beendet zuerst den Line-Drag: der wird GEPOLLT und ist vom `continue`
    ebenfalls nicht gedeckt, ein gehaltener Rechtsklick zöge sonst unter dem Scrim weiter Modelle.
- **Der Knopf sitzt in der Brett-Ecke oben rechts** (74×26 bei MARGIN 12, dieselbe Ecke wie der
  AUTO-PLAY-Punkt). **Gemessen gegen das Würfelpanel**: 334 px frei bei 1920, **14 px bei 1280** —
  dem schmalsten Fenster, für das dieses Projekt gebaut ist. Als Rechnung im Test gepinnt.
  - **Der AUTO-PLAY-Punkt weicht nach UNTEN aus**, nicht nach links, und das korrigiert die
    ursprüngliche Wahl aus gemessenem Grund: nach links liefe er in genau dieses Würfelpanel.
    `draw_auto_play_dot(avoid_rects=)` ist dasselbe Wort, das `AiBusyBadge` für dieselbe Idee schon
    benutzt; ohne Argument bewegt sich nichts, weshalb `test_ai_busy_badge.py` unverändert grün ist.

### Größere Schrift und ein Hintergrundbild (2026-09-07)

Zwei User-Bitten, EINE Schriftmenge: *"Die Font im Main Menu und Auswahl screen darf viel größer
sein"* und *"main-manu-background.jpg als hintergrund im hauptmenü setzen"*.

- **`tile_screen.make_fonts()` ist die eine Menge, gelesen von DREI Screens** (Kartenauswahl,
  Armeeauswahl, Game Menu) — "größer" ist also eine Änderung mit drei Konsumenten. Jeder Versatz
  ist jetzt eine benannte Konstante (`TITLE_FONT_DELTA` … `SMALL_FONT_DELTA`), also kostet "noch
  größer" eine Zeile je Rolle statt sechs Literale in einem Dict.
  Die REIHENFOLGE der Rollen bleibt (Titel > Name > Untertitel > Label > Body > Small) und ist als
  Ordnung gepinnt statt als sechs Zahlen — die Bitte galt der Größe, nicht der Hierarchie.
- **Was schiefgehen kann, sind nicht die Schriften, sondern die Kästen, die um die alten herum
  gemessen wurden** — und WELCHE davon wirklich mitwachsen mussten, hat die A/B-Sonde entschieden,
  nicht das Auge:
  - **`HEADER_HEIGHT` bleibt bei 104.** Die Sonde ("zurück auf den alten Wert") biss NICHT: die
    Leiste trägt Titel plus Hinweiszeile auch in der neuen Größe, und jeder Pixel, den man ihr
    gibt, kommt direkt aus `tile_area()`s Kachelband. Eine Änderung, die nichts kauft, ist keine.
  - **`FOOTER_HEIGHT` 58 → 70 und `CONFIRM_BUTTON_WIDTH` 240 → 300**, und was sie kaufen ist die
    LUFT unter den Knöpfen: "steht noch im Fenster" ist mit einem 4-Pixel-Streifen erfüllt, während
    die alte Fußzeile 14 px hatte. `FOOTER_CLEARANCE_PX` ist diese Marge, und erst diese Prüfung
    macht beide Konstanten tragend (vorher bissen ihre Sonden nicht). Bei 240 bricht das längste
    echte Confirm-Label auf DREI Zeilen um, der Knopf wächst auf 67 px und hängt unten heraus.
  - **`PANEL_WIDTH` 460 → 560 im Game Menu.** Eine Notiz unter einem Eintrag wird als EINE
    ungebrochene, zentrierte Zeile gezeichnet — ein Panel schmaler als die längste ("abandon this
    battle and pick a new map and armies", 370 px) malt sie über den eigenen Rahmen.
    **`ENTRY_HEIGHT` 46 → 58 ist dagegen reine SPACING-Wahl** und ausdrücklich so dokumentiert:
    `draw_button()` wächst eine zu kurze Zeile von selbst, die alte Zahl hätte also weiter
    funktioniert — die Sonde sagte es, und der Kommentar sagt es jetzt auch.
- **Ein vorbestehender Überlappungsfehler wurde dabei sichtbar und ist behoben:** die
  Kartenauswahl teilt sich ihre Kopfleiste mit der BIOM-Reihe, und ihre Hinweiszeile ist KEIN
  fester String — sie nennt die gewählte Karte. Gemessen: der Crucible-Hinweis läuft **608 px**
  schon in der alten Schriftgröße, gegen eine Reihe, die bei 1280 px bei **616 px** beginnt und mit
  dem vierten Biom weiter nach links gerückt ist. Der Kommentar an `BIOME_BUTTON_WIDTH` behauptete
  das Gegenteil ("sie sind feste Strings ... ~380 px Abstand") — das war beim Schreiben wahr.
  `ts.ellipsised()` kürzt jetzt, und `map_select._hint_width()` leitet den Platz aus
  `biome_layout()` ab statt ihn einmal zu messen und hinzuschreiben, sodass ein fünftes Biom die
  Zahl mitzieht.
- **Der Hintergrund: `sprites.menu_background_path()` / `menu_background_surface()`**, dieselbe
  "fehlende Kunst kostet ein Bild, nie den Screen"-Konvention wie jede andere Suche in dem Modul.
  - **Die Datei liegt in `Sprites/Death Guard/`, und das wird NICHT "korrigiert"** — `_resolve_path`
    durchsucht nach dem Top-Level die Fraktionsordner, und hier gilt wie überall: DER ORDNER
    GEWINNT. Auch der Name trägt die Schreibweise des Users ("manu"); ihn "richtig" zu
    transkribieren löst auf nichts auf (eigene A/B-Sonde).
  - **COVER, nicht Fit**: eine letterboxte Vorlage lässt Balken der Flächenfarbe an zwei Seiten
    stehen, was sich als nicht geladene Kunst liest. Seitenverhältnis bleibt, der Überstand wird
    mittig beschnitten. Nach `(Pfad, Breite, Höhe)` gecacht — eine Fenstergröße ändert sich, wenn
    das Fenster sich ändert, und das ist ein Vollbild-`smoothscale`.
  - **Der Schleier (`BACKGROUND_VEIL_COLOR`, Alpha 150) ist keine Dekoration:** goldene
    Überschrift, gerahmtes Panel und die rechtsbündige Tastenzeile liegen direkt auf einem Foto,
    und ohne ihn hängt ihr Kontrast davon ab, was zufällig dahinter liegt.
  - **Der IN-BATTLE-Host bleibt unangetastet** — sein Hintergrund ist das eingefrorene Brett, was
    der ganze Sinn eines Pausenschirms ist. Eigene Testzeile und eigene Sonde.
  - **Die zwei Picker bekommen die Kunst bewusst NICHT**: die Bitte nannte das Hauptmenü, und ein
    Foto hinter einem Raster aus Kartenvorschauen kämpft mit ihnen.
- **Getestet:** neu `test_menu_presentation.py` (**42/42**, vier Abschnitte) plus
  `ab_menu_and_decline.py` (16 der 20 Sonden gehören hierher, alle beißend). **Fünf Sonden bissen
  zuerst NICHT, und alle fünf waren Befunde über den TEST** (Fehlerklasse 24): die
  Fußzeilen-Prüfung fragte nur "steht es im Fenster" statt nach der Luft darunter; `HEADER_HEIGHT`
  brauchte gar keine Änderung; die Kartenauswahl reichte ihr Budget an eine Funktion, die der Test
  selbst aufrief statt den Screen (jetzt ein Spion auf `ts.draw_header`); Cover gegen Fit war an
  einer Surface fester Größe gar nicht unterscheidbar (jetzt an einem synthetischen Bild mit
  absichtlich falschem Seitenverhältnis); und `ENTRY_HEIGHT` war schlicht nicht tragend.
  Volle Regression **186 Suiten, ~16347 Prüfungen, 185 grün / 0 rot / 1 bekannt**, `run_tests.py
  --smoke` komplett grün.

### Der Titel, und keine Unterschriften mehr (2026-09-07)

- **`TITLE = "WARHAMMER 40K AI SIMULATOR"`** (User: "Oben links soll stehen Warhamer 40k AI
  Simulator"). Versalien, weil dieselbe Kopfleiste die zwei anderen Vorspiel-Screens trägt
  ("CHOOSE THE BATTLEFIELD", "CHOOSE FACTION") — die drei lesen sich sonst wie drei Programme.
  Gemessen: 582 px bei 1212 px Platz auf dem schmalsten Fenster.
- **Die Zeile unter jedem Knopf ist WEG** (User: "Die unterschriften unter den buttons können
  weg"). `entries()` liefert damit `(action, label, enabled)` statt eines Vierertupels, und
  `NOTE_GAP`/`NOTE_COLOR`/`DISABLED_NOTE_COLOR` sind ersatzlos entfallen — ein Feld, das niemand
  mehr zeichnet, ist genau der tote Code, den dieses Repo sonst findet, wenn es zu spät ist.
- **BENANNTE FOLGE, hier festgehalten statt zum Wiederentdecken:** die Startbildschirm-Zeile unter
  „Resume Game" nannte den Spielstand, der geladen wird ("map2 - battle round 1 - Player 1"), und
  die unter einem AUSGEGRAUTEN Resume nannte den GRUND ("no saved game yet"). Beides steht jetzt
  nirgends. `save_note` bleibt trotzdem Konstruktor-Argument, weil es das EIGNUNGS-TOR ist
  (Fehlerklasse 5: `summary()` gibt `None` für eine unlesbare Datei) — es war nie nur eine
  Unterschrift. Eine Zeile im Panel, falls es zurück soll.
- **`PANEL_WIDTH` und `ENTRY_HEIGHT` sind damit beide reine SPACING-Wahlen**, und das steht im
  Kommentar: die Notizen waren das Einzige, was je an die Panelbreite stieß (370 px Fließtext),
  und `draw_button()` wächst eine zu kurze Zeile ohnehin selbst. Ihre A/B-Sonden sagten es,
  bevor der Kommentar es sagte.
- **Getestet:** `test_game_menu.py` 139 → **141/141** (eine Zeile ist zu Recht rot geworden — sie
  las die Unterschrift des ausgegrauten Resume; sie prüft jetzt die FORM der Zeile und dass das
  Menü gar keine Notizfarbe mehr kennt), `test_menu_presentation.py` **42/42** (die
  Notiz-Passt-Prüfung ist durch „zwischen zwei Zeilen steht nichts mehr" ersetzt, also genau die
  Zusicherung, die eine versehentlich zurückkehrende Unterschrift bricht).

### Speichern und Laden: der Snapshot trägt jetzt den Missionsstand

CLAUDE.md führte „`scene_io` sichert keine VP" als offenen Punkt. Er ist zu.

- **Autosave zu Beginn jeder Schlachtrunde** (User: "Auto save pro Schlachtrunde") nach
  `scenes/autosave.json` (fester Name, kein Zuwachs auf der Platte), plus ein **Save-Knopf im
  Menü** (zeitgestempelt, damit der nächste Autosave keinen Handstand überschreibt). F9 unverändert.
  - **Eine RUNDENgrenze ist der einzige Zeitpunkt, an dem der Snapshot per KONSTRUKTION vollständig
    ist.** Alles Zug-gebundene der drei Missions-Controller (`_destroyed_this_turn`, die vier
    `*_at_turn_start`-Schnappschüsse, `guards`, `*_this_turn`, `ActionController.states`,
    ein offener Brett-Pick) ist dort leer — und die Hälfte davon ließe sich gar nicht schreiben, weil sie
    lebende Squad-Referenzen, `id()`-Schlüssel oder CALLBACKS hält. **Die Regel, die entscheidet:
    ein `card_state`-Schlüssel auf `_this_turn` ist zug-gebunden, jeder andere schlachtlang.**
  - Gehalten, solange irgendetwas ansteht, und AUSSERHALB der Event-Schleife.
- **`_save_scene()` ist der EINE Schreiber** (F9, Menü-Save, Autosave) und `_mission_slots()` die
  EINE Antwort darauf, welcher Controller in welchen Slot gehört.
- **Jeder Controller serialisiert sich selbst** (`save_state()`/`load_state()`), weil „was ist hier
  zug-gebunden" eine Tatsache über SEINE Regeln ist, nicht über das Dateiformat. Karten sind
  Modul-Singletons → nach KEY; Objective und Einheit → nach NAMEN; Death Traps `trapped` hat keinen
  Namen → nach INDEX in `state.terrain_areas` (deterministisch aus dem Kartenschlüssel, den der
  Snapshot ohnehin pinnt). **Die Deck-REIHENFOLGE wird mitgespeichert** — es wird per `pop(0)`
  gezogen, ein Neumischen beim Laden teilte eine andere Schlacht aus.
- **`FORMAT_VERSION` bleibt 1.** Präzedenzfall ist `armies`: ein OPTIONALER Abschnitt, ohne die
  Version zu bewegen. Die zwei vorhandenen Dateien in `scenes/` laden unverändert, nur ohne
  Missionsstand — im Test von beiden Seiten gepinnt.
- **Eine vor dem Speichern AUSGELÖSCHTE Einheit kam zurück — behoben.** `capture()` läuft über
  dieselben drei GameState-Listen wie `all_squads()`, eine tote Einheit steht in keiner und fehlt
  im Snapshot. `restore()` meldete das nur. **Gemessen:** auf dem Default-Pfad blieb sie zufällig
  unsichtbar (bei `PREGAME_DEPLOYMENT` stellt `register_unit()` gar nichts auf), auf dem
  Legacy-Pfad (`--no-deployment`) stand sie **mit voller Stärke auf dem Brett**. `restore()`
  RÄUMT sie jetzt ab (Modelle nach `destroyed_models`, `models` leer — wie diese Engine „zerstört"
  überall buchstabiert). **Sie wird NICHT als Kill verbucht** — die VP dafür sind im
  wiederhergestellten Ledger, ein zweites Mal zu zählen zahlte jeden Verlust doppelt. **Ventil:**
  passt der Snapshot auf KEINE Einheit der Szene, wird nichts gelöscht und der Grund gemeldet —
  sonst löschte ein Snapshot vom falschen Roster beide Armeen.
- **`newest()` liefert den jüngsten LESBAREN Snapshot** (nach mtime), nicht die jüngste `.json`:
  eine halb geschriebene oder fremde Datei ließe sonst Resume ausgegraut, während ein gutes Save
  eine Datei darunter liegt. `summary()` gibt `None` für Unlesbares und IST das Eignungs-Tor
  (Fehlerklasse 5) — angeboten wird nur, was auch geladen werden kann.

**Getestet:** neu `test_game_menu.py` (**139/139**, sechs Abschnitte) und `smoke_game_menu.py`
(**17/17**, 13 Frames, in `run_tests.py --smoke`; `--neutralize` fällt auf **3/17**, 14 Prüfungen
kippen). `test_scene_io.py` 40 → **74/74** (Abschnitt 8 die Auslöschung in beiden Pfaden plus dem
Ventil, Abschnitt 9 der Missions-Rundlauf). Volle Regression **168 Suiten, ~14932 Prüfungen, 167
grün / 0 rot / 1 bekannt**, alle acht Smokes.
**Im ECHTEN Spiel belegt:** der Autosave schreibt in einem `selfplay.py`-Lauf wirklich (Runde 1,
mit `missions`-Abschnitt), und ein per `--load` geöffneter echter Autosave bringt VP beider
Spieler, die ungewerteten Kills und den Primary-Punktestand zurück.
**Vier fremde Pins wurden zu Recht rot** und sind nachgezogen: die zwei `pygame.quit()`-Pins der
Picker (jetzt stärker: `main()` darf das Fenster gar nicht mehr schließen), und die zwei
ESC-Leiter-Pins in `test_line_drag.py` / `test_unit_selection.py`. Der erste davon hatte ein
FESTES 2200-Zeichen-Fenster um den ESC-Zweig und enthielt die geprüfte Zeile nicht mehr — er
schneidet jetzt am nächsten Zweig ab.

### Ein Save trägt jetzt WELCHES Modell — und wer schon gehandelt hat

**Gemeldet:** *"schaden auf einheiten wurde nicht gespeichert"* und *"es wurde nicht gespeichert,
wer schon welche aktion ausgeführt hat. zb wer schon geschossen hat und wer nicht"* — zwei Berichte,
zwei ganz verschiedene Ursachen.

**1. Der Schaden war IMMER in der Datei. Er landete beim Laden auf dem FALSCHEN Modell.**
Ein Snapshot hält die ÜBERLEBENDEN einer Einheit, die Szene beim Laden hält sie wie GEBAUT — und
`restore()` paarte sie der Reihe nach und schnitt den REST HINTEN ab. Also bekam ein Charakter am
Ende der Modellliste (wo 19.01 ihn hinstellt) nie seine Wunden zurück, und gelöscht wurde er obendrein.
- **Am EIGENEN Save des Users belegt** (`scenes/scene_20260904_214638.json`, map3, necrons vs death
  guard): `1 Skorpekh Destroyers 1 + Skorpekh Lord` steht darin mit EINEM Modell auf 5 Wunden — das
  ist der Lord auf 5/7. Restauriert wurde daraus ein **Skorpekh Destroyer auf 5/3**, also ÜBER
  seinem Maximum (i. e. unverwundet), während der Lord als Leiche galt. Dieselbe Form trifft jede
  Attached Unit: ein Immortal bekam routinemäßig die Wunden des Plasmancer, und der Plasmancer war
  das gelöschte Modell.
- **Der Fix ist eine IDENTITÄT pro Modell** (`"model"` = Datenblattzeile, `"weapons"` = Waffennamen)
  und `_match_models()` mit DREI enger werdenden Pässen: gleiche Zeile UND gleiche Waffen → nur
  gleiche Zeile → der Rest der Reihe nach. Der dritte Pass IST das alte Verhalten, also lädt eine
  Datei ohne Identität exakt wie bisher (`FORMAT_VERSION` bleibt 1, wie bei `armies` und `missions`).
  **Der zweite Pass ist keine Kosmetik:** `firing_deck.py` und `support_turret.py` verleihen Waffen
  für die Dauer einer Aktivierung, ein mitten darin gezogener Save hat also eine Waffenliste, die
  es beim Neubau nicht gibt.
- **Eine Leiche wird jetzt als Leiche wiederhergestellt** (`_make_casualty()`: 0 Wunden, auf
  `destroyed_models`) statt bloß weggeworfen — dieselbe Behandlung, die `_evict()` einer
  ausgelöschten EINHEIT längst gibt, und der Grund ist derselbe: Reanimation Protocols, Undying
  Legions, Grot Orderly und Vengeful Stars lesen genau diese Liste. Eine geladene Necron-Schlacht
  hat damit dieselben drei Krieger zum Reanimieren wie die, aus der sie gespeichert wurde.
- **Dazu eine KLAMMER auf `current_wounds`**: über das eigene Maximum kann kein Modell mehr
  zurückkommen. Für die Dateien, die schon auf der Platte liegen, ist das alles, was noch zu retten
  ist (ihnen fehlt die Identität) — der Skorpekh Destroyer steht danach auf 3/3 statt auf 5/3.
  Gefahrlos, weil eine Shield Drone `profile.wounds` MITerhöht.

**2. „Wer hat schon gehandelt" stand nirgends in der Datei.** Neu: `game/activation_state.py`.
- **Der AUTOSAVE hat es nie gezeigt, und das ist kein Zufall:** er läuft an der Rundengrenze, dem
  einen Moment, in dem per Konstruktion jedes dieser Register leer ist. F9 und „Save Game" laufen
  mitten im Zug — und genau die drückt ein Spieler.
- **EIN Modul statt acht `save_state()`-Methoden**, und das weicht bewusst von der Missions-Regel
  ab: dort trägt jeder Controller eine ANDERE Art Zustand, hier ist es EINE Frage mit acht
  identischen Antworten (Menge von Einheiten bzw. Dict nach Einheit). Was wirklich schiefgeht, ist
  ein NEUNTES Register, das niemand einträgt — und das fängt eine Tabelle plus Quell-Wächter, acht
  verstreute Methoden nicht.
- **Drinnen:** Movement (moved/stationary/advanced + `moved_distance_this_turn` für [HEAVY] 24.16 +
  `advance_bonus_by_squad`, weil 09.06 den Advance-Wurf für die Phase festschreibt), Shooting
  (shot + `last_ranged_attack_turn`, das 13.09s Hidden beendet, + `one_shot_used` für 24.26), Charge,
  Fight, Pile-In, Consolidate, Battle Shock, For The Greater Good — plus **22 Squad-Flags**: die
  Eignungs-Sperren (11.04/09.07/18.02/20.04) und jede „bis Ende des Zuges"-Wirkung, für die CP oder
  ein Battle-Focus-Token BEZAHLT wurde.
- **`one_shot_used` ist nach `(model.id, id(weapon))` gekeyt** — beides ist nach einem Neubau
  wertlos, also wird das Modell über seinen INDEX in der Einheit benannt (dieselbe Reihenfolge, die
  `restore()` zurücklegt) und die Waffe über ihren gedruckten Namen.
- **`restore_activation()` läuft NACH `begin_battle()`**, und hier hat die Ordnung Zähne:
  `begin_battle()` löscht `set_up_this_turn` auf JEDER Einheit (18.02), vorher gesetzt wäre es
  sofort wieder weg. Eigene A/B-Sonde dafür.
- **Bewusst NICHT drin, als EINE Regel statt einer Ausredenliste:** ein Snapshot stellt ein
  GESETZTES Brett wieder her, nie eine halbfertige Aktivierung. Namentlich betroffen:
  `nova_charge_grants`, `attached_ability_grace`, `fired_weapon_types` und `ActionController.states`.

**Getestet:** neu `test_scene_activation.py` (**66/66**, sechs Abschnitte — Abschnitt 1 fährt die
Einheit aus dem echten Save des Users) plus `ab_scene_activation.py` (**13 A/B-Sonden, alle
beißend**). `test_scene_io.py` 73 → **75/75** (Abschnitt 3s Überschrift versprach „verliert seinen
SCHWANZ", was aufgehört hat zu stimmen). Volle Regression **181 Suiten, ~15873 Prüfungen, 180 grün /
0 rot / 1 bekannt**.
- **VIER Sonden bissen zuerst NICHT oder ließen die Suite ABSTÜRZEN, alle vier Befunde über den
  TEST** (Fehlerklasse 24): die wichtigste Sonde stellte nur Pass 1 ab und ließ Pass 2 laufen, also
  gar nicht die Vor-Fix-Welt (Fehlerklasse 16); der Waffen-Fall kam auf dem gewählten Brett
  ZUFÄLLIG richtig heraus, weil die Spezialwaffen vorne stehen und überlebten (jetzt stirbt der
  Fusion-Schütze, und der Flamer-Träger ist das erste überlebende „Storm Guardian"); und dreimal
  wurde in eine leere Liste indiziert bzw. `str.index()` benutzt — **sechste bis achte Instanz**
  derselben Lehre, eine Sonde muss ROT machen, nicht abstürzen.
- **Im ECHTEN Spiel belegt** (`verify_save_load.py`, zwei `main()`-Läufe über `selfplay.py`s echte
  Schleife: spielen → Zustand setzen → Save drücken → die Datei per `--load` in ein zweites `main()`
  → die LEBENDEN Objekte fragen):

  | | gefixt | `--neutralize` (Vor-Fix) |
  |---|---|---|
  | Überlebender von `1 Windriders 1 + Warlock Skyrunners` | **Warlock Skyrunner** 1/2 | **Windrider** |
  | Modelle über ihrem Maximum | 0 | 0 (die Klammer) |
  | Avatar of Khaine hat schon geschossen | **True** | False |
  | ...darf nochmal ziehen | **False** | True |
  | `moved_distance_this_turn` | **6.5** | None |
  | `charged_this_turn` | **True** | False |

  Beide Hälften werden GESTELLT statt abgewartet, und der Grund steht im Modulkopf: ein
  MockAgent-Lauf erreicht in einem festen Framebudget verlässlich keine Schussphase (die
  dokumentierte Harness-Grenze), ein passiver Zähler hätte 0 gemeldet und wie ein Bestehen
  ausgesehen. Alles nach dem Setzen — Capture, Datei, Neubau, Restore — ist echt.

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

### Auswählen und BESTÄTIGEN — zwei Takte statt einem

**Ein Klick wählt AUS, erst der Knopf unten entscheidet** (User: "momentan geschieht die auswahl
schon, wenn man draufklickt. ich hätte gerne ein auswahl highlight + button. also erst auswählen,
dann wird die entsprechende kachel gehighlightet und dann auf den auswahl button unten drücken").
Gilt für BEIDE Screens; kein einzelner verirrter Klick entscheidet hier noch etwas.

- **`select()` / `confirm()` sind neu, `choose()` bleibt UNVERÄNDERT** — es tut jetzt beides in
  einem Aufruf. Der Klickpfad geht über die zwei Takte, der programmatische Einzelaufruf bedeutet
  weiter genau das, was er bedeutet hat; kein Aufrufer außerhalb der UI musste angefasst werden.
- **Der Bestätigen-Knopf wird ERST GEZEICHNET, wenn etwas gewählt ist** — dieselbe Konvention, die
  die Fußzeile für den Pager schon hat ("kein Chrome für ein Steuer, das nichts tun kann"). Ein
  ausgegrauter Knopf wäre ein zweites Ding zum Erklären. Was die zwei Takte stattdessen beibringt,
  ist die HINWEISZEILE, die sich mitändert ("… selected - press Confirm below, or pick another").
- **Er NENNT die Wahl** ("CONFIRM: ORKS"), weil eine Auswahl das Blättern ÜBERLEBT: sie ist eine
  Antwort, keine Zeigerposition. Ohne den Namen wäre ein Druck von einer anderen Seite aus
  erschreckend statt eindeutig.
- **Die Auswahlfarbe ist ein anderer FARBTON als der Hover, keine hellere Stufe davon.** Hover
  heißt "der Cursor ist hier" und wandert mit der Maus, Auswahl heißt "das ist deine Antwort" und
  bleibt. Zwei Helligkeiten einer Farbe läsen sich als ein Zustand mit zwei Stufen — genau die
  Verwechslung, die hier abgeschafft wird. Dazu ein Wort **SELECTED** in der Kachelecke: Farbe
  allein lässt einem farbenblinden Leser nur die Rahmen-BREITE.
  - **Eine gewählte Kachel reagiert trotzdem auf Hover** (hellerer Grünton) — sonst wäre
    ausgerechnet die Kachel, die man am ehesten noch einmal anklickt, die einzige ohne Rückmeldung.
    **Erst als Fehler bemerkt, weil der eigene Docstring es versprach und der Code es nicht tat** —
    dieselbe Klasse wie ein Kommentar, der ein Verhalten zusagt, das niemand gebaut hat.
- **`draw_footer()` gibt jetzt einen NAMENSSATZ zurück (`FooterButtons`), kein Tupel.** Das alte
  Tupel wurde positionell gelesen UND geschnitten (`ts.draw_footer(...)[1:]` im Kartenscreen) — ein
  vierter Knopf hätte diesem Aufrufer stillschweigend die falschen Rechtecke gegeben, also
  Fehlerklasse 22 in Reinform. `__slots__` und kein `__getitem__`, damit beides nie zurückkommt.
- **ENTER ist die Tastaturhälfte des Knopfes**, keine Abkürzung an Takt eins vorbei: ohne Auswahl
  tut es nichts.
- **Der Bestätigen-Knopf wird VOR den Kacheln getroffen** — dieselbe Begründung, die die Biom-Reihe
  schon trägt: ein Steuer, das nur antwortet, wenn darüber nichts gepasst hat, ist eine Umbaurunde
  davon entfernt, nie mehr zu antworten.
- **`MapSelectScreen(default=)` hatte gar keinen Leser** und öffnet den Screen jetzt auf der SEITE
  der aktuellen Einstellung. **Vorausgewählt wird bewusst nichts:** eine Kachel, die hervorgehoben
  ist, bevor der Spieler etwas angefasst hat, ließe die Hervorhebung "hier bist du" bedeuten statt
  "das ist deine Antwort".
- **Getestet:** `test_map_select.py` 129 → **150/150** (neuer Abschnitt 4b: die drei Zustände einer
  Kachel gegeneinander auf PIXELN, das Badge, der Namenssatz, und alle vier Fußzeilen-Knöpfe
  überschneidungsfrei und im Fenster bei 1280 — inklusive der Prüfung, dass kein echter Karten- oder
  Armeename den Knopf aus dem Fenster schiebt); `test_army_select.py` **253/253**;
  `test_biomes.py` 98 → **100/100** (der Pin "ein Kartenklick wählt eine Karte" maß das COMMIT und
  ist auf die zwei Takte nachgezogen — seine Aussage, dass die Biom-Reihe keine Kachelklicks
  schluckt, ist unverändert). Neu **`ab_pick_then_confirm.py`: 12 A/B-Sonden, alle beißend** — die
  erste stellt buchstäblich das alte Verhalten wieder her (Kachelklick committet), und wenn die
  Suiten das überleben, prüfen sie die Änderung gar nicht.
- **Im ECHTEN Spiel belegt:** `smoke_setup_screens.py` klickt jetzt als ZWEI Klicks auf zwei Frames
  durch `main()`s echte Schleife und prüft beide Hälften einzeln — dass die Auswahl den Screen
  STEHEN lässt und dass beim Druck auf Confirm wirklich schon etwas gewählt war. 13 → **17/17**;
  `--neutralize` weiterhin rot (0/17).

## Biome (game/biomes.py)

**VIER Biome — City, Desert, Forest, Arena — als vier Knöpfe ganz oben im Kartenauswahl-Screen.**
Die ersten drei sind je DREI BILDER, das vierte ist ZEICHENCODE — siehe `## Das Arena-Biom` unten.
`Biome.folder is None` markiert es, `biomes.is_procedural()` ist die EINE Frage danach, und alles
Übrige (Knopf, Vorschau, Cache, `--biome`, "rein kosmetisch") behandelt alle vier gleich.

Ursprünglich drei (User:
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
  legen. 11/11 → **13/13**; `--neutralize` weiterhin rot (0/13). Er klickt nach KEY, nicht nach
  Position, hat das vierte Biom also gratis überlebt.

## Das Arena-Biom (game/arena_biome.py)

**Das vierte Biom wird GERENDERT statt fotografiert** (User: "ich bin unzufrieden mit dem aussehen
der maps ... dort besteht die map nicht aus sprites, sondern du renderst sie. sie soll aussehen, wie
eine simulations arena. ähnlicher look wie das interface. eventuell mit leichten farbverläufen oder
ein ganz subtiles kariertes muster. natürlich dann unterschiedlich: boden, dense cover, light
cover") — und ist auf Nachtrag der **DEFAULT** ("und dann mach arena biom bitte als default").

- **`config.BIOME` UND `biomes.DEFAULT_BIOME` stehen beide auf `arena`, und das ist Absicht.** Die
  zwei beantworten verschiedene Fragen ("womit starten wir" / "was tun wir mit einem unbekannten
  Wert"), aber die richtige Antwort ist dieselbe: ein veralteter Settings-Wert soll auf dem Brett
  landen, das das Spiel normalerweise zeigt, nicht auf einem anders aussehenden. Im Test gegen
  EINANDER gepinnt, nicht gegen ein Literal.
- **Die alte Begründung für `desert` ist nicht verschwunden, sondern umgezogen.** Sie lautete: die
  drei Desert-Dateien sind byte-identisch mit denen, die früher lose in `Sprites/` lagen, ein
  unangetastetes Setup rendert also exakt das Vor-Biom-Bild. Das gilt UNVERÄNDERT für das
  Desert-BIOM und wird weiter geprüft — `test_biomes.py` Abschnitt 4 setzt das Biom dafür selbst,
  hängt also nie am Default. Nur "was ein unangetastetes Setup öffnet" ist jetzt etwas anderes.

- **Es beantwortet DIESELBEN drei Rollen, nur mit Code.** `sprites.*_texture_path()` gibt für dieses
  Biom `None` — und das ist **nicht** dasselbe `None` wie "Kunst fehlt", auf das der Renderer mit
  einem Flachfüller antwortet. Deshalb fragt der Renderer `is_procedural()` VOR dem Pfad; der Guard
  steht zusätzlich in `_biome_texture_path()`, weil sonst `os.path.join(..., None)` kracht.
  Der Fehlerfall wäre besonders unauffällig: `config.BACKGROUND_COLOR` ist selbst ein dunkles
  Blaugrau, ein unverdrahtetes Arena-Biom sähe also aus wie ein plausibles dunkles Brett —
  deshalb prüft der Test das GITTER, nicht die mittlere Farbe.
- **DREI Nähte im Renderer, jede an `biomes.is_procedural()`**: `_draw_ground()`, das neue
  `_cover_tile(role, board)` und der Wand-Zweig. `_tile_texture()` nimmt jetzt die FERTIGE Kachel
  statt eines Pfades — woher eine Kachel kommt, ist eine eigene Frage mit zwei Antworten, das
  Wrapping/Origin-Alignment/der Masken-Blend sind dieselben. Damit erbt der gezeichnete Pfad den
  hart erkämpften Masken-Alpha-Fix, statt ihn zu duplizieren.
- **REICHT bis auf die Wände, und das ist gemessen statt angenommen.** DENSE-Terrain ist gar keine
  der drei Rollen — es wird in jedem Biom als EIN flaches `OBSTACLE_COLOR` gezeichnet, was
  funktioniert, weil alle drei Fotoböden HELL sind. Auf einem dunklen nicht: Kontrast zum offenen
  Boden **Desert 137, Forest 30, City 22 — Arena mit der geteilten Farbe 11.8**, der schlechteste
  der vier um die Hälfte. Wände blockieren Sichtlinie, sind also das Wichtigste zum Ablesen; die
  Arena malt sie deshalb selbst (`draw_wall()`: Körper plus helle Kante, wie die HUD jedes solide
  Ding zeichnet). **Danach 60.1.** Die Testschranke ist keine Zauberzahl, sondern das SCHLECHTESTE,
  was die ausgelieferten Fotobiome schaffen, im Test selbst berechnet.
- **Die drei Rollen trennen sich über MUSTER zuerst, HELLIGKEIT zweitens** — nicht über Farbton:
  Boden flaches Gitter, Dense Cover ein ORTHOGONALES Plattenraster (am hellsten), Light Cover
  DIAGONALE Schraffur (dunkler, dünner). Zwei unabhängige Achsen, also übersteht die Trennung
  sowohl Farbenblindheit als auch den `TERRAIN_TILE_ALPHA`-Blend. Gemessen: Dense/Boden 32.9,
  Light/Boden 15.3, Light/Dense 17.6 — alle besser als die entsprechenden City- und Forest-Werte.
- **Die Kacheln müssen WRAPPEN**, weil der Renderer sie am Brett-Ursprung ausrichtet: jede Linie
  wird nur an der OBEREN/LINKEN Kante gezogen (die andere Hälfte liefert die Nachbarkachel), und
  die Schraffur-Steigung TEILT die Kachelgröße. Im Test an einem echten Dreier-Streifen geprüft:
  keine doppelt breite Naht-Linie, und die Diagonale wiederholt sich über die Naht ohne einen
  einzigen abweichenden Pixel.
- **Die Arena wählt ihre EIGENE Kachelgröße (3.0")** statt `DENSE_COVER_TILE_SIZE_IN` (4.5")
  wiederzuverwenden: die Renderer-Werte wurden gewählt, damit FOTOGRAFIERTE Pflastersteine
  glaubwürdig groß herauskommen — ein gezeichnetes Raster hat keine solche Vorlage. 3" ist eine
  ganze Zahl 1"-Zellen, jede Plattenkante landet also AUF einer Gitterlinie; 4.5" läge eine halbe
  Zelle daneben (im Test von beiden Seiten gepinnt).
- **Alles in ZOLL, nichts in Pixeln** — das ist der eigentliche Gewinn gegenüber einem vierten
  Bilderordner: dasselbe Gitter auf der Kartenvorschau (~11 px/Zoll) wie im Spiel (~62 px/Zoll),
  im Test an beiden Auflösungen gemessen. Und das Gitter IST das Lineal: 1" (Kohärenz, halbe
  Engagement Range) und 6" (der Mittelkreis, den der Renderer ohnehin zeichnet).
- **Die Palette ist an der HUD verankert, nicht daneben gewählt**: `GROUND_BASE` ist
  `button_style.BOX_BG_COLOR`, `GRID_COLOR` ist `BORDER_NORMAL`, `EDGE_COLOR` ist `BORDER_HOVER`.
  `button_style` wird bewusst NICHT importiert (es liegt unter `game/ui/` und zieht den Panel-Stack
  mit; dieses Modul läuft auf dem Render-Pfad) — die Werte stehen mit ihrer Quelle daneben und
  werden im Test GEGEN `button_style` gepinnt, was das Einzige ist, was der Import gekauft hätte.
- **Die Modelle lesen sich darauf nicht schlechter** — das Risiko eines DUNKLEN Bodens, denn eine
  Base ist nur ein farbiger RING ohne Füllung. Gemessen: eigener Ring 116 (Arena) gegen 117
  (Desert), Gegner 76 gegen 73. Als Prüfung gepinnt, weil "die Modelle verschwinden" genau von hier
  käme.
- **Kosten:** Boden 65 ms (map2) / 121 ms (map1) gegen 36 ms für den Fotopfad, EINMAL je Brettgröße
  (nach Pixelgröße gecacht, weil `map_preview` pro Render ein Wegwerf-`Board` baut). Die statische
  Ebene ist ohnehin pro Szene gecacht.
- **Getestet:** neu `test_arena_biome.py` (**58/58**, sechs Abschnitte) plus **13 A/B-Sonden** an
  der QUELLE, jede kippt genau ihre eigenen Prüfungen; die `is_procedural()`-Sonde kippt LAUT (der
  `os.path.join(..., None)`-Guard). `test_biomes.py` 87 → **97/97** (die "jedes Biom liefert drei
  Dateien"-Schleifen gehören jetzt `PHOTO_KEYS`, und die Arena bekommt die Gegenprobe: sie liefert
  KEINE). `test_ground_texture.py` **38/38** an der neuen `_tile_texture`-Signatur nachgezogen.
  Volle Regression **155 Suiten, ~13562 Prüfungen, 154 grün / 0 rot / 1 bekannt**, alle fünf Smokes
  und `run_tests.py --smoke` komplett grün. **Im ECHTEN Spiel belegt:** `selfplay.py` unter
  `BIOME = "arena"` auf map2 (2500 Frames) und map3 (800 Frames), beide exit 0.
- **VIER eigene Sondenfehler, alle von der Sonde selbst gefunden** — und drei davon sind
  Fehlerklasse 24 in Reinform:
  1. Der Checker-Vergleich prüfte gegen die MODULKONSTANTE, also bewegte die Sonde beide Seiten:
     mit `GROUND_CHECKER_LIFT = 0` blieb die Suite grün. Beide Schranken werden jetzt am BILD
     abgelesen. Zweites Mal dieselbe Tautologie in diesem Repo (siehe T'au-Enhancements).
  2. Die erste Checker-Messung verglich zwei BENACHBARTE 6"-Zellen und maß damit den Gradienten
     mit (1.47 statt 5). Die richtige Isolation sind zwei an der Brettmitte GESPIEGELTE Zellen —
     gleicher Gradient, andere Parität. Danach exakt 4.95/Kanal.
  3. Die Gitter-Erkennung benutzte EINEN Helligkeitsschwellwert für die ganze Zeile — die
     Mittenaufhellung macht dieselbe Linie in der Brettmitte ~18 Punkte heller als am Rand, ein
     fester Schnitt beantwortet also an beiden Enden verschiedene Fragen. Jetzt Linie gegen ihre
     eigene Nachbarlücke.
  4. Die 45°-Prüfung rotierte die Zeile in die FALSCHE Richtung und schlug gegen einwandfreie
     Kunst fehl. Eine verkehrte Richtung sieht hier genauso aus wie ein kaputtes Muster.

## Aufstellungszonen-Markierungen (game/renderer.py)

**Zone des Spielers GRÜN, die des Gegners ROT, beide Markierungen dicker** (User: "nur die
aufstellungszonen müssen sichtbarer sein. mach die markierungen dicker. gegner: rot / spieler:
grün"). Player 1 war ein Blau nahe `OWN_ARMY_COLOR`.

- **Der eigentliche Grund für die Unsichtbarkeit war ein SKALIERUNGSFEHLER, kein zu kleiner Wert.**
  Beide Breiten gingen ROH an `pygame.draw.line()` — auf einer Fläche, die `main.py` mit dem
  Mehrfachen der Bildschirmauflösung rendert. **Gemessen bei Default-Zoom:** die "2-Pixel"-Kontur
  landete auf **0.70** Bildschirmpixeln (map2, 1920×1080) bzw. **0.37** (map1), die "5-Pixel"-
  Kantenmarkierung auf 1.74 bzw. 0.94. Die Zahlen im Quelltext beschrieben eine Linie, die nie
  jemand gesehen hat.
- **Es ist exakt der Fehler, für den `_ring_width()` schon existiert** (er hat
  `TOKEN_INNER_RING_WIDTH` hervorgebracht, und der Konstruktor-Kommentar schreibt ihn aus). Beide
  Konstanten sind jetzt ON-SCREEN-Pixel und gehen dort hindurch; "dicker machen" ist also
  überwiegend, sie in der Breite zu zeichnen, die sie ohnehin behaupteten. 2 → 3 und 5 → 7 kamen
  obendrauf — und genau dieses Obendrauf ist auf Nachtrag wieder abgeräumt (User: "die
  aufstellungszonen linien sind jetzt sehr gut erkennbar, aber mach sie bitte etwas dünner"): jetzt
  **2.4 und 5**, der FIX bleibt. Gemessen 1920×1080/map2: Kontur 3.48 → 2.78 px, Kantenband
  8.35 → 5.92 px, das dickere also am stärksten. **Warum ein Bruch:** `_ring_width()` nimmt einen
  Float, und glatte 2.0 landeten EXAKT auf dem Modell-Basisring (beide 2.44 px) — womit die einzige
  Schranke dieser Arbeit fiele; 2.5 wiederum ist ein `round()`-Gleichstand (bricht auf GERADE, also
  2 px bei Skalierung 1 und 8 bei 3, ein 4x wo die Konstante 3x verspricht).
- **Und die zwei Breiten sind jetzt EINE** (User: "bei den Aufstellungszonen gibt es an den
  spielfeldrändern sehr dicke Linien. können die genau so dick sein wie die innenliegenden
  Linien?"): `BOARD_EDGE_LINE_WIDTH = DEPLOYMENT_ZONE_LINE_WIDTH`, **abgeleitet statt zweimal
  hingeschrieben** — Gleichheit IST die Bitte, und zwei getrennt gepflegte Zahlen sind der Weg, auf
  dem sie aufhört zu gelten. Gemessen 1920×1080/map2: Kantenband **5.92 → 2.78 px**, also exakt die
  Kontur; auf map1 4.30 → 2.06. Der Name bleibt, weil es weiter zwei ROLLEN sind.
  - **"Zuordnung der Spielfeldkanten" überlebt das**, und das ist der Grund, warum die Änderung
    gefahrlos ist: WEM eine Brettkante gehört, sagt die FARBE der Linie und ihre ANWESENHEIT (eine
    Kante, die niemandem gehört, bekommt gar keine) — nie ihre Dicke.
  - **Zwei fremde Pins waren zu Recht rot** und sind umgedreht: „das Kantenband ist das dickere der
    beiden" (jetzt: exakt gleich) und ein Vergleich einer gemessenen Pixelzeile gegen die
    Float-Konstante (jetzt gegen `_ring_width()`, also gegen die wirklich gezeichnete Breite).
    Die Basisring-Schranke steht jetzt AUCH fürs Kantenband ausdrücklich da, statt aus der
    heutigen Gleichheit zu folgen.
  - **Ein Befund vor dem Ausliefern:** die naheliegende Prüfung `BOARD_EDGE_LINE_WIDTH is
    DEPLOYMENT_ZONE_LINE_WIDTH` ist eine TAUTOLOGIE — CPython faltet gleiche Float-Konstanten eines
    Moduls zu EINEM Objekt, `2.4 is 2.4` über zwei Zuweisungen ist also True und die Prüfung
    bestünde für genau die Kopie, die sie verbieten soll. Geprüft wird deshalb der QUELLTEXT.
  - **Getestet:** `test_deployment_zone_markings.py` 50 → **58/58**, neu `ab_zone_edge_width.py`
    (**4 A/B-Sonden, alle beißend** — das fette Kantenband zurück, dieselbe Breite als KOPIE statt
    Ableitung, eine um 0.2 abweichende Breite, und die ungeskalierte Originalfassung).
- **`_draw_inset_edge_line()` bekommt die Breite ÜBERGEBEN** statt sie aus der Konstanten zu lesen:
  nur `Renderer` kennt die Render-Skalierung, und der Einzug wird aus derselben Zahl gebildet wie
  die gezeichnete Linie — aus zwei verschiedenen gerechnet hängt die halbe Linie über der
  Brettkante, was eine 7-Pixel-Markierung wie eine 3er aussehen lässt.
- **Die Schranke im Test ist ein VERHÄLTNIS, keine absolute Zahl**, und das ist gemessen begründet:
  `render_scale × camera` ist `Fläche_px / (Brett_in × PIXELS_PER_INCH)`, also schrumpft auf einem
  kleinen Fenster JEDE On-Screen-Pixel-Angabe dieses Renderers gemeinsam — Modellringe und Schriften
  eingeschlossen (1366×768 map1: das ganze Brett läuft auf 58% von nominal, die Kontur landet dort
  auf 1.8 statt 3.5 px). Eine absolute Untergrenze wäre also gar keine Aussage über die
  Markierungen, sondern über das Fenster. Geprüft wird deshalb: der Fix hat sie mit der
  Render-Skalierung multipliziert, und sie sind dicker als der Modell-Basisring, den der User
  bereits als lesbar akzeptiert hat.
- **Zonenfarbe und Basenfarbe stimmen wieder überein, und das ist eingetragen statt stillschweigend
  repariert:** hier stand, die Spielerzone sei bewusst NICHT die Basenfarbe — das hörte auf zu
  stimmen, als `OWN_ARMY_COLOR` zu Grün zurückging (siehe unten). Beide User-Entscheidungen wollten
  auf der Spielerseite Grün, das Zusammenfallen ist also zweimal bestellt und keine Kollision;
  "grün gehört mir, rot gehört ihm" sagt jetzt an beiden Stellen dasselbe. Die zwei Grüntöne
  bleiben verschieden (Ring (40,200,60) gegen das hellere (80,225,115), 40 auseinander) und liegen
  ohnehin nie nebeneinander — eines ist ein Ring auf einem Modell, das andere eine Linie an einer
  Zonengrenze.
- **Getestet:** neu `test_deployment_zone_markings.py` (**43/43**, vier Abschnitte) plus **acht
  A/B-Sonden**, jede kippt ihre eigenen Prüfungen. **Vorher gab es zu dieser Zeichnung GAR KEINEN
  Test** — 13 562 Prüfungen liefen grün durch eine so sichtbare Änderung, und genau deshalb konnte
  eine 0.37-Pixel-Linie jahrelang dort stehen. `test_deployment_shapes.py` besitzt weiter die
  FORMEN (was drin liegt, welche Brettkante wem gehört), diese Suite das AUSSEHEN.
- **Nebenbefund derselben Sitzung: der Objective-Hover stürzte ab** (User: "NameError: name 'rect'
  is not defined ... beim hovern über das objective info icon"). Vorbestehend, in `HEAD` belegt —
  siehe Fehlerklasse 15s Kehrseite oben für die Ursache und den Wächter. Die zweite Hälfte ist ein
  VERHALTENStest: **nichts in diesem Repo hat je ein Objective gezeichnet**, `draw_objectives()`
  kam in genau einer von 13 600 Prüfungen vor, und die ruft es nicht auf. Neu
  `test_objective_hover_label.py` (**11/11**) fährt jedes Objective jeder Karte unter dem Cursor —
  A/B mit wiederhergestellter Meldung: 6 von 11 fallen, jede nennt den gemeldeten Fehler wörtlich.
  Ein Quell-Wächter allein hätte nur gesagt, dass der Zweig LAUFEN kann, nicht dass das Label
  stimmt (es hängt jetzt nachweislich über dem Icon, an dem es klebt).
- **Zwei eigene Sondenfehler:** die "Vorher"-Zahl wurde zunächst mit der NEUEN Konstante gerechnet
  und schmeichelte der Vor-Fix-Welt um einen halben Pixel (die gelieferten Werte 2 und 5 stehen
  jetzt als eigene Konstanten im Test); und zwei Sonden ließen die Suite ABSTÜRZEN statt rot zu
  werden, weil eine Liste per Entpacken gelesen wurde — dritte Instanz derselben Lehre wie bei den
  `str.index()`-Wächtern.

## Spielerfarbe zurück auf GRÜN (game/renderer.py)

**`OWN_ARMY_COLOR` ist wieder (40, 200, 60)** (User: "ändere die spielerfarbe von spieler 1 wieder
zu grün. blau kann man schlecht erkennen auf blauem grund"). Der frühere Wechsel auf Blau
(60, 120, 240) war eine eigene User-Entscheidung und wird zurückgenommen, weil das ARENA-Biom —
inzwischen der DEFAULT — erst DANACH kam und den Boden mit einem BLAUEN Gitter zeichnet.

- **Der Befund ist die dokumentierte GRENZE des Mittelfarben-Proxys in Reinform.** Gegen den
  arena-BODEN misst das blaue Ring 115.4 und das grüne nur 75.4 — der Proxy nennt also BLAU das
  bessere von beiden, und genau deshalb blieben `test_arena_biome.py`s Ring-Prüfungen grün, während
  niemand seine Modelle fand. Gegen die GITTERLINIE, unter der ein Ring dort wirklich liegt, ist
  Blau **21.7** entfernt bei IDENTISCHEM Rotkanal (60 gegen 60), Grün **71.7**. Gleicher Farbton wie
  die Linien, auf denen es liegt: das ist "blau auf blauem Grund", und keine Boden-gegen-Ring-Zahl
  kann es sehen.
- **75.4 auf diesem Boden ist exakt der Wert von `ENEMY_ARMY_COLOR`** — ein Ring, der dort schon als
  lesbar akzeptiert ist. Und Grün liegt WEITER von `SELECTED_MODEL_COLOR`s Cyan (85.0) als das Blau,
  das es ersetzt (58.3) — dieser Abstand war die einzige Begründung des alten Kommentars für Blau.
- **Die Prüfung, die den Fehler gefangen HÄTTE, ist neu**: jeder Team-Ring muss auch von
  `arena_biome.GRID_COLOR` weg sein (> 40). A/B belegt — mit dem alten Blau nennt sie die Meldung
  wörtlich (`22 from GRID_COLOR`).
- **Die zweite Ring-Prüfung war relativ zum WÜSTEN-Boden formuliert und damit schief:** sie verlangte
  MEHR von einem Ring, der zufällig weit von Wüstensand entfernt liegt. Grün erreicht auf dem
  Arena-Boden dieselben 75 wie das Rot, das dieselbe Prüfung akzeptiert, und wäre allein daran
  gescheitert, auf Sand 88 zu erreichen. Die Schranke ist jetzt das SCHLECHTESTE Ring/Boden-Paar der
  drei fotografierten Biome, im Test berechnet — dieselbe Form wie die Wand-Schranke darüber.
- **Getestet:** `test_arena_biome.py` **60/60**. Volle Regression **162 Suiten, ~14273 Prüfungen,
  161 grün / 0 rot / 1 bekannt**, dazu `smoke_pregame.py map2`, `smoke_log_input.py map2` und
  `selfplay.py map2` — keine Formalie, weil `game/renderer.py` pro Frame läuft.

### Und sie WECHSELN NICHT MEHR: Player 1 grün, Player 2 rot, konstant

**`_token_color()` hing an `turn_tracker.active_player`, die zwei Armeen TAUSCHTEN also die
Farben** (User: "Die Farben der Spieler sollen nicht mehr wechseln, je nachdem wo der Fokus ist.
Sie sollen konstant bleiben. Spieler 1 - grün, Spieler 2 - rot").

- **Das ist kein seltenes Ereignis, und genau darin liegt der Fehler.** `game/turn.py` schreibt
  selbst aus, dass `active_player` ein transientes "wessen Entscheidung ist das gerade" ist — es
  flippt bei JEDEM Verteidiger-Save und jedem reaktiven Stratagem, und nur `turn_owner` trägt
  "wessen Zug". Das Brett wechselte also zweimal pro Schussangriff die Farbe, und das Einzige,
  wofür ein Ring da ist — die zwei Armeen auseinanderhalten — war das Erste, was ausfiel. Die
  laufende `turn_owner`-vs-`active_player`-Konvention oben in Teil 1 ist die Diagnose; hier ist
  sie einmal als Zeichnung aufgetreten.
- **`TOKEN_TEAM_COLORS` ist nach OWNER gekeyt, genau wie `DEPLOYMENT_ZONE_LINE_COLORS`** — das war
  schon immer so gebaut und sagt dieselben zwei Wörter. Die zwei stimmten vorher nur in den Frames
  überein, in denen der Fokus zufällig bei Player 1 lag; jetzt immer.
- **Der Parameter ist ENTFERNT, nicht ignoriert** (`Renderer.draw()`, `_draw_tokens()`,
  `draw_embarked_passengers()`, `_draw_embarked_icon()`, `_token_color()`). `draw()` wird
  positionell gerufen — ein toter Parameter mitten in der Signatur ist Fehlerklasse 22, die auf
  ihren Träger wartet. Sechs Aufrufstellen nachgezogen (zwei in `main.py`, zwei Messskripte; zwei
  weitere reichten ihn schon per Keyword).
- **Im ECHTEN Spiel belegt, und das ist der eigentliche Beweis:** ein Spion an `_token_color()`
  über 1200 Frames `selfplay.py map2` meldet für Player 1 **genau eine** Farbe (40,200,60) und für
  Player 2 **genau eine** (220,40,40). **A/B im echten Spiel mit dem alten Rumpf: BEIDE Spieler
  bekommen BEIDE Farben** — das gemeldete Verhalten, über denselben Lauf.
- **Getestet:** neu `test_player_colors.py` (**23/23**) plus `ab_player_colors.py` (**5 A/B-Sonden,
  alle beißend**; die ganze Vor-Fix-Welt kippt 7 von 23). **Vorher pinnte NICHTS das Verhältnis von
  Ring zu aktivem Spieler** — `test_arena_biome.py` und `test_token_base_fill.py` fassen diese
  Farben an, reichen aber beide ein fest verdrahtetes `"Player 1"`, konnten einen Tausch also gar
  nicht sehen. Die Prüfungen ankern bewusst an den zwei GESPROCHENEN Wörtern (Grünkanal dominiert /
  Rotkanal dominiert), nicht an `TOKEN_TEAM_COLORS` selbst — sonst bewegte eine Sonde beide Seiten
  des Vergleichs und die Tabelle dürfte zwei identische Grautöne enthalten.
- **Gemeinsame Regression dieser drei Änderungen** (Farben, Auswahl-Kasten im Panel, Volks-Grid):
  **173 Suiten, ~15205 Prüfungen, 172 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett
  grün, dazu `smoke_measure_tool.py`, `smoke_end_turn_warning.py`, `smoke_primary_mission.py`,
  `smoke_pregame.py map1`, `smoke_setup_screens.py` (+`--neutralize` weiter rot) und `selfplay.py`
  auf map2 und map3. Keine Formalie: `game/renderer.py` und `game/ui/action_panel.py` laufen beide
  pro Frame.

## Die Fraktions-Badges (game/ui/faction_badge.py, game_status_panel, turn_start_overlay)

**Das Zug-Banner trägt jetzt auch das Fraktionslogo** (User: "es gibt ja den promt, der anzeigt,
wer jetzt am zug ist. 'Player 2, Turn 1' baue dort bitte auch das fraktions Logo ein").

- **29. Extraktion am zweiten Konsumenten:** „wie sieht eine Fraktionskachel aus" (Rahmen,
  Aktiv-Glow, Kunst, Monogramm-Rückfall, Schriftsuche) lag im Game-Status-Panel, solange es die
  einzige Stelle war, die eine zeichnet. Das Panel **re-exportiert** jede Konstante, `_faction_monogram`
  IST jetzt `faction_badge.monogram`, und `_draw_badge`/`_monogram_font` delegieren — seine
  Pixel-Tests sind damit per Konstruktion unverändert (63/63 ohne eine Anpassung).
- **Die Kachel-RECT kommt vom Aufrufer, nicht eine Größe.** Panel 58 px (für eine 200-px-Spalte
  bemessen), Banner **76 px** — es steht in der Bildschirmmitte, hat 460 px zur Verfügung und ist
  einen Klick lang zu sehen. Nur die SCHRIFT wird gesucht, eine größere Kachel kostet also nichts.
- **ÜBER der Überschrift und zentriert, nicht daneben:** `draw_panel_header()` zeichnet eine
  Leiste über die volle Boxbreite, es gibt also keine Seite, auf die eine Kachel passt, ohne sie
  zu überlagern oder die Leiste kürzer zu machen als jede andere Überschrift im Spiel. Die
  Überschrift wird verschoben, indem ihr ein Rect gereicht wird, das UNTER der Kachel beginnt —
  `draw_panel_header()` muss nichts von Badges wissen.
- **Reserviert wird nur, was auch etwas zeigt** (`faction_badge.has_content()`): eine handgebaute
  Squad hat kein Datenblatt und damit keine Fraktion, und ein leeres gerahmtes Quadrat liest sich
  als Kunst, die nicht geladen hat. Ohne Fraktion ist das Banner exakt so hoch wie vorher.
- **`dismiss()` lässt Keyword UND Pfad los.** Sonst trüge das NÄCHSTE Banner — der Zug des anderen
  Spielers — das Wappen der falschen Armee. Eigene Testzeile, eigene A/B-Sonde.
- **`active=True`**, weil das Banner GENAU EINEN Spieler nennt und es seiner ist. Das Panel reicht
  dieselbe Flagge für die transiente „auf wen wartet das Spiel"-Frage — zwei Fragen, je eine
  Antwort pro Aufrufer, und genau deshalb bekommt `faction_badge.draw()` sie übergeben statt sie
  abzuleiten.
- **EINE Ableitung von „wer spielt welches Volk"**, `main.py`s `current_player_factions()`, gelesen
  vom Panel UND vom Banner. Zwei Kopien sind der Weg, auf dem die eine mit einem halbfertigen
  Vorspiel-Roster antwortet, während die andere sich längst gesetzt hat.
- **Getestet:** neu `test_turn_start_overlay.py` (**36/36**, fünf Abschnitte) — **zu diesem Overlay
  gab es vorher GAR KEINEN Test**. Gemessen auf PIXELN statt gegen die Konstanten, die das Layout
  erzeugt haben: die Box wächst wirklich um den reservierten Block, die Tinte liegt IN der Kachel
  und zentriert, die Überschrift liegt DARUNTER, und ein Volk ohne Kunst bekommt sein Monogramm.
  Plus `ab_turn_start_badge.py` (**10 A/B-Sonden, alle beißend**), das beide Suiten fährt — eine
  Änderung am geteilten Modul, die nur einer der zwei Aufrufer bemerkt, ist genau die Drift, gegen
  die die Extraktion gebaut ist.
  - **Ein Befund über den TEST:** die Sonde „der Logopfad wird nie nachgeschlagen" biss ZUERST
    NICHT — nichts unterschied KUNST von MONOGRAMM (beides ist Tinte in der Kachel, und zwei Völker
    unterscheiden sich so oder so). Jetzt wird dasselbe Volk zweimal gerendert und ihm einmal nur
    die Kunst weggenommen.
- **Im ECHTEN Spiel belegt:** `verify_turn_badge.py` fährt `selfplay.py`s echte `main()`-Schleife
  und meldet `Player 1 -> faction 'AELDARI', art 'Aeldari Logo.jpg'`, `Player 2 -> 'NECRONS',
  'Necron Logo.png'`, Kachel **76 px, artwork=True**. `--neutralize` meldet `faction None, art
  None` und **0 gezeichnete Kacheln**. Nichts wird dafür gestellt — das Banner öffnet zu Beginn
  jedes Spielerzuges von selbst, also ist das der seltene Fall, der PASSIV messbar ist.

### Die Badge-Zeile im Game-Status-Panel

**Sie hängt an der bekannten FRAKTION, nicht mehr an vorhandener KUNST** (User, mitten
in einer Aeldari-gegen-Death-Guard-Partie: "das rechte panel sieht wieder zurückgesetzt aus. das
hatten wir mal überarbeitet ua. mit logos der fraktionen").

- **Es war nichts verloren — es war das Alles-oder-nichts-Tor.** `_badge_row()` verlangte von BEIDEN
  Spielern eine Logodatei und ließ sonst die GANZE Gruppe auf ihre Vor-Umbau-Textform zurückfallen.
  Death Guard war die eine gebaute Fraktion ohne Badge, also nahm **ein fehlendes Bild** den goldenen
  Aktiv-Rahmen und die kompakten CP/VP/BF-Spalten mit — beides hat mit Logos nichts zu tun.
  **Reproduziert vor jeder Änderung:** aeldari vs necrons/orks/tau → Badges; aeldari vs death_guard →
  `None`, alte Darstellung. Der Sprite-Ordner-Umzug war NICHT schuld (`_resolve_path()` durchsucht
  die Fraktionsordner, alle vorhandenen Logos lösten auf).
- **Eine Fraktion ohne Kunst bekommt jetzt eine MONOGRAMM-Kachel** (`_faction_monogram()`), gleicher
  Rahmen, gleiche Größe, gleicher Aktiv-Highlight. Die alte Begründung ("eine halb gefüllte Zeile
  liest sich schlechter als die Zeile, die sie ersetzt") galt einer LEEREN Kachel — eine beschriftete
  ist weder leer noch halb gezeichnet, also war das nicht der abgewogene Handel.
- **Immer ZWEI Zeichen**, damit die zwei Kacheln symmetrisch bleiben, egal welche die Kunst
  vermisst: Initialen bei mehreren Wörtern (`DEATH GUARD` → `DG`, `T'AU EMPIRE` → `TE`), die ersten
  zwei Buchstaben bei einem (`AELDARI` → `AE`). Eine einzelne Initiale war die naheliegende erste
  Form und liest sich als Tippfehler.
- **Ein fehlendes KEYWORD lässt die Zeile weiter fallen**, und aus dem einzigen Grund, der bleibt:
  dann gibt es nichts zu zeichnen UND nichts zu schreiben, die Kachel wäre wirklich leer. Das ist der
  Fall einer handgebauten `Squad` ohne Datenblatt.
- **Die Schriftgröße wird GEMESSEN, nicht aus der Kachelhöhe abgeleitet** — ein fettes Zweizeichen-
  Wort ist breiter als hoch, eine nur an der Höhe gewählte Größe liefe seitlich über den Rahmen.
  Gecacht, weil das auf dem Zeichenpfad läuft.
- **Death Guards Logo kam noch in derselben Sitzung** (`Deathguard_Logo.jpg`) — **der Ordner
  gewinnt** wie überall in `sprites.py`: ein Wort mit Unterstrich, wo die anderen vier
  `<Fraktion> Logo` heißen. Damit ist der Platzhalter **von keinem ausgelieferten Roster mehr
  erreichbar** — ein belegter No-op, der als Netz für die nächste Fraktion stehen bleibt und deshalb
  an einem KONSTRUIERTEN Fall geprüft wird.
- **Zwei Befunde über den TEST (Fehlerklasse 24), beide von den eigenen Sonden:**
  1. „jede Fraktion hat Kunst" war über `FACTION_LOGO_KEYS`' EIGENE Schlüssel formuliert und damit
     eine TAUTOLOGIE — den Death-Guard-Eintrag zu löschen ließ die Suite grün, weil das gelöschte
     Keyword dann gar nicht mehr geprüft wird. Gefragt wird jetzt die ARMEELISTE (`ArmyList.
     faction_keyword`), also „kann eine Fraktion, die dieser Build FIELDEN kann, ein Monogramm
     zeigen". Eine sechste Liste ohne Kunst macht die Zeile rot und nennt die Fraktion.
  2. Die Vor-Fix-Sonde ließ die Suite ABSTÜRZEN statt rot zu werden (Indizieren in ein `None`
     gewordenes Row) — **dritte Instanz** derselben Lehre wie die zwei `str.index()`-Wächter.
     Jetzt über eine gepolsterte Kopie, also 55/62 mit sieben namentlichen Fehlern.
- **Getestet:** `test_faction_badges.py` 47 → **62/62** plus **vier A/B-Sonden an der QUELLE**, jede
  kippt ihre eigenen Prüfungen (Tor zurück auf KUNST → 55/62 und die Meldung wörtlich zurück;
  Monogramm nie geblittet → 61; Monogramm auf ein Zeichen → 58; Death-Guard-Eintrag entfernt → 61).
  Zwei fremde Pins sind zu Recht rot geworden und umgedreht — genau die sichtbare Einzeiler-Änderung,
  für die sie gesetzt waren (`test_army_select.py`s `LISTS_WITHOUT_ART` ist jetzt LEER und bleibt als
  Platz für die nächste Fraktion stehen; `test_death_guard_datasheets.py` prüft die DATEI samt ihrer
  abweichenden Schreibweise). Volle Regression **164 Suiten, ~14401 Prüfungen, 163 grün / 0 rot /
  1 bekannt**, alle acht Smokes exit 0.
- **Im ECHTEN Spiel belegt, nicht nur im Test** — das Panel läuft pro Frame in der Renderkette, und
  „gebaut, aber nie GEFÜTTERT" hat dieses Repo sechsmal getroffen: ein Spion an `_draw_badge()` in
  einem echten `selfplay.py map2`-Lauf mit der GEMELDETEN Paarung meldet **2998 Zeichnungen über 1500
  Frames**, beide Fraktionen mit Kunst, und der Highlight wandert zwischen ihnen. Der
  Monogramm-Pfad ebenso, mit zur Laufzeit entferntem Death-Guard-Eintrag: 1598 Zeichnungen, Zeile
  steht, `DEATH GUARD` als Monogramm-Kachel.
  **Harness-Falle dabei:** `import selfplay` führt NICHTS aus (`if __name__ == "__main__"`), der
  Spion meldete erst ein wahrheitsgetreu aussehendes 0 für eine Partie, die nie stattfand — `runpy`
  mit `run_name="__main__"`.

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

## Agile Manoeuvres sind TÜRKIS, nicht violett (game/ui/button_style.py)

**Eine vierte Accent-Palette** (User: "colorcode für agile manouvers ist momentan lila wie
stratagems. soll aber türkis sein. (buttons, überschriften)"). Die vier Agile-Manoeuvre-Knöpfe
trugen `accent="stratagem"` und sagten damit das Falsche über ihren PREIS: eine Agile Manoeuvre
zahlt einen **Battle-Focus-TOKEN**, keine CP — sie ist kein 15.01-Kauf.

- **Türkis und nicht das Default-BLAU**, obwohl blau die naheliegende "gratis"-Farbe wäre: blau
  heißt in diesem Panel "kostet nichts", und eine Manoeuvre ist nicht gratis — sie zehrt an einem
  pro Runde geteilten Vier-Token-Konto. Sie ist eine EIGENE Art von Kosten, bekommt also eine
  eigene Farbe, genau wie violett die der CP ist.
- **Der Farbton ist echtes Türkis (#40E0D0)**, nicht ein vom Default abgerücktes Blaugrün.
  **Gemessen, und die engste Paarung steht ausgeschrieben:** Abstand zum Default-Blau **74.2**, zum
  Confirm-Grün 110.3, zum Violett 176.4. Türkis liegt per Konstruktion ZWISCHEN dem Blau und dem
  Grün dieser Palette, ist also näher an beiden als die beiden aneinander (Blau/Grün 106.4) — das
  ist dem gewünschten Farbton inhärent und kein Versehen. Der Nachbar, der wirklich danebensteht,
  ist das Blau ("Move"/"Advance" sitzen direkt an den Manoeuvre-Knöpfen).
- **Vier Zeichenstellen**, alle gemessen: die drei Bewegungsphasen-Manoeuvres (Swift as the Wind,
  Flitting Shadows, Star Engines) an EINER Stelle, **Sudden Strike an seiner eigenen, in einer
  anderen Phase** — deshalb einzeln geprüft statt als mitgekommen angenommen.

### Die "Überschriften"-Hälfte, und warum sie eine ABLEITUNG bekam

"Überschriften" ist wörtlich dieselbe Stelle wie in der früheren Violett-Bitte: die
`{player} - Decision`-Zeile des `DecisionOverlay`. Die reaktiven Manoeuvres (Fade Back,
Opportunity Seized) öffnen dort einen Prompt, der bis hierher das schlichte Gold trug.

- **`DecisionManager.request()` bekam `is_battle_focus=`** neben `is_stratagem=`. Die zwei sind
  verschiedene REGEL-Fragen ("ist das ein 15.01-CP-Kauf" / "ist das eine Agile Manoeuvre") und
  behalten deshalb ihre eigenen Namen — `battle_focus._raise_offer()`s Kommentar erklärte den
  Unterschied schon, jetzt hat er auch seine positive Hälfte.
- **Aber "welche Farbe hat die Überschrift" ist EINE Frage mit EINER Antwort**, also gibt es
  `DecisionManager.accent` als abgeleitete Property und `decision_overlay.ACCENT_COLORS` als EINE
  Tabelle. Ohne das wäre am Zeichenort ein zweites `if/else` über zwei Flags entstanden — die Form,
  die dieses Repo bei `whole_unit_drag.py` schon einmal zusammengelegt hat. Eine vierte Kategorie
  kostet jetzt eine Tabellenzeile statt eines Zweigs. Die zwei Flags sind per Konstruktion exklusiv
  (ein Stratagem ist keine Agile Manoeuvre), die Reihenfolge arbitriert also nie — sie steht
  trotzdem da, damit sie nicht driften kann.
- **Die 30+ bestehenden `is_stratagem=True`-Aufrufstellen sind unangetastet.**

### Getestet

- `test_battle_focus.py` 168 → **195/195**, neuer Abschnitt 13. Beide Hälften werden dort geprüft,
  **wo sie GEZEICHNET werden**, nicht an der Konstante: die Knöpfe als PIXEL durch das echte
  `ActionPanel` (Manoeuvre-Knöpfe identifiziert wie in Abschnitt 8 — durch ANKLICKEN und schauen,
  welcher einen Token ausgibt, also kann die Prüfung nicht von der Regel abdriften), die Überschrift
  durch das echte `DecisionOverlay` mit einem Angebot, das der echte Pool erhoben hat. **Zwei
  Gegenproben, ohne die der Abschnitt auf einem durchgehend türkisen Panel bestünde:** kein
  Nicht-Manoeuvre-Knopf desselben Renders trägt Türkis, und ein Stratagem-Overlay bleibt violett.
  - **Eigene Scene statt Abschnitt 8s**: dessen Pool ist zu dem Zeitpunkt leergespielt, und ein
    leerer Pool bietet gar keine Manoeuvre-Knöpfe an — der Abschnitt hätte bestanden, indem er
    NICHTS misst.
  - **Ein Wächter benutzte `_PALETTES[...]` und STÜRZTE unter der Lösch-Sonde AB statt rot zu
    werden** — vierte Instanz derselben Lehre (die zwei `str.index()`-Wächter, die gepolsterte
    Zeile in `test_faction_badges.py`). Jetzt `.get()`.
- **Neu `ab_battle_focus_colour.py`: sieben A/B-Sonden an der QUELLE, alle beißend** (Knöpfe zurück
  auf violett → 191/195; Sudden Strike allein → 193; Flag entfernt → 193; Overlay ignoriert den
  Accent → 194; Paletten-Eintrag gelöscht → 191; Türkis auf Default-Blau genudget → 193; die GANZE
  Vor-Fix-Welt → **187/195**).
- Volle Regression **164 Suiten, ~14430 Prüfungen, 163 grün / 0 rot / 1 bekannt**, alle acht Smokes
  exit 0, `selfplay.py map2`.
- **Im ECHTEN Spiel belegt, nicht nur im Test** — `game/ui/action_panel.py` läuft pro Frame, und
  "gebaut, aber nie GEFÜTTERT" hat dieses Repo sechsmal getroffen: ein Spion an
  `button_style.draw_button()` in einem echten `selfplay.py map2`-Lauf mit Aeldari auf BEIDEN Seiten
  meldet **2578 Türkis-Zeichnungen über 3000 Frames**, auf einem echten Manoeuvre-Knopf
  (`Flitting Shadows - no Fire Overwatch at this unit (4 token(s))`), und **null** Violett im ganzen
  Lauf. **A/B im echten Spiel:** mit den Knöpfen zurück auf `accent="stratagem"` sind es **2620
  Violett-Zeichnungen und 0 Türkis** — genau das gemeldete Verhalten.

## Decline-Buttons sind ROT — auch im Overlay (game/decline_option.py)

**Gemeldet:** *"Decline Buttons auch in den overlays rot einfärben."*

- **Der Farbcode stand schon fest, er galt nur nicht überall.** `button_style.py`s eigener
  Docstring schreibt aus, was Rot in dieser HUD heißt ("this button abandons/declines the current
  action"), und das linke Panel hält sich seit Langem daran (26 `accent="danger"`-Stellen: jedes
  Cancel, jedes "Decline Charge"). `DecisionOverlay` — die modale Box, über die ~90 Bruchstellen
  dieses Spiels laufen — malte JEDE Option im selben flachen Grau. Also war ausgerechnet die
  Stelle, an der eine Entscheidung wirklich FÄLLT, die einzige ohne den Farbcode.
- **`game/decline_option.py` ist die eine Definition**, gelesen vom Overlay. Ein PRÄDIKAT auf das
  LABEL, nicht ein Flag an ~100 `request()`-Aufrufstellen — und das ist eine Messung, keine
  Bequemlichkeit: ein vergessenes Flag macht nichts rot, also bleibt der Knopf grau, also ist der
  Fehler exakt der heutige und verrottet still. Die Labels sind ohnehin für Menschen geschrieben
  und sagen "nein" in einem kleinen, geschlossenen Wortschatz.
- **Als PRÄFIXE gematcht**, weil mehrere davon per f-string ihre eigenen Zahlen tragen ("Keep the
  Advance roll (7)") und der Teil, der "nein" sagt, immer vorne steht.
- **Was NICHT rot wird, ist der Punkt:** eine echte Zwei-Wege-Wahl hat gar keinen Nein-Zweig
  ("Leap to Defend" gegen "Into the Fray", `[LETHAL HITS]` gegen `[SUSTAINED HITS 1]`) — die
  Hälfte davon rot zu malen behauptete etwas Falsches über sie.
- **Der Wächter ist eine MENGENDIFFERENZ an der QUELLE** (`test_decline_buttons.py` Abschnitt 3):
  jedes literale Options-Label in `game/` wird per AST eingesammelt und gegen eine erwartete
  Klassifikation gestellt. Ein Verhaltenstest kann eine NEUE Schreibweise von "nein" nicht sehen,
  weil es sie noch nicht gibt; hier wird die Zeile rot, statt dass noch ein grauer Decline gemalt
  wird. Beide Richtungen: eine unklassifizierte Absage UND eine fälschlich rot gemalte echte Wahl.
- **Die Farben kommen aus `button_style`, nicht aus einem zweiten Rot** — Panel und Box können
  damit nicht auseinanderlaufen. Die FORM bleibt die flache Rechteck-Liste des Overlays: das sind
  Antworten in einer Liste, und die Form zu ändern war nicht die Bitte.
- **Nur `decision_overlay` war betroffen** — geprüft, nicht angenommen: die sieben anderen Overlays
  haben gar keine Options-Knöpfe (sie sind Klick-weg-Notices), das Game Menu malt Quit längst rot,
  und der Brett-Pick-Screen des Panels zeichnet seine `skip_options` schon mit `accent="danger"`.
- **Getestet:** neu `test_decline_buttons.py` (**54/54**, vier Abschnitte — Füllung, Rahmen UND
  Textfarbe auf PIXELN durch die ECHTE Box, dazu die Gegenprobe, dass eine Liste aus lauter echten
  Wahlmöglichkeiten gar kein Rot bekommt; ohne die bestünde der Abschnitt auf einem durchgehend
  roten Panel) plus vier A/B-Sonden in `ab_menu_and_decline.py`, alle beißend.
  **Ein eigener Testfehler:** die Textfarbe wurde auf EINER Scanzeile gesucht, und ein
  antialiasiertes Label hat dort nicht zwingend einen Glyphenkern — jetzt über die ganze
  Knopffläche.

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

## Einheiten auf dem Brett wählen, nicht aus einer Liste (game/unit_pick.py)

**Jede Entscheidung, deren Optionen EINHEITEN nennen, wird durch Anklicken der Einheit
beantwortet** (User: "Immer wenn man eine einheit auf dem schlachtfeld wählen muss (zb wall of
mirrors) will ich die einheit nicht aus einer liste wählen, sondern auf dem schlachtfeld. Wie bei
overwatch"). **56 Aufrufstellen** in ~50 Modulen, von Wall of Mirrors über Isha's Fury und
Heroic Intervention bis zu den fünf Mortal-Wound-Fähigkeiten.

- **KEIN zweites Pending-System, und das ist die tragende Entscheidung.** Der naheliegende Bau
  ist ein `UnitPickController` mit eigener Queue; er wurde verworfen, weil er sofort Fragen
  schuldete, die `DecisionManager` längst beantwortet: wer blockiert den Phasenwechsel, welches
  Overlay besitzt den Klick, und wie erreicht `ai/agent_driver.py`s `_maybe_resolve_decision()`
  eine Option (über den INDEX — eine Wahl außerhalb der Queue wäre für die KI unsichtbar, und sie
  stallte auf einem Prompt, den sie nicht sieht). Ein Brett-Pick ist deshalb **keine neue Art von
  Pending, sondern eine ANSICHT auf eine anstehende Entscheidung**, deren Optionen Einheiten
  nennen. `unit_pick.pending()` ist die eine Antwort darauf; vier Leser lesen sie und sonst nichts.
- **Der Tag reitet IM Optionstupel, nicht in einer Parallelliste.** Eine Aufrufstelle schreibt
  `[(sq.name, lambda s=sq: self.use(s), sq) for sq in candidates]` — ein DREI-Tupel, die Einheit
  neben ihrem eigenen Callback. Die erste Fassung war ein `squads=[...]`-Argument und ist die
  deutlich gefährlichere: 56 Stellen hätten je zwei Listen von Hand ausrichten müssen, und eine
  Fehlausrichtung KRACHT NICHT, sie löst einen Klick auf Einheit A in den Callback von Einheit B
  auf. Im Tupel gibt es nichts auszurichten.
- **`options` ist für jeden Leser unverändert** (Label/Callback am selben Index), also sind
  `choose(index)`, das Overlay und der KI-Pfad **per Konstruktion** unberührt — der Grund, warum
  ~50 Module und ihre Suiten ohne eine einzige Anpassung grün blieben.
- **ZWEI ABSAGEN, beide in die sichere Richtung.** `pending()` gibt `None` zurück — der Prompt
  bleibt das gewohnte Listen-Overlay —, wenn (1) eine getaggte Einheit **nicht auf dem Brett**
  steht (Rapid Ingress bietet Einheiten aus den Strategic Reserves an; Solid-image Projection ein
  Redeploy) oder (2) **dieselbe Einheit ZWEIMAL** angeboten wird (Rapid Ingress listet eine
  Einheit mit Homing Beacon einmal für 1 CP und einmal gratis). Sonst wartete das Spiel auf einen
  Klick, der nie kommen kann — **Fehlerklasse 25, die einzige Klasse hier, die ein harter Deadlock
  ist statt eines stillen No-ops.** Der Wächter ist GENERISCH, eine künftige Fähigkeit mit
  Off-Board-Einheit fällt also von selbst auf die Liste zurück. Lebendigkeit wird an den TOKENS
  gefragt, nicht an `squad.models` (Fehlerklasse 12).
- **Der Prompt zieht ins LINKE PANEL, das Overlay zeichnet NICHTS.** Es dimmt das ganze Fenster
  und säße damit auf genau den Einheiten, die angeklickt werden müssen. `_button_rects` wird
  trotzdem GELEERT, bevor es zurückkehrt — sonst schluckte die Knopfliste des letzten Frames
  weiter Klicks hinter einem Bild, das nicht mehr da ist. Genau die Anordnung, die Burden of Trust
  schon hatte.
- **Die Einheiten werden GERINGT, "wie bei overwatch"** — dieselbe `draw_shoot_targets()`, die
  Fire Overwatchs berechtigte Einheiten zeichnet, statt einer zweiten Bildsprache für dieselbe
  Idee. **Burden of Trust gewinnt das dabei mit:** sein alter Panel-Screen hielt in seinem eigenen
  Docstring fest, dass "nothing on the board itself marks which units qualify".
- **Der Klick-Zweig sitzt INNERHALB von `elif decision_manager.is_pending:`**, und das ist keine
  Bequemlichkeit: dieser Zweig schluckt jeden anderen Klick, solange eine Entscheidung offen ist —
  das ist, was einen NICHT-modalen Pick daran hindert, "Next Phase" unter einer unbeantworteten
  Frage anklickbar zu lassen. Die Gefahr, die die modale Box vorher schlicht durch Im-Weg-Stehen
  deckte.
- **Burden of Trust ist mit umgezogen.** Es war der einzige Brett-Pick des Spiels und hatte ein
  eigenes kleines Pending-System (`pending_pick`-Dict, eigener `main.py`-Zweig, eigener
  Panel-Screen, eigener Term in `_board_gesture_blocked`). Alles davon ist weg;
  `request_unit_pick()` ist jetzt eine Delegation an die geteilte Queue. Zwei Mechanismen für eine
  Frage sind genau die Drift, die dieses Repo laufend konsolidiert.
- **DREI Aufrufstellen sind BEWUSST nicht getaggt, jede mit ihrem Grund IM QUELLTEXT**: Rapid
  Ingress (Einheiten in Reserve, plus dieselbe Einheit zweimal) sowie die Objective- und
  Karten-Listen, die gar keine Einheiten sind. **Solid-image Projection stand hier als vierte
  und ist es seit 2026-09-06 nicht mehr**: es bot jede Einheit ZWEIMAL an (einmal je Ziel) und
  ist in zwei Schritte geteilt — Einheit auf dem Brett, dann das Schicksal als Liste. **Combat Embarkation ist getaggt und fällt bei
  zwei Transportern in Reichweite von selbst auf die Liste zurück** — ein Klick sagt "diese
  Einheit", nicht "dieses Fahrzeug".
- **Getestet:** neu `test_unit_pick.py` (**67/67**, sechs Abschnitte) plus `ab_unit_pick.py`
  (**11 A/B-Sonden, alle beißend**; die ganze Vor-Fix-Welt kippt 17 von 67).
  `test_mission_unit_pick.py` **65/65** auf den geteilten Weg umgeschrieben,
  `test_secondary_missions.py` **553/553** nachgezogen.
  - **Abschnitt 6 ist der tragende: eine MENGENDIFFERENZ an der Quelle.** Ein Verhaltenstest kann
    die 57. Aufrufstelle nicht sehen, weil es sie noch nicht gibt. Also wird jede Optionsliste in
    `game/`, deren Label `<Laufvariable>.name` nennt, gegen eine dokumentierte Ausnahmeliste
    geprüft — in BEIDEN Formen, die eine Optionsliste hier annimmt (Comprehension und
    `append` in einer Schleife). Eine neue ungetaggte fällt namentlich durch. Und die
    Ausnahmeliste darf nicht verrotten: ein Eintrag, der keine ungetaggte Liste mehr enthält,
    ist eine abgelaufene Ausrede und fällt ebenfalls durch.
  - **Zwei Befunde über den TEST, beide von den Sonden** (Fehlerklasse 24): der Verdrahtungs-Pin
    prüfte nur den Teilstring `pick.pick(clicked.squad)`, der ein `if False:` überlebt — er pinnt
    jetzt die ganze geführte ANWEISUNG; und drei Sonden ließen die Suiten ABSTÜRZEN statt rot zu
    werden (Indizieren in ein `None` gewordenes Ergebnis), **neunte bis elfte Instanz** derselben
    Lehre. Beide Suiten degradieren jetzt zu ROT.
- **Im ECHTEN Spiel belegt:** neu `smoke_unit_pick.py` (**6/6**, 45 Frames, in `--smoke` mit).
  Es STAGET die Entscheidung selbst und sagt warum: jeder solche Prompt ist reaktiv, ein
  MockAgent-Lauf erreicht keinen zuverlässig (die dokumentierte Harness-Grenze), ein passiver
  Zähler hätte 0 gemeldet und wie ein Bestehen ausgesehen. Alles danach ist echt — gemeldet wird
  `1 Dark Reapers 1 (5 living models)`, Panel-Screen gezeichnet, **5 von 5 Modellen geringt**,
  Overlay deckt das Brett NICHT ab, und **ein ECHTER Klick auf die Einheit löst die Entscheidung
  auf**. `--neutralize` (die Option verliert nur ihre Einheit) kippt **alle sechs**.
  - **Harness-Falle, eine Runde Debugging wert:** die zwei Vorspiel-SCREENS (`MAP_SELECT`,
    `ARMY_SELECT`) fahren eigene Event-Schleifen, deren Frames kein `turn_tracker` haben — ohne
    `config.MAP_SELECT = False` wird der Pump von der Kartenauswahl leergesaugt und `main()` nie
    erreicht. Der Harness meldet dann wahrheitsgetreu aussehende 6000 Frames und ein leeres
    Locals-Dict.
- Volle Regression **179 Suiten, ~15720 Prüfungen, 178 grün / 0 rot / 1 bekannt**.

### Und die rechte Spalte sagt, WAS man da wählt (game/prompt_rule.py)

**Gemeldet:** *"immer wenn ich aufgefordert werde durch eine Fähigkeit etwas auf dem Spielfeld
auszuwählen. zb. bei necron immortals oder deathguard, schreibe die Fähigkeit Regel mit in die
rechte Spalte, sonst weiß ich gar nicht was ich da auswähle."*

- **Die Ursache ist eine bewusste Entscheidung dieses Features, keine Lücke:** ein Brett-Pick
  zeichnet ABSICHTLICH kein Overlay (es säße auf genau den Einheiten, die angeklickt werden
  müssen). Damit war die ganze Erklärung die eine Prompt-Zeile im linken Panel
  (`Living Lightning - strike which unit?`) plus ein paar Ringe.
- **Der Name der Fähigkeit steht schon im Prompt, also wird er ZURÜCKGELESEN statt ein zweites
  Mal erfragt.** Der naheliegende Bau ist `request(..., rule="Living Lightning")` — verworfen an
  einer Messung: 90 `request()`-Aufrufstellen in `game/`, ~55 davon getaggt, jede eine Chance, den
  Namen falsch oder gar nicht zu nennen, und **nichts würde je rot** (das Panel bliebe leer, also
  genau der heutige Zustand). Die Prompts nennen ihre Regel ohnehin, weil sie für Menschen
  geschrieben sind.
  - **Gemessen über alle 90 Prompts × 300 gedruckte Namen der fünf Fraktionen:** 56 Prompts
    enthalten einen gedruckten Regelnamen; der Rest sind Kernregeln ohne Korpus-Eintrag
    ([PRECISION], Reroll-Angebote, Counteroffensive, Missionen, der Vorspiel-Roll-off) — dort gibt
    es nichts zu zeigen. **NULL Prompts matchten zwei VERSCHIEDENE Regeln**; der eine Doppeltreffer
    ist dieselbe Regel unter zwei Überschriften, der Längster-Treffer-Tiebreak arbitriert also nie
    zwischen zwei echten Antworten.
  - **Wortgrenzen, nicht `in`:** ohne sie beantwortet "Guide" ein "Guided". Der kürzeste gedruckte
    Name ist 7 Zeichen ("Sunforge", "Pech'ra"), keiner davon ein Alltagswort.
  - **Die KLAMMER-Variante ist tragend, nicht kosmetisch:** **29 von 264** gedruckten
    Ability-Titeln enden auf `(Psychic)`/`(Aura)`, während der Prompt den nackten Namen schreibt —
    und darunter sind Guide, Doom und Pestilent Fallout, also ausgerechnet Brett-Picks. Ohne den
    Alias hätte genau die Form, für die das Feature existiert, nichts angezeigt.
- **Die Kandidaten sind nur, was auf dem TISCH steht** — die Datenblätter der übergebenen
  Einheiten plus die Detachment-Stratagems der fragenden Armee. Der ganze Korpus würde die
  Fehltreffer-Fläche vergrößern, ohne etwas zu kaufen: eine Regel, die niemand fieldet, kann nicht
  die fragende sein. Gepinnt, indem derselbe Prompt gegen die FALSCHE Armee `None` liefert.
- **Bei einer 19.01-Anbindung zählen die KOMPONENTEN, und das ist die gemeldete Hälfte:** die
  fragende Fähigkeit gehört dem LEADER (Living Lightning ist die des Plasmancer), `squad.datasheet`
  ist die der Immortals. Nur `squad.datasheet` zu lesen findet die Regel nie — eigene A/B-Sonde.
- **`rules_text.ability_blocks()` ist die strukturierte Schwester von `abilities_for()`** —
  dieselbe "ein Parser, zwei Sichten"-Teilung wie `army_rule_text()`/`army_rule_blocks()`. Gesetzt
  wird mit **`game/ui/rules_body.py`**, dem DRITTEN Konsumenten nach Regel-Leser und
  Stratagem-Tooltip, damit "wie werden gedruckte Regeln gesetzt" eine Antwort behält.
- **Seit 2026-09-06 in der LINKEN Spalte, mit Scrollleiste** (User: "'why you are choosing' soll
  in die linke spalte, nicht rechts"). Die ursprüngliche Messung bleibt richtig und ist der
  Grund, warum die Form sich ändern MUSSTE: das rechte Panel endet bei y=248 und hatte selbst
  bei 1280×720 noch 336 px frei, dort war Abschneiden also vertretbar. Die linke Spalte trägt
  gleichzeitig Prompt, Kandidatenliste und den Ausweg — dort muss eine lange Regel LESBAR
  bleiben statt bloß zu passen, also scrollt sie. Unter allem anderen der Pick-Anzeige, als
  Pixel-Gleichheit darüber gepinnt. Siehe `## Elf Meldungen aus drei Partien`.
- **Gecacht** (0.55 ms → 0.006 ms je Aufruf): das läuft pro FRAME, solange der Prompt offen steht,
  und ein Prompt steht so lange offen, wie der Mensch braucht.
- **Getestet:** neu `test_decision_rule_panel.py` (**42/42**, vier Abschnitte — beide gemeldeten
  Fälle, die Klammer-Variante, die Wortgrenze, VERBATIM gegen die eigene `.md`, und der Kasten auf
  PIXELN) plus `ab_decision_rule_panel.py` (**8 A/B-Sonden, alle beißend**; die Immortals-Sonde
  kippt 16 von 42). **Ein fremder Pin wurde zu Recht rot** (`test_unit_pick.py` pinnte die
  Import-ZEILE `from game import unit_pick` wörtlich und ging kaputt, als ein zweites Modul
  dazukam — jetzt der Import statt seiner Formatierung).
- **Im ECHTEN Spiel belegt:** `smoke_unit_pick.py` (6/6 → **7/7**) staget seinen Prompt jetzt mit
  einem WIRKLICH gedruckten Regelnamen der gestagten Einheit (aus dem Korpus gelesen, nicht
  hingeschrieben) und prüft per Spion, dass `main()` dem rechten Panel genau diese Regel reicht:
  `'Wraith Form' vs prompt's 'Wraith Form'`. `--neutralize` kippt weiterhin alle sieben.
- **BENANNTE GRENZE:** der zweite Mechanismus, mit dem man "etwas auf dem Spielfeld auswählt", ist
  die SCHADENS-Zuteilung (`pending_damage_choice`, ~15 Controller — Death Guards Lethal Ichor,
  Spore-laced Shock Waves, Sickening Impact). Die läuft NICHT über den `DecisionManager`, hat gar
  keinen Prompt-Text ("Choose which model takes the wound") und damit keinen Namen zum
  Zurücklesen — dafür bräuchte es eine Controller→Regelname-Tabelle. Bewusst nicht mitgebaut.

## Total-War-Linien-Formation (rechte Maustaste)

**Einheit auswählen, rechte Maustaste halten und ziehen — der Trupp formiert sich entlang der
Linie, die ZIEH-LÄNGE bestimmt die Frontbreite, die Reihenzahl folgt als `ceil(N/Frontbreite)`**
(User: "kennst du das sqad Drag-Movement von den Total war Spielen … jenachdem wie lang die
gedragte linie wird entstehen dann weniger reihen"). Gilt in BEIDEN Phasen: Aufstellung und
Bewegung. Setzt die erstklassige Auswahl darüber voraus — sie ist der GEGENSTAND der Geste.

- **Drei Prämissen widerlegt, alle tragend.** (1) Button 3 ist NICHT sicher vor der Event-Kette:
  ~40 der ~48 Zweige gaten NUR auf Controller-State, ohne `event.type`-Term, also trifft ein
  Rechtsdruck den ersten anstehenden, dessen Rumpf `button == 1` will, und ist weg — Fehlerklasse
  15 zum sechsten Mal. (2) Der Pitch muss PRO PAAR gerechnet werden. (3) Daraus folgt, dass
  `match_models_to_slots()` hier unbrauchbar ist.
- **Pitch pro Paar (`r_i + r_j + LINE_GAP_IN`), gemessen an 21 Necron Warriors + Technomancer:**

  | Frontbreite | 3 | 4 | 5 | 6 | 7 | 8 |
  |---|---|---|---|---|---|---|
  | pro Paar | 8.35" | 6.45" | 5.54" | 6.06" | 7.34" | 8.36" |
  | einheitlich | 12.96" | 9.83" | 9.04" | 9.83" | 11.77" | 13.31" |

  Einheitlich ist die Attached Unit bei JEDER Breite über 09.02s 9" — also nirgends aufstellbar.
  Für homogene Trupps sind beide identisch. **`LINE_GAP_IN = 0.1`, nicht `MODEL_GAP_IN = 1.5`**:
  die Ring-Konvention kostet gemessen jede legale Breite (20 Boyz bei 8 breit: 8.36" gegen 18.26").
- **`match_models_to_slots()` ist gemessen VERWORFEN**, nicht vergessen: sein Vertrag setzt voraus,
  dass die Slot-KOORDINATEN unabhängig davon sind, wer darin steht — mit Paar-Pitch stimmt das
  nicht, und Umverteilen erzeugte in **69 von 133** gemischten Fällen Basen-Überlappungen, also in
  praktisch jeder Attached Unit. Stattdessen „Reihen ausrichten", ordnungserhaltend: **Mittel
  +0.04"** vom Minimax-Optimum bei **0.03 ms statt 0.9–1.9 ms**, und es kreuzt keine Laufwege.
- **Der Docstring ÄNDERT `pack_positions()`' Anti-Linien-Argument ausdrücklich, statt es zu
  löschen**: dessen Argument ist ganz über SUCHE („die Plätze, die etwas taugen, sind genau die mit
  einer Wand daneben"), hier ZEICHNET ein Mensch. Seine drei GARANTIEN gelten weiter und werden
  anders eingelöst — Pro-Modell-Legalität an die Klammern delegiert, keine Squadmate-Überlappung
  **durch Konstruktion** (auditiert: 0 Verstöße in **39 535 Paaren** über 400 zufällige gemischte
  Roster, engster Abstand exakt 0.1000"), Kohärenz ebenfalls (0/200 Blöcke unzusammenhängend).
- **Tiefe wächst ZUM Trupp hin** (Zentroid der `origins`); die Gegenrichtung kostet gemessen Mittel
  +2.24" längsten Laufweg. Liegt der Zentroid auf der Linie, gewinnt die rohe Linksnormale — mit
  dem dokumentierten Nebeneffekt, dass **andersherum ziehen die Seite spiegelt**.
- **`origins` verhindert, dass das Layout auf seiner eigenen Ausgabe frisst**: während eines Drags
  tragen die Tokens die Vorschau des LETZTEN Frames. `MovementController` übergibt `last_waypoint`,
  `SetupController` seinen Gesten-Schnappschuss (`begin_group_drag` → **`begin_drag`** umbenannt,
  zweiter Bedeutungsträger).
- **Beide Controller tragen `apply_line_drag`/`finish_line_drag` unter DEMSELBEN Namen** — wie sie
  schon beide `apply_group_drag` tragen —, also ist das Beenden verzweigungsfrei und ruft **den
  beim DRUCK gefangenen Controller** (Fehlerklasse 9b). Bewegung: live schreiben, weil eine
  Ghost-Vorschau `clamp_move()` duplizieren müsste, um zu zeigen WER NICHT HINKOMMT — die
  geklammerten Positionen SIND die Warnung; `commit_group_drag()` wörtlich wiederverwendet. Set Up:
  `clamp_drag()` pro Modell (validator-bewusst), Front-Rank immer, **committet nichts**.
- **Kein `move_mode`-Tor** — `can_advance()`s „`move_mode is None` ist die ganze Regel" überträgt
  sich nicht (Advance ist eine Regelentscheidung IN einer Bewegung, dies eine Geste, die Modelle
  bewegt), und `apply_group_drag()` hat aus demselben Grund keines. Kein Eintrag in
  `REACTIVE_MOVE_MODES`: die Geste ÖFFNET keine Bewegung.
- **Nichts wird geklemmt, Confirm lehnt ab** (User-Entscheidung) — deshalb nennt das Readout das
  **legale Frontbreiten-Fenster ab dem ersten Frame**, EINMAL beim Druck gesweept (invariant unter
  dem Drag) und mit `finally` restauriert, weil der Sweep die Modelle zum Messen bewegt. Ohne diese
  Zahl wäre die Ablehnung willkürlich: ein 20-Modell-Trupp ist nur 3–8 breit legal.
- **Die Spannweite wird NACH der Klammer gemessen, die Frontbreite davor** (`game/line_drag.py`).
  Das ist die Stelle, an der dieses Feature am ehesten „funktionierend" und falsch ausliefert: die
  gezogene Linie ist in der Bewegungsphase regelmäßig eine Lüge, und die angeforderte Spannweite zu
  melden wäre ein grünes Readout über einer Formation, die abgelehnt wird.
- **`widest_pair()`/`spread_headroom()` nach `game/squad.py`** — vierter Konsument derselben Frage.
  `check_coherency()` geht jetzt hindurch: gemessen **1.01x**, und der heiße KI-Pfad erreicht die
  Stelle ohnehin nie, weil das Owner-Tor darüber den ganzen Sweep für sie überspringt.
  `measure_crowded_movement.py` unverändert bei **65 %**.
- **Verdrahtung: drei Einfügepunkte, KEINER in der Kette.** Druck/Loslassen als eigenes `if` VOR
  der Kette, Neuberechnung als Frame-Poll DAHINTER, Loslass-Failsafe aus
  `pygame.mouse.get_pressed()[2]`. Kein `continue` (das übersprünge `camera.update_pan`). Die Kette
  darf `line_drag_active` LESEN — die Kamera-Sperre muss —, aber die Geste nie HANDHABEN.
  **`pygame.WINDOWFOCUSLOST` kommt dazu**, weil die Poll-Annahme über den Fokusverlust unter dem
  Dummy-Treiber nicht messbar ist: drei Zeilen statt einer unbelegten Annahme.
- **`_board_gesture_blocked()` gated nur den START**, über `_front_notice()` statt einer zweiten
  Overlay-Liste. Die Regel, die dabei aufzuschreiben war: *eine ANSICHT darf nie gegated werden,
  eine AKTION darf es* — Fehlerklasse 15 sagt nicht „nie gaten", sondern „nie VERSEHENTLICH gaten".
- **Getestet:** neu `test_line_drag.py` (**105/105**, fünf Abschnitte; der Überlappungs-Audit ist
  der tragende) und `smoke_line_drag.py` (**13/13**, `--neutralize` fällt 6 von 13). Dazu **13
  A/B-Sonden, alle beißend** — inklusive der zwei, die die PLATZIERUNG beweisen: Poll wie ein
  Ketten-Zweig gegated → der Drag friert unter einem Modal ein; Druck ebenso → 6 von 10 fallen.
  **Drei bissen zuerst nicht, alle drei Befunde über den TEST:** die Reihen-Zentrierung war
  ungeprüft, die Druck-Sonde zielte auf die Suite statt auf den Smoke, und — die teuerste —
  **`testkit` patcht `random.randint` GLOBAL** (über `game.dice.random`), sodass mein
  `random.randint(2, 24)` den Würfel-Default 1 lieferte: jede „Roster" hatte ein Modell, das Audit
  prüfte null Paare und sah dabei bestanden aus. Es benutzt jetzt eine eigene `random.Random`-
  Instanz und zählt zusätzlich, dass es überhaupt etwas untersucht hat.
- Volle Regression **160 Suiten, ~13851 Prüfungen, 159 grün / 0 rot / 1 bekannt**, `run_tests.py
  --smoke` grün, alle sechs Smokes plus vier `--neutralize`-Gegenproben rot, `selfplay.py` auf map2
  und map3.
- **Vorbestehende Flake benannt, nicht mir zugeordnet:** `test_ere_we_go.py` fällt unter dem
  Parallel-Runner sprunghaft aus (~1 von 3), einzeln nie. **An einem HEAD-Worktree A/B belegt:**
  ohne eine einzige Änderung dieser Arbeit fällt es dort in 2 von 4 vollen Sweeps genauso. Nicht
  ursachenaufgeklärt.

### Direkt aus dem Pool / aus den Reserven, ohne Zwischenschritt

**Ein Rechts-Drag auf dem Brett SETZT eine getragene Einheit am Druckpunkt AB und formiert sie in
derselben Geste** (User: "wenn ich in der aufstellungsphase oder bei reserven meine einheiten
platzieren will, dann muss ich sie erstmal auf der map platzieren und kann dann im 2ten schritt
erst die drag-formation benutzen ... kann das direkt aus der reserve heraus funktionieren? ohne
zwischen step?"). **Reproduziert vor der Änderung:** mit einer Einheit im Pool gibt
`begin_line_drag()` **False** — die Geste hatte nur zwei Türen (`setup.PLACING` und eine gewählte
Bewegungsphasen-Einheit), und in beiden muss die Einheit schon auf dem Brett stehen.

- **`begin_line_drag(start_placement=...)` ist die dritte Tür, und sie ist ein CALLBACK.**
  "Welche Einheit wird getragen, und wohin geht sie zurück" ist `main.py`s Frage — der
  Vorspiel-Sequenzer und die Ingress-Regel besitzen je eine Hälfte, keine gehört in einen
  Input-Handler. **Die REIHENFOLGE ist gepinnt**: eine offene Platzierung gewinnt (`SetupController`
  ist Ein-Slot), sonst die getragene Einheit, sonst die Bewegungs-Route. Andersherum unterbräche
  ein liegengebliebener Pick genau die Platzierung, die gerade justiert wird. Und ein `blocked`
  Druck fragt den Callback GAR NICHT — er platziert eine Einheit, und hinter einem Modal darf nichts
  abgestellt werden.
- **`main.py`s `_place_picked_unit()` ist die EINE Antwort auf "wohin geht die getragene Einheit",
  gelesen von allen DREI Gesten**, die sie ablegen können: ein linker Klick aufs Brett, das Ende des
  Links-Drags, und der Rechts-Drag. Drei Kopien wären drei Chancen, `rapid_ingress_controller.
  consume()` (15.07) zu überspringen oder die Karte nach dem Ablegen getragen zu lassen. Erfolg wird
  am CONTROLLER abgelesen (`setup_controller.state == PLACING`), nicht an einem Rückgabewert:
  `start_ingress()` lehnt eine noch nicht berechtigte Ankunft (20.03) still ab.
- **`dragging_reserve_squad` heißt jetzt `picked_reserve_squad`** (Fehlerklasse 11): "wird gezogen"
  hörte auf zu stimmen, als ein schlichter Klick die Karte GETRAGEN lässt. **EIN Flag, nicht
  "gepickt" plus "gehalten"** — alle drei Gesten gehen durch denselben Helfer, also gibt es eine
  Antwort statt drei. Der Geist folgt dem Cursor und die Karte verlässt den Streifen, der Zustand
  ist also nicht zu übersehen; das grün/rote Platzierungs-Overlay läuft unverändert mit.
- **Der linke Klick aufs Brett legt eine getragene Karte ebenfalls ab** — dieselbe
  Klick-dann-Platzieren-Paarung, die der Vorspiel-Pool immer hatte, und der Grund, warum der
  Rechts-Drag überhaupt eine getragene Einheit vorfindet. Gegated auf `_carrying_a_unit()` und nicht
  auf "ist etwas gepickt": ein Zweig, der matcht und dann nichts tut, SCHLUCKT den Klick
  (Fehlerklasse 15 im Kleinen), und die geschluckten Klicks wären genau die, die die laufende
  Platzierung justieren.
- **Zwei Enden, die der längere Pick braucht.** Ein Frame-Poll lässt ihn VERFALLEN, sobald die
  Einheit nicht mehr in `state.reserves` steht oder die Bewegungsphase vorbei ist —
  `can_ingress()` prüft die Runde, aber nie die PHASE (was `reserves_panel_visible`s eigene Notiz
  schon festhält), sonst schmuggelte der nächste Brettklick eine Ankunft in die Schussphase. Und
  **ESC bekommt eine Sprosse**: getragene Karte ablegen → Auswahl loslassen → (heute) Menü. Ohne sie
  müsste ein Fehl-Pick erst platziert und dann per Cancel zurückgeschickt werden.
- **Der AST-Wächter (`test_event_chain_wiring.py` Abschnitt 4) war SCOPE-BLIND, und diese Arbeit hat
  es aufgedeckt.** Er sammelte per `ast.walk()` auch die Locals VERSCHACHTELTER Funktionen als
  main()-Locals; ein `squad = ...` in einem neuen Helfer ließ ihn eine Zeile melden, die in einer
  ANDEREN Funktion steht, deren `squad` ein PARAMETER ist. Er läuft jetzt nur über main()s eigene
  Ebene (gemessen: 23 nur-verschachtelte Namen hören auf, als Locals zu gelten; die geprüften
  `a.b = c`-Anweisungen fallen von 40 auf 39 — die eine ist genau der Fehlalarm) und nimmt die
  KLEINSTE Bindungs-Zeilennummer statt der zuerst durchlaufenen. **Keine Abdeckung verloren:** ob
  ein Name überhaupt gebunden ist, ist Abschnitt 1s Frage; dieser beantwortet nur, ob schon.
  A/B belegt (eine echte Ordnungsverletzung auf main()s Ebene wird weiter mit Zeile und Namen
  gemeldet).
- **Gemessene Grenze, benannt statt überdeckt:** ein MockAgent-Lauf erreicht **gar keinen** echten
  20.04-Moment — 6000 Frames, und `state.reserves` bleibt für Player 1 durchgehend LEER. Die
  Reserven-Hälfte ruht deshalb auf dem ECHTEN `IngressController` in der Suite plus Quell-Wächtern;
  die Kette selbst ist über die Pool-Hälfte belegt, die durch DENSELBEN Helfer geht.
- **Getestet:** `test_line_drag.py` 105 → **146/146** (neuer Abschnitt 4b: der Druck platziert
  wirklich, am PRESS-Punkt, die Reihenfolge in beide Richtungen, ein abgelehnter Callback fällt auf
  die Bewegungs-Route zurück, und der echte `IngressController` als 20.04-Route) plus neu
  `smoke_pool_line_drag.py` (**16/16**, 21 Frames, in `--smoke` mit; `--neutralize` fällt 7 von 12)
  und neu `ab_pool_line_drag.py` (**11 A/B-Sonden, alle beißend**; die ganze Vor-Fix-Welt kippt 15
  von 146).
  - **Drei Befunde über den TEST, alle Fehlerklasse 24:** ein Wächter matchte seinen EIGENEN
    Docstring (der zählt auf, welche Aufrufe der Helfer macht — also blieb die Suite grün,
    nachdem der echte `consume()`-Aufruf gelöscht war; **fünfte Instanz** dieser Lehre, deshalb gibt
    es jetzt `body_of()`, das den Docstring abschneidet); ein `.index()` ließ die Suite ABSTÜRZEN
    statt rot zu werden (**dritte Instanz**, jetzt `find()`); und zwei Prüfungen indizierten in
    Listen, die in der Vor-Fix-Welt leer sind (**vierte Instanz** — rot statt Absturz ist der Punkt
    einer Sonde).
- Volle Regression **166 Suiten, ~14677 Prüfungen, 165 grün / 0 rot / 1 bekannt**, `run_tests.py
  --smoke` grün, alle neun Smokes plus drei `--neutralize`-Gegenproben rot, `selfplay.py` auf map2
  und map3.
- **Fremde Fehlschläge, nicht dieser Arbeit zugeordnet (Fehlerklasse 20):** mitten im Lauf fielen
  `test_army_select.py`, `test_biomes.py` und `test_map_select.py`. Eine PARALLELE Sitzung baute
  gerade einen Confirm-Button in die Auswahl-Screens (316 uncommittete Zeilen in
  `game/ui/army_select.py`, `map_select.py`, `tile_screen.py`, Zeitstempel sekundenaktuell); keine
  der roten Zeilen berührt eine Datei dieser Arbeit, und alle drei waren zwei Minuten später von
  selbst wieder grün.

## Armeen (armies/*.json) und Listenauswahl

**Die ZEHN Listen sind DATEN: je eine `armies/<key>.json`.** Fünf Fraktionen, und die T'au stellen
vier davon, die Aeldari drei (siehe die Tabelle unten). Jede Datei ist vollständig — Name, Fraktion, Armeeregel,
Detachments, Force Disposition und jeder Eintrag —, und `ARMY_LISTS` entsteht aus einem
VERZEICHNIS-SCAN. Nichts davon steht ein zweites Mal im Quelltext; eine Liste, die man zweimal
aufschreibt, driftet.

Parameterisiert ist NUR der Owner (`owner=` plus der Namenspräfix über `unit_name()`), damit ein
Screen jede Liste JEDEM Spieler anbieten kann und ein Spiegelmatch zwei getrennte Armeen ergibt.

**Warum JSON und nicht Python** (User: "aus dem game sollte ja mal irgendwann eine ausführbare
Datei werden. wenn dann jemand eine Armeeliste importiert, sollte ja nicht der Quellcode in
army_lists neu geschrieben werden"): ein Python-Modul wird beim Bauen IN die Executable eingebacken,
ein Importer könnte danach keine Liste hinzufügen, und eine importierte `.py` auszuführen wäre ein
Code-Execution-Pfad. Eine Armeeliste trägt — anders als ein Datenblatt mit seinen
`_equip_*(token)`-Callbacks — keinerlei Verhalten, ist also datentauglich. `game/scene_io.py` ist
das Vorbild bis in die Details: `ARMIES_DIR` wird ZUR AUFRUFZEIT gelesen (der Haken, an dem ein
gepackter Build ein Benutzerverzeichnis setzt), `FORMAT_VERSION` wird laut abgelehnt, `summary()`
gibt `None` für Unlesbares.

**Eine Datenbank wäre falsch, und zwar aus einem projektspezifischen Grund:** die Methodik dieses
Repos hängt an `git diff` (`rules/*.md` existiert genau dafür). Bei 130 Datenblättern und 8 Listen
kauft eine DB nichts und kostet die Diffbarkeit. Der Standard des Genres sind ohnehin Datendateien;
Civ V/VI mit SQLite ist die Ausnahme, und die existiert fürs Mod-Merging über zehntausende Zeilen.

### Die drei Module

| Modul | Frage |
|---|---|
| `game/army_io.py` | laden, schreiben, scannen, VALIDIEREN |
| `game/army_roster.py` | `Unit`/`Leader` und der EINE Builder (vier Pässe) |
| `game/army_lists.py` | Registry, `ArmyList`, `FactionChoice`, `get`/`factions`/`apply_to_config` |

**Der Builder hat VIER PÄSSE, und das ist der Kern des Umbaus:** bauen → Enhancements → anhängen →
registrieren. Vorher registrierte jeder Builder INNERHALB der Bauschleife, und 19.01s `attach()`
muss davor laufen — also fiel jede Attached Unit aus der Tabelle in handgeschriebenen Code, und das
ist bei diesen Listen fast alles. Getrennte Pässe machen das unsagbar-falsch: Pass 2 vergibt, solange
jeder Charakter noch sein EIGENES Squad ist (nach dem Merge ist ein Fireblade eines von elf Modellen
und `grant()` lehnt eine mehrdeutige Einheit zu Recht ab — diese Begründung stand vorher dreimal da),
Pass 4 läuft in Roster-Reihenfolge, weshalb ein Transporter immer vor seinem Passagier registriert
wird. `build_tau_retaliation` hatte die halbe Idee schon (eine `leader`-Spalte in der Tabelle, null
Attach-Blöcke); dies ist sie zu Ende gedacht.

**Ein `register(squad)` für DEPLOY hat GENAU EIN Positionsargument** — vier Aufrufer übergeben ein
einargumentiges Callable (`list.append`), ein "sauber" mitgegebenes `pregame.DEPLOY` wäre ein
`TypeError` in vier Dateien.

### Was die Datei sagt

`datasheet`, `color` (PFLICHT, auch am Leader), `composition_index`, `gear`, `choices`, `leaders`
(eine GEORDNETE Liste — Aeldari hängt Farseer DANN Warlock Conclave an, und `can_attach()` erzwingt
das), `transport` (die `id` eines FRÜHEREN Eintrags), `enhancement`, `note` (freier Text, vom Loader
ignoriert — er ersetzt die Kommentare und überlebt einen Importer-Roundlauf).

`destination` gibt es nicht: EMBARK genau dann, wenn ein `transport` dasteht. `RESERVES` benutzt
keine Liste — das entscheidet der Vorspiel-Schritt.

**Der Validator ist stärker als der `NameError`, den er ersetzt.** Die 182 Wargear-Konstanten WAREN
schon Strings, der JSON-Wert ist wörtlich derselbe. Gemeldet wird jetzt aber ALLES auf einmal, je
mit Eintrag und Korrekturvorschlag ("`'Shild Drone'`. Did you mean `'Shield Drone'`?"). Und er
prüft zwei Dinge, die vorher NICHTS geprüft hat: ein `transport`, der auf einen SPÄTEREN Eintrag
zeigt, und ein Enhancement, dessen Detachment die Liste nicht fieldet — letzteres wurde bis dahin
vergeben, kostete Punkte, und `is_active()` gab still `False` zurück. Die vier handgepflegten
`_TAU_ENHANCEMENTS_*`-Slot-Tabellen samt Whitelist sind damit ersatzlos entfallen; ein Slot, den
nichts matchte, wurde vorher stillschweigend ignoriert.

### Was `tau_recon` am Coldstar aufgedeckt hat

Die erste Liste, die vollständig als Datendatei entstand — und sie hat prompt eine Datenblattlücke
gefunden, genau wie der 2026-09-05-Roster es davor tat.

**Der Commander in Coldstar Battlesuit druckt DREI Menüs**: eine Ersetzung der High-output Burst
Cannon aus zehn Optionen, „bis zu zwei" Drohnen, und „bis zu drei der folgenden" aus derselben
Zehnerliste. Die Engine modellierte das dritte als **drei handgeschnittene Bündel** — eine
`WargearOption` je Kombination, die irgendeine Liste zufällig kaufte (`+ 2x Burst Cannon`,
`+ Cyclic Ion Blaster`, `+ 3x Fusion Blaster`).

Das kann zwei Dinge nicht: eine Auswahl von drei VERSCHIEDENEN Items (Coldstar #1 nimmt Cyclic Ion
Blaster + Missile Pod + Weapon Support System), und die drei Support-Systeme überhaupt — **ein
Weapon Support System ist keine Waffe**, und eine `WargearOption` tauscht Waffe gegen Waffen.

**Der Enforcer Commander hatte die gedruckte Form die ganze Zeit richtig** (`support_menu_gear()`
plus zwei Gear-Gruppen). Der Coldstar hat sie jetzt auch, und die drei Bündel sind GELÖSCHT statt
danebengestellt — zwei Arten, „+ 3 Fusion Blaster" zu sagen, wären genau die Drift, die dieses Repo
konsolidiert. Dazu drei fehlende Waffen-Ersetzungen (Burst Cannon, Cyclic Ion Blaster, Missile Pod).

**Verhaltensneutral bis auf eine Buchführung, am Golden Master abgelesen:** 24 Zeilen bewegen sich,
alle nur im `{gear_names}`-Teil; die Waffen in `[...]` sind auf jeder Zeile byte-identisch, und
keine Einheiten-Zeile (Name, Punkte, Modelle, Transport) bewegt sich. Die vier bestehenden
T'au-Listen wurden dafür von `choices` auf `gear` umgestellt — **18 Waffen**, und der Loader hat
jede einzelne Stelle namentlich gemeldet, statt sie still fallen zu lassen.

**Ein vorbestehender Anzeigefehler fiel dabei auf und ist behoben:** `loadout.model_line_groups()`
hängte `gear_names` unbesehen an die Waffenliste, und `support_menu_gear`s Items SIND Waffen unter
demselben Namen — der Enforcer las „3x Missile Pod, 2x Shield Drone, 3x Missile Pod". Verglichen
wird jetzt gegen die ROHEN Waffennamen (`labels` trägt schon Zähler, ein Set daraus trifft nie).
Ein Gear-Item, dessen Waffe anders heißt, bleibt sichtbar — ein Gun Drone gewährt eine Twin Pulse
Carbine, und ein Shield Drone gar keine Waffe; genau dafür ist `gear_names` da.
**Benannte Restlücke:** eine Waffe, deren Profil einen Modus-Suffix trägt (`Cyclic Ion Blaster -
Standard`), matcht ihr Gear-Label nicht und erscheint weiter zweimal. Das MODELL ist richtig.

### Der Golden Master ist das Dauerwerkzeug

`test_army_rosters.py` + `armies/baseline.txt` fingerprinten **8 Listen × 2 Spieler** in
Registrierungsreihenfolge: Namen, `destination`, Transport-Paarung, Punkte, Modellzahlen, **Farbe
pro Modell**, Profil + Waffen, **Gear-Namen**, 19.01-Komponenten mit Rollen, Enhancements. Eine
Listenänderung ist eine Zeile, dann `--write`, dann den Diff lesen.

Er erfasst so viel, weil das meiste davon sonst UNSICHTBAR ist: ein getauschter Drohnentyp bewegt
weder Punkte noch Waffenzahl noch Totals (A/B belegt: 14 Einheiten / 69 Modelle / 1975 pts vor UND
nach dem Tausch), und beim Transkribieren der ersten Datei wurden prompt zwei Farben falsch geraten.
**Die Migration selbst ist damit belegt: alle acht Listen sind byte-identisch** zu dem, was die
Builder produzierten.

**Kein Hash, sondern Text** — ein Hash sagt "etwas hat sich bewegt" und nichts sonst; der Test
druckt die erste abweichende ZEILE.

### Was der Umbau gekostet und gebracht hat

2094 Zeilen (51 % Prosa) → **988 Zeilen Code plus 1123 Zeilen Daten**, und "Fireblade in die
Breacher" ist EINE Zeile in einer 197-Zeilen-Datei statt einer 25-Zeilen-Schleife plus einer
magischen `+ 4` plus eines Slot-Namens plus dreier Docstring-Stellen.

**Duplikation zwischen Listen ist eine bewusste Ausnahme von Fehlerklasse 10:** eine Armeeliste ist
eine DEKLARATION, kein Code, und zwei Listen, die zufällig Einträge teilen, sind trotzdem zwei
Listen. Der Fall, an dem das entschieden wurde, waren `tau` und `tau_epc` mit zwölf gemeinsamen
Einträgen — unter dem geteilten Builder änderte das Editieren der Kauyon-Pathfinder still auch die
Prototypes-Liste, was bug-förmige Kopplung ist. **`tau_epc` ist am 2026-09-07 zurückgezogen worden**,
das Paar existiert also nicht mehr; die Regel steht, weil das nächste Paar sie wieder braucht, und
der Golden Master pinnt jede Liste einzeln, sodass Kopien nicht unbemerkt driften können.

**Zwei Prosa-Leichen fielen dabei auf, beide vorbestehend:** `build_orks`' Docstring listete "2x
Trukk", die der Builder nie baute (`grep -c TRUKK` = 0), und der Kommentar über `ARMY_LISTS` nannte
zwei Primary Missions "DORMANT", die seit den T'au-Listen gespielt werden.

**`_check_positions` bekam nebenbei einen echten Fix:** sein `wanted` war handgepflegt und in drei
Richtungen inkonsistent (Aeldari verlangte 5 für 11 Einheiten, Kauyon 19 bei 18 verbrauchten,
Orks/Necrons/Death Guard übergaben 0 — weshalb `--no-deployment` auf map3 BESTAND und die ganze
Armee still auf (0,0) stapelte, exakt das Versagen, das der Wächter verhindern soll). Jetzt
`len(roster)`.

- **Der Squad-NAME ist ein Identifier**, keine Dekoration: `ai/agent_driver.py`s Planbefehle
  adressieren Einheiten über den exakten Namen, `game/maps.py`s Teilroster nennen sie, und ein
  Szenen-Snapshot schlüsselt darauf. Deshalb ist die Form `"<Spielerziffer> <Datenblatt> <Kopie>"`
  tragend und `army_lists.unit_name()` die eine Stelle, an der sie gebildet wird. Ein Spiegelmatch
  funktioniert genau deswegen: dieselbe Liste zweimal teilt keinen einzigen Namen.
- **Was eine `ArmyList` außer ihrem Roster trägt**: Fraktions-Keyword (damit `sprites.py` das Badge
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
  - **VIER SCHRITTE, EIN MENSCH.** User: "Aber ich wähle für die KI. Die KI soll nicht selber
    wählen." Also kein Spieler-Schritt und ein KI-Schritt: die Person am Rechner beantwortet alle,
    Player 2s Liste wird der KI ZUGEWIESEN. Der Screen läuft, bevor überhaupt ein Agent existiert,
    und importiert nichts aus `ai/` — als Quellprüfung festgehalten, weil das stärker ist als ein
    Aufrufzähler.
    **Seit dem 2026-09-03-Umbau sind es ZWEI Fragen PRO SPIELER** (User: "ich habe vor pro Volk
    mehrere listen anzulegen. daher muss sich der Volk Auswahl Prozess etwas ändern. erst wählt
    man das Volk und dann kommen die verschiedenen Listen zur Auswahl. also in 2 Stufen") — siehe
    `### Volk zuerst, dann Liste` unten.
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
  - **DER KACHEL-KOPF WIRD AUS SEINEN ECHTEN ZEILEN GEMESSEN** (User mit Screenshot: "Oben
    überlagert sich text"). Zwei Fehler in einem Bild, und 352 Prüfungen sahen keinen von beiden,
    weil nie etwas den Kopf gemessen hat: der NAME wurde umbrochen, aber `_header_height()` nahm
    flache VIER Zeilen an — also schob "T'au Empire (Prototypes)" auf einer Vier-Kachel-Seite die
    drei Zeilen darunter in die Summenzeile; und Detachment- und Dispositions-Zeile wurden GAR
    NICHT umbrochen, also lief "Auxiliary Cadre + Experimental Prototype Cadre (2 DP)" seitlich aus
    der Kachel in die Nachbarin.
    - **`_header_blocks(entry, text_width)` ist die eine Definition** der vier gedruckten Dinge
      (Name, Detachments, Force Disposition, Armeeregel), jedes an der Breite umbrochen, die es
      wirklich hat — gelesen von der HÖHENrechnung UND von `_draw_tile()`. Vorher waren es zwei
      Meinungen, und beide Hälften standen auf dem Schirm.
    - **Worst case über die Seite, nicht pro Kachel** (`self._header_px`, in `layout()` gesetzt):
      jede Kachel beginnt ihr Porträtraster auf derselben Höhe, was zwei Listen erst vergleichbar
      macht — dieselbe Begründung wie `_lay_out_sections()`' reservierte Charakterzeilen.
      Gerechnet über ALLE Listen, nicht nur die der Seite, damit Blättern das Raster nicht bewegt.
    - **Der Schlussterm ist ABGELEITET** statt der bisherigen festen 18: das ist die Summenzeile
      plus ihre Linie, und bei der größeren Label-Schrift waren 18 sieben Pixel zu wenig — die
      Summe wurde über die Armeeregel gemalt. Das war die zweite Überlappung im selben Screenshot.
    - **Getestet:** `test_army_select.py` 352 → **359/359** (Abschnitt 7d, bei 1920×1080 — vier
      Kacheln, also die fotografierte Seite und die schmalste Kachelbreite: keine Zeile läuft über
      ihre Kachel hinaus, keine erreicht die Summenzeile, der gemeldete Name bricht dort wirklich
      um, und alle vier Raster starten gleich hoch). Ein fremder Pin in
      `test_force_dispositions.py` ist zu Recht rot geworden — er matchte die einzelne
      `self.font.render(...)`-Zeile, die es nicht mehr gibt — und prüft jetzt den Blockeintrag.
      Drei A/B-Sonden, alle beißend.
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

### Volk zuerst, dann Liste (2026-09-03)

**Jeder Spieler beantwortet jetzt ZWEI Fragen: erst das Volk, dann eine seiner Listen** — Vorbau
für "pro Volk mehrere Listen". Heute hat jedes Volk genau EINE Liste, die zweite Stufe zeigt also
eine Kachel; das ist die ehrliche Fassung des bestellten Ablaufs und füllt sich, sobald Listen
dazukommen.

- **Die Gruppierung ist ABGELEITET, nirgends zweitgeschrieben.** `ArmyList.faction_keyword` gab es
  schon, und der Anzeigename kommt aus dem `Faction`-Objekt, das die Regeln ohnehin führen
  (`game/factions/faction.py`s `FACTIONS`, nach demselben Keyword gekeyt). Eine zweite Tabelle mit
  Volksnamen neben den Listen wäre genau die Kopie, die dieses Repo laufend konsolidiert — und die
  veralten würde, weil das Keyword das ist, worauf Datenblätter, Badges und Regeln wirklich matchen.
  Neu in `game/army_lists.py`: `FactionChoice`, `factions()`, `lists_for()`, `faction_of()`.
- **`FactionChoice.key` IST das Keyword**, damit eine Kachel einem Volk und einer Liste dieselben
  zwei Fragen stellen kann ("wie heißt dein Key", "welches Badge trägst du"), ohne zu wissen, was
  sie gerade hält.
- **Reihenfolge = `ARMY_LISTS`-Reihenfolge**, nicht alphabetisch: eine zweite Ork-Liste soll die
  erste Stufe nicht umsortieren.
- **EIN Index über `(Spieler, Stufe)`-Paare** statt Spielerindex plus Stufenfeld. Jede Frage nach
  "wo bin ich" — fertig? was macht Back rückgängig? wer ist dran? — ist damit EIN Nachschlagen
  statt zweier, die sich widersprechen können. `_step_items()` ist die eine Stelle, an der sich die
  Stufen im INHALT unterscheiden.
- **Back geht eine STUFE zurück**, nicht einen Spieler — das ist der Sinn der Teilung. Und ein
  Volkswechsel VERWIRFT die darunter schon gewählte Liste, sonst endet Back-dann-vorwärts mit
  Ork-Volk und Aeldari-Liste.
- **DIE VOLKS-KACHELN STEHEN IN EINEM GRID, nicht in einer Reihe** (User: "bei der volkauswahl im
  pregame ist jetzt viel verschwendeter platz, weil die volk kacheln sehr klein sind. die können
  sich in einem grid anordnen statt nur nebeneinander. so sollte die paginierung dann erst sehr
  spät einsetzen").
  - **GEMESSEN vor der Änderung, und das ist der ganze Befund:** eine Reihe dieser kurzen Karten
    füllte **11 %** des Kachelbandes bei 1920×1080 (19 % bei 1280×720), und fünf Völker brauchten
    schon ZWEI Seiten — der Pager arbeitete also, während neun Zehntel des Schirms leer waren.
  - **`ts.tile_rects()` UMBRICHT jetzt in Zeilen**, `rows_that_fit()` und `Paged.fit_grid()` sind
    die vertikalen Zwillinge von `tiles_that_fit()`/`fit_page()`. **Für die zwei Ein-Reihen-Screens
    ist das byte-identisch** — sie reichen `count <= per_row`, also ist `i // per_row` immer 0;
    über 672 Layouts gegen die alte Formel geprüft, **0 Abweichungen**, und `test_map_select.py`
    plus `test_biomes.py` bleiben unberührt.
  - **Der DECKEL bleibt eine Aussage über die BREITE.** `MAX_TILES_PER_PAGE = 4` begründet sich mit
    "ab vier vergleicht man leichter durch Blättern als durch Hinüberschauen" — das gilt dem
    seitlichen Scannen und sagt nichts darüber, eine zweite Zeile darunter zu stapeln. Spalten also
    weiter gedeckelt, Zeilen ungedeckelt.
  - **Kapazität aus der MINDESThöhe, Höhe aus dem Rest**: sonst schrumpfte die Seite jedes Mal, wenn
    eine Karte wächst. Gemessen: eine Seite fasst jetzt **8 bis 28** Kacheln statt 2 bis 4, der
    Pager erscheint also erst ab **9 bis 29** Völkern statt ab 3 bis 5.
  - **Der Block wird VERTIKAL ZENTRIERT** (`ts.grid_block()`): oben angenagelt liest sich ein
    kurzes Grid als eine Reihe an der Decke über einem Loch — genau der gemeldete Eindruck.
  - **Die Karten WACHSEN, aber nur so weit ihr BADGE trägt** — die zweite Hälfte des Satzes ("sehr
    klein"). `FACTION_LOGO_MAX_PX = 132` ist der Deckel, und die Kartenhöhe ist genau die einer
    Karte mit diesem Badge, also wird jeder gewonnene Pixel von KUNST getragen. Damit bleibt die
    ältere Entscheidung dieses Screens intakt ("eine Kachel, die überwiegend leer ist, liest sich
    wie etwas, das nicht lädt") statt umgangen zu werden. `_draw_faction_tile()` leitet die
    Badge-Größe aus dem Rect ZURÜCK ab, also können Layout und Zeichnung nicht zwei Regeln folgen.
    Gemessen: Bandfüllung **11 % → 22 %** (1920×1080), **19 % → 72 %** (1280×720); Badge 72 → 132 px.
  - **Der LISTEN-Schritt bleibt eine Reihe**, und das ist keine Faulheit: seine Kacheln tragen ein
    Porträtraster und sind fast vollhoch (es gibt keine zweite Zeile), und ihre HÖHE hängt davon ab,
    welche Einträge auf der Seite sind — die Seitengröße hinge also von sich selbst ab. Eine
    Volks-Karte hat eine feste Höhe, deshalb ist ihre Kapazität vorab bekannt.
  - **Getestet:** `test_army_select.py` 299 → **331/331**, neuer Abschnitt 7c (Spalten/Zeilen an
    drei Auflösungen, Überschneidungsfreiheit, die Zentrierung als Zahlenpaar, die Kapazität gegen
    24 und 60 künstliche Völker, und das Badge-Wachstum auf PIXELN). Neuer Helfer
    `many_factions(n)` neben `multi_list_faction(n)` — der eine lässt Schritt EINS wachsen, der
    andere Schritt ZWEI. Neu `ab_faction_grid.py` (**9 A/B-Sonden, alle beißend**), darunter eine,
    die absichtlich die geteilte Reihen-Arithmetik bricht und dann `test_map_select.py` rot machen
    MUSS — sonst bewacht nichts das gemeinsame Gerüst.
  - **Sechs fremde Pins in Abschnitt 7b waren zu Recht rot** — und der Befund über den TEST ist der
    interessantere: sie standen unter einer Überschrift, die sagt, Paginierung gehöre "STEP TWO",
    trieben aber ausnahmslos den VOLKS-Schritt. Sie treiben jetzt Listen; 7c treibt Völker.
  - **Ein eigener Testfehler:** "bei vollem Band sitzen die Karten auf der Mindesthöhe" war schlicht
    falsch — vier Zeilen à 104 px lassen von 558 px noch 76 übrig, die verteilt werden. Die Prüfung
    sagt jetzt, was wirklich gilt (tiefere Seite → kürzere Karten, unter dem Deckel, Band gefüllt).
- **Die Volks-Kachel trägt KEIN Porträtraster**: ein Volk hat mehrere Listen, es gibt also keine
  eine Einheitenmenge — und alle gleichzeitig zu zeigen wäre die Bilderwand, gegen die die Teilung
  gerade gebaut wird. Sie zeigt Badge, Name, Armeeregel und die ANZAHL der Listen; die Zahl ist der
  Grund, warum es die Stufe gibt (führt dieses Volk zu einer Wahl oder zu einer Formalität).
- **`choose(listen_key)` beantwortet weiter BEIDE Fragen in EINEM Aufruf.** Das ist, was `--army1`,
  ein Snapshot und die zehn Harnesses brauchen — "gib diesem Spieler diese Liste" bleibt eine
  Anweisung, und der Zwei-Stufen-Weg ist der, den ein MENSCH klickt. Es spult dafür zur Volksfrage
  dieses Spielers zurück, funktioniert also aus beiden Stufen und über Völker hinweg.
  - **Dabei eine selbstgebaute Falle, gefunden und entschärft:** `army_lists.get()` klein­schreibt,
    und ein Volks-Keyword fällt dabei genau auf einen Listen-Key ("AELDARI" → "aeldari"). Die erste
    Fassung des Shortcuts routete darüber und drehte sich unendlich. Jetzt wird `BY_KEY` DIREKT
    gefragt, und `_answer()` ist der einstufige Pfad ohne Shortcut darin — was durch `choose()`
    hereinkam, geht nicht wieder durch `choose()` hinaus.
- **Getestet:** `test_army_select.py` 253 → **291/291**, neuer Abschnitt 4b (die Gruppierung, die
  vier Schritte in Reihenfolge, Back je Stufe, der Volkswechsel-Verwurf, die Ablehnung eines Keys
  aus der falschen Stufe, der Ein-Aufruf-Shortcut aus beiden Stufen, und die Volks-Kachel auf
  PIXELN). Zwei neue Test-Helfer tragen den Umbau: `list_screen()` beantwortet die Volksfrage für
  die Abschnitte, die von LISTEN-Kacheln handeln, und **`multi_list_faction()` baut fünf Listen
  EINES Volkes** — die Form, die der User gerade anlegt, und ab jetzt das, wogegen Pager, geteilte
  Zellgröße und Kachelgeometrie geprüft werden statt gegen fünf Völker.
  `smoke_setup_screens.py` klickt jetzt **vier** Armee-Schritte statt zweier, jeder weiter in zwei
  Takten; die gepinnte Klickfolge steht vollständig da, weil die REIHENFOLGE die Aussage ist.
  Volle Regression **170 Suiten, ~15060 Prüfungen, 169 grün / 0 rot / 1 bekannt**, alle acht Smokes,
  `smoke_setup_screens.py --neutralize` weiter rot.

- **Player 1 — Aeldari, 11 Einheiten, 1910 pts**, **Seer Council + Path of the Outcast** (Default).
  19 Listeneinträge, 71 Modelle. **SECHS** Attached Units (19.01): Farseer + Warlock Conclave in
  Guardian Defenders, Eldrad + Warlock Conclave in Storm Guardians, Jain Zar in Howling Banshees,
  Asurmen in Dire Avengers, Lhykhis in Warp Spiders, Warlock Skyrunner in die Windriders. Dazu
  **Avatar of Khaine**, Dark Reapers, Rangers, Striking Scorpions, Wraithguard.
  **Der Avatar steht ALLEIN, und das ist die Datenblatt-Aussage** — er druckt gar keine
  LEADER-Zeile, `leadable_unit_names()` ist leer und `can_attach()` lehnt jeden der fünf Charaktere
  ab. Der Unterschied zum Warlock Skyrunner ist der Punkt: DER stand eine Revision lang allein, weil
  die Liste keine Windriders fieldete, also aus einem LISTEN-Grund; beide Fälle sind einzeln
  gepinnt, damit der eine nicht wie eine vergessene Anbindung aussieht.
  **Die zwei Gear-Spalten der ARMY-Tabelle sind wieder ungenutzt** — der Shining-Spear-Exarch mit
  seinem Shimmershield war der einzige Eintrag, der sie je gefüllt hat. Sie bleiben stehen, weil sie
  die Form der Tabelle für JEDE Liste sind.
  **Zweite Liste mit einem Detachment-PAAR**, und wie die T'au genau am Budget: Seer Council (2 DP)
  + Path of the Outcast (1 DP) = 3, keiner der beiden druckt einen Exclusion-Tag. **Path of the
  Outcast war eine der sieben "gebaut, deklariert, nicht gefieldet"-Detachments** — der Pin in
  `test_aeldari_detachment_rules.py` ("fields Seer Council and nothing else") ist genau dafür rot
  geworden. Seine Regel ist auf diesem Roster NICHT dormant: Far-Reaching Doom liest
  RANGERS/SHROUD RUNNERS, und die Liste fieldet Rangers — **im echten Spiel belegt**
  (`selfplay.py map2` mit Spion: `PATH_OF_THE_OUTCAST_PLAYERS = ('Player 1',)` und
  `frd.applies` → `['1 Rangers 1']` auf dem gebauten Brett).
  **Die Force Disposition bleibt Priority Assets** (Seer Council), also weiter Secure Asset als
  Primary — das Paar gewährt zwei, die Bitte nannte aber ein Detachment und keine andere Mission.
  Erste Liste hier, bei der die Wahl wirklich zwei verschiedene Antworten hat (das T'au-Paar gewährt
  zweimal dieselbe).
- **Aeldari (Warhost) — `aeldari_warhost`, 10 Listeneinträge, 10 Einheiten, 60 Modelle, 2005 pts**
  (User-Export "1k sc", 2000 pts). **Zweite Aeldari-Liste**, also das zweite Volk mit einer echten
  Wahl in Stufe zwei des Auswahl-Screens. **FÜNF** Attached Units: Asurmen in Dire Avengers,
  Farseer (Enhancement **Timeless Strategist**) + Warlock Conclave in Guardian Defenders, Jain Zar
  in Howling Banshees, **Autarch in Striking Scorpions**, Lhykhis in Warp Spiders. Dazu Avatar of
  Khaine (allein, siehe oben), Falcon, War Walkers, Windriders, Wraithguard.
  - **Warhost allein = 3 DP, also das ganze Budget**, und es gewährt genau Reconnaissance — die
    Force Disposition ist hier KEINE Wahl, und die Primary ist Reconnaissance Sweep.
  - **Sie macht drei Dinge scharf, die vorher "dormant by roster" waren**: das Detachment Warhost
    (Martial Grace), sein Panel-Stratagem, und mit Timeless Strategist das **erste Aeldari-
    Enhancement, das eine ausgelieferte Liste überhaupt kauft** — die anderen 27 bleiben dormant.
    Beide Prüfungen, die das behaupteten, waren auf `get("aeldari")` verengt und blieben deshalb
    GRÜN, während ihre eigene Begründung veraltete (die Mont'ka-Fehlerform); sie sweepen jetzt
    über JEDE ausgelieferte Aeldari-Liste.
  - **EINE Punkte-Abweichung, und es ist die bekannte**: Dire Avengers 75 statt der gedruckten 70
    (`verify_rules_vs_engine.py` führt sie), also 2005 gegen die 2000 des Exports. Jede andere der
    sechzehn Zeilen stimmt auf den Punkt, inklusive Farseer 65 + 15 = 80.
  - **Aspect Shrine Tokens stehen NICHT in der Datei** — sie werden beim Bau als
    `starting strength // 5` vergeben, und die 1/1/2/1 des Exports kommen genau so heraus.
  - **Die Bright Lance der Heavy Weapon Platform ist die DEFAULT-Waffe, keine Option** — die vier
    gedruckten Alternativen sind weiter nicht modelliert (stehende benannte Lücke), und diese Liste
    will zufällig die eine, die es gibt.
  - **Der Export nennt den Avatar WARLORD**; nichts in dieser Engine liest einen Warlord (belegter
    No-op), also steht das in der `note` der Datei und sonst nirgends.
- **Aeldari (Guardian Battlehost) — `aeldari_guardian_battlehost`, 11 Listeneinträge,
  11 Einheiten, 70 Modelle, 2025 pts** (User-Export "1k sc", 1995 pts).
  **Armoured Warhost (1 DP) + Guardian Battlehost (2 DP)**, also ein PAAR genau am Budget, und
  das erste hier, dessen zwei Hälften **verschiedene** Dispositionen gewähren (Reconnaissance
  gegen Take and Hold): die deklarierte **Take and Hold** ist damit eine echte Listenbau-Wahl und
  nicht die einzige Antwort. Primary ist **Battlefield Dominance** — die erste Aeldari-Liste, die
  nicht Secure Asset oder Reconnaissance Sweep spielt.
  - **Erst als Warhost/Reconnaissance angelegt und vom User korrigiert.** Der Roster war richtig
    und ist BYTE-IDENTISCH geblieben — der Golden Master bewegt bei der Korrektur genau zwei
    Zeilen, nämlich die zwei Abschnitts-Überschriften mit dem Key. Das ist der Beleg, dass die
    Änderung ausschließlich Metadaten war.
  - **Beide Detachment-Regeln greifen auf diesem Roster wirklich**, gemessen statt angenommen
    (die Path-of-the-Outcast-Regel dieses Repos): **Skilled Crews** findet die zwei War-Walkers-
    Einheiten (AELDARI VEHICLE), **Defend at All Costs** deckt **49 Modelle in 8 der 11
    Einheiten** ab — und schließt dabei korrekt Asurmen, beide Farseer, Eldrad und alle sechs
    Warlocks aus, weil es PRO KOMPONENTE fragt (ein Farseer, der Guardian Defenders führt, ist
    kein GUARDIAN).
  - **Der erste Roster überhaupt, der denselben Eintrag MEHRFACH fieldet**: zwei Guardian-
    Defenders-Blöcke mit je eigenem Farseer und Warlock Conclave, zwei War Walkers, zwei D-cannon
    Platforms. Auseinandergehalten werden sie allein über die Kopiennummer, die der Builder an den
    Squad-Namen hängt — und das ist der Identifier, den Planbefehle, Teilroster und Snapshots
    adressieren. Im echten Spiel belegt: `1 Guardian Defenders 1/2`, `1 Farseer 1/2`, und die drei
    Conclaves als `1 Warlock Conclave 1/2/3`, über den GANZEN Roster durchgezählt.
  - **Die zwei D-cannon Platforms sind die einzige Stelle, an der die KOPIEN-Staffelung sichtbar
    wird**: 110 für die erste, 125 für die zweite. Der Export druckt beide Zahlen, und die Engine
    trifft sie ohne Zutun — der einzige Aeldari-Eintrag mit `PointsTier(to_unit=1)`.
  - **DREI Punkte-Abweichungen, alle bekannt** (Dire Avengers 150/140, Eldrad 130/120, Storm
    Guardians 110/100), zusammen +30 — daher 2025 gegen die 1995 des Exports. Jede andere Zeile
    stimmt, inklusive der zwei D-cannon-Stufen.
  - **Die zwei Power Swords der Storm Guardians sind per MODELL-INDEX adressiert** (`[4, 5]`), also
    landen sie nicht auf den Guardians, die ihre Shuriken Pistol für Flamer/Fusion Gun abgegeben
    haben. Der Export sagt nicht, welches Modell was trägt — beide Verteilungen sind legal —, also
    folgt das der Entscheidung, die die andere Aeldari-Liste für dasselbe Loadout schon getroffen
    hat.
  - **Das "Serpent shield" des Export-Eintrags ist WARGEAR, keine Waffe** — es steht in der
    `Wargear Abilities`-Spalte des Korpus und gewährt der Einheit 5+ Invulnerable. Gemessen:
    `invulnerable_save.effective_invulnerable_save()` liefert für Plattform UND Storm Guardians 5+,
    es fehlt also nichts, obwohl die Waffenliste des Modells nur die Close Combat Weapon zeigt.
  - **Sie kauft KEIN Enhancement.** Damit steht "1 von 28 gekauft" unverändert, obwohl die
    ausgelieferten Listen jetzt **5 von 8** Detachments deklarieren und **16 von 28** Enhancements
    zu einem gefieldeten Detachment gehören — "gehört zu einem gefieldeten Detachment" und
    "wird gekauft" sind zwei verschiedene Zahlen, und der Abstand zwischen ihnen ist der Punkt.
- **Necrons — 15 Listeneinträge, 9 Einheiten, 68 Modelle, 2020 pts**, Awakened Dynasty. Default für
  Player 2 (`config.PLAYER2_ARMY = "necrons"`). **SECHS** Anbindungen: Overlord in die Lychguard,
  Technomancer in die Necron Warriors, je ein Plasmancer in jede der ZWEI Immortals-Einheiten
  (Gauss / Tesla), Skorpekh Lord in die Skorpekh Destroyers, Lokhust Lord in die Lokhust
  Destroyers. Nur der C'tan Shard steht allein — er hat als einziger Charakter dieser Liste gar
  keine LEADER-Zeile. Vollständig beschrieben im Necron-Abschnitt unter `## Fraktionen`.
- **T'au Empire — FÜNF Listen, und das erste Volk hier mit mehr als einer.** Sie unterscheiden
  sich in Detachment, Enhancements und damit in der Primary Mission:

  | Liste | Detachment(s) | pts | Einträge / Einheiten / Modelle | Primary Mission |
  |---|---|---|---|---|
  | `tau` | Kauyon + Advanced Acquisition Cadre | 2165 | 21 / 18 / 76 | Reconnaissance Sweep |
  | `tau_montka` | Mont'ka | 1975 | 18 / 14 / 69 | Secure Asset |
  | `tau_retaliation` | Retaliation Cadre | 1965 | 16 / 12 / 57 | Unstoppable Force |
  | `tau_recon` | Advanced Acquisition + Auxiliary + Experimental Prototype Cadre | 1985 | 20 / 17 / 78 | Reconnaissance Sweep |

  **`tau_recon` ist die erste Liste überhaupt, die DREI Detachments fieldet** (2026-09-07 als
  App-Export geliefert): 1+1+1 DP ist exakt das Budget, keines der drei druckt einen
  Exclusion-Tag. Sie ist auch die erste, die vollständig als DATENDATEI entstanden ist — alle
  zwanzig gedruckten Preise stimmen auf Anhieb, siehe `### Was `tau_recon` am Coldstar aufgedeckt
  hat` weiter unten.

  **`tau_epc` (Prototypes) wurde am 2026-09-07 auf User-Wunsch zurückgezogen** ("diese liste kann
  weg"). Gemessene Folgen, benannt statt still hingenommen: **Death Trap ist wieder dormant** (sie
  war die einzige mit Disruption), und **Supernova Launcher und Admired Leader haben keinen Träger
  mehr**. Die anderen zwei Experimental-Prototype-Cadre-Enhancements überleben in `tau_recon`, die
  dasselbe Detachment fieldet — `verify_prototype_weapons.py` zeigt dort weiter zwei Upgrades statt
  drei. Mit ihr fiel auch die letzte geteilte Roster-Hälfte weg: die zwölf Einträge, die sie mit
  `tau` teilte, gibt es nur noch einmal.

  Beschrieben in `## Die T'au-Liste (2026-09-05)` weiter unten; das Wichtigste hier: es sind **die
  ersten Listen überhaupt, die ENHANCEMENTS kaufen** (bis dahin nahm jede Liste keins), und mit der
  zweiten wird der Zwei-Stufen-Auswahl-Screen zum ersten Mal echt.
  Drei Anbindungen in den ersten dreien: je ein Cadre Fireblade in eine der zwei Breacher Teams
  (User: "die Fireblades in die Breacher"), beide Paare in je einem Devilfish, und **der Commander
  in Coldstar in die Crisis Sunforge Battlesuits** — die dritte ist nicht gewählt, sondern vom
  gedruckten Text seines Enhancements erzwungen ("while the bearer is leading a unit"). Der
  Ethereal steht weiter allein, weil der User es so gesagt hat. **Die vierte hat VIER
  Anbindungen**, alle vier nachgereicht (User: "die charactere sind keinen squads zugeordnet") —
  siehe `### Die VIERTE T'au-Liste`.
- **Orks — 14 Einheiten, 103 Modelle, 1935 pts**. Attached: Warboss + Painboy im 20er-Boyz-Mob,
  Beastboss in Beast Snagga Boyz (im Kill Rig), Warboss in Mega Armour bei den Meganobz (im
  Battlewagon). Stormboyz und Deffkoptas in Reserve.
- **Death Guard — 16 Listeneinträge, 14 Einheiten nach zwei Anbindungen, 49 Modelle, 2020 pts**,
  Death Lord's Chosen. Die fünfte FRAKTION; Defaults unverändert. Vollständig beschrieben im
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


## Die T'au-Liste (2026-09-05)

**Der vom User gelieferte Roster ersetzt die 2026-08-30-Liste vollständig.** 21 Listeneinträge,
**18 Einheiten** nach drei Anbindungen, **76 Modelle**, Engine-Summe **2165 pts** — die Zahl, die
die Liste selbst druckt.

- **SECHS ENHANCEMENTS, und das ist die eigentliche Neuerung.** Bis hierher hat KEINE Liste dieses
  Projekts eines gekauft; der Mechanismus war gebaut, verdrahtet und wurde ausschließlich mit einer
  eigenen Testtabelle gefahren. Jetzt trägt ihn ein Roster:

  | Kauyon | Advanced Acquisition Cadre |
  |---|---|
  | Through Unity, Devastation (30) → Fireblade 1 | Negation Emitters (15) → Stealth Battlesuits 1 |
  | Precision of the Patient Hunter (15) → Fireblade 2 | Unmasking Suite (15) → Ghostkeel |
  | Exemplar of the Kauyon (20) → Commander in Coldstar | |
  | Solid-image Projection Unit (20) → Ethereal | |

- **Die Enhancement-Vergabe musste umgebaut werden, und der Grund ist eine echte Grenze der alten
  Form.** `_TAU_LIST_ENHANCEMENTS` war `{Detachment: (Name, Träger-Datenblatt)}` — EIN Enhancement
  je Detachment, Träger per Datenblatt gesucht. Diese Liste ist damit nicht ausdrückbar: **ZWEI
  Cadre Fireblades nehmen VERSCHIEDENE Enhancements**, und von **zwei identischen Stealth-Teams**
  nimmt nur EINES eines. Eine Datenblatt-Suche findet jeweils das erste und gäbe still dem
  falschen. Die Vergabe passiert deshalb jetzt **am BAUORT** — der einzigen Stelle, die zwei
  gleiche Squads auseinanderhalten kann. `_grant_tau_enhancement()` lehnt einen Namen ab, den die
  Tabelle nicht nennt: die Tabelle IST die aufgeschriebene Liste, und ein Grant daneben ließe
  Roster und Protokoll (samt Punkten) auseinanderlaufen.
- **DREI Anbindungen (19.01), und zwei davon entscheidet der GEDRUCKTE TEXT, nicht eine Vorliebe:**

      Cadre Fireblade 1 (Through Unity, Devastation)   -> Breacher Team 1
      Cadre Fireblade 2 (Precision of the Patient Hunter) -> Breacher Team 2
      Commander in Coldstar (Exemplar of the Kauyon)   -> Crisis Sunforge Battlesuits

  Exemplar of the Kauyon und Through Unity öffnen beide mit **"while the bearer is leading a
  unit"** — ein allein stehender Träger gibt seine Punkte für nichts aus. Die dritte Anbindung ist
  neu und war vorher gar nicht möglich: **diese Liste fieldet zum ersten Mal eine Crisis-Einheit**,
  und die steht auf der LEADER-Zeile des Coldstar. Die zwei Fireblades setzen die eigene Vorgabe
  des Users fort ("die Fireblades in die Breacher"). **Der Ethereal steht weiter allein** ("der
  ethereal ist solo") — sein Solid-image Projection Unit ist ein armeeweiter Redeploy und braucht
  keine geführte Einheit, es zieht also nichts in die andere Richtung.
- **PUNKTE: alle 21 Einträge stimmen — der erste Roster hier, bei dem NICHTS abweicht.** Die
  Transkription gewinnt weiterhin, sie muss hier nur nirgends. Der Vorgänger wich in zehn
  Einträgen ab; mehrere dieser Datenblätter sind schlicht nicht mehr dabei (The Twin Lance,
  Shadowsun, das zweite Pathfinder Team, die zweite Piranha), und die zwei, die geblieben sind,
  stimmen in ihrer neuen Größe: Devilfish 75 (die alte Liste sagte 85) und Kroot Hounds 45.

### Die ZWEITE T'au-Liste: Mont'ka — ERSETZT am 2026-09-06

**Der User hat den Roster durch einen App-Export ausgetauscht** ("Tau - RC 1k", 1975 pts).
18 Einträge, **14 Einheiten nach vier Anbindungen**, 69 Modelle, **1975 pts** — alle achtzehn
Zeilen stimmen mit der Transkription überein.

Was hier vorher stand, war die Geschichte der ERSTEN Fassung ("fast gleich nur montka und andere
enhancements", 21 Einträge, 2150 pts, geteilter Builder). Der Teil davon, der Bestand hat, steht
unten; der Rest ist ersetzt statt angehängt.

- **SIE IST AUS DEM GETEILTEN BUILDER AUSGEZOGEN, und das ist die strukturelle Änderung.**
  `_build_tau_roster()` existierte, weil die Liste WÖRTLICH der Kauyon-Roster mit einer anderen
  Enhancement-Tabelle war. Die neue Fassung behält Breacher, Devilfish, Fireblades, Broadsides,
  Pathfinder, Riptide und die zwei Stealth-Teams — und lässt Ghostkeel, Hammerhead, Sky Ray,
  Piranha, Kroot Hounds, Vespid und den Ethereal fallen, während Farsight, Darkstrider, The Twin
  Lance und beide Crisis-Einheiten dazukommen. **14 von 21 gemeinsamen Einträgen sind kein
  geteilter Roster**, also hat sie jetzt einen eigenen Builder und `_build_tau_roster()` ist von
  drei Aufrufern auf zwei (Kauyon und Prototypes).
  - **Der Quell-Wächter dafür liest jetzt den AST statt eines Teilstrings.** Die alte Zeile zählte
    `_build_tau_roster(` im Text und kam auf **4**, weil drei Docstrings die Funktion beim Namen
    besprechen — sie beantwortete also „wie oft wird sie ERWÄHNT" statt „wer RUFT sie". Dieselbe
    Guard-matcht-seine-eigene-Erklärung-Falle, die dieses Repo schon zweimal notiert hat. Jetzt
    steht dort die MENGE der aufrufenden Funktionen (`build_tau`, `build_tau_epc`), also die
    eigentliche Behauptung.
- **VIER ANBINDUNGEN, aus ZWEI Quellen — die einzige Stelle, an der diese Liste keine reine
  Transkription ist:**

      Commander Farsight (Warlord)  -> Crisis Sunforge Battlesuits   (Export)
      Commander in Coldstar         -> Crisis Starscythe Battlesuits (Export)
      Cadre Fireblade 1             -> Breacher Team 1               (User)
      Cadre Fireblade 2             -> Breacher Team 2               (User)

  Die ersten zwei nennt zum ersten Mal die QUELLE selbst: der Export druckt eine eigene Überschrift
  „Attached Units" mit der Rolle jedes Modells, statt sie einem Satz des Users zu überlassen.
- **DIE ZWEI FIREBLADES SIND EINE ENTSCHEIDUNG GEGEN DEN EXPORT** (User, 2026-09-06: "bei der Tau
  Montka liste sollen die fireblades die breacher anführen"). Der Export druckt beide unter
  CHARACTERS und preist seine Breacher Teams mit der ungeführten 90 — das ist also ein bewusstes
  Übersteuern, keine Transkription. **Es kostet nichts:** `attach()` summiert die Komponenten, die
  Armeesumme bleibt dieselben 1975, nur die Einheitenzahl bewegt sich (16 → 14). Damit ist auch
  wiederhergestellt, was der Vorgänger-Roster tat (User damals: "die Fireblades in die Breacher").
  - **Genau deshalb sind die PAARUNGEN gepinnt und nicht die Summe:** eine Anbindung, die nichts
    kostet, ist für jede Punkteprüfung unsichtbar.
- **DARKSTRIDER STEHT WEITER ALLEIN**, und er ist der einzige Charakter, der es tut. Seine eigene
  LEADER-Zeile nennt das Pathfinder Team, eine Anbindung wäre also legal — der Export stellt ihn
  unter CHARACTERS, und dazu ist nichts gesagt worden. Als Listen- und nicht als Regelentscheidung
  gepinnt.
- **EIN Enhancement statt vier: Strategic Conqueror auf dem Coldstar** (95 + 15 = die 110 des
  Exports). Jeder andere Charakter steht auf seinem Grundpreis, was die Liste sagen lässt, dass
  sie nichts weiter kauft.
  - **DREI VON MONT'KAS VIER ENHANCEMENTS VERLIEREN IHREN EINZIGEN TRÄGER** — Coordinated
    Exploitation, Exemplar of the Mont'ka und Strike Swiftly sind gebaut, verdrahtet und getestet,
    und ab hier fieldet sie keine ausgelieferte Liste. Derselbe „dormant by construction"-Zustand,
    in dem das Experimental-Prototype-Cadre-Trio war, bevor eine Liste seine Waffen kaufte.
    Benannt und gepinnt, statt zum Wiederentdecken liegen zu lassen. Die frühere Zeile hier
    („Strike Swiftly wirkt wirklich") gilt entsprechend nicht mehr.
  - Der Träger ist am MODELL gepinnt, nicht an der Einheit: nach 19.01 hält sein Trupp vier
    Modelle, und „die Einheit trägt es" bestünde auch mit dem Enhancement auf einem
    Starscythe-Suit.
- **EIN DATENBLATT MUSSTE NACHZIEHEN, und der Fehler war ein Kommentar ohne Code.** Der Pathfinder
  Shas'ui trägt in diesem Export den Semi-automatic Grenade Launcher; die Option war nur auf der
  Mannschaftszeile verdrahtet, **während der Kommentar darüber wörtlich „Offered on BOTH model
  lines" behauptete** und sogar eine Armeeliste zitierte, die genau das kauft. Der gedruckte Text
  sagt „1 MODEL IN THIS UNIT equipped with a pulse carbine", und der Shas'ui trägt eine.
  - **Die Fehlerform ist die gefährliche:** `build_squad()` verwirft einen `choices`-Eintrag, der
    ein (Zeile, Option)-Paar nennt, das das Datenblatt nicht hat — **still**. Die Einheit kommt
    eine Waffe zu kurz und mit korrektem Preis heraus, also überlebt sie jede Punkteprüfung und
    jeden Blick auf die Summe.
  - **BENANNTE GRENZE:** `max_models` gilt PRO ZEILE, die zwei Einträge zusammen erlauben also
    ZWEI Werfer, wo der Text einen erlaubt — dieselbe schon dokumentierte Schwäche von
    `WargearOption`, die keinen zeilenübergreifenden Deckel ausdrücken kann.
- **Die Pathfinder nehmen ION RIFLES statt Rail Rifles**, und das ist der Unterschied zwischen 85
  und den gedruckten 100: beide ersetzen die Pulse Carbine auf drei Modellen, aber Rail Rifles sind
  gratis und Ion Rifles kosten 5 je Stück.
- **Die DROHNEN sind eine eigene Prüfung, weil sonst NICHTS sie fangen kann:** jede ist gratis, ein
  falsches Modell bewegt also weder den Einheitenpreis noch die Armeesumme noch die Waffenzahl.
  Drei haben sich gegenüber der Vorgängerfassung bewegt (Breacher-Shas'ui Gun → Shield, Coldstar
  Marker+Shield → zwei Shields, zweiter Fireblade nackt → zwei Gun Drones), und **eine A/B-Sonde,
  die eine davon zurückdrehte, war SILENT**, bis der Test die Drohnen Modell für Modell pinnte —
  ein Befund über den TEST, wie er im Buche steht.
- **Die FORCE DISPOSITION ist unverändert und weiter abgeleitet, nicht gewählt:** Mont'ka erlaubt
  genau Priority Assets, also spielt die Liste **Secure Asset**. 3 DP allein füllen das Budget.
- **Jede Breacher-Einheit fährt mit ihrem Fireblade in ihrem EIGENEN Devilfish** (11 von 12
  Plätzen). Der Export nennt zwei DEDICATED TRANSPORTS und sagt nicht, wer darin sitzt — dieselbe
  Lücke wie bei jedem früheren Roster; die Breacher sind weiter die einzige Einheit, deren
  10"-Pulse-Blaster ohne Transport unbrauchbar ist. Die Zuordnung wird über den ECHTEN
  `register`-Callback geprüft, weil `preview_squads()` das Ziel wegwirft.
- **DER WARLORD ist Farsight, und nichts liest das** — dieselbe belegte No-op wie Supreme Commander
  und „cannot be your WARLORD". Aufgeschrieben, weil der Export es sagt.
- **Getestet:** `test_tau_enhancements.py` 308 → **333/333** (Abschnitt 9b vollständig neu
  geschrieben) plus neu `ab_montka_roster.py` (**10 A/B-Sonden, alle beißend**; „zurück auf den
  geteilten Builder" kippt 14 Prüfungen, „die Fireblades führen die Breacher nicht mehr" fünf). Volle Regression **184 Suiten, ~16236 Prüfungen, 183 grün
  / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett grün.
- **Im ECHTEN Spiel belegt:** `selfplay.py map2` mit `tau_montka` auf BEIDEN Seiten protokolliert
  `[primary] Player 1 plays Secure Asset (Force Disposition: Priority Assets)`, alle VIER
  Anbindungen als `is one attached unit (19.01)` — inklusive
  `1 Breacher Team 1 + Cadre Fireblade` — und `Commander in Coldstar Battlesuit in 1 Crisis Starscythe
  Battlesuits 1 + Commander in Coldstar Battlesuit carries the Strategic Conqueror Enhancement
  (15 pts).`
- **BENANNT, nicht mitgeändert:** die KI stellt die Breacher zu Fuß auf, statt den Transport-Hinweis
  zu befolgen — ihr Declare-Battle-Formations-Schritt entscheidet Transporte selbst
  (`TRANSPORT_PASSENGER_PRIORITY`). **Vorbestehend und nicht dieser Änderung zuzuordnen**: die
  Kauyon-Liste verhält sich im selben Lauf identisch. Der Hinweis gilt dem MENSCHEN.

**Was von der ersten Fassung Bestand hat:** mit ihr wurde der ZWEI-STUFEN-SCREEN zum ersten Mal
echt. Der „erst das Volk, dann die Liste"-Fluss wurde für „ich habe vor pro Volk mehrere listen
anzulegen" gebaut und hatte bis dahin nur eine KÜNSTLICHE Registry (`multi_list_faction()`) zum
Gruppieren; der Helfer bleibt für das, was ein echtes Paar nicht erreicht (der Pager braucht mehr
Kacheln als eine Seite trägt).

### Die DRITTE T'au-Liste: Prototypes (2026-09-05) — ZURÜCKGEZOGEN 2026-09-07

**Diese Liste gibt es nicht mehr** (User: "diese liste kann weg"). Was mit ihr ging, steht im
T'au-Listenblock weiter oben: Death Trap ist wieder dormant, Supernova Launcher und Admired Leader
haben keinen Träger mehr.

**Der Abschnitt bleibt wegen EINER Erkenntnis stehen, und die ist über die Arbeitsweise, nicht über
die Liste:** ein Enhancement kann vollständig verdrahtet und trotzdem unerreichbar sein, wenn kein
Roster seine Vorbedingung erfüllt.

Hier stand außerdem, die drei Coldstar-Waffenersetzungen gäbe es, "weil diese Liste sie gekauft
hat". **Das war falsch herum und ist korrigiert** (User: "wieso existiert etwas, weil eine liste es
benutzt?"). Ein Datenblatt ist eine TRANSKRIPTION des gedruckten GW-Blatts; welche Optionen eine
Liste kauft, hat mit der Frage, welche EXISTIEREN, nichts zu tun. Die drei existieren, weil sie
gedruckt sind — die Liste hat nur aufgedeckt, dass sie fehlten. Gemessen: **3 von 18 T'au-
Datenblättern mit Wargear-Menü kannten weniger Optionen, als gedruckt sind.** Der Cadre Fireblade
war der reine Fall (drei gedruckte Drohnen, eine modelliert, mit "since only Gun Drone was ever
asked for on this model" als Begründung im Quelltext) und ist behoben; die anderen zwei sind
Coldstar und Enforcer, denen in Menü 1 die drei Support-Systeme fehlen — und das ist eine echte
strukturelle Grenze, keine Nachlässigkeit: eine `WargearOption` tauscht Waffen gegen Waffen und
kann kein Profil-Flag setzen.

**Auxiliary Cadre + Experimental Prototype Cadre, 2310 pts** (User: "danach diese zusätzliche
Liste die 2 weiteren coldstars sind solo"). 23 Einträge, 20 Einheiten, 78 Modelle — derselbe Kern
wie die anderen zwei plus **zwei weitere Commanders in Coldstar Battlesuit**.

- **SIE MACHT EXPERIMENTAL PROTOTYPE CADRE ÜBERHAUPT ERST ERREICHBAR.** CLAUDE.md hielt hier fest:
  *"Experimental Prototype Cadre bekäme NICHTS ... alle drei seiner Enhancements verbessern eine
  benannte Waffe, und kein Modell dieser Liste trägt T'au Flamer, Plasma Rifle oder Airbursting
  Fragmentation Projector."* Diese Liste rüstet genau die drei aus, einen je Commander — die
  Enhancements waren also **per Konstruktion dormant**, und der Grund war der Roster, nicht die
  Verdrahtung. **Gemessen, dass sie wirklich greifen:** Plasma Rifle S8/AP-3/D3 → **S10/AP-4/D4**,
  T'au Flamer S4/AP0/D1 → **S6/AP-1/D2**, Airbursting S3/AP0/D1 → **S6/AP-1/D2**.
- **DEATH TRAP wird zum ersten Mal von einem ausgelieferten Roster GESPIELT.** Die Primary-Mission-
  Karte war gebaut, getestet und dormant; `test_force_dispositions.py`s Pin ("...leaving these two
  dormant") ist genau dafür rot geworden. Es blieb eine dormant — Unstoppable Force, bis die
  VIERTE Liste sie eine Stunde später auch noch holte.
  Die Disposition ist hier eine WAHL — Auxiliary Cadre gewährt Disruption, Experimental Prototype
  Cadre Priority Assets, und die Liste deklariert Disruption.
- **Sie ist die erste Liste, die das DP-Budget NICHT ausschöpft:** 1 + 1 von 3. Das Budget ist eine
  Obergrenze, keine Zielmarke — bis hierher hat jede Liste zufällig genau 3 ausgegeben.
- **Der Builder trägt jetzt eine COMMANDER-TABELLE** statt eines einzelnen Commanders:
  `(Slot, Waffenwahl, führt-die-Sunforge)` je Eintrag. Die zwei Listen mit einem Commander
  bekommen sie als Default, lesen sich also unverändert. Der ERSTE führt die Crisis Sunforge, die
  anderen stehen allein (User-Vorgabe) — und nichts zieht dagegen: alle drei EPC-Enhancements
  wirken auf die eigene Waffe des Trägers, brauchen also keine geführte Einheit.
- **Beide Fireblades nehmen NICHTS**, und das ist die Liste: beide stehen zum Grundpreis 50. Keines
  der zwei Detachments hat ein Enhancement, das ein Fireblade tragen könnte — Admired Leader geht
  auf den Ethereal, die anderen drei sind BATTLESUIT-only.
- **Drei neue Waffenoptionen am Coldstar-Datenblatt** (Plasma Rifle, T'au Flamer, Airbursting
  Fragmentation Projector als Ersatz der High-output Burst Cannon). Alle drei stehen im gedruckten
  Menü; sie fehlten, weil sie bis hierher niemand gekauft hat.
- **Getestet:** `test_tau_enhancements.py` 267 → **283/283** (neuer Abschnitt 9c: die drei
  Commander mit ihren drei Waffen, dass die Upgrades die Waffen wirklich erreichen, die zwei
  allein stehenden, und die Punkte als Gleichung gegen die anderen Listen);
  `test_force_dispositions.py` **151/151** (vier von fünf Missionen erreicht, Death Trap namentlich
  der Prototypes-Liste zugeordnet); `test_army_select.py` **349/349** (drei T'au-Listen im
  Zwei-Stufen-Screen). Volle Regression **184 Suiten, ~16082 Prüfungen, 183 grün / 0 rot /
  1 bekannt**, `smoke_setup_screens.py` und `smoke_pregame.py map2`.
- **Im ECHTEN Spiel belegt:** `selfplay.py map2` mit `tau_epc` auf beiden Seiten protokolliert
  `[primary] Player 1 plays Death Trap (Force Disposition: Disruption)` und alle vier
  Enhancements auf ihren Trägern.

### Die VIERTE T'au-Liste: Retaliation Cadre (2026-09-05)

**Retaliation Cadre allein, 3 DP, 1965 pts** (User: "jetzt noch retaliation cadre Liste
zusätzlich"). 16 Einträge, **12 Einheiten nach vier Anbindungen**, 57 Modelle — und **die einzige T'au-Liste, die den Kern
der anderen drei NICHT teilt**: keine Breacher Teams, keine Devilfish, kein Ethereal, keine
Fireblades. Ein Battlesuit-Heer aus fünf Charakteren und sechs Crisis-Einheiten, also mit eigenem
Builder statt einer Tabelle für den geteilten.

- **UNSTOPPABLE FORCE wird damit gespielt** — die LETZTE der fünf Primary Missions, die kein
  ausgeliefertes Roster je erreicht hatte. Zusammen mit der Prototypes-Liste (Death Trap) ist die
  dormant-Spalte damit **leer**; `test_force_dispositions.py` pinnt jetzt "keine dormant" statt
  einer Namensliste.
- **VIER ANBINDUNGEN (19.01), alle vier vom User benannt** (nachgereicht: "die charactere sind
  keinen squads zugeordnet. ich dachte das wäre im text schon enthalten ... Farsight in die Flamer
  Starsythe / Burst Cannon Coldstar in die Burst Cannon Starsysthe / Missile Pod Enforcer in die
  Fireknife / Fusion Enforcer in die Sunforge"). Hier stand vorher das Gegenteil ("NICHTS ist
  angebunden ... die Liste sagt es nicht"), und der Eintrag ist die Korrektur wert: die
  Anbindungen standen im gelieferten Listentext, sie sind beim Transkribieren untergegangen.

      Commander Farsight             -> Crisis Starscythe 1 (sechs T'au Flamer)
      Commander in Coldstar          -> Crisis Starscythe 2 (sechs Burst Cannons)
      Commander in Enforcer (Pods)   -> Crisis Fireknife
      Commander in Enforcer (Fusion) -> Crisis Sunforge

  - **Die Regeln entscheiden hier GAR NICHTS** — alle drei Commander-Datenblätter nennen auf
    ihrer LEADER-Zeile alle drei Crisis-Datenblätter, jede der zwölf Paarungen wäre also legal.
    Welche zu welcher gehört, ist reine LISTEN-Tatsache; genau deshalb wäre Raten hier still
    gewesen, statt an `can_attach()` zu scheitern.
  - **Namen können die Paarung nicht prüfen, WAFFEN schon.** Die zwei Starscythe sind DASSELBE
    Datenblatt und die zwei Enforcer ebenso — ein vertauschter Leader ergibt identische
    Einheitennamen, identische Modellzahlen und dieselbe Armeesumme. Der User hat sie deshalb
    selbst nach ihren Waffen benannt, und der Test pinnt sie genauso (A/B belegt: die zwei
    Vertauschungen kippen 2 bzw. 3 Prüfungen, ohne dass sich sonst eine Zahl bewegt).
  - **Der Enhancement-SLOT reitet jetzt in der Leader-Spezifikation** statt "der erste gebaute
    Enforcer" zu sein. Die alte Form beantwortete "welcher der zwei" über die Baureihenfolge, und
    genau die hat sich mit den Anbindungen bewegt. Starflare Ignition System sitzt am
    MISSILE-POD-Enforcer, also in der Fireknife-Einheit — im Test am MODELL gepinnt, nicht an der
    Einheit: nach 19.01 hält der Trupp vier Modelle, und "die Einheit trägt es" bestünde auch mit
    dem Enhancement auf einem Fireknife-Suit.
  - **THE TWIN LANCE steht als einziger Charakter weiter allein, und das ist sein Datenblatt** —
    es druckt gar keine LEADER-Zeile (`tau_empire_points.py` gibt ihm kein `leads`), also lehnt
    `can_attach()` jede Paarung ab. Gepinnt, damit es nicht wie eine fünfte vergessene Anbindung
    aussieht.
- **Der Coldstar BEHÄLT hier seine High-output Burst Cannon** und füllt beide Slots (zwei Burst
  Cannons plus ein Cyclic Ion Blaster) — die anderen drei Listen ersetzen diese Waffe. Beide
  Slot-Optionen gab es längst; sie hatte nur nie jemand gekauft. **Das ist zugleich, was ihn als
  "Burst Cannon Coldstar" identifizierbar macht.**

#### Drei Punkte-Korrekturen, alle von dieser Liste aufgedeckt

1. **Crisis Starscythe stand auf 90/100, gedruckt sind 100/110.**
2. **The Twin Lance stand auf 220, gedruckt sind 230.** Korpus und Liste sagen dasselbe, es gibt
   hier also nichts abzuwägen — anders als bei den Abweichungen, die dieses Repo bewusst stehen
   lässt (dort widerspricht die Liste der Transkription; hier war die Transkription falsch).
3. **Ein "per <Waffe>"-Preis wird PRO WAFFE IM GEBAUTEN TRUPP berechnet, nicht pro Tausch.** Das
   kehrt eine dokumentierte Entscheidung um, und die Evidenz ist diese Liste selbst: sie preist
   **dasselbe Starscythe-Datenblatt zweimal — 130 mit sechs T'au Flamern und 100 mit keinem.**
   100 + 6×5 passt, "pro Tausch" nicht. Damit steht auch fest, was die gedruckte Basiszahl IST:
   der Trupp OHNE die bepreiste Waffe, nicht der gedruckte Default (der drei trägt und deshalb
   115 kostet).
   - `points.py`s alte Begründung nannte genau diesen Fall und schloss aus "sonst würde der
     gedruckte Default mehr kosten als die gedruckte Einheit" auf "nur der ZWEITE Flamer zählt".
     Die Prämisse war, dass die gedruckte Zahl der Preis des Defaults ist. Sie ist es nicht.
   - **`UnitPoints.per_weapon` ist der zweite Topf neben `wargear`**, und die zwei sind bewusst
     getrennt benannt: auf der Seite sehen "per Cyclic Ion Raker 15" und "per T'au flamer 5" gleich
     aus, und sie bedeuten nur dasselbe, solange der Default die Waffe nicht trägt.
   - **Gemessen über alle fünf Fraktionen: GENAU ZWEI Datenblätter sind betroffen** (Crisis
     Fireknife und Crisis Starscythe) — für jeden anderen bepreisten Eintrag trägt der Default
     keine, dort sind die zwei Lesarten identisch. Beide ziehen ihren Preis nach `per_weapon` um
     und geben ihn an ihren Optionen ab, sonst zählte er doppelt.
- **Getestet:** `test_tau_enhancements.py` 283 → **308/308** (Abschnitt 9d: die vier Paarungen an
  ihren WAFFEN statt an ihren Namen, der Enhancement-Träger am MODELL, der Alleinstand des Twin
  Lance an seinem fehlenden `leads`, die drei Korrekturen gegen den KORPUS statt gegen Literale,
  und die Zwei-Punkte-Messung an den zwei Starscythe-Einheiten — die einzige Form, in der die
  per-Waffe-Frage überhaupt eine Antwort hat; sie liest jetzt die BODYGUARD-KOMPONENTE, weil beide
  Trupps einen 80-Punkte-Commander tragen und `Squad.points` die Summe ist).
  `test_tau_walkers.py` **79/79** und
  `test_twin_lance.py` **66/66** nachgezogen — ihre Pins hielten die alten Zahlen fest, was genau
  ihre Aufgabe war. `test_force_dispositions.py` **154/154**, `test_army_select.py` **352/352**.
  Neu `ab_retaliation_attachments.py` (**5 A/B-Sonden, alle beißend**; die gemeldete Welt — jeder
  Charakter gebaut, keiner angebunden — kippt 8 von 308). **Zwei Sonden ließen die Suite zuerst
  ABSTÜRZEN statt rot zu werden** (Indizieren in ein Paarungs-Dict bzw. in eine leere
  Bewertungsliste) — **sechzehnte und siebzehnte Instanz** derselben Lehre; beide degradieren jetzt.
  Volle Regression **184 Suiten, ~16145 Prüfungen, 183 grün / 0 rot / 1 bekannt**,
  `run_tests.py --smoke` komplett grün.
- **Im ECHTEN Spiel belegt:** `selfplay.py map2` mit `tau_retaliation` auf BEIDEN Seiten meldet
  `[primary] Player 1 plays Unstoppable Force (Force Disposition: Purge the Foe)`, alle **vier**
  Anbindungen als `is one attached unit (19.01)` für jeden Spieler, das Enhancement auf
  `Commander in Enforcer Battlesuit in 1 Crisis Fireknife Battlesuits 1 + Commander in Enforcer
  Battlesuit`, und alle vier gemergten Einheiten werden aufgestellt (je 4 Modelle). Keine
  Formalie: eine Anbindung fasst Aufstellung, Kohärenz und Zielwahl an.

### Was der Roster an der Engine geändert hat

- **Der Commander in Coldstar konnte keine vier Fusion Blaster tragen.** Sein gedrucktes Menü ist
  EIN Ersatz der High-output Burst Cannon plus **bis zu DREI** Zusätze aus derselben Liste, und der
  Fusion Blaster trägt kein "keine Duplikate"-Sternchen — 1 + 3 ist also ein legaler Build. Die
  Engine hatte nur `+ 2x Burst Cannon` und `+ Cyclic Ion Blaster`. Neu:
  `COLDSTAR_BURST_TO_FUSION` und `COLDSTAR_ADD_3X_FUSION_BLASTER`, beide gratis wie ihre zwei
  Nachbarn (nichts davon steht im Wargear-Dict der offiziellen Punkteliste).
- **Der Pathfinder-Granatwerfer war als TAUSCH modelliert und ist gedruckt ein ZUSATZ.** Der Text
  lautet *"1 model in this unit equipped with a pulse carbine can be equipped with 1
  semi-automatic grenade launcher. That model's pulse carbine cannot be replaced."* Die Engine
  hatte zwei Tausch-Optionen (max 2 auf der Mannschaft plus 1 auf dem Shas'ui) — das kostete den
  Träger eine Carbine, die er behält, und erlaubte drei Werfer, wo der Text einen erlaubt.
  **Gefunden beim Transkribieren der Liste**, deren Pathfinder Team `6x Pulse carbine ... 1x
  Semi-automatic grenade launcher` über NEUN Modelle druckt — zehn Waffen für neun Körper, was nur
  aufgeht, wenn der Werfer neben einer Carbine getragen wird.
  - **Die Liste adressiert die Optionen per MODELL-INDEX**, nicht per Anzahl: eine reine Ergänzung
    startet bei Modell 0, und dort landen auch die Rail Rifles — ein schlichter Zähler gäbe den
    Werfer also genau dem Modell, dem gerade die Carbine weggetauscht wurde. Genau dafür kennt
    `build_squad()` die Indexform.
- **Der Ghostkeel brauchte NICHTS.** Die Liste kauft ein "Battlesuit Support System"; das
  Datenblatt setzt `battlesuit_support_system` bereits bedingungslos, der Kauf ändert also nichts.
  Benannt statt als Gear modelliert, das ein No-op wäre.

**Getestet:** `test_tau_army.py` neu geschrieben (**109/109**, sieben Abschnitte) — jeder
Listeneintrag Modell für Modell und Waffe für Waffe, die drei Anbindungen mit ihrem jeweiligen
Grund, die sechs Enhancements auf ihren Trägern (inklusive der zwei Fälle, die eine
Datenblatt-Suche falsch beantwortet), und die Totals **beim ECHTEN Builder erfragt** statt von
Hand nachgebaut — dieselbe Falle, die diese Datei schon einmal getroffen hat (sie war grün gegen
einen ersetzten Roster). `test_tau_enhancements.py` Abschnitt 9 fährt jetzt die ECHTE Liste statt
einer eigenen Tabelle (**256/256**) — der Grund für die Tabelle war "die Liste vergibt nichts", und
das stimmt nicht mehr. Vier fremde Suiten zu Recht rot und nachgezogen: `test_army_select.py`
(Kachelzahlen 18/76/2165), `test_detachments.py` (Enhancement-Punkte im Preview),
`test_take_to_the_skies_policy.py` (12 → 14 Keeps; **die Crisis-Suits sind zurück**, wofür der Pin
gesetzt war) und `test_pathfinders.py` (der Werfer ist ein Zusatz). Volle Regression **184 Suiten,
~16032 Prüfungen, 183 grün / 0 rot / 1 bekannt**, `smoke_pregame.py map2`,
`smoke_setup_screens.py` und `selfplay.py map2` mit T'au auf BEIDEN Seiten.
**Im ECHTEN Spiel belegt:** das Log nennt alle sechs Enhancements auf ihren Einheiten, u. a.
`Cadre Fireblade in 1 Breacher Team 1 + Cadre Fireblade carries the Through Unity, Devastation
Enhancement (30 pts).`

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
  ihrer einen Definition. **Die zweite Hälfte ("your opponent can select NEW targets for that
  charge") stand hier als BENANNTE GRENZE und ist seit 2026-09-06 gebaut** — samt der Feststellung,
  dass die alte Begründung falsch war: `_start_declared_move()` prüft die ZIELE gar nicht neu,
  und `embark()` lässt die Koordinaten der eingestiegenen Modelle stehen, die Charge wurde also
  gegen ein Phantom im Transporter aufgelöst. Siehe `## Elf Meldungen aus drei Partien`.
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

Seit ein Detachment zur LISTE gehört (`game/detachments.py`), vergibt `army_lists.build_tau()` die
Enhancements, die die Liste nennt, und `enhancements.is_active()` lehnt eines ab, dessen Detachment
nicht gefieldet wird. **Gelesen wird die ArmyList, nicht `config`** — `preview_squads()` baut die
Kachel des Armee-Screens, bevor irgendetwas in `config` geschrieben ist, ein config-basiertes Tor
ließe also Preview und Schlacht auseinanderlaufen.

**Seit dem 2026-09-05-Tausch vergibt die Liste SECHS** (siehe `## Die T'au-Liste (2026-09-05)`) —
die erste Liste dieses Projekts, die überhaupt eines kauft. Bis dahin war der Absatz hier das
Gegenteil: der 2026-08-30-Roster nannte keins, jeder Charakter stand zum Grundpreis, und
`_TAU_LIST_ENHANCEMENTS` war LEER. Der Satz bleibt trotzdem stehen, weil er die Regel benennt, die
weiter gilt: **was die Liste nennt, wird vergeben — nicht mehr und nicht weniger.**

**Die VERGABE hat dabei ihre Form gewechselt, und der Grund ist messbar:** sie war
`{Detachment: (Name, Träger-Datenblatt)}`, also EINS je Detachment mit Suche nach Datenblatt. Diese
Liste ist damit nicht ausdrückbar — zwei Cadre Fireblades nehmen VERSCHIEDENE Enhancements, und von
zwei identischen Stealth-Teams nimmt nur eines eines; eine Datenblatt-Suche findet jeweils das
erste. `_grant_tau_enhancement()` läuft deshalb am BAUORT und lehnt einen Namen ab, den die Tabelle
nicht nennt.

**Der MECHANISMUS wird seither durch den ROSTER selbst getestet** statt durch eine eigene Tabelle:
`test_tau_enhancements.py` Abschnitt 9 fährt die echte Liste (welche Einheit welches trägt, die
Punkte, und dass ein nicht gefieldetes Detachment alle sechs inaktiv macht), `test_detachments.py`
prüft, dass ihre Punkte schon zur PREVIEW-Zeit stehen. Der frühere Grund für die Fake-Tabelle
("die Liste vergibt nichts") ist entfallen.

**Experimental Prototype Cadres drei Enhancements waren PER KONSTRUKTION dormant** — alle drei
verbessern eine benannte Waffe, und kein Modell irgendeines Rosters trug T'au Flamer, Plasma Rifle
oder Airbursting Fragmentation Projector. **Seit der dritten T'au-Liste (2026-09-05) nicht mehr:**
sie rüstet genau diese drei Waffen aus, eine je Commander in Coldstar, und die Upgrades greifen
messbar (siehe `### Die DRITTE T'au-Liste`). Benannt statt durch Umschreiben einer User-Liste
"behoben" — und die Lehre steht: ein Enhancement kann vollständig verdrahtet und trotzdem
unerreichbar sein, wenn kein Roster seine Vorbedingung erfüllt.

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
(Transporter füllen, Reserven deklarieren, Support Artillery, 20.01 hart erzwungen) → Roll-off →
abwechselnd aufstellen → zweiter Roll-off (erster Zug) → SCOUTS. **`TurnTracker` bekam `deferred_start=`/`start_battle()`**
statt einer neuen Konstruktionsreihenfolge für ~35 Controller; Battle Round 0 macht Ingress gratis
tot. Beweisbar API-frei (0 Agent-Calls, per Stub-Zähler im Smoke erzwungen).

- **DIE SCHLACHT BEGINNT GENAU EINMAL — `pregame.Resume` erzwingt das Hand-off-Protokoll, statt es
  zu dokumentieren** (User: "der erste zug ging noch nicht los und der gegner spieler 2 hat schon
  36 VP").
  - **Reproduziert im ECHTEN `main()`-Lauf, bevor irgendetwas angefasst wurde:** `_finish_deployment`
    **3×**, `ScoutsStep.start` **3×**, `_begin_battle` **3×**. Das Log des Users zeigt genau das
    (dreimal "deployment complete", dreimal der Erste-Zug-Roll-off, zweimal der ganze
    Schlachtstart-Block) — und weil `main()`s `begin_battle()` Core CP verteilt UND die Primary der
    ersten Command-Phase wertet, sind 2 × 18 = 36 VP vor dem ersten Zug.
  - **EIN Protokoll, ZWEI widersprüchliche Lesarten, beide ausgeliefert.** Jedes Hand-off hier hat
    dieselbe Form: `step.start(self, on_done)`, und der Treiber macht selbst weiter, wenn der Schritt
    "nichts zu tun" antwortet. `enh_solid_image_projection._apply()` schreibt die eine Lesart wörtlich
    aus ("calling on_done AND returning False would run _finish_deployment() twice, and the second run
    would start a second first-turn roll-off"); `test_wraith_constructs.py` PINNT die andere an
    `fated_hero` (on_done gefeuert UND `start()` gibt False). **VIER ausgelieferte Schritte nehmen die
    zweite Lesart** — `fated_hero`, `enh_strike_swiftly`, `prince_of_corsairs` und der terminale Zweig
    von `main.py`s `_RedeployChain` —, und jeder ließ seinen Treiber die Sequenz ZWEIMAL weiterlaufen.
    Fehlerklasse 10 in der Form "ein Vertrag, zwei Lesarten": ein Kommentar in EINEM Modul erreicht den
    nächsten Autor nicht.
  - **Deshalb liegt die Durchsetzung beim TREIBER, nicht beim Schritt.** `Resume` feuert höchstens
    einmal und merkt sich, DASS es gefeuert hat; beide Treiber (`_finish_deployment`s Redeploy-Haken,
    `_run_next_prebattle_step`) und `main.py`s `_RedeployChain` lesen `fired` zusätzlich zum
    Rückgabewert. Damit ist JEDE der zwei Lesarten richtig, und ein fünfter Schritt kann es nicht
    erneut brechen. Die Rückgabewerte der vier Schritte sind bewusst UNANGETASTET — sonst würde
    `test_wraith_constructs.py`s Pin zu Recht rot, für eine Änderung, die nichts kauft.
  - **Die Fortsetzung ist `_deployment_finished`, nicht `_finish_deployment`**: ein Schritt, der
    zurückgibt, hat die Aufstellung nicht ein zweites Mal beendet und darf das nicht protokollieren.
    Der ECHTE zweite Besuch (ein Redeploy, der Einheiten nach `_pending` zurücklegt) kommt weiter über
    `_advance_if_nothing_to_place()` und loggt zu Recht erneut.
  - **`_begin_battle()` ist zusätzlich idempotent** (`state == DONE` → return). Kein Ersatz für den
    Fix, sondern der Backstop für den katastrophalen Ausgang: was zweimal dort ankommt, darf nicht
    zweimal CP und VP auszahlen.
  - **Getestet:** `test_pregame.py` 138 → **149/149** (neuer Abschnitt 9: die ganze Sequenz mit
    Schritten in der gefährlichen Form, plus ein Spion auf `finish_prebattle_abilities` — ohne den ist
    ein doppelt gelaufener Prebattle-Treiber hinter dem `_begin_battle`-Guard UNSICHTBAR, und eine
    Sonde darauf sähe harmlos aus). Neu `ab_pregame_starts_once.py` (**9 A/B-Sonden, alle beißend**);
    die ganze Vor-Fix-Welt kippt 5 von 149, und die erste rote Zeile meldet
    `the battle starts exactly ONCE -- ['Player 1', 'Player 1', 'Player 1']`.
  - **Im ECHTEN Spiel belegt:** `verify_pregame_starts_once.py` fährt `selfplay.py`s echte
    `main()`-Schleife und meldet **1/1/1/1/1** (Aufstellung fertig, Roll-off, Prebattle, Scouts,
    Schlachtstart) und **keine Primary-VP in Runde 1**; `--neutralize` (die volle Vor-Fix-Welt,
    inklusive `main.py`s Kette) meldet **3 Aufstellungs-Abschlüsse, 3 Roll-offs, 3 Scouts-Queues, 2-3
    Schlachtstarts** und Primary-Zahlungen in Runde 1. Nichts wird dafür gestellt — das Vorspiel läuft
    zu jedem Schlachtbeginn von selbst, also der seltene PASSIV messbare Fall.
- **SUPPORT ARTILLERY ist die DRITTE Deklaration des Schritts** (User: "im pre game muss man sich
  entscheiden ob die Support weapons (d-cannons) an einen Guardian Trupp angeschlossen werden
  sollen oder allein stehen. ähnlich wie man im pregame Einheiten in Transporter steckt").
  Gedruckt auf allen drei SUPPORT-WEAPON-Plattformen: *"At the start of the Declare Battle
  Formations step, this model can join one GUARDIAN DEFENDERS unit from your army (a unit cannot
  have more than one SUPPORT WEAPON model joined to it)."*
  - **Die REGEL war fertig, die FRAGE fehlte** — die schon dokumentierte Form, nur eine Ebene
    höher als sonst: 19.01s SUPPORT-Rolle, `can_attach()` und die Paarungstabelle stehen seit dem
    Bau der drei Plattformen, und `can_attach(platform, guardians)` gab die ganze Zeit `[]` zurück.
    Angeboten hat es nichts. Eine `armies/*.json` hätte es über `leaders:` einbacken können — und
    genau das wäre die falsche Zeit: der gedruckte Text stellt die Frage dem SPIELER, im Vorspiel.
  - **`pregame.JOIN` ist die dritte Destination**, und ihr Ziel ist ein SQUAD, wo EMBARKs ein
    Transporter-TOKEN ist. Beide reiten im selben Slot der Deklaration, weil eine Einheit genau
    ein Ziel hat und die zwei per gedrucktem Text exklusiv sind (eine gejointe Einheit darf nicht
    einsteigen).
  - **Aufgelöst wird ZUERST**, vor der Reserven-/Embark-Schleife: der gedruckte Text sagt "at the
    START of the step", und mechanisch ist die GEMERGTE Einheit das, worauf alles danach wirkt —
    eine Plattform an einer reservierten Einheit geht mit in die Reserve, und `_pending` darf sie
    nie als eigenes zu platzierendes Ding führen. Gemessen: Starting Strength 11 → **12**
    ("increases its Starting Strength accordingly"), die Plattform ist aus `army()` und vom Brett,
    und die Guardians werden als EIN Ding aufgestellt.
  - **`game/formations.py` bekommt `support_join_errors()`/`eligible_join_targets()`** — dieselbe
    "eine Definition von legal, zwei Wähler"-Teilung, die dort schon für Transporter und Reserven
    gilt. Die PAARUNG delegiert an `can_attach()` statt sie herzuleiten; alles Zusätzliche ist eine
    Bedingung des Vorspiel-SCHRITTS, von der `can_attach()` nichts wissen soll.
  - **Das ROLLEN-Tor ist tragend, und die eigene Sonde hat das gezeigt:** ohne es bekäme ein
    FARSEER einen "Join"-Knopf, denn `can_attach(farseer, guardians)` ist völlig legal (zur
    Listenbau-Zeit). Erst der Test mit einem Leader lässt die Sonde beißen — vorher meldete sie
    NO BITE, was ein Befund über den Test war und keine Entwarnung.
  - **"Deploy on the battlefield" IST die Allein-stehen-Antwort**, es braucht also keinen eigenen
    Default. Und die KI antwortet weiter mit genau dieser: der Join ist optional und sein Handel
    geht in beide Richtungen (er kauft der Plattform einen Schirm aus Guardian-Körpern und drückt
    sie zugleich auf Toughness 3, ihre eigene Support-Weapon-Regel), es gibt per stehender Vorgabe
    keinen Aeldari-KI-Pfad, und der Default ist eine legale Antwort statt eines Hängers. NAMENTLICH
    in `ai/deployment_ai.py` festgehalten, damit es nicht wie ein Versehen aussieht.
- **ZWEITER, ECHTER FEHLER, beim Lesen desselben gedruckten Absatzes gefunden: der Transport-Bann
  galt bei 18.01 nicht.** *"This model, and any unit it is joined to, cannot embark within a
  TRANSPORT."* `TransportController.can_embark()` erzwingt das seit dem Bau der Plattformen —
  `game/formations.py`s `embark_errors()` nicht. Reproduziert: `embark_errors(D-cannon, Wave
  Serpent)` gab `[]`, und `eligible_transports()` bot den Wave Serpent an; der Vorspiel-Screen
  hätte die Plattform also eingeladen, und erst die Mitten-im-Spiel-Regel hätte je widersprochen.
  EIN Satz, ZWEI Leser, nur einer antwortete. Beide Hälften sind jetzt da, inklusive der zweiten
  ("and any unit it is joined to"), die nur im FENSTER zwischen den zwei Deklarationen existiert —
  danach trägt die gemergte Einheit das Modell selbst und derselbe Pro-Modell-Test beantwortet sie.
- **`can_attach()` sagt einem SUPPORT-Trupp jetzt "join", nicht "lead".** Die Meldung wurde an dem
  Tag spielersichtbar, an dem es das Angebot gab — sie ist der Grund, warum eine Einheit NICHT auf
  der Liste steht.
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
    bezahlt zu werden. Fenster 1 (vor dem Kampf, Form von Unbridled Carnage) gab es genau für die
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
  Term). **BENANNTE, GEMESSENE LÜCKE: Mont'kas Killing Blow bleibt draußen** — seine Bedingung
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

## Regelengine — Command-Phase / Stratagems / Schaden

- Battle-Shock (01.07/08.03), Command Points (08.02), alle Core-Stratagems mit Anwendungsfall:
  Command Re-roll (15.02), Insane Bravery (15.04), Explosives (15.05), Crushing Impact (15.06),
  Rapid Ingress (15.07), Fire Overwatch/Snap Shooting (15.08/15.09), Heroic Intervention (15.11),
  Counteroffensive (15.12), Epic Challenge (15.03). `StratagemController` trägt die 15.01-Buchführung
  (einmal pro Phase/Ziel, optional `max_per_battle`, optional `allow_battle_shocked_target`).
  `_cost_for()` ist die EINE Definition des Preises, gelesen von `can_use()` UND `use()`; Rabatte
  hängen als Liste `cost_discounts` dran (Puretide, Strands of Fate).
- **Heroic Intervention (15.11) hatte GAR KEINEN Test — der gemeldete CP-Fehler existiert aber
  nicht.** Gemeldet als "ich habe heroic intervention benutzt mit dem avatar, aber die cp scheinen
  nicht abgezogen geworden zu sein". Dieselbe Ausgangslage wie 15.12 (das ohne Test ein 2-CP-No-op
  war), also war der Verdacht berechtigt; die MESSUNG widerlegt ihn.
  - **Das Hauptbuch stimmt, an zwei unabhängigen Belegen.** Im gemeldeten Log
    (`game_20260903_212406`… bzw. `game_20260903_212846.log` Z. 422) steht `Player 1 spends 1 CP`
    direkt vor `Player 1 uses Heroic Intervention`, und eine Nachrechnung ÜBER DIE GANZE SCHLACHT
    — verankert an den fünf `now has N CP`-Zeilen, die der Log selbst druckt — geht ohne
    Abweichung auf (4/4/3/3/3). Zusätzlich hat JEDE `spends`-Zeile des Laufs eine passende
    `uses`-Zeile; die drei Ausnahmen sind Strands of Fate bzw. My Will Be Done mit `spends 0 CP`.
  - **`test_heroic_intervention.py` (neu, 35/35, vier Abschnitte)** treibt den ECHTEN
    `HeroicInterventionController` gegen ein ECHTES CP-Konto und einen ECHTEN `ChargeController`:
    1 CP beim Annehmen, dem REAGIERENDEN Spieler belastet, GENAU EINMAL (der Modus-Prompt ist eine
    zweite Entscheidung und darf nicht erneut kassieren), nichts beim Anbieten, nichts beim
    Ablehnen, kein zweiter Kauf in derselben Phase (15.01). **A/B: mit entferntem `use()`-Aufruf
    fallen 6 von 35** — die Suite würde den gemeldeten Fehler fangen, wenn es ihn gäbe.
  - **Die ZWEITE Hälfte ist `active_player`, und die ist der eigentliche Grund für die Suite.**
    15.11 läuft AUSSERHALB der Phase des Reagierenden, `offer()` dreht `active_player` also um,
    und JEDER Ausgang muss zurückdrehen — Ablehnen, der beendete Charge, UND der deklarierte,
    aber nie ausgeführte Charge (ein zu kurzer 2W6, dann Cancel; der häufigste Ausgang). Ein
    vergessener Pfad ließe den Reagierenden für den Rest der Schlacht aktiv, und
    `game/command_reroll.py` belastet CP gegen `active_player` — der NÄCHSTE Command Re-roll ginge
    also aufs falsche Konto. Genau die Form, die als "CP stimmen nicht" auffiele; alle drei
    Ausgänge sind einzeln gemessen und alle drei stellen korrekt wieder her.
  - **Die Bühne der Suite prüft ihre eigenen zwei Schranken**, statt sie zu glauben: die Lücke von
    5" ist Mitte-zu-Mitte, also 2.8" Kantenabstand — außerhalb 03.04s Engagement Range (eine
    gebundene Einheit ist nicht berechtigt) und innerhalb 15.11s 6". Die erste Fassung stand bei
    4.0" und war ENGAGED, also scheiterte alles aus dem falschen Grund.
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
- **Ein Save Roll, den niemand bestehen kann, wird gar nicht erst geworfen** (User: "Save Rolls,
  die man gar nicht bestehen kann, sollten auch gar nicht gewürfelt werden. Manchmal werden da
  6en gewürfelt, die dann aber rot sind"). `damage_resolution.save_is_impossible()` ist die eine
  Definition, `AUTO_FAILED_SAVE = 1` der Platzhalter (05.04: eine unmodifizierte 1 scheitert
  immer, also ist das die eine Zahl, deren Ergebnis feststeht — es werden keine Würfel erfunden).
  - **Reproduziert vor der Änderung:** Gauss Destructor (AP-4) gegen Sv4+ Windriders ohne
    Rettungswurf braucht eine **8+**. Jeder Würfel ist rot, bevor er fällt, und das Panel hält
    das Spiel trotzdem für eine Entscheidung an, die es nicht gibt.
  - **Gefragt wird JEDES lebende Modell der Zieleinheit, nicht der Repräsentant** — und das ist
    die einzige Sorgfalt an der ganzen Änderung. Die Wurfstellen bemaßen ihr Panel über
    `displayed_save_threshold()` für EIN Modell (`allocation_target_model()`), aber
    `DamageAllocationSession._advance()` leitet `save_thresholds()` PRO MODELL neu ab. Gemessen
    an Windriders + Warlock Skyrunner: die Leibwache braucht 8+, der Charakter rettet auf seinen
    4+ Invulnerable — auf dem Repräsentanten zu überspringen hätte dessen Rettungswurf still
    gelöscht. Eigene Testzeile mit echter Attached Unit.
  - **VERHALTENSNEUTRAL außer dem Wurf**, A/B belegt: derselbe Ausgang (Modell zerstört), nur
    ohne Panel-Schritt. Die Gegenprobe steht daneben — dieselbe Waffe gegen Warlock Skyrunners
    (4+ Invulnerable gegen AP-4) wirft weiter und rettet; ohne sie bestünde der Abschnitt auch,
    wenn der Fix jeden Save Roll im Spiel entfernt hätte.
  - **[PRECISION] überlebt den Skip.** Wohin die Wunden fallen, ist eine Frage des ANGREIFERS und
    davon unabhängig, ob ein Würfel sie hätte stoppen können — deshalb teilen der bestätigte und
    der übersprungene Pfad EINE Fortsetzung (`_continue_after_save()`, je eine in `shooting.py`
    und `fight.py`), statt den Zweig zu duplizieren.
  - **Das Log lügt nicht**: statt einer erfundenen Würfelliste steht dort
    `save roll (not rolled - no save is possible, needed 8+): 0 saved, 1 failed.` plus eine
    eigene Zeile mit dem Grund. Ein Wurf, der stattfand, listet weiter seine Würfel — die beiden
    lesen sich verschieden, und genau das ist im Test gepinnt.
  - **Alle VIER `roll_kind=SAVE_ROLL`-Stellen** (je zwei in `shooting.py` und `fight.py`, die
    gewöhnliche und die kritische Teilmenge) gehen durch dasselbe Tor; ein Quell-Wächter zählt
    Stellen gegen Tore, ein fünfter kann nicht ungegated dazukommen.
  - **Getestet:** neu `test_impossible_save_skip.py` (**29/29**, fünf Abschnitte) plus zwei
    A/B-Sonden an der QUELLE, jede kippt genau ihre eigenen Prüfungen — das Prädikat
    abgeschaltet 5 von 29, auf den Repräsentanten verkürzt **genau die eine** Mixed-Unit-Zeile.
    Die 6+/7+-Grenze ist von BEIDEN Seiten gemessen, sonst bestünde der Test mit `>= 6` genauso.
  - **Ein fremder Pin wurde dabei zu Recht rot** (`test_aeldari_enhancements.py`): er pinnte den
    Wortlaut `if self._precision_choice_needed(split_weapon, target_squad):`, den der geteilte
    Fortsetzungspfad verschoben hat. Er prüft jetzt die zwei AUFRUFAUSDRÜCKE statt einer
    Anweisungsform — dieselbe Lehre wie bei den früheren Interpunktions-Pins.
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

## Primary Missions über Force Dispositions (game/primary_missions.py)

**Jedes Detachment lässt genau EINE Force Disposition zu; die Liste schreibt eine davon fest, und
die bestimmt die Primary Mission** (User: "jedes detachment hat zugang zu einer force disposition.
diese wählt man beim listen bau ... ist aber in der Liste festgeschrieben"). Fünf Dispositionen,
fünf gelieferte Karten. **Nur Spieler 1** — die KI behält "Hold the Line"
(`config.PRIMARY_MISSION_CARD_PLAYERS`).

**Die Dispositionen sind TRANSKRIPTION, nicht Zuweisung.** Sie standen die ganze Zeit im Cache:
Wahapedia druckt sie als ICON im `<h2>` jedes Detachments, direkt neben den DP, die der Scraper
schon las — `page_headings()` strippt die Tags und warf damit genau das Icon weg.
`heading_force_dispositions()` ist der zweite Pass über das ROHE Heading-HTML, `--offline` reicht
(0 Netzzugriffe), und **alle 56 Detachment-`.md` tragen die Zeile** neben ihren DP. Der Diff IST
die Evidenz; zwei Läufe erzeugen 56 byte-identische Dateien.
- **Das Heading ist auch der einzig sichere Weg:** die Detachment-FILTER-Liste derselben Seite
  schreibt "Kauyоn" mit KYRILLISCHEM о (U+043E) — dieselbe Falle, die `fetch_datasheet_rules.py`
  schon für `dsLeftСolKW` dokumentiert. Das Heading schreibt lateinisch, und
  `rules/tau_empire/detachments/Kauyon.md` heißt bereits so.
- **Gegenprobe zur Vertrauenswürdigkeit:** alle 10 automatisch vergleichbaren DP-Werte des Repos
  stimmen mit Wahapedia überein. `test_force_dispositions.py` pinnt die 17 modellierten
  Detachments gegen den KORPUS, nicht gegen Literale.

| Liste | Detachment | Disposition | Primary Mission |
|---|---|---|---|
| Aeldari | Seer Council + Path of the Outcast | Priority Assets | **Secure Asset** |
| Aeldari (`aeldari_warhost`) | Warhost | Reconnaissance | **Reconnaissance Sweep** |
| Aeldari (`aeldari_guardian_battlehost`) | Armoured Warhost + Guardian Battlehost | Take and Hold | **Battlefield Dominance** |
| Orks | War Horde | Take and Hold | **Battlefield Dominance** |
| Necrons | Awakened Dynasty | Take and Hold | **Battlefield Dominance** |
| T'au (`tau`) | Kauyon + Adv. Acquisition Cadre | Reconnaissance | **Reconnaissance Sweep** |
| T'au (`tau_montka`) | Mont'ka | Priority Assets | **Secure Asset** |
| T'au (`tau_recon`) | Advanced Acquisition + Auxiliary + Experimental Prototype Cadre | Reconnaissance | **Reconnaissance Sweep** |
| T'au (`tau_retaliation`) | Retaliation Cadre | Purge the Foe | **Unstoppable Force** |
| Death Guard | Death Lord's Chosen | Priority Assets | **Secure Asset** |

**ZWEI Listen fielden ein Detachment-PAAR, und nur eine davon hat wirklich eine WAHL.** Bei den
T'au hat der User sie benannt ("für die Tau Liste nehme ich reconnaissance (advanced acquisition
cadre)") — beide ihrer Detachments gewähren ohnehin Reconnaissance, die Wahl fällt also auf
dieselbe Mission, aber WOHER sie kommt ist die Listenbau-Tatsache und steht aufgeschrieben. Bei den
Aeldari gewährt das Paar seit dem 2026-09-01-Tausch **zwei verschiedene** (Seer Council Priority
Assets, Path of the Outcast Reconnaissance) — die erste echte Wahl hier. Sie bleibt auf Priority
Assets: die Bitte nannte ein Detachment, keine andere Primary Mission, also steht die Deklaration,
wo sie stand. EINE Zeile in `ARMY_LISTS`, falls das nicht gemeint war.

**VIER der fünf Missionen werden gespielt; DEATH TRAP ist wieder dormant.** Die Geschichte lohnt
den Eintrag, weil sie zweimal gekippt ist: die zwei letzten waren lange gebaut, getestet und per
Konstruktion unerreichbar, weil kein Roster ihr Detachment fieldete; die drei T'au-Listen vom
2026-09-05 holten sie (Prototypes → Death Trap, Retaliation Cadre → Unstoppable Force); und am
2026-09-07 wurde die Prototypes-Liste auf User-Wunsch zurückgezogen ("diese liste kann weg"),
womit Death Trap zurückfiel. **Es ist die einzige, und sie ist eine Zeile davon entfernt, wieder
live zu sein:** Disruption gewähren Auxiliary Cadre UND Windrider Host, beide modelliert — jede
Liste, die eines davon deklariert, holt sie zurück.

Der Pin, der das festhält, ist zweimal zu Recht rot geworden und ist genau dafür gesetzt. Er nennt
die dormante Mission jetzt NAMENTLICH statt nur zu zählen, und pinnt zusätzlich, dass gar keine
ausgelieferte Liste mehr Disruption deklariert — sonst läse sich "eine ist dormant" auch auf einem
Stand, auf dem eine andere es geworden ist.

### Warum das keine `SecondaryMissionCard` ist

Eine Secondary ist EINE Karte mit EINEM Zeitpunkt, EINMAL einlösbar, aus einer Hand. Eine Primary
ist EINE Karte für die ganze Schlacht mit MEHREREN unabhängigen Wertungsboxen — je eigener
Zeitpunkt, eigenes Rundenband — und **jede zahlt JEDES Mal**, wenn ihr Zeitpunkt eintritt.
`ScoringBox(key, timing, score, label, min_round, max_round)`; `score(ctx)` ist eine reine
Funktion wie bei einer Secondary.

**Automatisch, ohne Prompt.** Die Secondary fragt, weil eine Karte eine Ressource ist, die man
aufheben kann. Eine Primary bietet keine Wahl: eine Karte, nicht abwerfbar, jede Box eine feste
Bedingung. **Folge: die Headless-Harnesses brauchen KEIN Opt-out** (anders als beim Kartenstapel),
`selfplay.py` und alle Smokes fahren die echte Primary in jedem Lauf mit — als Abwesenheit
getestet, damit der neunte Harness es nicht "vorsorglich" abschaltet. **Kein VP-Cap**
(User-Entscheidung; die Karten drucken keinen, und Hold the Line hat auch keinen).

### Drei Zeitpunkte, alle an einer BESTEHENDEN Naht in main.py

| Timing | Naht |
|---|---|
| END OF YOUR TURN | `if ending_player is not None:` |
| END OF CMD PHASE | `if phase_before == PHASE_COMMAND:` mit `mover_before` |
| END OF BATTLE | `_check_battle_end()`, VOR `battle_end_overlay.show()` |

**Das ENDE der Command-Phase ist NICHT der Zeitpunkt, an dem Hold the Line wertet** (deren Naht
ist der ANFANG). Battle Shock liegt dazwischen, und die OC einer geschockten Einheit wird zum
Strich (01.07/02.02) — wer was kontrolliert kann sich zwischen den beiden also echt
unterscheiden. Eigene Testzeile.

### Vier Zugbeginn-Schnappschüsse, nach dem Vorbild von Overwhelming Force

Drei Boxen fragen nach einem Moment, der beim Werten vorbei ist, und nach Einheiten, die es dann
nicht mehr gibt: `enemies_in_terrain_at_turn_start` (Death Trap braucht WELCHE Area),
`enemies_on_central_objective_at_turn_start` (Secure Asset), `objectives_controlled_at_turn_start`
(Unstoppable Force). Zu Beginn JEDES Zuges, bedingungslos — ob eine Box sie braucht, steht dann
nicht fest.

### Die zwei Objective Actions — Regel 16.01 trug beide ohne neue Mechanik

- **Secure Asset** ist Cleanse mit PLUNDERS Use Limit (einmal pro ZUG, nicht Cleanses
  Eindeutigkeit pro Objective) — zwei Formen, die gleich aussehen.
- **Booby Trap** ist Plunders Form (`completes_immediately`) mit CLEANSES Use Limit
  (Eindeutigkeit auf dem Ziel). Es ist die einzige Action mit einem echten CALLBACK, weil
  *trapped* eine bleibende Tatsache über das BRETT ist statt über diesen Zug.
  - **Zwei Buchführungen, zwei Lebensdauern**: `trapped` (ganze Schlacht — die UNITS-Zeile sagt
    "not yet trapped") und `trapped_this_turn` (was die 2-VP-Box zählt, am Zugende geleert). In
    eine gefaltet würde entweder dieselbe Area jede Runde 2 VP zahlen oder die zweite Runde
    unsichtbar.
  - Der Zustand liegt im CONTROLLER, **nicht** auf `TerrainArea` (die trägt gar keinen) und
    **nicht** aus den `ActionState`s abgeleitet wie bei Plunder: `reset_for_turn()` leert die
    jeden Zug, *trapped* überlebt sie.
  - "Diese Area IST ein Objective" ist IDENTITÄT, nicht Geometrie — `GameState.add_objective()`
    gibt dem Objective genau die `TerrainArea`, die in `state.terrain_areas` steht.
- **`ActionController.resolve_end_of_turn()` bekam einen Idempotenz-Wächter** (`(player, turn)`,
  geleert in `reset_for_turn()`): ZWEI Missionssysteme besitzen jetzt Actions und fragen an
  derselben Naht. Zweimal aufgelöst feuerte jeden EFFECT zweimal — lautlos, weil ein Effekt nichts
  zurückgibt. **Gemessen mit einer konstruierten Action mit echtem Effekt**, weil keine der vier
  ausgelieferten an dieser Naht einen hat (drei geben `effect=None`, Booby Traps feuert bei
  `start()`) — eine A/B-Sonde ohne den Wächter änderte deshalb NICHTS Beobachtbares.
- Der hartkodierte Slot-Name (`if action.key == "plunder" else ...`) wandert als `result_slot`
  auf die `ActionDefinition`. Verhaltensgleich für die zwei alten Karten — der Gewinn ist, dass
  eine dritte Action nicht im else-Zweig landen kann, und genau das prüft der Test.

### `central_objectives()` — geometrisch, ohne erfundene Konstante

Nötig für Secure Asset und Unstoppable Force. **map3 hat gar kein Objective namens "Central"** —
seine Mitte ist eine 9"-Scheibe mit ZWEI Objectives. Also: **das der Brettmitte nächste, Gleichstand
zählt mit**, Kandidaten sind die No-Man's-Land-Objectives. Gemessen:

| Karte | zentral | nächstbestes |
|---|---|---|
| map1 | Central Objective 0.00" | 17.35" |
| map2 | Central Objective 0.00" | 19.96" |
| map3 | Objective East + West, je 6.13" | 22.78" |

**map3s Gleichstand ist BIT-IDENTISCH** (Differenz exakt 0.0), die 0.001"-Toleranz ist auf den
ausgelieferten Karten also nachweislich INERT und nur das Netz für eine künftige Karte, deren
Spiegelung durch andere Arithmetik läuft (dieselbe 7e-15-Sorte, die schon einmal aus einem
Rechteck ein Fünfeck gemacht hat). Der Home-Ausschluss ist ebenfalls ein gemessener No-op auf
allen drei Karten — und wird deshalb an einem KONSTRUIERTEN Brett geprüft, auf dem ein
Home-Objective wirklich das nächste zur Mitte ist.

### 26. Extraktion: `game/mission_context.py`

Die Primaries sind der ZWEITE Konsument von `MissionContext` und dem ganzen Geometriesatz.
Andersherum zu importieren hätte die PRIMARY von der SECONDARY-Deck abhängig gemacht — zwei
Systeme, die nichts teilen außer dieser Geometrie, und eines davon ist für die meisten Spieler aus.
`secondary_missions.py` **re-exportiert alles**, also sind seine 17 Karten und die 552 Prüfungen
seiner Suite **per Konstruktion** unverändert (im Test als Objekt-IDENTITÄT gepinnt, nicht als
Gleichheit — dieselbe Idiom wie `is_tau_unit` und `has_detachment`).
`ENGAGE_CENTRE_EXCLUSION_IN` heißt dort jetzt `CENTRE_EXCLUSION_IN`, weil Reconnaissance Sweep die
6"-Klausel wörtlich genauso druckt (Fehlerklasse 11) — der alte Name bleibt als Alias auf DENSELBEN
Wert.

### Getestet

- Neu `test_primary_missions.py` (**250/250**, dreizehn Abschnitte) und
  `test_force_dispositions.py` (**146/146**, sieben Abschnitte).
- **33 A/B-Sonden an der QUELLE (`ab_primary_missions.py`), alle beißend.** **Fünf bissen zuerst
  NICHT, und alle fünf waren Befunde über den TEST** (Fehlerklasse 24): die
  Trapped-Persistenz-Prüfung war von 16.01s eigenem Per-Zug-Limit MASKIERT (der Test räumt jetzt
  `reset_for_turn()` dazwischen, wie main.py es tut); der Idempotenz-Wächter war ohne eine Action
  mit echtem Effekt unmessbar; der `result_slot` ist für die zwei alten Karten verhaltensgleich;
  der Home-Ausschluss in `central_objectives()` ist auf allen drei Karten ein No-op; und die
  Scraper-Sonde las Dateien, die schon auf der Platte lagen, statt den Parser.
- **Neu `smoke_primary_mission.py`** — die drei Nähte durch `main()`s ECHTE Schleife, weil ein
  Quell-Wächter nicht zeigt, dass sie LAUFEN, und dieses Repo sechs "gebaut, aber nie
  gefüttert"-Fälle hat. `--neutralize` kippt 7 von 21 Prüfungen. Es unterscheidet dabei Secure
  Assets +8 von Hold the Lines +9 auf demselben Brett — eine Prüfung, die "es hat überhaupt
  gewertet" nicht leisten kann.
- **Ein echter Fehler, den nur der AST-Wächter fand:** `Renderer.draw_terrain_markers()` rief
  `_clamp_rect_to_surface()` als freien Namen, obwohl es eine statische METHODE ist — ein
  `NameError` beim ersten Marker MIT Label. Weder Suite noch Smoke erreichten die Zeile (der Smoke
  setzt seine Falle im letzten Frame). `test_event_chain_wiring.py` Abschnitt 1b hat ihn gemeldet;
  jetzt gibt es zusätzlich einen VERHALTENStest, der wirklich auf eine Surface zeichnet.
- **Zwei fremde Pins wurden zu Recht rot** und sind ehrlicher nachgezogen: `test_actions.py` pinnte
  den hartkodierten Sekundär-Aufruf des Panels (das Panel fragt jetzt BEIDE Systeme), und
  `test_secondary_missions.py` pinnte den EXAKTEN mehrzeiligen `mission_cards_overlay.draw()`-Aufruf
  — ein Wächter, der Whitespace pinnt, scheitert an Formatierung statt an Bedeutung.
- **`test_detachments.py`s `fielding()` musste die Disposition mitleeren:** eine hypothetische
  Detachment-Menge trägt keine Meinung darüber, mit welcher Disposition die Liste geschrieben
  worden wäre, und die echte stehenzulassen ließ jeden Block an einer Regel scheitern, um die
  keiner von ihnen geht.
- Volle Regression **162 Suiten, ~14249 Prüfungen, 161 grün / 0 rot / 1 bekannt**, alle neun
  Smokes plus fünf `--neutralize`-Gegenproben rot, `selfplay.py` auf map2 und map3.
- **Im ECHTEN Spiel belegt:** je ein `selfplay.py`-Lauf unter JEDER der fünf Dispositionen (alle
  exit 0), jeder mit seiner eigenen `[primary]`-Zeile im Log — also auch die zwei dormanten
  Missionen. Und die Wertung selbst: `Player 1 scores 2 Primary VP (Battlefield Dominance - MORE
  OBJ)` neben `Player 2 scores 3 Primary point(s)` — der Mensch auf seiner Karte, die KI auf Hold
  the Line, in derselben Runde.

### Die Ökonomie, gemessen — weil es keinen Cap gibt

Da kein VP-Cap existiert, ist die Größenordnung eine Aussage und keine Formalie. Gemessen auf
map2 (5 Objectives), VP je Schlachtrunde NUR aus den Objective-Boxen — ohne Kills, ohne Actions,
ohne Spread:

| gehalten | Hold the Line | Battlefield Dom. | Recon Sweep | Unstoppable | Secure Asset |
|---|---|---|---|---|---|
| 1 (nur Home) | 6 | 3 | 0 | 0 | 0 |
| 3 | 18 | 13 | 3 | 8 | 8 |
| 5 | 30 | 23 | 3 | 16 | 8 |

Über eine ganze Schlacht mit konstant 3 von 5 gehaltenen Objectives: Hold the Line **90 VP** (fünf
Runden), Battlefield Dominance 52, Unstoppable Force und Secure Asset je 32, Reconnaissance Sweep
12. Die drei niedrigen holen ihren Rest woanders (Recon aus Spread 3-6/Zug plus 1 je Kill, Secure
Asset aus 4/Zug für die Action, Unstoppable aus Kills plus 5 in der Endwertung). Zwei Zeilen der
Tabelle sind Regeln, keine Balance: bei EINEM gehaltenen Objective zahlen drei der vier Karten
NULL, weil ihre Box das eigene Home-Objective ausschließt; und Battlefield Dominance zieht bei
hoher Kontrolle davon, weil ihr kumulativer Home-Bonus jedes Vorwärts-Objective von 3 auf 5 hebt.

**Die Aussage dieser Tabelle hat sich UMGEDREHT, und das ist bestellt.** Sie las früher "die Karten
liegen in derselben Größenordnung wie die Mission der KI, nicht darüber" — bei 3 VP je Objective
kam Hold the Line auf 45 gegen die 52 von Battlefield Dominance. Auf User-Wunsch zahlt sie jetzt
**6 statt 3** (und No Mercy **3 statt 1**, siehe unten), also liegt die KI-Mission deutlich VORNE.
Es ist ein bewusster Handicap-Regler zugunsten der KI, keine Balance-Messung; die Zahlen stehen
hier, damit die nächste Änderung an einer Force-Disposition-Karte weiß, wogegen sie antritt.

### Bewusst offen

Kein KI-Pfad (Spieler-1-Vorgabe, als Negativraum geprüft: kein neuer Name in
`ai/agent_driver.py`); und die "OPPONENT: TAKE AND HOLD"-Annahme aller fünf Karten wird NICHT
erzwungen, sondern bei Verletzung als `[primary]`-Logzeile benannt (beide Default-Listen erfüllen
sie).

## Die Hover-Datacard zeigt den GEDRUCKTEN Regeltext (game/rules_text.py)

**Der Korpus wird zum ersten Mal ZUR LAUFZEIT gelesen** (User: "im overlay
sollten nicht nur die stats stehen, sondern auch alle Fähigkeiten, die diese
Einheit hat" + "und zeige bitte die original regeltexte an. keine selbst
generierten varianten"). `rules/<fraktion>/<Datenblatt>.md` lag seit dem Bau des
Korpus da und hatte **keinen einzigen Leser** — es war ein reines
`git diff`-Artefakt.

- **`Datasheet.abilities_text` kann die Frage NICHT beantworten, und das steht in
  seinem eigenen Scaffold-Docstring** ("purely for reference/display"): seine
  Treue ist je Fraktion verschieden. Orks und T'au sind nahezu wörtlich, Aeldari
  und Death Guard sind Paraphrase plus `see game/bladestorm.py`. Das einem
  Spieler vorzusetzen zeigt ihm eine NOTIZ ÜBER die Regel, nicht die Regel.
- **VERBATIM ist gemessen, nicht behauptet** — die tragende Prüfung der Suite:
  jeder Text, den das Modul ausgibt, muss als Teilstring in seiner eigenen `.md`
  stehen (506 Abilities über alle 130 gebauten Datenblätter, 0 Abweichungen).
  Ein Test, der nur "irgendein Text kam zurück" prüft, bestünde auch bei einer
  Paraphrase. Dazu die Gegenprobe: `see game/`/`.py` darf NIRGENDS ankommen —
  und dass das eine echte Differenz ist und kein sauberer Korpus, wird an
  `abilities_text` selbst belegt.
- **Alle 130 gebauten Datenblätter lösen ohne Alias-Tabelle auf**, per reiner
  Normalisierung. Zwei Ableitungen (Ordner je Fraktion, Datenblattname →
  Dateiname) sind aus `fetch_datasheet_rules.py` DUPLIZIERT statt importiert —
  das ist ein CLI-Werkzeug, das `urllib` auf Modulebene zieht, also die falsche
  Abhängigkeitsrichtung für den Render-Pfad —, und **gegen es GEPINNT**. Eine
  Antwort, Drift wird rot.
- **Gelesen werden `Abilities`, `Wargear Abilities`, `Transport` und
  `Damaged: *`.** Letzteres per PRÄFIX (die Schwelle steht in der Überschrift,
  "1-4" bis "1-20") und weil es aus den AKTUELLEN Wunden feuert — genau das,
  wofür man hovert. Alles Übrige steht schon anders auf der Karte (Profile →
  Statblock, Weapons → Waffentabellen) oder ist Armeebau-Information.
- **Drei gedruckte Formen, über den ganzen Korpus gezählt** (261 / 320 / 56):
  `CORE: **Deep Strike, Leader**` (Label-Zeile), `**Bladestorm:** ...`
  (benannte Fähigkeit), und blanke Prosa (Damaged/Transport drucken keinen
  Namen). Getrennt gehalten, damit die Karte die Hierarchie des Datenblatts
  zeichnet statt eines grauen Blocks — das ist die Lesbarkeits-Hälfte derselben
  Bitte.
- **Typografische Glyphen werden GEFALTET, nie gelöscht** (`’`→`'`, `–`→`-`):
  pygames Default-SysFont zeichnet sie als Tofu. Kein Wort ändert sich; im Test
  ist beides geprüft (kein ungefalteter Glyph überlebt, UND die Faltung feuert
  wirklich).
- **`abilities_for()` gibt bei JEDEM Fehlschlag `[]`** (kein Datenblatt, keine
  Fraktion, fehlende Datei) — es läuft auf dem Render-Pfad, wo eine Exception
  ein abgestürzter Frame ist. Nach Pfad gecacht.

### Die Karte selbst (game/ui/unit_datacard.py)

- **Eine Gruppe PRO KOMPONENTE bei einer Attached Unit (19.01)**, nach Datenblatt
  dedupliziert. `squad.datasheet` beschreibt eine gemergte Einheit nur zur
  Hälfte: einen Boy zu hovern hätte nie gezeigt, dass der Warboss in derselben
  Einheit Waaagh! mitbringt. Eine schlichte Einheit bekommt KEINE Überschrift —
  es gibt ein Datenblatt, und es zu benennen wiederholte nur den Kartentitel.
- **Zwei Wege hinein** (`update_hover()`, GEPOLLT): CTRL+Hover öffnet SOFORT
  (die bestehende Geste, unverändert — wer die Abkürzung kennt, soll nicht auf
  einen Timer warten), und Verweilen für `HOVER_DELAY_MS` ohne gedrückte Taste
  öffnet von selbst. Ein Poll, kein KEYDOWN/KEYUP-Paar: Fehlerklasse 15
  (~48 Zweige, deren Rümpfe nur Klicks behandeln) und dieselbe Begründung, die
  `update_measuring()` für das ALT-Lineal ausschreibt.
  - **`HOVER_JITTER_PX` ist tragend, nicht Kosmetik:** eine auf der Maus
    ruhende Hand bewegt sie ein, zwei Pixel. Ein exakt eingefrorener Cursor als
    Bedingung hieße, dass die Karte fast nie erscheint.
- **Scrollen mit dem Mausrad**, weil die Karte jetzt regelmäßig aus dem Fenster
  wächst (gemessen: 873 px für Boyz + Warboss + Painboy). Die Radbehandlung wird
  im BESTEHENDEN frühen `MOUSEWHEEL`-Zweig angeboten, VOR dem Kamera-Zoom, und
  wird nur beansprucht, solange die Karte offen UND wirklich scrollbar ist —
  eine kurze Karte zoomt weiter wie bisher.
- **Die Scroll-Position hängt am TOKEN**: zu einem anderen Modell zu wechseln
  öffnet dessen Karte oben, statt einen an einer viel längeren Karte gemessenen
  Versatz zu erben.
- **`last_rect`**, weil eine zu hohe Karte an die untere Fensterkante geheftet
  wird und dann NICHT beim Cursor steht — jede aus der Mausposition gerechnete
  Lage ist geraten. (Genau daran sind zwei meiner eigenen Testprüfungen zuerst
  gescheitert.)
- **Ein Modal unterdrückt die Karte** — sie wird über das Brett gezeichnet, läge
  also auf genau dem Prompt, der zuerst beantwortet werden muss.

### Armeeregel und Detachment-Regeln lesen (game/ui/army_rules_overlay.py)

**Der einzige Ort, an dem diese zwei Regeln bisher nirgends standen** (User: "es
fehlt noch ein ort, wo man armeeregel und detachment regeln anschauen kann. ich
würde vorschlagen, das im game info panel rechts zu platzieren. dort soll
irgendwo ein kleiner link sein 'see army rules' unter den logos und
volkernamen"). Fähigkeiten stehen auf der Hover-Karte, Missionen auf dem
Streifen, ein Stratagem benennt sich auf seinem Knopf — "was tut Battle Focus
eigentlich" existierte nur in der Engine und im Korpus auf der Platte.

- **BEIDE Armeen, nicht nur die eigene.** Ob die gegnerische Armeeregel nach
  einem Advance chargen lässt, ist eine Tatsache, die man zum Gegenspielen
  braucht, und sie ist vom Brett nicht ablesbar. Die eigene steht oben.
- **Ein LINK, kein Knopf**, und das ist der Grund für die Formulierung: ein
  Knopf in dieser Spalte gibt etwas aus oder bringt das Spiel weiter ("Next
  Phase"), dieser öffnet nur einen Leser. Klein, unterstrichen, hellt beim
  Hover auf. **Ohne Badges kein Link** — ohne Fraktion gibt es nichts
  nachzuschlagen.
- **`handle_army_rules_click()` ist eine EIGENE Methode**, kein zweiter
  Rückgabewert von `handle_click()`: die zwei Antworten bedeuten für `main()`
  völlig Verschiedenes, und wer sie verwechselt, schaltet die Phase weiter,
  wenn der Spieler eine Regel lesen wollte. Der Link-Zweig steht in `main.py`
  ÜBER dem des Phasenknopfes — beide liegen im rechten Panel, und der erste
  passende Zweig gewinnt.
- **Ein MODAL über dem Brett**, nicht im Panel: das sind mehrere hundert Wörter
  je Regel (Battle Focus allein 26 Absätze) und das rechte Panel ist 220 px
  breit. Mausrad scrollt, jeder Klick und ESC schließen. **Er besitzt jedes
  Event, solange er offen ist**, und wird dafür GANZ OBEN in der Event-Schleife
  gefragt — er ist eine ANSICHT, und Fehlerklasse 15 hat diese Kette fünfmal
  eine Steuerung schlucken lassen. `continue`, weil der schließende Klick nicht
  zusätzlich auf dem Brett landen darf.
- **`rules_text` liest jetzt auch `army_rules.md` und `detachments/*.md`.** Zwei
  Namensfaltungen sind dafür nötig und beide sind an den gelieferten Daten
  gemessen, nicht geraten: die Seite schreibt "For the Greater Good" klein, und
  Death Guards Armeeregel heißt dort "Nurgle's Gift (Aura)", während die Liste
  "Nurgle's Gift" deklariert. Gelesen wird BEIM NAMEN und nicht "der erste
  Abschnitt": eine `army_rules.md` kann mehrere tragen (Aeldari: Battle Focus
  UND Disparate Paths), und Errata/FAQ liegen in derselben Datei — die fragt
  niemand beim Namen.
- **Vom Detachment nur der `## Detachment rule`-Abschnitt.** Die Datei trägt
  auch Stratagems und Enhancements; das sind Seiten von Text und gehören auf
  einen eigenen Screen. Im Test an einem Namen geprüft, der NUR dort vorkommt
  ("Lucid Eye") — nach "Stratagem" oder "CP" zu suchen schlägt fehl, weil
  Strands of Fate' eigener Regeltext beides erwähnt.
- **Die EINE Rendering-Entscheidung: eine plattgedrückte Tabellenzeile wird an
  ihrer eigenen Markierung getrennt.** Der Scraper macht aus einer
  Wahapedia-Tabellenzeile `Incursion**2**`, und Marker-Strippen allein zeigt
  "Incursion2". Bewusst ENG — eine ganze Zeile, die genau aus Label plus einem
  fetten Lauf besteht: die naheliegende allgemeine Regel ("Leerzeichen um jeden
  fetten Lauf") setzt in Fließtext ein Leerzeichen vor das Komma nach
  `**Normal**`. Gemessen über alle Armeeregel- und Detachment-Dateien: 24
  Zeilen treffen zu, 0 davon Prosa. Es ändert kein Wort — es ist eine
  Entscheidung über eine ZELLGRENZE, die der Korpus selbst markiert.
- **Ein echter Robustheitsfehler dabei gefunden und behoben:**
  `rules_text` löste die Fraktion über `faction.get_faction()` auf, und die
  Registry ist erst gefüllt, wenn das jeweilige Fraktionsmodul importiert wurde
  — nichts importiert die fünf eifrig. Ein Aufruf aus einem frischen Prozess
  gab also STILL `[]` zurück, genau das Versagen, vor dem der Modul-Docstring
  warnt. Der Keyword ("T'AU EMPIRE") faltet ohnehin auf denselben Ordner wie
  der Name, also gibt es jetzt `folder_for_keyword()` — dieselbe Faltregel,
  zweiter Eingang, und der Test pinnt für jede gebaute Fraktion, dass beide
  Eingänge dasselbe antworten.
- **Zwölfte Konsumenten-Extraktion: `button_style.draw_scrollbar()`.** Die
  Hover-Datacard hatte eine, der Leser braucht dieselbe — Spur und Griff, wobei
  die LÄNGE des Griffs sagt, wie viel noch kommt, und seine LAGE, wo man ist.
- **Getestet:** neu `test_army_rules_overlay.py` (**58/58**, fünf Abschnitte —
  Inhalt, Schließen/Scrollen, das Zeichnen auf PIXELN inklusive "kein Text
  entkommt dem Panel" und "der Clip wird zurückgegeben", der Link im echten
  Panel, und der Quell-Wächter auf `main.py`); `test_rules_text.py` 38 →
  **65/65**; `test_faction_badges.py` 62 → **63/63** (ein Pin verlangte, dass
  die Badge-Form 40 px kürzer ist als die lange Form — der Link kostet 18 davon;
  er misst jetzt gegen `ARMY_RULES_LINK_HEIGHT` statt gegen einen blanken Rand).
- **Im ECHTEN Spiel belegt:** ein Spion durch `selfplay.py map2` klickt den Link
  an der Stelle, an der das Panel ihn gezeichnet hat — der Leser geht auf, trägt
  **52 Blöcke** für die echten Armeen (aeldari/necrons), zeichnet, und der
  nächste Klick schließt ihn wieder.
- **Benannte Grenze:** der Korpus hat Wahapedias Tabellen an manchen Stellen zu
  Fließtext verschmolzen ("BATTLE SIZEBATTLE FOCUS TOKENS" — zwei Spaltenköpfe
  ohne trennende Markierung). Das ließe sich nur durch Erfinden von Text
  reparieren und bleibt deshalb, wie es gedruckt ankommt.

#### Nachgezogen: lesbar gesetzt, scrollbar, und ZWEI Links (2026-09-04)

**Gemeldet:** *"der Text hinter See Army Rules ist noch schwer lesbar. Beispiel aeldari. es fehlt
an überschriften, ansätzen, fett geschriebenen Namen ... außerdem könnte ich das Fenster nicht
scrollen. beim scrollen ging das Fenster wieder zu. außerdem sollten dort 2 links sein einer für
Spieler 1 und einer für Spieler 2"* — drei Anliegen, drei verschiedene Ursachen.

**1. Das Mausrad schloss das Fenster.** `handle_event()` verwarf bei JEDEM `MOUSEBUTTONDOWN,`
ohne `event.button`-Prüfung. **pygame liefert fürs Mausrad aus 1.x-Kompatibilität zusätzlich zu
`MOUSEWHEEL` ein `MOUSEBUTTONDOWN` mit Button 4/5** — eine Radrastung kommt also als ZWEI Events
an, scrollte und schloss im selben Frame, und weil `dismiss()` `scroll` nullt, war der Leser
überhaupt nicht scrollbar. **Es war die einzige Stelle im Repo ohne diese Prüfung**
(`army_select.py`, `game_menu.py`, `map_select.py` und jeder Notice-Zweig in `main.py` gaten auf
`button == 1`). **User-Entscheidung: der KLICK soll weiter schließen, auch im Fenster — nur das
Rad nicht** ("Das sollen 2 verschiedene Eingaben sein"), also bleibt der gepinnte
"a click closes it, including inside the panel"-Test gültig und die Scrollleiste bleibt reine
Anzeige. Dazu Tastatur als zweiter Weg (PgUp/PgDn/Home/End/Pfeile/Space), weil ein Steuer mit
genau einer Route ein geschlucktes Event von unbenutzbar entfernt ist.
**Warum 58 grüne Prüfungen das nicht sahen: sie schicken alle ein NACKTES `MOUSEWHEEL`** — das
PAAR, das die Hardware wirklich liefert, kam darin nicht vor. Fehlerklasse in Reinform.

**2. Der Text war strukturlos, weil die Struktur beim PARSEN vernichtet wurde.** Nicht ein
Styling-Versäumnis im Renderer: `_strip_markdown()` löschte jedes `**`, `### ` fiel zu Prosa
zusammen, und die `""`-Trenner warf das Overlay weg. Der Leser bekam für Aeldari Battle Focus
**26 nicht unterscheidbare Strings**, alle in einer Schrift mit einem Abstand.
- **`game/rules_text.py` führt jetzt `RuleLine` + `army_rule_blocks()`/`detachment_rule_blocks()`,
  und `army_rule_text()` ist deren FLACHE PROJEKTION** (`_flatten(_corpus_lines(body))`) — ein
  Parser, zwei Sichten, dieselbe Form wie `info_rows()`/`info_lines()` in `mission_cards.py`.
  **Byte-identisch belegt** (`ab_rules_text_projection.py`): 181 Abschnitte in 61 Korpusdateien,
  **0 Abweichungen**, und die Runs sind verlustfrei (0 lossy splits). Deshalb blieben
  `test_rules_text.py` (65/65) und der Datacard-Pfad `abilities_for()` unangetastet.
- **Die Kinds sind am Korpus GEMESSEN, nicht geraten**: 885 `LABEL:`-Zeilen (TRIGGER/EFFECT/WHEN/
  TARGET/RESTRICTIONS, 9 verschiedene, 0 Fehltreffer), 31 bare-ALL-CAPS-Überschriften, 107
  Bullets, 24 flachgedrückte Tabellenzeilen — und **1148 Zeilen (48 %) mit INLINE-Fett**, also
  keine Dekoration, die man weglassen kann.
- **`text_utils.wrap_runs()/draw_rich_text()/rich_text_height()`** brechen über Lauf-Grenzen um,
  damit `TRIGGER:` fett und blau im SELBEN umbrochenen Absatz weiterläuft. Messen und Zeichnen
  teilen `wrap_runs()` — die Falle, die `unit_datacard._ability_height` ausschreibt, und hier
  schlimmer, weil eine Fehlmessung den Scrollweg speist. **Gegen `wrap_text()` gepinnt: 444
  Vergleiche über 5 Armeeregeln × 6 Breiten, 0 Abweichungen.** Die Breiten werden dafür pro
  SAME-FONT-SEGMENT als ganze Strings gemessen — `size(a) + size(b) != size(a+b)`, und die
  Summenform packte messbar mehr auf die Zeile.
- **`unit_datacard.py` bleibt unberührt** — der Leser ist der ERSTE Konsument von Rich Text; die
  Extraktion gehört zum zweiten.

**3. Eine dritte Ursache, die niemand genannt hatte: die ZEILENLÄNGE.** Das Panel nahm 62 % des
Schirms und gab dem Text jeden Pixel davon — bei 1600×900 eine 937-px-Spalte, bei 6.19 px
mittlerer Zeichenbreite **151 Zeichen pro Zeile** (angenehm sind 45–90), bei 1.18 Durchschuss.
Kein Fett und keine Überschrift rettet eine Zeile, deren Anfang das Auge nicht wiederfindet.
`MAX_TEXT_WIDTH = 560` deckelt die SPALTE (Panel 992 → 615 px), Durchschuss 13 → 17 px.

**Zwei Links, je einer unter seiner eigenen Badge-Kachel** (User-Entscheidung: **je nur diese
Armee**). `handle_army_rules_click()` → **`army_rules_player_at()`**, das den SPIELER
zurückgibt statt `bool` — mit einem Link pro Spieler ist die Antwort kein Ja/Nein mehr, und den
Namen zu behalten wäre die stille Drift, gegen die Fehlerklasse 11 existiert.
- **Das kehrt das lauteste Argument dieser Datei um** ("BOTH ARMIES, not just the reader's").
  Das Argument bleibt gültig — man braucht die gegnerische Armeeregel — und wird anders eingelöst:
  sie ist weiter EINEN Klick entfernt, unter IHRER Kachel, und der eigene Weg führt nicht mehr an
  ihr vorbei. Gemessen: beide zusammen 1232 px in einem 662-px-Fenster, die Necron-Hälfte allein
  **braucht gar kein Scrollen**. Der Test prüft beide Richtungen UND dass die Vereinigung weiter
  beide Armeen abdeckt, damit die Umkehrung eine Umsortierung bleibt und kein Verlust.
- **Das Label MUSSTE kürzen, und die bindende Schranke ist die ZENTRIERUNG, nicht die Gesamtbreite:**
  ein Link sitzt mittig unter einer `LOGO_BOX`-Kachel, deren Mitte 29 px von der Panelkante steht,
  darf also höchstens 58 px breit sein. "see army rules" ist 75+8 = 83 px und hinge 12 px über
  JEDE Seite; "see rules" ist 55 px. (Zwei der alten Labels hätten nebeneinander sehr wohl
  gepasst — 166 px in einer 200-px-Spalte. Es ist, wo sie SITZEN müssen.)

**Performance nebenbei:** das Layout wird jetzt einmal pro Spaltenbreite gecacht statt zweimal pro
Block pro Frame umbrochen, und Blöcke außerhalb des sichtbaren Bandes werden übersprungen.
`_last_content_bottom` erlaubt dem Test, die VORHERSAGE gegen das GEZEICHNETE zu prüfen — genau der
Vergleich, der bei den Missionskarten einen echten doppelt gezählten Abstand gefunden hat.

**Getestet:** `test_army_rules_overlay.py` 58 → **105/105** (neu: Abschnitt 6 das Rad-PAAR und die
Tastatur, 7 die wiedergewonnene Struktur, 8 die Zeilenlänge an drei Auflösungen plus
Vorhersage-gegen-Gezeichnetes, 9 die Typografie auf PIXELN — Überschriftfarbe gegen Bodyfarbe,
Label-Präfix und Satz in EINEM Absatz, Tabellenwerte mit gemeinsamer rechter Kante, kein Text
außerhalb der Spalte). Abschnitt 1s Verbatim-Pin ist durch einen STÄRKEREN ersetzt: nicht mehr
"jeder Absatz taucht irgendwo auf", sondern die ganze Wortfolge stimmt überein — die alte Form
hätte ein verlorenes oder doppeltes Wort anderswo nicht bemerkt.
`test_faction_badges.py` **63/63** nachgezogen. Neu `ab_army_rules_reader.py`: **7 A/B-Sonden an
der QUELLE, alle beißend**, und die erste nennt den gemeldeten Fehler wörtlich
(`one real wheel notch scrolls it: got False`).
**Im ECHTEN Spiel belegt** (`verify_army_rules_links.py`, `runpy` auf `selfplay.py`s echte
`main()`-Schleife): das Panel zeichnet beide Links, ein Klick auf Player 1 öffnet **nur Aeldari**
(48 Blöcke), einer auf Player 2 **nur Necrons** (10 Blöcke), eine echte Radrastung lässt den Leser
**offen und auf 48 px gescrollt**, ESC schließt ihn. `--neutralize` (Vor-Fix-Welt) meldet
**geschlossen, Scroll 0** — das gemeldete Verhalten.
**Harness-Falle dabei:** `selfplay.py` ERSETZT `pygame.event.get` beim Import, eine vorher
installierte Sonde wird also überschrieben; sie hängt sich jetzt beim ersten Panel-Frame ein. Und
sie ERSETZT die Events der zu messenden Frames, statt sie zu ergänzen — selfplay klickt pro Frame
selbst mit Button 1 aufs Brett, und einer davon hätte den Leser geschlossen und wäre für den
gemessenen Fehler gehalten worden.

**Benannte Grenzen:** die verschmolzenen Tabellenköpfe bleiben wie gedruckt (siehe oben); es gibt
**EINE Überschriftenebene**, weil der Korpus `AGILE MANOEUVRES` und `SWIFT AS THE WIND` beide als
bare ALL-CAPS druckt und zwei Ebenen eine Hierarchie erfänden, die der gedruckte Text nicht trägt;
und `abilities_for()` flacht Inline-Fett weiterhin ab.

#### Und ohne Lore und Beispiele (2026-09-04)

**Gemeldet:** *"keine hintergrund info texte und example texte in den armeeregeln bitte. nur
reine regeltexte."* Jede Armeeregel öffnete mit einem Absatz Lore, drei der fünf zusätzlich
in ihren Unterabschnitten (Death Guard eine Zeile über JEDER der drei Plagues), jedes Stratagem
mit seinem Legend, und Reanimation Protocols mit einem sechszeiligen Rechenbeispiel.

- **Behoben eine Ebene tiefer, im Korpus** — siehe `## Regeltext-Korpus`. Der Leser selbst ist
  unverändert; er zeigt, was auf der Platte liegt, und dort liegt jetzt nur noch Regeltext.
- **Wie viel es war, gemessen** (Leser-Blöcke gegen den Korpus aus `HEAD`, alle fünf Listen):
  **349 → 296 Blöcke, 5620 → 4137 Wörter — 26 % jedes Wortes im Leser war Lore oder Beispiel**,
  also gut ein Viertel des Scrollwegs. Pro Liste: Aeldari 326 Wörter, Orks 231, Necrons 334,
  T'au 309, Death Guard 283.
- **Getestet:** `test_datasheet_rules.py` 89 → **108/108** (neuer Abschnitt 5c) und
  `test_army_rules_overlay.py` 106 → **122/122** (neuer Abschnitt 1b). Der Abschnitt im
  Korpus-Test misst gegen die GECACHTEN SEITEN statt gegen drei zitierte Lore-Sätze — jeder
  `ShowFluff`/`redExample`-Block der fünf Seiten wird geerntet (982) und muss im Korpus fehlen;
  ein Pin, der drei Absätze benennt, wird beim vierten grün. **Und er fragt DREI Ebenen**, weil
  Abschnitt 5b genau das gelehrt hat: eine Suite, die nur `rules/` liest, bleibt gegen einen
  kaputten Scraper grün, also werden `to_markdown()` und `parse_stratagems()` direkt gefahren.
  **Jede Prüfung ist ein PAAR** (der verschwundene Absatz plus die Regel, die daneben stand) —
  "die Lore ist weg" stimmt auch für einen Korpus, der die Regel mitgenommen hat.
- **Neu `ab_rules_no_fluff.py`: 4 A/B-Sonden an der QUELLE, alle beißend** (ShowFluff zurück →
  102/108 + 116/122; redExample zurück → 104 + 120; der Stratagem-Legend zurück → 104 + 121;
  die ganze Vor-Fix-Welt → **97 + 113**). Sie REGENERIEREN den Korpus je Sonde: eine Sonde, die
  nur den Scraper anfasst, ließe die Suiten die schon reparierten Dateien lesen und meldete einen
  sauberen Durchgang gegen einen kaputten Parser (Fehlerklasse 16).
- **Im ECHTEN Spiel belegt:** `verify_army_rules_links.py map2` — beide Links öffnen ihre eigene
  Armee (98 bzw. 39 Blöcke), Rad scrollt, ESC schließt; und `verify_stratagem_tooltip.py map2`
  meldet `'Sudden Storm' (NECRONS) -> 5 printed blocks` statt der früheren 6 — die eine Zeile
  weniger IST der entfallene Legend.
- **Ein fremder Pin wurde zu Recht rot** (`test_aeldari_detachment_stratagems.py`): er hielt den
  Tippfehler "be/ies" der Seite fest — der stand im LEGEND von Wraithbone Armour und ist mit der
  Lore gegangen. Umgedreht statt gelöscht; der zweite Artefakt-Pin ("(excluding TITANIC units]")
  steht im TARGET und gilt unverändert.

#### Die Detachment-STRATAGEMS: im Leser und als Hover-Tooltip (2026-09-04)

**Gemeldet:** *"was noch fehlt sind die Infos zu den detachment stratagems. die gehören zum einen
in die Army Rules overlays. zum anderen sollte das stratagems vollständig angezeigt werden wenn
man ein paar Sekunden über einen stratagems Knopf hovert."*

Der `## Stratagems`-Abschnitt jeder Detachment-Datei war beim Bau des Lesers **ausdrücklich
übersprungen** worden (`detachment_rule_text()`s Docstring: "those are pages of text that belong
on a screen of their own"). Das ist jetzt dieser Screen — und die Zeilenlängen-Korrektur, die mit
den zwei Links kam, ist der Grund, warum die Seiten dort jetzt lesbar hineinpassen.

- **`rules_text.detachment_stratagems()` liefert eine LISTE von `RuleStratagem`**, nicht einen
  flachen Block: zwei Konsumenten stellen zwei verschiedene Fragen an denselben Abschnitt — der
  Leser will alle in gedruckter Reihenfolge, ein Tooltip genau EINEN nach Namen. Flach
  zusammengefügt müsste der zweite wieder aufteilen, was der erste schon aufgeteilt hat
  (Fehlerklasse 10). Getrennt wird an der `### `-Überschrift, also am Marker des Korpus selbst;
  die Kosten (`- 1CP`) werden vom NAMEN abgetrennt und als eigenes Feld geführt.
- **Der `subtitle`-Kind ist neu** (`*Seer Council - Strategic Ploy Stratagem*`). **Gemessen statt
  vorsichtig gewählt:** alle **283** Einfach-Sternchen-Läufe des Korpus sind GANZZEILIG, 0 sind
  inline — und alle 283 liegen in `## Stratagems`-Abschnitten, die bis dahin niemand las. Deshalb
  kann die Erweiterung keine bestehende Ausgabe bewegen; die Identitäts-Sonde bestätigt es
  (181 Abschnitte, 0 Abweichungen).
  **Die Marker bleiben im FLACHEN Text und fehlen in den RUNS**, und genau diese Spaltung ist der
  Sinn der zwei Sichten: die flache ist definiert als „was `_paragraphs()` immer ausgegeben hat"
  und darf sich nicht bewegen, der Leser zeichnet aus den Runs und setzt den Untertitel in seinem
  eigenen Stil statt in Sternchen.
- **`stratagem_named()` löst einen KNOPF-Namen auf einen gedruckten auf: EXAKT, dann ein
  EINDEUTIGES SUFFIX.** Das Panel kürzt Namen, damit sie auf 220 px passen — „Sudden Storm" für
  `PROTOCOL OF THE SUDDEN STORM`, „Arro'kon Protocol" für `THE ARRO'KON PROTOCOL`. Gemessen über
  jedes Stratagem jeder ausgelieferten Liste hat jeder gekürzte Name **genau EINEN**
  Suffix-Kandidaten. **Ein MEHRDEUTIGES Suffix gibt None zurück statt zu raten** — die falschen
  Regeln anzuzeigen ist schlimmer als keine, weil nichts auf dem Schirm sagen würde, dass es die
  falschen sind. Eigene Testzeile mit zwei konstruierten Zwillingen.

**`game/ui/rules_body.py` ist die 27. Extraktion, am ZWEITEN Konsumenten.** „Wie werden gedruckte
Regeln gesetzt" lag in der Mitte des Lesers, solange er der einzige Setzer war; der Tooltip ist der
zweite und will genau dasselbe. Beim Leser BLEIBT, was Tatsachen über ein modales Fenster sind —
Panel, Scrim, Scrollen, Kopfzeile und der Block-BAU (welche Armeen, welche Detachments, welche
Reihenfolge). `RulesBody` zeichnet nie einen Rahmen, liest nie die Maus und weiß nicht, was ein
Spieler ist. Die Farb- und Abstandskonstanten des Lesers sind **Re-Exporte** daraus, damit jeder
Leser und jeder Pixel-Test per Konstruktion unverändert bleibt (dieselbe Weiterleitungs-Idiom wie
`selection.py`s `selected_squad`).

**Der Tooltip (`game/ui/stratagem_tooltip.py`) ist ein DWELL, kein Hover.** Das Panel ist eine
Spalte Knöpfe, über die man auf dem Weg zum Klicken hinwegfährt; ein Kasten, der bei Berührung
aufginge, würde ständig aufblitzen. `STRATAGEM_TIP_DELAY_MS = 1400` — **länger als die 900 ms der
Datacard**, und das ist die Begründung: die Karte geht über dem BRETT auf, wo Verweilen „erzähl mir
von diesem Modell" heißt.
- **Aufgezeichnet wird in `_draw_button()` selbst**, nicht an den siebzehn Aufrufstellen mit
  `accent="stratagem"`: eine Zeile deckt alle siebzehn UND jeden künftigen Stratagem-Knopf ab.
  **In einer EIGENEN Liste neben `self._buttons`**, weil `handle_click()` die als `(rect,
  callback)` entpackt — sie auf ein 3-Tupel zu verbreitern bräche jeden Klick im Panel
  (Fehlerklasse 22 in ihrer schärfsten Form).
- **Verglichen wird nach NAMEN, nicht nach Rect**: das Panel baut seine Rects jeden Frame neu, eine
  Identitätsprüfung setzte den Dwell also jeden Frame zurück und der Kasten ginge nie auf. Der Test
  modelliert das mit einem zur Laufzeit GEBAUTEN String, weil Python Literale interniert und die
  Prüfung sonst per Zufall bestünde.
- **Gezeichnet aus `main()`, nicht aus dem Panel**, und das ist eine Z-Order-Entscheidung: der
  Missionsstreifen fährt von der Panelkante über das Brett aus und malte über einen früher im Frame
  gezeichneten Kasten. Neben der Datacard gezeichnet erbt er außerdem deren Modal-Unterdrückung —
  `_modal_up` ist jetzt EIN Ausdruck, den beide lesen.
- **WESSEN Stratagem es ist, kommt von der GEWÄHLTEN Einheit, nicht davon, wer am Zug ist:** die
  reaktiven (Fire Overwatch, Heroic Intervention, die Fate dice) werden im GEGNERzug gekauft, und
  in der falschen Armee nachzuschlagen fände nichts — genau dann, wenn man es am dringendsten
  braucht. **Die Laufzeit-Sonde hat das selbst vorgeführt:** ihre erste Fassung spritzte ein
  Aeldari-Stratagem auf eine Necron-Einheit und meldete `(NECRONS) -> 0 printed blocks`.
- **Kein gedruckter Eintrag, kein Kasten.** Die Core-Stratagems (Command Re-roll, Epic Challenge,
  Insane Bravery, Explosives, Crushing Impact) stehen in keiner Detachment-Datei; ein leerer Kasten
  wäre schlechter als keiner, und der Knopf sagt seinen Preis ohnehin selbst.

**Getestet:** neu `test_stratagem_tooltip.py` (**70/70**, sechs Abschnitte) plus
`ab_stratagem_tooltip.py` (**10 A/B-Sonden, alle beißend**). `test_army_rules_overlay.py`
**106/106**, `test_fight_end_turn_warning.py` **47/47** (sein Modal-Gate-Zähler geht 3 → 4 — genau
die sichtbare Änderung, für die er da ist: eine neue Ansicht, die die Modal-Liste vergisst, ist
das, was er fangen soll).
**Drei Befunde über den TEST** (Fehlerklasse 24), alle von den Sonden: zwei Sonden ließen die Suite
ABSTÜRZEN statt rot zu werden (Indizieren in eine leere Liste, `.name` auf None, `Rect.contains`
auf None) — **fünfte, sechste und siebte Instanz** derselben Lehre —, und die
Rect-Identitäts-Sonde biss zuerst nicht, weil die Bühne ein interniertes String-Literal
wiederverwendete.

**Im ECHTEN Spiel belegt** (`verify_stratagem_tooltip.py`, `runpy` auf `selfplay.py`s echte
`main()`-Schleife): `TOOLTIP: 'Sudden Storm' (NECRONS) -> 6 printed blocks, drawn=True` —
also auch der SUFFIX-Treffer im echten Lauf. `--neutralize` meldet `never opened`.
**Die Sonde braucht drei Zutaten, die dieser Harness nicht selbst herstellt**, und sie sind
einzeln benannt statt stillschweigend gefälscht: eine gewählte Einheit, ein diese Phase nutzbares
Stratagem, und ein Dwell ohne offenen Prompt (die KI öffnet alle paar Frames einen, was den
Tooltip zu Recht unterdrückt). Alles danach ist echt — das echte `_draw_button` zeichnet auf,
`main()` pollt, die Suche liest den echten Korpus.

### Missionskarten: lesbarer (game/ui/mission_cards.py)

User: "auch auf den missionskarten. die sind gerade sehr schwer lesbar. die
sollten etwas aufgeräumter und besser lesbarer sein."

- **Die URSACHE war nicht die Schriftgröße, sondern eine stille
  Monospace-Annahme.** Die Info-Zeilen waren EINE Zeichenkette mit per
  LEERZEICHEN hinübergeschobenem Wert (`"WHEN     end of your turn"`,
  `"%-12s"`) — das richtet sich nur in einer nichtproportionalen Schrift aus,
  und `config.FONT_NAME` ist `None`, also pygames proportionaler Default
  (gemessen: `WWWW` 37 px gegen `iiii` 12 px). Dazu trennt `wrap_text()` an
  LEERZEICHEN, also verlor die eine Zeile, die lang genug zum Umbrechen war
  (gemessen 323 px gegen 226 px Kartenbreite), ihren Einzug KOMPLETT und las
  sich als neuer Satz.
- **`info_rows()` gibt `(LABEL, value)`-PAARE**, auf beiden Kartenklassen;
  `info_lines()` bleibt als Verflachung DARAUS gebaut, also können die zwei sich
  nicht widersprechen. Das Panel legt daraus zwei echte Spalten — ein
  umgebrochener Wert bleibt in seiner eigenen Spalte.
- Dazu: Karte 250 → **320 px**, Fließtext `FONT_SIZE-4` → **-3**, mehr
  Zeilendurchschuss, und je eine Haarlinie zwischen Metadaten / gedrucktem Text
  / Detail — vorher lief alles als ein Prosablock zusammen, weshalb man den
  Missionstext lesen musste, um zu finden, wo die Antwort auf "wann wertet das"
  aufhört.
- **`_last_content_bottom`** wird beim Zeichnen mitgeschrieben, damit der Test
  die VORHERSAGE (`_full_height()`) gegen das GEZEICHNETE prüfen kann. Ein
  umgebrochener Info-Wert verschiebt alles darunter — genau der Fehler, dem
  dieses Layout am stärksten ausgesetzt ist. **Der Vergleich hat sofort einen
  echten Fehler gefunden:** beide Blöcke tragen einen abschließenden
  `INFO_ROW_GAP` in ihrer eigenen Höhe, den das ZEICHNEN als Anlauf zur
  Trennlinie wieder ausgibt — die Messung zählte ihn doppelt und reservierte je
  Block 3 px zu viel.

### Die Wertungstabelle: Was | Wann | VP

**Nachtrag desselben Berichts** (User: "könntest du hier absätze unten einbauen,
was wieviele punkte gibt? und vielleicht punkte und text tabellarisch trennen?
so im fließtext ist die information sehr unübersichtlich. vielleicht eine kleine
tablle / Was | Wann | VP"). Betrifft die PRIMARY-Karte: sie hat als einzige
mehrere Wertungsboxen, und deren Raten standen ausschließlich im Fließtext.

- **`ScoringBox.vp` ist PFLICHT, ohne Default.** Eine Box, die ihre Rate
  vergisst, zeichnete eine leere Zelle — und eine leere VP-Zelle liest sich als
  "zahlt nichts". Ein STRING, keine Zahl: die Hälfte der Boxen zahlt keinen
  festen Betrag ("3 or 6", "1/unit", "3/obj, +2"), und `score(ctx)` kann die
  Frage auch nicht beantworten — es braucht ein lebendes Brett, während die
  Karte ihre Rate nennen muss, bevor irgendetwas passiert ist. **Jede ist aus
  DERSELBEN Modulkonstante gebaut, die ihre Score-Funktion liest**, also können
  gedruckte und gezahlte Rate nicht auseinanderlaufen.
- **`scoring_rows()` ist von `info_rows()` GETRENNT**, nicht als dritte Spalte
  angehängt: das sind zwei verschiedene ARTEN von Zeile. `info_rows()` sind
  einmalige Tatsachen über die Karte (Disposition, Objective Action),
  `scoring_rows()` ist die wiederkehrende Preisliste. Zusammengelegt teilte
  sich jede Wertungsbox ein Spaltenlayout mit einem Fließsatz über eine Aktion,
  und die VP-Spalte hätte nirgends gefluchtet.
- **"Was" ist das gedruckte Box-LABEL, keine Zusammenfassung ihrer Bedingung.**
  Die Bedingung ist der gedruckte Text darunter; sie in eine Zelle zu
  paraphrasieren wäre exakt die "selbst generierte Variante", die eine Meldung
  vorher aus der Datacard entfernt wurde.
- **`text_utils.split_paragraphs()` ist VERLUSTFREI**, und das ist die tragende
  Zusicherung: `" ".join(result)` ist immer die whitespace-normalisierte
  Eingabe, es ändert sich also kein Wort — Umbrechen ist eine Zeile davon
  entfernt, Umschreiben zu werden. Gemessen über JEDEN Missionstext des Repos
  (5 Primary, 17 Secondary): 2-4 Blöcke je Karte, 0 verlustbehaftet. `6"` und
  `Rounds 1-2` tragen keinen Punkt, brechen also nicht.
- **Die VP-Spalte ist rechtsbündig in fester Spalte** — nur dann sind die Zahlen
  eine Zahlen-SPALTE, und das ist der ganze Grund, sie aus der Prosa zu holen.
  Im Test an PIXELN gemessen: die rechten Kanten clustern, die linken streuen
  (Linksbündigkeit zeigte genau das Gegenteil). Die Toleranz ist die
  Glyphen-BREITE, nicht Schlamperei: die Zellen werden bündig geblittet, aber
  "6", "t" und "3" enden je ein paar antialiaste Pixel vor ihrer eigenen Kante
  (gemessen 5 px).
- **Nur die Primary hat die Tabelle.** Eine Secondary hat EINEN Zeitpunkt und
  eine Score-Funktion, also keine Boxen, aus denen sich eine Preisliste bauen
  ließe; ihre Stufen stehen in der Prosa (die jetzt ebenfalls in Absätzen
  gesetzt ist) und ihr aktueller Wert auf dem Balken. Benannte Grenze —
  `scoring=()` ist der Haken, an dem sie später andocken kann.
- **Drei eigene Testfehler, alle von den eigenen Prüfungen gefunden:** die
  VP-Spalte wurde per "Tinte nahe dem rechten Rand" gesucht und fing damit den
  gerundeten KARTENRAHMEN und den umgebrochenen Text der WANN-Spalte mit; und
  die waagerechten Tabellen-LINIEN zählten als Zellen. Gescannt wird jetzt der
  x-Bereich der Spalte selbst, und eine Zeile, deren Tinte die ganze Spalte
  überspannt, ist eine Linie und keine Zelle.

### Die Waffentabelle druckte den PLATZHALTER, nicht die gewürfelte Notation

**Gemeldet:** *"in den infos stehen völlig falsche schadenswerte ... shard of the voiddragon: void
spear w6+2 statt 8 / Plagueburst Crawler: entropy cannon w6+1 statt 4 / BLight hauler multimelter
w6 statt 3. sind diese fehler echt oder nur anzeige fehler? wenn die fehler echt sind, dann müsste
dringend mal alle stats gegengecheckt werden."*

**ANZEIGEFEHLER für die drei gemeldeten — die Würfel waren die ganze Zeit richtig.** Und der
Gegencheck, der das belegen sollte, hat **dreizehn ECHTE** Datenfehler gefunden, die niemand
bewachte. Zwei verschiedene Befunde aus einer Meldung.

- **Die Ursache ist ein zweites Feld, das dieselbe Frage anders beantwortet** (Fehlerklasse 10 in
  Reinform, nur sichtbar auf dem Bildschirm): drei Charakteristiken können eine WÜRFELZAHL sein
  (`attacks_notation`, `strength_notation`, `damage_notation`), und daneben steht ein flacher
  `attacks`/`strength`/`damage`-int, den jedes der drei Felder im eigenen Kommentar als
  **grouping/preview placeholder** ausschreibt. `unit_datacard.py:572` druckte genau diesen
  Platzhalter. Die echte Auflösung würfelt die Notation (`damage_resolution.py`s
  `pending_damage_roll`, `ShootingController`s "attacks"/"strength"-Schritte) — Spiel richtig,
  Karte falsch.
- **Es traf ALLE 106 Waffen mit Notation und ALLE DREI Spalten**, nicht die drei gemeldeten: der
  Void-Dragon-Speer zeigte auch **A=1 statt D3**, die Voltaic Storm **A=1 statt D6+3**, die Zzap Gun
  **S=9 statt D6+6**. Die A- und S-Hälfte hatte niemand bemerkt.
- **`printed_characteristic(weapon, which)` ist die eine Antwort** und liest
  `dice_notation.describe()` — die Definition, wie eine Notation gedruckt wird, gab es längst, die
  Karte hat sie nur nie benutzt.

### Der Gegencheck: 3732 Waffenwerte gegen den Korpus

`verify_rules_vs_engine.py` prüfte Statlines, Basen, Punkte und Rettungswürfe — **Waffenwerte gar
nicht**. Genau dort saß der Fehler, und dort saßen dreizehn weitere.

- **Zwei Dinge muss der Vergleich richtig machen, sonst ertrinkt er in Fehlalarmen** — beide
  teuer gelernt: WS/BS liegen am PROFIL, nicht an der Waffe (eine Waffe trägt nur dort einen
  Override, wo ihre gedruckte Zeile ihrem Träger widerspricht), also wird override-else-profile
  aufgelöst wie `effective_ballistic_skill()`; und wo eine Notation gesetzt ist, wird SIE
  verglichen, nicht der Platzhalter — sonst meldet der Prüfer jede Notations-Waffe als falsch und
  macht denselben Fehler wie die Karte. Meine erste Fassung tat beides falsch und meldete 314
  Abweichungen statt 13.
- **Eine Waffe, deren gedruckte Zeile nicht gefunden wird, wird GEMELDET, nicht übersprungen** —
  ein gedrifteter Name ist genau der Weg, auf dem eine Waffe aufhört, verglichen zu werden.
- **[TORRENT] mit gedrucktem BS "N/A" ist ÜBEREINSTIMMUNG, keine Abweichung** (24.37: kein
  Trefferwurf, die Fertigkeit wird nie gelesen). Alle 35 zu melden ist, wie ein Bericht aufhört,
  gelesen zu werden; eine Waffe, die N/A druckt und NICHT torrent ist, fällt weiter durch.

**Die dreizehn echten Fehler, alle behoben:**

| Waffe | gedruckt | Engine | Wirkung |
|---|---|---|---|
| Dark Reapers' Missile launcher – starshot | D6 | **flache 6** | fast doppelter Schaden |
| Farseer / Skyrunner Eldritch Storm | BS 3+ | 2+ (Profil) | traf zu gut |
| Firesight Team Pulse pistol | BS 3+ | 4+ (Profil) | traf zu schlecht |
| Commander Shadowsun Pulse pistol | BS 3+ | 2+ (Profil) | traf zu gut |
| Corsair Voidreavers Wraithcannon | BS 3+ | 4+ | traf zu schlecht |
| Voidscarred Close combat weapon | A3 | A2 | ein Angriff fehlte |
| Voidscarred Power sword (3 Zeilen) | A3 | A2 | ein Angriff fehlte |
| Voidscarred Paired Hekatarii blades | A4 / WS2+ / AP-2 | A5 / 3+ / -1 | drei Werte |

- **Vier davon brauchten eine EIGENE KLASSE, keine Wertänderung** — die Klasse ist geteilt, und die
  anderen Träger sind richtig: `PowerSwordProfile` tragen auch Storm Guardians und Voidreavers
  (beide A2), `AeldariCloseCombatWeaponA2Profile` elf Datenblätter, `WraithcannonProfile` auch die
  Wraithguard (4+), `PulsePistolProfile` fünf T'au-Datenblätter (drei davon zu Recht bei 4+). Das
  ist die Rezept-Regel "gleicher Name, andere Zahlen → eigene Klasse", und sie wird geerbt mit nur
  der abweichenden Zahl überschrieben, damit die zwei gegeneinander gepinnt bleiben.
- **Der Dark-Reaper-Fund hatte eine FALSCHE BEGRÜNDUNG im eigenen Docstring**, und die hat den
  Fehler getarnt: "D6 where that one is D3" — beide drucken D6, und der flache `damage = 6` war,
  was die zwei unterscheidbar aussehen ließ. Was sie wirklich trennt, ist [IGNORES COVER]. Der
  zugehörige Pin verglich die zwei PLATZHALTER (6 gegen 3) und war deshalb grün.

**Der Riptide fieldet zwei Waffen, die sein Datenblatt nicht druckt** (2× Missile Drone; die
11th-Edition-Zeile hat gar keine Drohnen) — eine ZUSAMMENSETZUNGS-, keine Wertfrage, deshalb
benannt statt still entfernt. Ebenso die sieben reinen Namensdrifts (`Grot-Smacka` für "Runtherd
tools", `Spiked Wheel` für "Spiked wheels", `- Overcharge` für "– supercharge", `Plasma Gun` für
"plasma gun – standard", und 5× `Missile Launcher - Sunburst Blast`, wo "blast" das KEYWORD ist) —
bei allen stimmen die Zahlen exakt.

### Getestet

- **`test_weapon_characteristics.py` (neu, 8/8) ist eine SUITE, wo `verify_rules_vs_engine.py` ein
  Bericht bleibt**, und das ist der tragende Unterschied: der Bericht existiert, weil Punkte und
  Basen PER STEHENDER ENTSCHEIDUNG abweichen. Für Waffenwerte gibt es keine solche Entscheidung —
  nach den Fixes sind es **null** Abweichungen —, also lässt sich der Rat des Berichts ("was NICHT
  bewusst gewählt war") hier erzwingen statt drucken. Der Vergleich wird IMPORTIERT, nicht kopiert.
  Die Ausnahmeliste ist namentlich begründet, und **ein Eintrag, der nichts mehr abdeckt, fällt
  ebenfalls durch** — eine abgelaufene Ausrede darf nicht ewig stehen bleiben.
- **Ein Vakuum-Wächter gehört dazu**: ein Sweep, der aufhört, Waffen zu finden, meldet null
  Abweichungen und sieht aus wie ein Bestehen. Eigene Sonde dafür.
- `test_unit_datacard.py` 65 → **76/76** (Abschnitt 9: die drei gemeldeten Waffen, die GANZE
  gezeichnete Zeile in Reihenfolge statt "D6+2 kommt irgendwo vor" — die Stärke des Speers IST 8,
  eine Karte mit dem Platzhalter enthielte also weiter eine 8 und weiter ein D6+2 aus der
  Nahkampfzeile), `test_dark_reapers.py` **80/80** (der Pin, der den Fehler festschrieb, umgedreht).
- **Neu `ab_weapon_characteristics.py`: 16 A/B-Sonden an der QUELLE, alle beißend.** **Zwei bissen
  zuerst NICHT, beide Fehlerklasse 24:** die S-Spalten-Sonde, weil die gepinnte Speer-Zeile eine
  flache 8 hat und die Spalte gar nicht prüfte (jetzt zusätzlich die Zzap Gun, die einzige Waffe
  mit Notations-STÄRKE); und "ein gedrifteter Name wird still übersprungen", weil jeder Drift auf
  der Ausnahmeliste steht und deshalb gar nichts angehängt wurde (jetzt wird eine AUSNAHME
  entfernt, was einen echten Drift erzeugt). Dazu ein Test, der unter einer Sonde ABSTÜRZTE statt
  rot zu werden (`describe(None)`) — sechste Instanz dieser Lehre, jetzt degradiert er.
- **Im ECHTEN Spiel belegt** (`verify_weapon_card_values.py`, `runpy` auf `selfplay.py`s echte
  `main()`-Schleife, Necrons gegen Death Guard, damit alle drei gemeldeten Waffen auf dem Brett
  stehen): 177 Waffentabellen auf echten Frames, 48 Waffen, und alle drei melden ihren gedruckten
  Wert. **`--neutralize` reproduziert den Bericht wörtlich: 8, 4, 3.** Gestaget ist NUR der Hover
  (ohne Maus ist `hovered_token` in jedem Frame None — ein passiver Zähler hätte 0 gezeichnete
  Karten gemeldet und wie ein Bestehen ausgesehen; die erste Fassung dieser Sonde tat genau das).
- Volle Regression **182 Suiten, ~15922 Prüfungen, 181 grün / 0 rot / 1 bekannt**,
  `run_tests.py --smoke` komplett grün.

**Benannt, nicht mitgeändert: die Platzhalter sind untereinander uneinheitlich**, und
`damage_estimate.py:231` liest genau sie. Manche sind das MAXIMUM des Würfels (Void-Dragon-Speer 8
für D6+2, Fusion Blaster 6 für D6), manche der MITTELWERT (Zzap Gun 9 für D6+6, laut eigenem
Docstring). Die KI überschätzt damit einen Max-Platzhalter um bis zu 71 %, was ihre Zielwahl
verzerrt. Das ist eine eigene Messreihe wert (es verschiebt die Zielwahl armeeweit) und keine
Nebenwirkung dieser Anzeigekorrektur.

### Die Waffentabelle druckte auch die KEYWORDS nicht

**Gemeldet:** *"in den weapon info tabellen im overlay fehlen die keywords (zb twin linked oder
sustained hits)."* Die Tabelle zeichnete Range/A/BS/S/AP/D und hörte da auf — also stand die
HÄLFTE einer Waffenzeile, die entscheidet, wie sie sich verhält ([TORRENT] heißt gar kein
Trefferwurf, [TWIN-LINKED] ein Reroll, [DEVASTATING WOUNDS] Wunden, die den Save überspringen), an
KEINER Stelle des Spiels auf dem Schirm.

- **`weapons.printed_keywords(weapon)` ist die EINE Definition** von "wie wird die Keyword-Spalte
  dieser Waffe gedruckt", und sie liegt bei den Flags, die sie liest, nicht in der Karte, die sie
  zuerst brauchte — ein zweiter Konsument (Tooltip, Loadout-Liste, ein künftiger Waffen-Picker)
  stellt dieselbe Frage und muss dieselbe Antwort bekommen.
- **`weapons.anti_entries()` ist die 31. Extraktion, am zweiten Konsumenten:** "wie liest man
  `WeaponProfile.anti`" lag als `_anti_entries` in `shooting.py`. `shooting.py` re-exportiert es
  unter dem alten privaten Namen, es gibt also weiter EINE Definition und keine Aufrufstelle
  bewegt sich.
- **ALPHABETISCH, weil das die gedruckte Reihenfolge ist — gemessen, nicht angenommen:** von den
  35 verschiedenen Mehr-Keyword-Zeilen in `rules/*.md` sind **alle 35** sortiert.
- **Die Keywords stehen UNTER den Zahlen, nicht in einer achten Spalte, und die Breite ist der
  Grund:** die breiteste Keyword-Zeichenkette, die eine gebaute Waffe druckt
  (`ANTI-INFANTRY 2+, BLAST, HAZARDOUS, IGNORES COVER, PSYCHIC`), misst **346 px** — passt also in
  die 432 px breite Tabelle auf EINE Zeile und hätte in der 132-px-Namenszelle **vier** gebraucht.
  Eine Waffe ohne Keywords kostet ihre Zeile nichts.
- **Die Spaltentrenner enden am Zahlen-Band** (`_weapon_band_height()`): eine senkrechte Linie, die
  durch die Keyword-Zeile weiterläuft, zerschneidet sie in Stücke, die zu Spalten gehören, mit
  denen sie nichts zu tun haben. Dazu eine waagerechte Linie ZWISCHEN den Waffen — mit einem
  Keyword-Band unter manchen Zeilen und unter anderen nicht ist "wo endet diese Zeile" aus den
  Zahlen allein nicht mehr ablesbar.
- **NICHT gedruckt wird, was die Engine nicht durchsetzt:** Dead Choppy, Snagged und Linked Fire
  sind drei datenblatt-spezifische Waffen-Fähigkeiten, die dieses Repo bewusst nicht modelliert
  (jede dort dokumentiert, wo ihre Waffe definiert ist). Sie stehen als benannte Ausnahmen im
  Sweep statt auf der Karte: jedes Keyword, das die Karte zeigt, ist eines, das die Engine wirklich
  anwendet — der Handel ist benannt, weil er in beide Richtungen vertretbar ist (diese drei stehen
  im Korpus AUSSCHLIESSLICH in der Keyword-Spalte, ein Spieler erfährt sie also nirgends).

**Und der Vergleich hat FÜNF echte Engine-Fehler gefunden — genau die Form, in der der
Charakteristik-Sweep dreizehn fand.** Die `Keywords`-Spalte lag seit dem Bau des Korpus in
`rules/*.md` und hatte **keinen einzigen Leser**:

| Waffe | gedruckt | Engine | Wirkung |
|---|---|---|---|
| Corsair Voidscarred, Paired Hekatarii Blades | twin-linked | — | rerollte gar nichts |
| Defiler, Ectoplasma Destructor | blast, lethal hits | lethal hits | kein [BLAST] gegen große Einheiten |
| Jain Zar, Silent Death | assault | assault, anti-infantry 3+ | krittete gegen Infanterie auf 3+ |
| Myphitic Blight-hauler, Missile Launcher – krak | *(leer)* | lethal hits | Auto-Wound, den die Zeile nicht druckt |
| The Twin Lance, XV Pulse Pistol | rapid fire 2 | rapid fire 2, pistol | durfte aus dem Nahkampf feuern |

- **Zwei Pins hatten den Fehler als Regel protokolliert** und sind umgedreht: `test_jain_zar.py`
  (dessen Kommentar festhielt, die zwei Zeilen sähen vertauscht aus und die Frage sei deshalb
  GESTELLT worden — der Korpus ist die Seite selbst, und die stehende Entscheidung dieses Repos
  ist, dass die Transkription gewinnt) und `test_twin_lance.py` (dessen Docstring aus dem NAMEN
  der Waffe herleitete, sie sei [PISTOL] — eine Zeile darüber druckt das Shardstorm burst system
  wirklich "pistol", die Seite unterscheidet die beiden also).
- **Ein Docstring behauptete das GEGENTEIL der Seite** und ist mitkorrigiert: der
  Blight-hauler-Frag sagte wörtlich, seine Keyword-Spalte sei leer und nur der Krak trage
  [LETHAL HITS]. Gedruckt ist es andersherum — der FRAG trägt [BLAST], der Krak nichts. Beide
  Hälften sind gefixt, und die Notiz bleibt stehen, weil ein Kommentar, der eine geprüfte Tatsache
  behauptet, genau das ist, was den nächsten Leser vom Prüfen abhält.

**Getestet:** `test_weapon_characteristics.py` 8 → **23/23** (Abschnitt 5 der Korpus-Sweep über
**627 Keyword-Spalten**, mit Vakuum-Wächter und nicht verrottbarer Ausnahmeliste, Abschnitt 6 die
fünf Fixes namentlich, Abschnitt 7 die Schreibweise der VALUE-Keywords — [ANTI-X], die
Würfel-[SUSTAINED HITS D3], die alphabetische Ordnung, plus die Gegenprobe, dass eine Waffe ohne
Keywords keine druckt); `test_unit_datacard.py` 76 → **89/89** (Abschnitt 10 auf PIXELN: die
gemeldeten Keywords auf einer echten Einheit, ein Band pro Waffe die welche HAT und keins für die
übrigen, die Zeilenhöhen-Buchführung, kein Trenner durch eine Keyword-Zeile, und die 346-px-Messung
selbst). **Neu `ab_weapon_keywords.py`: 20 A/B-Sonden an der QUELLE, alle beißend.**
`ab_weapon_characteristics.py` **16/16** (ein Anker musste nachziehen).
Volle Regression **189 Suiten, ~16771 Prüfungen, 188 grün / 0 rot / 1 bekannt**.

**Im ECHTEN Spiel belegt** (`verify_weapon_card_keywords.py`, `runpy` auf `selfplay.py`s echte
`main()`-Schleife, Necrons gegen T'au — damit beide gemeldeten Keywords auf dem Brett stehen):
**226 Waffentabellen auf echten Frames, 28 Waffen mit Keyword-Band, 14 529 keyword-farbene Pixel**
auf der LEBENDEN Screen-Surface, `Voltaic Storm -> BLAST, SUSTAINED HITS 2` und
`Twin Pulse Carbine -> ASSAULT, TWIN-LINKED`. `--neutralize` meldet **0 Bänder und 0 Pixel**.
Gestaget ist nur der Hover (ohne Maus ist `hovered_token` in jedem Frame None — die dokumentierte
Harness-Grenze); gezählt werden PIXEL und nicht nur Render-Aufrufe, weil ein Render beweist, dass
gerendert wurde, und erst die Farbe, dass es auf dem Schirm steht.

**BENANNT, nicht mitgeändert:** die Myphitic Blight-hauler fieldet ihren FRAG-Werfer gar nicht (das
Datenblatt druckt beide Zeilen, `weapon_pairs()` findet nur den Krak). Eine ZUSAMMENSETZUNGS-Frage
wie der Missile Pod des Riptide, keine Keyword-Frage.

### Getestet

- Neu `test_rules_text.py` (**38/38**) und `test_unit_datacard.py` (**65/65**);
  `test_mission_cards_ui.py` 54 → **102/102** (Abschnitt 8 der Info-Block,
  Abschnitt 9 die Wertungstabelle — beide auf PIXELN: jede Zeile beginnt in
  einer der Spalten, beide werden benutzt, ein umgebrochener Wert behält seine
  Spalte auf JEDER Zeile, und die VP-Zellen teilen sich eine rechte Kante,
  während ihre linken streuen). `test_primary_missions.py` 261 → **264/264**.
  **Zur Datacard gab es vorher GAR KEINEN Test** — deshalb konnte eine Karte,
  die unten aus dem Fenster wächst, unbemerkt bleiben.
- **Neu `ab_datacard_rules.py`: 18 A/B-Sonden an der QUELLE, alle beißend.**
  **ZWEI bissen zuerst NICHT, und beide waren ein Befund über den TEST**
  (Fehlerklasse 24): zur Missionskarten-Lesbarkeit gab es überhaupt keine
  Prüfung — die alte Suite maß den Info-Block nie. Abschnitt 8 ist die Antwort
  darauf, und danach kippen beide.
- **Ein fremder Pin wurde zu Recht rot** (`test_fight_end_turn_warning.py`): er
  ZÄHLTE die Zeichenkette `"and not fight_warning_overlay.is_pending"` == 3, und
  das Datacard-Tor ist jetzt ein Early-out mit umgekehrtem Vorzeichen — dasselbe
  Tor, andere Interpunktion. Vierte Instanz derselben Lehre (`.index()`, die
  schließende Klammer, der Namenszähler). Er prüft jetzt die BEDEUTUNG, nennt
  das Datacard-Tor beim Namen, und ist per A/B belegt (Tor entfernt → 44/46 und
  beide Zeilen nennen es).
- Ein zweiter fremder Pin wurde zu Recht rot: `test_primary_missions.py` pinnte
  die Box-Zeitpunkte in `card.info` — die sind in die Wertungstabelle
  umgezogen. Er stellt dieselbe Frage jetzt an `card.scoring` und prüft
  zusätzlich, dass keine Box eine leere VP-Zelle hat.
- Volle Regression **166 Suiten, ~14587 Prüfungen, 165 grün / 0 rot /
  1 bekannt**, `run_tests.py --smoke` komplett grün, dazu
  `smoke_measure_tool.py`, `smoke_end_turn_warning.py`,
  `smoke_primary_mission.py` und `selfplay.py map3`.
- **Im ECHTEN Spiel belegt, nicht nur im Test** — "gebaut, aber nie GEFÜTTERT"
  hat dieses Repo sechsmal getroffen, und ein Quell-Wächter zeigt nur, dass der
  Aufruf DASTEHT. Zwei Spione durch die echte `main()`-Schleife
  (`selfplay.py map2`): die Datacard meldet **1199 Polls (einen pro Frame), 1183
  Zeichnungen und 5915 gerenderte Abilities**; der Missionsstreifen über 900
  Frames **899 Kartenzeichnungen, 3596 gezeichnete Wertungszeilen** (Secure
  Assets vier Boxen mal 899) **und 2697 Absätze**.

## Missionen (game/missions.py, game/secondary_missions.py)

### Die erste Schlachtrunde zahlt keine Primary-VP

**`missions.PRIMARY_FIRST_SCORING_ROUND = 2`** (User: "außerdem sollte man im ersten zug noch keine
vp für objectives bekommen. erst ab zug 2").

- **Das ist Hold the Line, das nachzieht, was jede Force-Disposition-Karte längst DRUCKT.** Alle
  fünf banden ihre Objective-Boxen auf "2ND ROUND ONWARD" (`primary_missions.SECOND_ROUND_ONWARD`);
  die Standard-Primary war die EINZIGE, die noch für das Brett zahlte, wie es nach der Aufstellung
  stand — wer auf drei Objectives aufstellte, hatte eine volle Runde VP, bevor ein Modell gezogen
  war. Im Test gegen `SECOND_ROUND_ONWARD` gepinnt, nicht gegen ein Literal.
- **BENANNTE AUSNAHME, bewusst stehengelassen:** Battlefield Dominances "MORE OBJ"-Box ist auf ihrer
  Karte "Rounds 1-2" gedruckt, und eine transkribierte Regel gewinnt gegen diese hier. Als eigene
  Testzeile festgehalten, damit sie nicht wie eine übersehene Stelle aussieht.
- **`battle_round` hat KEINEN Default** — dieselbe Begründung wie bei `_detectable_models()`: eine
  Aufrufstelle, die es vergisst, wäre still wieder der gemeldete Fehler und kein kleinerer. Alle drei
  `main.py`-Aufrufe reichen `turn_tracker.battle_round`; ein Quell-Wächter liest die AUFRUFAUSDRÜCKE
  und würde einen vierten mit hartkodierter Runde melden.
- **Beide KI-Prompts sagen es jetzt** ("round 1 pays nothing, so round 1 is for getting onto the
  objectives, not for sitting on the ones you deployed on"). Der Planner wägt Boden gegen Kills mit
  genau dieser Arithmetik ab — eine Rundenbande, die nur die Engine kennt, ist jeden Zug ein
  falscher Plan, und nichts im Spiel widerspricht ihr.
- **Getestet:** `test_standard_missions.py` 33 → **44/44** (neuer Abschnitt 1b, beide Seiten der
  Grenze gemessen — "< 2" als "< 3" geschrieben bestünde sonst mit); drei A/B-Sonden in
  `ab_pregame_starts_once.py`, alle beißend. **Im ECHTEN Spiel belegt:**
  `verify_pregame_starts_once.py` meldet in Runde 1 `none`, `--neutralize` meldet die Zahlungen.

### Die Raten der Standard-Missionen (User-Handicap zugunsten der KI)

**Hold the Line zahlt 6 statt 3, No Mercy 3 statt 1** (User: "ändere die Missionen der ki leicht.
primary gibt 6 Punkte pro objektive, statt 3. und secondary gibt 3 statt 1").

- **"Die Missionen der KI" ist, was sie im AUSGELIEFERTEN Zustand sind — keine von beiden gehört
  einem Spieler.** Hold the Line spielt jeder, der NICHT in `config.PRIMARY_MISSION_CARD_PLAYERS`
  steht, No Mercy jeder, der nicht in `config.SECONDARY_MISSION_CARD_PLAYERS` steht — und beide
  Tupel nennen Player 1, den Menschen. Heute erreichen die Raten also nur die KI; leert ein Harness
  eines der Tupel, bekommt sie der Mensch auch. Steht als Kommentar an den Konstanten.
- **Die Zahl stand an VIER Stellen, und drei davon hätten still veralten können:** die Konstante,
  der gedruckte Kartentext auf dem Missionsstreifen, und BEIDE KI-Prompts. Der Kartentext und die
  Prompts interpolieren sie jetzt aus `game/missions.py`, statt sie zu wiederholen.
- **Der Prompt ist die gefährlichste davon.** Der Planner wägt Boden gegen Kills mit exakt dieser
  Arithmetik ab; eine veraltete Rate dort ist jeden Zug ein falscher Plan, und nichts im Spiel
  widerspricht ihr. Das wäre die Sorte Änderung, die fertig AUSSIEHT und es nicht ist.
- **Die Beratungsregel überlebt die Umstellung**, und das ist geprüft statt angenommen: "Boden zahlt
  wiederholt, ein Kill einmal" gilt bei 6/Runde gegen 3 einmalig weiterhin — nur der Wechselkurs
  verschiebt sich (ein Kill ist jetzt eine halbe Objective-Runde statt einer drittel).
- **Die Ökonomie-Tabelle weiter oben hat sich dadurch UMGEDREHT** — Hold the Line liegt jetzt vor
  den fünf Force-Disposition-Karten statt gleichauf. Bewusst: es ist ein Handicap-Regler, keine
  Balance-Messung. Dort ausgeschrieben, damit die alte Aussage nicht als Messung stehenbleibt.
- **Getestet:** neu `test_standard_missions.py` (**33/33**) — **zu diesem Modul gab es vorher GAR
  KEINEN Test**, die zwei Raten wurden nur nebenbei als Literale in drei anderen Dateien
  behauptet, was genau der Weg ist, auf dem eine Neujustierung halb ankommt. Abschnitt 3 ist der
  tragende: jede Stelle, an der eine Rate GEZEIGT oder ERZÄHLT wird, muss aus der Konstante kommen —
  mit der Gegenprobe, dass die ALTEN Zahlen nirgends mehr stehen ("quotes the new number" besteht
  auch auf einem Prompt, der beide enthält). Drei fremde Pins nannten die alte Rate als Literal und
  sind auf die Konstante umgestellt, also kostet die nächste Justierung EINE Zeile.
  Neu `ab_mission_rates.py`: **9 A/B-Sonden, alle beißend**, darunter die zwei, die nur die
  Prompts zurückdrehen.
- **Im ECHTEN Spiel belegt:** `selfplay.py map2` protokolliert
  `Player 2 scores 6 Primary point(s) (controls 1 objective(s))`.
- **Eigener Testfehler, der dabei auffiel und ein echtes Merkmal des Moduls ist:**
  `record_destroyed_squad()` dedupliziert über `id(squad)`, und ein inline erzeugtes Squad wird
  sofort wieder freigegeben — CPython vergibt dieselbe id an das nächste, drei Opfer zählten also
  als eines. Im echten Spiel harmlos (die Squads leben auf dem Brett), aber eine Falle für jeden
  Test, der das Modul direkt treibt.

Primary **"Hold the Line"** (**6** VP je kontrolliertem Objective, zu Beginn der eigenen
Command-Phase)
gilt für BEIDE Spieler, **außer für wen `config.PRIMARY_MISSION_CARD_PLAYERS` nennt** — der spielt
die Force-Disposition-Primary des Abschnitts darüber. `score_primary()` trägt den Early-out an
EINER Stelle, nicht an seinen drei Aufrufstellen. Die Secondary **"No Mercy"** (**3** VP je zerstörter
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
    und ich muss auf der Map mein Einheit anklicken"). **Seit dem 2026-09-04-Umbau ist das der
    GETEILTE Mechanismus** (`game/unit_pick.py`, siehe `## Einheiten auf dem Brett wählen`) und
    kein eigenes Pending-System mehr: `request_unit_pick()` legt eine gewöhnliche
    `DecisionManager`-Anfrage mit getaggten Optionen an und trägt ihr `subject` — das Objective —
    weil genau das die Frage ausmacht. Die Karte gewinnt dabei das BRETT-HIGHLIGHT, das ihr alter
    Screen im eigenen Docstring als fehlend vermerkt hatte.
    - **Der Klick MUSS vor dem generischen Board-Zweig gefangen werden**, sonst schluckt ihn die
      Kamera-Behandlung: Fehlerklasse 15, fünfmal im Repo verzeichnet. Er wird jetzt im
      `decision_manager.is_pending`-Zweig aufgelöst, der weit vor jedem Controller-State-Zweig
      steht; ein Quell-Wächter prüft beide Seiten dieser Klammer.
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
  - **"2ND ROUND ONWARD"** ist als `min_battle_round` modelliert und in `scores_at()` geprüft.
    **Unter dem heutigen Zeitpunkt kann es nie greifen** (die Karte wertet ohnehin nur in Runde 5),
    und genau das ist inzwischen ein OFFENER PUNKT statt einer Kuriosität: eine gedruckte Karte
    trägt keine Bande, die nie gilt. Der Wortlaut ist beim User erfragt — siehe
    `## Zwei Meldungen aus einer Partie`.
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
  mehr nicht (kein spekulatives System). Kein KI-Pfad: die KI behält ihre Standard-Missionen.
  (`scene_io` sicherte lange weder VP noch Hand noch Stapel — das ist seit dem Game Menu erledigt,
  siehe dort; die Grenze ist jetzt nur noch der Zeitpunkt: ein F9 MITTEN im Zug verliert eine
  angefangene Action, ein Rundengrenzen-Autosave nichts.)
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
    `Demon Price of Nurgle.png` (zwei Tippfehler in einem Dateinamen). **Das Fraktionslogo ist
    inzwischen da** (`Deathguard_Logo.jpg`) — wieder der Ordner: ein Wort mit Unterstrich, wo die
    anderen vier `<Fraktion> Logo` mit Leerzeichen heißen. Damit haben **alle fünf** Armeelisten
    ein Badge, geprüft an der DATEI statt an der Tabelle.
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
  - **Bewusst offen:** Signal Pox inert; die vier Enhancements bleiben reine
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
- **NUR REGELTEXT: Fluff und Beispiele werden beim SCRAPE verworfen** (User nach einer Partie:
  "keine hintergrund info texte und example texte in den armeeregeln bitte. nur reine
  regeltexte"). Beides ist von WAHAPEDIA SELBST markiert, wird also nicht geraten: `ShowFluff` ist
  die Klasse, an der die Seite ihren eigenen Fluff-Schalter hängt (die Lore über jeder Armeeregel,
  jeder Detachment-Regel und jedem Enhancement), `redExample` das durchgerechnete Beispiel unter
  einer Regel. Beide stehen jetzt in `SKIP_CLASSES` neben dem Errata-Umschalter — dieselbe
  Begründung, dieselbe Mechanik.
  - **Der Stratagem-LEGEND ist die eine Ausnahme und braucht einen zweiten Griff:** er wird per
    eigener Regex aus der Seite gehoben, die Klasse erreicht den Renderer also nie. Er wird
    deshalb gar nicht erst GELESEN (kein `legend` mehr in `STRATAGEM_FIELDS`). Der Untertitel
    (`*Seer Council - Battle Tactic Stratagem*`) bleibt — das ist keine Lore, sondern die
    Typ-Zeile.
  - **Am SCRAPE statt im Leser, und das ist die Entscheidung:** der Korpus existiert, damit
    `git diff` "hat GW diese Regel geändert?" beantwortet, und Fluff ist darin reines Rauschen;
    ein Leser-Filter müsste außerdem RATEN, welche Absätze Lore sind — ein Marker, dem er trauen
    könnte, wäre ohnehin hier zu schreiben.
  - **Gemessen, nicht behauptet:** 62 Dateien ändern sich, **1092 Zeilen weg**, und **0
    Datenblätter** sind betroffen (die tragen in ihren Ability-Abschnitten keine Lore) — die
    Hover-Datacard bleibt also unberührt. Jede entfernte Zeile ist gegen die gecachten Seiten
    zurückverfolgt: 545 von 545 sind ein `ShowFluff`- oder `redExample`-Block, der Rest des Diffs
    ist die ältere Force-Disposition-Zeile.
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
  Technomancer, Matter Absorption, Living Lightning, Wraith Form und alle sechs
  Awakened-Dynasty-Protokolle. **KORREKTUR: Plasmacyte stand hier zu Unrecht** — `use()` hat
  ueberhaupt keinen Aufrufer, die Faehigkeit ist fuer BEIDE Seiten unverdrahtet (siehe die
  KI-Weiche oben). Die drei proaktiven davon (Hungry Void, Sudden Storm, Conquering
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

## Ein API-Fehler stoppt die KI, nicht das Spiel (ai/connection.py)

**Gemeldet:** *"momentan stürzt das Spiel ab, wenn KI Modus an ist und die Verbindung verloren geht
oder api Fehler oder Guthaben leer. besser wäre eine Meldung 'Connection lost' und das Spiel geht
aber ohne KI weiter."*

**Reproduziert durch die ECHTE `main()`-Schleife**, bevor etwas geändert wurde: ein Agent, der beim
ersten Aufruf `anthropic.APIConnectionError` wirft, beendet den Lauf mit
`CRASHED OUT OF main(): APIConnectionError` bei **0 weiteren Frames**.

- **Der PLANNER war längst abgesichert** (`except Exception ... out["error"]`, mit dem Kommentar
  „the whole point is to not crash the game"); der taktische `agent.decide()`-Aufruf war es nicht.
  Ein Abfangen an genau einer der beiden Stellen ist die Form, die dieses Repo als
  Fehlerklasse 10 führt.
- **`ai/connection.py` beantwortet EINE Frage** — ist der Agent erreichbar, und wenn nicht, warum.
  Vier Ausfälle interessieren einen Spieler (tote Verbindung, abgelehnter Key, leeres Guthaben,
  Rate Limit) und das SDK schreibt sie als vier Typen plus eine Statusfamilie; die Reaktion des
  Spiels ist auf alle vier dieselbe. Also eine Antwort statt einer Taxonomie, auf die nichts
  verzweigt.
- **`connection.ask(call, *args)` ist die EINE Grenze zwischen Engine und Agent** — und sie liegt
  dort und nicht in `ai/claude_agent.py`, weil `agent` ein INTERFACE ist (`ai/base.py`): nur den
  Anthropic-Client abzusichern ließe jede andere Implementierung (MockAgent, ein späteres lokales
  Modell, ein Harness-Stub) das Spiel weiter abstürzen. **Genau drei Aufrufstellen** (ein
  `decide`, zwei `plan_turn`) — die ganze Außenfläche der Engine, im Test gezählt.
  **Erst am Agenten gebaut, dann verschoben:** die erste Fassung saß in `ClaudeAgent`, und die
  Reproduktion (die MockAgent benutzt) stürzte weiter ab — der Beweis, dass die Grenze das
  Interface ist und nicht die eine Implementierung.
- **`except Exception`, bewusst, aber ENG UMSCHLOSSEN.** Eine Liste von anthropic-Klassen ließe den
  fünften Typ weiter krachen, was genau der gemeldete Fehler ist; `describe()` NENNT dafür jeden
  unerwarteten Typ beim Namen, statt ihn als „no connection" zu verkleiden — sonst schickt ein Bug
  im Agenten jemanden zum Router. Umschlossen ist nur der Agent-Aufruf: `take_one_action()` fängt
  **ausschließlich `AIUnavailable`**, also stürzt ein echter Handler-Bug weiter laut ab. Eine
  stillschweigend übersprungene KI-Runde ist viel schwerer zu bemerken als ein Traceback.
- **EIN LATCH, kein Retry.** Jeder dieser Ausfälle hält länger als einen Frame, und die Schleife
  fragt den Agenten bei Auto-Play mehrmals pro Sekunde: ein Wiederversuch machte aus einer
  verlorenen Verbindung einen Strom von Timeouts, jeder davon ein hängender Frame. `take_one_action()`
  prüft `is_online()` deshalb VOR dem Aufruf, nicht nur danach. Der ERSTE Fehler ist außerdem der
  einzig informative — jeder weitere ist seine Folge —, also gewinnt er.
- **Die Meldung sagt, was jetzt zu tun ist.** „Connection lost" allein ließe einen Spieler warten,
  dass es zurückkommt; die zweite Zeile ist die wichtige („The battle continues - you now take its
  turns as well"). Danger-Akzent, als einzige Meldung des Spiels, die einen Fehler meldet statt
  eines Ereignisses. EIN Slot statt der Queue ihrer zwei Geschwister: ein Waaagh! kann wieder
  passieren, „die KI hat aufgehört" ist ein Ereignis, dessen Wiederholung dasselbe Ereignis ist.
  Sie führt `_front_notice()` direkt hinter dem Battle-End an — alles dahinter handelt von einem
  Spiel, dessen Vorzeichen sich gerade geändert haben.
- **Dass es „weitergeht", ist keine Annahme:** der „Next Phase"-Zweig ist nicht auf den Turn-Owner
  gegatet, der Mensch kann die Phasen der KI also selbst weiterschalten. Geprüft, bevor der Rest
  entworfen wurde — ohne das wäre „ohne KI weiter" ein eingefrorenes Spiel gewesen.

**Getestet:** neu `test_ai_offline.py` (**50/50**, sechs Abschnitte) plus `ab_ai_offline.py`
(**9 A/B-Sonden, alle beißend**). Die tragende Prüfung ist nicht „eine Ausnahme wurde gefangen",
sondern dass der Fang ENG ist: eine Sonde, die `except AIUnavailable` auf `except Exception`
verbreitert, muss rot werden — sonst wäre der bequeme falsche Fix nicht von dem richtigen zu
unterscheiden.
**Drei Befunde über den TEST**, alle von den Sonden: zwei ließen die Suite ABSTÜRZEN statt rot zu
werden (`AIUnavailable` aus dem Test heraus, `str.index()` auf einen fehlenden Namen) — **achte und
neunte Instanz** dieser Lehre —, und ein Verdrahtungs-Pin prüfte nur den TEILSTRING
`ai_offline_overlay.show(...)`, der ein `if False and ...` überlebt: er pinnt jetzt die ganze
Anweisung.

**Im ECHTEN Spiel belegt** (`verify_ai_offline.py`, `runpy` auf `selfplay.py`s echte Schleife):

| | gefixt | `--neutralize` (Vor-Fix) |
|---|---|---|
| Absturz aus `main()` | **nein** | `APIConnectionError` |
| offline gelatcht | True (`no connection to the API`) | False |
| Meldung erhoben | **1×** | 0× |
| Frames NACH dem Ausfall | **919** | 0 |

Die letzte Zeile ist die eigentliche Zusicherung: „stürzt nicht ab" und „spielt weiter" sind zwei
verschiedene Behauptungen, und nur die zweite war die Bitte.

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

## Die KI-Weiche: deterministisch fuer die KI, waehlbar fuer den Menschen

**Eine Regel BIETET IMMER AN; der Determinismus lebt auf der ANTWORTSEITE**
(User: "die KI soll das zwar deterministisch anwenden, aber die Funktion selbst soll nicht
deterministisch sein. wenn ein Mensch zb. necrons spielt, muss er die stratagems, Faehigkeiten und
Platzierung der Modelle manuell ganz normal steuern koennen. es muss also eine weiche geben").

Das Muster war in ~83 Modulen schon richtig — `game/mortal_wound_abilities.py:268-279` (Living
Lightning) und `game/technomancer.py:108-127` sind die Referenz: gemeinsame Kandidatenmenge,
`_pick()` als KI-Politik, volle Optionsliste plus „Decline" fuer alle anderen. **Ein mechanischer
Abgleich aller 88 Gates — Owner im Gate gegen den Empfaenger des `decision_manager.request()`, an
das es durchfaellt — ergibt 88 von 88 Treffern.** Die Arbeit bestand also darin, das Muster dort
einzuloesen, wo es fehlte, tot war oder vorgefiltert wurde.

**Warum `auto_players` ueberhaupt existiert, und warum es nie in die Regel gehoert:**
`ai/agent_driver.py:6660 _maybe_resolve_decision()` kann JEDEN offenen Prompt des eigenen Spielers
beantworten — aber ueber das LLM, also kostenpflichtig. `auto_players` ist ausschliesslich dazu da,
die KI **gratis und deterministisch** antworten zu lassen. Eine Regel, die selbst entscheidet, nimmt
dem Menschen die Wahl; eine Regel ohne `auto_players`-Zweig kostet die KI Geld. Beide Haelften
gehoeren zusammen.

**DIE TRENNLINIE, die den Konflikt mit Fehlerklasse 5 aufloest:**
- **Eignung / Inertheit** — die Regel erlaubt es nicht, oder die Option bewirkt NACHWEISLICH nichts
  → weiter fuer alle unterdrueckt.
- **Wuenschbarkeit** — lohnt sich der CP, der Token, das Risiko → **nur KI-Politik**, der Mensch
  wird trotzdem gefragt.

### Eine Definition statt fuenf Schreibweisen

`config.AI_PLAYERS` ist die eine Antwort auf „welche Seite beantwortet die Engine selbst".
`main()` bildet daraus EINMAL `ai_players`/`human_players` (aus `sorted(armies)`, also aus den
Spielern dieser Schlacht abgeleitet statt als zweites Literalpaar) und reicht sie weiter.

Vorher: **82 Literale `("Player 2",)` in `main.py`**, plus vier weitere Schreibweisen derselben
Tatsache — `scouts.human_players` (invers), `pregame.human_player` und `plagues.human_player`
(singular), `deployment_ai.resolve_scouts(ai_players=)` (ein Default, den niemand ueberschrieb) und
`agent_driver.take_one_action(player=)`.

- **EINGEFROREN per Konstruktion, und das ist der Grund, warum die Frage vor der Schlacht gestellt
  werden darf:** jedes der ~83 Module normalisiert in seinem eigenen `__init__`. Keine der
  `set(auto_players)`-Zeilen musste angefasst werden; die sieben `tuple(...)`-Module bleiben
  `tuple` (beide beantworten `in` identisch — sieben Dateien Risiko fuer null Verhalten).
- **SIEBEN Controller lasen `auto_players` und bekamen es nie** (`kauyon_*` x3, `montka_*` x3,
  `aac_autoreactive_camouflage`) → die KI waere dort in `_maybe_resolve_decision()` gelandet und
  haette pro Prompt gezahlt. Heute inert, weil kein Roster diese Detachments fieldet. Jetzt verdrahtet.
- **`resolve_scouts`' Default ist von `("Player 2",)` auf `()` gekippt**: ein Aufrufer, der es
  vergisst, loest jetzt NICHTS auf statt still die Scouts-Bewegung eines MENSCHEN zu nehmen.
- **`ai_players` leer ist erreichbar**, also kehren beide KI-Einstiege (`run_ai_action()`,
  `run_ai_pregame_action()`, EINE Aufrufstelle bei `main.py:5753-5755`) frueh zurueck — sonst
  `IndexError`, und schlimmer: der Agent handelte fuer einen Menschen und zahlte dafuer.
- **Ein Kommentar, der zur Luege geworden waere, ist mitkorrigiert** („Player 2 is this project's AI
  player throughout main.py").

### Was wirklich kaputt war

| # | Fundstelle | Defekt |
|---|---|---|
| A | `pestilent_fallout.py:79-81` | Das Gate war **toter Code** — beide Zweige byte-gleich — und der Controller hatte gar kein `decision_manager`. Ein Mensch bekam das Enfeeble-Ziel von `_best_damage_target` gewaehlt. Sein vier Zeilen frueher gebautes Geschwister `barrage_of_filth.py` hat den Prompt immer gehabt. |
| B | `word_of_the_phoenix.py` | Speicherte `auto_players` UND `decision_manager`, las keines. Lief aus `main.py:3721-3725` bedingungslos fuer den Command-Phasen-Spieler — **auch Spieler 1**. Der Docstring behauptete das Gate, das der Code nicht hatte. |
| C | `ard_as_nails.py:280`, `dlc_sickening_impact.py:135` | `is_worth_using()` lief **vor** dem Split: ein KI-Heuristik entschied, ob ein MENSCH das Stratagem ueberhaupt sieht. `dlc_undying_spite.py` machte es richtig und beschrieb 'Ard as Nails dabei falsch. |
| D | `reanimation_protocols.should_reroll()` | Der Necron-Warriors-Reroll wurde nur angeboten, wenn das KI-Urteil ohnehin ja sagte — bei gewuerfelter 2 oder 3 nie. Jetzt getrennt: `can_reroll()` ist die Regel (samt Inertheit), `should_reroll()` die KI-Politik. |
| E | `resurrection_orb.py:104` | Die KI rankte nach `recoverable_wounds`, der Mensch bekam `candidates[0]` (alphabetisch) als blosses Ja/Nein. Jetzt die volle Kandidatenliste, mit der Wundzahl im Label. |
| F | `bounty_hunters.py` | Waehlte das Beuteziel auch fuer die Farstalker des MENSCHEN, per `target_pick=_best_damage_target` — und hatte weder `decision_manager` noch `auto_players`. |
| G | acht Module | **Jede** Modell-Rueckkehr platzierte engine-gewaehlt — siehe den eigenen Abschnitt unten. |

**Zwei Befunde, die KEINE Aenderung brauchten und deshalb aufgeschrieben statt „behoben" sind:**
`curse_of_the_walking_pox` druckt zwar „you can return", aber beide Haelften sind inert (ein
zurueckkehrendes Modell kommt gratis mit vollen Wunden, und POXWALKERS ist eine Ein-Zeilen-
Datenblatt, also sind alle Kandidaten identisch); und `raid_and_run` / `spiritseer.TearsOfIsha`
haben zwar tote Gates, sind aber fuer BEIDE Seiten unerreichbar (`start_move()` / `resolve()` ohne
Aufrufer) — ein Menschprompt hinter einem toten Pfad waere spekulativ. Der Quell-Waechter
**verifiziert die Unerreichbarkeit**, die Ausnahme laeuft also von selbst ab, sobald jemand sie
verdrahtet.

### Die Platzierung zurueckkehrender Modelle (game/return_placement.py)

Regel 01.02.03: ein zurueckgestelltes Modell wird AUFGESTELLT, und Aufstellen ist Sache des
Spielers. Acht Faehigkeiten holen Modelle zurueck und **alle acht waehlten den Platz selbst, fuer
beide Seiten**. Der Platz war nie illegal — `formation_layout.returning_positions()` setzt in
Kohaerenz per Konstruktion — er war nur nie jemandes Wahl.

- **`SetupController` lernt eine TEILMENGE** (`start_setup(..., models=, positions=, mark_set_up=)`,
  alle drei mit dem heutigen Default). `placing_models` ist die EINE Antwort darauf, welche Modelle
  diese Platzierung bewegt, gelesen von neun Stellen (Stapel-Schleife, beide Drags, Line-Drag,
  `is_placeable()`, die Ueberlappungs-Ausnahme, `cancel_setup()`). **Fuer jeden bestehenden Aufrufer
  per Konstruktion inert** — die volle Regression ist ohne eine einzige Aenderung gruen.
- **Es reitet auf `PLACING` statt einen zweiten Pending-Zustand zu bauen**, und das ist der Kern:
  was `main()` blockiert, MUSS anklickbar UND gezeichnet sein, sonst ist es ein harter Deadlock
  (Fehlerklasse 25). `PLACING` wird bereits blockiert, geroutet, gemalt und hat Confirm/Cancel.
- **DREI Fallen, alle vom Design-Durchlauf gefunden und einzeln gepinnt:**
  - **`mark_set_up=False`** — `confirm_setup()` setzt sonst `set_up_this_turn`, was 18.02 als „darf
    nicht einsteigen" liest. Eine Einheit, die zwei Krieger reanimiert hat, wurde NICHT aufgestellt.
    Faellt erst eine Phase spaeter auf.
  - **Die Ueberlappungs-Ausnahme gehoert der PLATZIERUNG, nicht der Einheit.** Bei einer Teilmenge
    stehen die Ueberlebenden still und muessen gemieden werden — sonst laesst der Drag zu, was
    `confirm_setup()`s squad-weites `check_model_overlap()` am Ende ablehnt. Fehlerklasse 8, die
    schon einmal eine ganze Einheit gekostet hat.
  - **`allow_engaged=True` plus der Validator der Faehigkeit**: 01.02.03 erlaubt engaged, wenn die
    Einheit ohnehin gebunden ist, und der Validator erzwingt genau das pro Position.
- **VIER der acht sind verdrahtet** (Reanimation Protocols, Grot Orderly, Unquenchable Resolve,
  Curse of the Walking Pox); die anderen vier stehen mit ihrem Grund im Test, damit die fuenfte eine
  sichtbare Einzeiler-Aenderung ist.
- **Aber eine FAEHIGKEIT zu verdrahten ist nicht dasselbe wie ihren TRICHTER zu verdrahten** (User:
  "Einheiten wurde automatisch platziert bei protocol of the undying legion, obwohl ich necrons
  spiele. da scheint sich noch eine automatismus zu verstecken, der nur bei KI greifen soll").
  Fehlerklasse 9 in Reinform — der Trichter ist nicht immer der, der so aussieht.
  - **`reanimation_protocols.reanimate()` hat DREI Aufrufer, nicht einen.** Der Controller der
    Armeeregel bekam seinen Placer; **Protocol of the Undying Legions und der Resurrection Orb
    rufen dieselbe Funktion direkt** und bekamen keinen — also setzte die Engine die Modelle des
    MENSCHEN weiter selbst. `reanimate(placer=None)` faellt per Default auf den alten Pfad zurueck,
    ein vergessener Aufrufer ist also still und sieht von innen richtig aus.
  - **Reproduziert vor jeder Aenderung**, beide Tueren, beide Seiten: der Mensch bekommt seine
    Modelle zurueck und `setup.state` bleibt `idle` — identisch zur KI. Danach `placing` fuer den
    Menschen, `idle` fuer die KI.
  - **Der Waechter ist eine MENGENDIFFERENZ an der QUELLE** (`test_return_placement.py`
    Abschnitt 7): jeder `reanimate()`-Aufruf ausserhalb seines eigenen Moduls muss `placer=`
    mitgeben, und `main.py` muss dem zugehoerigen Controller einen geben. Ein Verhaltenstest kann
    die VIERTE Tuer nicht sehen, weil es sie noch nicht gibt.
  - **Und der Waechter musste den AUFRUFAUSDRUCK pruefen, nicht einen Teilstring** — die eigene
    A/B-Sonde hat das gefunden (Fehlerklasse 24): `"placer=return_placement_controller," in
    MAIN_SRC` ist schon wahr, weil Curse of the Walking Pox es ebenfalls uebergibt, also blieb die
    Zeile gruen, waehrend Undying Legions unverdrahtet war. Jetzt per AST, und in BEIDEN Formen,
    die die Konstruktionsreihenfolge erzwingt (Konstruktor-kwarg fuer den nach dem Placer gebauten
    Controller, Attributzuweisung fuer den davor gebauten — Fehlerklasse 23).
- **Eine RÜCKKEHR-Platzierung trägt jetzt auch 09.02s KOHÄRENZ — im Overlay UND im Drag** (User:
  "immer wenn man Einheiten platzieren muss, zb durch Reanimation, muss man in coherency
  platzieren. dementsprechend muss auch das overlay sein. im Moment geht das über die ganze map?").
  - **Gemessen vor der Änderung, map2:** das Overlay malte **85.9 % des Bretts grün, legal waren
    2.0 %** — **42× zu viel Boden**, und die Ablehnung kam erst beim Confirm. Eine gewöhnliche
    Aufstellung sieht genauso aus (86.8 % gegen 2.6 %).
  - **`position_valid()`s Docstring nannte den Grund und war für diesen Fall falsch:** Kohärenz
    "depends on the whole squad's final positions together, not a single point" — wahr, solange
    jedes Modell der Einheit noch in der Luft ist. Eine RÜCKKEHR ist genau der Fall, in dem das
    nicht gilt: die Überlebenden stehen still und SIND der Anker, also hat "würde dieses Modell die
    Einheit in einem Stück lassen" eine exakte Antwort pro Position.
  - **NUR Teilmengen-Platzierungen** (User-Entscheidung): die gewöhnliche Aufstellung bleibt, wie
    sie ist — dort gibt es keinen Anker —, und die Aufstellungs-KI ist per Konstruktion unberührt,
    weil sie `position_valid()` direkt liest und nie durch `placement_validator()` geht.
  - **Overlay UND Klemmung, nicht nur die Anzeige** (User-Entscheidung): die vier Konsumenten von
    `placement_validator()` sind Overlay, `clamp_drag`, `apply_group_drag` und `pack_positions` —
    also bleibt die dokumentierte Zusicherung "was grün ist, ist da, wo das Modell stehenbleiben
    darf" erhalten, statt an genau dieser Stelle zu brechen. **Gemessen:** ein Zug quer über das
    Brett klemmt jetzt an die Kohärenzgrenze zurück, statt dort zu landen, wo der Confirm ablehnt.
  - **`squad.coherency_probe(models, moving)` beantwortet ZUSAMMENHANG, nicht "hat einen Nachbarn
    in 2\"".** Der schwächere Test ist genau der Fehler, für den `check_coherency()` einst
    umgeschrieben wurde (zwei gegenseitig kohärente Cluster erfüllen ihn, während die Einheit in
    zwei Teile zerfallen ist). Die Sonde berechnet EINMAL die Komponenten der übrigen Modelle und
    fragt je Punkt nur, ob er ALLE berührt — O(Komponenten) statt Graph-Neubau, weil das Overlay
    Tausende Punkte fragt und der Drag bisektiert.
  - **Der gecachte Overlay-Layer musste mitziehen:** die Maske wird bewusst einmal pro Platzierung
    gebaut, und `placement_generation` reichte, solange die legale Fläche eine Tatsache über das
    BRETT war. Der Kohärenzring stammt aus den NACHBARN, und die bewegen sich beim Platzieren.
    `SetupController.overlay_cache_key(token)` ist die eine Antwort darauf — beim Controller, nicht
    im Zeichencode: "wovon hängt die legale Fläche ab" ist eine Tatsache über die Regel. Sie lässt
    das gezeichnete Modell bewusst AUS (sonst würde die Maske bei jeder Mausbewegung neu gebaut)
    und nimmt seine Identität mit auf (sonst teilten sich zwei gleich große Modelle eine Maske, die
    nur für eines stimmt).
  - **Getestet:** `test_return_placement.py` 89 → **111/111** (Abschnitt 9: die GRENZE wird
    gelaufen statt gepinnt — das Modell wandert nach außen, bis der Validator ablehnt, und dieser
    Punkt wird gegen die Regel-Sonde geprüft; der Brücken-Fall zwischen zwei Clustern; die
    unveränderte volle Aufstellung; der Cache-Schlüssel in beide Richtungen).
    `ab_return_placement.py` 13 → **18 Sonden, alle beißend**.
  - **Zwei eigene Testfehler, beide von den Sonden gefunden:** der erste Grenzfall-Punkt war
    konstruiert und scheiterte an ÜBERLAPPUNG statt an Kohärenz (jetzt wird die Grenze abgelaufen,
    was die anderen Terme aus der Antwort hält); und zwei Sonden ließen die Suite ABSTÜRZEN statt
    rot zu werden (Indizieren in `placing_models`, das in der Vor-Fix-Welt leer ist, und `*None`
    aus dem abgebrochenen Lauf) — **zwölfte und dreizehnte Instanz** derselben Lehre.
  - **Im ECHTEN Spiel belegt:** `verify_return_placement.py` misst jetzt zusätzlich die gemalte
    Fläche durch DASSELBE Prädikat, das `main()` dem Renderer reicht — **1.7 % des Bretts** statt
    der 85.9 % davor, bei unveränderten "1 von 5 Modellen platziert / 0 für die KI geöffnet /
    0 bewegte Überlebende".
  - **Und das Overlay zeichnet seither BASISRÄNDER statt Mittelpunkte** (User: "momentan ist die
    Grenze des overlays so dass der Base Mittelpunkt bis zur Grenze gehen kann. intuitiver wäre
    aber der Baserand ... bei Baserand muss jedes Modell unabhängig von der Basegröße den selben
    Abstand einhalten"). Derselbe Handel wie bei den Engagement-Ringen, und aus demselben Grund
    richtig — nur ist hier zusätzlich ein echter Fehler mitgefallen.
    - **Die alte Begründung war eine Tatsache über die REGEL, keine über die Zeichnung.** Jede
      Prüfung dieser Engine misst Kante zu Kante (`edge_distance` = Mittelpunkte minus beide
      Radien), die Regel behandelt also alle Basisgrößen gleich. Die legale MITTELPUNKT-Fläche ist
      dagegen pro Basisgröße eine andere Kurve, das Overlay kann nur EINE zeigen, und `main.py`
      wählte das größte Modell mit der Begründung, dessen Fläche sei "eine Teilmenge jeder
      anderen".
    - **Die Kohärenz hat diese Begründung gebrochen, und das ist gemessen:** sie WÄCHST mit dem
      Radius (`Mittelpunkte ≤ 2" + r_a + r_b`), während Gelände und Brettkante mit ihm schrumpfen.
      An Necron Warriors + Overlord: **8.6 sq.in nur fürs große Modell legal, 9.3 sq.in nur fürs
      kleine** — es gab also gar keine sichere Einzelmaske mehr.
    - **`SetupController.base_edge_zones()` liefert ZWEI Zonen, weil ein Vorzeichen dreht:**
      `keep_out` (Brettkante, Dense-Gelände, fremde Modelle, plus was die Regel ergänzt — hier darf
      KEIN Teil einer Base hin) und `band` (09.02s Kohärenz — dieses Band MUSS die Base erreichen).
      Beide für eine PUNKTFÖRMIGE Base ausgewertet, und genau das macht sie basisgrößenunabhängig.
    - **Beide Lesarten sind die Regel selbst, keine Näherung**: `position_valid()` prüft die
      Scheibe des Modells gegen die Geometrie, also ist "die ganze Base ist aus dem Roten heraus"
      dieselbe Aussage; und `edge_distance <= 2"` heißt, die Base überlappt die um 2" gewachsenen
      Nachbarn, also ist "die Base berührt das Grüne" ebenfalls wörtlich die Regel. Die KLEMMUNG
      bleibt deshalb unverändert bei `placement_validator()` — Bild und Spiel können nicht driften.
    - **Der Punkt-Radius wird geholt, indem der Radius des Tokens für die Dauer JEDES Aufrufs auf 0
      gesetzt wird** (`try/finally`). Damit werden dieselben Prädikate gefragt statt einer zweiten
      Kopie der Regeln, und die IDENTITÄT des Modells bleibt erhalten — ein Stellvertreter-Objekt
      würde sie verlieren, und `position_valid()` nimmt ein Modell per Identität von der
      Kollision mit sich selbst aus.
    - **`max(overlay_models, key=radius_in)` ist ersatzlos entfallen.** Die Keep-out-Linie ist für
      die ganze Einheit dieselbe; nur das Band hängt noch am gezogenen Modell (weil "die anderen"
      je Modell eine andere Menge sind) und bekommt deshalb seinen eigenen Cache-Schlüssel.
    - **Getestet:** `test_return_placement.py` 111 → **132/132** (Abschnitt 10), `ab_return_placement.py`
      18 → **24 Sonden, alle beißend**. **Vier Befunde über den TEST**, alle von den Sonden: der
      Basisgrößen-Vergleich benutzte ein FREMDES Modell (was die Nachbarmenge ändert und damit aus
      einem anderen Grund abweicht — jetzt dasselbe Modell mit getauschtem Radius); er prüfte nur
      zwei 30" auseinanderliegende Punkte, die jede Radius-Abhängigkeit überleben (jetzt zusätzlich
      ein Punkt DIREKT an der Bandkante); der Renderer-Pin prüfte einen STRING, den ein `if False:`
      davor überlebt (jetzt die Erreichbarkeit); und die Radius-Prüfung stand VOR dem ersten Aufruf,
      während der Radius nur währenddessen null ist. Dazu **vierzehnte und fünfzehnte Instanz** der
      "eine Sonde muss rot machen, nicht abstürzen"-Lehre.
    - **Im ECHTEN Spiel belegt** (`verify_return_placement.py`): die Keep-out-Linie ist für eine
      1.26"- und eine 4.2"-Base **an 2745 von 2745 Punkten identisch, 0 Unterschiede**, das Band
      wird gezeichnet, und der Radius des Modells überlebt die Abfrage.
- **Und das BRETT sagt jetzt, WELCHE Modelle gerade zurueckgekommen sind** (User: "Widerbeleben -
  ich kann nicht erkennen, welche einheiten gerade zurueckgekommen sind, um sie zu verschieben.
  bitte hervorheben").
  - **Die Luecke war strukturell, nicht eine fehlende Farbe.** Eine Rueckkehr setzt ein, zwei
    Modelle in eine Einheit, die SCHON STEHT — und die einzige Markierung war
    `draw_placement_identity()`s Umriss um die GANZE Einheit, der fuer die zwanzig Ueberlebenden
    genauso zutrifft wie fuer die zwei neuen Basen. Nichts sagte, welche zwei gerade erschienen sind.
  - **`Renderer.draw_returning_models(surface, board, models)` nimmt eine MODELL-Liste**, keine
    Einheit — genau das ist der Punkt. Dieselbe Form wie `draw_damage_choice_highlight()` eine
    Methode darueber, aus demselben Grund. `draw_placement_identity(..., placing_models=)` ist die
    einzige Naht: eine echte Teilmenge bekommt die Ringe, `None` oder die ganze Einheit zeichnet
    exakt das alte Bild (was jede gewoehnliche Aufstellung will).
  - **WEISS und ein DOPPELring.** Weiss, weil jede andere Brettmarkierung bereits einen Farbton
    besitzt (Cyan Auswahl, Gelb Schadenswahl, Orange Schussziel, Rot Kohaerenz/Feind, Gruen eigene
    Armee, Violett Zuteilung) — ein sechster Farbton waere eine weitere Vokabel, Weiss gehoert
    keinem und liest auf jedem Biom-Boden. Der zweite Ring, weil ein einzelner sich vom
    Auswahl-Umriss nur in der FARBE unterscheidet, und das hier in einem gepackten Blob auf einen
    Blick zu finden sein muss — was die ganze Meldung war.
  - **Die Namensplakette zaehlt sie** ("... - place 2 returning models") und haengt ueber den
    ZURUECKKEHRENDEN Modellen statt ueber der Einheit: die sind es, die gezogen werden muessen, und
    die Ueberlebenden koennen irgendwo stehen. Das linke Panel sagte "Returning Models" schon
    laenger — jetzt hat diese Ueberschrift auch auf dem Brett eine Antwort.
  - **Getestet:** `test_return_placement.py` 132 → **140/140** (Abschnitt 11, auf PIXELN: jedes
    zurueckkehrende Modell hat seinen Ring, KEIN Ueberlebender hat einen, die Ringe sind wirklich
    zwei, und eine gewoehnliche Aufstellung zeichnet gar keine — ohne die letzte Gegenprobe
    bestuende der Abschnitt auch, wenn alles geringt wuerde). Der Test stellt die zwei Modelle
    dafuer FREI: `tk.line_up()` packt Basen 1.4" auseinander, enger als die Ringe breit sind, ein
    Ring liesse sich sonst keinem Modell zuordnen. `test_unit_selection.py`s Quell-Pin auf den
    `draw_placement_identity`-Aufruf ist zu Recht rot geworden und prueft jetzt den
    AUFRUFAUSDRUCK per AST statt einer Zeile Formatierung.
  - **Im ECHTEN Spiel belegt** (`verify_return_placement.py`, dritte Haelfte derselben Sonde):
    `models ringed as RETURNING: 1 of 5 in the unit` ueber 2964 Identity-Zeichnungen;
    `--neutralize` meldet `None of 5` und die Zeile "the board never said which models came back".
    **Die Sonde brauchte dafuer mehr Frames** — ihr altes 1200er-Budget erreicht die erste
    Command-Phase des Menschen gar nicht und meldete 0 Aktivierungen, was wie ein Fehler des
    Gemessenen aussieht statt wie ein zu kurzer Lauf; Default jetzt 3000.
- **Die KI ist unveraendert, und das ist gepinnt**: fuer einen Owner in `auto_players` landen die
  Modelle auf exakt den Punkten, die die Faehigkeit ohnehin berechnet hat, im selben Frame, ohne
  dass etwas geoeffnet wird.

### Getestet

- Neu `test_ai_mode.py` (**29/29**) + `ab_ai_mode.py` (**8 Sonden, alle beissend**),
  `test_deterministic_gates.py` (**38/38**) + `ab_deterministic_gates.py` (**8 Sonden**),
  `test_return_placement.py` (**132/132**) + `ab_return_placement.py` (**24 Sonden, alle
  beissend**; die zwei zusaetzlichen Tueren in `reanimate()` je 5, die Koherenz-Haelfte 4, die
  Basisrand-Darstellung 6).
- **Quell-Waechter gegen die KLASSE** in `test_ai_mode.py`: jedes Modul, das `auto_players` nimmt,
  muss es LESEN (oder an eine Basis weiterreichen — ohne diese Klausel meldet der Waechter die vier
  `CommandPhaseMark`-Unterklassen falsch mit, und ein Waechter mit Fehlalarmen wird geloescht); und
  jeder Controller, den `main.py` baut, muss es am AUFRUFAUSDRUCK bekommen, nicht bloss dem Namen
  nach (Fehlerklasse 24).
- **Im ECHTEN Spiel belegt**, mit Necrons auf BEIDEN Seiten:
  `verify_ai_players_wiring.py` (**83 von 83** Controllern gefuettert, EIN Wert),
  `verify_human_choice_paths.py` (**0** Prompts an die KI, **0** LLM-Fallbacks) und
  `verify_return_placement.py` (der Mensch platziert **1 von 5** Modellen, die Ueberlebenden bewegen
  sich **nicht**, fuer die KI wird **nichts** geoeffnet); dazu
  `verify_undying_legions_placement.py` fuer die zwei ANDEREN Tueren in `reanimate()`, das die LIVE
  von `main()` gebauten Controller aus dessen eigenem Frame nimmt und meldet
  `placement opened for the human: True (placing 1 of 5)` gegen `--neutralize`s `False (0 of 5)` —
  der gemeldete Fehler woertlich. Alle vier **STAGEN die Tatsache selbst** —
  ein MockAgent-Lauf erreicht keine Reanimation, weil nichts stirbt, und ein passiver Zaehler haette
  0 gemeldet und wie ein Bestehen ausgesehen.
- Volle Regression **176 Suiten, ~15366 Pruefungen, 175 gruen / 0 rot / 1 bekannt**, alle Smokes.
- **Eigene Fehler, alle vom Werkzeug gefangen und hier notiert, weil sie sich wiederholen werden:**
  `verify_ai_players_wiring.py` fand sofort einen `TypeError` in `main.py`s `take_one_action`-Aufruf
  (ich hatte die 13 positionellen Argumente auf Keywords umgeschrieben und `memory` als `ai_memory`
  benannt) — **von 15 000 gruenen Pruefungen nicht gesehen, weil keine Suite `main()` faehrt**;
  seither steht dort wieder die positionelle Kette mit nur `player=` angehaengt. Eine Regex ueber
  einen Konstruktoraufruf hat den ARGUMENTBLOCK EINES ANDEREN Controllers verschluckt. Und die
  vierstufige Panel-Kette (`draw` → `_draw_dispatch` → `_draw_pregame_ui` →
  `_draw_pregame_deploying` → `_draw_setup_ui`) war nach dem ersten Anlauf halb verdrahtet — genau
  die Narbe, die `action_panel.py` traegt; ein AST-Sweep „welcher Name wird benutzt, ohne Parameter
  zu sein" hat beide Male die Stelle genannt.

### EIN Schalter: KI-Modus IST Auto-Play (game/ai_mode.py, 2026-09-04)

**Gemeldet nach einer Partie:** *"Protokoll of undying legions wurde wieder automatisch ausgeführt,
obwohl KI Modus aus war"* — und auf die Rückfrage, ob Auto-Play und die Fähigkeits-Gates zwei
verschiedene Dinge seien: *"das ist für mich das gleiche. KI - Modus ist autoplay, erkennbar am
roten punkt. das steuert auch, ob die ki pfade für fähigkeiten und stratagems aktiviert sind.
verstehe nicht warum man das trennen sollte."*

- **Die KI handelte über ZWEI Kanäle, und nur einer hörte auf den Punkt:** `take_one_action()` pro
  Frame (von Auto-Play gegated) und die ~83 `auto_players`-Gates in den Fähigkeits- und
  Stratagem-Controllern (von gar nichts gegated). **Im Log des Users belegt**
  (`game_20260904_174253.log`): `auto-play OFF` in Zeile 17, danach hat der Mensch alle acht
  Player-2-Einheiten von Hand aufgestellt (Kanal eins stand also wirklich), und in Zeile 175 gab
  Kanal zwei trotzdem 1 CP aus.
- **`game/ai_mode.py` ist die Fusion, und der Trick ist die Trennung von WER und OB.**
  `config.AI_PLAYERS` sagt weiter, welche Seite der KI gehört; das Modul sagt, ob diese Seite
  gerade überhaupt von der Engine gespielt wird. **Eingefrorene MITGLIEDER, lebende
  MITGLIEDSCHAFT:** `players()` gibt eine Sicht zurück, deren `__contains__` den Modus mitfragt —
  damit erreicht ein Schalter ~83 Gates, die EINMAL beim Schlachtbau entstehen und nie wieder.
  **Keine der ~90 Lesestellen musste angefasst werden** (alle fragen `x in self.auto_players`),
  nur die 80 Schreibstellen (`set(auto_players)` → `ai_mode.players(auto_players)`).
- **`ai_players` in `main()` IST diese Sicht**, und das gatet den zweiten Kanal gratis mit: beide
  KI-Einstiege beginnen ohnehin mit `if not ai_players: return`, und die Sicht liest sich bei
  ausgeschaltetem Modus als leer — also stehen Frame-Tick UND die Einzelschritt-Taste „A" still,
  ohne dass eine von beiden vom Modus wissen muss. `human_players` ist die lebende KOMPLEMENTÄR-
  Sicht (`ai_mode.humans()`).
- **DEFAULT AN, SCHLACHTSTART AUS** — kein Widerspruch, sondern dieselbe Trennung: ohne laufende UI
  sagen die eingefrorenen Mitglieder alles (~18 Suiten reichen `auto_players=(AI,)` und erwarten
  genau das), und `main()` setzt den Modus dort explizit, wo vorher `ai_auto_play = False` stand.
  Ein Spiel startet also wie immer mit stiller KI, und die zehn Harnesses (alle schicken Shift+A)
  sind unberührt.
- **Der rote Punkt ist ein TOGGLE geworden** (User: "außerdem wäre ein toggle in der oberfläche gut
  für den KI Modus. vielleicht dort, wo jetzt der rote punkt ist"), gezeichnet in BEIDEN Zuständen,
  unter dem MENU-Knopf in der Brett-Ecke. Ein Punkt, den es nur im EIN-Zustand gab, war das
  eigentliche Problem: es gab nichts anzuklicken, um den Modus wieder einzuschalten, und nichts auf
  dem Schirm sagte, dass es ihn gibt. `button_style.draw_toggle()`, also dieselbe Bildsprache wie
  die Schalter im linken Panel samt ihrer drei redundanten Zustands-Signale (Knopfseite, Track-,
  Rahmenfarbe). Der Klick-Zweig steht VOR der ~48-Zweige-Kette (Fehlerklasse 15) und verbraucht den
  Klick, sonst schwenkte er zusätzlich die Kamera.
- **Der Log nennt den Schalter jetzt beim Namen** (`Player 2: AI mode ON (Shift+A).` /
  `(AI toggle)`) — genau die Zeile, die den gemeldeten Fehler überhaupt lesbar gemacht hat.
- **Getestet:** `test_ai_mode.py` 29 → **61/61** (Abschnitte 8-10: die lebende Sicht, der gemeldete
  Fall end-to-end durch den ECHTEN `UndyingLegionsController` mit echtem CP-Konto, eine
  MENGENDIFFERENZ an der Quelle — kein Gate darf eine eingefrorene Kopie halten, und jedes muss
  `ai_mode` wirklich importieren —, und `main()`s Verdrahtung); `test_ai_busy_badge.py` 62 →
  **63/63** (Abschnitt 6 misst den Schalter jetzt in BEIDEN Zuständen, inklusive der
  Graustufen-Probe); `test_game_menu.py` **139/139** nachgezogen.
  Neu **`ab_ai_mode_switch.py`: 8 A/B-Sonden an der QUELLE, alle beißend.**
- **Im ECHTEN Spiel belegt** (`verify_ai_mode_switch.py`, `runpy` auf `selfplay.py`s echte
  `main()`-Schleife): der Schalter wird bei `Rect(700, 50, 92, 26)` gezeichnet, ein Klick auf genau
  diese Koordinaten kippt den Modus `True -> False`, und der LIVE von `main()` gebaute Controller
  antwortet für **`2 Canoptek Wraiths 1`** — die Einheit aus dem Bericht — mit `mode ON: cp 5->4,
  kein Prompt` gegen `mode OFF: prompt, cp 5->5`. **`--neutralize` reproduziert den Bericht
  wörtlich:** `mode OFF: cp 5->4`, ohne Prompt.
- **Zwei eigene Sondenfehler, beide Fehlerklasse 24:** eine Sonde schrieb
  `ai_toggle_rect = ai_mode.enabled() and draw_ai_mode_toggle(` und die Suite blieb grün (der Pin
  fragte nur, ob ein `elif` fehlt — jetzt muss die Zuweisung ein NACKTER Aufruf sein), und eine
  zweite machte den Klick-Zweig mit `and False` tot statt ihn zu löschen, was die ehrliche
  Vor-Fix-Welt gewesen wäre.

### Und zwei Folgeberichte aus derselben Partie

**Beides Folgen desselben Satzes „KI-Modus aus muss ein echter Modus sein" — der erste ist aber
ein EIGENER Bug, der auch mit eingeschalteter KI zugeschlagen hätte.**

- **Rapid Ingress: gekauft, aber nichts platzierbar** (User: *"Ich habe im letzten spiel als player
  2 rapid ingress für den shard of the voiddragen verwendet, konnte aber danach keine einheit
  platzieren"*). `main()`s Frame-Poll verwarf eine getragene Reserve-Karte, sobald die Phase nicht
  Bewegung ist — und **15.07s Fenster ist per Definition nicht in der Bewegungsphase**: es geht auf,
  während die gegnerische Bewegungsphase ENDET, also nach `advance_phase()`, wenn die Uhr schon
  Schießen sagt. Karte aufnehmen, nächster Frame, Karte weg. Im Log: Fenster in Zeile 259, eine
  Zeile nach „Shooting phase begins", ungenutzt geschlossen in Zeile 313.
  **Nichts mit dem KI-Modus zu tun** — die KI erreicht ihre Reserven über `ai/deployment_ai.py` und
  nie über diesen Pick, weshalb nur ein Mensch darauf treffen konnte. Die Ausnahme gilt GENAU der
  einen Einheit, für die ein Fenster offen ist, damit der Wächter weiter tut, wofür er da ist
  (keine fremde Reserve-Einheit auf dem Rücken eines fremden Stratagems außer der Reihe hereinholen).
- **Ohne KI-Modus ging es vor der Aufstellung nicht weiter** (User: *"es gibt keinen knopf mit dem
  man den roll für attacker/defender auslösen könnte"*). Der Roll-off war nie das Problem — er
  beginnt von selbst, sobald BEIDE Spieler ihre Formations erklärt haben. Was nicht passieren
  konnte, war Player 2s Erklärung: `PregameController` wurde mit dem Default `human_player =
  "Player 1"` gebaut (`main()` hat nie einen übergeben), und das Panel bot genau dessen Einheiten
  an. Also stand dort „Waiting for your opponent..." — für einen Gegner, der bei ausgeschalteter KI
  die Person an der Maus ist.
  **`human_player` (singular) → `human_players` (Menge)**, an allen fünf Stellen: der
  Formations-Start, der Deploy-Roll-off, `_begin_battle()`, `game/plagues.py` und das Panel, das
  jetzt JEDEN menschlichen Owner nacheinander durchgeht und ihn benennt, sobald mehr als einer
  dran ist. `main()` reicht dieselbe lebende Sicht durch, die auch die Regel-Gates bekommen. Das
  war der als offen geführte „zweite Teil" der KI-Weichen-Arbeit.
  **`PregameController.human_player` bleibt als weiterleitende Property** (erster menschlicher
  Owner) — acht Harnesses treiben die Aufstellung darüber, und bei eingeschaltetem Modus antwortet
  sie exakt wie vorher.
- **Getestet:** `test_pregame.py` 125 → **138/138** (neuer Abschnitt „Hotseat", der die gemeldete
  Sackgasse als Vor-Fix-Welt festhält: mit EINEM Menschen zeigt das echte Panel **keinen einzigen
  Knopf**, und der Roll-off beginnt nie); `test_line_drag.py` 146 → **150/150** (Quell-Pins auf die
  Ausnahme, samt der Gegenprobe, dass sie NICHT auf „irgendein Fenster ist offen" verallgemeinert).
  Beide sind in `ab_ai_mode_switch.py` mit je einer beißenden Sonde belegt.

### Bewusst offen

- **Der SCHALTER steht (siehe oben), die FRAGE zu Schlachtbeginn nicht.** `config.AI_MODE_SELECT`
  liegt weiter bereit und hat weiter keinen Leser: der Modus wird heute im Spiel umgelegt (Toggle
  in der Brett-Ecke oder Shift+A), nicht vor der Schlacht erfragt (User: „Frage am Anfang der
  Schlacht durch ein promt, ob der ki Modus an oder aus sein soll"). Sie
  gehoert nach `main.py`s `run()` — zwischen Game-Menue und `main()` —, weil alle zehn Harnesses
  `main.main()` DIREKT rufen: dort kostet ein Screen **null** Opt-outs, in `main()` zehn plus einen
  Waechter. Mit „KI aus" muessen zusaetzlich `pregame.human_player` (singular) zu einer MENGE werden
  und die beiden KI-Treiber gegated bleiben.
- Die vier uebrigen Rueckkehr-Faehigkeiten (siehe oben), und `reanimate()`s zwei restliche
  Unterentscheidungen (welches Modell geheilt wird, welches zurueckkommt) — beide heute noch
  deterministisch fuer alle. Vor dem Bau ist die PROMPTZAHL zu messen: Reanimation feuert fuer jede
  Einheit jede Command-Phase, und ein Prompt pro Wunde koennte schlimmer sein als das, was er behebt
  (`measure_stim_injectors_prompts.py` ist die Vorlage).
- `raid_and_run`, `plasmacyte`, `dlc_signal_pox` sind fuer BEIDE Seiten unverdrahtet — eine andere
  Fehlerklasse als die gemeldete, hier benannt statt nebenbei gebaut. **CLAUDE.md fuehrte Plasmacyte
  faelschlich als fertigen KI-Pfad**; diese Zeile ist unten korrigiert.

## Elf Meldungen aus drei Partien (2026-09-06)

Jede ist auf eine Ursache an der QUELLE zurückgeführt und, wo möglich, am Log belegt. Sie
fallen in fünf Gruppen, und zwei davon sind bekannte Fehlerklassen dieses Repos. Beim
Nachverfolgen kam ein Fund dazu, der nicht gemeldet war und schwerer wiegt als die meisten
gemeldeten (die doppelt zugewiesene `on_unit_finished_fighting`), und WÄHREND der Arbeit eine
zwölfte Meldung, die den ersten Hazardous-Fix als zu klein entlarvte (siehe dort).

**Die Überschrift bleibt "Elf", obwohl es zwölf sind** — sie wird aus dem Datacard-Abschnitt
heraus per Namen referenziert, und ein Querverweis ist mehr wert als eine korrekte Zahl in
einer Überschrift.

### `turn_owner` nach `advance_phase()` — eine Naht, vier Stratagems

`main.py:3187` ruft `turn_tracker.advance_phase()`; Fight ist die LETZTE Phase, also flippt
`turn_owner` dort auf den nächsten Spieler und `phase` auf Command. Der
End-of-Fight-Phase-Block darunter las danach `turn_tracker.turn_owner` — **vier
Aufrufstellen, alle mit dem falschen Spieler**, während `mover_before` ungenutzt zwei Zeilen
darüber lag (`resurrection_orb` benutzte es bereits korrekt). Die Kommentare behaupteten, die
vier lägen auf VERSCHIEDENEN Seiten, und reichten alle denselben Ausdruck — der Beleg, dass
der Block geschrieben wurde, als `turn_owner` noch nicht geflippt hatte.

**Wall of Mirrors (gemeldet) war davon zweimal betroffen**: der falsche Spieler wurde gefragt
(und weil die Uhr schon weiter war, sah es aus wie "am Anfang der Gegner Runde"), UND
`can_use()`s `phase != PHASE_FIGHT` konnte per Konstruktion nie halten, weil der Mensch Frames
später antwortet — also gab `use()` immer False: kein CP, kein Rückzug, keine Logzeile
("funktioniert auch nicht"). Kollateral in derselben Naht: Cost of Victory (bot gar nichts
an), Webway Tunnel, Elemental Ensnarement.

- **`game/phase_window.py` (30. Extraktion)**: ein Angebot an einer Phasengrenze wird Frames
  SPÄTER beantwortet, ein Live-Phasentest ist dafür strukturell falsch. Das Fenster ist eine
  Tatsache, die der Controller besitzt — geöffnet vom eigenen Angebot, geschlossen im
  Per-Phasen-Reset von `main.py`, der VOR den Angeboten derselben Grenze läuft. Form der
  zwölf `_offered_this_phase`-Memos um `game/fail_safe_detonator.py`.
- **Quell-Wächter** (`test_event_chain_wiring.py` Abschnitt 8): keine Aufrufstelle unterhalb
  von `advance_phase()` darf `turn_tracker.turn_owner` als Spielerargument reichen. Ein
  fünfter Reaktor kann nicht ungeprüft dazukommen.
- **Im ECHTEN Spiel belegt** (`verify_wall_of_mirrors.py`, live aus `main()`s Frame):
  `asked=Player 1, in_strategic_reserves=True` gegen `--neutralize`s `offer_opened=False`.
  **Die BOUNDARY wird gestellt** — ein MockAgent-Lauf erreicht in 6000 Frames auf map2 keine
  Fight-Phase, ein passiver Zähler hätte 0 gemeldet und wie ein Bestehen ausgesehen.

### Gebaut, aber nie GEFÜTTERT — die siebte und achte Instanz

- **Die drei EPC-Waffen-Enhancements griffen nie** (gemeldet). `apply_all()` hat zwei
  Aufrufer, beide tot: einer hinter `if turn_tracker.started:` (im Normalfall False), der
  andere mit `state.all_squads()` — **im Declare-Battle-Formations-Schritt LEER**, weil
  `register_unit()` bei `PREGAME_DEPLOYMENT` früh zurückgibt und die drei Container, die
  `all_squads()` liest, dort nichts enthalten. Registry, `grant()`, `is_active()` und die
  Waffenklassen waren alle korrekt; es fehlte ausschließlich eine nicht-leere Liste.
  `_all_squads(state, pregame_controller)` existiert genau für diese Falle und sagt es im
  eigenen Docstring. **Kollateral in derselben Zeile:** Student of Kauyon wurde ebenso leer
  gefüttert. **Im ECHTEN Spiel belegt** (`verify_prototype_weapons.py`):
  `apply_all(<29 squads>) -> 3`, Plasma Rifle **S8→S10, AP-3→-4, D3→D4, A1→A2**;
  `--neutralize` zeigt die gedruckten Werte.
- **NICHT GEMELDET, und der schwerste Fund: `fight_controller.on_unit_finished_fighting`
  wurde ZWEIMAL zugewiesen.** `main.py` setzte die verkettete Necron/Death-Guard-Kette und
  überschrieb sie ~120 Zeilen später mit dem Counteroffensive-Lambda; das `_previous`-Idiom
  darüber fing den Slot VOR beiden ab und rettete nichts. **Sieben Fähigkeiten feuerten nach
  einer Nahkampf-Aktivierung nie** — Undying Legions, Curse of the Walking Pox, Lethal Ichor,
  Undying Spite, To Their Final Breaths, Malevolent Souls, Vaul's Vengeance. Alle sieben
  hatten grüne Suiten, weil die ihre Controller DIREKT treiben; nur die QUELLE sieht einen
  Slot, der zweimal beschrieben wird, und der AST-Wächter (Abschnitt 4) prüft die REIHENFOLGE
  von `a.b = c`, nicht die Doppelzuweisung. **Neuer Wächter** (Abschnitt 9): jeder mehrfach
  zugewiesene `on_*`-Callback muss den vorigen zwischen den Zuweisungen LESEN. Bewusst eng —
  Listen heißen `*_reactions` und werden angehängt, Datenfelder wie `homing_beacon_bearer`
  dürfen neu gesetzt werden. **Im ECHTEN Spiel belegt** (`verify_fight_finished_chain.py`):
  **8 von 8** erreicht gegen `--neutralize`s **1 von 8**, mit den sieben namentlich.

### Drei Eignungs-Tore, die nie aufgingen

- **Aggressive Mobility war harter toter Code.** `can_use()` lehnte
  `movement_controller.selected_squad` ab — und das Panel fragt
  `buttons_for(movement_controller.selected_squad)` und sonst nichts, die Bedingung war also
  bei JEDER Auswertung wahr. `selected_squad` wird schon vom bloßen ANKLICKEN gesetzt und
  bedeutet nicht "hat seine Bewegung begonnen"; die richtige Lesart von "has not been selected
  to move this phase" ist `moved_squad_ids` + `advanced_squad_ids`, exakt wie beim Geschwister
  mit identischem gedrucktem WHEN (`game/aux_alien_expertise.py`). **Warum die Suite es nicht
  sah:** ihr `MoveStub` hatte gar kein `selected_squad`, also las die Klausel dort immer None.
- **Marker Beacon** war ein Panel-Knopf während der Bewegungsphase, und sein Tor liest
  `Objective.controlled_by` — das nur in `advance_turn_phase()` neu berechnet wird (14.02).
  Mitten in der Phase ist das der Stand VOR jeder Bewegung, also war genau der Fall, für den
  das Stratagem existiert ("aufmarschieren und sichern"), unerreichbar. Jetzt ein Angebot an
  der Phasengrenze (`phase_before == PHASE_MOVEMENT`, nach `update_control()`), mit
  `PhaseWindow` und für den Brett-Pick getaggt; die Objective-Wahl bleibt eine Liste.
- **Pinpoint Counter-Offensive** bekam vom Todes-Sweep regelmäßig `killer_squad=None`:
  `remove_dead_models()` läuft einmal pro Frame NACH der Ereignisbehandlung, und
  `_actually_finish_squad()` nullt `active_squad` — eine von der LETZTEN Waffengruppe
  ausgelöschte Einheit ist also killerlos, und das ist der einzige Fall, den dieses Stratagem
  interessiert. Jetzt AUFGESCHOBEN wie `game/protocol_vengeful_stars.py`: der Sweep sammelt,
  und `maybe_offer()` liefert den Angreifer aus den Nach-Aktivierungs-Haken, wo er als
  Argument ankommt und nicht geraten werden kann. Dazu ein zweiter Fehler: `_pending` war ein
  Einzelslot, bei zwei im selben Sweep ausgelöschten Einheiten überschrieb der zweite Prompt
  den ersten und die erste Antwort markierte den falschen Gegner — der Killer reitet jetzt in
  der Closure der Option.

### Die Charge-Reaktionskette

- **Combat Embarkation ließ die Charge in den Transporter laufen.** "If it does, your
  opponent can select new targets for that charge" war als NAMED LIMITATION eingetragen, und
  die Limitation war schlimmer als sie las: `_start_declared_move()` prüft Zustand,
  Nicht-Leerheit und `max_distance` neu, aber **nie die ZIELE**, und `embark()` nimmt die
  Modelle aus `tokens`, lässt aber ihre KOORDINATEN stehen — `check_charge_engagement()`
  engagierte also ein Phantom. Am Log belegt
  (`logs/game_20260905_203642.log:191-196`: eingestiegen, trotzdem gechargt, `closed to 0.0"`).
  Neu `ChargeController.reopen_target_selection(dropped_squad)`: **kein Zustandsumbau** — der
  Controller verlässt `DECLARING_TARGETS` während einer Reaktion gar nicht und der 2W6 steht
  schon; der gedruckte Effekt öffnet die ZIELE neu, nicht den Wurf.
  - **Das Fenster stoppt die Kette, nicht ein verschlucktes `resume`.** Die erste Fassung ließ
    `_finish()` die Fortsetzung einfach fallen; eine A/B-Sonde zeigte, dass der Wächter damit
    UNERREICHBAR ist — die Form, die dieses Repo laufend verrotten sieht. Jetzt wird die Kette
    protokollgemäß weitergereicht und `window_is_open()` beendet sie. **Und der Wächter
    musste ans KETTENENDE**: `step()` fiel nach dem letzten Reaktor unbedingt in
    `_start_declared_move()`, und der letzte Reaktor ist so oft wie nicht der, der das Fenster
    neu geöffnet hat.
  - **Der KI-Pfad brauchte nichts:** `_handle_charge()` kehrt schon zurück, wenn eine Reaktion
    die Fortsetzung besitzt, und findet beim Wiedereintritt leere `charge_targets` — es wählt
    dann neu aus `eligible_charge_target_squads()`, das aus der Tokenliste gebaut wird und die
    eingestiegene Einheit gar nicht mehr anbietet. Per `selfplay.py map2` 6000 Frames belegt
    (exit 0, kein Hänger).
  - **Eine eigene Behauptung wurde von der Sonde widerlegt und zurückgenommen:** `_finish()`
    "stellt `active_player` nicht wieder her" — gemessen stellt auf diesem Pfad NICHTS ihn um
    (das Geschwister restauriert nur, weil sein Battle-Shock-Test ihn bewegt). Ein No-op als
    Fix auszugeben wäre schlimmer als die Lücke.
- **Photon Grenades wurde einer Einheit im Transporter angeboten.** `eligible_defenders()`
  hatte keinen Embark-Term, und `is_engaged()` ist keiner: die zurückgelassenen Koordinaten
  lesen sich als frei. Die Kette reicht `targets` EINMAL gefangen an alle Reaktoren, und
  Combat Embarkation sitzt auf derselben Kette. Jetzt zwei Terme —
  `getattr(squad, "embarked_in", None)` (der kanonische Test dieses Repos) UND die Tokenliste,
  was dieselbe Zeile eine im selben Frame ausgelöschte Einheit decken lässt (Fehlerklasse 12).
  **Beide werden EINZELN geprüft**, weil sie sich in einer naiven Bühne gegenseitig decken —
  von der eigenen A/B-Sonde gefunden.

### [HAZARDOUS] wurde von der GEDRUCKTEN Waffe gelesen

`game/shooting.py`s Hazard-Ledger las `pairs[0][1].hazardous`, also das gedruckte Profil,
während jeder Laufzeit-Grant auf `_adjusted_weapon()`s Kopie liegt. Experimental Ammunitions
dritte Klausel war damit inert: +1 S und +1 AP wirkten (sie laufen über die Kopie), ein Hazard
Roll fand nie statt. Am Log belegt (`logs/game_20260905_212844.log:149-158`). Jetzt wird die
ANGEPASSTE Waffe gefragt, damit jeder künftige Grant per Konstruktion zählt statt namentlich
nachgetragen werden zu müssen; `game/fight.py` hat dieselbe Form und ist mitgezogen (heute
gibt es keinen Melee-Grant — es ist die Form, damit der nächste funktioniert). **Warum die
Suite es nicht sah:** sie fragte ausschließlich `adjusted_weapon()` und nie den Controller.

**NACHTRAG aus derselben Meldung, und der eigentlich teurere Fehler** (User nach dem Fix:
*"Hazardous bei den sunforge viel zu wenig … für jede waffe, die abgefeuert wurde muss gewürfelt
werden"*). Der Ledger zählte **eine Prüfung je ANGRIFFSGRUPPE**, nicht je Waffe — sein Kommentar
schrieb das ausdrücklich aus ("once per weapon SELECTION … not once per model"). 24.15 sagt
aber *"roll one D6 for each [HAZARDOUS] weapon that was used to make one or more of those
attacks"*, also **je WAFFE**.

- **Gemessen an der gemeldeten Einheit** (`1 Crisis Sunforge Battlesuits 1 + Commander in
  Coldstar`): 3 Suits × 2 Fusion Blaster + 4 am Commander = **10 Waffen**, die 04.03 zu **2**
  Gruppen bündelt (BS 3+ und BS 4+). Vorher 2 Würfel, jetzt 10. Am nackten Sunforge-Trupp
  end-to-end durch den echten Controller: **1 → 6**.
- **`pairs` ist bereits die richtige Menge** — ein Eintrag je (Modell, Waffe), und schon durch
  `_can_reach()` gefiltert. `len(pairs)` IST damit wörtlich "die Waffen, die benutzt wurden";
  eine Waffe außer Reichweite zählt nicht mit, was der gedruckte Halbsatz "that was used"
  verlangt. `_pending_subgroups_hazardous` ist deshalb ein ZÄHLER statt eines Flags — und wird
  weiterhin nur EINMAL je Auswahl addiert, auch wenn 13.08 die Gruppe in zwei Würfelsequenzen
  spaltet.
- **Der Blast Radius ist gemessen und NULL:** über alle fünf Fraktionen drucken genau **zwei**
  Datenblätter [HAZARDOUS] (Kharseth, Kill Rig), beide Ein-Modell-Einheiten mit genau einer
  solchen Waffe — für sie ist 1 = 1. Die Änderung kann also nur dort beißen, wo ein
  LAUFZEIT-Grant die Waffen einer ganzen Einheit erfasst, und das ist exakt der gemeldete Fall.
- **Die Suite prüfte nur, DASS gewürfelt wird, nicht wie oft** — genau die Zahl, um die es geht.
  Sie zählt jetzt WÜRFEL gegen die Waffenzahl der Einheit, mit der Gegenprobe, dass es ein
  einziger Wurf bleibt (ein Prompt je Waffe wäre eine andere Art Fehler).

### Prompt-Hygiene und die zwei UI-Änderungen

- **Der Resurrection Orb fragte an JEDER Phasengrenze** (fünfmal pro eigenem Zug, jedes Mal
  als Brett-Pick über das ganze linke Panel) und hielt kein Abgelehnt-Gedächtnis — die
  "Decline"-Option war wörtlich `("Decline", None)`. **User-Entscheidung: nur erneut fragen,
  wenn sich etwas geändert hat.** Ein Ablehnen wird gegen die Zahl gemerkt, um die es geht
  (`recoverable_wounds`); die Frage kommt wieder, sobald es MEHR zu holen gibt. Gemessen:
  10 Phasengrenzen → **1 Prompt**, nach einem weiteren Verlust wieder angeboten, danach wieder
  still. **Bewusst NICHT in `reset_turn()` geleert** — ein neuer Zug auf unverändertem Brett
  ist ein unverändertes Brett.
- **Solid-image Projection Unit ist jetzt ein ZWEI-SCHRITT-Brett-Pick** (User-Entscheidung).
  Das Hindernis war echt und stand im Quelltext: jede Einheit wurde ZWEIMAL angeboten (einmal
  je Ziel), und `unit_pick.pending()` lehnt eine doppelt genannte Einheit zu Recht ab. Schritt
  eins nennt jede Einheit genau einmal und ist getaggt, Schritt zwei wählt das Schicksal und
  ist eine gewöhnliche Liste. Damit fällt der einzige Grund weg, aus dem das Modul auf der
  Ausnahmeliste stand — `test_unit_pick.py` Abschnitt 6 führt sie als MENGENDIFFERENZ und
  hätte einen abgelaufenen Eintrag ohnehin gemeldet.
- **"WHY YOU ARE CHOOSING" zieht in die LINKE Spalte** (User-Entscheidung), mit
  **Scrollleiste**. Die alte Begründung fürs rechte Panel bleibt gültig und wird anders
  aufgelöst: dort waren 336 px frei, und Abschneiden war deshalb vertretbar; in der 220 px
  breiten linken Spalte, die schon Prompt, Einheitenliste und den Ausweg trägt, muss eine
  lange Regel LESBAR bleiben statt bloß zu passen. `button_style.draw_scrollbar()` ist
  dieselbe Leiste, die der Army-Rules-Leser und die Hover-Datacard benutzen; der Scroll-Offset
  hängt am REGELNAMEN, damit eine andere Entscheidung ihre Regel oben öffnet. Das Mausrad wird
  im bestehenden frühen `MOUSEWHEEL`-Zweig angeboten und nur beansprucht, solange der Cursor
  über der Box steht UND es etwas zu scrollen gibt — sonst wäre der Brett-Zoom weg.

### Getestet

Volle Regression **184 Suiten, ~16240 Prüfungen, 183 grün / 0 rot / 1 bekannt**,
`run_tests.py --smoke` komplett grün (alle neun schweren Skripte, inkl. `smoke_pregame.py`,
`smoke_unit_pick.py` und `selfplay.py map2 1500`). Neu bzw. erweitert:
`test_tau_detachment_stratagems.py` (313 → **384**, u. a. der erste Verhaltenstest für Wall of
Mirrors überhaupt — vorher wurde dort nur `is_eligible_unit()` geprüft),
`test_aeldari_detachment_stratagems.py` (**970**), `test_tau_enhancements.py` (**331**),
`test_decision_rule_panel.py` (**53**, auf die linke Spalte neu geschrieben),
`test_deterministic_gates.py` (**43**), `test_unit_pick.py` (**67**),
`test_event_chain_wiring.py` (**67**, zwei neue Wächter: Abschnitt 8 die Naht, Abschnitt 9 die
Doppelzuweisung).

**37 A/B-Sonden über vier Dateien, ALLE beißend** — `ab_end_of_fight_window.py` (7),
`ab_stratagem_offers.py` (10), `ab_charge_window_and_prompts.py` (9),
`ab_decision_rule_panel.py` (11).

**Im ECHTEN Spiel belegt**, je mit `--neutralize`, das die Meldung reproduziert:

| Sonde | gefixt | `--neutralize` |
|---|---|---|
| `verify_wall_of_mirrors.py` | Angebot an den Kauyon-Spieler, Uhr steht auf `Command`, Ghostkeel **wirklich in den Reserven** | **gar kein Angebot** (die falsche Seite hat keine berechtigte Einheit) |
| `verify_prototype_weapons.py` | `apply_all(<29 squads>) -> 3`, Plasma Rifle **S10 AP-4 D4 A2** | `<0 squads> -> 0`, Plasma Rifle S8 AP-3 D3 A1 |
| `verify_fight_finished_chain.py` | **8 von 8** Reaktoren erreicht | **1 von 8** (nur Counteroffensive) |

Die Wall-of-Mirrors-Sonde STELLT genau eine Tatsache und sagt warum: T'au gegen Necrons auf map2
schafft gemessen **zwei Phasenwechsel in 3000 Frames**, die Fight-Grenze ist passiv also
unerreichbar (die dokumentierte MockAgent-Grenze) — ein passiver Zähler hätte 0 gemeldet und wie
ein Bestehen ausgesehen. GEMESSEN wird nur die Grenze, die dem GEGNER der Kauyon-Seite gehört,
und `ending_player` ist in beiden Läufen derselbe Wert; sonst landeten die zwei Läufe auf
verschiedenen Grenzen und die Vor-Fix-Welt träfe die richtige Seite zufällig.

Für [HAZARDOUS] gibt es bewusst KEINE Laufzeit-Sonde: die Mechanik liegt vollständig im
`ShootingController`, den die Suite end-to-end mit echten Würfeln fährt — es gibt keine
`main.py`-Verdrahtung, die eine Sonde zusätzlich zeigen könnte.

**Neun Sonden bissen zuerst NICHT, und jede war ein Befund über den TEST** (Fehlerklasse 24):
die zwei `main.py`-Argument-Sonden (keine Suite las die Aufrufstelle → Quell-Wächter), Cost of
Victory (die Suite parkte die Uhr auf Fight, ein Moment, den es nie gibt → Grenztest), zwei
Marker-Beacon-/Pinpoint-Verdrahtungspins, die redundante `_pending`-Sonde, die zwei
Photon-Grenades-Terme, die sich gegenseitig deckten, und der Combat-Embarkation-Wächter, den
ein verschlucktes `resume` unerreichbar machte.

## Absturz beim Feuern der D-cannon (2026-09-08)

**Gemeldet:** *"absturz im letzten spiel / feuern der d-cannon"*, mit
`AttributeError: 'function' object has no attribute 'add'` aus
`main.py:5458 → shooting_controller.on_dice_acknowledged() → damage_resolution.py:423`.

**ZWEI Fehler auf EINER Waffe.** Der zweite ist beim Reproduzieren des ersten aufgefallen und
ist der teurere: er hat auf JEDEM D-cannon-Schuss zugeschlagen, nicht nur auf jedem sechsten.

### 1. Zwei Log-Idiome, unterschieden allein am FELDNAMEN

Dieses Repo führt zwei Protokoll-Konventionen, und nichts trennt sie außer dem Namen des Feldes:

| Feld | was es ist | wie es benutzt wird | Träger |
|---|---|---|---|
| `self.game_log` | das GameLog-OBJEKT | `self.game_log.add(msg)` | ~90 Controller |
| `self.log` | ein CALLABLE | `self.log(msg)` | **4** Module |

`damage_resolution.py`s automatischer Damage-Reroll war in der ERSTEN Konvention gegen ein Feld
der ZWEITEN geschrieben — **die einzige solche Zeile im ganzen Produktivcode** (gemessen:
`grep` findet genau eine). Sie hat es ausgeliefert, weil die **einzige** Fähigkeit, die diesen
Zweig überhaupt erreicht, Structural Collapse der D-cannon ist ("re-roll a Damage roll of 1"):
der Rumpf war nie ein einziges Mal gelaufen.

**Warum die Suite grün blieb** — und das ist die Lehre, nicht der Tippfehler: sie trieb
`offer.auto_reroll_for(3)` DIREKT und pinnte den Quellstring `"auto_reroll_for(amount)"`. Beides
hält perfekt an einem Zweig, dessen RUMPF nie ausgeführt wird. Die Datei trug sogar einen
Abschnitt mit der Überschrift "END TO END through the real ShootingController" — er prüfte, dass
das Angebot GEBAUT und richtig beschriftet ist, und ließ nie einen Würfel fallen.

### 2. Die zweite Hälfte: ein Reroll, den die Regel nie gewährt

Gedruckt: *"re-roll a Damage roll of 1. **If that attack targets a TITANIC unit**, you can
re-roll the Damage roll **instead**."* Zwei Klauseln, und die zweite hängt am ZIEL.

Das Angebot wurde mit einem `decision_manager` gebaut, **bedingungslos** — also öffnete jeder
D-cannon-Wurf, der KEINE 1 war, einen "Structural Collapse: re-roll the Damage roll (6)?"-Prompt.
Gemessen: gegen ein nicht-TITANIC-Ziel **stand der Prompt, und die Session parkte darauf, sodass
der Schaden gar nicht landete — 0 statt 6**. `structural_collapse.targets_titanic()`, geschrieben
für genau diese Klausel, hatte **null Produktiv-Aufrufer** (siebte Instanz der
"gebaut, aber nie GEFÜTTERT"-Klasse).

- **"INSTEAD" macht die beiden EXKLUSIV**, nicht additiv: gegen TITANIC ERSETZT der freie Reroll
  den automatischen. Also `automatic_faces=()` **und** `offerable=True` dort, und genau umgekehrt
  sonst — nicht beides gleichzeitig.
- **`DamageRerollOffer.offerable` ist neu und trennt zwei Fragen, die vorher eine waren:**
  `can_offer()` heißt "ist an diesem Würfel noch ein Reroll übrig", `offerable` heißt "darf die
  FRAGE überhaupt gestellt werden". Default `True`, also sind die vier reinen Angebote (Sunforge,
  Breath of Vaul, Assured Destruction, Path of the Warrior) per Konstruktion unberührt — eigene
  A/B-Sonde, die den Default auf `False` dreht und `test_sunforge.py` rot macht.
- **Nichts Gebautes trägt TITANIC** (die zwei Wraithknights sind bewusst nicht gebaut), der
  TITANIC-Zweig ist also gemessen inert und wird im Test von HAND gestellt — dieselbe Behandlung,
  die das Prädikat selbst bekommt.

### Der Wächter: `test_event_chain_wiring.py` §17d

**Der Spiegel von §17b, eine Ebene tiefer.** §17b bewacht den AUFRUFER ("was man einer Session
als `log=` reicht, muss aufrufbar sein"); §17d bewacht den EMPFÄNGER ("eine Klasse, die ein
Callable speichert, darf es nicht als Objekt behandeln"). Beide Richtungen sind jetzt zu.

- **Per AST, und das ist keine Stilfrage:** `.log.add(` matcht auch
  `strategic_reserves.withdraw_to_reserves(log=...)`, dessen Parameter `log` wirklich das OBJEKT
  ist (alle neun Aufrufer reichen `log=self.game_log`) und das damit korrekt ist. Gepinnt wird der
  SELF-ATTRIBUT-Vertrag, also wird der geparst.
- **Selbstpflegend:** die Menge der Klassen wird gefunden (`__init__` nimmt `log` und weist
  `self.log = log` zu), nicht aufgeschrieben. Ein fünftes Modul erbt den Wächter gratis.
- **Mit Positiv-Hälfte und Liveness:** jedes gefundene Modul muss `self.log(...)` auch wirklich
  RUFEN — ein Modul, das `log` speichert und nie benutzt, machte die Prüfung darüber vakuum-grün.
- Dazu die von §17b auf ALLE vier Klassen verallgemeinerte Aufrufer-Hälfte (gemessen: 20
  Konstruktionsstellen, 0 falsch).

### Getestet

- `test_support_weapon_platforms.py` 154 → **166/166** (neuer Abschnitt 5b: der Schuss END TO END
  durch den echten Controller — der Reroll passiert wirklich, ohne Prompt, und die re-gewürfelte 6
  landet als D6+2 = 8; die Gegenprobe, dass ein Würfel von 4 NICHT neu geworfen wird und seine 6
  landet; und der TITANIC-Zweig in beide Richtungen). **Ein MEHRWUNDIGES Ziel ist Pflicht** —
  Überschussschaden läuft nicht über, gegen 1-Wunden-Guardians sind eine re-gewürfelte 8 und eine
  behaltene 3 nicht unterscheidbar. Und der Schuss läuft durch `_begin_resolution()`, weil
  `on_dice_acknowledged()` ohne `current_group` früh zurückkehrt — eine Sonde, die das überspringt,
  misst NICHTS und sieht wie ein Bestehen aus (eigener Fehler, beim Reproduzieren bezahlt).
- `test_event_chain_wiring.py` 150 → **165/165**.
- **Neu `ab_dcannon_damage_reroll.py`: 7 A/B-Sonden an der QUELLE, alle beißend** — die
  `.log.add`-Zeile zurück (Suite UND Wächter), ein Session-Konstruktor, der das GameLog-Objekt
  reicht, das TITANIC-Tor weg, das `offerable`-Flag gebaut-aber-ungelesen, der Default auf `False`,
  und die ganze Vor-Fix-Welt.
- **Eine eigene Sonde ließ die Suite ABSTÜRZEN statt rot zu werden** (achtzehnte Instanz dieser
  Lehre): §5b fängt den Absturz jetzt und meldet ihn als FEHLGESCHLAGENE Prüfung mit dem
  Traceback-Text, statt den Lauf abzubrechen — ein abgebrochener Lauf sagt nicht, WELCHE
  Zusicherung gebrochen ist.

### Im ECHTEN Spiel belegt

`verify_dcannon_damage_reroll.py` fährt `selfplay.py`s echte `main()`-Schleife mit
**`aeldari_guardian_battlehost` als PLAYER 1** — der EINZIGEN ausgelieferten Liste, die die
D-cannon Platform überhaupt fieldet (gemessen, nicht angenommen), also der Armee des Users; und
auf der MENSCHEN-Seite, weil `config` die Necrons als Player 2 ausliefert und eine Frage über die
Waffe des Menschen sonst die Armee der KI misst.

| | gefixt | `--neutralize` (Vor-Fix) |
|---|---|---|
| Würfel 1: Absturz | **keiner** | `AttributeError: 'function' object has no attribute 'add'` |
| Würfel 1: neu geworfen | **ja**, ohne Prompt | nein |
| Würfel 1: Schaden gelandet | **8** | **0** |
| Würfel 4: Prompt erhoben | **nein** | **JA** |
| Würfel 4: Schaden gelandet | **6** | **0** |

**Drei gestellte Tatsachen, jede mit Grund benannt:** der Schuss selbst (über 260 Frames kommt
"D-cannon feuert UND ein Save fällt UND der Damage-Würfel zeigt 1" nie zusammen — die
dokumentierte MockAgent-Grenze; ein passiver Zähler hätte 0 gemeldet und wie ein Bestehen
ausgesehen), die 24.12-FNP-Etappe (sie ist ein eigener Würfelschritt, und eine Sonde, die davor
stehenbleibt, meldet 0 Schaden und liest sich wie ein Versagen des Gemessenen), und ein GELEERTER
Prompt-Puffer vor jeder Messung. Alles danach ist echt.

- **Das Ziel wird als UNMITIGIERT ausgewählt, nicht als das fetteste.** Der C'tan Shard ist das
  dickste Necron-Ziel und trägt Necrodermis, das aus 8 still eine 7 macht — die Sonde hätte dann
  jene Fähigkeit gemessen statt dieser. Gefragt werden `molten_form` und `damage_reduction`, die
  Module, denen die Frage gehört, also schließt eine künftige Minderungsquelle ihren Träger von
  selbst aus.
- **Zwei eigene Sondenfehler, beide gemessen:** der Neutralize-Pfad scheiterte STILL, weil
  `drive()` sein `SystemExit` schluckte (er meldet den Grund jetzt in `RESULTS`); und
  `decision_manager.is_pending` ist die GANZE Queue, nicht die Frage dieses Schusses — die
  laufende Partie hat dort regelmäßig einen eigenen Prompt, was eine Messung sprunghaft falsch
  machte.

## Bekannte offene Punkte

- Ein von allen Seiten umstelltes Fahrzeug kann steckenbleiben (Ein-Wegpunkt-Heuristik + A*, keine
  formationsbewusste Pfadsuche).
- Keine explizite Right-of-Way-Koordination zwischen Einheiten im selben Zug (nur implizit über
  `priority` und die Korridor-/Ausladezonen-Stufen).
- `GreaterGoodController.choose_target()` kann bei einer (nie auftretenden) ungültigen Zielwahl in
  `CHOOSING_TARGET` hängen bleiben.
- `TransportController`s Rapid-Disembark-Pfad prüft 20.04s Zonen-Sperre nicht.
- **Mont'kas Killing Blow gewährt [ASSAULT], erreicht aber 10.05s Advance-Tor nicht** — gemessen,
  benannt, bewusst offen: `coldstar.weapon_has_assault()` bekommt keinen `turn_tracker`, und
  Mont'kas Bedingung ist ein Rundenfenster. Nachzureichen heißt, das Argument durch
  `_attack_groups()`s elf Aufrufstellen auf dem heißesten Schusspfad zu fädeln, und eine HALBE
  Fädelung wäre schlechter als der Status quo (die Einheit bekäme Assault Shooting angeboten und
  danach null berechtigte Waffen). **Sie ist LIVE, nicht dormant** — hier stand bis zum 2026-09-06
  „kein ausgeliefertes Roster fieldet Mont'ka", was seit dem Tag falsch war, an dem `tau_montka`
  angelegt wurde: die Liste fieldet Mont'ka, und Killing Blow gewährt in den Runden 1-3 JEDER ihrer
  Fernkampfwaffen [ASSAULT], das sie nach einem Advance nicht benutzen kann.
  `test_event_chain_wiring.py` Abschnitt 7 nennt die Lücke namentlich, damit sie nicht verschwindet.
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

## Blades of Asuryan: [PISTOL] erreichte das EIGNUNGS-TOR nicht (2026-09-08)

**Gemeldet:** *"blades of asurian — ich konnte zwar mit asurmen schießen, aber nicht mit dem rest
meines avengers squads. das umwandeln der waffen in pistol hat wohl nicht geklappt."*

**Fehlerklasse 10 in ihrer teuersten Form, zum ZWEITEN Mal — diesmal für [PISTOL] statt [ASSAULT].**
Die Warnung dafür stand seit dem Sudden-Storm-Fix wörtlich in `coldstar.weapon_has_assault()`s
Docstring; sie galt nur nicht für das Nachbar-Keyword.

- **Reproduziert an der Quelle, bevor etwas angefasst wurde** (Asurmen + Dire Avengers in
  Engagement Range): nach dem Kauf gewährte die **ADJUSTER-KETTE [PISTOL] an 6 von 6**
  Fernkampfwaffen, während das **EIGNUNGS-TOR weiter 1 von 6** sah — Asurmens Bloody Twins, die
  gedruckt [PISTOL] ist. Genau deshalb konnte er schießen und sonst niemand.
- **Die zwei Leser sehen einander nicht ähnlich.** `ShootingController`s Adjuster-Kette ist die
  Schadensmathematik — leicht zu verdrahten, leicht zu testen, und das, was der bestehende Test
  fuhr. `is_close_quarters()`, erreicht aus `available_shooting_types()` und
  `_weapon_eligible_for_type()`, ist das EINZIGE, was entscheidet, ob eine ENGAGIERTE Einheit
  überhaupt schießen darf (10.06) — und genau dafür kauft man das Stratagem.
- **Die zwei Zeilen standen NEBENEINANDER in derselben Funktion**, und das ist der ganze Befund:

      has_assault        = any(weapon_has_assault(w, squad) for ...)   # grant-aware
      has_close_quarters = any(is_close_quarters(w)         for ...)   # printed only

- **Nur EIN [PISTOL]-Grant existiert heute** (gemessen: genau ein Modul schreibt zur Laufzeit
  `.pistol = True`), der Sweep ist also abgeschlossen und nicht bloß gestoppt.

### Der Fix: `squad` ist PFLICHT, kein Default

`is_close_quarters(weapon, squad)` und `_weapon_side(weapon, squad)` nehmen die Einheit jetzt
verbindlich — sechs Aufrufstellen, alle in `shooting.py`, alle mit einem Modell oder Squad im
Scope. **Ein Default wäre exakt der Fehler, den der Parameter verhindern soll** (dieselbe
Begründung, die `_detectable_models()` für seinen eigenen gibt): eine vergessene Aufrufstelle
krachte dann nicht, sie läse still nur das gedruckte Flag.

- **`shooting.py` importierte das Grant-Modul längst** (Zeile 61, für die Adjuster-Kette) — das Tor
  hat es nie gefragt. Es gab also nichts zu verdrahten, nur etwas zu fragen.
- **24.07s Seitensperre zieht mit**, und das ist eine Regelaussage, keine Kosmetik: eine gewährte
  [PISTOL] setzt die Waffe wirklich auf die Pistolen-Seite, und wenn der Grant JEDE Fernkampfwaffe
  der Einheit erfasst, hört die Sperre auf, sie zu spalten — was „sie sind jetzt alle Pistolen"
  bedeutet. Behauptet im Docstring UND gemessen (`test_close_quarters_shooting.py` §6), weil eine
  unbelegte Behauptung über eine Regel genau der Weg ist, auf dem das Tor überhaupt aus dem Takt
  geriet.

### Warum der bestehende Test es nicht sah

**Abschnitt 3e fuhr ausschließlich `gba.adjusted_weapon()`** plus einen Quell-Grep, dass
`shooting.py` das Modul erwähnt. Beides hält perfekt, während das Tor nie fragt. Neu ist §3e2, das
**BEIDE Leser GETRENNT** misst — zusammen geprüft würde einer den anderen tragen.

**Und die Typ-Ebene allein hätte es NICHT gefangen**, was die Meldung so unauffällig machte: mit
Asurmen im Trupp liefert `available_shooting_types()` in BEIDEN Welten `['Close-Quarters']` — seine
gedruckte Pistole trägt den Typ. Nur die WAFFENZAHL unterscheidet sie (1 gegen 6). Deshalb steht
daneben der Fall OHNE gedruckte Pistole: dort geht die Einheit von „kann gar nicht schießen" auf
Close-Quarters, und das ist, was das CP wirklich kauft.

### Der Wächter: `test_event_chain_wiring.py` §19

Der [PISTOL]-Zwilling von §7, faction-blind: **jedes Modul, das zur Laufzeit `.pistol = True`
vergibt, muss im RUMPF von `is_close_quarters()` genannt sein.** Ein Verhaltenstest kann einen
ZWEITEN Grant nicht sehen, weil es ihn noch nicht gibt. Dazu prüft er die SIGNATUR (Squad als
letztes Argument, kein Default) — eine vergessene Aufrufstelle soll krachen statt still zu
schweigen —, und er trägt eine Liveness-Zeile, weil ein Sweep, der keine Grantoren mehr findet, eine
leere Differenz meldet und wie ein Bestehen aussieht. **Die Ausnahmeliste ist LEER**, mit §7s
Kommentar daneben: ein künftiger Eintrag muss die MESSUNG mitbringen, die ihn dormant nennt, nicht
die Erinnerung an eine.

### Getestet

- `test_aeldari_detachment_stratagems.py` 998 → **1013/1013** (neu §3e2),
  `test_close_quarters_shooting.py` 33 → **47/47** (neu §6 — diese Suite besitzt 10.06 und 24.07 und
  hatte bis dahin NUR gedruckte Pistolen gestagt, war für die andere Eingabe des Tors also blind),
  `test_event_chain_wiring.py` 142 → **150/150**.
- **Neu `ab_blades_of_asuryan_gate.py`: 8 A/B-Sonden an der QUELLE, alle beißend.** Die erste ist
  die tragende: sie lässt die Adjuster-Kette unangetastet gewähren und blendet NUR das Tor aus —
  die ausgelieferte Welt, nicht eine mit abgeschaltetem Stratagem. Die zwei Tor-Hälften kippen
  einzeln (`available_shooting_types` → gar keine Option; `_weapon_eligible_for_type` → Option,
  aber keine Waffen).
- **Zwei Sonden bissen zuerst NICHT, beide Befunde über den TEST** (Fehlerklasse 24), und beide
  Lücken sind geschlossen statt die Sonde umgehängt: `test_close_quarters_shooting.py` stagte nie
  einen GEWÄHRTEN Grant, und die 24.07-Seitenzuordnung war überhaupt nicht gemessen.
- **Ein fremder Pin wurde zu Recht rot** — eine Staging-Zeile, die die neue Pflicht-Signatur
  brauchte; sie fragt jetzt beide Lesarten (mit Squad und printed-only) und pinnt, dass sie hier
  übereinstimmen.
- Volle Regression **194 Suiten, ~17225 Prüfungen, 193 grün / 0 rot / 1 bekannt**,
  `run_tests.py --smoke` komplett grün (alle neun schweren Skripte).

### Im ECHTEN Spiel belegt

`verify_blades_of_asuryan_gate.py` fährt `selfplay.py`s echte `main()`-Schleife mit
`aeldari_guardian_battlehost` als PLAYER 1 und misst die LIVE von `main()` gebauten Objekte:

| | gefixt | `--neutralize` |
|---|---|---|
| Fernkampfwaffen der Einheit | 12 | 12 |
| davon gedruckt [PISTOL] | 1 | 1 |
| **die das Tor feuern lässt** | **12** | **1** |
| engagiert angebotener Typ | `['Close-Quarters']` | `['Close-Quarters']` |

Die letzte Zeile ist der eigentliche Fund: **der Typ wird in BEIDEN Welten angeboten**, weil
Asurmens gedruckte Pistole ihn trägt — die Einheit sah also nicht kaputt aus, und nur die
Waffenzahl verrät es. Genau das hat der Bericht beschrieben.

**GESTELLT werden ZWEI Tatsachen, beide benannt:** der KAUF (ein Panel-Knopf des Menschen, und
dieser Harness klickt keinen — zuerst gemessen: 2500 Frames, null Käufe; die Sonde treibt deshalb
den LIVE-Controller über sein echtes `use()`, sodass jede andere Eignungsklausel echt beantwortet
wird) und die ENGAGEMENT-Lage (als Token-LISTE mit einem synthetischen Nachbarn — auf dem Brett
bewegt sich nichts). Alles Übrige ist echt.

## "TARGET: One <X> unit from your army" wurde NICHT gewählt (2026-09-08)

**Gemeldet:** *"cost of victory wird mir pauschal angeboten, aber ich habe 3 guardian squads. ich
kann nicht wählen welchen squad zurück in reserve schicken will. es muss auf dem feld angeklickt
werden."*

- **Reproduziert an der Quelle, bevor etwas angefasst wurde:** mit drei berechtigten Guardian
  Defenders öffnete das Angebot einen Prompt, der EINEN von ihnen nannte — den in Sortierreihenfolge
  ersten —, mit den Optionen `['Use (1 CP)', 'Decline']`, **keine davon mit einem Squad getaggt**,
  also gab `unit_pick.pending()` `None` zurück und es konnte nie ein Brett-Klick sein. Der Spieler
  wurde gebeten, eine Wahl zu bestätigen, die die Engine schon getroffen hatte.
- **VIER Stratagems hatten diese Form, und alle vier drucken dieselbe TARGET-Zeile:** Cost of
  Victory (GUARDIANS), Webway Tunnel (ASURYANI INFANTRY), Skyborne Sanctuary (unengaged ASURYANI)
  und Overflight (ASURYANI MOUNTED). **"One <X> unit from your army" ist eine Wahl des SPIELERS**;
  jedes der vier lief über die berechtigten Einheiten, bot die erste an und kehrte zurück.
- **Das FÜNFTE mit derselben gedruckten Zeile war schon richtig gebaut** — Kauyons Wall of Mirrors
  (`[(s.name, cb, s) for s in candidates]`), und genau das macht die vier als Defekt lesbar statt
  als Design. Ausgerechnet Cost of Victorys eigener Docstring vergleicht sich mit dessen Nachbarn.

### `game/unit_choice_offer.py` — 33. Extraktion, und NICHT `per_unit_offer`

Die zwei sind leicht zu verwechseln, weil der FALSCHE Code für beide gleich aussieht:

| Modul | Frage | Prompts |
|---|---|---|
| `per_unit_offer.offer_each()` | "JEDE berechtigte Einheit bekommt ihr EIGENES Angebot" (eine FÄHIGKEIT: Airborne Agility, Ride the Wind, Cloudstrider) | N, verkettet |
| `unit_choice_offer.offer_one_of()` | "der Spieler wählt EINE davon" (ein STRATAGEM) | 1, N getaggte Optionen |

**Die vier waren zu keiner der beiden Formen geschrieben:** ein Prompt über eine willkürlich
gewählte Einheit beantwortet keine der zwei Fragen.

- **EIN Request statt einer Kette**, und das ist keine Abkürzung: `per_unit_offer` verkettet
  bewusst, weil sich Eignung zwischen Antworten ändern kann und Ride the Wind einen laufenden
  Zähler druckt. Bei EINER Wahl gilt beides nicht — und jeder Kandidat muss GLEICHZEITIG sichtbar
  sein, damit ein Brett-Pick überhaupt etwas bedeutet: **die Ringe SIND der Prompt**.
- **Das FENSTER bleibt beim Aufrufer.** `PhaseWindow` zu armen ist zwei Zeilen, aber WER an einer
  Phasengrenze reagieren darf, ist die gedruckte WHEN-Zeile ("your opponent's Fight phase" bietet
  der Gegenseite; "the end of THE Fight phase" gehört niemandem und bietet beiden) — eingefaltet
  wäre das ein Flag je WHEN-Klausel für eine Frage, die das Modul nicht sehen kann.

### Skyborne Sanctuary ist ZWEISTUFIG, weil seine TARGET-Zeile ZWEI Dinge nennt

"One unengaged ASURYANI unit ... **and** one friendly TRANSPORT it is able to embark within" — es
fragte nach keinem von beiden: Prompt über die erstsortierte Einheit, Transporter still als
`transports_for(squad)[0]`. Jetzt Brett-Pick für die Einheit, danach eine gewöhnliche LISTE für den
Transporter — **und nur, wenn es wirklich mehr als einen gibt** (Fehlerklasse 5). Dass die alte
Ein-Schritt-Fassung überall dort richtig las, wo genau ein Wave Serpent in Reichweite stand, ist der
Grund, warum sie überlebt hat. Eine LISTE und kein zweiter Brett-Pick: die Optionen nennen
TRANSPORTER desselben Spielers, die unter der gerade angeklickten Einheit stehen können.

### Warum keine der vier Suiten es sah

**Jede stagt genau EINE berechtigte Einheit** — und bei einem Kandidaten sind die kaputte und die
richtige Form nicht unterscheidbar. Deshalb ist die tragende Prüfung der neuen Suite nicht "ein
Prompt ging auf", sondern **"ein Klick auf den ZWEITEN Kandidaten löst den ZWEITEN auf"**: eine
bloße Options-ZÄHLUNG besteht auch gegen ein Angebot, das jede Option auf dieselbe Einheit
verdrahtet (die Late-Binding-Sonde belegt genau das).

### Der Wächter: `test_event_chain_wiring.py` §18

**Ein Angebot, das seinen Request INNERHALB einer Kandidaten-Schleife erhebt, muss mindestens eine
Option mit einer Einheit TAGGEN.** Eine Einheit im Prompt-TEXT zu nennen und ein nacktes Ja/Nein
anzubieten ist die gemeldete Form. Faction-blind, per AST, mit Liveness-Zeile.

- **Was er BEWUSST nicht meldet, gemessen statt angenommen:** vier per-Unit-FÄHIGKEITEN erheben
  ihren Request ebenfalls in so einer Schleife (`auxiliary_cadre`, `elemental_ensnarement`,
  `hallucinogen_grenades`, `neocapacitor_shields`). Alle vier taggen ihre Optionen mit der
  FEIND-Einheit, die die Fähigkeit anzielt — dort wird also weiterhin auf dem Brett gewählt, und die
  Schleife läuft über TRÄGER, was eine andere Frage ist. Ein Wächter, der sie meldet, ist eine
  Fehlalarm-Maschine, und ein Wächter mit Fehlalarmen wird gelöscht.
- **Er muss ein LOKALES auflösen**, und das hat seine eigene erste Runde gefunden:
  `neocapacitor_shields` baut `options = [...]` und übergibt dann den Namen — eine Prüfung, die nur
  die Argumente des Aufrufs durchsucht, meldete einen sehr wohl anklickbaren Prompt als ungetaggt.
  Eigene A/B-Sonde dafür.

### Ein fremder Wächter wurde zu Recht rot, und ist gewachsen statt aufgeweicht

`test_ai_mode.py`s "no class takes auto_players and ignores it" meldete alle vier: sie LESEN
`self.auto_players` nicht mehr, sie reichen es an den geteilten Helfer weiter. Der `forwards`-Term
kannte nur die Weitergabe an eine BASIS-Klasse. Er kennt jetzt auch die an einen KOLLABORATOR — und
**die Zusicherung ruht nicht auf dem Token**: alle vier werden in der neuen Suite mit einem
KI-Besitzer gefahren und müssen nichts anbieten und ihr Fenster wieder schließen.

### Getestet

- Neu `test_unit_choice_offers.py` (**64/64**, sechs Abschnitte — eine Datei für EINEN Defekt über
  vier Module, dieselbe Begründung wie `test_mortal_wound_drains.py`), plus Wall of Mirrors als
  gemessene REFERENZ. `test_event_chain_wiring.py` → **142/142** (neuer §18),
  `test_ai_mode.py` **61/61**.
- **Neu `ab_unit_choice_offers.py`: 12 A/B-Sonden an der QUELLE, alle beißend** — je Controller die
  alte Schleife byte-für-byte zurück, dazu drei auf den Helfer selbst (Tag weg → 42/64, nur der
  erste Kandidat → 48/64, Late Binding → 59/64) und die ganze Vor-Fix-Welt (**32/64**).
- **Zwei Befunde über den TEST, beide von den Sonden** (Fehlerklasse 24): die Sonden ließen die neue
  Suite zuerst ABSTÜRZEN statt rot zu werden (`unit_pick.pending()` gibt in der Vor-Fix-Welt `None`,
  und `.squads` darauf bricht den ganzen Lauf ab) — jetzt über einen `_NoPick`-Platzhalter; und die
  zwei Sonden gegen `test_aeldari_detachment_stratagems.py` bzw. `test_aeldari_stratagem_ui.py`
  meldeten **NO BITE**, was WAHR ist: die Suiten stagen eine Einheit und KÖNNEN diesen Defekt nicht
  sehen. Sie zielen jetzt auf den Quell-Wächter, der die Klasse wirklich abdeckt.
- Volle Regression **193 Suiten, ~17166 Prüfungen, 192 grün / 0 rot / 1 bekannt**,
  `run_tests.py --smoke` komplett grün (alle neun schweren Skripte).

### Im ECHTEN Spiel belegt

`verify_cost_of_victory_choice.py` fährt `selfplay.py`s echte `main()`-Schleife mit
**`aeldari_guardian_battlehost` als PLAYER 1** — der ausgelieferten Liste, die Guardian Battlehost
fieldet und **genau DREI GUARDIANS-Einheiten** hat, also die gemeldete Armeeform wörtlich, statt
einer für die Sonde erfundenen Szene. Sie liegt auf der MENSCHEN-Seite, weil eine Frage über dessen
Prompts sonst die Armee der KI misst (die Lehre der drei Necron-Sonden).

| | gefixt | `--neutralize` |
|---|---|---|
| berechtigte Einheiten auf dem Brett | 3 | 3 |
| vom Prompt genannte Einheiten | **3** | **0** |
| per Brett-Klick beantwortbar | **ja** | **NEIN** |
| geringte Einheiten | **3** | 0 |
| angeklickt wurde NICHT die erste | **2×** | 0 |
| die angeklickte Einheit zog sich zurück | **2×** | 0 |

`--neutralize` meldet die Meldung wörtlich: `prompt 'Cost of Victory (1 CP): pull 1 Guardian
Defenders 1 + Farseer + Warloc' -> NOT a board pick; 0 unit(s) named, 3 eligible on the board`.

**GESTELLT wird EINE Tatsache, und der Grund steht im Modulkopf:** dass die Schlacht überhaupt ein
Fight-Phasen-Ende erreicht. Auf diesem Harness überlebt allein die Schussphase das Framebudget, die
Grenze ist passiv also unerreichbar (die dokumentierte MockAgent-Grenze) — ein passiver Zähler hätte
0 gemeldet und wie ein Bestehen ausgesehen. Alles danach ist echt.

## Zwei Meldungen aus einer Partie (2026-09-08)

Beide reproduziert, bevor etwas angefasst wurde; beide haben eine Ursache, die MEHR als die
gemeldete Fähigkeit betrifft.

### "nur einer der beiden Vespid-Squads wurde gefragt" — drei Controller, ein Defekt

**Gemeldet:** *"ich habe 2 vespiden, aber die rückkehr in reserve wurde mir immer nur von einem der
beiden squads angeboten."*

- **Reproduziert an der Quelle:** zwei berechtigte Vespid-Einheiten, `offer_at_end_of_turn()` →
  **ein** Prompt. Der Rumpf war eine Schleife, die beim ERSTEN berechtigten Trupp `request()` rief
  und `return True` machte; `main.py` ruft die Methode genau einmal je Zugende, also gab es kein
  zweites Angebot.
- **Dieselbe Schleife steht dreimal da** — Airborne Agility (Vespid), Ride the Winds
  Rückzugs-Klausel (Windrider Host) und Cloudstrider (Aeldari) —, und alle drei tragen einen
  KOMMENTAR, der das Gegenteil verspricht: `main.py` schreibt neben den Aufruf "unlike Airborne
  Agility, which is per unit", und Cloudstrider schreibt die Ausrede aus ("one at a time; the next
  end of turn offers again"). **Das nächste Zugende ist ein ANDERER Moment derselben Fähigkeit,
  kein zweiter Versuch für diesen** — dieselbe Klasse wie `resolve_scouts()`' nie gebauter
  Menschenpfad: ein Kommentar, der ein Verhalten zusagt, das kein Code einlöst.
- **`game/per_unit_offer.py` ist die 32. Extraktion**, am zweiten UND dritten Konsumenten:
  `offer_each()` bietet EINEM Trupp an und hängt die Fortsetzung an BEIDE Optionen, also auch an
  die Absage.
  - **Warum verkettet und nicht alles auf einmal.** `DecisionManager` ist selbst eine Queue, ein
    `request()` je Einheit wäre also kürzer — und für Ride the Wind falsch: dessen Rückzug ist
    nach Schlachtgröße GEDECKELT und sein Prompt DRUCKT den Reststand. Vorab gebaut läsen alle
    dieselbe veraltete Zahl, und die Angebote jenseits des Deckels täten beim Annehmen nichts
    (Fehlerklasse 5). Verkettet wird die Eignung vor JEDEM Prompt neu gefragt, also stimmt der
    Zähler und der Deckel hält. **Gemessen:** vorher 1 Prompt und `remaining()` konnte sich nie
    bewegen; jetzt "2 of 2 left" → "1 of 2 left", dritte Einheit gar nicht mehr gefragt.
  - Der Reset des Zählers bleibt in `offer_at_end_of_turn()`, weil die Kette in `offer_each()`
    zurückkehrt und nie in die Methode — sonst schenkte eine Antwort mitten in der Kette eine
    frische Erlaubnis.
  - **Ein `auto_players`-Owner wird jetzt aus den KANDIDATEN gefiltert statt den Sweep zu beenden.**
    Die alte Form gab beim ersten KI-Trupp `return False`, ein menschlicher weiter hinten in der
    Sortierung bekam also gar kein Angebot. Was die KI TUT, ist unverändert: sie bleibt stehen.
- **Warum keine der drei Suiten es sah:** jede stellte GENAU EINE berechtigte Einheit. Die
  Prüfung ist deshalb jetzt die ZAHL über eine Zwei-Einheiten-Armee, durch die echte
  DecisionManager-Queue gedrainiert.
- **Getestet:** `test_tau_kroot_and_vespid.py` 140 → **146/146**, `test_aeldari_detachment_rules.py`
  380 → **385/385** (der Deckel-Fall mit drei Einheiten), `test_baharroth.py` 66 → **70/70**.
  Neu `ab_per_unit_offer.py` (**9 A/B-Sonden, alle beißend**) — je Controller die alte Schleife
  zurück, plus die Kette selbst ohne Fortsetzung gegen alle drei Suiten.
  **Ein Befund über den TEST:** zwei Sonden ließen `test_aeldari_detachment_rules.py` ABSTÜRZEN
  statt rot zu werden (Indizieren in eine Prompt-Liste, die in der Vor-Fix-Welt einen Eintrag
  hat) — die Prüfung polstert jetzt.
- **Im ECHTEN Spiel belegt** (`verify_airborne_agility_offers.py`, `runpy` auf `selfplay.py`s echte
  `main()`-Schleife, mit `tau_recon` — der einzigen ausgelieferten Liste mit ZWEI
  Vespid-Einheiten, also der gemeldeten Armeeform): der LIVE von `main()` gebaute Controller meldet
  **2 berechtigte Einheiten und 2 Prompts**; `--neutralize` (die alte Schleife) meldet
  **2 berechtigte und 1 Prompt** — die Meldung wörtlich.
  **Drei gestellte Tatsachen, jede mit Grund benannt:** die Position (die Ecke wird aus dem
  Standort des Gegners ABGELEITET — eine feste setzte sie beim ersten Lauf in Player 2s eigene
  Aufstellungskante), das Zugende, und ein FRISCHER `DecisionManager` für die Messung, weil die
  Kette eine ANTWORT braucht und die laufende Partie fast immer einen eigenen Prompt vorne in der
  Queue hat (gemessen: hier auch) — den auf Spielerkosten zu beantworten hätte die gemessene
  Partie verändert. Nur der Briefkasten ist getauscht.

### Defend Stronghold: die Endrunden-Karten konnten nie ausgezahlt werden

**Gemeldet:** *"defend stronghold wurde mir nicht zugerechnet, obwohl ich meine homeobjective die
ganze zeit hatte. lag es an objective secured?"*

- **An "Secured" (14.03) lag es NICHT** — `_defend_stronghold()` liest `Objective.controlled_by`,
  also 14.02s gewöhnliche Kontrolle; `secured_by` kann sie nur HALTEN, nie verhindern, und wird
  ohnehin allein von Marker Beacon gesetzt.
- **Der gefundene Fehler ist eine REIHENFOLGE in `main.py`.** Drei der siebzehn Karten werten an
  genau einem Moment — "am Ende des gegnerischen Zuges in der letzten Schlachtrunde" (Beacon,
  Burden of Trust, Defend Stronghold). Nimmt der Kartenspieler den ERSTEN Zug der Runde, IST das
  das letzte Zugende der Schlacht, und `advance_turn_phase()` rief `_check_battle_end()` in
  DEMSELBEN Durchlauf, in dem `begin_end_of_turn()` den Wertungs-PROMPT geöffnet hatte. Das
  kostete die Karte doppelt: `BattleEndOverlay.show()` FRIERT die angezeigten Zahlen ein (die VP
  fehlten also), und `_front_notice()` stellt dieses Overlay vor die Entscheidungsbox, die
  `main.py` nur zeichnet, solange `_front_notice()` None ist — der Prompt dahinter war damit auch
  nicht mehr beantwortbar.
- **Reproduziert:** Karte vollständig für 5 VP, Prompt offen, eingefrorener Endstand **0**.
- **Der Fix ist ein Tor plus ein Wiedervorlage-Punkt** (Fehlerklasse 14): `_check_battle_end()`
  hält an, solange `decision_manager.is_pending`, und wird zusätzlich EINMAL PRO FRAME gerufen,
  außerhalb der Event-Kette (Fehlerklasse 15) — also erscheint das Ergebnis den Frame nach der
  Antwort. `decision_manager` statt des Deck-eigenen Flags, weil das EINE Bedingung ist statt
  zweier, die sich widersprechen können; und alles andere, was an dieser Naht noch offen steht
  (Starflare sitzt dort), hat denselben Anspruch, vor dem Schlussstand beantwortet zu werden.
- **Die Gegenrichtung ist mitgeprüft**, sonst tauscht der Fix ein stilles Versagen gegen ein
  anderes: eine Schlacht ohne offene Frage endet unverändert im selben Aufruf.
- **Getestet:** neu `test_final_round_scoring.py` (**22/22**, vier Abschnitte) — **zu diesem
  Zusammenspiel gab es GAR KEINEN Test**: `test_secondary_missions.py` besitzt die KARTEN und
  fasst `main.py`s Reihenfolge nie an, und kein Smoke erreicht Runde 5. Die Kartenmenge ist eine
  MENGENDIFFERENZ über die Karten-OBJEKTE, nicht über `ALL_CARDS` — Burden of Trust ist gebaut und
  bewusst nicht im Stapel, eine Prüfung am Deck hätte also zwei von drei abgedeckt.
  **BENANNTE GRENZE:** Abschnitt 2 fährt `main.py`s Tor in der FORM nach, nicht dessen eigene
  Closure (`_check_battle_end()` lebt in `main()`, das keine Suite fährt) — die Verdrahtung hält
  Abschnitt 4 per AST fest, weil der Name auch in seiner eigenen `def`-Zeile und in einem Kommentar
  steht und ein Zähler auf ERWÄHNUNGEN genau die Schwäche ist, an der dieses Repo schon zweimal
  hing. **Keine Laufzeit-Sonde:** das letzte Zugende liegt fünf Runden tief, und ein
  MockAgent-Lauf schafft gemessen ~7 Phasenwechsel je 3000 Frames gegen die ~50 einer Schlacht.
- **OFFEN und beim User erfragt: die RUNDENBANDE der Karte.** Sie trägt neben dem
  Endrunden-Zeitpunkt ein `min_battle_round=2`, das unter diesem Zeitpunkt **niemals greifen
  kann**. Eine gedruckte Karte trägt keine Bande, die nie gilt — es ist also entweder die Bande
  zu viel oder der Zeitpunkt falsch, und im zweiten Fall wertet die Karte am Ende JEDES
  gegnerischen Zuges ab Runde 2, was genau die Beobachtung des Users erklärt (Home Objective die
  ganze Zeit gehalten, in den Runden 2-4 nichts bekommen). Nicht geraten, sondern der WORTLAUT
  erfragt (Fehlerklasse 13).
  - **Drei Messungen, die den offenen Punkt schärfen** (Nachtrag, nachdem der User sagte "dann war
    es aber ein anzeige Fehler, mein home objective war die ganze Zeit in meiner Farbe"):
    1. **Das BRETT hat nicht gelogen.** `renderer.draw_objectives()` färbt aus
       `objective.controlled_by` — GENAU dem Feld, das `_defend_stronghold()` liest. Farbe und
       Karte können per Konstruktion nicht auseinanderlaufen; "die ganze Zeit meine Farbe" heißt
       also, die Bedingung war die ganze Zeit erfüllt.
    2. **Die KARTE widerspricht sich auf dem Schirm.** `info_rows()` zeigt für sie
       `WHEN end of enemy turn, round 5` UND `FROM battle round 2` übereinander, und ihr
       `text` öffnet mit beiden Klauseln in einem Satz. Beacon, das denselben Zeitpunkt trägt,
       zeigt nur die WHEN-Zeile. Das ist der ANZEIGE-Fehler, den der User meint — kein
       Rendering-Fehler, sondern der sichtbar gewordene Datenwiderspruch.
    3. **Sie ist die EINZIGE der 18 Karten mit einer Rundenbande** überhaupt, und die ist inert.
    Die FROM-Zeile wird deshalb NICHT vorsorglich unterdrückt: das wäre kosmetisch und löschte
    genau das Signal, an dem der Widerspruch überhaupt aufgefallen ist.

## Der Avatar-Charge und der Home-Objective-Klumpen (2026-09-08)

**Gemeldet:** *"der große necron warrior squad hat den avatar of khaine gecharged. das sollte er
lieber nicht machen."* und *"die necrons kommen immer nicht so richtig von ihrem home objective
weg. sowohl necron warriors als auch immortals klumpen auf dem home objective und können sich von
da aus keine guten schusspositionen erarbeiten."*

**DIE ZWEI SIND DIESELBE GESCHICHTE**, und das ist der Befund, der die Arbeit zusammenhält: der
Blob war nach dem Charge zwei seiner fünf Runden im Nahkampf des Avatars festgenagelt. Gemessen an
`logs/game_20260908_204854.log`s eigenen `[move detail]`-Zeilen (Zentroide je Zug): Necron
Warriors T1 (32,4) → T2 (33,6) → nie wieder, Immortals 1 (29,9) → nie wieder, Immortals 2
(13,13) → nie wieder. **43 Modelle, zwei Zoll Boden in fünf Runden**, während jede andere Einheit
der Armee vorrückte.

### Der Charge: die taktische Schicht bekommt GAR KEINE Bewertung

- **Reproduziert an den echten Datenblättern:** der Charge auf den Avatar entfernt **7.5
  pts/Runde und 0.0 Modelle** (3 % einer Ein-Modell-Einheit), der Gegenschwung des Avatars nimmt
  **89.1 pts/Runde** — ein 12:1-Verlust. Das Log bestätigt es: **2 von 21 Modellen** kamen in
  Engagement Range, der Kampf machte **0 Wunden**.
- **Die Ursache ist eine Beobachtungslücke (Fehlerklasse 1+2), keine Modellschwäche.**
  `observation.squad_summary()` trägt ÜBERHAUPT KEINE Bewertung — Name, Modelle, Wunden, OC. Die
  `[threat]`-Zeile mit „by charging: Avatar 10.0 pts/turn (0.0 models, trading down)" geht
  ausschließlich an den PLANNER. **Das Log ist das A/B:** derselbe Spielstand, dieselbe
  Modellfamilie — der Planner, der die Zahlen bekommt, hat den Charge dreimal in Folge
  abgelehnt und wörtlich begründet („Charging the Avatar trades down badly (345 vs 250 pts)");
  die taktische Schicht, die keine bekommt, hat ihn gemacht.
- **`_charge_trade_note()` ist die Antwort, und sie steht in der Option — nicht als zweite
  Sperre.** Genau die Form, die dieselbe Funktion für die ODDS schon hat („it belongs in the
  option's own text"). Gelesen an zwei Stellen: der Deklaration und der Zielwahl.
- **EINE ZWEITE SPERRE WURDE GEMESSEN UND VERWORFEN, und das ist die tragende Entscheidung.**
  Über die zwei KI-Armeen gegen jede ausgelieferte Gegnerliste (**2070 Paarungen**) liegt der
  gemeldete Fall bei gain/loss 0.08, in den schlechtesten 1.7 % — aber die Population, von der
  er getrennt werden müsste, ist STETIG: unter den Einheiten, die die bestehende
  Shooting-Specialist-Sperre nicht ohnehin stoppt, läuft der entfernte Anteil 0.01, 0.02, 0.03
  (der gemeldete Fall), 0.04, 0.05, 0.06, 0.07, 0.08 **ohne jede Lücke**, und die
  Chaff-Charges, die eine Geschützlinie binden, liegen im selben Band wie die aussichtslosen.
  Eine Schwelle dort läge INNERHALB einer Überlappung — genau das, wofür
  `_shooting_specialist_charge_block()` eine Pro-Ziel-Ratio verworfen hat. Withholding ist die
  richtige Antwort für eine Option, die NIE genommen werden soll; diese soll manchmal.
- **Die bestehende Sperre ist unverändert und schweigt zu Recht**: Necron Warriors sind 1.1x,
  unter der 1.4-Schwelle. Sie war das falsche Werkzeug, nicht ein kaputtes.

### Der Klumpen: eine Bedrohung setzt die LATTE, sie schaltet den Pass nicht ab

- **`_uncontested_objectives()` ist zu `_held_objectives()` geworden** und liefert
  `(objective, threat_oc)` für JEDES kontrollierte Objective. Vorher nahm ein Gegner irgendwo
  innerhalb `GARRISON_THREAT_RANGE_IN` das Objective KOMPLETT aus dem Over-Garrison-Pass — im
  gemeldeten Spiel stand der Avatar ab Runde 2 etwa 12" von P2 Home, also durfte beliebig viel
  dort parken.
- **Regel 14.02 sagt selbst, wie groß eine Garnison sein muss:** Kontrolle ist die höhere
  OC-Summe, die Latte ist also die OC des Gegners und nicht seine Anwesenheit. Am gemeldeten
  Brett gemessen: **Avatar OC 5, Immortals OC 21, Necron Warriors OC 41** — die Immortals halten
  es allein, die 41 waren restlos überflüssig.
- **`_garrison_surplus()` ist die EINE Definition** von „wer wird gebraucht, wer ist übrig",
  gelesen vom Bericht an den Planner UND von der Korrektur. Die zwei hatten dieselben sechs
  Zeilen doppelt — die Form, die dieses Repo laufend konsolidiert, und sie wäre in dem Moment
  gedriftet, in dem eine der beiden Seiten von Bedrohungen erfahren hätte. **Damit fällt
  `_garrison_fitness` von drei Lesern auf zwei** (siehe die Extraktionsliste in Teil 1).
- **Der unbedrohte Fall ist per Konstruktion unverändert:** `threat_oc` ist dann 0, die OC des
  ersten Keepers übertrifft das, also bleibt genau eine Einheit stehen. Das `keepers and`-Gate
  ist, was das wahr macht statt fast wahr — ohne es hielte eine battle-shocked Einheit (OC 0,
  Regel 01.07) die Schleife am Laufen und niemand würde befreit.

### Der 0-Zoll-Freeze, und was er WIRKLICH war

- **Gemessen am kompletten gemeldeten Brett (alle 74 Modelle, wo das Log sie lässt):** der Blob,
  auf `(34,8)` befohlen — 1.97" vom Zentroid und INNERHALB der eigenen Formation —, bewegt sich
  **0.00"**; derselbe Blob auf demselben Brett auf Punkte außerhalb seiner Formation befohlen
  bewegt sich **2.50"** und **4.72"**. Nichts war blockiert: die Modelle auf der anderen Seite des
  Punktes müssten rückwärts in ihre eigenen Kameraden laufen, also kam jede Sprosse von
  `_advance_toward()`s Leiter mit nichts zurück.
  - **KORREKTUR einer eigenen Zwischenmessung:** eine frühere Zahl von 7.24" stammte von einem
    Brett, dem die Canoptek Wraiths fehlten — die stehen direkt nördlich des Blobs und kosten
    ihn den Weg. Die Zahlen oben sind die vom vollständigen Brett.
- **Der gemeldete Befehl war aber `hold`, und die Einheit hat ihn korrekt ausgeführt.** Der
  Widerspruch lag im PLAN (Rolle „hold" neben einem Fließtext, der eine Umpositionierung
  beschreibt) — dieselbe Falle wie Fehlerklasse 4, nur andersherum: hier wurde das FELD befolgt,
  und das ist die richtige Hälfte. Befreit wird die Einheit vom Garnisons-Pass, der eine Regel
  hat, die sagt, dass sie weg muss.
- **Der Wächter im Validator gilt deshalb NUR einer AKTIVEN Rolle**: ein Punkt in der eigenen
  Formation ist dort ein No-op, der die echten Optionen verdrängt (eine benannte Position
  unterdrückt Advance und Move-to-Target). Bei `hold`/`screen`/`stage` heißt derselbe Punkt
  „bleib stehen", was ein echter Befehl ist — die erste, breitere Fassung nahm prompt dem KEEPER
  seine eigene Garnisons-Koordinate weg, und `test_over_garrison.py` hat das sofort gemeldet.
- **`geometry.convex_hull()` / `point_inside_hull()` (34. Extraktion)**, am zweiten Konsumenten:
  `game/renderer.py` hatte den Hull privat (Objective-Umrisse) und kann von `ai/` nicht
  importiert werden (pygame, Renderpfad). Der Renderer RE-EXPORTIERT ihn unter dem alten privaten
  Namen, also ist jeder Pixel-Test der Objective-Umrisse per Konstruktion unverändert.

### Was NICHT angefasst wurde, und warum

Die dritte Ursache des Klumpens ist die dokumentierte Bewegungsgrenze großer Trupps
(`measure_crowded_movement.py`: 15+ Modelle realisieren ~20 % ihres erreichbaren Zuges) — ein
echter 16"-Vormarsch des Blobs kommt auf 54 %. Auf User-Entscheidung bewusst ausgelassen; CLAUDE.md
führt dort vier gemessene und wieder ausgebaute „Verbesserungen".

### Getestet

Neu `test_report_20260908.py` (**48/48**, acht Abschnitte) plus `ab_report_20260908.py`
(**13 A/B-Sonden, alle beißend, keine stürzt ab**). `test_over_garrison.py` 71 → **77/77**
(Abschnitt 6 stellt jetzt die NEUE Regel fest und misst die Latte in beide Richtungen — eine
größere Bedrohung hält eine zweite Einheit dort), `test_home_garrison.py` **86/86**.
- **Zwei Befunde über den TEST, beide von den Sonden:** der `_garrison_fitness`-Zähler war
  `src.count(...) - 1` und blieb durch genau diese Änderung grün, weil eine Erwähnung im
  DOCSTRING den weggefallenen Leser ersetzte (die „ein Wächter matcht seine eigene Erklärung"-
  Falle, fünfte Instanz) — er zählt jetzt per AST echte AUFRUFE; und drei Sonden ließen ihre
  Suite mit `KeyError` ABSTÜRZEN statt sie rot zu machen (Nachschlagen mit `[...]` auf ein Dict,
  das in der Vor-Fix-Welt den Schlüssel nicht hat) — **achtzehnte Instanz** derselben Lehre,
  jetzt `.get()`.
- Volle Regression **196 Suiten, ~17339 Prüfungen, 195 grün / 0 rot / 1 bekannt**,
  `run_tests.py --smoke` komplett grün (alle neun schweren Skripte).

### Im ECHTEN Spiel belegt

`verify_charge_trade_and_garrison.py` fährt `selfplay.py`s echte `main()`-Schleife mit der
gemeldeten Paarung (Aeldari gegen Necrons):

| | gefixt | `--neutralize` |
|---|---|---|
| Charge-Optionen mit dem Handel | **4 von 4** | **0 von 6** |
| Garnison: Einheiten befreit / behalten | **1 / 1** (threat OC 5) | **0 / 2** |

Die Optionstexte zeigen die Unterscheidung, um die es geht:
`it would remove about 6.7 of its models (101 pts/turn) ... 11 pts/turn back` gegen
`about 0.1 of its models (12 pts/turn) ... 78 pts/turn back`. `--neutralize` liefert dafür
`charge 1 Guardian Defenders 1 ...` und `charge 1 Wraithguard 1` — zwei nackte Namen.
**GESTELLT wird je eine Tatsache pro Hälfte, beide im Modulkopf benannt:** dass die KI überhaupt
in ihrer Charge-Phase neben etwas steht, und die Plan-FORM (MockAgents `plan_turn()` gibt jeder
Einheit „advance" ohne Koordinate, also findet `_planned_garrisons()` nie eine Garnison und der
Pass kann von selbst nicht feuern). Die Bedrohung wird ebenfalls gestellt — ohne sie ist das
Objective unbedroht, beide Welten befreien den Überschuss, und die Sonde misst nichts.

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
  - **Und genau diese Stelle war danach eine ENDLOSSCHLEIFE** (User: "im letzten spiel wurde ich
    immer wieder gefragt, ob ich den advance rerollen will mit den destroyern. es war eine
    schleife bis ich ihn gererollt habe"). Kein Fehler in einer der zwei Fähigkeiten, sondern
    eine Eigenschaft der KETTE: der Zweig bietet zuerst an und macht dann
    `if decision_manager.is_pending: continue`, hält den Wurf also bewusst UNBESTÄTIGT, solange
    ein Prompt offen ist — er MUSS das, weil `acknowledge()` `pending_values` leert und
    `reroll_die()` danach nichts mehr wirft. "Keep it" hinterließ damit exakt das Brett, das die
    Frage erzeugt hat, und der nächste Klick fragte erneut. **Nur Rerollen beendete es**, weil das
    die einzige Antwort ist, die den gelesenen Zustand ändert (`already_rerolled`).
  - **Das Gedächtnis gehört dem WURF, nicht der Fähigkeit** → `DiceManager.claim_reroll_offer(source)`,
    von `roll()` geleert wie `already_rerolled` daneben. **EIN Aufruf, kein Fragen/Merken-Paar:**
    ein Angebot, das gemacht und nicht gebucht wird, IST der Fehler, also gibt es keine Möglichkeit,
    die Hälfte davon zu tun.
  - **Nach QUELLE gekeyt, nicht ein geteiltes Flag** — zwei Fähigkeiten dürfen je einmal aus ihrem
    eigenen gedruckten Grund fragen. **Gemessen: keine Einheit kann beide halten** (Aeldari-
    Datenblatt gegen Necron-Stratagem-Grant), also kann eine A/B-Sonde gegen die zwei
    Fähigkeits-Suiten ein Set nicht von einem Flag unterscheiden — die Zusicherung steht deshalb
    KONSTRUIERT in der Suite des `DiceManager` selbst.
  - **Die andere Richtung ist die gefährlichere und hat eine eigene Sonde:** wird das Gedächtnis
    nicht von `roll()` geleert, wird der ZWEITE Advance der Schlacht nie mehr angeboten — ein
    stiller Verlust ist schlimmer als die Schleife.
  - **Getestet:** `test_hazard_lock_and_dice.py` 43 → **50/50** (der `DiceManager` selbst),
    `test_autarchs_and_maugan_ra.py` 129 → **137/137**, `test_awakened_dynasty.py` 89 → **95/95**;
    neu `ab_advance_reroll_loop.py` (**5 A/B-Sonden, alle beißend**, über alle DREI Suiten — ein Fix,
    der nur eine der zwei Fähigkeiten erreicht, ist genau die Drift, die dieses Repo konsolidiert).
  - **Im ECHTEN Spiel belegt** (`verify_advance_reroll_loop.py`, `runpy` auf `selfplay.py`s echte
    `main()`-Schleife, mit ECHTEN Mausklicks in die ECHTE Event-Kette): **1 Prompt, abgelehnt, Würfel
    bestätigt** gegen `--neutralize`s **130 Prompts und ein Würfel, der nie verschwindet**. Der
    Grant und der Advance-Wurf werden gestellt (ein MockAgent-Lauf erreicht "gekauft UND advanced
    UND der Mensch klickt" nicht), alles danach ist echt.
    **Harness-Falle dabei, und sie kostete einen Fehllauf:** `movement_controller.selected_squad`
    ist das Feld, aus dem der Zweig die Einheit liest, und die parallel laufende KI ruft
    `select(None)` zwischen den Frames — die Sonde maß dadurch einen Klick ohne Einheit und meldete
    wahrheitsgetreu aussehende Nullen. Sie hält die Auswahl jetzt. **Und ein zweiter Fehllauf war
    die dokumentierte `__pycache__`-Rennbedingung** (Fehlerklasse 19): direkt nach einem
    Sondenlauf, der den Cache im Sekundentakt loescht, meldete derselbe Aufruf 0 statt 130 —
    wiederholt nach `rm -rf __pycache__` sofort korrekt.
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
und `enhancements=` sind deshalb LEER, mit dem Grund darüber. **Die damals einzige
Aeldari-Liste fieldete weiter Seer Council** (User-Entscheidung): die sieben waren deklariert
und einzeln per `selfplay.py` verifiziert, aber nichts am Default-Spiel änderte sich — dieselbe
Behandlung wie die 27 Datenblätter, die in keiner Demo-Armee stehen. **Seit den zwei Listen
vom 2026-09-08 sind VIER der sieben wirklich gefieldet** — Warhost, Armoured Warhost, Guardian
Battlehost und (schon länger) Path of the Outcast; ungefieldet bleiben Aspect Host, Windrider
Host und Spirit Conclave. Der Default (`config.PLAYER1_ARMY`) ist unverändert `aeldari`.

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
| 25 | `game/whole_unit_drag.py` | Block-Deployment und Block-Movement waren EINE Einstellung mit zwei Flags (siehe die Toggle-Leiste) |

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

**Kein KI-Pfad** (User-Vorgabe), für alle 36 als Negativraum geprüft. **Keine Demo-Armee änderte
sich** — die damals einzige Aeldari-Liste fieldete weiter Seer Council. **Seit den zwei Listen
vom 2026-09-08 sind Warhost, Armoured Warhost und Guardian Battlehost gefieldet**, ihre
Stratagems also nicht mehr dormant: von den neunzehn PANEL-Knöpfen der Fraktion sind **acht statt
drei** im echten Spiel erreichbar. **Die Reichweite ist dabei sehr ungleich gewachsen** — Warhost
allein brachte EINEN Knopf, weil fast alles daran reaktiv ist und ein reaktives Stratagem gar nicht
erst auf die Registry kommt; das Paar darunter hat sie verdoppelt. Genau deshalb leitet der Wächter
die Zahl aus den deklarierten Detachments ab, statt sie hinzuschreiben.

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

## Werden die Necron-Stratagems überhaupt ANGEBOTEN? (Prüfung, 2026-09-08)

**Auftrag:** dieselbe Prüfung wie für die Aeldari und die T'au, für die Necrons —
*„werden sie dem Spieler zum korrekten Zeitpunkt angeboten, und wirken sie dann
auch wirklich?"*, ausdrücklich **inklusive Enhancements**.

**Fünf echte Fehler**, und die zwei schwersten sind KEINE Angebots-Fehler,
sondern Wirkungs-Fehler: eine Regel, die ihre Wunden nie zuteilt, und eine, die
dem Menschen die Platzierung wegnimmt. Alle fünf standen an der Quelle fest,
BEVOR eine Zeile Test existierte.

### Der Zuschnitt war anders, und das ist der Inhalt

Die zwei vorherigen Audits fanden dieselbe Lücke (kein Test hat je das ECHTE
Panel gezeichnet). Hier gilt sie auch — aber sie ist nicht mehr die Hauptfläche:

- **Die drei Panel-Knöpfe sind die am schlechtesten bewachten des Spiels.**
  Hungry Void / Sudden Storm / Conquering Tyrant gehen NICHT über
  `proactive_stratagems`: keiner definiert `panel_label()`, sie kommen als
  eigene Keyword-Argumente durch `draw() → _draw_dispatch() →
  _draw_movement_ui()`. **§14 deckt also keinen von ihnen.** Der einzige Beleg
  war `test_awakened_dynasty.py:527`, ein blanker Teilstring
  `"hungry_void_controller=hungry_void_controller" in main_src` — er hält unter
  `if False:`, hält, wenn das Panel nichts zeichnet, und hält in der falschen
  Phase. **Gemessen sind sie trotzdem RICHTIG**; nur bewiesen war nichts.
- **Die KI-WEICHE ist hier die eigentliche Fläche, und sie existierte bei den
  anderen zwei gar nicht.** Necrons sind die Default-Armee der KI, jede
  Fähigkeit hat zwei Wege (`auto_players` / Prompt), und genau dort wurde in
  diesem Repo schon einmal ein Fehler AUSGELIEFERT. Drei der fünf Funde liegen
  hier.
- **Und die Funde sind NICHT dormant.** `armies/necrons.json` fieldet Awakened
  Dynasty, alle sechs Protokolle sind im echten Spiel live — anders als die
  30 von 42 Aeldari-Controllern, die kein Roster erreicht.

**Die Wächter waren grün und WAREN NICHT die Lücke** (113 Prüfungen, 0 rot).
Alle fünf Funde liegen in ihren blinden Winkeln, und der Grund ist strukturell:
§6/§10/§11/§12 starten alle bei „wen FRAGT `main.py`" — ein Controller, den
`main.py` gar nichts fragt, ist ihnen unsichtbar.

### Die fünf Fehler

| # | Fehler | Wirkung |
|---|---|---|
| 1 | **VIER** Controller öffnen eine `MortalWoundAllocationSession` und **keiner** kann sie leeren | gegen jedes Mehr-Modell-Ziel landen **null** Wunden — das Log meldet sie trotzdem |
| 2 | Dieselben drei Aeldari-Module übergeben das GameLog-**Objekt** statt eines Callables | `TypeError: 'GameLog' object is not callable`, sobald eine Wunde auf einem Ein-Modell-Ziel landet |
| 3 | Die **zweite** reanimierende Einheit wird dem Menschen weggeplatziert | Platzierung öffnet zweimal für die ERSTE; keine unterscheidende Logzeile |
| 4 | Vengeful Stars: die KI läuft alle Paare, der Mensch bekommt ein nacktes Ja/Nein auf Kandidat[0] | restliche Kandidaten still verworfen, keine Brett-Tags |
| 5 | Prompt-Hygiene: ein Decline, den die Regel nicht druckt; Optionen ohne Brett-Tag | Living Lightning, Technomancer |

**F1 — die vier, und sie sind ZWEI Fraktionen.** 21 Module in `game/` bauen
eine Session, **16** leeren sie, `damage_resolution.py` ist die
Definitionsstelle — bleiben `wraith_form.py` (Necron), `drakolithe.py`,
`harvester_of_souls.py`, `monofilament_snare.py` (Aeldari). Es gibt **keinen**
geteilten Sweep. Reproduziert, Canoptek Wraiths über zehn Boyz: `remaining=3,
inflicted=0, pending_choice=10 Kandidaten`, Log sagt „3 mortal wound(s)", **0
gelandet**. Gegen ein EIN-Modell-Ziel löste es auf — deshalb hat es überlebt.
`wraith_form.is_busy` liest den WÜRFEL (`_pending`), der eine Zeile VOR dem
Session-Bau genullt wird, ist also die ganze Lebensdauer der Session False.
Das direkte Geschwister, 8 Zeilen später am SELBEN Haken gebaut, hat alle drei
Methoden (`enh_internal_grenade_racks.py:186-227`).

**F2 ist der Spiegel von F1 und war ohne die Necron-Arbeit unsichtbar.**
Die Session ruft `self.log(msg)` als CALLABLE; 18 von 21 Bauplätzen übergeben
eins, genau drei das Objekt. **Mehr-Modell-Ziel parkt für immer, Ein-Modell-Ziel
kracht** — die zwei Ausfallarten haben einander verdeckt. `monofilament_snare`
hatte den richtigen Helfer schon und benutzte ihn nicht.

**F3 — der stille Mensch→Auto-Rückfall.** `return_placement.py`s dritter
Disjunkt `not can_start_setup(squad)` heißt „SOMEBODY is already placing" und
war mit „this is the AI" zusammengefaltet. `reanimation_protocols._apply_and_advance`
rollte den nächsten Würfel im selben Call-Stack über die offene Platzierung.
Reproduziert (zwei beschädigte menschliche Einheiten, D3 auf 3):
`placement opened for: ['1 Unit0 1', '1 Unit0 1']`.

**F4** ist wörtlich die Form, die `resurrection_orb.py:148-171` bereits behoben
hat — dessen Kommentar zitiert den User-Bericht, aus dem die Klasse stammt.

### Die Fixes

- **F2 zuerst** (3 Zeilen), weil kein Verhaltenstest für die drei eine Wunde
  landen lassen kann, solange sie kracht.
- **F1: die zwei SINGULÄREN Halter** kopieren das Geschwister (es gibt bereits
  16 solche Kopien; ein Mixin für zwei von 21 wäre eine dritte Schreibweise —
  Fehlerklasse 10s dritte Form). **Die zwei LISTEN-Halter** sind der ZWEITE
  Konsument einer Form ohne jede Kopie → neu **`game/mortal_wound_sessions.py`**
  (32. Extraktion). Dort ist die REIHENFOLGE Teil der Antwort: `pending_choice()`
  liefert die erste geparkte Session in Einfüge-Reihenfolge und `choose()`
  routet in dieselbe, sonst teilen zwei Replays einer Schlacht dieselben Wunden
  verschieden zu.
  Dazu je fünf `main.py`-Kanten (AI-Pause, Phasen-Tor mit BEIDEN Termen,
  Klick-Zweig, Highlight, Würfel-Ack). Die FNP-Etappe muss VOR `if self._pending
  is None: return False` stehen — sechsmal im Aeldari-Audit bezahlt.
- **F3: der Rückfall wird an der Engstelle GETEILT.** Die EIGENE offene
  Platzierung → Warteliste, von `confirm()` UND `_on_cancel()` abgearbeitet.
  Eine FREMDE (Ingress, Disembark) → Engine antwortet weiter, **aber sie sagt
  es** — sie zu queuen wäre ein Deadlock, weil niemand hier das Resume einer
  fremden Platzierung besitzt. Der `auto_players`-Disjunkt bleibt ERSTER und
  unangetastet (die stehende „THE AI IS UNCHANGED"-Zusage). Dazu hält
  `_apply_and_advance()` die Warteschlange, mit einem `_applying`-LATCH gegen
  die Re-Entrancy: auf dem KI-Pfad ruft `place()` sein `on_done` SYNCHRON,
  ohne den Latch rückt die Queue zweimal vor (Fehlerklasse 9b).
- **F4** nach dem Muster des Orbs: EINE Liste, von beiden Zweigen gelesen; eine
  getaggte Option je gültigem Paar; das Label nennt BEIDE Einheiten (zwei
  Optionen „Use Protocol of the Vengeful Stars" sind ununterscheidbar); der
  Regelname bleibt im PROMPT, weil `prompt_rule.py` ihn dort zurückliest.
- **F5**: Living Lightnings Decline gestrichen (gedruckt „select one enemy
  unit", mandatorisch — Typhus' Eater Plague daneben druckt „you can select"
  und BEHÄLT seinen, das ist die Gegenprobe); Technomancer-Optionen bekommen
  den dritten Tupel-Slot.

### ZWEI eigene tote Zweige, von den eigenen Sonden gefunden

Der erste Anlauf gab `is_busy` ein `or bool(self._waiting)` und `main.py` einen
zweiten Tor-Term. **Beide Sonden meldeten NO BITE**, und Nachmessen zeigte
warum: `place()` queut nur, solange `_pending` gesetzt ist, eine gequeute
Platzierung hat also IMMER eine offene vor sich — und eine offene ist
`setup_controller.state == PLACING`, worauf das Tor längst wartet. Beides
entfernt statt mit einer Sonde versehen, die nicht fallen kann; die Invariante
ist in `test_return_placement.py` §12 gepinnt.

### Der neue Wächter: `test_event_chain_wiring.py` §17/§17b

**Die Umkehrung von §6, eine Schicht weiter außen.** §6/§10/§11/§12 starten bei
`main.py`; §17 startet beim MODUL: jedes, das eine Session ÖFFNET, muss sie
leeren können. Per AST, und das ist keine Stilfrage — ein Teilstring-Sweep
trifft ~30 Module, davon neun nur in Kommentaren, und
`mortal_wound_abilities.py:244-262` nennt die Klasse in einem Kommentar, der
**genau diesen Fehler erklärt** (Fehlerklasse 24 in Reinform).
Ausnahmeliste: **ein** Eintrag (`damage_resolution.py`) mit DREI
Lebendigkeitszeilen — es baut noch eine, es definiert die Klasse, und es leert
sie synchron per `while not …done`. **§17b**: das `log=`-Argument darf nicht das
GameLog-Objekt sein, als REFUSAL der einen falschen Form geschrieben statt als
Whitelist der richtigen. **113 → 136.**

### Die neue Suite: `test_necron_stratagem_ui.py` (100 Prüfungen)

Die fehlende Hälfte, Vorlage `test_tau_stratagem_ui.py`. Vier Dinge, die eine
kopierte Suite still nichts hätte messen lassen:

- **Hungry Voids fehlende Owner-Klausel ist AM PANEL messbar**, und das kann
  keine der zwei anderen Fraktionen: sein WHEN ist „Fight phase." ohne „Your",
  und `MovementController.can_select()` gibt im Fight bedingungslos True zurück
  (12.02/12.04) — die T'au mussten deshalb auf `can_use()` ausweichen. §2b
  rendert es im Fight des GEGNERS und verlangt den Knopf DORT.
- **§0 Liveness misst den DISPATCH-ZWEIG, nicht die Knopfzahl.** Gemessen: in
  Command, Charge und Fight zeichnet das Panel ohne Charge-/Fight-Controller
  gar keine Knöpfe, „labels > 0" wäre also schlicht falsch. Was jede
  Abwesenheitsprüfung wirklich braucht, ist, dass der Render
  `_draw_movement_ui()` erreicht hat.
- **Die Ledger-Klausel als NEGATIV** (Einheit als `fought`/`shot` markieren,
  rendern, Knopf muss WEG sein) — das ist die gedruckte TARGET-Zeile, und
  nichts sonst misst sie am Panel.
- **AST-Pins statt Index-Pin**, weil die drei per Keyword kommen: alle DREI
  Signaturen, beide Weiterreich-Hops per Keyword mit passendem Namen, das
  positionelle Präfix von `main.py`s Aufruf (ab Index 2 — die ersten zwei
  Locals heißen `screen`/`left_panel_rect`, wo die Parameter `surface`/`rect`
  heißen), **und die User-Entscheidung selbst**: keiner der drei steht auf der
  Registry, keiner definiert `panel_label()`. Eine spätere Migration macht
  diese Zeile absichtlich rot.

**Gemessener Nebenbefund:** das Panel lässt **„Protocol of the"** fallen — eine
größere Kürzung als Arro'kons führendes „The". `rules_text.stratagem_named()`
löst das über den Eindeutig-Suffix-Rückfall auf; beide Hälften sind gepinnt.

### Die Enhancements: ALLE VIER sind Daten, und das ist eine ROSTER-Tatsache

`enhancements.ENHANCEMENTS` hält **47** Specs über 14 T'au- und
Aeldari-Detachments und **null** Necron-Einträge. **User-Entscheidung: als
benannte Lücke pinnen, nicht verdrahten** — kein Roster kauft eins
(`armies/necrons.json`), sie wären also dormant by construction wie die 28
Aeldari und 7 T'au; erfundener Listeninhalt ist die Bewegung, die dieses Repo
nicht macht. Von BEIDEN Seiten gepinnt, damit die Lücke weder still schließt
noch still wächst.

**Und der Kommentar, der sie begründete, war VERALTET** — dieselbe Klasse wie
die Mont'ka-Rechtfertigung: `game/factions/necrons.py` behauptete
„Enhancements are not a system in this engine", was in dem Moment falsch wurde,
in dem `game/enhancements.py` entstand. Ersetzt durch den gemessenen Grund.

### Benannte Grenzen, gepinnt statt gefixt

- **`protocol_eternal_revenant` bleibt in `NOT_ROUTED`** — aber seine
  Begründung ist geschärft: „keine Überlebenden zum Kohärenz-Halten" ist ein
  Argument über KOHÄRENZ, nicht darüber, wer den Platz wählt, und eine
  Ein-Modell-Einheit hat gar keine Kohärenz-Schranke. Der ehrliche Grund ist,
  dass `enh_phoenix_gem` und `word_of_the_phoenix` dieselbe Form teilen: die
  drei bewegen sich zusammen oder gar nicht.
- **`MortalWoundAllocationSession.resume()` hat null Aufrufer**
  (`damage_resolution.py:658-664` / `main.py:2049`) — Aeldari, nicht
  reproduziert, dieselbe Klasse wie F1.
- **`resurrection_orb._use()` verbrennt den Orb bei abgebrochener Platzierung.**
- **`fought_squad_ids`/`shot_squad_ids` halten Squads, keine Ids** — lügender
  Name mit zwei Trägern, ~12 Module, außerhalb dieses Umfangs.
- **`plasmacyte` ist für beide Seiten unerreichbar** (steht schon oben).

### Getestet

Neu `test_necron_stratagem_ui.py` (**100**), `test_mortal_wound_drains.py`
(**49**, eine Datei für vier Abilities über zwei Fraktionen — es ist EIN Defekt
und EIN Fix, und eine Fraktions-Suite hätte immer nur ihre eigene Hälfte sehen
können; dieselbe Begründung wie `test_return_placement.py`).
`test_event_chain_wiring.py` 113 → **136**, `test_awakened_dynasty.py` 95 →
**111**, `test_return_placement.py` → **158**, `test_reanimation_protocols.py`
53 → **60**, `test_necron_abilities.py` 101 → **111**,
`test_necron_datasheets.py` 155 → **164**.

**36 A/B-Sonden über drei Dateien, ALLE beißend** — `ab_necron_mortal_wounds.py`
(16), `ab_necron_offer_windows.py` (10), `ab_necron_stratagem_ui.py` (10).
Volle Regression **192 Suiten, ~17055 Prüfungen, 191 grün / 0 rot / 1 bekannt**,
`run_tests.py --smoke` komplett grün.

**Fünf Befunde über den TEST, alle von den Sonden** (Fehlerklasse 24): der
Sonden-Treiber verglich GRÜNE statt ROTE Prüfungen und ließ damit eine Sonde
durchrutschen, die die Prüfzahl ÄNDERT (jetzt zählt er Rot); §17c suchte
`pending_damage_choice` in ganz `main.py`, wo der Klick-Zweig es ohnehin nennt
(jetzt der AST-Rumpf des Phasen-Tors); zwei Log-Sonden bissen nicht, weil die
Suite die Session SELBST baute statt die echten Bauplätze zu fahren; und eine
Sonde ließ die Suite mit einem SyntaxError sterben, weil der Anker nur drei von
fünf Kommentarzeilen traf.

### Im ECHTEN Spiel belegt

Alle drei Sonden fielden die **Necrons als PLAYER 1** — `config` liefert
`PLAYER2_ARMY = "necrons"` aus, und eine Frage über die Knöpfe des MENSCHEN
misst sonst die Armee der KI und meldet eine wahrheitsgetreu aussehende Null.

| Sonde | gefixt | `--neutralize` |
|---|---|---|
| `verify_necron_stratagem_buttons.py` | **DRAWN 3/3**, off-WHEN 0, und Hungry Void wirklich im Fight des GEGNERS | **0/3** |
| `verify_necron_wraith_form.py` | Brett zeigt die Wahl (2 Frames), **2 echte Klicks**, 3 Frames blockierend, aufgelöst bei Frame 703, **3 Wunden gelandet** | **0 gezeichnet, 0 Klicks, 1815 Frames blockierend, NIE aufgelöst, 0 Wunden** |
| `verify_return_placement.py` (erweitert auf ZWEI Einheiten) | beide bekommen ihre eigene Platzierung, **keine engine-gesetzt** | **`seated by the ENGINE for a human: 1 Immortals 1 + Plasmancer`**, nur eine geöffnet |

Die Wraith-Form-Sonde postet einen ECHTEN `MOUSEBUTTONDOWN` in `main()`s
eigenen Pump, an der Bildschirmposition eines Modells, das das Spiel selbst für
wählbar erklärt — hat die Kette keinen Zweig dafür, passiert nichts.
**Was gestellt wird, ist einzeln benannt:** die Necrons als Player 1, das
Detachment (per WRAPPER, weil `apply_to_config()` jede Einstellung neu
schreibt), die Bewegung bzw. der Confirm (selfplay beantwortet außerhalb des
Vorspiels keinen Mensch-Prompt), und Einheit plus Phase mit **teilerfremden
Perioden** — ein geteilter Modulus koppelt Einheit *i* für immer an Phase *i*%5.

**Zwei Zahlen sind bewusst schwach und stehen so da:** „0 Phasenwechsel danach"
ist ehrlich (ein Necron-Selbstspiel erreicht in einem vertretbaren Budget kaum
welche), deshalb ruht der Kein-Deadlock-Beleg auf „hörte auf zu blockieren und
die Schleife lief weiter", nicht auf einer Phasenzählung.

### Nebenbefund: die Parallelsitzung hat Sonden-Rückstand committet

Commit `412dc4a` enthält `game/protocol_hungry_void.py` mit
`if False: return False` an der Stelle des gedruckten TARGET-Ledgers — mein
A/B-Lauf hatte die Datei transient neutralisiert, und der `git add -A` der
parallelen Sitzung hat genau diesen Moment eingefangen. **Fehlerklasse 20 in
einer neuen Form:** die `-A`-Regel ist Absicht und bleibt, aber ein
Sondenlauf und ein Commit dürfen sich nicht überlappen. Nur diese eine Datei
ist betroffen (per `git grep` über HEAD geprüft); der Arbeitsstand hatte die
korrekte Fassung und stellt sie mit diesem Commit wieder her.

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
