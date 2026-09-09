import math, pygame, collections
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
raw = pygame.image.tostring(s,'RGB'); W,PX=2400,40.0
def rgb(x,y):
    i=(y*W+x)*3; return raw[i],raw[i+1],raw[i+2]
print('sample at the central icon  (1195, 845):', rgb(1195,845))
print('sample at the P2 home H     (2008, 345):', rgb(2008,345))
print('sample at a green diamond   ( 535, 425):', rgb(535,425))
# centroid of each icon inside a generous local window, by its own exact colour
def centroid(colour, x0,y0,x1,y1, tol=30):
    pts=[(x,y) for y in range(y0,y1) for x in range(x0,x1)
         if max(abs(a-b) for a,b in zip(rgb(x,y), colour)) <= tol]
    if not pts: return None
    return (sum(p[0] for p in pts)/len(pts)/PX, sum(p[1] for p in pts)/len(pts)/PX, len(pts))
c = rgb(1195,845)
print('central teal icon centroid :', centroid(c, 1100, 760, 1300, 940))
b = rgb(2008,345)
print('P2 home blue-H centroid    :', centroid(b, 1930, 270, 2090, 420))
