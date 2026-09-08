"""Old rule (bisector of the two zone CENTROIDS) vs the shape rule (closer to
which zone), over a 201x201 grid on every shipped map, for both players."""
from game import maps, config
from game.game_state import GameState
import game.mission_context as mc

class Ctx:
    def __init__(self, zones, player, opponent):
        self.deployment_zones = zones; self.player = player; self.opponent = opponent

def old_rule(ctx, x, y):
    mine = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    theirs = [z for z in ctx.deployment_zones if z.owner == ctx.opponent]
    if not mine or not theirs: return True
    mc_ = mc._zone_centre(mine[0]); tc = mc._zone_centre(theirs[0])
    return ((x-mc_[0])**2 + (y-mc_[1])**2) <= ((x-tc[0])**2 + (y-tc[1])**2)

def shape_rule(ctx, x, y):
    mine = [z for z in ctx.deployment_zones if z.owner == ctx.player]
    theirs = [z for z in ctx.deployment_zones if z.owner == ctx.opponent]
    if not mine or not theirs: return True
    return mine[0].distance_to_point(x, y) <= theirs[0].distance_to_point(x, y)

for key in ("map1", "map2", "map3"):
    bm = maps.get(key); maps.apply_to_config(bm)
    st = GameState(); bm.build(st)
    zones = st.deployment_zones
    W, H = bm.width_in, bm.height_in
    for player, opp in (("Player 1", "Player 2"), ("Player 2", "Player 1")):
        ctx = Ctx(zones, player, opp)
        diff = 0; tot = 0
        for i in range(201):
            x = W * i / 200.0
            for j in range(201):
                y = H * j / 200.0
                tot += 1
                if old_rule(ctx, x, y) != shape_rule(ctx, x, y): diff += 1
        print('%-5s %-9s  %d of %d points change hands (%.2f%%)' % (key, player, diff, tot, 100.0*diff/tot))
