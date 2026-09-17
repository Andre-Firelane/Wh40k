# Orks: Codex 2026-09 (2)

Fortsetzung von `docs/stand/orks-codex-2026-09.md` (E1 bis E3c), angelegt am 2026-09-17, als die
erste Datei die 42.000-Zeichen-Grenze erreicht hätte. Wird NICHT automatisch geladen. Verzeichnis
und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den passenden
Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Ork-Fahrzeuge (2026-09-Codex): Warbikers, Deffkoptas, Trukk, Battlewagon, Deff Dread — Etappe E3d

Plan: `C:\Users\Andre\.claude\plans\transient-munching-boot.md`. Gedruckter Text in `rules/orks/*.md`,
jedes Modul trägt ihn im Docstring. `armies/orks.json` bleibt minimal lauffähig: **14 Einheiten,
101 Modelle, 2165 pts** (Battlewagon ohne 'Ard Case und Zzap Gun 160 → 150, Deff Dread 110 → 130,
Deffkoptas 140 → 160, beide Warbikers-Einheiten ohne Power Klaw 60 → 75; der Golden Master bewegt
nur diese Zeilen).

**Datenblätter:**
- **Warbikers:** Biker Nob (W4, 6+ Invul, Kustom Choppa + Dual Kombi-rokkit/Dakkagun als
  Zweiprofil-Kette, beide [ASSAULT]) + 2 bzw. 5 Warbiker (W3, Choppa, Dual Dakkagun). 75/140, eine
  Stufe. Kein Wargear mehr.
- **Deffkoptas:** 3 bzw. 6, jetzt MOUNTED statt VEHICLE, FLY, Deep Strike. Rokkit Launcha als Kette
  Blasta (S4) → Busta (S10 [LETHAL HITS]); je 3 Modelle eine Kustom Mega-blasta. Die Deffkopta-Choppa
  druckt WS 4+ (das Modell trägt 3+). 80/160, ab der dritten Einheit 90/170.
- **Trukk:** M12 T8 Sv4+ W10, Firing Deck 12, Deadly Demise D3 (echter Wurf), Kapazität 12 ORKS
  INFANTRY ohne JUMP PACK, MEGA ARMOUR zählt 2. Dual Big Shoota → Rokkit Launcha; Buzzsaw ODER
  Grabbin' Klaw als ZUSATZ zur Spiked Ram. 60, ab dem vierten 70.
- **Battlewagon:** T11 Sv3+ W16 OC5, **Damaged 6** (`damaged_threshold`, `_damaged_modifier()` liest
  ihn), Firing Deck 11, Deadly Demise D6, Kapazität 22 (MEGA ARMOUR/JUMP PACK je 2). Crushin' Bulk plus
  drei kostenlose Zusätze (Wreckin' Ball, 4 Big Shootas, Grabbin' Klaw). 150, ab dem dritten 160.
- **Deff Dread:** M8 T9 Sv2+ W8 OC3, WALKER, Deadly Demise 1, 60 mm. Big Shoota und Skorcha je gegen
  „one of the following" tauschbar. **Reihenfolge zählt:** die Big-Shoota-Tausche stehen zuerst, weil
  `build_squad()` in Listenreihenfolge anwendet und ein Tausch JEDE Kopie entfernt — „Skorcha → Big
  Shoota" zuerst hätte dem Big-Shoota-Tausch eine zweite Big Shoota zum Wegnehmen gegeben. 130, ab
  dem dritten 140.

| Fähigkeit | Träger | Modul | Naht |
|---|---|---|---|
| High-speed Carnage | Warbikers | `high_speed_carnage.py` | +1 S und D in `FightController._adjusted_weapon()` nach `charged_this_turn`, dritter Charge-Grant neben Tide of Muscle und Rokkit Charge |
| Deff from Above | Deffkoptas | `deff_from_above.py` | +1 Hit in `ShootingController._hit_modifiers()`, wenn `IngressController.ingressed_this_turn`; reaktiv nie |
| Aerial Manoover | Deffkoptas | `aerial_manoover.py` | Angebot am Ende-der-Fight-Phase-Block mit `mover_before`, `per_unit_offer`, `withdraw_to_reserves()` |
| Pilin' Out | Trukk | `pilin_out.py` | reaktiver RAPID-Disembark an drei Haken: `on_move_finished`, `on_ingress_resolved`, neu `on_disembark_resolved` |
| Mobile Fortress / Dread 'Ard | Battlewagon / Deff Dread | `damage_reduction.py` | `ranged_damage_reduction` bzw. `damage_reduction`, Boden 1 |

- **Pilin' Out ist eine PLATZIERUNG, kein `move_mode`** — deshalb KEIN Eintrag in
  `REACTIVE_MOVE_MODES`/`OUT_OF_PHASE_MOVE_MODES` (die Plan-Zeile nannte sie): ein Disembark läuft
  in diesem Repo über `SetupController` (PLACING), und darauf warten schon zwei Tore —
  `_has_unresolved_declaration()` in `main.py` und `_is_blocked()`s Fremd-Platzierung in der KI. Ein
  Eintrag, der nie der haltende Term sein kann, wäre ein toter Zweig. Die KI platziert ihre eigenen
  Insassen über `_maybe_resume_disembark_placement()` (gebaut für den Emergency Disembark).
  `start_disembark(squad, mode=RAPID)` nimmt den GEDRUCKTEN Modus statt `determine_mode()`s.
- **Eine Warteschlange, ein Insasse zur Zeit.** `SetupController` hat einen Slot; der nächste wird
  erst gefragt, wenn der offene Disembark AUFGELÖST ist. Dafür feuert `TransportController` jetzt
  `on_disembark_resolved(squad, confirmed)` synchron aus Confirm, Cancel und dem Ende des
  Combat-Hazard-Wurfs — kein Lückenframe. Derselbe Haken ist der dritte Auslöser („ein Feind hat
  seinen Disembark beendet").
- **Einmal pro Bewegungsphase gefragt:** „Stay put" (und ein abgebrochener Disembark) merkt sich die
  Einheit bis `reset_movement_phase()`, sonst fragte jede weitere KI-Bewegung in 8" erneut.
  „Innerhalb 8"" ist Kante zu Kante von einem lebenden Modell AUF DEM BRETT — das deckt auch die
  abgebrochene Ankunft ab (siehe unten).
- **KI:** `agent_driver.pilin_out_verdict()` — aussteigen nur, wenn die erwarteten Wunden gegen den
  Trukk seine Restwunden erreichen (ein Wrack heißt Emergency Disembark mit Hazard und Battle-shock).
  `aerial_manoover_choice()` ist `hyperphasing_choice()` ohne Deckel (nie wenn verloren, Garnison
  bleibt, weg bei halbierter Erwartung oder nichts zu tun). Beide injiziert, 0 API-Calls.
- **`strategic_reserves.withdrawal_is_doomed()`/`misses_next_arrival()`** — Extraktion am zweiten
  Leser (Hyperphasing, jetzt Aerial Manoover); `hypercrypt_hyperphasing.py` re-exportiert.
- **`damage_reduction.adjusted_damage(model, amount, weapon)`** — die Waffe reist mit, damit
  „RANGED attacks" beantwortbar ist; ohne Waffe zählt die Fernkampf-Hälfte nicht.
  `damage_reduction_label` nennt die Regel im Log (fünf Träger, vier Namen).
- **ZWEI echte Funde:**
  - **`disembarked_from_this_turn` wurde nie zurückgesetzt**, obwohl der Squad-Kommentar es
    versprach (dieselbe Klasse wie Scouts: ein Kommentar, den kein Code einlöst). Und der
    Rundenende-Sweep von `charge_locked_until_end_of_turn` lief nur über `ending_squads` — ein
    Pilin'-Out-Lock aus dem gegnerischen Zug hätte die Boyz auch im EIGENEN Zug am Charge gehindert.
    Der Sweep läuft jetzt über `state.all_squads()` und setzt beide Felder.
  - **`_matchup_hint` las nur das GETRAGENE Profil** einer Mehrprofilwaffe: die Deffkoptas glaubten,
    ihr Rokkit Launcha verwunde einen Ghostkeel auf 6 (Blasta S4) statt auf 3 (Busta S10). Jetzt
    `weapon_profiles.valued_profiles()` wie `damage_estimate` seit E3c.
- **Benannte Abweichungen/Grenzen:** die 75×42-mm-Ovale von Warbikers und Deffkoptas bleiben 0.98"
  (flächengleich wären 1.10"); „up to 4 Big Shoota" nur als alle vier; die zwei Trukk-Zusätze
  schließen sich nicht aus (dieselbe Lücke wie Tankbustas); der Rapid Disembark der Engine würfelt
  keinen Hazard (vorbestehend, alle teilen es); GHAZGHKULL THRAKA (4 Plätze) und DEDICATED TRANSPORT
  nicht modelliert.
- **Stillgelegt:** Drive-by Dakka, Grot Riggers, Ramshackle but Rugged (`game/drive_by_dakka.py`,
  `grot_riggers.py`, `ramshackle.py`; `ap_worsening.py` hat zwei Träger weniger), 'Ard Case, Zzap Gun,
  Killkannon, Lobba, Deff Rolla, Kopta Rokkits, Stompy Feet, Tracks and Wheels, `test_battlewagon.py`.
  Die zwei Engine-Mechanismen, die nur daran hingen — Würfel-STÄRKE (`strength_notation`) und ein
  BEPREISTES Gear — prüft `test_ork_wargear.py` jetzt an synthetischen Trägern mit den Zahlen der
  Zzap Gun.
- **Nachgezogen:** `test_army_select.py` (2165), `test_player2_army.py`, `armies/baseline.txt`,
  `test_close_quarters_shooting.py`, `test_explosives.py` (die Deffkoptas sind kein VEHICLE mehr —
  der engagierte-VEHICLE-Fall braucht eine Pistole), `test_melee_weapon_groups.py`,
  `test_ork_mobs.py`, `test_ork_war_horde.py`, `test_report_20260824.py` (Warbikers Ratio 0.48 →
  assault), `test_target_priority.py`, `test_transport_priority.py`, `test_unit_datacard.py`,
  `test_aeldari_detachment_stratagems.py`, `test_weapon_characteristics.py` (`CORPUS_AHEAD` nur noch
  Kill Rig), `test_event_chain_wiring.py` §8 (266 Prüfungen), fünf `measure_*.py` ohne die
  stillgelegten Optionen.

**Sonden:** `ab_ork_vehicles.py` (**49 Sonden, 50 Suite-Läufe, alle beißend, Restore byte-genau**).
Im ersten vollständigen Lauf bissen fünf nicht — alles Befunde über den TEST: drei stürzten die
Suite ab statt sie rot zu machen (`dm.options`/`dm.prompt` ohne offenen Prompt in
`test_ork_vehicles.py`; `_TAIL.split(call)[1]` in `test_event_chain_wiring.py` §8, wo ein fehlender
Aufruf schon oben rot ist), eine prüfte „nicht im EIGENEN Zug" mit den eingestiegenen Boyz als
Mover, die ohnehin nie auslösen, und eine fand ein ZWEITES Brett-Tor in `on_ingress_resolved()`,
das `transports_in_range()` schon hält — entfernt, die Sonde zielt jetzt auf den Filter dort.
**Prozess-Fund:** ein durch das Kompaktieren abgebrochener Sondenlauf ließ eine Sonde in der NEUEN,
ungetrackten `game/aerial_manoover.py` stehen, und `git grep "AB-PROBE"` sah sie nicht — ungetrackte
Dateien übergeht es. Die Restprüfung ist jetzt `git grep --untracked` (Treiber-Docstring).

**Getestet:** neu `test_ork_vehicles.py` (**147/147**, zehn Abschnitte — Datenblätter gegen die
Korpus-Keywords, Waffenketten und Wargear, Transport über `formations.embark_errors()` UND
`TransportController.can_embark()`, High-speed Carnage durch die echte Fight-Kette, Deff from Above
durch die echten Hit-Modifier, Mobile Fortress/Dread 'Ard durch eine echte
`DamageAllocationSession`, Aerial Manoover und Pilin' Out mit echtem
`SetupController`/`MovementController`/`TransportController` inklusive Warteschlange, Abbruch,
Combat-Hazard-Reihenfolge und KI-Pfad, dazu die AST-Pins in `main.py`). Volle Regression **236
Suiten, ~23039 Prüfungen, 235 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett grün,
`selfplay.py map2 1500` Orks gegen Necrons in beiden Sitzordnungen exit 0.
`verify_rules_vs_engine.py` **100 → 73** (Ork-Zeilen nur noch Kill Rig und die Warboss-Base),
`fetch_datasheet_rules.py --offline` ohne Diff, `measure_crowded_movement.py` unverändert gedrängt
**62 % / 210.2"**, isoliert **87 % / 292.3"** (schwächste Einheit: die Deffkoptas mit 38 %).

**Im ECHTEN Spiel belegt** (`verify_ork_vehicles.py map2`, Orks als Player 1; 13/13, unter
`--neutralize` 6/6 Abwesenheitsprüfungen):

| | gefixt | `--neutralize` |
|---|---|---|
| Pilin' Out an den drei Live-Haken, beide KI-Policies, IngressController am Schießen | ja | nein |
| Pilin' Out über `main()`s Move-Listener | gefragt, RAPID-Platzierung offen, KI 90 Frames gehalten (0 Player-2-Modelle bewegt), bestätigt, Charge-Lock, Resolved-Haken lief | kein Prompt |
| Aerial Manoover an `main()`s `advance_turn_phase()` | gefragt (auch die gelisteten Deffkoptas), in Strategic Reserves | kein Prompt, bleiben stehen |
| Rundenende-Sweep | Lock aus Player 2s Zug in Player 1s Zug weg | Lock überlebt |
| Deff from Above am Live-`ShootingController` | `[]` → `[-1]` | `[]` |

**Die Halte-Prüfung ist selbst A/B-belegt:** mit `_is_blocked()`s Fremd-Platzierungs-Zweig per
Import-Hook entfernt bewegte die KI während der offenen Platzierung **38** Player-2-Modelle und die
Prüfung fiel — „gehalten" heißt also nicht „die KI hätte ohnehin nichts getan".

GESTELLT: Orks als Player 1, ein gebauter Trukk mit Boyz in 8" einer Player-2-Einheit auf einem
Platz mit freiem Ausstiegsring, gebaute Deffkoptas am weitesten von Player 2, die Phase (Player 2s
Bewegung), der „Zug beendet"-Moment, die Platzierung der Boyz im Ring, der Sprung ans Ende von
Player 2s Fight-Phase im selben Frame wie das Bestätigen und die Ingress-Marke für D.
`--neutralize` nimmt die sechs Nähte per Import-Hook zurück.

## Kill Rig (2026-09-Codex): Beastscent, Warpath, der psychische Wurf — Etappe E3e

Plan: `C:\Users\Andre\.claude\plans\transient-munching-boot.md`. Gedruckter Text in
`rules/orks/Kill Rig.md`, jedes Modul trägt ihn im Docstring. **Damit stehen alle 17 gebauten
Ork-Datenblätter auf Codex-Stand.** `armies/orks.json` unverändert: **14 Einheiten, 101 Modelle,
2195 pts** (Kill Rig 145 → 175; der Golden Master bewegt nur diese zwei Zeilen).

**Datenblatt:** M10 T10 Sv3+ W16 Ld7+ OC5, **neu InSv 6+**, CORE Damaged 6 (vorher 1-5), Deadly
Demise D6, Feel No Pain 5+ (vorher 6+); KEYWORDS MONSTER; BEAST SNAGGA; PSYKER; TRANSPORT; WAGON
(KILL RIG entfällt). Transport **12** BEAST SNAGGAS INFANTRY (vorher 11). Waffen: 'Eavy Lobba jetzt
fest **A3** und [BLAST 2] (vorher D6 und [BLAST]), Wurrtower fest **A1 / D6** (vorher D3 und D6 als Würfe), Saw
Blades [CLEAVE 1] und [EXTRA ATTACKS] — alle drei Nahkampfwaffen sind jetzt [EXTRA ATTACKS], 04.01s
Einwaffen-Wahl betrifft keine. 175, ab dem dritten 185. **Benannt:** die Base bleibt 2.1" wie der
Devilfish (stehende User-Entscheidung, das Oval wären 2.68").

| Fähigkeit | Modul | Naht |
|---|---|---|
| psychischer Wurf | `psychic_roll.py` | drei Tore (nicht battle-shocked, Unstable-Energies-Budget, freier Würfel-Slot), sichtbarer W6, eine 1 über `battle_shock.set_battle_shocked()` |
| Warpath | `warpath.py` | Angebot in `FightController._start_fighting()` (wie Rokkit Charge), Grant pro Phase: Nahkampfwaffen mit [LETHAL HITS] und [PSYCHIC] |
| Beastscent | `beastscent.py` | neuer `TransportController.on_disembark_started`; Grant auf dem AUSSTEIGENDEN Trupp bis Zugende: +1 Verwunden gegen MONSTER/VEHICLE in beiden `_wound_modifiers()` |

- **Lesart des Wurfs (Plan-Entscheidung):** der Effekt kommt bei JEDEM Wurf, eine 1 macht
  zusätzlich battle-shocked. Der Aufrufer setzt den Grant also beim Benutzen; das Modul besitzt
  nur, was der W6 entscheidet. Der Wurf VERBRAUCHT die Psychic-Stufe, egal was fällt.
- **Unstable Energies ist nicht mehr ruhend:** Psyker-Stufe 1 gegen zwei Fähigkeiten der Stufe 1 —
  eine pro Schlachtrunde, Beastscent ODER Warpath, und das Budget ist die EINZIGE Einmal-Grenze.
  Ein `not is_active()`-Term in beiden `can_use()` war ein toter Zweig und ist wieder raus.
- **Beastscent: zwei Einheiten, zwei Rollen.** Wurf, Budget und Shock gehören dem Kill Rig, der
  Grant dem Passagier. „Your Movement phase" heißt Phase Bewegung UND Besitzer des Kill Rig am Zug.
  Ein nach dem Wurf abgebrochener Ausstieg behält den Grant (die Einheit WURDE ausgewählt) —
  benannt.
- **[PSYCHIC] auf einem NAHKAMPF-Angriff:** Regel 24.29s Modifier-Drop stand bisher nur in
  `shooting.py`, weil keine Nahkampfwaffe das Keyword druckte. `FightController._hit_modifiers()`
  nimmt jetzt die ANGEPASSTE Waffe (alle drei Aufrufer reichen sie), und ein beschädigter Kill Rig
  unter Warpath verliert seinen eigenen Damaged -1 — im echten Hit-Roll gemessen (4+ → 3+) und im
  Hit-SCHRITT, der seine Schwelle selbst rechnet.
- **DER FUND: ein Würfel-Slot, zwei Würfe.** `DiceManager` hält genau einen offenen Wurf, und ein
  zweites `roll()` ersetzt den ersten spurlos. Warpath würfelt bei „selected to fight" —
  `_handle_fight()` der KI warf direkt danach im selben Aufruf den Hit Roll. Im echten Spiel
  belegt (per Import-Hook ohne den neuen Wächter): `['Psychic roll: Warpath …', 'Hit Roll: Saw
  Blades (6 attack(s))']` in EINEM Aufruf, und die 1 hat den Kill Rig nie geschockt, weil die
  Bestätigung den Hit-Würfel las. Zwei Nähte: `_handle_fight()` hört nach `select_to_fight()` auf,
  solange ein Wurf offen ist (der Resume-Zweig macht weiter), und `PsychicRollController` löst einen
  ERSETZTEN Wurf mit seiner eigenen Augenzahl auf und schreibt eine `[psychic roll]`-Dateizeile.
  Beastscents KI würfelt nie bei einem Combat- oder Emergency-Ausstieg: deren Hazard-Wurf folgt im
  selben KI-Aufruf auf die Bestätigung — benannt, eine Policy-Grenze statt Regel.
- **KI (0 API-Calls):** `warpath_verdict()` würfelt immer, außer der Kill Rig steht in
  Objective-Reichweite (eine 1 → OC 0). `beastscent_verdict()` würfelt, wenn ein feindliches
  MONSTER/VEHICLE in 15" steht (3" Ausstieg + 12"), nicht auf einem Objective, nie Combat/Emergency.
- **Stillgelegt:** Spirit of Gork (`game/spirit_of_gork.py`, zwei Squad-Flags, das Profil-Flag, die
  `main.py`-Verdrahtung, `test_kill_rig.py`); damit ist auch die benannte Lücke 2 in
  `## Unit Statistics` weg (Spirit of Gork schrieb `current_wounds` direkt).
  **`CORPUS_AHEAD` ist gelöscht** — samt drei Wächtern und drei Sonden in
  `ab_weapon_characteristics.py`: jede Ork-Waffe wird wie jede andere geprüft, null Abweichungen.
- **Nachgezogen:** `test_player2_army.py` (2195, „11 of 12"), `test_army_select.py`,
  `armies/baseline.txt`, `test_crit_labels.py` (Hit 'Em Harder statt Spirit of Gork als
  [LETHAL HITS]-Quelle), `test_ork_army_rules.py`. **Drei veraltete Sondenanker aus E3d**, die
  dessen Lauf nicht gesehen hatte (nur die eigenen Treiber per `--check` geprüft): Waaagh!-Flag
  (`ab_ork_army_rules.py`, jetzt die Gretchin-Zeile), `withdrawal_is_doomed` nach
  `game/strategic_reserves.py` (`ab_necron_hypercrypt_legion.py`), Arrogant Invulnerability als
  jetzt ERSTER AP-Schritt (`ab_ork_mobs.py` — die alte Ersetzung `pass` hätte `ap` ungebunden
  gelassen und abgestürzt statt rot gemacht). Alle drei beißen wieder. **Lehre:** nach einer Etappe
  JEDEN Treiber mit `--check` fragen, nicht nur den eigenen.

**Getestet:** neu `test_ork_kill_rig.py` (**108/108**, acht Abschnitte - Datenblatt gegen die
Korpus-Keywords, die sechs Waffen, Transport an 18.01 UND 18.02 samt A/B der BEAST-SNAGGA-Hälfte,
der psychische Wurf mit allen drei Toren und dem ersetzten Wurf, Warpath durch einen echten
`FightController` bis in den Hit-SCHRITT, Beastscent durch echten `TransportController`/
`SetupController` und beide `_wound_modifiers()`, die KI samt `_handle_fight()`, AST-Pins in
`main.py`) und `ab_ork_kill_rig.py` (**48 Sonden, 49 Läufe, alle beißend, kein Rest**). **Eine biss
zuerst nicht, ein Befund über den TEST:** „jeder TRANSPORT hat Beastscent" blieb grün, weil der
Battlewagon der Szene keine Psyker-Stufe hat und das Budget-Tor zuerst ablehnte - die Szene nimmt
jetzt einen PSYKER-Battlewagon (Unterklasse nur auf diesem Token). Volle Regression **236 Suiten,
~23019 Prüfungen, 235 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett grün,
`selfplay.py map2 1500` Orks gegen Necrons in beiden Sitzordnungen exit 0 (der MockAgent erreicht
keine Fight-Phase mit dem Kill Rig - dafür ist die Laufzeit-Sonde da). `verify_rules_vs_engine.py`
**73 → 68** (einzige Ork-Zeile: die Warboss-Base, eine benannte Entscheidung),
`fetch_datasheet_rules.py --offline` ohne Diff, `measure_crowded_movement.py` unverändert gedrängt
**62 % / 210.2"**, isoliert **87 % / 292.3"**.

**Im ECHTEN Spiel belegt** (`verify_ork_kill_rig.py map2`, Orks als Player 1; 14/14, unter
`--neutralize` 6/6 Abwesenheitsprüfungen; in beiden Aufstellungs-Reihenfolgen gelaufen):

| | gefixt | `--neutralize` |
|---|---|---|
| Warpath am Live-`FightController`, Beastscent am Live-`TransportController`, beide auf `main()`s Wurf | ja | nein |
| Beastscent beim Ausstieg (der Aufruf des Panel-Knopfs) | gefragt, W6 (4) von `main()`s Bestätigung aufgelöst, Grant, Stufe verbraucht, +1 Verwunden gegen den MONSTER im Live-`ShootingController`, Warpath für diesen Kill Rig gesperrt | kein Prompt |
| Warpath bei „selected to fight" | gefragt, die 1 schockt über `main()`s Bestätigung, Live-Kette [LETHAL HITS]+[PSYCHIC], Damaged -1 fällt aus den Live-Hit-Modifiern | kein Prompt |
| Zugende über `main()`s `advance_turn_phase()` | beide Grants weg | von Hand gestellt, beide überleben |
| KI-`_handle_fight()` an den Live-Objekten | wählt den Kill Rig, im Aufruf fällt NUR der psychische Wurf, `main()` löst ihn auf | kein psychischer Wurf |

**Der KI-Wächter ist eigens A/B-belegt:** mit nur dem neuen Stopp in `_handle_fight()` per
Import-Hook entfernt fielen im selben Aufruf `Psychic roll: Warpath` UND `Hit Roll: Saw Blades (6
attack(s))`, der offene Wurf war der Hit Roll, und die Prüfung fiel. Vor der Härtung des
Controllers blieb dabei auch der Shock auf der 1 aus.

GESTELLT: Orks als Player 1, drei gebaute Kill Rigs (A mit Beast Snagga Boyz, B mit 5 Wunden an C
von Player 2), auf dem freiesten Boden außerhalb jeder Engagement Range und mit C außerhalb jeder
Objective-Reichweite, die Phasen, der Start des Fight-Schritts ohne Pile-In-Prüfung, die
W6-Augen (4 und 1), die Antworten des Menschen, das Abbrechen von Ausstieg und Kampf nach dem
Lesen, ein `advance_turn_phase()` und der `_handle_fight()`-Aufruf. **Der Zugende-Check fragt die
Uhr**, nicht den nächsten Besitzer: war der gestellte Zug in Wahrheit Player 2s zweiter der Runde,
gehört der nächste wieder Player 1 - so ist die erste Fassung der Prüfung in einem von drei Läufen
fälschlich rot geworden.
