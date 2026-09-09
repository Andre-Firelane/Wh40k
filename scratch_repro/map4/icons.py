"""Independent cross-check: where the art puts each objective ICON, against the
centre of the piece the fit produced."""
import pickle, math, collections, pygame
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
raw = pygame.image.tostring(s,'RGB'); W,H,PX = 2400,1760,40.0
def rgb(x,y):
    i=(y*W+x)*3; return raw[i],raw[i+1],raw[i+2]
KIND = {
 'teal skull (central)': lambda c: c[1]>150 and c[1]-c[0]>110 and c[2]>70 and c[2]<c[1],
 'green diamond':        lambda c: c[1]>150 and c[1]-c[0]>110 and c[2]<90,
 'red H':                lambda c: c[0]>150 and c[0]-c[1]>90 and c[0]-c[2]>90,
 'blue H':               lambda c: c[2]>150 and c[2]-c[0]>90 and c[2]-c[1]>60,
}
pts = collections.defaultdict(list)
for y in range(H):
    for x in range(W):
        c = rgb(x,y)
        for k,f in KIND.items():
            if f(c): pts[k].append((x,y)); break
def clusters(ps, r=60):
    out=[]
    for p in ps:
        for g in out:
            if abs(p[0]-g[0][0])<r and abs(p[1]-g[0][1])<r: g.append(p); break
        else: out.append([p])
    return [g for g in out if len(g)>=300]
print('%-22s %-18s' % ('icon', 'centroid (in)'))
found=[]
for k in KIND:
    for g in clusters(pts[k]):
        cx=sum(p[0] for p in g)/len(g)/PX; cy=sum(p[1] for p in g)/len(g)/PX
        print('%-22s (%6.2f, %6.2f)  n=%d' % (k, cx, cy, len(g)))
        found.append((k,cx,cy))
print()
final = pickle.load(open('scratch_repro/map4/final.pkl','rb'))
print('nearest fitted piece centre for each icon:')
for k,cx,cy in found:
    best=None
    for src,(px_,py_,w,h,a),n in final:
        d=math.hypot(cx-px_/PX, cy-py_/PX)
        if best is None or d<best[0]: best=(d,src,px_/PX,py_/PX)
    print('  %-22s -> piece #%-2d at (%6.2f,%6.2f), %.2f" away' % (k, best[1], best[2], best[3], best[0]))
