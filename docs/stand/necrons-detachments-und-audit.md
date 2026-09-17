# Necrons: Detachments und Stratagem-Prüfung

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die Necron-Detachments (Etappen 1-3)

**Auftrag:** drei weitere Necron-Detachments vollständig — Regel, alle Stratagems, alle
Enhancements —, eines pro Etappe: Canoptek Court → Hypercrypt Legion → Cryptek Conclave. Plan:
`C:\Users\Andre\.claude\plans\necron-detachments-anlegen-detachment-nifty-quill.md`.
**User-Entscheidungen:** keine Armeeliste ändert sich (dormant by roster, belegt per Suite und
Laufzeit-Sonde — für die Hypercrypt Legion seit dem 2026-09-13 überholt: der User hat dafür eine
Liste geliefert, `armies/necrons_hypercrypt.json`, siehe `## Armeen`); volle deterministische KI-Nutzung (0 API-Calls); „Your NECRONS WARLORD" ist ein
belegter No-op; Reanimation-Boosts gelten bei JEDER Aktivierung; nach jeder Etappe commit + push +
Bericht + anhalten.

### Etappe 1 — Canoptek Court (3 DP, Take and Hold)

Regel Power Matrix, vier Enhancements, sechs Stratagems. Module `game/court_*.py`,
`game/enh_{dimensional_sanctum,hyperphasic_fulcrum,autodivinator,metalodermal_tesla_weave}.py` und
`game/necron_detachments.py` (Spiegel von `aeldari_detachments.py`: CRYPTEK/CANOPTEK je EINHEIT per
19.03 und je MODELL per `model_has_datasheet_keyword()`). **Präfix `court_`, nicht `canoptek_`**
(`canoptek_swarm.py` existiert); die Conclave-Etappe darf nicht `conclave_` nehmen (Aeldari-Zählsweep).

**Drei Vorarbeiten, jede ein eigener Befund:**
1. **`movement_controller.on_move_finished` wurde in `main()` NEU ZUGEWIESEN** (`= [...]`), nachdem
   fünf Listener angehängt waren — Spirit Stone, Spirit Mark, Higher Duty, **Wraith Form** und
   Internal Grenade Racks haben in einem echten Spiel nie einen Zug gehört. Jetzt `.extend([...])`;
   Wächter `test_event_chain_wiring.py` §25. Im echten Spiel: 9 von 9 Listenern auf der Live-Liste,
   `--neutralize` 6 fehlen.
2. **`reanimation_protocols.activate()` ist die EINE Tür in `reanimate()`** (Boost + gedruckter
   Bonus + reanimate), gelesen von Armeeregel, Undying Legions, Resurrection Orb, Repair Barge und
   Suboptimal Facade — beide Canoptek-Boosts drucken „EACH TIME ... activate" (User-Entscheidung;
   vorher erreichte der Boost nur die Armeeregel). AST-Wächter: kein `reanimate(` außerhalb des Moduls.
3. **Per-Modell-Term im Angriffsschlüssel** (`necron_detachments.attack_key()`): Cynosure und Curse
   fragen CRYPTEK/CANOPTEK-MODELLE, und 04.03 löst mit dem ersten Modell der Gruppe auf. Für jeden
   Spieler ohne das Detachment die Konstante `(False, False)`, keine bestehende Gruppe spaltet sich.

**Power Matrix** (`court_power_matrix.py`): drei Regionen, die Matrix ist eine Vereinigung;
„wholly within" je Modell über `contains_circle`/`distance_to_point`. Latch je
`(Runde, Zugbesitzer, Phase)`, gestempelt in `main.py`s Start-of-any-phase-Block; ohne Stempel die
Live-Antwort. **„Mindestens die Hälfte" von null ist nicht die Hälfte** (auf allen vier Karten
unerreichbar, gemessen und gepinnt). Reroll: automatische Hit-1er für jede CRYPTEK/CANOPTEK-Einheit,
der ganze Wurf wholly within → achter Eintrag in `reroll_scope.ONES_OR_WHOLE_LABELS`, beide Phasen.

**Enhancements:** Dimensional Sanctum (Klausel in `squad_has_infiltrators()`), Hyperphasic Fulcrum
(automatische Wound-1er; „leading" = echte 19.01-Anbindung), **Autodivinator** — dafür bekam
`CommandPointManager.gain_cp()` ein PFLICHT-`source=` (`SOURCE_ABILITY`/`SOURCE_MISSION`) und
`on_cp_gained`-Listener, die nur einen GELANDETEN Grant hören; alle sechs Produktionsaufrufer
nachgezogen, der Secondary-Discard ist MISSION. Sein D6 wird im Modul geworfen (der Auslöser kann
mitten in einem fremden Wurf liegen — benannte Ausnahme). **Metalodermal Tesla Weave** ist ein
Reaktor in `charge_declaration_reactions` mit eigener `MortalWoundAllocationSession` und allen fünf
main.py-Kanten (§6/§11/§12/§17/§20).

**Stratagems:** Curse of the Cryptek (reaktiv: Tod aus dem Sweep, Angebot aus den
Nach-Aktivierungs-Haken, schlachtlange Marke, −1 auf die Schwellen nur für CANOPTEK-MODELLE),
**Cynosure of Eradication** und **Solar Pulse** (Registry-Knöpfe; Cynosure druckt „the start of THE
Fight phase" ohne Besitzer), Reactive Subroutines (`on_move_finished`-Listener, Modus in
`REACTIVE_MOVE_MODES`, Confirm/Cancel im Panel, KI über injizierte Destination/Mover),
Countertemporal Shift (`shooting_target_reactions` + `revalidate_target_selection`), Suboptimal
Facade (Charge-Deklarations-Reaktor, `activate()` mit Placer). KI: Cynosure und Solar Pulse als
`_handle_*` ohne `agent`, der Rest über `auto_players`; die Beobachtung meldet `power_matrix`.

**Echter Fehler, vom eigenen Test gefunden:** `reactive_subroutines_destination()` gab
`first_leg_toward()`s `{"x","y"}`-Dict zurück, Controller und `_advance_toward()` indizieren ein
Paar → `KeyError` beim ersten KI-Einsatz. Jetzt ein Tupel, plus End-to-end-Prüfung mit der echten
Politik.

**Die Panel-Hälfte:** neu `test_necron_detachment_ui.py` (wächst je Etappe) — Liveness, 2×5-Matrix,
die Besitzer-Klausel (Cynosure im gegnerischen Fight AM PANEL, weil `can_select()` dort beide
zulässt), Detachment-Tor am Panel, TARGET- und Start-of-phase-Negative, **beide Resets einzeln**
(15.01-Ledger allein lässt den Knopf weg, der eigene Phasen-Reset allein auch), der Klick zahlt
(Solar Pulse erst nach der Objective-Frage; Cancel kostet nichts), Label ↔ Korpus, und per AST:
genau die zwei Knöpfe definieren `panel_label()` und stehen auf der Registry, die vier reaktiven nicht.

**A/B-Sonden (`ab_necron_canoptek_court.py`): 69 Sonden, 74 Suite-Läufe, alle beißend.** Neun bissen
zuerst nicht oder ließen die Suite abstürzen, jede ein Befund über den TEST: der automatische
Shooting-1er-Wurf war nur per Teilstring gepinnt (jetzt der echte `_hit_step`); ein Ein-Modell-Ziel
der Tesla Weave fehlte (die Klicks des Tests leerten die Session und verdeckten einen Controller,
der sich nie selbst fertig meldet); der Curse-Tod ohne Täter; die per-MODELL-Lesung des Curse
brauchte eine gemischte Einheit (Geomancer in Macrocytes); Cynosure in der Fight-Adjuster-Kette;
zwei Stellen stürzten ab statt rot zu werden; und **`test_event_chain_wiring.py` §11 akzeptierte eine
Würfelbestätigung unter `if False:`** (Regex über Text) — jetzt AST über erreichbaren Code. Der
Statement-Pin der Court-Suite ist ebenso gegen `if False:`/`False and` gehärtet. Jede Ersetzung
trägt den Marker `AB-PROBE`; der Treiber hasht jede sondierte Datei vor und nach dem Lauf, und
danach muss `git grep "AB-PROBE" -- . ":!ab_*.py"` leer sein.

**Im ECHTEN Spiel belegt** (`verify_necron_canoptek_court.py`; Necrons als Player 1, Detachment per
Wrapper; `--neutralize` lädt `main.py` per Import-Hook mit den gemessenen Nähten zurückgebaut — die
Datei auf der Platte bleibt unberührt):

| | gefixt | `--neutralize` |
|---|---|---|
| gefütterte Listener auf der Live-Liste | 9 von 9 | 6 fehlen |
| Power Matrix für die laufende Phase gestempelt | ja | nein |
| ganzer Hit-Wurf für `1 Immortals 1 + Plasmancer` | `'Power Matrix'` | None |
| Cynosure / Solar Pulse gezeichnet | Shooting+Fight / Shooting | nie |
| Knöpfe außerhalb ihres WHEN | 0 | 0 |

**Gemessener Harness-Befund:** die Phasen-Rotation muss beim Eintritt in den Fight
`reset_fight_phase()` rufen wie `main()` — sonst trägt der Fight-Controller `done` aus einer früheren
Fight-Phase, und Cynosure wird 631-mal aus einem Grund abgelehnt, den kein Spiel erzeugt.
**Benannt, kein Fehler:** im Fight der KI beginnt `_handle_fight()` den Fight-Step, sobald auf keiner
Seite ein Pile In aussteht; das Fenster des Menschen für Cynosure ist also genau so lang, wie eine
eigene Einheit noch einen Pile In schuldet — genau dann, wenn sie überhaupt kämpfen könnte.

**Mitwandernde Pins:** `test_detachments.py`, `test_force_dispositions.py` (18),
`test_corsairs.py` (8 Labels), `test_necron_canoptek.py` (5 Boost-Türen),
`test_necron_datasheets.py`, `test_tau_enhancements.py` (KI-Leck-Wächter auf T'au-Detachments
verengt), `test_unit_pick.py` (Solar Pulse' Objective-Liste), `test_charge_retry_reactions.py` §6
(fegt jetzt jeden `charge_declaration_reactions.extend([`-Block).

**Getestet:** `test_necron_canoptek_court.py` **415/415**, `test_necron_detachment_ui.py` **97/97**,
`test_event_chain_wiring.py` **249/249**, `test_charge_retry_reactions.py` **48/48**. Volle
Regression **230 Suiten, ~21527 Prüfungen, 229 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke`
komplett grün (inkl. `selfplay.py map2 1500` mit den Default-Armeen), dazu `selfplay.py map2 1500`
mit Necrons auf BEIDEN Seiten und beiden im Court (exit 0; das Log zeigt
`[power matrix] Player 2: your deployment zone + No Man's Land.` — die Matrix wächst live).
`verify_rules_vs_engine.py` unverändert bei 70 Differenzen, keine nennt den Court;
`fetch_datasheet_rules.py --offline` ohne Korpus-Diff.

### Etappe 2 — Hypercrypt Legion (2 DP, Reconnaissance)

Regel Hyperphasing, vier Enhancements, sechs Stratagems. Module `game/hypercrypt_*.py` und
`game/enh_{dimensional_overseer,arisen_tyrant,hyperspatial_transfer_node,osteoclave_fulcrum}.py`.
Dieselben Vorgaben wie Etappe 1 (dormant by roster, volle deterministische KI-Nutzung).

**Sechs Vorarbeiten:**
1. **`game/battle_size.py`** — `normalize()`/`lookup(table)`, gelesen von Battle Focus, Ride the Wind
   und Hyperphasing (drei Kopien derselben Schlachtgrößen-Frage).
2. **`game/end_of_turn_withdrawal.py`** — die Zugende-Rücknahme in Strategic Reserves als Basisklasse
   aus `RideTheWindController` (Zähler, `limit()`, `per_unit_offer`-Kette, `prompt_for`). Ride the
   Wind verhaltensneutral umgestellt (seine Suite ohne Anpassung grün; `ab_per_unit_offer.py` zielt
   jetzt auf die Basis). Neu: ein injiziertes `choose(eligible, cap)` beantwortet `auto_players`
   synchron; ohne Politik wird die KI weiter nur herausgefiltert (Ride the Wind injiziert keine).
3. **Relaxed Arrival (User-Entscheidung):** „anywhere on the battlefield" hebt 20.04s
   Gegnerzonen-Verbot auf — `IngressController._in_enemy_deployment_zone()` antwortet False für
   `_uses_relaxed_arrival()`, und Overlay, Confirm und die KI-Landesuche
   (`_ingress_landing_candidates`) lesen dieselbe Stelle. Daring Riders und Cloudstrider ziehen mit.
4. **Eigenes Eternity-Gate-Charge-Lock** (`Squad.eternity_gate_charge_locked`, dazu
   `eternity_gate_bearer_started_on_board` und `IngressController.gate_arrivals_this_turn`):
   `eternity_gate.use` setzt es statt des geteilten `charge_locked_until_end_of_turn` — sonst höbe
   Dimensional Corridor Cosmic Precisions Lock mit auf. In `SQUAD_FLAGS`, am Zugende geräumt;
   `test_necron_titans.py` pinnt beide Richtungen.
5. **`FightController.models_lost_this_activation()`** — Spiegel der Schuss-Seite, damit
   Hyperphasic Recall aus beiden Phasen das Verlust-Ledger SEINER Phase bekommt.
6. **Off-Board-Reanimation:** `reanimation_protocols.activate(..., off_board=True)` (weiter die eine
   Tür) nimmt eine Einheit in `state.reserves`: Heilen wie immer, wiederbelebte Modelle kehren in
   `squad.models` zurück — ohne Token, ohne Platzierung, ohne Boost-FRAGE (der Boost gilt); sie
   landen mit der Einheit per Ingress. `test_return_placement.py` nimmt diese Tür ausdrücklich von
   der „jede Tür bekommt einen Placer"-Regel aus, mit Liveness-Zeile.

**Hyperphasing** (`hypercrypt_hyperphasing.py`): Cap 1/2/3 nach Battle Size plus Dimensional
Overseer; NECRONS, nicht engaged, nicht embarked, nicht schon in Reserve. **Nie angeboten, wenn die
Rücknahme nach 20.03 sicher tödlich wäre** (`withdrawal_is_doomed`: keine eigene Bewegungsphase mehr
vor der Zerstörung am Ende von Runde 3) — es öffnet dann gar keinen Prompt. **KI-Politik**
`agent_driver.hyperphasing_choice` (User: „Retten + Umpositionieren"): nie in Runde 1, nie eine
Garnison auf einem gehaltenen Objective; retten, wenn der erwartete eingehende Schaden ≥ ½
Restwunden; umpositionieren, wenn nächsten Zug weder Feind noch Objective erreichbar ist; nach
Punkten, bis zum Cap. Die Rückkehr übernimmt `_auto_ingress_squad`.

**Enhancements:** Dimensional Overseer (+1 auf den Cap, Träger auf dem Brett ODER in Reserve;
eingestiegen zählt nicht, und dafür braucht es keinen Filter — gemessen steht eine eingestiegene
Einheit in keinem der zwei gelesenen Container), Arisen Tyrant (automatische Hit-1er, ganzer Wurf
wenn die Einheit `set_up_this_turn` ist; neunter Eintrag in `ONES_OR_WHOLE_LABELS`, beide Phasen),
Hyperspatial Transfer Node (Kein-Wurf-Advance +6" in `start_run`), Osteoclave Fulcrum (Deep Strike
auf JEDES Modell der Einheit, idempotent, am Declare-Battle-Formations-Seam wie Student of Kauyon).

**Stratagems:**
- **Quantum Deflection** (reaktiv, in BEIDEN `target_reactions`): 4+ Invulnerable für die Phase,
  eigener Phasen-Reset; die KI kauft nur, wo 4+ die beste Rettung wirklich verbessert.
- **Entropic Damping** (reaktiv, nur Schuss): die Marke liegt auf dem ANGREIFER, `_adjusted_weapon`
  gibt jeder seiner Waffen [HAZARDOUS], der Hazard-Ledger zählt je Waffe; eine schon durchgehend
  hazardous Einheit wird nicht gefragt. KI: immer, wenn angeboten.
- **Hyperphasic Recall** (reaktiv aus `_necron_after_enemy_shooting`/`_fight`): Einheit getaggt,
  Monolith-Liste nur bei mehreren. **Das Set-up wartet auf den Todes-Sweep** (`resolve_deferred()`
  nach `remove_dead_models()`) — vorher liegen die Leichen noch im Weg; Basen wholly within 6" des
  Monolithen, nicht in Engagement Range, Cancel stellt die alten Positionen wieder her. KI: kauft,
  wenn der erwartete Schaden die Einheit sonst auslöscht.
- **Reanimation Crypts** (Panel, eigene Command-Phase): je Reserve-Einheit ein sichtbarer D3 durch
  `activate()` off board; die Würfel-Queue steht im Phasen-Tor und wird aus `main.py` bestätigt. KI
  (`_handle_reanimation_crypts`): ab zwei zurückholbaren Wunden.
- **Cosmic Precision** (Panel, eigene Movement-Phase, **auf dem ARRIVAL-Screen**): der erste
  Registry-Knopf, der auf dem Set-Up-Screen einer Ingress-Ankunft statt auf dem Einheiten-Screen
  steht. Naht: `ProactiveStratagems.buttons_for(squad, screen=ARRIVAL_SCREEN)` plus `notes_for()`,
  `PANEL_SCREEN` als Klassenattribut, und das Panel reicht die Registry per Keyword an
  `_draw_setup_ui()` (Fehlerklasse 22). Wirkung: Relaxed Arrival, Charge-Lock, neu gebautes
  Platzierungs-Overlay. KI in `_auto_ingress_squad`: nur bei klar besserem Landeplatz — ein
  Gleichstand ist kein CP.
- **Dimensional Corridor** (Panel, eigene Charge-Phase): hebt NUR das Gate-Lock, und nur wenn 11.02
  danach wirklich ja sagt — `eligible_once_lifted()` fragt die echte `can_declare_charge()` mit
  beiseitegelegtem Lock und stellt es im `finally` zurück. **Für die KI dormant**, solange sie das
  Eternity Gate ablehnt (benannt).

**Die Panel-Hälfte** (`test_necron_detachment_ui.py` §9-17): Liveness, die 2×5-Matrix auf BEIDEN
Screens (RC/DC nie auf dem Arrival-Screen, COS nie auf dem Einheiten-Screen), Besitzer, Detachment-
Tor und TARGET-Negative am Panel, isolierte Resets, der Klick zahlt (RC-Würfel revive off board,
COS zeichnet seine Notiz statt der Shortened-Blade-Zeile, DC hebt das Lock), Label ↔ Korpus, und per
AST: genau die drei definieren `panel_label()` und stehen auf der Registry,
`_h_screens == {"CosmicPrecisionController": "ARRIVAL_SCREEN"}`.

**A/B-Sonden (`ab_necron_hypercrypt_legion.py`): 91 Sonden, 108 Suite-Läufe, alle beißend, keine
stürzt ab.** Sechs bissen im ersten Lauf nicht — jede ein Befund über einen Test oder den Code:
- **Ein Test fragte den Controller der EINEN Szene nach der Einheit einer ZWEITEN**
  (`dc_scene(in_set=False)` zweimal gebaut): die fremde Einheit steht nicht auf dessen Brett, also
  Ablehnung aus dem falschen Grund.
- **Zwei Filter waren redundant und sind entfernt:** Overseers `embarked_in`-Term und Recalls
  „kein Monolith"-Early-out (`monoliths_with_room()` liest `monoliths_for()`). Die Sonden zielen
  jetzt auf das, was wirklich entscheidet (ein dritter Container; die MONOLITH-Keyword-Frage).
- **`test_reroll_scope.py` konnte einen verschwundenen Label gar nicht sehen** — jeder Abschnitt
  iteriert die Menge selbst. Die neun Mitglieder sind jetzt namentlich gepinnt.
- **Zwei Sonden zielten auf Suiten, die die Stelle nicht sehen können**, und sind umdeklariert:
  Reanimation Crypts' `is_busy` ist am Panel von 15.01 maskiert, und `test_event_chain_wiring.py`
  §10 prüft nur Tor → auflösbar, nie auflösbar → Tor.

**Im ECHTEN Spiel belegt** (`verify_necron_hypercrypt_legion.py`; Necrons als Player 1, Detachment
per Wrapper; `--neutralize` per Import-Hook, `main.py` auf der Platte unberührt):

| | gefixt | `--neutralize` |
|---|---|---|
| Hyperphasing hält die KI-Politik | ja | nein |
| Quantum Deflection Schuss/Fight, Entropic Damping Schuss | ja/ja, ja | nein |
| Reanimation Crypts hält den Boost | ja | nein |
| auf main()s Registry | alle drei | keiner |
| Phasen-Tor wartet auf Reanimation-Crypts-Würfel | ja | nein |
| Recall aus beiden Hooks, je eigenes Ledger | shooting, fight | nie |
| gezeichnet | RC Command, DC Charge, COS Movement (Arrival) | nie |
| Knöpfe außerhalb ihres WHEN | 0 | 0 |

**Gemessener Harness-Befund:** ein Lauf zeichnete Reanimation Crypts nie. selfplays eigene
„Next Phase"-Klicks treiben die echte Uhr über Runde 3 hinaus, und 20.03 zerstört dort jede noch
reservierte Einheit — auch die zwei gestagten. Die Sonde pinnt die Runde deshalb auf 2 und zählt
Reserve-Zerstörungen während des Stagings (0).

**Mitwandernde Pins:** `test_corsairs.py` (neun Labels), `test_return_placement.py` (Off-Board-Tür,
und `_constructs()` erkennt eine per `proactive_stratagems.add(...)` gebaute Controller-Instanz),
`test_necron_titans.py` (eigenes Gate-Lock), `test_detachments.py`, `test_force_dispositions.py`
(19), `test_necron_datasheets.py`, `ab_per_unit_offer.py`.

**Getestet:** `test_necron_hypercrypt_legion.py` **455/455**, `test_necron_detachment_ui.py`
**209/209**, `test_reroll_scope.py` **138/138**, `test_event_chain_wiring.py` **252/252**. Volle
Regression **231 Suiten, ~22124 Prüfungen, 230 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke`
komplett grün (alle neun schweren Skripte, inkl. `selfplay.py map2 1500` mit den Default-Armeen),
dazu `selfplay.py map2 1500` mit Necrons auf BEIDEN Seiten im Hypercrypt (exit 0; Runde 1 mit zwei
Zugenden, die KI-Politik nimmt dort bewusst nichts). `verify_rules_vs_engine.py` unverändert bei 70,
`fetch_datasheet_rules.py --offline` ohne Korpus-Diff (255 Dateien, nur das Abrufdatum).

**Offen:** Etappe 3 (Cryptek Conclave), erst nach „weiter".

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
- ~~**`plasmacyte` ist für beide Seiten unerreichbar**~~ — **erledigt in Necron-Etappe 3**:
  der Offer haengt jetzt an `FightController._start_fighting()`, dem einen Ort, an dem
  12.04s "selected to fight" fuer beide Wege dorthin passiert.

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
