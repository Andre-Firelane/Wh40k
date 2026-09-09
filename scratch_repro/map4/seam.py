"""Split the W flank stack at the MEASURED seam (the width step at u=7.45") and
fit each half. The two rectangles then meet by construction - no nudge."""
import pickle, math
PX = 40.0
comps = pickle.load(open('scratch_repro/map4/comps.pkl','rb'))
c = comps[5]
r = math.radians(55.0); ux,uy = math.cos(r), math.sin(r)
us_all = [x*ux + y*uy for x,y in c]
u0 = min(us_all)
SEAM = u0 + 7.45*PX
lo_half = [p for p in c if p[0]*ux + p[1]*uy <  SEAM]
hi_half = [p for p in c if p[0]*ux + p[1]*uy >= SEAM]
def hull(pts):
    pts=sorted(set(pts))
    def half(ps):
        out=[]
        for p in ps:
            while len(out)>=2:
                (ax,ay),(bx,by)=out[-2],out[-1]
                if (bx-ax)*(p[1]-ay)-(by-ay)*(p[0]-ax)<=0: out.pop()
                else: break
            out.append(p)
        return out
    return half(pts)[:-1]+half(pts[::-1])[:-1]
def best_angle(pts):
    h=hull(pts); n=len(h); best=None
    for i in range(n):
        x0,y0=h[i]; x1,y1=h[(i+1)%n]; dx,dy=x1-x0,y1-y0; L=math.hypot(dx,dy)
        if L<1e-9: continue
        vx,vy=dx/L,dy/L
        aa=[p[0]*vx+p[1]*vy for p in h]; bb=[-p[0]*vy+p[1]*vx for p in h]
        area=(max(aa)-min(aa))*(max(bb)-min(bb))
        if best is None or area<best[0]: best=(area,math.degrees(math.atan2(dy,dx)))
    return best[1]
def fit(pts,ang,lo=2.0,hi=98.0):
    rr=math.radians(ang); a,b=math.cos(rr),math.sin(rr)
    p1=sorted(p[0]*a+p[1]*b for p in pts); p2=sorted(-p[0]*b+p[1]*a for p in pts)
    def q(arr,pc): return arr[max(0,min(len(arr)-1,int(round(pc/100.0*(len(arr)-1)))))]
    x0,x1,y0,y1=q(p1,lo),q(p1,hi),q(p2,lo),q(p2,hi)
    cu,cv=(x0+x1)/2.0,(y0+y1)/2.0
    return cu*a-cv*b, cu*b+cv*a, x1-x0, y1-y0
for name, pts in (('container (narrow half)', lo_half), ('slab (wide half)', hi_half)):
    a = best_angle(pts)
    while a<=-90: a+=180
    while a>90: a-=180
    cx,cy,w,h = fit(pts,a)
    if w<h:
        a += 90
        while a>90: a-=180
        cx,cy,w,h = fit(pts,a)
    print('%-24s n=%5d  (%6.2f,%6.2f)  %5.2f x %5.2f @ %5.1f' % (name,len(pts),cx/PX,cy/PX,w/PX,h/PX,a))
    # also at the shared 55.0 axis, so the pair can be placed end to end
    cx2,cy2,w2,h2 = fit(pts, 55.0)
    print('%-24s  at 55.0 deg:      (%6.2f,%6.2f)  %5.2f x %5.2f' % ('', cx2/PX,cy2/PX,w2/PX,h2/PX))
