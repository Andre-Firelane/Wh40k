"""The Orks army rule "Waaagh!" (2026-09 codex) - who has it, and its first bullet.

PRINTED (rules/orks/army_rules.md):

    Friendly ORKS units with this ability can:
    - Re-roll advance rolls.
    - Become riled up, as stated in other rules.
    [the three riled-up effects]
    War Cry (Once per battle, per army): At the start of the Command phase, you
    can use this ability. If you do, friendly ORKS units with the Waaagh!
    ability are riled up until the end of the next turn.

WHERE EACH PART LIVES
---------------------
  * who has the ability ........ has_waaagh() / qualifying_players() below
  * the Advance re-roll ........ WaaaghAdvanceRerollController below, on
                                 game/advance_reroll_offer.py
  * riled up and its effects ... game/riled_up.py
  * War Cry .................... game/war_cry.py

WHAT WAS RETIRED WITH THE OLD RULE. The user-supplied Waaagh! this module used to
hold (a WaaaghController, +1 S and +1 A on melee weapons, a 5+ invulnerable save
and charge-after-Advance "until the start of your next Command phase") is gone,
and so are the three datasheet riders that only existed as part of it: the
Warboss's "Da Biggest and da Best", the Warboss in Mega Armour's "Dead Brutal"
and the Meganobz' Feel No Pain "Krumpin' Time". Their trigger no longer exists;
the datasheets print new abilities in their place, built with the datasheet
stages.

"Da Boss" (a WARLORD gains 1CP at the start of the battle round) is
game/da_boss.py since the Mecha Orks stage G2 gave army lists a Warlord
(game/warlord.py).
"Unstable Energies" is game/unstable_energies.py. The "Special Move Types" (pulse
jet move, assault disembark move) are rules OTHER rules point at, and no built
Ork datasheet points at either - so there is nothing to build until one does.
"""

from game.advance_reroll_offer import AdvanceRerollOfferController

WAAAGH_LABEL = "Waaagh!"


def has_waaagh(squad):
    """Whether this unit has the Waaagh! ability.

    Read as a unit-wide ability (rule 19.04) rather than off a representative
    model: an attached unit (19.01) is no longer homogeneous, and a Warboss
    joining a Boyz mob must not decide the whole mob's answer by happening to be
    (or not be) models[0]. Only Ork datasheets set the flag, and
    test_ork_army_rules.py pins it against every printed FACTION line."""
    from game.squad import unit_wide_ability
    if squad is None or not getattr(squad, "models", None):
        return False
    return bool(unit_wide_ability(squad, "waaagh"))


def qualifying_players(squads):
    """Which players' armies count as ORKS for this rule.

    The same derivation game/battle_focus.py's own qualifying_players() uses:
    this engine has no army-faction declaration, so "your Army Faction is ORKS"
    is read as "this player's army contains units with the Waaagh! ability".
    Derived rather than configured, because a config constant is the thing
    someone forgets to update - and the failure mode is an army rule firing for
    an army that does not have it (user, about the old rule: "die necrons haben
    soeben einen waagh ausgerufen. das koennen nur orks").

    Meant to be called ONCE, when the armies are complete: army faction is fixed
    at list-building and does not stop being ORKS when the last Boy dies."""
    return frozenset(
        squad.owner for squad in squads
        if squad.owner is not None
        and any(getattr(m.profile, "waaagh", False) for m in getattr(squad, "models", ()) or ())
    )


class WaaaghAdvanceRerollController(AdvanceRerollOfferController):
    """"Friendly ORKS units with this ability can: re-roll advance rolls" -
    every Advance, for every unit with the ability, with no condition."""

    LABEL = WAAAGH_LABEL

    def applies(self, squad):
        return has_waaagh(squad)
