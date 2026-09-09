import pickle, math
comps = pickle.load(open('scratch_repro/map4/comps.pkl','rb'))
def near(a, b, step=4):
    cell = {}
    for x,y in b: cell.setdefault((x//16, y//16), []).append((x,y))
    best = 1e9
    for x,y in a[::step]:
        r = 1
        while r <= 20:
            found = False
            for gx in range(x//16-r, x//16+r+1):
                for gy in range(y//16-r, y//16+r+1):
                    for q in cell.get((gx,gy), ()):
                        found = True
                        d = math.hypot(x-q[0], y-q[1])
                        if d < best: best = d
            if found: break
            r += 1
    return best
LBL={3:'SE rot ruin',4:'NW rot ruin',5:'W flank stack',6:'E flank stack',
     1:'P1 home ruin',9:'S rubble slab',7:'SW diag barricade',0:'central ruin'}
for a,b in ((4,5),(3,6),(1,7),(9,0),(7,9)):
    d = near(comps[a], comps[b])
    print('%-18s <-> %-18s  drawn gap %6.1f px = %5.2f"' % (LBL[a], LBL[b], d, d/40.0))
