"""Orks datasheet ability: Trukk's Grot Riggers, as supplied by the user
(not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/starscythe.py etc. for the equivalent T'au
abilities).

RULE: at the start of your Command phase, this model regains 1 lost wound."""


def apply_grot_riggers(all_tokens, player):
    """Called once at the start of `player`'s own Command phase (see
    main.py's advance_turn_phase(), same hook as
    support_turret_controller.expire_for()). "This model" (singular,
    per-model wording, unlike e.g. Fieldcraft's "this unit") heals
    independently of the rest of its squad, so this loops tokens directly
    rather than through a squad_has_*() whole-unit check."""
    for token in all_tokens:
        if token.squad is None or token.squad.owner != player:
            continue
        if not token.profile.grot_riggers:
            continue
        if token.is_dead():
            continue
        if token.current_wounds < token.profile.wounds:
            token.current_wounds += 1
