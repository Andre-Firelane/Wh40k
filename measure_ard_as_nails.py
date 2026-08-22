"""How often 'Ard as Nails' three conditions actually all hold, and how much
the damage estimate they rest on is missing.

Run: python measure_ard_as_nails.py

WHY THIS EXISTS
---------------
game/ard_as_nails.py fires on a user-specified rule: at least 100 points, more
than half its models, and the incoming attack is expected to take at least half
of what is left of it. The first two are exact reads of the unit. The third is game/damage_estimate.py's ESTIMATE,
and that estimate reads printed weapon characteristics only - every
ability/stratagem that changes them at resolution time (Volley Fire, Bonded
Heroes, Waaagh!, Get Stuck In's [SUSTAINED HITS], Starscythe, Drive-by Dakka,
The Arro'kon Protocol, [MELTA]) is applied inside game/shooting.py and
game/fight.py, not here.

So the estimate is a LOWER bound on incoming damage, which means this stratagem
fires LESS often than the printed rule would. Section 3 measures that gap on
the one case the user asked about (Breachers with a Cadre Fireblade attached:
Volley Fire takes them from 20 shots to 30).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game import maps
from game.ard_as_nails import MIN_MODEL_LOSS_FRACTION, expected_models_lost, is_eligible_unit, is_worth_using, remaining_wounds
from game.attached_units import attach
from game.damage_estimate import expected_wounds_against
from game.factions import build_squad
from game.factions.orks import (
    BOYZ, DEFFKOPTAS, DEFF_DREAD, GRETCHIN, MEGANOBZ, STORMBOYZ, TANKBUSTAS, TRUKK, WARBIKERS,
)
from game.factions.tau_empire import (
    BREACHER_TEAM, CADRE_FIREBLADE, CRISIS_STARSCYTHE, DEVILFISH, GHOSTKEEL_BATTLESUIT, KROOT_CARNIVORES,
    STEALTH_BATTLESUITS, STRIKE_TEAM,
)
from game.game_state import GameState
from game.squad import is_at_half_strength, squad_has_volley_fire

maps.apply_to_config(maps.get("map2"))

ORK_TARGETS = [
    ("Boyz", BOYZ, {}), ("Gretchin", GRETCHIN, {}), ("Meganobz", MEGANOBZ, dict(composition_index=1)),
    ("Stormboyz", STORMBOYZ, dict(composition_index=1)), ("Trukk", TRUKK, {}), ("Deff Dread", DEFF_DREAD, {}),
    ("Tankbustas", TANKBUSTAS, {}), ("Deffkoptas", DEFFKOPTAS, {}), ("Warbikers", WARBIKERS, dict(composition_index=0)),
]
TAU_ATTACKERS = [
    ("Breacher Team", BREACHER_TEAM), ("Crisis Starscythe", CRISIS_STARSCYTHE), ("Kroot Carnivores", KROOT_CARNIVORES),
    ("Ghostkeel", GHOSTKEEL_BATTLESUIT), ("Stealth Battlesuits", STEALTH_BATTLESUITS), ("Strike Team", STRIKE_TEAM),
    ("Devilfish", DEVILFISH),
]


def trimmed(sheet, kwargs, keep):
    """A unit with only `keep` models still standing, casualties applied the
    way the real game applies them (GameState.remove_dead_models()) -
    is_at_half_strength() counts len(squad.models), so leaving dead tokens in
    the list would make every trimmed unit look full-strength."""
    st = GameState()
    squad = build_squad(sheet, "Player 2", name="target", **kwargs)
    for mdl in squad.models:
        mdl.x_in = mdl.y_in = 10.0
        st.add_token(mdl)
    if keep is not None and keep < len(squad.models):
        for mdl in squad.models[keep:]:
            mdl.current_wounds = 0
        st.remove_dead_models()
    return squad


print("=" * 78)
print("1. TARGET eligibility across the Ork army (ORKS, not GROTS/MONSTER/VEHICLE)")
print("=" * 78)
for name, sheet, kwargs in ORK_TARGETS:
    squad = trimmed(sheet, kwargs, None)
    print(f"  {name:12} {str(squad.points):>4} pts  {len(squad.models):2} models  "
          f"eligible={'yes' if is_eligible_unit(squad) else 'no '}")

print()
print("=" * 78)
print("2. How often all three conditions hold, over every above-half state")
print("=" * 78)
fires, total = [], 0
for name, sheet, kwargs in ORK_TARGETS:
    for keep in range(1, 13):
        target = trimmed(sheet, kwargs, keep)
        if keep >= len(target.models) + 1 or is_at_half_strength(target) or not is_eligible_unit(target):
            continue
        for aname, asheet in TAU_ATTACKERS:
            attacker = build_squad(asheet, "Player 1", name="attacker")
            total += 1
            for melee in (False, True):
                if is_worth_using(attacker, target, melee=melee):
                    fires.append((name, keep, len(target.models), target.points,
                                  expected_models_lost(attacker, target, melee=melee),
                                  aname, "melee" if melee else "shooting"))
for row in fires:
    print(f"  FIRES  {row[0]:11} {row[1]:2}/{row[2]:2} models left, {row[3]:3} pts  "
          f"vs {row[5]:19} {row[6]:8} - loses ~{row[4]:.1f} "
          f"(needs {row[2] * MIN_MODEL_LOSS_FRACTION:.1f})")
print(f"\n  {len(fires)} of {total} above-half matchups qualify "
      f"({100.0 * len(fires) / max(total, 1):.1f}%)")
print(f"  Threshold: lose at least {MIN_MODEL_LOSS_FRACTION:.0%} of the models still standing.")
print("  The stricter 'would be destroyed outright' version measured 1 of 126 here, which")
print("  is why it was relaxed. Note section 3: the estimate UNDERSTATES every attack,")
print("  so the true rate is higher than whatever this prints.")

print()
print("=" * 78)
print("3. What the estimate does NOT count (the user's own two examples)")
print("=" * 78)
st = GameState()
breachers = build_squad(BREACHER_TEAM, "Player 1", name="Breachers")
fireblade = build_squad(CADRE_FIREBLADE, "Player 1", name="Cadre Fireblade")
stormboyz = build_squad(STORMBOYZ, "Player 2", name="Stormboyz", composition_index=1)
for mdl in list(breachers.models) + list(fireblade.models):
    mdl.x_in, mdl.y_in = 20.0, 20.0
    st.add_token(mdl)
for mdl in stormboyz.models:
    mdl.x_in, mdl.y_in = 20.0, 26.0
    st.add_token(mdl)

alone = expected_wounds_against(breachers, stormboyz)
printed_shots = sum(
    w.attacks for m in breachers.models for w in m.weapons if getattr(w, "weapon_type", None) == "ranged"
)
attach(fireblade, breachers, st)
led = expected_wounds_against(breachers, stormboyz)
led_shots = sum(
    w.attacks for m in breachers.models for w in m.weapons if getattr(w, "weapon_type", None) == "ranged"
)
real_shots = led_shots + sum(
    1 for m in breachers.models for w in m.weapons if getattr(w, "weapon_type", None) == "ranged"
)
print(f"  Breacher Team alone            : estimate {alone:5.2f} wounds, {printed_shots} printed shots")
print(f"  Breacher Team + Cadre Fireblade: estimate {led:5.2f} wounds, {led_shots} printed shots")
print(f"  Volley Fire active on the unit : {squad_has_volley_fire(breachers)}")
print(f"  ...but the shots it will ACTUALLY fire are {real_shots} (+1 Attack per ranged weapon),")
print(f"     so the estimate is short by roughly {100.0 * (real_shots - led_shots) / led_shots:.0f}%.")
print()
print("  Not counted, all applied at resolution time instead:")
for line in (
    "Volley Fire (Cadre Fireblade)        +1 Attack per ranged weapon in the led unit",
    "Bonded Heroes (Retaliation Cadre)    +1 S within 12\", +1 AP within 9\", BATTLESUITs",
    "Coldstar Commander                   [ASSAULT] on the led unit's ranged weapons",
    "Waaagh! (Orks army rule)             +1 A and +1 S on melee weapons while active",
    "Get Stuck In (War Horde)             [SUSTAINED HITS 1] on every Ork melee weapon",
    "Unbridled Carnage (War Horde)        Critical Hits on 5+, so more of the above",
    "The Arro'kon Protocol                [SUSTAINED HITS 1/2] vs big units",
    "Might is Right (Warboss)             +1 to melee Hit rolls in the led unit",
    "Starscythe / Drive-by Dakka          weapon characteristic changes",
    "[MELTA X], re-rolls, [LETHAL HITS], [DEVASTATING WOUNDS], [BLAST], cover",
):
    print(f"    - {line}")
print()
print("  Direction of the error: the estimate UNDERSTATES almost every attack, so")
print("  'Ard as Nails fires less often than the printed rule would, never more.")
