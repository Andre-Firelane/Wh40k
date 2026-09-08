import pygame, math
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
W,H = s.get_size()
px = pygame.PixelArray(s); get = lambda x,y: s.unmap_rgb(px[x,y])[:3]
# white ruler pixels inside/near the central ruin
pts = []
for y in range(700, 1150):
    for x in range(850, 1600):
        c = get(x,y)
        if c == (255,255,255):
            pts.append((x,y))
del px
xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
print('white pixels', len(pts), 'x', min(xs), max(xs), 'y', min(ys), max(ys))
# endpoints: extreme along the (1,-0.68) direction
import math
d = (1.0, -0.680578); n = math.hypot(*d); d = (d[0]/n, d[1]/n)
proj = sorted(pts, key=lambda p: p[0]*d[0]+p[1]*d[1])
a, b = proj[0], proj[-1]
print('ends', a, b, 'straight px', math.dist(a,b), '=', math.dist(a,b)/40.0, 'in')
