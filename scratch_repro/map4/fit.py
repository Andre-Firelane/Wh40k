import pygame
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
W, H = s.get_size()
px = pygame.PixelArray(s)
get = lambda x, y: s.unmap_rgb(px[x, y])[:3]
PINK = (255, 237, 237); BLUE = (237, 245, 255)
pdata, bdata = [], []
for y in range(H):
    pinks = [x for x in range(W) if get(x, y) == PINK]
    blues = [x for x in range(W) if get(x, y) == BLUE]
    if pinks: pdata.append((y, max(pinks)))
    if blues: bdata.append((y, min(blues)))
del px

def fit(data, label):
    d = data
    for _ in range(6):
        n = len(d); sy = sum(p[0] for p in d); sx = sum(p[1] for p in d)
        syy = sum(p[0]*p[0] for p in d); sxy = sum(p[0]*p[1] for p in d)
        m = (n*sxy - sy*sx) / (n*syy - sy*sy); b = (sx - m*sy)/n
        res = [abs(x - (m*y+b)) for y, x in d]
        med = sorted(res)[len(res)//2]
        keep = [p for p, r in zip(d, res) if r <= max(2.0, 4*med)]
        if len(keep) == len(d): break
        d = keep
    res = [abs(x-(m*y+b)) for y, x in d]
    print('%s: x = %.6f*y + %.3f   n=%d/%d  maxres=%.2f  angle_from_vertical=%.3fdeg'
          % (label, m, b, len(d), len(data), max(res), __import__('math').degrees(__import__('math').atan(m))))
    return m, b
pm, pb = fit(pdata, 'PINK edge')
bm, bb = fit(bdata, 'BLUE edge')
print()
print('slope diff', bm-pm)
print('horizontal gap at y=0:', bb-pb, 'px =', (bb-pb)/40.0, 'in')
import math
n = 1.0/math.hypot(1.0, pm)
print('perpendicular gap:', (bb-pb)*n, 'px =', (bb-pb)*n/40.0, 'in')
