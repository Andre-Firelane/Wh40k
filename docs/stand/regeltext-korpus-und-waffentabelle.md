# Missionskarten, Waffentabelle, Regeltext-Korpus

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

## Die Hover-Datacard zeigt den GEDRUCKTEN Regeltext — Fortsetzung

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
bei allen stimmen die Zahlen exakt. `Grot-Smacka` ist mit dem Runtherd in Orks E3a entfallen.

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

### Das 2026-09-Layout (Orks zuerst), `--faction` und der Übergang

**Wahapedia hat die Datenblatt-SEITE umgebaut, sichtbar zuerst am neuen Ork-Codex** (User:
"Orks haben neue Regeln bekommen. Aktualisiere die Armeeregel, das Detachment und die Datasheets").
Der alte Parser las die neue Seite **ohne einen einzigen Fehler** und verlor dabei vier Dinge. Er
liest jetzt beide Layouts; die vier anderen Fraktionen (Cache noch alt) rendern gemessen
byte-identisch (In-Memory-Vergleich über 255 Dateien, 0 Differenzen). Plan und Etappen:
`C:\Users\Andre\.claude\plans\transient-munching-boot.md`.

- **Keyword-Leiste:** `dsLeftСolKW bkg1` — die Klasse bekam eine zweite Klasse; `KW_LEFT_RE`/
  `KW_RIGHT_RE` erlauben `(?:\s[^"]*)?`. Ohne das fehlt die KEYWORDS-Zeile lautlos.
- **CORE/FACTION** stehen in `table.dsCoreArmy` (Labels CORE ABILITIES / ARMY RULES) statt als
  Absatz. `extract_core_army()` löst die Tabelle VOR `parse_sections()` aus dem Body — sonst wird
  sie in MELEE WEAPONS verschluckt (Beastboss) oder an WARGEAR OPTIONS geklebt (Warboss) —, und
  `attach_core_army()` setzt `CORE: **…**`/`FACTION: **…**` an den Kopf von ABILITIES. Das ist die
  alte Korpusform, `rules_text` liest sie also unverändert. **Ein unbekanntes Label bricht ab.**
- **Hunter-Profile:** `tr.dsHunterKwRow` über einer Waffe wird `HUNTER: MONSTER/VEHICLE` als
  erstes Keyword der Zeile darunter. Bedingte Keywords (`LETHAL HITS: non-MONSTER/VEHICLE`) kommen
  ganz an. Fette Waffennamen (`b.dsWeaponName`) verlieren ihr `**…**`.
- **Damaged X** hat im neuen Layout keine `## Damaged:`-Sektion mehr: es steht als CORE-Keyword
  (`Damaged 6`) und als `dsCharDamagedVal` am W-Wert; der Parser liest beides.
- **`"Psychic Abilities"`** gehört zu `rules_text.ABILITY_SECTIONS` (Kill Rig).
- **`--faction FOLDER`** (wiederholbar) holt nur diese Fraktionen. `rules/README.md` wird trotzdem
  neu geschrieben; die Zeilen der übrigen baut `_index_rows_from_disk()` von der Platte, also
  schreiben `--offline` und `--offline --faction orks` byte-identische READMEs.
- **Ein zurückgezogenes Detachment verliert seine Datei** — nur auf einem vollen Fraktionslauf
  (nie mit `--detachment`) und erst hinter `MIN_DETACHMENTS_PER_FACTION`, damit ein kaputter
  Download den Ordner nicht leert. Orks 2026-09: 5 weg, 7 neu, **15**; alle Fraktionen **58**.
- **War Horde druckt ZWEI Force Dispositions** ("Take and Hold; Purge the Foe"):
  `Detachment.force_dispositions` ist ein TUPEL, `force_disposition` eine Property auf den ersten
  Eintrag, `force_dispositions.from_printed_list()` liest die Zeile, und `detachments.py` prüft die
  Deklaration einer Liste gegen die VEREINIGUNG. Die Ork-Liste bleibt bei Take and Hold.
- **ÜBERGANG, bis die Datenblatt-Etappen landen:** der Korpus ist den gebauten Ork-Blättern
  VORAUS (E0: alle 17, E3a 12, E3b 8, E3c 6, E3d 1; **seit E3e keins mehr - `CORPUS_AHEAD` ist samt
  Wächtern und Sonden gelöscht, siehe `## Kill Rig`**). `test_weapon_characteristics.py` führte sie in `CORPUS_AHEAD` — ihre Abweichungen wurden
  GESAMMELT statt gefailt, und die Menge ist dreifach bewacht (nur `orks`; Anzahl ==
  `EXPECTED_AHEAD`; jedes gelistete Blatt MUSS noch abweichen, sonst raus). Jede Datenblatt-Etappe
  senkt die Zahl, die letzte löscht den Block samt drei Sonden. `verify_rules_vs_engine.py` meldet
  bis dahin mehr Differenzen: E0 **173** (106 Ork-Zeilen), E3a **133** (66), E3b **115** (48), seit E3c **100** (33). Seit E2 spielt die Engine
  denselben War-Horde-Text, den der Army-Rules-Leser zeigt.
- **Getestet:** `test_datasheet_rules.py` → **145/145** (neu §6: eine COMMITTETE, ERFUNDENE Fixture
  `testdata/wahapedia_new_layout_blocks.html` — nur Markup, kein GW-Text, weil `.cache/`
  gitignoriert ist —, derselbe Satz Zusicherungen am echten Ork-Korpus, und die README-Zeilen von
  der Platte durch den echten Writer gegen die committete Datei); `test_force_dispositions.py`
  **180/180**; `ab_weapon_characteristics.py` **19/19** (drei neue Sonden auf `CORPUS_AHEAD`).
  Volle Regression **233 Suiten, ~22305 Prüfungen, 232 grün / 0 rot / 1 bekannt**, `--smoke` grün.

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
