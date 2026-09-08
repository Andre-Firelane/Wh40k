import pygame
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
W, H = s.get_size()
px = pygame.PixelArray(s)
get = lambda x, y: s.unmap_rgb(px[x, y])[:3]

PINK = (255, 237, 237)
BLUE = (237, 245, 255)

rows = []
for y in range(H):
    pinks = [x for x in range(W) if get(x, y) == PINK]
    blues = [x for x in range(W) if get(x, y) == BLUE]
    rows.append((y, max(pinks) if pinks else None, min(blues) if blues else None,
                 len(pinks), len(blues)))
del px
for y, pmax, bmin, np_, nb in rows[::40]:
    print(y, 'pink_max_x=%s(%d)' % (pmax, np_), 'blue_min_x=%s(%d)' % (bmin, nb))
