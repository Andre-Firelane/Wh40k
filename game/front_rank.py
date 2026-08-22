"""Which models of a unit belong at the FRONT of its formation.

WHY THIS EXISTS
---------------
User report: "die ki stellt den warboss immer sehr weit hinten im squad auf.
der sollte ganz vorne im squad aufgestellt werden, damit er auch als ersten in
den nahkampf kommt. kann sonst nicht zuschlagen." - and, on the follow-up,
"das gilt fuer alle nahkampflastigen charaktere".

Measured on the real Player 2 mob (20 Boyz + Warboss + Painboy) before this
existed: the Warboss came out rank 7 of 22 and the Painboy rank 9, both with
six Boyz standing in front of them. That is not so much a bug in the packer as
a consequence of its shape - game/formation_layout.py fills concentric rings
outward from the drop point, so the first model placed sits at the CENTRE of
the finished block and later ones wrap all the way around it, including in
front. The widest model picks first (a Warboss is 0.98" to a Boy's 0.63"), so
the character reliably ends up buried in the middle.

That costs real attacks. Only models within Engagement Range fight (rule
12.05), and a charge fills engagement slots nearest-first, so a character six
ranks back gets whatever is left over - which is often nothing.

WHAT COUNTS AS A MELEE CHARACTER
--------------------------------
Two conditions, and the second one is the whole reason this is a function
rather than a flag:

  * it is a CHARACTER - a model contributed by a Leader or Support component
    of a rule 19.01 attached unit (attached_units.leader_models());
  * its own damage comes mainly from MELEE - its best melee attack sequence
    beats its whole ranged output against the same reference defender.

The second test is deliberately about the model ITSELF, not about how it
compares to the rank and file. A Cadre Fireblade's honour blade beats a
Breacher's close combat weapon, so a relative test would shove the squad's
shooting buff into the front rank to die; a Warboss leading a shooty unit is
still a melee threat and still belongs in front. "Is this model here to
fight?" is the question that was actually asked.

THE REFERENCE DEFENDER
----------------------
A ratio needs something to measure both halves against, since Strength-vs-
Toughness, AP-vs-save and damage-vs-wounds all enter the arithmetic. It is a
fixed neutral statline rather than a real unit, and the classification was
measured against a second, very different one (T8/3+/8W) to check that it does
not hinge on the choice. Every character in both demo armies lands on the same
side of 1.0 either way (melee/ranged ratio, soft reference / tough reference):

    Warboss            18.5 / 37.5      Cadre Fireblade    0.56 / 0.56
    Warboss (Mega)      9.3 / 17.8      Coldstar Commander 0.28 / 0.28
    Beastboss          18.5 / 53.3
    Painboy             inf (no ranged weapons at all)
    Commander Farsight  1.7 /  2.1

The nearest pair either side of the line is Farsight at 1.67 against the
Fireblade at 0.56, so 1.0 sits in a wide gap rather than on a cliff edge. It
is still a judgement call, not a constant that was discovered.

GETTING THEM THERE
------------------
They are PLACED FIRST, from a front-to-back candidate ordering, rather than
being laid out normally and swapped forward afterwards. The swap version was
built first and measured, and it cannot work for a character whose base is
bigger than the rank and file's: game/formation_layout.py pitches its candidate
grid off the SMALLEST base in the unit (1.5" for a Boyz mob), while a 0.98"
Warboss standing next to a 0.63" Boy needs 1.66" of centre-to-centre clearance.
The only slot in the finished block he fits in is therefore the one the packer
already cleared around him - every forward swap was rejected and he stayed rank
7 of 22. Placing him first is what makes that hole form at the FRONT.

The forward limit each packer passes is the front edge of the block the unit
actually forms, taken from a plain fill done first. Without it a character
would be flung to the front of the whole candidate disc, somewhere the rest of
the squad cannot chain onto him under rule 09.02.

Both packers keep the plain placement unless the front-rank one seats at least
as many models. A failed placement is expensive everywhere this is used - an
Emergency Disembark (18.05) destroys the unit outright - so this never trades a
working formation for a better-looking one.

"""

from game import attached_units
from game.damage_estimate import expected_wounds


class _ReferenceDefender:
    """Neutral yardstick for the melee-vs-ranged comparison - see the module
    docstring. Deliberately not a real datasheet: it exists to cancel out of a
    ratio, not to predict an outcome."""

    toughness = 4
    armor_save = "4+"
    invulnerable_save = None
    wounds = 2


REFERENCE_DEFENDER = _ReferenceDefender()

# How much of a model's damage has to come from melee before it is worth
# putting in harm's way. 1.0 = "more from fighting than from shooting".
MELEE_LEAD_RATIO = 1.0


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


def is_melee_character(model, squad):
    """Both conditions from the module docstring: a 19.01 character, and one
    that is here to fight.

    attached_units.is_attached_unit() rather than the looser test, because a
    lone unattached Character IS its own unit's only Leader model - it leads
    nobody, has no formation to lead from, and there is nothing to promote it
    ahead of."""
    if not attached_units.is_attached_unit(squad):
        return False
    if not any(m is model for m in attached_units.leader_models(squad, alive_only=False)):
        return False
    return is_melee_focused(model)


def front_rank_models(squad):
    """This unit's melee characters, hardest hitter first.

    Ordered so that with two of them - the reported mob has a Warboss AND a
    Painboy - the bigger threat takes the front-most slot and the other the
    next one, rather than the order falling out of which was attached first."""
    if not attached_units.is_attached_unit(squad):
        return []
    leaders = attached_units.leader_models(squad, alive_only=False)
    fighters = [m for m in leaders if is_melee_focused(m)]
    return sorted(fighters, key=lambda m: -model_output(m, melee=True))
