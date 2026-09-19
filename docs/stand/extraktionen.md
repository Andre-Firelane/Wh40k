# Extraktionskatalog

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Extraktionskatalog (aus Fehlerklasse 10 ausgelagert)

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
    Seither **`game/damage_pick.py` (37.)** — „welcher Controller wartet auf einen
    MODELL-Klick, und für WEN", gelesen vom linken Panel, dem Brett-Highlight, der KI-Pause und
    dem Klick-Zweig. Die Liste ist NICHT neu — sie ist `_any_pending_damage_choice()`s
    vorhandenes Tupel, eine Ebene höher gehoben; neu ist, dass das PANEL sie auch liest. Es
    fragte 2 von 27, und die übrigen 25 fielen durch die ganze `_draw_dispatch()`-Kette auf den
    nächsten passenden Zweig (siehe `## Fünf Meldungen aus einer Partie`).
    Seither **`game/base_contact.py`** — „ist dieses Modell in Basenkontakt, und darf dieser
    Zug es deshalb nicht bewegen", gelesen von `clamp_move()`, `is_movable()`, der KI-Spreizung,
    dem Renderer, dem Panel und der Logzeile. Keine Extraktion im engeren Sinn, sondern eine
    HAUSREGEL, die es an einer Stelle als getarnte Optimierung schon gab.
    Seither **`mission_context.objective_action_targets_for()` (38.)** — „auf welchen
    Objectives darf diese Einheit eine OBJECTIVE ACTION beginnen", gelesen von Cleanse
    (Secondary) und Secure Asset (Primary), die dieselbe UNITS- UND dieselbe COMPLETES-Zeile
    drucken und beide eine eigene Kopie hatten. **Beide Kopien waren gleich falsch**, und das
    ist die lehrreiche Hälfte: das START-Tor las die 3"-Fassung von „within range of an
    objective", das COMPLETES-Tor die 14.02-Fassung — dieselbe Frage, zwei Antworten, drei Zoll
    auseinander (siehe `## Cleanse bot einen Knopf an, der nicht auszahlen konnte`).
    Seither **`attached_units.model_has_datasheet_keyword()` (39.)** — „traegt DIESES
    MODELL dieses Datenblatt-Keyword", gefragt an der KOMPONENTE, aus der es stammt.
    `cryptothralls.py` hatte es fuer „that CRYPTEK model" ausgeschrieben, Nekrosor
    Ammentars Infectious Murder-madness fragt dasselbe fuer DESTROYER CULT. Es KANN nicht
    `unit_has_datasheet_keyword()` mit einem Modell sein — ein Modell weiss nicht, von
    welchem Datenblatt es kommt.
    Seither **`game/reactive_bodyguard_shooting.py` (40.)** — „einmal pro Zug, wenn eine
    befreundete Einheit in der Naehe beschossen wird, schiess danach zurueck", gelesen von
    Kroot Packmates (T'au, 6", KROOT INFANTRY) und Multi-threat Eliminator (Necrons, 3",
    NECRONS). Der SCHWANZ war schon geteilt (`start_reactive_shooting(restrict_to=)`), der
    vierteilige AUSLOESER nicht — und den falsch zu haben ist nicht hypothetisch: die erste
    Fassung von Kroot Packmates lieferte mit dem falschen `target_reactions`-Vertrag aus und
    liess jedes Spiel abstuerzen, sobald irgendeine Einheit ein Schussziel waehlte.
    Seither **`game/cover_denial.py` (41.)** — „nachdem dieses Modell geschossen hat, kann
    EINE getroffene Feindeinheit bis zum Ende der Phase keine Deckung haben", gelesen vom
    Defiler (Barrage of Filth) und vom Triarch Stalker (Targeting Relay), die denselben Satz
    unter zwei Namen drucken. Geteilt ist genau das, was man zweimal subtil falsch macht: die
    Kandidaten sind, was WIRKLICH getroffen wurde; „select" ist keine Wahl über das OB; die
    Marke lebt eine PHASE; und eine befreundete Einheit ist nie Kandidat. Eine Unterklasse
    besitzt ZWEI Knöpfe (Profil-Flag, gedruckter Name) — als Klassenattribute, damit ein
    Vergessen LAUT scheitert. **Und `_compute_benefit_of_cover()` hat EINEN Leser** statt
    zweier `if`s (`cover_denial.denied(target, (…, …))`), also können die zwei sich nie darüber
    uneinig werden, was „denied" heißt.
    Seither **`game/pinned.py` (42.)** — der STATUS „pinned" (−2 Move, −2 auf Charge-Würfe),
    gelesen vom Night Spinner (Monofilament Web) und vom Geomancer (Tectonic Reverberations).
    Geteilt sind Status, Penalties und die zwei SEAMS (`coldstar.py`s Move-Fold,
    `charge.py`s Wurf-Fold); NICHT geteilt ist die UHR — der eine läuft bis zum Beginn des
    nächsten ZUGES, der andere bis zur nächsten MOVEMENT-Phase, also trägt der Pin sein
    Ablaufdatum bei sich (`UNTIL_TURN`/`UNTIL_MOVEMENT`) und `clear_at()` räumt genau eine
    Grenze. `monofilament_web.py` re-exportiert, seine Aufrufer bewegen sich nicht.
    Seither **`game/fnp_aura.py` (43.)** — „eine Feel-No-Pain-Aura", gelesen von Nekrosor
    Ammentars Nullstone Field und den zwei Spyder-Wargear-Items. Fünf Knöpfe (Flag, Schwelle,
    Reichweite, Squad-Flag, welche Einheiten sie deckt) plus der eine, der zwei verschiedene
    REGELN daraus macht: `mortal_or_psychic_only`. **Jede Aura stempelt ihr EIGENES
    Squad-Flag**, sonst überschreiben zwei einander auf einem Brett.
    Seither **`game/retinue.py` (44.)** — rule 19.01s DRITTE Anbindungsform, gelesen von den
    Cryptothralls (Cryptek Retinue) und den Canoptek Tomb Crawlers (Canoptek Retinue), die
    denselben Absatz drucken. Der eine Unterschied ist ein Wort („a CRYPTEK model" gegen „a
    CRYPTEK INFANTRY model") und heute ein gemessener No-op — trotzdem als zwei Prädikate
    geschrieben, weil sie sich beim ersten nicht-INFANTRY-Cryptek trennen.
    Seither **`objectives.model_is_within_range_of_objective()`** — dieselbe Distanz, an EIN
    MODELL gefragt. Vierzehn Aufrufer fragen sie pro SQUAD; Obelisk Node Control ist der erste,
    der „while THIS MODEL is within range" druckt. Die Squad-Fassung ist jetzt eine Faltung
    darüber, also können die zwei sich nie darüber uneinig werden, was „within range" ist —
    dieselbe Teilung wie `unit_`/`model_has_datasheet_keyword()`.
    Seither **`weapons.anti_entries()` (31.)** — „wie liest man `WeaponProfile.anti`", gelesen von
    `shooting._wound_crit_threshold()` und von `weapons.printed_keywords()`; es liegt jetzt bei
    dem Feld, das es liest, und `shooting.py` re-exportiert es unter dem alten privaten Namen,
    also bewegt sich keine Aufrufstelle (siehe `## Die Waffentabelle druckte auch die KEYWORDS
    nicht`).
    Seither **`game/heal.py`** — Kernregel 02.02.04 (heilen, dann nicht-CHARACTER
    wiederbeleben), aus `reanimation_protocols.reanimate()` gehoben, als Crude Surgery der
    zweite Konsument wurde; `reanimation_protocols` re-exportiert. Daneben
    **`game/per_army_round_limit.py`** — „einmal pro Schlachtrunde pro Armee" samt Spiegel auf
    ein gespeichertes Squad-Flag, gelesen von beiden Boss-Motivationen.
    Seither **`strategic_reserves.withdrawal_is_doomed()`/`misses_next_arrival()`** (Orks E3d) -
    die Regel-20.03-Fragen zu einem Rückzug am Zugende des Gegners, aus Hypercrypt Legions
    Hyperphasing gehoben, als Aerial Manoover der zweite Leser wurde; `hypercrypt_hyperphasing`
    re-exportiert. Und **`game/psychic_roll.py`** (Orks E3e) - der psychische Wurf der Orks
    (nicht battle-shocked, Unstable-Energies-Budget, freier Würfel-Slot, eine 1 über die eine
    Shock-Tür), von Beginn an von zwei Fähigkeiten gelesen (Beastscent, Warpath). Die leicht zu
    verfehlende Hälfte: ein ERSETZTER Wurf - der Controller löst mit seiner eigenen Augenzahl auf,
    statt den Würfel eines fremden Wurfs zu lesen.
    Dann der **`WarpathController`** (Mecha Orks G1) - kein neues Modul, sondern der Rahmen des
    Kill-Rig-Warpath, parametrisiert (`ABILITY_FLAG`, `ACTIVE_FLAG`, `EFFECT_TEXT`), als der
    Weirdboy dieselbe Fähigkeit unter demselben Namen mit anderer Wirkung druckte; die Wirkung
    selbst steht in `game/weirdboy_warpath.py` (Fehlerklasse 11). Die leicht zu verfehlende
    Hälfte: die ANKER des Kill-Rig-Sondentreibers - der Umbau hat jede sondierte Zeile wörtlich
    stehen lassen, die 14 Warpath-Sonden beißen weiter.
    Mit Green Tide (Mecha Orks G3) drei: **`game/save_characteristic.py`** - der Save-KENNWERT
    samt Ersetzungen (Shieldvanes, 'Ardboyz), am ZWEITEN Ersetzer; sechs Leser (Wurf und Panel,
    Zuteilung, `defender_soak()`, Beobachtung, Matchup-Hinweis, Datacard). Die leicht zu
    verfehlende Hälfte: die ersten fünf sahen die Shieldvanes nie - der erste Ersetzer war nur am
    Wurf verdrahtet; `test_event_chain_wiring.py` §30 nennt jeden verbleibenden Direktleser.
    **`attached_units.unit_datasheet_names()`/`unit_is_datasheet()`** - „welche Datenblätter
    stecken in dieser (angeschlossenen) Einheit", an der DRITTEN Kopie (`enhancements._unit_is`,
    `far_reaching_doom._datasheet_names`); für Datenblattnamen in Großbuchstaben (BOYZ), die kein
    Keyword der Zeile sind. **`dice_notation.plus()`** - „+N auf eine Würfelnotation", an der
    VIERTEN Kopie; Psychic Communion hatte dabei die Würfel-ANZAHL fallen lassen (2D6 → D6,
    latent, weil ihr Träger 1W6 würfelt).
