"""For map3's corner zones: which rule agrees more with the board's own
corner-to-corner diagonal (the plain reading of "my half of the board")?"""
from game import maps, config
from game.game_state import GameState
import game.mission_context as mc

bm = maps.get("map3"); maps.apply_to_config(bm)
st = GameState(); bm.build(st)
zones = st.deployment_zones
W, H = bm.width_in, bm.height_in
z = {zz.owner: zz for zz in zones}

def diagonal(player, x, y):
    # P1 owns low-x/high-y, P2 high-x/low-y -> split on the (0,0)-(60,44) diagonal
    below = (y * W - x * H) >= 0          # below/left of the diagonal
    return below if player == "Player 1" else not below

def centroid_rule(player, x, y):
    opp = "Player 2" if player == "Player 1" else "Player 1"
    a = mc._zone_centre(z[player]); b = mc._zone_centre(z[opp])
    return ((x-a[0])**2+(y-a[1])**2) <= ((x-b[0])**2+(y-b[1])**2)

def shape_rule(player, x, y):
    opp = "Player 2" if player == "Player 1" else "Player 1"
    return z[player].distance_to_point(x, y) <= z[opp].distance_to_point(x, y)

for name, rule in (("centroid (today)", centroid_rule), ("shape (proposed)", shape_rule)):
    bad = 0; tot = 0
    for i in range(201):
        x = W*i/200.0
        for j in range(201):
            y = H*j/200.0
            tot += 1
            if rule("Player 1", x, y) != diagonal("Player 1", x, y): bad += 1
    print('%-18s disagrees with the board diagonal on %5d of %d points (%.2f%%)' % (name, bad, tot, 100.0*bad/tot))

print()
print('centroids:', mc._zone_centre(z["Player 1"]), mc._zone_centre(z["Player 2"]))
