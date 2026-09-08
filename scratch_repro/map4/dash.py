import pygame, math
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
W, H = s.get_size()
px = pygame.PixelArray(s); get = lambda x,y: s.unmap_rgb(px[x,y])[:3]

def is_pink_dash(c):
    r, g, b = c
    return r > 240 and g == b and 150 <= g <= 225
def is_blue_dash(c):
    r, g, b = c
    return b > 240 and r < 230 and g > r and 150 <= r <= 225

pd, bd = [], []
for y in range(H):
    xs = [x for x in range(W) if is_pink_dash(get(x, y))]
    if xs:
        # one run only (contiguous); take its centre
        runs = []
        cur = [xs[0]]
        for x in xs[1:]:
            if x == cur[-1] + 1: cur.append(x)
            else: runs.append(cur); cur = [x]
        runs.append(cur)
        if len(runs) == 1 and 3 <= len(runs[0]) <= 8:
            pd.append((y, sum(runs[0]) / len(runs[0])))
    xs = [x for x in range(W) if is_blue_dash(get(x, y))]
    if xs:
        runs = []; cur = [xs[0]]
        for x in xs[1:]:
            if x == cur[-1] + 1: cur.append(x)
            else: runs.append(cur); cur = [x]
        runs.append(cur)
        if len(runs) == 1 and 3 <= len(runs[0]) <= 8:
            bd.append((y, sum(runs[0]) / len(runs[0])))
del px

def fit(d, label):
    for _ in range(6):
        n=len(d); sy=sum(p[0] for p in d); sx=sum(p[1] for p in d)
        syy=sum(p[0]*p[0] for p in d); sxy=sum(p[0]*p[1] for p in d)
        m=(n*sxy-sy*sx)/(n*syy-sy*sy); b=(sx-m*sy)/n
        res=[abs(x-(m*y+b)) for y,x in d]; med=sorted(res)[len(res)//2]
        keep=[p for p,r in zip(d,res) if r <= max(1.5, 4*med)]
        if len(keep)==len(d): break
        d=keep
    res=[abs(x-(m*y+b)) for y,x in d]
    print('%s n=%d maxres=%.2f' % (label, len(d), max(res)))
    print('   px: x = %.6f*y + %.3f' % (m, b))
    print('   in: (%.3f, 0.0) -> (%.3f, 44.0)' % (b/40.0, (m*1760+b)/40.0))
    return m, b
pm, pb = fit(pd, 'PINK dash')
bm, bb = fit(bd, 'BLUE dash')
print()
print('slope diff %.6f  (angle diff %.4f deg)' % (bm-pm, math.degrees(math.atan(bm))-math.degrees(math.atan(pm))))
gap = (bb-pb)/math.hypot(1.0, pm)
print('perpendicular gap between the two dashes: %.2f px = %.3f in' % (gap, gap/40.0))
