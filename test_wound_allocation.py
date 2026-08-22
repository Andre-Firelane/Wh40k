"""Regression tests for the two user reports about wound allocation:

  "ki ligt wunden immer zuerst auf den squad leader. das ist dumm. auf den
   solllten wunden immer zuletzt gelegt werden."
  "bei mir wird die erste wunde auch atomatisch auf den squad leader gelegt.
   das soll nicht so sein."

Two independent causes, one per report:

  1. Squad.allocation_groups()' ordering key (_group_weakness) tied on every
     term for a fresh 2W leader vs fresh 1W rank and file, so the stable sort
     fell back on datasheet order and put the LEADER'S group first. Its group
     holds only that one model, so no choice was ever offered to either
     player - the wound was applied automatically. Affects Strike Team, Boyz,
     Stormboyz, Warbikers (leader has more W than its squad).

  2. ai/agent_driver.py's _resolve_own_damage_choice() picked candidates[0]
     within the offered group, and a datasheet lists its leader first.
     Affects the squads whose leader shares its squad's W and Sv and is
     therefore in the SAME group: Breacher Team, Kroot, Stealth, Tankbustas.

Run: python test_wound_allocation.py
"""
import sys

from ai.agent_driver import _resolve_own_damage_choice, _wound_allocation_pick
from game.damage_resolution import DamageAllocationSession, MortalWoundAllocationSession
from game.factions import build_squad
from game.factions import orks, tau_empire
from game.weapons import WeaponProfile

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print(f"  {'OK  ' if condition else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")


class _TestGun(WeaponProfile):
    """AP-4 D1: every save fails on the rolls these tests feed in (a roll of
    1 is an automatic failure per rule 05.04 anyway), so each roll passed to
    DamageAllocationSession becomes exactly one allocated wound."""
    name = "Test gun"
    strength = 8
    ap = -4
    damage = 1


class _StubController:
    """The two-member protocol every real controller exposes for wound
    allocation (ShootingController/FightController/HazardRollStep/... all
    have exactly this pair) - lets _resolve_own_damage_choice() drive a REAL
    DamageAllocationSession without standing up a whole hit/wound/save
    machine around it."""

    def __init__(self, session):
        self.session = session

    @property
    def pending_damage_choice(self):
        return self.session.pending_choice

    def choose_damage_model(self, model):
        self.session.choose_model(model)


def squad_of(datasheet, name, owner="Player 2", **kwargs):
    return build_squad(datasheet, owner=owner, name=name, x_in=10, y_in=10, **kwargs)


def leaders(models):
    return [m for m in models if m.profile.squad_leader]


print("\n--- 1. the leader's group is no longer allocated first (report 2) ---")
# Strike Team is built exactly as main.py's demo scene builds it: the Shield
# Drone on the Shas'ui adds 1 to its Wounds characteristic (game/drones.py),
# which is what put it in a tougher one-model group of its own in the first
# place. Without that gear the Shas'ui is W1 and shares the squad's group,
# i.e. the reported bug simply doesn't arise - so the gear is the test case.
SHAS_UI_GEAR = {"Fire Warrior Shas'ui": ["Guardian Drone", "Shield Drone"]}
for label, datasheet, gear in (("Strike Team", tau_empire.STRIKE_TEAM, SHAS_UI_GEAR),
                               ("Boyz", orks.BOYZ, None), ("Stormboyz", orks.STORMBOYZ, None),
                               ("Warbikers", orks.WARBIKERS, None)):
    squad = squad_of(datasheet, label, gear=gear)
    groups = squad.allocation_groups()
    tougher_leader = any(m.profile.wounds > min(x.profile.wounds for x in squad.models)
                         for m in leaders(squad.models))
    check(f"{label}: leader model IS tougher than the rank and file (precondition)", tougher_leader)
    check(f"{label}: leader's group sorts LAST, not first",
          not leaders(groups[0]) and leaders(groups[-1]),
          f"first={[m.profile.name for m in groups[0]][:1]}, last={[m.profile.name for m in groups[-1]]}")
    session = DamageAllocationSession([1], _TestGun(), squad)
    check(f"{label}: the first wound OFFERS a choice instead of auto-applying",
          session.pending_choice is not None and len(session.pending_choice) > 1,
          f"{len(session.pending_choice or [])} candidate(s)")
    check(f"{label}: the leader is not among the first wound's candidates",
          session.pending_choice is not None and not leaders(session.pending_choice))

print("\n--- 2. within one shared group, the AI picks a non-leader (report 1) ---")
for label, datasheet in (("Breacher Team", tau_empire.BREACHER_TEAM),
                         ("Kroot", tau_empire.KROOT_CARNIVORES),
                         ("Stealth", tau_empire.STEALTH_BATTLESUITS),
                         ("Tankbustas", orks.TANKBUSTAS)):
    squad = squad_of(datasheet, label)
    groups = squad.allocation_groups()
    check(f"{label}: leader shares its squad's group (precondition)",
          len(groups) == 1 and bool(leaders(groups[0])))
    session = DamageAllocationSession([1], _TestGun(), squad)
    check(f"{label}: the leader IS among the candidates (so it is a real choice)",
          bool(leaders(session.pending_choice)))
    check(f"{label}: candidates[0] is still the leader (the old pick - reproduces the report)",
          session.pending_choice[0].profile.squad_leader)
    check(f"{label}: _wound_allocation_pick() picks a non-leader instead",
          not _wound_allocation_pick(session.pending_choice).profile.squad_leader,
          _wound_allocation_pick(session.pending_choice).profile.name)

print("\n--- 3. end to end: the AI hook kills rank and file, never the leader ---")
for label, datasheet, wounds in (("Tankbustas", orks.TANKBUSTAS, 8), ("Kroot", tau_empire.KROOT_CARNIVORES, 5),
                                 ("Boyz", orks.BOYZ, 5)):
    squad = squad_of(datasheet, label, owner="Player 2")
    controller = _StubController(DamageAllocationSession([1] * wounds, _TestGun(), squad))
    resolved = _resolve_own_damage_choice("Player 2", [controller])
    dead = [m for m in squad.models if m.is_dead()]
    check(f"{label}: the AI resolved the allocation", resolved is True)
    check(f"{label}: models actually died", len(dead) > 0, f"{len(dead)} dead")
    check(f"{label}: the leader is untouched while rank and file remain",
          all(m.current_wounds == m.profile.wounds for m in leaders(squad.models)),
          ", ".join(f"{m.profile.name} {m.current_wounds}/{m.profile.wounds}" for m in leaders(squad.models)))

print("\n--- 4. the rules still win over the preference ---")
squad = squad_of(orks.TANKBUSTAS, "Tankbustas", owner="Player 2")
squad.models[3].apply_damage(1)  # a wounded rank-and-file model
session = DamageAllocationSession([1], _TestGun(), squad)
check("a single already-damaged model is forced, no choice offered (05.04 step 1)",
      session.pending_choice is None and squad.models[3].is_dead())

squad = squad_of(orks.TANKBUSTAS, "Tankbustas", owner="Player 2")
leader = leaders(squad.models)[0]
leader.apply_damage(1)
session = DamageAllocationSession([1], _TestGun(), squad)
check("a damaged LEADER is still forced to take the next wound (rules beat leader-last)",
      session.pending_choice is None and leader.is_dead())

squad = squad_of(orks.TANKBUSTAS, "Tankbustas", owner="Player 2")
for model in squad.models:
    if not model.profile.squad_leader:
        model.apply_damage(model.profile.wounds)
session = DamageAllocationSession([1], _TestGun(), squad)
candidates = session.pending_choice or [m for m in squad.models if not m.is_dead()]
check("with only the leader left, the pick still returns it (no crash, no empty pick)",
      _wound_allocation_pick(candidates).profile.squad_leader)

print("\n--- 5. mortal wounds (06.02) use the same pick ---")
squad = squad_of(orks.TANKBUSTAS, "Tankbustas", owner="Player 2")
controller = _StubController(MortalWoundAllocationSession(squad, 4))
_resolve_own_damage_choice("Player 2", [controller])
check("mortal wounds spare the leader too",
      all(m.current_wounds == m.profile.wounds for m in leaders(squad.models))
      and any(m.is_dead() for m in squad.models))

squad = squad_of(tau_empire.BREACHER_TEAM, "Breacher", owner="Player 2")
fireblade = squad_of(tau_empire.CADRE_FIREBLADE, "Fireblade", owner="Player 2")
from game import attached_units  # noqa: E402 - only needed for this one case
attached_units.attach(fireblade, squad)
session = MortalWoundAllocationSession(squad, 1)
check("an attached CHARACTER is still protected first (06.02, unchanged)",
      session.pending_choice is not None and not any(m.profile.character for m in session.pending_choice))

print("\n--- 6. an opponent-owned choice is still left to the human ---")
squad = squad_of(orks.TANKBUSTAS, "Tankbustas", owner="Player 1")
controller = _StubController(DamageAllocationSession([1], _TestGun(), squad))
check("_resolve_own_damage_choice() does not touch Player 1's own allocation",
      _resolve_own_damage_choice("Player 2", [controller]) is None
      and controller.pending_damage_choice is not None)

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED: " + "; ".join(FAIL))
sys.exit(1 if FAIL else 0)
