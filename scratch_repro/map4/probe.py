import pygame, collections
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
W, H = s.get_size()
px = pygame.PixelArray(s)
cnt = collections.Counter()
for y in range(0, H, 4):
    for x in range(0, W, 4):
        cnt[s.unmap_rgb(px[x, y])[:3]] += 1
del px
for c, n in cnt.most_common(24):
    print(c, n)
