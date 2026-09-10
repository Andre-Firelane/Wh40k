"""Canoptek Macrocytes' two wargear items (Necrons).

RULES (printed, word for word):

  ACCELERATOR MANDIBLE: "At the start of the Fight phase, select one friendly
    CANOPTEK unit within 3" of the bearer's unit. Until the end of the phase,
    improve the Weapon Skill characteristic of weapons equipped by models in
    that unit by 1."

  NANOSCARAB PROJECTOR: see game/reanimation_boost.py - it adds to the same
    number the Canoptek Reanimator's aura does, at the same moment, so the two
    live together rather than apart.

THE ACCELERATOR MANDIBLE IS THE FIRST THING IN THIS ENGINE THAT IMPROVES A
WEAPON SKILL CHARACTERISTIC. Every melee accuracy effect before it is a
Modifier on the HIT ROLL, which is a different quantity: rule 24.29 [PSYCHIC],
ignores_hit_modifiers and Kauyon all filter hit-roll modifiers and would leave
this one alone, because it is not one. It is applied at
fight.effective_weapon_skill(), the single place a melee weapon's skill is
resolved.

"IMPROVE ... BY 1" MEANS A LOWER THRESHOLD - WS4+ becomes WS3+ - and it is
CLAMPED AT 2+, the same floor every other characteristic improvement in this
engine respects: an unmodified 1 always fails (05.04), so a 1+ would be a
threshold no die can miss and no rule prints one.

"WEAPONS EQUIPPED BY MODELS IN THAT UNIT" - so it improves the WIELDER's skill,
and a weapon that prints its OWN worse WS (the Power Klaw's 4+) keeps that one:
effective_weapon_skill() reads the weapon's override first, and this improves
what the MODEL contributes. Written out because "weapons equipped by models" is
easy to read as "the weapons' own characteristic".

A SQUAD FLAG rather than a live measurement: it is granted once at the start of
the Fight phase and held "until the end of the phase", so a distance re-checked
per attack would silently expire the grant the moment the target unit moved -
and a Pile In moves it every activation.
"""

from game import ai_mode
from game.squad import edge_distance

ACCELERATOR_MANDIBLE_LABEL = "Accelerator Mandible"

#: "within 3" of the bearer's unit".
ACCELERATOR_MANDIBLE_RANGE_IN = 3.0
#: "improve the Weapon Skill characteristic ... by 1" - a better skill is a
#: LOWER threshold.
ACCELERATOR_MANDIBLE_BONUS = 1
#: Rule 05.04: an unmodified 1 always fails, so no threshold goes below 2+.
BEST_POSSIBLE_SKILL = 2


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def is_canoptek_unit(squad):
    """"one friendly CANOPTEK unit" - read off the DATASHEET keyword line,
    which is where the word is printed."""
    from game.attached_units import unit_has_datasheet_keyword
    return unit_has_datasheet_keyword(squad, "CANOPTEK")


def bearer_models(squad):
    return [m for m in _living(squad)
            if getattr(m.profile, "accelerator_mandible", False)]


def improved_weapon_skill(model, printed):
    """The Weapon Skill this model's weapons resolve to right now.

    `printed` is what effective_weapon_skill() had - the weapon's own override
    if it prints one, otherwise the model's. Returned as a threshold STRING,
    the form that function already deals in."""
    squad = getattr(model, "squad", None)
    if squad is None or not getattr(squad, "accelerator_mandible_bonus", False):
        return printed
    try:
        value = int(str(printed).rstrip("+"))
    except (TypeError, ValueError):
        return printed
    return "%d+" % max(BEST_POSSIBLE_SKILL, value - ACCELERATOR_MANDIBLE_BONUS)


class AcceleratorMandibleController:
    """Offered at the start of every Fight phase, once per bearer unit."""

    def __init__(self, decision_manager=None, game_state=None, game_log=None,
                 auto_players=()):
        self.decision_manager = decision_manager
        self.game_state = game_state
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._offered = set()

    def _tokens(self):
        return getattr(self.game_state, "tokens", None) or []

    def _squads(self, owner=None):
        seen = {}
        for token in self._tokens():
            squad = getattr(token, "squad", None)
            if squad is None:
                continue
            if owner is not None and squad.owner != owner:
                continue
            seen[id(squad)] = squad
        return list(seen.values())

    def candidates(self, bearer_squad):
        """Friendly CANOPTEK units within 3" of the bearer's UNIT - the
        printed subject is the unit, not the model carrying the mandible."""
        mine = _living(bearer_squad)
        out = []
        for squad in self._squads(getattr(bearer_squad, "owner", None)):
            if not is_canoptek_unit(squad):
                continue
            others = _living(squad)
            if not others:
                continue
            if any(edge_distance(a, b) <= ACCELERATOR_MANDIBLE_RANGE_IN
                   for a in mine for b in others):
                out.append(squad)
        return sorted(out, key=lambda s: s.name)

    def offer_at_start_of_fight(self, player):
        raised = False
        for squad in self._squads(player):
            if not bearer_models(squad) or id(squad) in self._offered:
                continue
            targets = self.candidates(squad)
            if not targets:
                continue
            self._offered.add(id(squad))
            if len(targets) == 1 or player in self.auto_players \
                    or self.decision_manager is None:
                self._grant(squad, targets[0])
                continue
            options = [("%s: %s" % (ACCELERATOR_MANDIBLE_LABEL, t.name),
                        (lambda target=t, s=squad: self._grant(s, target)), t)
                       for t in targets]
            self.decision_manager.request(
                player,
                "%s: improve which unit's Weapon Skill?" % ACCELERATOR_MANDIBLE_LABEL,
                options)
            raised = True
        return raised

    def _grant(self, bearer_squad, target):
        if target is None:
            return False
        target.accelerator_mandible_bonus = True
        if self.game_log is not None:
            self.game_log.add(
                "%s (%s): %s improves its Weapon Skill by 1 until the end of "
                "the phase." % (ACCELERATOR_MANDIBLE_LABEL, bearer_squad.name,
                                target.name))
        return True

    def reset_phase(self, squads=()):
        """"Until the end of the phase" - one clock, and it is the short one."""
        self._offered.clear()
        for squad in squads or self._squads():
            squad.accelerator_mandible_bonus = False


def equip_accelerator_mandible(token):
    token.profile.accelerator_mandible = True


def equip_nanoscarab_projector(token):
    token.profile.nanoscarab_projector = True
