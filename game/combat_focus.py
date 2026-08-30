"""Whether a unit's damage comes from SHOOTING or from FIGHTING, and how
lopsidedly - the one place that question is answered.

WHY THIS EXISTS
---------------
The per-MODEL half of it has been here for a while, in game/front_rank.py,
where it answers "is this character here to fight, so does it belong in the
front rank". Two more consumers arrived at once, both from the same report,
and both about the UNIT rather than one of its models:

  * ai/agent_driver.py's Charge phase. User: "havey destroyer - die sollten
    nicht chargen. das sind fernkampf einheiten. erst recht keine so starken
    nahkampfeinheiten, wie banshees. baue gerne eine charge sperre ein, wenn
    die fernkampfwaffen so extrem viel staerker sind als die nahkampfwaffen."
  * ai/deployment_ai.py's role classification. User: "nahkkaempfer sollten
    eher weiter vorne starten, aber moeglichst versteckt."

Those are the same measurement read from its two ends, so they are one
function with two thresholds rather than two functions - the alternative was a
second reference defender and a second ratio living in ai/, which is exactly
the quietly diverging pair this codebase keeps having to consolidate.

front_rank.py keeps its own names working by importing them from here, so
every existing `front_rank.model_output` / `front_rank.is_melee_focused`
caller is untouched.

THE REFERENCE DEFENDER
----------------------
A ratio needs something to measure both halves against, since Strength-vs-
Toughness, AP-vs-save and damage-vs-wounds all enter the arithmetic. It is a
fixed neutral statline rather than a real unit - see front_rank.py's module
docstring for the original argument and the per-character numbers.

Being defender-free is what lets DEPLOYMENT use it at all: units are set up
alternately, so when the AI places its eighth unit there is no settled enemy
army to measure against, and half of one is not a sample.

THE TWO THRESHOLDS ARE ONE NUMBER
---------------------------------
"Shooting is R times melee" and "melee is R times shooting" are the same
statement about lopsidedness, so there is one constant and the assault side
reads 1/R. Both bands were measured over every unit of both armies the AI can
field (Necrons and Orks) plus Player 1's list, against this reference defender
AND against a second, very different one (T8/3+/8W), the same cross-check
front_rank.py's docstring documents:

  shooting side, ratio = ranged / melee
    must be blocked   Immortals+Plasmancer 1.70, Lokhust Heavy 4.00,
                      Lokhust Destroyers 6.67, Doomsday Ark 5.56
    must stay free    Necron Warriors 1.09, Ork Warbikers 1.00,
                      Gretchin 0.97, C'tan Void Dragon 0.23
    => clean band 1.09 .. 1.70; SHOOTING_SPECIALIST_RATIO sits at 1.4

  assault side, same ratio read downward (only reached by units that are not
  already "heavy", "key" or "shooter" - see ai/deployment_ai.py)
    should be assault Skorpekh 0.00, Canoptek Wraiths 0.00, Lychguard 0.00,
                      Beast Snagga Boyz 0.08, Ork Boyz 0.12, Stormboyz 0.12,
                      Meganobz 0.16
    should stay screen Gretchin 0.97, Warbikers 1.00
    => clean band 0.16 .. 0.97; 1/1.4 = 0.71 sits inside it

The C'tan Shard of the Void Dragon at 0.23 is the case the user named
explicitly ("manche einhetien sind sowohl nahkaempfer als auch fernkaempfer.
wie zb shard of the void dragen. da soll die sperre nicht greifen") and it is
not a close call: it clears the line by a factor of six, because its Spear
strike profile is A5 S12 AP-4 D6+2 against a D3-shot ranged row.

THE ONE UNIT NEAR THE LINE is the Ork Warbikers, at 1.00 against this
reference and 1.50 against the tough one - so they stay free here and would
not against a tougher yardstick. Recorded rather than tuned away: the same
honesty front_rank.py's "it is still a judgement call, not a constant that was
discovered" applies to.

A THIRD CONSUMER SHAPE arrived later and reads both thresholds at once:
home_garrison_rank(), the "who should stand on the home objective" question.
It lives here rather than in ai/ because it is the same measurement read a
third way, and because putting it beside the two thresholds is what keeps the
deployment step and the turn-plan step from answering it differently - they
are two phases of one decision and used to disagree.

APPROXIMATE in exactly the ways game/damage_estimate.py is (no re-rolls, no
[SUSTAINED HITS]/[LETHAL HITS]/[DEVASTATING WOUNDS], no cover, no abilities) -
and that matters less here than anywhere else it is used, because both halves
of a ratio are computed the same way and most of what is missing cancels.
"""

from game.damage_estimate import expected_wounds
from game import weapon_range


class _ReferenceDefender:
    """Neutral yardstick for the melee-vs-ranged comparison - see the module
    docstring. Deliberately not a real datasheet: it exists to cancel out of a
    ratio, not to predict an outcome."""

    toughness = 4
    armor_save = "4+"
    invulnerable_save = None
    wounds = 2


REFERENCE_DEFENDER = _ReferenceDefender()

# How much of a MODEL's damage has to come from melee before it is worth
# putting in harm's way. 1.0 = "more from fighting than from shooting".
MELEE_LEAD_RATIO = 1.0

# How lopsided a UNIT's output has to be before the lopsidedness is worth
# acting on. See "THE TWO THRESHOLDS ARE ONE NUMBER" above for both measured
# bands. Deliberately larger than MELEE_LEAD_RATIO: that one only has to
# decide which way a model leans, this one has to be sure enough to take a
# whole option off the table.
SHOOTING_SPECIALIST_RATIO = 1.4


def model_output(model, melee, defender=REFERENCE_DEFENDER):
    """Roughly how many wounds one model's shooting (or fighting) is worth
    against `defender`.

    The per-model half of damage_estimate.expected_wounds_against(), including
    rule 04.01 - a model attacking in melee picks ONE melee weapon, so only the
    best of them counts, plus any [EXTRA ATTACKS] weapon (24.11), which swings
    in addition to it."""
    want = "melee" if melee else "ranged"
    skill = model.profile.weapon_skill if melee else model.profile.ballistic_skill
    total = 0.0
    best_selectable = 0.0
    for weapon in model.weapons:
        if getattr(weapon, "weapon_type", None) != want:
            continue
        value = expected_wounds(weapon, weapon.attacks, skill, defender)
        if melee and not weapon.extra_attacks:
            best_selectable = max(best_selectable, value)
        else:
            total += value
    return total + best_selectable


def is_melee_focused(model):
    """Whether this model's damage comes mainly from melee. Split out from
    is_melee_character() so the two halves of the test stay separately
    readable and separately testable."""
    melee = model_output(model, melee=True)
    if melee <= 0.0:
        return False
    ranged = model_output(model, melee=False)
    if ranged <= 0.0:
        return True  # nothing but melee weapons at all - the Painboy case
    return melee / ranged >= MELEE_LEAD_RATIO


def squad_output(squad, melee, defender=REFERENCE_DEFENDER):
    """model_output() summed over the models that are still ALIVE.

    Live models rather than the printed datasheet, for the same reason
    damage_estimate.models_destroyed_by() reads remaining wounds: three
    surviving Lokhust Heavy Destroyers and one are not the same unit, and the
    Charge-phase caller is asking about the unit in front of it. A ratio is
    mostly insensitive to this - losing models scales both halves - but an
    attached unit (19.01) whose CHARACTER is the only model with a melee
    weapon is not, and that is a shape both demo armies contain."""
    return sum(model_output(m, melee=melee, defender=defender)
               for m in squad.models if not m.is_dead())


def ranged_to_melee_ratio(squad, defender=REFERENCE_DEFENDER):
    """How many times more damage this unit's shooting does than its fighting.

    None when the unit can do neither (no models left, or nothing that
    attacks) - a caller has no verdict to draw from that, and returning 0.0
    would read as "pure melee". float('inf') for a unit with guns and no melee
    weapon at all, which is a real shape (Doomsday Ark's own melee row exists,
    but a Devilfish's does not)."""
    melee = squad_output(squad, melee=True, defender=defender)
    ranged = squad_output(squad, melee=False, defender=defender)
    if melee <= 0.0:
        return float("inf") if ranged > 0.0 else None
    return ranged / melee


def is_shooting_specialist(squad, defender=REFERENCE_DEFENDER):
    """This unit's guns are decisively better than its fists - the user's "das
    sind fernkampf einheiten".

    A unit with no melee capability at all (ratio inf) is included, which is
    the degenerate end of the same statement."""
    ratio = ranged_to_melee_ratio(squad, defender)
    return ratio is not None and ratio >= SHOOTING_SPECIALIST_RATIO


def is_assault_unit(squad, defender=REFERENCE_DEFENDER):
    """The same test read from the other end: this unit's fists are decisively
    better than its guns, so it has nothing to do until it reaches the enemy.

    A unit with no ranged weapons at all (ratio 0.0) is included."""
    ratio = ranged_to_melee_ratio(squad, defender)
    return ratio is not None and ratio <= 1.0 / SHOOTING_SPECIALIST_RATIO


# How good a unit is at STANDING ON THE HOME OBJECTIVE, best first. See
# home_garrison_rank() - three bands, not a score, because a continuous one
# would out-vote the points term that the garrison passes are otherwise built
# on and hand the job to whatever gun is biggest.
GARRISON_BAND_SHOOTER = 0   # its guns are the point, and they reach the fight
GARRISON_BAND_NEUTRAL = 1   # neither decisively - it loses least by standing there
GARRISON_BAND_ASSAULT = 2   # it has nothing to do until it reaches the enemy


def best_ranged_reach_in(squad):
    """The longest range any live model in this unit can shoot to, in inches.

    Reads game/weapon_range.py rather than the printed characteristic, because
    that is this repo's one definition of "how far does this weapon reach right
    now" - two abilities extend it live, and a second reader of the printed
    number is exactly the quietly diverging pair the extraction exists to
    prevent. 0.0 for a unit with no ranged weapons at all."""
    best = 0.0
    for model in squad.models:
        if model.is_dead():
            continue
        for weapon in model.weapons:
            if getattr(weapon, "weapon_type", None) != "ranged":
                continue
            best = max(best, weapon_range.effective_range_in(model, weapon))
    return best


def home_garrison_rank(squad, reach_needed_in=None, defender=REFERENCE_DEFENDER):
    """Which of the three GARRISON_BAND_* this unit belongs in for the job of
    holding a HOME objective - the ground behind one's own lines that nobody is
    contesting. Lower is better.

    User: "die ki soll fernkampfeinheiten stark bevorzugen, wenn es darum geht
    das home objective zu halten. sie hat im letzten spiel dafuer die lychguard
    benutzt, was voelliger quatsch ist. die immortals waeren perfekt. starke
    fernkaempfer mit hoher reichweite."

    BOTH HALVES OF THAT SENTENCE ARE TERMS, and they are not the same term -
    measured over all three lists, range and the shooting/melee ratio do not
    run parallel. The Aeldari Wraithguard read as a shooting unit (ratio 2.00)
    on a 12" gun: parked on a home objective it contributes exactly as little
    as the Lychguard do, because the nearest ground anyone fights over is 15-17"
    away (see ai/observation.py's garrison_reach_needed_in(), where that
    distance is measured off the board rather than guessed). So a unit is in
    the top band only if its damage comes from shooting AND that shooting can
    still touch the game from back there.

    `reach_needed_in=None` drops the range half, for a caller that has no board
    to measure against.

    THREE BANDS RATHER THAN A SCORE. The garrison passes that read this are
    built on "cheapest unit that can do the job", and a continuous ranged-ness
    score would out-vote the points term everywhere: on the Ork list it would
    move the job from the 45-point Gretchin to the 160-point Battlewagon.
    Banding keeps points deciding WITHIN a band, which is where that rule was
    always right."""
    if is_assault_unit(squad, defender):
        return GARRISON_BAND_ASSAULT
    if not is_shooting_specialist(squad, defender):
        return GARRISON_BAND_NEUTRAL
    if reach_needed_in is not None and best_ranged_reach_in(squad) < reach_needed_in:
        return GARRISON_BAND_NEUTRAL
    return GARRISON_BAND_SHOOTER


def describe_ratio(squad, defender=REFERENCE_DEFENDER):
    """The three numbers behind a verdict, for a log line.

    A diagnostic line that omits the very number in dispute sends the next
    investigation back to the board - this repo has paid that twice - so a
    blocked charge says how lopsided the unit was and by how much, not just
    that it was."""
    ratio = ranged_to_melee_ratio(squad, defender)
    ranged = squad_output(squad, melee=False, defender=defender)
    melee = squad_output(squad, melee=True, defender=defender)
    if ratio is None:
        return "this unit has no attacks at all"
    shown = "no melee weapons at all" if ratio == float("inf") else f"{ratio:.1f}x"
    return (f"its shooting is worth {ranged:.1f} wounds a turn against its melee's "
            f"{melee:.1f} ({shown})")
