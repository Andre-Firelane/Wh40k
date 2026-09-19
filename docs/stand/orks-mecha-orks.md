# Orks: Mecha Orks (ab G2)

Fortsetzung von `docs/stand/orks-codex-2026-09-2.md` (dort steht G1: Bigboss, Weirdboy, Gunwagon),
angelegt am 2026-09-19, damit die restlichen Etappen des Plans
`C:\Users\Andre\.claude\plans\mecha-orks.md` die 42.000-Zeichen-Grenze jener Datei nicht sprengen.
Wird NICHT automatisch geladen. Verzeichnis und Pflegeregeln: `CLAUDE.md`. Neuer Stand zu diesem
Thema gehört VERDICHTET in den passenden Abschnitt hier; ein neuer `##`-Abschnitt braucht eine
Zeile im Verzeichnis.

## Mecha Orks G2: Big Mek in Mega Armour, Ghazghkull Thraka, der Warlord (2026-09-19)

Gedruckter Text in `rules/orks/Big Mek In Mega Armour.md` und `Ghazghkull Thraka.md` (per `--only`
in derselben Sitzung), jedes Modul trägt ihn im Docstring. `armies/orks.json` UNVERÄNDERT (G6).

**Datenblätter:**
- **Big Mek in Mega Armour** (90, App-Stand 80): M5 T6 Sv2+ W5, 40 mm, WS3+/BS4+, LEADER für Meganobz
  (und Mek Gunz, nicht gebaut). Alle Waffen außer der neuen Tellyport Blasta sind vorhandene Zeilen
  mit gleichen Zahlen (Kustom Shoota/Kombi-weapon als Meganob-Ketten, Kustom Mega-blasta, Killsaw,
  Power Klaw). Wargear: Tellyport Blasta als Zusatz, Kustom Force Field als Gear-Item
  (`Token.kustom_force_field`) — das „one of" zwischen beiden ist nicht erzwungen (die benannte
  Tankbustas-Grenze); die drei Kustom-Shoota-Tausche teilen den Cursor.
- **Ghazghkull Thraka** (300, App-Stand 235 für zwei Modelle): EIN Modell (Makari ist jetzt eine
  Fähigkeit), 80 mm, M8 T10 Sv2+ W16 OC4 InSv 4+, EPIC HERO, kein Leader-Abschnitt. Mork's Roar als
  Zweiprofil (Aimed → Point Blank 2D6+2 TORRENT), Adamantine 'Eadbutt ([EXTRA ATTACKS], schwingt
  neben der Klaw), Gork's Klaw. **Transport:** 4 Plätze in Battlewagon/Gunwagon
  (`transport.GHAZGHKULL_CAPACITY_COST`, global wie die MEGA-ARMOUR-Regel), der Trukk verweigert ihn
  (`transport_excludes`) — beides war seit E3d als „nicht modelliert" benannt.

| Fähigkeit | Träger | Modul | Naht |
|---|---|---|---|
| More Dakka | Big Mek | `more_dakka.py` | [IGNORES COVER] + riled up [SUSTAINED HITS 1] in `ShootingController._adjusted_weapon()`; das Cover-Tor liest die Kette (siehe unten) |
| Kustom Force Field | Big Mek (Gear) | `kustom_force_field.py` | 4+ InSv gegen Fernkampf für die EINHEIT in `effective_invulnerable_save()`, 19.04 komponentenweise |
| Fix Dat Armour Up | Big Mek | `fix_dat_armour_up.py` | Crude Surgerys Heilung (`heal.py`, Platzierer), aber einmal pro Schlacht → ANGEBOTEN am Beginn der eigenen Command-Phase, „Save it for later" |
| Da Grand Warlord's Ladz | Ghazghkull | `grand_warlords_ladz.py` | sechste Quelle in `conditional_lone_operative.SOURCES` |
| Makari, Hoist Dat Banner! | Ghazghkull | `makari.py` | Registry-Knopf ohne CP, Einheiten-Pick bis zur Rundenzahl, einmal pro Schlacht pro Armee |
| Prophet of da Great Waaagh! | Ghazghkull | `prophet_of_da_great_waaagh.py` | Aura 6", +1 Treffer/+1 Verwunden im Nahkampf in `FightController`, eigene Einheit zählt (Shadowsun-Lesart) |
| Da Boss (Armeeregel) | Warboss, WMA, Beastboss, Ghazghkull | `da_boss.py` | `sync_battle_round()` am Schlachtbeginn und an jeder Phasengrenze, idempotent |

**DER WARLORD (`game/warlord.py`)** — die Engine hatte bis hierher keinen, und jede Warlord-Regel
war ein dokumentierter No-op. Jetzt:
- Ein Listeneintrag (Einheit oder Leader) darf `"warlord": true` tragen; der Builder schreibt es in
  Pass 2 auf das MODELL (`Token.warlord`), solange der Charakter noch eigener Trupp ist — nur auf
  CHARACTER-Modelle (die Menhire der Silent King bleiben unmarkiert). Gespeichert wird nichts: ein
  Load baut die Armee aus der Liste.
- Beim Laden geprüft: höchstens einer, ein CHARACTER, kein „cannot be your WARLORD" (C'tan),
  **Supreme Commander** muss es sein — nennt die Liste niemanden, IST er es (Ghazghkull, Shadowsun,
  The Silent King; die beiden letzten waren dokumentierte No-ops und tragen jetzt das Flag), nennt
  sie einen anderen, wird sie abgelehnt. **Keine ausgelieferte Liste nennt einen Warlord** — alle
  Warlord-Regeln bleiben für sie ruhend, auch Da Boss für die bisherige Ork-Liste (G6 bringt
  Ghazghkull). Reanimation Crypts bleibt per User-Entscheidung beim Ziel-No-op.
- **Da Boss:** ein LEBENDER Warlord mit der Fähigkeit (in Reserve zählt er, der Text sagt nicht „on
  the battlefield"). Der CP läuft über `gain_cp()` und damit unter den +1-Bonus-CP-Deckel der
  Hausregel. Die bezahlte Runde steht auf der Einheit (`Squad.da_boss_round`, gespeichert): **der
  Deckel-Zähler wird NICHT gespeichert** (`scene_io` hält nur die CP-Stände), nach einem Laden mitten
  in der Runde stünde sonst ein zweiter CP offen. Die A/B-Sonde fand das: der Deckel verdeckte die
  Idempotenz im Test, erst ein frisches CP-Ledger zeigte, welcher Term hält.

**DER COVER-TOR-FIX (vorbestehend, beim Bau von More Dakka gefunden).** Beide Leser von
[IGNORES COVER] — der Cover-Split in `_dispatch_group()` und der Benefit-of-Cover-Term in
`_hit_modifiers()` — bekamen die GEDRUCKTE Waffe. Jeder Ketten-Grant (Pech'ra, Faolchu, Oversight
Drone, Nebuloscope, Preternatural Precision) kam dort nie an; ihre Suiten prüften nur das Flag an der
Kopie. Gemessen: aktive Oversight Drone → Kopie `ignores_cover=True`, Hit Roll trotzdem „+1 (Benefit
of Cover)". Beide Leser bekommen jetzt `self._adjusted_weapon(...)`; Wächter
`test_event_chain_wiring.py` **§29** (§27s Form), A/B belegt, dazu `## Regelengine — Schießen`.

- **Makari (Lesarten):** Kandidaten sind befreundete Einheiten mit der Waaagh!-Fähigkeit, die der
  Grant VERLÄNGERN würde (Fehlerklasse 5) — auch Fahrzeuge (im Spiel gezogen: der Battlewagon). Der
  erste Pick verbraucht die Nutzung, Abbrechen davor nicht. Ein gewählter Trupp fällt von selbst aus
  den Kandidaten, weil der Grant seine Frist genau auf diese setzt — ein eigener „schon gewählt"-Term
  war ein toter Zweig (die Sonde darauf biss nicht) und ist entfernt.
- **KI (0 API-Calls):** Fix Dat per injiziertem `fix_dat_armour_up_verdict()` ab 3 heilbaren Wunden;
  Makari per `_handle_makari()` in `_handle_movement()` vor Da Jump, wenn mindestens min(Runde, 3)
  Einheiten mit Feind in Advance + Charge gewinnen, die nächsten zuerst.
- **Nachgezogen:** `test_ork_army_rules.py` (22 Blätter; §1 prüft jetzt Da Boss gegen jede gedruckte
  FACTION-Zeile, §10s „kein Warlord"-Pin ist ersetzt), `test_aeldari_enhancements.py` (sechste
  Lone-Operative-Quelle), `test_roll_modifier_cap.py` (die zwei Prophet-Modifikatoren als ROLL, 56
  Stellen), `test_tau_characters.py` und `test_necron_ctan.py` (No-op-Texte), `rules/README.md`
  (Orks 22). **Zwei Sondenanker älterer Treiber** hatte G2 verschoben — der Trukk-Ausschluss
  (`ab_ork_vehicles.py`) und eine vom Da-Boss-Handler wörtlich übernommene Zeile im Makari-Handler
  (`ab_ork_war_horde.py`, Anker doppelt; die Makari-Zeile ist jetzt eigen). `--check` über alle
  Treiber fand beide, beide beißen wieder.

**Getestet:** neu `test_ork_mecha_characters.py` (**122/122**, elf Abschnitte — Datenblätter gegen
Korpus, Transport an 18.01 UND 18.02, More Dakka am ECHTEN Cover-Tor samt Oversight Drone, Kustom
Force Field über `effective_invulnerable_save()`, Fix Dat mit Angebot/Ablehnung/Nutzung/KI, Warlord
über `army_io.parse()` und den echten Builder, Da Boss samt geladenem Spielstand, Ladz über
`lone_operative_range()`, Prophet über den echten `FightController` samt ±1-Deckel mit Sumfin' to
Prove, Makari mit Pick/Limit/echtem `ActionPanel` in allen fünf Phasen/KI, AST-Pins) und
`ab_ork_mecha_characters.py` (**66 Sonden, 71 Läufe, alle beißend, kein Rest**). **Im ersten Lauf
bissen sieben nicht** — zwei Abstürze (`next()` ohne Default, `None.attacks`), drei VERDECKTE Terme
(Fix Dat „erneut angeboten" hinter „nichts zu heilen", zweimal Da Boss hinter dem CP-Deckel), eine
KI-Szene ohne qualifizierende Einheit, und ein toter Zweig im Code (Makari, s. o.). Volle Regression
**239 Suiten, ~23339 Prüfungen, 238 grün / 0 rot / 1 bekannt**, `run_tests.py --smoke` komplett grün,
`selfplay.py map2 1500` Orks gegen Necrons in beiden Sitzordnungen exit 0.
`verify_rules_vs_engine.py` **68** (unverändert), `fetch_datasheet_rules.py --offline` nur mit den
zwei neuen Blättern im README, `measure_crowded_movement.py` unverändert gedrängt **62 % / 210.2"**,
isoliert **87 % / 292.3"**.

**Im ECHTEN Spiel belegt** (`verify_ork_mecha_characters.py map2`, Orks als Player 1; 9/9, unter
`--neutralize` 7/7 Abwesenheitsprüfungen):

| | gefixt | `--neutralize` |
|---|---|---|
| Wiring | Fix Dat mit `main()`s Platzierer, Da Boss mit `main()`s CP-Ledger, Makari registriert | Makari fehlt |
| KI-Makari über `main()`s Auto-Play (Runde 3) | drei Player-2-Boyz riled up | nie |
| Da Boss an `main()`s Phasengrenze | 1 CP, Runde gestempelt, nächste Grenze derselben Runde 0 | nichts |
| Makari auf `main()`s Panel | gezeichnet, Pick über `main()`s DecisionManager, Einheit riled up, verbraucht | nie gezeichnet |
| More Dakka am Live-`ShootingController` | kein Benefit of Cover für die Big-Mek-Einheit, plain Meganob +1 | Cover bleibt |
| Prophet am Live-`FightController` | −1/−1 | nichts |
| Fix Dat an `main()`s Command-Grenze | gefragt, 11 → 14 Wunden, verbraucht | nie gefragt |

GESTELLT: Orks als Player 1, gebaute Einheiten (die Liste fieldet sie erst ab G6), Player 1s
Ghazghkull von Hand als Warlord markiert, die Uhr je Stufe, einmal Deckung für die Cover-Lesung, und
für die KI-Stufe Ork-Einheiten für Player 2 (dessen Armee sind Necrons).
