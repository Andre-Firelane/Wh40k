"""Minimum-area rectangle (rotating calipers on the convex hull) and the upright
percentile box for every terrain component, plus the FILL fraction that map3's
recipe uses to tell a genuinely rotated rectangle from a wedge."""
import pickle, math
PX = 40.0
comps = pickle.load(open('scratch_repro/map4/comps.pkl','rb'))

def hull(pts):
    pts = sorted(set(pts))
    if len(pts) <= 2: return pts
    def half(ps):
        out = []
        for p in ps:
            while len(out) >= 2:
                (ax,ay),(bx,by) = out[-2], out[-1]
                if (bx-ax)*(p[1]-ay) - (by-ay)*(p[0]-ax) <= 0: out.pop()
                else: break
            out.append(p)
        return out
    return half(pts)[:-1] + half(pts[::-1])[:-1]

def min_area_rect(pts):
    h = hull(pts)
    best = None
    n = len(h)
    for i in range(n):
        x0,y0 = h[i]; x1,y1 = h[(i+1) % n]
        dx,dy = x1-x0, y1-y0
        L = math.hypot(dx,dy)
        if L < 1e-9: continue
        ux,uy = dx/L, dy/L
        us = [p[0]*ux + p[1]*uy for p in h]
        vs = [-p[0]*uy + p[1]*ux for p in h]
        w = max(us)-min(us); ht = max(vs)-min(vs)
        if best is None or w*ht < best[0]:
            cu = (max(us)+min(us))/2; cv = (max(vs)+min(vs))/2
            cx = cu*ux - cv*uy; cy = cu*uy + cv*ux
            best = (w*ht, cx, cy, w, ht, math.degrees(math.atan2(dy,dx)))
    return best

def pct_box(pts, lo=2, hi=98):
    xs = sorted(p[0] for p in pts); ys = sorted(p[1] for p in pts)
    def q(a, p): return a[max(0, min(len(a)-1, int(round(p/100.0*(len(a)-1)))))]
    x0,x1,y0,y1 = q(xs,lo), q(xs,hi), q(ys,lo), q(ys,hi)
    return (x0+x1)/2.0, (y0+y1)/2.0, x1-x0, y1-y0

print('%-3s %8s | %-34s %6s | %-30s %6s' % ('#','area','MIN-AREA RECT (in, deg)','fill','UPRIGHT 2/98 BOX (in)','fill'))
for k, c in enumerate(comps):
    if len(c) < 2000: continue
    area, cx, cy, w, h, ang = min_area_rect(c)
    # normalise angle to (-90, 90] and make w the longer side reported as given
    a = ang
    while a <= -90: a += 180
    while a > 90: a -= 180
    fill_rot = len(c) / area
    ux,uy,uw,uh = pct_box(c)
    fill_up = len(c) / (uw*uh) if uw*uh else 0
    print('%-3d %8d | (%6.2f,%6.2f) %6.2f x %5.2f @ %6.1f %5.0f%% | (%6.2f,%6.2f) %6.2f x %5.2f %5.0f%%'
          % (k, len(c), cx/PX, cy/PX, w/PX, h/PX, a, 100*fill_rot,
             ux/PX, uy/PX, uw/PX, uh/PX, 100*fill_up))
