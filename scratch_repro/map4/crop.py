import pygame, sys
pygame.init()
s = pygame.image.load('Sprites/map4.png')
x0,y0,x1,y1 = [int(v) for v in sys.argv[1:5]]
sub = s.subsurface(pygame.Rect(x0,y0,x1-x0,y1-y0)).copy()
scale = float(sys.argv[5]) if len(sys.argv)>5 else 1.0
if scale != 1.0:
    sub = pygame.transform.smoothscale(sub, (int(sub.get_width()*scale), int(sub.get_height()*scale)))
pygame.image.save(sub, sys.argv[6] if len(sys.argv)>6 else 'scratch_repro/map4/crop.png')
print(sub.get_size())
