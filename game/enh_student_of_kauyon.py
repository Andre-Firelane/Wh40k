"""Auxiliary Cadre Enhancement: Student of Kauyon (20 pts).

RULE (verbatim, rules/tau_empire/detachments/Auxiliary Cadre.md):
  KROOT SHAPER model only. In the Declare Battle Formations step, you can select
  up to three friendly KROOT CARNIVORES/FARSTALKERS units. Those units have
  Deep Strike.

WHERE IT LANDS, AND WHY THE TIMING IS LOAD-BEARING
----------------------------------------------------
Deep Strike (24.09) is what lets a unit arriving from Strategic Reserves be set
up anywhere more than 9" from every enemy, instead of only against a board edge
(20.04). The DECLARATION that a unit starts in Strategic Reserves is made in
the very same step, so this has to be offered BEFORE the declarations are
answered - a grant made afterwards would be worth nothing this battle, which is
the whole reason the printed text names that step rather than "before the
first turn".

So it runs at the START of Declare Battle Formations, from
PregameController.start(), and the units it touches then go through the
ordinary reserve declaration like any other.

"THOSE UNITS HAVE DEEP STRIKE" is written onto the models' own UnitProfile
instances (build_squad() makes them per model), the same way every other
granted keyword in this engine is - there is no separate keyword system to add
to. It is permanent: the printed text gives no end.

"KROOT CARNIVORES/FARSTALKERS units" names two DATASHEETS, not a keyword: the
KROOT keyword also covers Kroot Hounds, Krootox Riders, Krootox Rampagers and
the three Shapers, and granting them Deep Strike would be a much wider rule
than the one printed. Matched on the datasheet name, the way
game/enhancements.py's two "unit only" bearer restrictions are, and pinned
against the KROOT keyword in the tests so the difference cannot quietly
collapse.

UP TO THREE, and "up to" means declining is legal. Offered one prompt per unit
rather than a single three-from-N choice, because DecisionManager offers a flat
list of options and a combinatorial one would be unreadable; the running count
is what enforces the three.

An owner in `auto_players` takes the first three by name - deterministic, and a
rule answering its own prompt rather than an AI path (the standing T'au rule).
"""

from game import ai_mode, enhancements

STUDENT_OF_KAUYON = "Student of Kauyon"
MAX_UNITS = 3
ELIGIBLE_DATASHEETS = ("Kroot Carnivores", "Kroot Farstalkers")


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def is_eligible_unit(squad):
    """"friendly KROOT CARNIVORES/FARSTALKERS units" - by DATASHEET, not by the
    KROOT keyword. See the module docstring."""
    if squad is None:
        return False
    names = []
    sheet = getattr(squad, "datasheet", None)
    if sheet is not None and getattr(sheet, "name", None):
        names.append(sheet.name)
    for component in getattr(squad, "attached_components", ()) or ():
        sheet = getattr(component, "datasheet", None)
        if sheet is not None and getattr(sheet, "name", None):
            names.append(sheet.name)
    return any(n in ELIGIBLE_DATASHEETS for n in names)


def has_deep_strike(squad):
    """Every living model of the unit prints or has been granted it - the same
    "every model" reading rule 24.09 itself uses."""
    models = _living(squad)
    return bool(models) and all(m.profile.deep_strike for m in models)


def grant_deep_strike(squad, game_log=None):
    if squad is None:
        return False
    for model in squad.models:
        model.profile.deep_strike = True
    if game_log is not None:
        game_log.add(f"{squad.owner}: {squad.name} has Deep Strike (rule 24.09) from the "
                     f"{STUDENT_OF_KAUYON} Enhancement.")
    return True


class StudentOfKauyonStep:
    """Run at the start of Declare Battle Formations, from
    PregameController.start()."""

    def __init__(self, decision_manager=None, game_log=None, auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self.granted = {}      # player -> [squads], for reporting and the count
        # The army being offered from, remembered so an accepted grant can
        # re-offer the next one: DecisionManager resolves asynchronously, so
        # start() can only ever raise ONE prompt and the chain has to continue
        # from the callback. Same shape ScoutsStep's own queue uses.
        self._squads = []

    def bearer_units(self, squads, player):
        return enhancements.bearer_units(squads, STUDENT_OF_KAUYON, player=player)

    def eligible_targets(self, squads, player):
        """Candidates that would actually gain something: a unit that already
        has Deep Strike is not offered, on the "never offer what buys nothing"
        rule."""
        already = self.granted.get(player, [])
        return [s for s in squads
                if s.owner == player and is_eligible_unit(s)
                and not has_deep_strike(s) and s not in already]

    def remaining(self, player):
        return MAX_UNITS - len(self.granted.get(player, []))

    def start(self, squads, player):
        """Offer up to three grants for `player`. Returns True if anything was
        asked or granted."""
        self._squads = list(squads or ())
        if not self.bearer_units(self._squads, player):
            return False
        acted = False
        while self.remaining(player) > 0:
            targets = self.eligible_targets(self._squads, player)
            if not targets:
                break
            if player in self.auto_players or self.decision_manager is None:
                self.grant(player, sorted(targets, key=lambda s: s.name)[0])
                acted = True
                continue
            options = [(f"{STUDENT_OF_KAUYON}: {t.name}",
                        (lambda target=t: self.grant(player, target)), t)
                       for t in targets]
            options.append(("No more", None))
            self.decision_manager.request(
                player,
                f"{STUDENT_OF_KAUYON}: give Deep Strike to a KROOT CARNIVORES/FARSTALKERS "
                f"unit? ({self.remaining(player)} left)",
                options)
            return True
        return acted

    def grant(self, player, squad):
        """The prompt callback. Grants, then re-offers while there is room -
        the loop in start() cannot do it, because a human answer arrives a
        frame or more later."""
        if squad is None or self.remaining(player) <= 0:
            return False
        grant_deep_strike(squad, game_log=self.game_log)
        self.granted.setdefault(player, []).append(squad)
        # Only the PROMPTED path needs re-offering. The automatic path is
        # already inside start()'s own loop, and re-entering it from here would
        # run that loop twice over the same candidates - harmless (remaining()
        # still caps it at three) but confusing to read and to trace in a log.
        if (player not in self.auto_players and self.decision_manager is not None
                and self.remaining(player) > 0 and self._squads):
            self.start(self._squads, player)
        return True
