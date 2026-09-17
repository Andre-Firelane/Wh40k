# CLAUDE.md

Projektkontext und Hinweise für Claude Code in diesem Repository.

**Diese Datei wird bei JEDER Anfrage vollständig mitgeladen** und ist damit der feste Sockel jedes
Kontexts; `/compact` kann sie nicht verkleinern. Sie hält deshalb nur, was JEDE Arbeit betrifft: die
Arbeitsweise (Teil 1), ein Verzeichnis des Stands (Teil 2) und die offenen Punkte (Teil 3). Der
Stand selbst — was gebaut ist, warum, und wie es belegt wurde — liegt in `docs/stand/*.md` und wird
nur bei Bedarf gelesen; die chronologische Sitzungshistorie liegt in `CLAUDE.history.md`.

**Warum:** bis 2026-09-17 stand der ganze Stand hier. Die Datei ist dreimal auf ~1 MB gewachsen,
zuletzt von 418 KB (06.09.) auf 1,19 MB (17.09.) — gemessen rund 2 Zeichen pro Token, also
~590.000 Tokens bei jeder Anfrage. Längere Aufgaben endeten in „prompt too long“, und `/compact`
konnte es nicht beheben.

**Pflege — hierher kommt nichts, was nur einen Teil des Spiels betrifft:**
- Neuer Stand zu einem Subsystem → VERDICHTET in den passenden Abschnitt der passenden
  `docs/stand/`-Datei (Verzeichnis in Teil 2). Ein neuer `##`-Abschnitt dort bekommt eine Zeile im
  Verzeichnis. Eine Meldung aus einer Partie geht in die jüngste `meldungen-*.md`, ein neues
  Extraktionsmodul nach `extraktionen.md`, ein neues Mess- oder Sondenskript nach `werkzeuge.md`.
- Die Sitzungserzählung (was gemeldet, gemessen, verworfen wurde) → `CLAUDE.history.md`.
- Hierher nur: eine neue Konvention oder Fehlerklasse (knapp, ohne Messbericht), eine neue
  Verzeichniszeile, ein offener Punkt.
- Eine `docs/stand/`-Datei bleibt unter 42.000 Zeichen (≈ 21.000 Tokens, in EINEM Read lesbar).
  Wird sie größer, wird sie an einem `###` geteilt (Muster: `## <Abschnitt> — Fortsetzung`) oder
  eine neue Datei angelegt.
- `docs/stand/`-Dateien NIE per `@pfad` importieren: ein Import lädt sie wieder bei jeder Anfrage.
- `test_claude_md_budget.py` hält all das fest (diese Datei ≤ 100 KB, jede `docs/stand/`-Datei
  unter der Grenze, Verzeichnis vollständig und ohne tote Zeilen, kein Import).

**Nachschlagen:** ein Verweis der Form `` `## Titel` `` — hier, in Code-Kommentaren, Tests oder
Memory — meint fast immer einen Abschnitt in `docs/stand/`: das Verzeichnis nennt die Datei, oder
`Grep "## Titel" docs/stand`. „See CLAUDE.md“ in einem Code-Kommentar heißt entsprechend: diese
Datei oder `docs/stand/`.

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
RICHTIG — sie ist gerade zu dieser Phase geworden (das mit Orks E3b stillgelegte
`grot_orderly.py` war der eine solche Leser).

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
→ **§6** (klickbar + gezeichnet), **§12** (KI-Pause). Gehört die Wahl der KI, beantwortet sie
sie aus DERSELBEN Liste (`damage_choice_controllers`, an `take_one_action()` gereicht) → **§28**;
ein neuer Eintrag in diesem Tupel ist damit für beide Seiten verdrahtet.
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

**Ein Stub prüft keinen Vertrag.** Drei Suiten fuhren `start_reactive_shooting()` gegen Stubs, die jede
`restrict_to`-Form schluckten — grün, während der echte Controller beim ersten echten Aufruf abstürzte
(siehe `## Regelengine — Schießen`). Wer einen Kollaborator stubbt, braucht mindestens EINEN Durchlauf
gegen den echten, und zwar durch den Trichter, aus dem die Fähigkeit wirklich gerufen wird.

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
   (`reachable_this_turn`), einen deterministischen Backstop — **und den PUNKT zum Auswählen.**
   Der Rückweg an den Planner war für zu weite Koordinaten der falsche dritte Baustein (siehe 27):
   seit 2026-09-09 trägt jeder Objective- und Feindeintrag außerhalb einer Bewegung
   `first_leg_this_turn` (den Punkt auf der Linie dorthin, plain und Advance), damit der Planner
   einen Wegpunkt WÄHLT statt ihn herzuleiten.
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
9. **Der Trichter ist nicht immer der, der so aussieht.** `_finish_hit_roll()` wurde vom
   Monster-Hunters-Zweig umgangen (seit Orks E3a entfallen), `_apply_feel_no_pain()` hat nur einen Aufrufer,
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
    Seither Dutzende weitere. Der KATALOG — welches Modul, am wievielten Konsumenten, und was an
    der jeweiligen Extraktion die leicht zu verfehlende Hälfte war — steht in
    `docs/stand/extraktionen.md`; neue Einträge gehören DORTHIN. Vor einer neuen Extraktion dort
    nach dem Begriff greppen: die Frage hat oft schon eine Antwort unter anderem Namen.
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
    **DRITTE Form, und die stillste: ein ZWEIARMIGER Zustands-Zweig, bei dem nur EIN Arm
    antwortet.** `action_panel.py`s `_draw_movement_ui()` teilt sich in `state == MOVING` und
    `else`, und die Agile-Manoeuvre-Knöpfe standen nur im `else` — also verschwanden sie in dem
    Moment, in dem der Spieler „Move" drückte, und Star Engines, dessen Trigger NUR mitten in
    einer Bewegung erfüllbar ist, wurde nie angeboten. Kein Zweig ist hier tot und keiner
    schluckt etwas; es fehlt schlicht eine Antwort im zweiten Arm, und die Symmetrie sieht kein
    Verhaltenstest — der Panel-Test rendert, was er stagt, und §8 stagte 400 Zeilen lang nur
    `SELECTED`. Der Wächter ist deshalb eine SYMMETRIE-Prüfung per AST
    (`test_event_chain_wiring.py` §23: derselbe Aufruf muss in `body` UND `orelse` stehen, und
    genau zweimal in der Datei). **Vor der nächsten Meldung dieser Familie also drei Fragen:
    schluckt ein Zweig (15), altert ein unerreichter (15s Kehrseite), oder antwortet ein
    zweiarmiger nur halb?**

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
    **DRITTE Form, und sie läuft andersherum: ein GENERATOR-Lauf der einen
    Sitzung löscht die handgeschriebene Prosa der anderen.** `rules/README.md`
    wird von `fetch_datasheet_rules.py` neu erzeugt; Commit `c72db33` hat dort
    einen Absatz über die Core-Stratagem-Tooltips von Hand eingefügt, und eine
    Minute später hat ein routinemäßiger `--offline`-Rundlauf ihn wortlos
    entfernt. Behoben, indem der Absatz in den GENERATOR gewandert ist (samt
    Kommentar, warum er dort steht): eine generierte Datei direkt zu
    beschriften ist per Konstruktion transient. **Beim nächsten Mal also nicht
    nur `git grep` über HEAD, sondern auch `git status --porcelain` auf die
    GENERIERTEN Verzeichnisse lesen, bevor man den Diff für sauber hält** — er
    sah mit einer einzigen `M rules/README.md`-Zeile harmlos aus.
    **Und die -A-Regel trägt in BEIDE Richtungen:** `c72db33` hat umgekehrt die
    komplette, noch uncommittete Etappe-8-Arbeit dieser Sitzung mitgenommen und
    unter einer Commit-Message über Playtest-Berichte abgelegt. Kein Verlust
    (per `git show --stat` geprüft, und HEAD ist frei von Sonden-Rückständen),
    aber die Etappe steht dadurch in zwei Commits statt in einem.
    **VIERTE Form, zwei Lehren an einem Sondenlauf (2026-09-12):** (a) die Prozessprüfung vor
    einem Sondenlauf sieht Python, aber kein `git commit` — `512b649` der Parallelsitzung fing
    `ai/agent_driver.py` mitten in Sonde 9 ein (die Sondenzeile stand in HEAD, der Folgecommit
    repariert sie). Nach jedem Sondenlauf daher `git grep` der ERSATZTEXTE über HEAD, nicht nur
    `if False:`. (b) Ein Restore per RÜCKWÄRTS-Ersetzung — gebaut, damit parallele Edits am
    selben File überleben — ersetzt JEDES Vorkommen des Ersatztexts. Stand der schon in der
    Datei, schreibt der Restore fremden Code um: `roll_choice.take()`s `return True` wurde zu
    einer `NameError`-Zeile. Ein Sondentreiber muss einen bereits vorhandenen Ersatztext
    ABLEHNEN (`ab_command_reroll_owner.py` tut es).
    **FÜNFTE Form (2026-09-17): `git grep` übergeht UNGETRACKTE Dateien.** Ein beim Kompaktieren
    abgebrochener Sondenlauf ließ eine Sonde in einer NEUEN Datei stehen, und die Restprüfung war
    leer. Die Restprüfung ist `git grep --untracked "AB-PROBE"`; ein Sondenlauf ohne
    Schlusszeile im Output gilt als mitten in einer Sonde abgebrochen.
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

26. **Ein RETRY, der eine Reaktionskette erneut durchläuft.** `_run_charge_attempts()` ruft
    `begin_charge_move()` für jeden der dreizehn Anläufe einer Charge, und das läuft die
    Deklarations-Reaktionskette (Grav-Inhibitor Field, Photon Grenades, Combat Embarkation) jedes
    Mal neu. Zwei Folgen, beide reproduziert (2026-09-09): ein Reaktor OHNE `_offered_key`-Memo
    fragte den Menschen bei JEDEM Retry erneut; und öffnete eine Reaktion beim Retry einen Prompt,
    blieb der Zug GESCHLOSSEN — `clamp_move()` gibt dann den Wunsch zurück, `try_commit_segment()`
    akzeptiert — und die Leiter versetzte alle fünf Modelle UNVALIDIERT, lehnte die Charge ab und
    ließ den Prompt stehen. Drei Nähte halten das jetzt: jeder Reaktor merkt sich die Deklaration,
    die er gefragt hat (`_declaration_key`; `test_charge_retry_reactions.py` §6 prüft das als
    MENGENDIFFERENZ über alle in `main.py` registrierten Reaktoren); die Leiter prüft nach JEDEM
    `reopen()`, ob ein Zug offen ist, und gibt sonst `None` zurück ("komm wieder", nicht "gescheitert");
    und der Resume-Zweig von `_handle_charge()` öffnet den Zug nur, wenn er nicht schon offen ist —
    `begin_charge_move()` über einem offenen Zug ist dieselbe Kette ein weiteres Mal, und dort
    konnte der Wächter einen zweiten Prompt nicht sehen.
27. **Ein Retry, der dieselbe OFFENE Frage zurückreicht, bekommt dieselbe Antwort.** Der
    Retry-Kanal an den Planner schickte eine zu weite Koordinate mit „unerreichbar, nur 14" auch
    mit Advance" zurück — also mit genau der Aufgabe, an der der Planner gerade gescheitert war:
    einen erreichbaren Punkt herzuleiten. Gemessen (`logs/game_20260909_210843.log`): die Wraiths
    bei (34,4) sollten nach (25,20), 17" weit; die Revision befahl (44,7), erreichbar und **2"
    WEITER** vom Central Objective weg, das die Begründung selbst nannte. Die Einheit lief
    rückwärts, wie befohlen. Ein Rückweg lohnt nur für Probleme, deren Lösung ein URTEIL braucht,
    das dieser Code nicht fällen kann (`_problems_for_the_planner()`: LONE OPERATIVE vom
    bestellten Standort unbeschießbar, Über-/Ein-Einheiten-Garnison). Wo die Lösung ein PUNKT
    ist, wird er ANGEBOTEN (`first_leg_this_turn`) und deterministisch eingesetzt
    (`_validate_turn_plan()`: Clamp auf den ersten Schenkel, Ersatz eines Rückwärtsbefehls durch
    den ersten Schenkel zum eigenen Ziel). Vor jedem neuen „schick es dem Planner zurück" fragen:
    kann er die Frage mit dem, was er hat, überhaupt anders beantworten als beim ersten Mal?

## Diagnose-Logging

Wiederholt war der eigentliche Defekt nicht der Fehler, sondern dass er im Log unsichtbar war — die
Untersuchung musste dann aus rohen Koordinaten rekonstruiert werden. Vorhandene `file_only`-Zeilen:
`[move detail]`, `[move choice]` (gewählter Optionstyp + Zielpunkt + Plan-Koordinate), `[charge]`
(Ziel, Wurf, erreichte Kantendistanz, Engagement — auch bei Ablehnung mit den Odds), `[coherency]`
(welche Modelle, wie weit daneben, an jeder Phasengrenze, entprellt), `[threat]`, `[turn plan]`
(inkl. `@(x,y)`), `[ingress]` (der TATSÄCHLICHE Landeplatz), `[regroup]`, `[pile in]` (vorher ->
nachher engagierte Modelle), `[deploy]`, `[charge reroll]`, `[disembark]`, und seit 2026-09-09
`[move sweep]` (je Bewegung: Kandidaten, Gewinner mit erreicht/beabsichtigt, Fallbacks, Friendly-
Clamp clear/relanded/truncated, Split-Pässe) und `[charge geometry]` (bei einer von jedem Anlauf
abgelehnten Charge: Ring-Slots, davon LEGAL, im Wurf, nächster; dazu `[charge] ... not offered`,
wenn um keinen Feind in 12" ein legaler Standplatz liegt).

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
- **Smokes, Messskripte, Laufzeit-Sonden** (`smoke_*.py`, `measure_*.py`, `verify_*.py`) — was
  jedes Skript belegt, welche Tatsachen es STELLT und was sein `--neutralize` meldet, steht im
  Katalog `docs/stand/werkzeuge.md`; ein neues Skript wird DORT eingetragen. Das gemeinsame Muster:
  durch `selfplay.py`s echte `main()`-Schleife (per `runpy`), nur stellen, was ein MockAgent-Lauf
  nachweislich nicht erreicht (und im Modulkopf sagen warum), und `--neutralize` stellt die
  Vor-Fix-Welt her und MUSS scheitern. `run_tests.py --smoke` fährt die schweren davon mit.
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
- **Und `config.AUTOSAVE = False`, VOR `import main`** — sonst überschreibt der Lauf
  `scenes/autosave.json`, also genau die Datei, die „Resume Game" des Users anbietet. Am
  2026-09-12 waren mindestens 17 der 26 Läufe, die einen Autosave schrieben, Harnesses.
  `test_autosave.py` §5 prüft das an jedem Skript, das `main.main()`/`main.run()` ruft
  (`verify_*.py` erben es über `selfplay.py`). Wer den Autosave MESSEN will, schaltet ihn im
  Harness wieder ein und lenkt `scene_io.SCENES_DIR` in einen Wegwerf-Ordner — Vorlage
  `verify_phase_autosave.py`.
- Der Turn-Plan-Grund `(test plan)` bzw. `(mock plan)` unterscheidet einen Selbstspiel-Lauf von einer
  echten Partie des Users im selben `logs/`-Ordner.

---

# Teil 2 — Stand: Verzeichnis von `docs/stand/`

Jede Datei hält Abschnitte, die bis 2026-09-17 hier standen, wörtlich; die Zeilen unter einer Datei
sind ihre `##`-Überschriften. Gelesen wird nur, was die Aufgabe betrifft — bei Arbeit an einer
Fraktion deren Dateien plus `fraktionen.md`; bei einer gemeldeten Fehlerform zuerst die
`meldungen-*.md` und die Stratagem-Prüfungen, weil die meisten Formen dort schon aufgetreten sind.

## Brett und Darstellung

### `docs/stand/karten-und-gelaende.md` — die vier Karten samt Objective-Namen, gedrehtes Terrain, halbierte Wanddicke
- Karten und Szene
- Terrain darf sich DREHEN (game/terrain.py, Stufe 2)
- Die Wände sind halb so dick (game/terrain.py)

### `docs/stand/zonen-biome-und-farben.md` — Aufstellungszonen als Formen und Territorien, Zonenmarkierungen, Biome (Arena gerendert), konstante Spielerfarben
- Aufstellungszonen sind FORMEN (game/shapes.py, game/deployment.py)
- Aufstellungszonen-Markierungen (game/renderer.py)
- Biome (game/biomes.py)
- Das Arena-Biom (game/arena_biome.py)
- Spielerfarbe zurück auf GRÜN (game/renderer.py)

## Oberfläche

### `docs/stand/menue-speichern-autosave.md` — Game Menu (Start und ESC), Titel und Hintergrund, Speichern/Laden, Autosave je Phasenwechsel, Modell-Identität im Save
- Game Menu (game/ui/game_menu.py, main.py's run())

### `docs/stand/kartenauswahl-und-vorspiel.md` — Kartenauswahl-Screen (Kachelhöhe, zwei Takte), Vorspiel-Sequenz 03.01 (Resume, Support Artillery, Aufstellungs-KI)
- Kartenauswahl (game/ui/map_select.py)
- Vorspiel (Regel 03.01)

### `docs/stand/ui-status-panels.md` — Fraktions-Badges, Rundenbalken am oberen Rand, Türkis für Agile Manoeuvres, rote Decline- und blaue Overlay-Knöpfe
- Die Fraktions-Badges (game/ui/faction_badge.py, game_status_panel, turn_start_overlay)
- Der Rundenbalken am oberen Brettrand (game/ui/round_progress_bar.py)
- Agile Manoeuvres sind TÜRKIS, nicht violett (game/ui/button_style.py)
- Decline-Buttons sind ROT — auch im Overlay (game/decline_option.py)

### `docs/stand/ui-stats-und-toggles.md` — Unit-Statistics-Resümee (auch am Schlachtende), Toggle-Leiste (Drag Whole Unit, Reichweiten-Lineal)
- Unit Statistics — das Resümee der Partie (game/battle_stats.py, game/ui/unit_stats_overlay.py)
- Die Toggle-Leiste unten links (game/ui/button_style.py, game/whole_unit_drag.py)

### `docs/stand/ui-wuerfelpanel-und-auswahl.md` — Würfelpanel (Größe, Crit-Plaketten, Titel, Reroll- und Fähigkeitsknöpfe), erstklassige Einheiten-Auswahl
- Das Würfelpanel: nichts fliegt mehr heraus, und Crit-Labels sind Plaketten
- Einheiten-Auswahl ist erstklassig (game/selection.py)

### `docs/stand/ui-brett-pick-und-linien.md` — Einheiten auf dem Brett wählen (unit_pick, Regeltext und Überschrift in der linken Spalte), Total-War-Linien-Formation
- Einheiten auf dem Brett wählen, nicht aus einer Liste (game/unit_pick.py)
- Total-War-Linien-Formation (rechte Maustaste)

### `docs/stand/datacard-und-regelleser.md` — Hover-Datacard mit gedrucktem Regeltext, Army-Rules-Leser, Stratagem-Tooltip
- Die Hover-Datacard zeigt den GEDRUCKTEN Regeltext (game/rules_text.py)

## Armeen und Listen

### `docs/stand/armeen-listen-1.md` — Armeelisten als JSON (Module, Validator, Golden Master, tau_recon/Coldstar), Detachments gehören zur Liste
- Armeen (armies/*.json) und Listenauswahl
- Detachments gehören zur LISTE (game/detachments.py)

### `docs/stand/armeen-listen-2.md` — Volk-dann-Liste-Screen samt Grid, und jede ausgelieferte Liste im Detail (T'au in tau-listen.md)
- Armeen (armies/*.json) und Listenauswahl — Fortsetzung

### `docs/stand/tau-listen.md` — die T'au-Listen im Detail (Kauyon, Mont'ka, Prototypes zurückgezogen, Retaliation Cadre) und was sie an der Engine änderten
- Die T'au-Liste (2026-09-05)

## Regelengine

### `docs/stand/regelengine-bewegung.md` — Bewegung, Landeplatz-Suche, Charge-Geometrie, Wand-Hausregel, Take to the Skies, Bewegungsqualität (Mess-Baseline)
- Regelengine — Bewegung
- Bewegungsqualität — was gemessen ist

### `docs/stand/regelengine-schiessen.md` — Schießen (10.06, reaktive Schüsse, Zielwahl-Freeze, Unmodified-Six-Knopf), der T'au-Lag-Fix (Sichtlinien-Memo, Greater Good)
- Regelengine — Schießen
- Die Schussphase war mit T'au unspielbar (2026-09-08)

### `docs/stand/regelengine-nahkampf.md` — Nahkampf (12.02-Freeze, Waffengruppen, Counteroffensive, Sudden Strike, End-Turn-Warnung, [ASSAULT]-Tor)
- Regelengine — Nahkampf

### `docs/stand/regelengine-command-status.md` — Command-Phase, Core-Stratagems (Explosives, Heroic Intervention, Command Re-roll), Schaden und Saves, Terrain/Objectives/Status
- Regelengine — Command-Phase / Stratagems / Schaden
- Terrain / Objectives / Status

## Missionen und Regeltext

### `docs/stand/aktionen-und-primary-missions.md` — Aktionen (16.01), Primary Missions über Force Dispositions
- Aktionen (Regel 16.01, game/actions.py)
- Primary Missions über Force Dispositions (game/primary_missions.py)

### `docs/stand/missionen-standard-und-secondary.md` — Hold the Line / No Mercy (Raten, erste Runde), der Tactical-Secondary-Kartenstapel und alle Karten
- Missionen (game/missions.py, game/secondary_missions.py)

### `docs/stand/regeltext-korpus-und-waffentabelle.md` — Missionskarten-Layout und Wertungstabelle, Waffentabelle (Platzhalter, Keywords, Gegencheck), Regeltext-Korpus (Scraper, 2026-09-Layout)
- Die Hover-Datacard zeigt den GEDRUCKTEN Regeltext — Fortsetzung
- Regeltext-Korpus (`rules/*.md`, `fetch_datasheet_rules.py`)

## Fraktionen

### `docs/stand/fraktionen.md` — Übersicht aller fünf Fraktionen (Necrons und Death Guard ausführlich)
- Fraktionen

### `docs/stand/tau-detachments.md` — T'au-Detachment-Regeln, alle 25 Stratagems, alle 19 Enhancements
- T'au-Detachment-Regeln: Kauyon und Mont'ka
- Die drei übrigen T'au-Detachment-Regeln
- T'au-Detachment-Stratagems
- T'au-Detachment-Enhancements (game/enhancements.py + game/enh_*.py)

### `docs/stand/tau-datenblaetter.md` — die T'au-Datenblatt-Etappen 1a bis 4 und die Sprites
- Die drei Kroot Shaper (Etappe 1a der fehlenden T'au-Datenblätter)
- Die sechs übrigen T'au-Charaktere (Etappe 1b)
- Kroot und Vespid (Etappe 2)
- Die zwei Walker (Etappe 3)
- Die drei Fahrzeuge (Etappe 4 — damit ist der T'au-Nachzug fertig)
- T'au-Sprites vollständig

### `docs/stand/aeldari-nachzug.md` — die 27 restlichen Aeldari-Datenblätter, sieben Detachment-Regeln, 36 Detachment-Stratagems, Battle Focus der Wraith Constructs
- Die restlichen Aeldari-Datenblätter (27 Stück, sieben Etappen)
- Die sieben Aeldari-Detachment-REGELN
- Die 36 Aeldari-Detachment-STRATAGEMS (sieben Etappen)
- WRAITH CONSTRUCTs hatten Battle Focus, das sie nicht drucken

### `docs/stand/necrons-datenblaetter-1.md` — Umfang, Etappe 0 (TITANIC-Leser), 1 Crypteks, 2 Fußvolk, 3 Destroyer Cult
- Die restlichen Necron-Datenblätter (32 Stück, neun Etappen)

### `docs/stand/necrons-datenblaetter-2.md` — Etappe 4 Triarch, 5 Canoptek, 6 die drei C'tan
- Die restlichen Necron-Datenblätter — Fortsetzung

### `docs/stand/necrons-datenblaetter-3.md` — Etappe 7 anbindbare Charaktere, 8 Grav-Skimmer und Ghost Ark
- Die restlichen Necron-Datenblätter — Fortsetzung

### `docs/stand/necrons-datenblaetter-4.md` — Etappe 9 Monolith und The Silent King
- Die restlichen Necron-Datenblätter — Fortsetzung

### `docs/stand/necrons-detachments-und-audit.md` — Canoptek Court, Hypercrypt Legion; die Prüfung „werden die Necron-Stratagems angeboten“
- Die Necron-Detachments (Etappen 1-3)
- Werden die Necron-Stratagems überhaupt ANGEBOTEN? (Prüfung, 2026-09-08)

### `docs/stand/orks-codex-2026-09.md` — Etappen E1 Armeeregel, E2 War Horde, E3a Mobs, E3b Charaktere, E3c Spezialisten
- Die Ork-Armeeregel (2026-09-Codex): Waaagh!, riled up, War Cry — Etappe E1
- War Horde (2026-09-Codex): Detachment-Regel, vier Enhancements, sechs Stratagems — Etappe E2
- Ork-Mobs (2026-09-Codex): Boyz, Beast Snagga Boyz, Stormboyz, Gretchin, Meganobz — Etappe E3a
- Ork-Charaktere (2026-09-Codex): Warboss, Warboss in Mega Armour, Beastboss, Painboy — Etappe E3b
- Ork-Spezialisten (2026-09-Codex): Flash Gitz, Tankbustas — Etappe E3c

### `docs/stand/orks-codex-2026-09-2.md` — Etappen E3d Fahrzeuge (Pilin' Out, Aerial Manoover, Mobile Fortress/Dread 'Ard, Rundenende-Sweep) und E3e Kill Rig (psychischer Wurf, Warpath, Beastscent, ein Würfel-Slot)
- Ork-Fahrzeuge (2026-09-Codex): Warbikers, Deffkoptas, Trukk, Battlewagon, Deff Dread — Etappe E3d
- Kill Rig (2026-09-Codex): Beastscent, Warpath, der psychische Wurf — Etappe E3e

### `docs/stand/audits-aeldari-und-tau.md` — die Prüfungen „werden die Aeldari-/T'au-Stratagems angeboten und wirken sie“
- Werden die Aeldari-Stratagems überhaupt ANGEBOTEN? (Prüfung, 2026-09-07)
- Werden die T'au-Stratagems überhaupt ANGEBOTEN? (Prüfung, 2026-09-07)

## KI

### `docs/stand/ki-architektur.md` — zwei Schichten, Validator, Garnisons-Pässe, erster Schenkel, deterministische Antworten; API-Ausfall
- KI-Architektur
- Ein API-Fehler stoppt die KI, nicht das Spiel (ai/connection.py)

### `docs/stand/ki-weiche.md` — deterministisch für die KI, wählbar für den Menschen: auto_players, Rückkehr-Platzierung, KI-Modus-Schalter
- Die KI-Weiche: deterministisch fuer die KI, waehlbar fuer den Menschen

## Meldungen aus Partien

### `docs/stand/meldungen-1.md` — 2026-09-06 bis -08: Elf Meldungen aus drei Partien, D-cannon-Absturz, Blades of Asuryan
- Elf Meldungen aus drei Partien (2026-09-06)
- Absturz beim Feuern der D-cannon (2026-09-08)
- Blades of Asuryan: [PISTOL] erreichte das EIGNUNGS-TOR nicht (2026-09-08)

### `docs/stand/meldungen-2.md` — 2026-09-08: TARGET-Einheitenwahl, Zwei Meldungen, Avatar-Charge und Home-Objective-Klumpen
- "TARGET: One <X> unit from your army" wurde NICHT gewählt (2026-09-08)
- Zwei Meldungen aus einer Partie (2026-09-08)
- Der Avatar-Charge und der Home-Objective-Klumpen (2026-09-08)

### `docs/stand/meldungen-3.md` — 2026-09-09/-10: Fünf Meldungen aus einer Partie, Cleanse-Knopf
- Fünf Meldungen aus einer Partie (2026-09-09)
- Cleanse bot einen Knopf an, der nicht auszahlen konnte (2026-09-10)

### `docs/stand/meldungen-4.md` — 2026-09-11/-12: Vier Meldungen (T'au gegen Death Guard), GRENADES-Keyword
- Vier Meldungen aus einer T'au-gegen-Death-Guard-Partie (2026-09-11)
- GRENADES fehlte auf 18 Profilklassen — Explosives unerreichbar (2026-09-12)

## Kataloge

### `docs/stand/extraktionen.md` — jede Extraktion seit der zehnten: Modul, Konsumenten, die leicht zu verfehlende Hälfte (Fehlerklasse 10)
- Extraktionskatalog (aus Fehlerklasse 10 ausgelagert)

### `docs/stand/werkzeuge.md` — Smokes, Messskripte und Laufzeit-Sonden: was jedes belegt, was es stellt, was --neutralize meldet
- Smokes, Messskripte und Laufzeit-Sonden (aus „Tests und Werkzeuge“ ausgelagert)

# Teil 3 — Offen

## Bekannte offene Punkte

- Ein von allen Seiten umstelltes Fahrzeug kann steckenbleiben (Ein-Wegpunkt-Heuristik + A*, keine
  formationsbewusste Pfadsuche).
- **Der gemeldete Lychguard-Charge (Fall A) bleibt zu Recht unvollendet** — kürzester legaler
  PFAD 12.05–12.26" bei 12" Wurf; die Machbarkeits-Prüfung vor der Deklaration rechnet Luftlinie
  zum nächsten legalen Slot (11.17") und würde ihn weiter anbieten. Eine pfadbewusste Prüfung
  (A* je Kandidat vor der Deklaration) ist die nächste Stufe, wenn solche Fälle im Log häufig
  werden; `[charge geometry]` nennt seit dem Review die LEGALEN Slots.
- `measure_fly_penalty.py` baut KEIN Terrain (`GameState()` ohne `battle_map.build`) — sein
  +0.93"-Befund stammt von einem terrainfreien Brett; `measure_reported_moves.py` ist die Vorlage,
  die das richtig macht.
- `observation.charge_now` (die Odds im Prompt) rechnet weiter Luftlinie; die Deklarationsschleife
  der taktischen Schicht nicht mehr. Eine eigene Entscheidung mit eigenem Pin
  (`test_staging_and_charge.py`).
- Keine explizite Right-of-Way-Koordination zwischen Einheiten im selben Zug (nur implizit über
  `priority` und die Korridor-/Ausladezonen-Stufen).
- `GreaterGoodController.choose_target()` kann bei einer (nie auftretenden) ungültigen Zielwahl in
  `CHOOSING_TARGET` hängen bleiben.
- `TransportController`s Rapid-Disembark-Pfad prüft 20.04s Zonen-Sperre nicht.
- ~~**Mont'kas Killing Blow gewährt [ASSAULT], erreicht aber 10.05s Advance-Tor nicht**~~ —
  **erledigt** im T'au-Stratagem-Audit (2026-09-07, Fund F3), und die Abwägung, die diesen Eintrag
  trug, ist dabei bestätigt statt umgeworfen worden: der `turn_tracker` wird weiterhin NICHT durch
  `_attack_groups()`s elf Aufrufstellen gefädelt — die Antwort kommt als SQUAD-FLAG
  (`Squad.montka_killing_blow`, einmal je Phasenwechsel von `montka.refresh_killing_blow()` aus
  DERSELBEN `is_active()` gestempelt, die auch die Adjuster-Kette liest).
  `weapon_has_assault()` endet auf `montka.grants_assault(squad)`, und Abschnitt 7s
  `_ASSAULT_GRANT_GAPS` ist damit **leer**. Im echten Spiel belegt
  (`verify_tau_montka_assault.py`): **0 von 151** Fernkampfwaffen am Advance-Tor abgelehnt, gegen
  **102** unter `--neutralize`. **Die Lehre bleibt und steht dort ausgeschrieben:** dieser Eintrag
  wurde ZWEIMAL mit einer Begründung gerechtfertigt, die ablief, während die Zusicherung grün
  blieb — genau die Ausfallart, die ein BENANNTER Gap hat und eine Mengendifferenz nicht.
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
- **Die Zug-nach-dem-Schießen-FAMILIE gehört extrahiert, und zwar überfällig.** Fünf Module
  derselben Form: `tactical_acumen.py` (Asurmen, 6", kein ER-Satz), `fire_and_fade.py`
  (Lone-Spear, 6", ER-Satz), `warhost_fire_and_fade.py` (Stratagem, 6", + Embark-Lock),
  `chronometron.py` (Chronomancer, 5", ER-Satz), `evasion_engrams.py` (Tomb Blades, 6", kein
  ER-Satz). `fire_and_fade.py` argumentiert für Zwillinge statt einer geteilten Klasse ("sie
  unterscheiden sich in ihrem Prädikat") — eine faire Lesart bei ZWEI. Bei FÜNF sind die
  variierenden Teile auf **vier Knöpfe** zusammengefallen: Prädikat, Distanz, ob der gedruckte
  Text eine Engagement-Range-Klausel trägt, und welche Locks beim Confirm greifen. Nach der
  Zweiter-Konsument-Regel dieses Repos also fällig; bewusst NICHT in einer Datenblatt-Etappe
  gemacht (das schriebe vier laufende Module und ihre Suiten mitten in einer anderen Arbeit um),
  und als Kandidat samt Knopfliste in `game/evasion_engrams.py`s Docstring festgehalten.

