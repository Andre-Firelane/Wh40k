# Hover-Datacard und Regel-Leser

Ausgelagert aus `CLAUDE.md` am 2026-09-17, Inhalt wörtlich. Wird NICHT automatisch geladen.
Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem Thema gehört VERDICHTET in den
passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine Zeile im Verzeichnis.

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
