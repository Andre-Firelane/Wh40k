"""Which fitted rectangles come close enough to be a drawn seam? map3's percentile
fit takes a slice off BOTH pieces of a touching pair, so a seam the art draws
closed comes out as a slot."""
import pickle, math
PX = 40.0
final = pickle.load(open('scratch_repro/map4/final.pkl','rb'))
def corners(cx,cy,w,h,a):
    r=math.radians(a); ux,uy=math.cos(r),math.sin(r)
    out=[]
    for su in (-1,1):
        for sv in (-1,1):
            u=su*w/2; v=sv*h/2
            out.append((cx+u*ux-v*uy, cy+u*uy+v*ux))
    return [out[0],out[1],out[3],out[2]]
def seg_dist(p,q,r,s):
    def d(a,b,c):
        vx,vy=c[0]-b[0],c[1]-b[1]; L2=vx*vx+vy*vy
        t=0 if L2==0 else max(0,min(1,((a[0]-b[0])*vx+(a[1]-b[1])*vy)/L2))
        return math.hypot(a[0]-(b[0]+t*vx), a[1]-(b[1]+t*vy))
    return min(d(p,r,s), d(q,r,s), d(r,p,q), d(s,p,q))
def rect_gap(A,B):
    ca, cb = corners(*A), corners(*B)
    best=1e9
    for i in range(4):
        for j in range(4):
            best=min(best, seg_dist(ca[i],ca[(i+1)%4], cb[j],cb[(j+1)%4]))
    return best/PX
pieces=[(i,p) for i,(src,p,n) in enumerate(final)]
close=[]
for i in range(len(pieces)):
    for j in range(i+1,len(pieces)):
        g = rect_gap(pieces[i][1], pieces[j][1])
        if g < 3.0: close.append((g,i,j))
for g,i,j in sorted(close):
    a=final[i][1]; b=final[j][1]
    print('%5.2f"  #%-2d (%5.2f,%5.2f)@%5.1f  <->  #%-2d (%5.2f,%5.2f)@%5.1f'
          % (g,i,a[0]/PX,a[1]/PX,a[4], j,b[0]/PX,b[1]/PX,b[4]))
