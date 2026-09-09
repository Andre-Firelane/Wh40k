"""Rotated or upright? Decide by how much of the fitted RECTANGLE is really drawn
terrain - map3's fill criterion - then check the 180-degree symmetry the layout
claims, so only one half has to be transcribed."""
import pickle, math, pygame
pygame.init()
srf = pygame.image.load('Sprites/map4.png').convert(24)
raw = pygame.image.tostring(srf, 'RGB'); W, PX = 2400, 40.0
exec(open('scratch_repro/map4/measure.py').read().split('pieces = []')[0].split('comps =')[0].replace('import pickle, math, collections, pygame','import math'))
comps = pickle.load(open('scratch_repro/map4/comps.pkl','rb'))

def components_of(pts):
    S=set(pts); out=[]; seen=set()
    for p in pts:
        if p in seen: continue
        st=[p]; seen.add(p); g=[]
        while st:
            q=st.pop(); g.append(q); x,y=q
            for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if n in S and n not in seen: seen.add(n); st.append(n)
        out.append(g)
    return sorted(out,key=len,reverse=True)
def erode(pts,k):
    S=set(pts)
    for _ in range(k):
        S={(x,y) for (x,y) in S if (x-1,y) in S and (x+1,y) in S and (x,y-1) in S and (x,y+1) in S}
    return S
def split_two(pts):
    seeds=[g for g in components_of(list(erode(pts,12))) if len(g)>=200][:2]
    cent=[(sum(p[0] for p in g)/len(g), sum(p[1] for p in g)/len(g)) for g in seeds]
    gr=[[],[]]
    for p in pts:
        d0=(p[0]-cent[0][0])**2+(p[1]-cent[0][1])**2; d1=(p[0]-cent[1][0])**2+(p[1]-cent[1][1])**2
        gr[0 if d0<=d1 else 1].append(p)
    return gr
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
def rect_fill(pts,cx,cy,w,h,ang):
    r=math.radians(ang); ux,uy=math.cos(r),math.sin(r); S=set(pts); hit=tot=0
    for i in range(max(2,int(w/2))):
        u=-w/2+w*(i+0.5)/max(2,int(w/2))
        for j in range(max(2,int(h/2))):
            v=-h/2+h*(j+0.5)/max(2,int(h/2))
            x=int(round(cx+u*ux-v*uy)); y=int(round(cy+u*uy+v*ux)); tot+=1
            if (x,y) in S: hit+=1
    return hit/tot

pieces=[]
for k,c in enumerate(comps):
    if len(c)<2000 or k==13: continue
    if k in (5,6):
        for g in split_two(c): pieces.append((k,g))
    else: pieces.append((k,c))

out=[]
print('%-4s | %-40s %5s | %-40s %5s | choice' % ('src','ROTATED at min-area angle','fill','UPRIGHT (0 or 90 deg)','fill'))
for k,c in pieces:
    a=best_angle(c)
    while a<=-90: a+=180
    while a>90: a-=180
    cx,cy,w,h=fit(c,a)
    if w<h:
        a2=a+90
        while a2>90: a2-=180
        cx,cy,w,h=fit(c,a2); a=a2
    fr=rect_fill(c,cx,cy,w,h,a)
    ux_,uy_,uw,uh=fit(c,0.0)
    fu=rect_fill(c,ux_,uy_,uw,uh,0.0)
    rotated = fr > fu + 0.02
    pick = (cx,cy,w,h,a) if rotated else (ux_,uy_,uw,uh,0.0)
    out.append((k, pick, len(c)))
    print('%-4d | (%6.2f,%6.2f) %6.2f x %5.2f @ %6.1f      %4.0f%% | (%6.2f,%6.2f) %6.2f x %5.2f @    0.0 %4.0f%% | %s'
          % (k, cx/PX,cy/PX,w/PX,h/PX,a, 100*fr, ux_/PX,uy_/PX,uw/PX,uh/PX, 100*fu,
             'ROTATED' if rotated else 'upright'))
pickle.dump(out, open('scratch_repro/map4/final.pkl','wb'))

print()
print('--- 180-degree symmetry (mirror through the board centre) ---')
BW, BH = 60.0, 44.0
used=set()
for i,(k,(cx,cy,w,h,a),n) in enumerate(out):
    mx, my = BW - cx/PX, BH - cy/PX
    best=None
    for j,(k2,(cx2,cy2,w2,h2,a2),n2) in enumerate(out):
        if j==i: continue
        d=math.hypot(mx-cx2/PX, my-cy2/PX)
        if best is None or d<best[0]: best=(d,j,cx2/PX,cy2/PX,w2/PX,h2/PX,a2)
    d,j,bx,by,bw,bh,ba = best
    da=abs(((a-ba+90)%180)-90)
    print('%-2d (%5.2f,%5.2f) %5.2fx%4.2f @%5.1f  ->  mirror lands %5.2f" from #%-2d  dsize %4.2f/%4.2f  dang %4.1f'
          % (i, cx/PX,cy/PX,w/PX,h/PX,a, d, j, abs(w/PX-bw), abs(h/PX-bh), da))
