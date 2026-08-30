import io

p = "test_aeldari_enhancements.py"
s = io.open(p, encoding="utf-8").read()

# 1. the fake weapon carries a REAL DiceNotation, not a string standing in for
#    one - the substitute answered no question the engine ever asks of it.
old = '''class _WNotation(_WPsychic):
    damage_notation = "D6"
'''
new = '''class _WNotation(_WPsychic):
    #: A REAL DiceNotation, not the string "D6" this stood at first. The string
    #: made the fake unable to answer the one question the rule asks of a rolled
    #: Damage - what its BONUS is - so the pin below could only ever have
    #: recorded "nothing happened".
    damage_notation = DiceNotation(6, 0)
'''
assert s.count(old) == 1
s = s.replace(old, new)

# 2. the pin itself, which recorded the wrong behaviour.
old = '''    # A rolled Damage is left alone.
    c.eq("a rolled Damage keeps its notation value",
         epw.adjusted_weapon(_WNotation(), _pw_model).damage, _W.damage)
'''
new = '''    # A ROLLED DAMAGE GETS THE BONUS TOO, on its NOTATION. "Add 1 to the Damage
    # characteristic" of a D6 weapon makes it D6+1, and rule 24.25's [MELTA]
    # already does exactly this (game/shooting.py's melta_adjusted_weapon).
    # BOTH halves are pinned: the notation because it is what the roll reads,
    # and `damage` because it is the preview shown beside it.
    _pw_rolled = epw.adjusted_weapon(_WNotation(), _pw_model)
    c.eq("a rolled Damage gains the bonus on its NOTATION",
         _pw_rolled.damage_notation.bonus, _WNotation.damage_notation.bonus + 1)
    c.eq("...the die itself is untouched", _pw_rolled.damage_notation.sides, 6)
    c.eq("...and its preview value moves with it",
         _pw_rolled.damage, _W.damage + 1)
'''
assert s.count(old) == 1
s = s.replace(old, new)

if "from game.dice_notation import DiceNotation" not in s:
    anchor = "from game.weapons import RANGED"
    assert s.count(anchor) >= 1
    s = s.replace(anchor, "from game.dice_notation import DiceNotation\n" + anchor, 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
