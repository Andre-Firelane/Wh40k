# T'au: Detachments

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

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
