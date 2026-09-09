import pygame, sys
pygame.init()
s = pygame.image.load(sys.argv[1])
x0,y0,x1,y1 = [int(v) for v in sys.argv[2:6]]
sub = s.subsurface(pygame.Rect(x0,y0,x1-x0,y1-y0)).copy()
sc = float(sys.argv[6])
sub = pygame.transform.smoothscale(sub,(int(sub.get_width()*sc),int(sub.get_height()*sc)))
pygame.image.save(sub, sys.argv[7]); print(sub.get_size())
