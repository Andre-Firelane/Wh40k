"""Corrects both +1 Damage Enhancements: a rolled Damage gets the bonus on its
NOTATION, it is not skipped."""
import io

NOTE = '''
A ROLLED DAMAGE GETS THE BONUS TOO, on its NOTATION. My first version skipped a
weapon whose Damage is a notation, reasoning that adding to the preview value
would be overwritten by the roll - true of the preview, and the wrong
conclusion. "Add 1 to the Damage characteristic" of a D3 weapon makes it D3+1,
and DiceNotation carries a `bonus` field for exactly that; rule 24.25's [MELTA]
already does it this way (game/shooting.py's melta_adjusted_weapon), as does
Psychic Communion for an Attacks notation. BOTH are updated - the notation so
the roll is right, and `damage` so the preview beside it agrees.

IT MATTERS HERE MORE THAN ANYWHERE: measured, EVERY ranged psychic weapon a
Farseer, Eldrad, a Farseer Skyrunner or the Yncarne carries prints a rolled
Damage. Skipping notations would have made a 30-point Enhancement inert on
four of its most likely bearers, and a probe on a flat-damage weapon would
never have shown it.
'''

# --- Psychic Destroyer -----------------------------------------------------
p = "game/enh_psychic_weapons.py"
s = io.open(p, encoding="utf-8").read()
old = '''    if _is_ranged_psychic(weapon) and _bearer_has(model, PSYCHIC_DESTROYER):
        # A rolled Damage is left alone - adding to a notation's PREVIEW value
        # would be overwritten by the roll, the trap game/hand_of_asuryan.py
        # records for its own Damage override.
        if getattr(weapon, "damage_notation", None) is None:
            out = out if out is not None else copy.copy(weapon)
            out.damage = weapon.damage + PSYCHIC_DESTROYER_DAMAGE
'''
new = '''    if _is_ranged_psychic(weapon) and _bearer_has(model, PSYCHIC_DESTROYER):
        out = out if out is not None else copy.copy(weapon)
        out.damage = weapon.damage + PSYCHIC_DESTROYER_DAMAGE
        # A ROLLED Damage gets the bonus on its NOTATION - see the docstring.
        if weapon.damage_notation is not None:
            out.damage_notation = DiceNotation(
                weapon.damage_notation.sides,
                weapon.damage_notation.bonus + PSYCHIC_DESTROYER_DAMAGE)
'''
assert s.count(old) == 1
s = s.replace(old, new)
s = s.replace('''NEVER A DOWNGRADE, AND NEVER A MUTATION.''', NOTE.strip() + '''

NEVER A DOWNGRADE, AND NEVER A MUTATION.''')
s = s.replace("from game.weapons import RANGED",
              "from game.dice_notation import DiceNotation\nfrom game.weapons import RANGED", 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("Psychic Destroyer corrected")

# --- Aspect of Murder ------------------------------------------------------
p = "game/enh_aspect_of_murder.py"
s = io.open(p, encoding="utf-8").read()
old = '''    out = copy.copy(weapon)
    # A rolled Damage keeps whatever it prints - see the docstring.
    if getattr(weapon, "damage_notation", None) is None:
        out.damage = weapon.damage + ASPECT_OF_MURDER_DAMAGE
    out.precision = True
    return out'''
new = '''    out = copy.copy(weapon)
    out.damage = weapon.damage + ASPECT_OF_MURDER_DAMAGE
    # A ROLLED Damage gets the bonus on its NOTATION, not skipped - see the
    # docstring, and rule 24.25's [MELTA] for the same treatment.
    if weapon.damage_notation is not None:
        out.damage_notation = DiceNotation(
            weapon.damage_notation.sides,
            weapon.damage_notation.bonus + ASPECT_OF_MURDER_DAMAGE)
    out.precision = True
    return out'''
assert s.count(old) == 1
s = s.replace(old, new)
old = '''A ROLLED DAMAGE IS LEFT ALONE. Adding 1 to a notation's preview value would be
overwritten by the roll - the trap game/hand_of_asuryan.py records for its own
Damage override. Named rather than left as a silent branch.'''
new = '''A ROLLED DAMAGE GETS THE BONUS ON ITS NOTATION, not skipped. "Add 1 to the
Damage characteristic" of a D3 weapon makes it D3+1, and DiceNotation carries a
`bonus` field for exactly that - rule 24.25's [MELTA] already does it this way.
Both halves are written: the notation so the roll is right, and `damage` so the
preview beside it agrees.'''
assert s.count(old) == 1
s = s.replace(old, new)
s = s.replace("from game.weapons import RANGED",
              "from game.dice_notation import DiceNotation\nfrom game.weapons import RANGED", 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("Aspect of Murder corrected")
