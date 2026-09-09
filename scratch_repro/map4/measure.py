"""The measurement map4 is transcribed from: one clean rectangle per drawn piece.

Angle from the minimum-area rectangle; centre and size from the 2nd/98th
percentile along THAT rectangle's own axes (map3's recipe - the art draws
irregular rubble past each footprint's edge, and the percentile fit discards it).
Coverage is reported both ways so the trim is a measured number, not a claim."""
import pickle, math, collections, pygame
pygame.init()
srf = pygame.image.load('Sprites/map4.png').convert(24)
raw = pygame.image.tostring(srf, 'RGB')
W, H, PX = 2400, 1760, 40.0
def rgb(x, y):
    i = (y * W + x) * 3
    return raw[i], raw[i+1], raw[i+2]

comps = pickle.load(open('scratch_repro/map4/comps.pkl','rb'))

def components_of(pts):
    S = set(pts); out = []; seen = set()
    for p in pts:
        if p in seen: continue
        stack=[p]; seen.add(p); grp=[]
        while stack:
            q = stack.pop(); grp.append(q); x,y = q
            for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if n in S and n not in seen: seen.add(n); stack.append(n)
        out.append(grp)
    return sorted(out, key=len, reverse=True)

def erode(pts, k):
    S = set(pts)
    for _ in range(k):
        S = {(x,y) for (x,y) in S
             if (x-1,y) in S and (x+1,y) in S and (x,y-1) in S and (x,y+1) in S}
    return S

def split_two(pts):
    seeds = [g for g in components_of(list(erode(pts, 12))) if len(g) >= 200][:2]
    cent = [(sum(p[0] for p in g)/len(g), sum(p[1] for p in g)/len(g)) for g in seeds]
    groups = [[], []]
    for p in pts:
        d0 = (p[0]-cent[0][0])**2 + (p[1]-cent[0][1])**2
        d1 = (p[0]-cent[1][0])**2 + (p[1]-cent[1][1])**2
        groups[0 if d0 <= d1 else 1].append(p)
    return groups

def hull(pts):
    pts = sorted(set(pts))
    def half(ps):
        out = []
        for p in ps:
            while len(out) >= 2:
                (ax,ay),(bx,by) = out[-2], out[-1]
                if (bx-ax)*(p[1]-ay)-(by-ay)*(p[0]-ax) <= 0: out.pop()
                else: break
            out.append(p)
        return out
    return half(pts)[:-1] + half(pts[::-1])[:-1]

def best_angle(pts):
    h = hull(pts); n = len(h); best = None
    for i in range(n):
        x0,y0 = h[i]; x1,y1 = h[(i+1) % n]
        dx,dy = x1-x0, y1-y0; L = math.hypot(dx,dy)
        if L < 1e-9: continue
        ux,uy = dx/L, dy/L
        us = [p[0]*ux+p[1]*uy for p in h]; vs = [-p[0]*uy+p[1]*ux for p in h]
        a = (max(us)-min(us)) * (max(vs)-min(vs))
        if best is None or a < best[0]: best = (a, math.degrees(math.atan2(dy,dx)))
    return best[1]

def fit(pts, angle_deg, lo=2.0, hi=98.0):
    r = math.radians(angle_deg); ux,uy = math.cos(r), math.sin(r)
    us = sorted(p[0]*ux+p[1]*uy for p in pts)
    vs = sorted(-p[0]*uy+p[1]*ux for p in pts)
    def q(a,p): return a[max(0,min(len(a)-1,int(round(p/100.0*(len(a)-1)))))]
    u0,u1,v0,v1 = q(us,lo), q(us,hi), q(vs,lo), q(vs,hi)
    cu,cv = (u0+u1)/2.0, (v0+v1)/2.0
    cx = cu*ux - cv*uy; cy = cu*uy + cv*ux
    return cx, cy, u1-u0, v1-v0

def coverage(pts, cx, cy, w, h, angle_deg):
    r = math.radians(angle_deg); ux,uy = math.cos(r), math.sin(r)
    inside = 0
    for x,y in pts:
        dx,dy = x-cx, y-cy
        u = dx*ux + dy*uy; v = -dx*uy + dy*ux
        if abs(u) <= w/2 and abs(v) <= h/2: inside += 1
    # how much of the RECTANGLE is drawn terrain
    S = set(pts); hit = tot = 0
    steps_u = max(2, int(w/3)); steps_v = max(2, int(h/3))
    for i in range(steps_u):
        u = -w/2 + w*(i+0.5)/steps_u
        for j in range(steps_v):
            v = -h/2 + h*(j+0.5)/steps_v
            x = int(round(cx + u*ux - v*uy)); y = int(round(cy + u*uy + v*ux))
            tot += 1
            if (x,y) in S: hit += 1
    return inside/len(pts), hit/tot

def palette(pts):
    g = gold = grey = 0
    for x,y in pts:
        r,gr,b = rgb(x,y)
        if gr > r and gr > b and gr >= 95: g += 1
        elif r > b + 40 and gr > b: gold += 1
        else: grey += 1
    n = len(pts)
    return g/n, gold/n, grey/n

pieces = []
for k, c in enumerate(comps):
    if len(c) < 2000: continue
    if k == 13: continue                       # the central objective ICON, not terrain
    if k in (5, 6):
        for g in split_two(c): pieces.append((k, g))
    else:
        pieces.append((k, c))

print('%-4s %8s | %-38s | %-13s | %s' % ('src','px','FIT  centre(in)  w x h  @ angle','cover drawn/rect','green/gold/grey'))
rows = []
for k, c in pieces:
    a = best_angle(c)
    while a <= -90: a += 180
    while a > 90: a -= 180
    cx, cy, w, h = fit(c, a)
    if w < h:                                   # report the long side first, consistently
        a2 = a + 90
        while a2 > 90: a2 -= 180
        cx, cy, w, h = fit(c, a2); a = a2
    cd, cr = coverage(c, cx, cy, w, h, a)
    gr, go, gy = palette(c)
    rows.append((cx/PX, cy/PX, w/PX, h/PX, a, k))
    print('%-4d %8d | (%6.2f,%6.2f) %6.2f x %5.2f @ %6.1f | %4.0f%% / %4.0f%% | %3.0f%% %3.0f%% %3.0f%%'
          % (k, len(c), cx/PX, cy/PX, w/PX, h/PX, a, 100*cd, 100*cr, 100*gr, 100*go, 100*gy))
pickle.dump(rows, open('scratch_repro/map4/rows.pkl','wb'))
