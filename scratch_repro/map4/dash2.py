import pygame, math
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
W, H = s.get_size()
px = pygame.PixelArray(s); get = lambda x,y: s.unmap_rgb(px[x,y])[:3]

def fit(d, label):
    d = list(d)
    for _ in range(8):
        n=len(d); sy=sum(p[0] for p in d); sx=sum(p[1] for p in d)
        syy=sum(p[0]*p[0] for p in d); sxy=sum(p[0]*p[1] for p in d)
        m=(n*sxy-sy*sx)/(n*syy-sy*sy); b=(sx-m*sy)/n
        res=[abs(x-(m*y+b)) for y,x in d]; med=sorted(res)[len(res)//2]
        keep=[p for p,r in zip(d,res) if r <= max(1.0, 4*med)]
        if len(keep)==len(d) or len(keep) < 50: break
        d=keep
    res=[abs(x-(m*y+b)) for y,x in d]
    print('%s n=%d maxres=%.2f  px: x=%.6f*y+%.3f  -> in (%.3f,0) .. (%.3f,44)'
          % (label, len(d), max(res), m, b, b/40.0, (m*1760+b)/40.0))
    return m, b

# seeds from the tint fit
seeds = {'PINK': (0.680550, 1.782, lambda c: c[0] > 240 and c[1]==c[2] and 140 <= c[1] <= 230),
         'BLUE': (0.680329, 1192.749, lambda c: c[2] > 240 and c[1] > c[0] and 140 <= c[0] <= 230)}
for label, (m0, b0, ok) in seeds.items():
    data = []
    for y in range(H):
        c0 = m0*y + b0
        xs = [x for x in range(max(0,int(c0)-14), min(W,int(c0)+15)) if ok(get(x,y))]
        if 2 <= len(xs) <= 10 and xs[-1]-xs[0] == len(xs)-1:
            data.append((y, sum(xs)/len(xs)))
    fit(data, label + ' dash')
del px
