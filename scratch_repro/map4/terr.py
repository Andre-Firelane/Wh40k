import math
from game import shapes, config
from game.deployment import DeploymentZone
from game import mission_context as mc

W, H = 60.0, 44.0
def zone(sign):
    # sign=+1 -> high-x side (P2), -1 -> low-x side (P1)
    if sign < 0:
        edge = shapes.HalfPlane.through(0.0, 0.0, 30.0, 44.0, 0.0, 44.0)
    else:
        edge = shapes.HalfPlane.through(30.0, 0.0, 60.0, 44.0, 60.0, 0.0)
    return shapes.Intersection([edge,
        shapes.HalfPlane(1,0,0), shapes.HalfPlane(-1,0,-W),
        shapes.HalfPlane(0,1,0), shapes.HalfPlane(0,-1,-H)])

config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN = W, H
z1 = DeploymentZone("Player 1", shape=zone(-1))
z2 = DeploymentZone("Player 2", shape=zone(+1))
print('centroid P1', z1.shape.centroid(board_box=(0,0,W,H)))
print('centroid P2', z2.shape.centroid(board_box=(0,0,W,H)))
c1 = z1.shape.centroid(board_box=(0,0,W,H)); c2 = z2.shape.centroid(board_box=(0,0,W,H))
d = (c2[0]-c1[0], c2[1]-c1[1])
print('centroid-join dir', d, 'bisector dir (perp)', (-d[1], d[0]))
print('bisector dx/dy = %.4f' % (-d[1]/d[0]) if d[0] else 'inf')
print('zone edge dx/dy = %.4f' % (30.0/44.0))
print('bisector angle from vertical %.2f deg, zone edge %.2f deg'
      % (math.degrees(math.atan2(abs(d[1]), abs(d[0]))), math.degrees(math.atan(30.0/44.0))))
