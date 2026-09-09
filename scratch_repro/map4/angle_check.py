"""Does the engine's angle_deg mean the same thing as the angle measured in the
image? Build the fitted rectangle as a real Obstacle and ask IT which drawn
pixels it covers - both signs, so the answer is measured, not assumed."""
import pickle, sys
sys.path.insert(0, '.')
from game.terrain import Obstacle, LIGHT
PX = 40.0
comps = pickle.load(open('scratch_repro/map4/comps.pkl','rb'))
# NW rotated ruin, fitted (13.30, 10.79) 11.02 x 6.78 @ 55.0 deg in image space
for sign in (+1, -1):
    ob = Obstacle(x_in=13.30, y_in=10.79, width_in=11.02, height_in=6.78,
                  category=LIGHT, angle_deg=sign * 55.0)
    pts = comps[4]
    inside = sum(1 for x, y in pts if ob.contains_point(x / PX, y / PX))
    print('angle_deg=%+6.1f  covers %5.1f%% of the drawn piece' % (sign * 55.0, 100.0 * inside / len(pts)))
