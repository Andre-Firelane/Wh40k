# Armeelisten (2): Auswahl-Screen und Listen

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Armeen (armies/*.json) und Listenauswahl — Fortsetzung

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
- **Necrons (Hypercrypt Legion) — `necrons_hypercrypt`, 13 Listeneinträge, 9 Einheiten, 62 Modelle,
  1990 pts** (User-Export newrecruit.eu, 2000 pts, 2026-09-13). **Zweite Necron-Liste**, also die
  zweite Wahl in Stufe zwei. Hypercrypt Legion allein (2 von 3 DP), Reconnaissance →
  **Reconnaissance Sweep**. VIER Anbindungen: Plasmancer in die Immortals (10 Tesla Carbines),
  Technomancer in die 20 Warriors, Overlord (Resurrection Orb, Voidscythe) in 10 Lychguard
  (Hyperphase Sword + Dispersion Shield), Skorpekh Lord in 3 Skorpekh Destroyers (kein Plasmacyte).
  Allein: Void Dragon, Hexmark Destroyer (Lone Operative), 2 Lokhust Heavy Destroyers, Monolith
  (4 Death Rays), 10 Triarch Praetorians.
  - **Sie macht scharf, was vorher dormant by roster war:** Hyperphasing samt der sechs
    Hypercrypt-Stratagems, den Hexmark Destroyer, die Triarch Praetorians — und den **Monolith als
    erstes TITANIC-Modell eines ausgelieferten Rosters** (Eternity Gate, die TITANIC-Leser aus
    Etappe 0). Die vier Hypercrypt-Enhancements bleiben dormant, die Liste kauft keines.
  - **ZWEI Punkte-Abweichungen, beide bekannt** (`verify_rules_vs_engine.py`): Plasmancer 55 gegen
    gedruckte 60, Skorpekh Lord 90 gegen 95. Die gedruckte Seite stimmt mit dem Export überein, die
    Abweichung liegt also in der Engine-Transkription — die per stehender Entscheidung gewinnt.
  - **WARLORD (Overlord) ist ein belegter No-op**, die SECONDARY-Zeile des Exports eine
    App-Auswertung und keine Listendaten; beides steht nur in der `note`.
  - **Die sieben „dormant by roster"-Pins der Necron-Suiten lasen NUR `armies/necrons.json`** und
    blieben deshalb grün, als diese Liste Monolith, Hexmark und Praetorians fieldete — genau der
    Wechsel, für den sie gesetzt waren, war für sie unsichtbar (Fehlerklasse 17 in neuer Form: ein
    Pin, der nur EINEN Roster liest). Sie gehen jetzt über `testkit.lists_fielding()` (liest die
    GELADENEN Roster samt Leadern, nicht den JSON-Text) und nennen die fieldende Liste namentlich.
    Rot wurde zu Recht nur `test_necron_hypercrypt_legion.py` §17, der alle Listen las; umgedreht.
  - **Getestet:** neu `test_necron_hypercrypt_army.py` (**52/52**) — gegen den EXPORT, nicht gegen
    sich selbst: der Golden Master wird aus dem Build geschrieben und hätte eine falsche
    Transkription gesegnet. Neu `ab_necron_hypercrypt_army.py` (**7 A/B-Sonden, alle beißend**,
    Dateien per Hash zurückgestellt). Golden Master +84 Zeilen, keine bestehende bewegt.
    Im echten Spiel (`selfplay.py map2 2500`, die Liste auf beiden Seiten, exit 0):
    `[primary] Player 1 plays Reconnaissance Sweep`, alle vier Anbindungen je Seite, der Monolith
    aufgestellt bzw. von der KI per Deep Strike in Reserve genommen. **Grenze:** Hyperphasing
    feuert in diesen 8 Phasen nicht (es läuft erst am Ende eines Gegnerzugs); belegt ist es durch
    `test_necron_hypercrypt_legion.py` und `verify_necron_hypercrypt_legion.py`.
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
- **Orks — „Mecha Orks", 12 Einheiten, 78 Modelle, 1990 pts** (seit 2026-09-20, G6: die Liste des
  Users ersetzt die bis dahin minimal gehaltene; Key `orks` bleibt). **DREI Detachments zu genau
  3 DP** — Blitz Brigade + Da Big Hunt + Green Tide —, Take and Hold, und **vier Enhancements, die
  wirklich getragen werden**: Ferocious Show-off (Bigboss), 'Ardboyz (Zehner-Boyz), Boss Boomer
  (Battlewagon), Targetin' Gizmos (Gunwagon). **Ghazghkull ist der WARLORD** (Supreme Commander
  verlangt es, Da Boss zahlt dadurch 1 CP je Schlachtrunde) — die erste Liste, die das
  `warlord`-Feld benutzt. Attached: Warboss + Bigboss (SUPPORT) im 20er-Boyz-Mob (im Battlewagon,
  22/22), Big Mek in Mega Armour bei drei Meganobz (im Gunwagon, 8/12), Beastboss + Weirdboy
  (SUPPORT) bei Beast Snagga Boyz (zu Fuß — der Weirdboy ist kein BEAST SNAGGA, der Kill Rig nimmt
  nur solche); die zweite Beast-Snagga-Einheit fährt im Kill Rig (10/12). Die Transporte stehen
  NICHT im Export und sind in der `note` der Datei als Engine-Entscheidung benannt — sie sind es,
  die die zwei Fahrzeug-Enhancements überhaupt wirksam machen. Aus der Liste GEFALLEN (die
  Datenblätter bleiben gebaut und getestet): Warbikers, Stormboyz, Flash Gitz, Tankbustas, Deff
  Dread, ein zweiter Grotmob, Painboy, Warboss in Mega Armour.
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

