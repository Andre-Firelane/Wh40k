"""Do the ART's pieces touch? Measured pixel-to-pixel, the way map3 decided which
seams to close - a drawn separation of a line's width means touching, a real gap
does not."""
import pickle, math
comps = pickle.load(open('scratch_repro/map4/comps.pkl','rb'))
def near(a, b, cap=200):
    A = [p for p in a]; B = set(b)
    # coarse: bucket B by 8px cells
    cell = {}
    for x,y in b: cell.setdefault((x//8, y//8), []).append((x,y))
    best = 1e9
    for x,y in A[::3]:
        for gx in range(x//8-3, x//8+4):
            for gy in range(y//8-3, y//8+4):
                for q in cell.get((gx,gy), ()):
                    d = math.hypot(x-q[0], y-q[1])
                    if d < best: best = d
        if best <= 1: break
    return best
LBL = {0:'central ruin',1:'P1 home ruin',2:'P2 home ruin',3:'SE rot ruin',4:'NW rot ruin',
       5:'W flank stack',6:'E flank stack',7:'SW diag barricade',8:'NE diag barricade',
       9:'S rubble slab',10:'N rubble slab',11:'S braced bar',12:'N braced bar'}
for a,b in ((9,11),(10,12),(4,5),(3,6),(9,1),(5,4)):
    d = near(comps[a], comps[b])
    print('%-18s <-> %-18s  drawn gap %5.2f px = %5.3f"' % (LBL[a], LBL[b], d, d/40.0))
