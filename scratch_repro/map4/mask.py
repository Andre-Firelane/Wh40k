import pygame, math, sys
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
W, H = s.get_size()
raw = pygame.image.tostring(s, 'RGB')

def rgb(x, y):
    i = (y * W + x) * 3
    return raw[i], raw[i+1], raw[i+2]

def is_terrain(r, g, b):
    if max(r, g, b) >= 230:            # white ground, zone tint, dashes, icon fill
        return False
    if b - r > 90 and b > 140:         # blue label text / blue icons
        return False
    if r - g > 80 and r > 140:         # red icon
        return False
    if g - r > 100 and g > 150:        # teal objective icon
        return False
    if r == g == b and r > 95:         # grey dimension guide lines (102/149/207)
        return False
    return True

mask = bytearray(W * H)
for y in range(H):
    base = y * W * 3
    row = y * W
    for x in range(W):
        i = base + x*3
        if is_terrain(raw[i], raw[i+1], raw[i+2]):
            mask[row + x] = 1
print('terrain px', sum(mask))
with open('scratch_repro/map4/mask.bin','wb') as f: f.write(bytes(mask))
print('W,H', W, H)
