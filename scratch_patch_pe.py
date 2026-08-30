import io

p = "test_aeldari_enhancements.py"
s = io.open(p, encoding="utf-8").read()

old = '''# ...and the psychic-weapon adjuster through the same real chain. Driven on a
# unit whose gun IS psychic, because the module's whole gate is that keyword.
with only("WARHOST_PLAYERS"):
    _pe = tk.shooting_scene(D["Farseer"], D["Guardian Defenders"], attacker_owner=HUMAN)
    tk.line_up(_pe["attacker"], 30.0, 30.0, spacing=1.2)
    tk.line_up(_pe["target"], 30.0, 33.0, spacing=1.2)
    _pe_shoot = _pe["shooting"]
    _pe_shoot.active_squad = _pe["attacker"]
    _pe_gun = next((w for w in _pe["attacker"].models[0].weapons
                    if w.weapon_type == RANGED and getattr(w, "psychic", False)
                    and w.damage_notation is None), None)
    c.true("the Farseer really carries a ranged psychic weapon", _pe_gun is not None)
    if _pe_gun is not None:
        _pe_pairs = [(m, _pe_gun) for m in _pe["attacker"].models]
        _pe_base = _pe_shoot._adjusted_weapon(_pe_pairs, _pe["target"]).damage
        E.grant(_pe["attacker"], "Psychic Destroyer")
        c.eq("the real ranged chain adds 1 Damage to it",
             _pe_shoot._adjusted_weapon(_pe_pairs, _pe["target"]).damage, _pe_base + 1)
'''

new = '''# ...and the psychic-weapon adjuster through the same real chain. Driven on a
# unit whose gun IS psychic, because the module's whole gate is that keyword.
#
# TWO BEARERS, because a ranged psychic weapon prints its Damage in TWO forms
# and the rule reaches both. MEASURED over every Aeldari datasheet: the four
# most likely bearers of a 30-point ASURYANI PSYKER Enhancement (Farseer,
# Eldrad, Farseer Skyrunner, the Yncarne) ALL print a ROLLED Damage, and the
# flat ones are the Warlock guns. A pin on one form alone would have left the
# other free - and the notation half is the one an earlier version of this
# module got wrong, skipping it outright and making the Enhancement inert on
# exactly those four.
def _psychic_gun(squad, rolled):
    """The unit's first ranged [PSYCHIC] weapon with a rolled / flat Damage."""
    return next((w for w in squad.models[0].weapons
                 if w.weapon_type == RANGED and getattr(w, "psychic", False)
                 and ((w.damage_notation is not None) == rolled)), None)


for _pe_sheet, _pe_rolled, _pe_what in (("Farseer", True, "a ROLLED Damage (D3)"),
                                        ("Warlock Conclave", False, "a flat Damage")):
    with only("WARHOST_PLAYERS"):
        _pe = tk.shooting_scene(D[_pe_sheet], D["Guardian Defenders"], attacker_owner=HUMAN)
        tk.line_up(_pe["attacker"], 30.0, 30.0, spacing=1.2)
        tk.line_up(_pe["target"], 30.0, 33.0, spacing=1.2)
        _pe_shoot = _pe["shooting"]
        _pe_shoot.active_squad = _pe["attacker"]
        _pe_gun = _psychic_gun(_pe["attacker"], _pe_rolled)
        c.true("the %s really carries a ranged psychic weapon with %s"
               % (_pe_sheet, _pe_what), _pe_gun is not None)
        if _pe_gun is not None:
            _pe_pairs = [(m, _pe_gun) for m in _pe["attacker"].models]
            _pe_in = _pe_shoot._adjusted_weapon(_pe_pairs, _pe["target"])
            _pe_base, _pe_base_bonus = _pe_in.damage, (
                _pe_in.damage_notation.bonus if _pe_in.damage_notation else None)
            E.grant(_pe["attacker"], "Psychic Destroyer")
            _pe_out = _pe_shoot._adjusted_weapon(_pe_pairs, _pe["target"])
            c.eq("the real ranged chain adds 1 Damage to the %s gun" % _pe_sheet,
                 _pe_out.damage, _pe_base + 1)
            if _pe_rolled:
                # THE HALF THAT DECIDES THE ROLL. `damage` beside it is only the
                # preview; DiceNotation.bonus is what the Damage roll actually
                # reads, so a version that moved only the preview would look
                # right here and pay nothing on the table.
                c.eq("...on its NOTATION, which is what the roll reads",
                     _pe_out.damage_notation.bonus, _pe_base_bonus + 1)
                c.eq("...and the die itself is untouched (D3 stays a D3)",
                     _pe_out.damage_notation.sides, _pe_in.damage_notation.sides)
            else:
                c.true("...and a flat Damage grows no notation",
                       _pe_out.damage_notation is None)
            # NEVER A MUTATION: the WeaponProfile class is shared by every model
            # in the game carrying that gun.
            c.eq("...and the shared instance is untouched", _pe_in.damage, _pe_base)
'''

assert s.count(old) == 1, s.count(old)
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new))
print("patched")
