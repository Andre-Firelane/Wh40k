# Meldungen aus Partien (1)

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

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
