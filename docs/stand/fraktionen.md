# Fraktionen: Übersicht

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

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
  Armour), Painboy. Armeeregel Waaagh! (seit E1 der 2026-09-Codex: riled up + War Cry, siehe
  `## Die Ork-Armeeregel`), Detachment "War Horde" (seit E2 Codex-Stand: Get Stuck In, vier Enhancements,
  sechs Stratagems, siehe `## War Horde`); seit E3a stehen Boyz, Beast Snagga Boyz, Stormboyz,
  Gretchin und Meganobz auf Codex-Stand (siehe `## Ork-Mobs`), seit E3b auch Warboss, Warboss in
  Mega Armour, Beastboss und Painboy (siehe `## Ork-Charaktere`), seit E3c Flash Gitz und
  Tankbustas (siehe `## Ork-Spezialisten`). Komplette
  Punkteliste (58 Einträge).
- **Aeldari** — Guardian Defenders, Storm Guardians, Striking Scorpions, Howling Banshees, Warp
  Spiders, Dire Avengers, Fire Dragons, Dark Reapers, Shining Spears, Windriders, Warlock Skyrunners,
  Rangers, Shroud Runners, Swooping Hawks, Wraithguard, Falcon, Warlock Conclave, Farseer, Eldrad
  Ulthran, Avatar of Khaine, Asurmen, Jain Zar, Lhykhis, Baharroth. Armeeregel **Battle Focus**
  (eigenes Token-Konto, 6 Agile Manoeuvres), Detachment **Seer Council** (Strands of Fate + 6
  Stratagems). Punkteliste bewusst NUR für gebaute Einheiten (ein KeyError heißt "noch nicht
  transkribiert", nicht "kostenlos").

- **Necrons — 46 von 64 Datenblättern**, und der Nachzug ist damit FERTIG
  Nachzug (siehe `## Die restlichen Necron-Datenblätter`): Necron Warriors, Immortals,
  Lychguard, Skorpekh Destroyers, Lokhust Destroyers,
  Lokhust Heavy Destroyers, Canoptek Wraiths, Doomsday Ark, Overlord, Plasmancer, Technomancer,
  Illuminor Szeras, C'tan Shard of the Void Dragon, Skorpekh Lord, Lokhust Lord;
  dazu Etappe 1 **Chronomancer, Psychomancer, Orikan The Diviner**, Etappe 2
  **Deathmarks, Flayed Ones, Cryptothralls, Tomb Blades** und Etappe 3
  **Hexmark Destroyer, Ophydian Destroyers, Nekrosor Ammentar**, Etappe 4
  **Triarch Praetorians, Triarch Stalker** und Etappe 5 **Canoptek Scarab Swarms,
  Canoptek Spyders, Canoptek Doomstalker, Canoptek Reanimator, Canoptek Macrocytes,
  Canoptek Tomb Crawlers, Geomancer** und Etappe 6 **C'tan Shard of the Deceiver,
  C'tan Shard of the Nightbringer, Transcendent C'tan** und Etappe 7 **Royal
  Warden, Overlord with translocation shroud, Imotekh The Stormlord, Trazyn The
  Infinite** und Etappe 8 **Catacomb Command Barge, Annihilation Barge, Ghost Ark**
  und Etappe 9 **Monolith, The Silent King**.
  Armeeregel
  **Reanimation Protocols**
  (`game/reanimation_protocols.py`), Detachment **Awakened Dynasty** (Command Protocols + alle
  sechs Stratagems; die vier Enhancements bleiben reine Daten — anders als die T'au, deren
  neunzehn alle verdrahtet sind).
  Punkteliste bewusst NUR für gebaute Einheiten. **Die erste Fraktion, die die KI spielen soll und
  die nicht Player 2s Default ist** — umschaltbar über `config.PLAYER2_ARMY` / `--army2 necrons`.
  **Skorpekh Lord, Lokhust Lord und alle 26 Datenblätter der Etappen 1-7 stehen in KEINER
  Demo-Armee** — angelegt, getestet, *dormant by roster*, und diese Abwesenheit ist gepinnt,
  damit ein späteres Fielden eine sichtbare Änderung ist.

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
    MENGE ist). Die Form ist "die 1en ODER der ganze Wurf" — "instead" macht die beiden zu
    Alternativen, und mit 1en auf dem Tisch ist "Keep result" keine legale Antwort. **Der Zusatz
    "nie nur die Fehlschläge" stand hier und war falsch** (gemeldet 2026-09-11): der gedruckte Satz
    erlaubt jede Teilmenge des Wurfs, und die Fehlschlag-Option wird bei allen sieben angeboten. **`game/fight.py` hatte gar keinen automatischen 1er-Reroll** und hat ihn jetzt
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
    - **KI-Pfade sind für die drei reaktiven schon da** (`auto_players`, Muster des mit Orks E2 stillgelegten `'Ard as Nails`):
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
      `auto_players` im eigenen Controller (Muster des stillgelegten `'Ard as Nails`) und braucht in `ai/`
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
  - **Tank Hunters existierte ZWEIMAL unter einem Namen** (seit Orks E3c nur noch einmal: der
    Ork-Codex hat die Tankbusta-Fassung durch Hunter-Profile ersetzt). Der Myphitic Blight-hauler druckt
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
    inzwischen da** (`Deathguard_Logo.png`) — wieder der Ordner: ein Wort mit Unterstrich, wo die
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
      ihre Ziel-Tests waren Komplemente. Monster Hunters ist mit Orks E3a entfallen; der
      gemeinsame Schritt heißt jetzt `hit_optional_reroll`.
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
