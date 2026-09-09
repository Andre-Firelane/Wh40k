import pygame
pygame.init()
s = pygame.image.load('Sprites/map4.png')
# W flank stack bbox from comps: x[328,690] y[613,1118]; E flank: x[1710,2050] y[637,1123]
a = s.subsurface(pygame.Rect(320, 605, 380, 520)).copy()
b = s.subsurface(pygame.Rect(1700, 630, 380, 520)).copy()
b = pygame.transform.rotate(b, 180)
out = pygame.Surface((780, 520))
out.fill((255,255,255)); out.blit(a,(0,0)); out.blit(b,(400,0))
pygame.draw.line(out,(255,0,255),(390,0),(390,520),4)
pygame.image.save(out, 'scratch_repro/map4/flanks.png')
print(out.get_size())
