import pygame
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
px = pygame.PixelArray(s); get = lambda x,y: s.unmap_rgb(px[x,y])[:3]
for y in (300, 900, 1500):
    xs = int(0.680550*y + 1.782)
    print('--- row y=%d, pink edge near x=%d' % (y, xs))
    print('  ', [(x, get(x,y)) for x in range(xs-6, xs+9)])
    xb = int(0.680329*y + 1192.749)
    print('--- row y=%d, blue edge near x=%d' % (y, xb))
    print('  ', [(x, get(x,y)) for x in range(xb-8, xb+7)])
del px
