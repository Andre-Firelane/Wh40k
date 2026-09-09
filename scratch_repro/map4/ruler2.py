"""The art annotates 24.25" with a hand-drawn white ruler. Measure the ruler
itself: if it is shorter than the two dashed zone lines really are, the label
describes the drawn line, not the zones."""
import math, pygame
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
raw = pygame.image.tostring(s,'RGB'); W,H,PX = 2400,1760,40.0
def rgb(x,y):
    i=(y*W+x)*3; return raw[i],raw[i+1],raw[i+2]
# White pixels that are NOT background: a white pixel with a dark neighbour
# within 12 px in any of the four directions is on the ruler, not the open ground.
def dark(c): return max(c) < 140
line = []
for y in range(600, 1200):
    for x in range(880, 1560):
        if rgb(x,y) != (255,255,255): continue
        if (any(dark(rgb(x+d,y)) for d in (-12,12)) and
            any(dark(rgb(x,y+d)) for d in (-12,12))):
            line.append((x,y))
print('ruler pixels found:', len(line))
if line:
    d = (1.0, -0.680578); n = math.hypot(*d); d = (d[0]/n, d[1]/n)
    proj = sorted(line, key=lambda p: p[0]*d[0]+p[1]*d[1])
    a, b = proj[0], proj[-1]
    L = math.dist(a, b)
    print('endpoints %s -> %s' % (a, b))
    print('straight length %.1f px = %.2f"' % (L, L/PX))
    # path length along the wiggle, ordered by projection
    tot = 0.0; prev = None
    for p in proj:
        if prev is not None and math.dist(p, prev) < 6: tot += math.dist(p, prev)
        prev = p
    print('(the ruler is drawn wiggly; straight end-to-end is the honest number)')
    # how far each endpoint sits from its own dashed line, measured perpendicular
    for name, m, c in (('pink', 0.680578, 3.755), ('blue', 0.680362, 1190.707)):
        for p in (a, b):
            dist = abs(p[0] - (m*p[1] + c)) / math.hypot(1.0, m)
            print('  endpoint %s is %6.1f px = %5.2f" from the %s dash' % (p, dist, dist/PX, name))
