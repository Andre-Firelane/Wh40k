"""The W flank stack is ONE drawn run: a narrow container end-to-end with a wide
slab. Measure the width profile along its own axis - the seam is where the width
steps - so both pieces get a shared, exact boundary instead of an erosion guess."""
import pickle, math
PX = 40.0
comps = pickle.load(open('scratch_repro/map4/comps.pkl','rb'))
c = comps[5]
ANG = 55.0
r = math.radians(ANG); ux,uy = math.cos(r), math.sin(r)
band = {}
for x,y in c:
    u = x*ux + y*uy; v = -x*uy + y*ux
    band.setdefault(int(round(u)), []).append(v)
us = sorted(band)
print('axis span %.2f" ; width profile every 0.25" (u along %.1f deg):' % ((us[-1]-us[0])/PX, ANG))
prev = None
for i in range(us[0], us[-1]+1, 10):
    vs = []
    for k in range(i, min(i+10, us[-1]+1)):
        vs.extend(band.get(k, ()))
    if not vs: continue
    vs.sort()
    lo = vs[int(0.02*(len(vs)-1))]; hi = vs[int(0.98*(len(vs)-1))]
    mid = (lo+hi)/2
    print('  u=%7.2f"  width %5.2f"  centre v=%7.2f"' % ((i-us[0])/PX, (hi-lo)/PX, mid/PX))
