"""Some drawn pieces TOUCH, so the mask merged them. Erode each component until
it breaks apart, then hand every pixel back to its nearest surviving seed."""
import pickle, collections
comps = pickle.load(open('scratch_repro/map4/comps.pkl','rb'))

def components_of(pts):
    S = set(pts); out = []; seen = set()
    for p in pts:
        if p in seen: continue
        stack=[p]; seen.add(p); grp=[]
        while stack:
            q = stack.pop(); grp.append(q)
            x,y = q
            for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if n in S and n not in seen:
                    seen.add(n); stack.append(n)
        out.append(grp)
    return sorted(out, key=len, reverse=True)

def erode(pts, k):
    S = set(pts)
    for _ in range(k):
        S = {(x,y) for (x,y) in S
             if (x-1,y) in S and (x+1,y) in S and (x,y-1) in S and (x,y+1) in S}
    return S

for k in (5, 6, 7, 8, 0, 3):
    c = comps[k]
    line = ['comp %-2d (n=%d):' % (k, len(c))]
    for depth in (4, 8, 12, 16, 20):
        parts = [g for g in components_of(list(erode(c, depth))) if len(g) >= 200]
        line.append('e%d->%d%s' % (depth, len(parts), [len(g) for g in parts[:4]]))
    print(' '.join(line))
