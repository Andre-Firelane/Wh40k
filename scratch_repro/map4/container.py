"""The two green containers came out 0.93" apart in length because the erosion
split cut the shared seam differently on the two sides. Measure them from their
OWN colour instead - green is 69-73% of the container and 1-2% of the slab it
touches - so the split never enters the answer."""
import pickle, math, pygame
pygame.init()
s = pygame.image.load('Sprites/map4.png').convert(24)
raw = pygame.image.tostring(s,'RGB'); W,PX = 2400,40.0
def rgb(x,y):
    i=(y*W+x)*3; return raw[i],raw[i+1],raw[i+2]
comps = pickle.load(open('scratch_repro/map4/comps.pkl','rb'))
def greenish(c):
    r,g,b = c
    return g > r and g > b and g >= 95
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
        ux,uy=dx/L,dy/L
        us=[p[0]*ux+p[1]*uy for p in h]; vs=[-p[0]*uy+p[1]*ux for p in h]
        a=(max(us)-min(us))*(max(vs)-min(vs))
        if best is None or a<best[0]: best=(a,math.degrees(math.atan2(dy,dx)))
    return best[1]
def fit(pts,ang,lo=2.0,hi=98.0):
    r=math.radians(ang); ux,uy=math.cos(r),math.sin(r)
    us=sorted(p[0]*ux+p[1]*uy for p in pts); vs=sorted(-p[0]*uy+p[1]*ux for p in pts)
    def q(a,p): return a[max(0,min(len(a)-1,int(round(p/100.0*(len(a)-1)))))]
    u0,u1,v0,v1=q(us,lo),q(us,hi),q(vs,lo),q(vs,hi)
    cu,cv=(u0+u1)/2.0,(v0+v1)/2.0
    return cu*ux-cv*uy, cu*uy+cv*ux, u1-u0, v1-v0
for k, label in ((5,'W flank container'), (6,'E flank container')):
    g = [p for p in comps[k] if greenish(rgb(*p))]
    a = best_angle(g)
    while a<=-90: a+=180
    while a>90: a-=180
    cx,cy,w,h = fit(g,a)
    if w < h:
        a += 90
        while a>90: a-=180
        cx,cy,w,h = fit(g,a)
    print('%-20s n=%5d  (%6.2f,%6.2f)  %5.2f x %5.2f @ %5.1f' % (label,len(g),cx/PX,cy/PX,w/PX,h/PX,a))
    if k == 5: keep=(cx/PX,cy/PX,w/PX,h/PX,a)
mx,my = 60.0-keep[0], 44.0-keep[1]
print()
print('mirror of the W container: (%6.2f,%6.2f) %5.2f x %5.2f @ %5.1f' % (mx,my,keep[2],keep[3],keep[4]))
