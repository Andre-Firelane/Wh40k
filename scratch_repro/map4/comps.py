import math
W, H = 2400, 1760
mask = bytearray(open('scratch_repro/map4/mask.bin','rb').read())

# --- morphological open with a 3x3 kernel: kills 1-2px lines and hairlines ---
def erode(m):
    out = bytearray(W*H)
    for y in range(1, H-1):
        r = y*W
        for x in range(1, W-1):
            if m[r+x] and m[r+x-1] and m[r+x+1] and m[r-W+x] and m[r+W+x]:
                out[r+x] = 1
    return out
def dilate(m):
    out = bytearray(W*H)
    for y in range(1, H-1):
        r = y*W
        for x in range(1, W-1):
            if m[r+x] or m[r+x-1] or m[r+x+1] or m[r-W+x] or m[r+W+x]:
                out[r+x] = 1
    return out

m = mask
for _ in range(2): m = erode(m)
for _ in range(2): m = dilate(m)
print('after open', sum(m))

# --- connected components (4-neighbour), iterative flood fill ---
lab = [0]*(W*H)
comps = []
nxt = 0
for y0 in range(H):
    for x0 in range(W):
        i0 = y0*W + x0
        if not m[i0] or lab[i0]: continue
        nxt += 1
        stack = [i0]; lab[i0] = nxt; pts = []
        while stack:
            i = stack.pop(); pts.append(i)
            x, y = i % W, i // W
            for j, ok in ((i-1, x>0), (i+1, x<W-1), (i-W, y>0), (i+W, y<H-1)):
                if ok and m[j] and not lab[j]:
                    lab[j] = nxt; stack.append(j)
        if len(pts) >= 400:
            comps.append(pts)
print('components >=400px:', len(comps))
comps.sort(key=len, reverse=True)
import pickle
pickle.dump([[(i%W, i//W) for i in c] for c in comps], open('scratch_repro/map4/comps.pkl','wb'))
for k, c in enumerate(comps):
    xs = [i%W for i in c]; ys = [i//W for i in c]
    print('%2d area=%7d  bbox x[%4d,%4d] y[%4d,%4d]  centre_in=(%.2f, %.2f)'
          % (k, len(c), min(xs), max(xs), min(ys), max(ys),
             (min(xs)+max(xs))/2/40.0, (min(ys)+max(ys))/2/40.0))
