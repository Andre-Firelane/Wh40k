"""A psychic mark on an enemy unit that outlives the turn - the machinery
shared by the Farseer's Guide and Eldrad Ulthran's Doom.

The two abilities are printed as the same sentence twice, changing one word:

  Guide: "At the end of your Movement phase, select one enemy unit within 18"
  of and visible to this model. Until the start of your next Command phase,
  each time a friendly AELDARI model makes an attack that targets that enemy
  unit, add 1 to the HIT roll. Each unit can only be selected for this ability
  once per turn."

  Doom:  "At the end of your Movement phase, select one enemy unit within 18"
  of and visible to this model. Until the start of your next Command phase,
  each time a friendly AELDARI model makes an attack that targets that enemy
  unit, add 1 to the WOUND roll."

So everything about the MARK is shared - when it is set, how the candidate is
chosen, how long it lives, and whose attacks read it - and what belongs to each
ability is only which roll it modifies (i.e. which of the two modifier hooks it
hangs in) and which profile flag names its bearer. Sixth extraction of this
shape, after game/invulnerable_save.py, game/crit_hit.py,
game/damage_reroll.py, game/damage_estimate.py and game/unmodified_six.py, and
for the same two reasons each time: a second foreign consumer, and one call
site to update.

TWO DIFFERENCES THAT ARE REAL, not cosmetic, and both parameterised here:

  * the ONCE-PER-TURN cap. Guide prints "each unit can only be selected for
    this ability once per turn"; Doom does NOT. Confirmed by asking for that
    sentence specifically rather than assuming the twins matched, because
    copying a near-identical profile is exactly how a restriction gets granted
    or given away by accident.
  * the ROLL. Guide is a hit-roll bonus and hangs in _hit_modifiers(); Doom is
    a wound-roll bonus and hangs in _wound_modifiers(). Both in BOTH phases,
    because "makes an attack" is not "makes a ranged attack".

THE LONGEST-LIVED EFFECT IN THIS ENGINE
---------------------------------------
"Until the start of your next Command phase" spans the rest of your own turn,
the whole of your opponent's, and ends only when your next turn begins. Every
other duration in this codebase is "until the end of the phase" or "until the
end of the turn", and both of those are cleared in main.py's own end-of-turn
block; this one is cleared when its OWNER's Command phase begins instead.

That matters: the mark is live during the opponent's turn, which is exactly
when a Fire Overwatch snap shot (15.08/15.09) or a Heroic Intervention (15.11)
would read it.

THE BENEFIT IS ARMY-WIDE, not unit-wide - "each time a friendly AELDARI model
makes an attack", not "a model in this unit". So the mark is held per PLAYER
rather than on the bearer's own squad, and every Aeldari unit they own reads
it. That is also why it is checked against the ATTACKING side's faction, using
the same AELDARI test game/psychic_guidance.py and game/psychic_communion.py
use (it reads the datasheet's faction, since game/factions/aeldari.py
deliberately does not repeat faction keywords on each datasheet).

Faction is asked of the SQUAD, not the model: rule 19.01 only merges units of
the same faction, so there is no attached unit whose models could disagree -
and the two wound-roll hooks have no attacking model to hand anyway, only the
active/fighting squad.

"WITHIN 18 INCHES OF AND VISIBLE TO THIS MODEL" is checked once, when the unit
is selected - it is a selection criterion, not a condition on each later
attack, which is the same reading rule 10.02 gets for range and line of sight.
"""

from game import psychic_guidance
from game.line_of_sight import has_line_of_sight

DEFAULT_MARK_RANGE_IN = 18.0


class PsychicMark:
    """One ability's marks. Subclassed per ability (see game/guide.py and
    game/doom.py) so that the flag, the range and the once-per-turn rule live
    with the ability rather than at the call site.

    Human-only in practice like the rest of the Aeldari work, but the selection
    is an ordinary DecisionManager break point, so an AI would resolve it
    through the generic path with nothing extra here."""

    ability_name = "Psychic mark"
    flag = None                 # the UnitProfile attribute naming a bearer
    effect_text = ""            # the half-sentence a prompt uses for the effect
    range_in = DEFAULT_MARK_RANGE_IN
    once_per_turn = False       # whether "each unit can only be selected ... once per turn" is printed

    def __init__(self, decision_manager=None, game_log=None, all_tokens=None,
                 obstacles=None, terrain_areas=None):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.obstacles = obstacles if obstacles is not None else []
        self.terrain_areas = terrain_areas if terrain_areas is not None else []
        self._marks = {}              # player -> set of marked enemy Squads
        self._marked_this_turn = {}   # player -> set of Squads already selected this turn

    # --- bearers ----------------------------------------------------------
    def bearers(self, squad):
        return [m for m in getattr(squad, "models", None) or ()
                if getattr(m.profile, self.flag, False) and not m.is_dead()]

    def squad_has_ability(self, squad):
        return bool(self.bearers(squad))

    # --- lifetime ---------------------------------------------------------
    def marked_by(self, player):
        return set(self._marks.get(player, ()))

    def start_of_command_phase(self, player):
        """"Until the start of your next Command phase" - so the mark ends
        here, not at end of turn. Also the point at which "once per turn"
        resets, since a player's turn begins with their Command phase."""
        self._marks.pop(player, None)
        self._marked_this_turn.pop(player, None)

    # --- reading it -------------------------------------------------------
    def applies_to_squad(self, attacking_squad, target_squad):
        """Whether attacks by this squad against that unit get the bonus: a
        friendly AELDARI unit attacking one its owner has marked."""
        if attacking_squad is None or target_squad is None:
            return False
        if not psychic_guidance._is_aeldari(attacking_squad):
            return False
        return target_squad in self._marks.get(attacking_squad.owner, ())

    def applies(self, attacking_model, target_squad):
        """The per-model form, for the hooks that have a model to hand."""
        if attacking_model is None:
            return False
        return self.applies_to_squad(getattr(attacking_model, "squad", None), target_squad)

    # --- setting it -------------------------------------------------------
    def candidates(self, bearer_squad):
        """The enemy units this unit could select right now: within range of
        and visible to a bearer model, not already marked, and - where the
        ability says so - not already selected this turn."""
        bearers = self.bearers(bearer_squad)
        if not bearers:
            return []
        blocked = set(self._marks.get(bearer_squad.owner, set()))
        if self.once_per_turn:
            blocked |= set(self._marked_this_turn.get(bearer_squad.owner, set()))
        out = []
        for token in self.all_tokens:
            other = getattr(token, "squad", None)
            if other is None or other.owner == bearer_squad.owner or token.is_dead():
                continue
            if other in out or other in blocked:
                continue
            for bearer in bearers:
                dx, dy = bearer.x_in - token.x_in, bearer.y_in - token.y_in
                if (dx * dx + dy * dy) ** 0.5 > self.range_in:
                    continue
                if has_line_of_sight(bearer, token, self.obstacles, self.all_tokens,
                                     terrain_areas=self.terrain_areas):
                    out.append(other)
                    break
        return sorted(out, key=lambda s: s.name)

    def offer_at_end_of_movement(self, player, squads):
        """Called from main.py when the Movement phase ends. One offer per
        bearer unit that has a legal selection."""
        if self.decision_manager is None:
            return
        for squad in squads:
            if squad.owner != player or not self.squad_has_ability(squad):
                continue
            options = self.candidates(squad)
            if not options:
                continue
            self.decision_manager.request(
                player,
                f'{squad.name}: {self.ability_name} - select one enemy unit within '
                f'{self.range_in:g}" and visible. Friendly AELDARI models {self.effect_text} '
                "against it until the start of your next Command phase.",
                [(target.name, (lambda t=target: self.mark(player, t)), target) for target in options]
                + [(f"Do not use {self.ability_name}", lambda: None)],
            )

    def mark(self, player, target):
        self._marks.setdefault(player, set()).add(target)
        self._marked_this_turn.setdefault(player, set()).add(target)
        if self.game_log is not None:
            self.game_log.add(
                f"{self.ability_name}: friendly AELDARI models {self.effect_text} against "
                f"{target.name} until the start of the next Command phase."
            )
