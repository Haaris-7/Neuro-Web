import numpy as np
from PIL import Image, ImageFilter, ImageDraw

W, H = 1500, 1150
OUT = "/home/haaris786/dev/Neuro-Web/brag-output/composition/assets/brain"

ANCH = [
 (0.00,(0.267004,0.004874,0.329415)),(0.10,(0.282623,0.140926,0.457517)),
 (0.20,(0.253935,0.265254,0.529983)),(0.30,(0.206756,0.371758,0.553117)),
 (0.40,(0.163625,0.471133,0.558148)),(0.50,(0.127568,0.566949,0.550556)),
 (0.60,(0.134692,0.658636,0.517649)),(0.70,(0.266941,0.748751,0.440573)),
 (0.80,(0.477504,0.821444,0.318195)),(0.90,(0.741388,0.873449,0.149561)),
 (1.00,(0.993248,0.906157,0.143936)),
]
def lut(n=256):
    xs=np.array([a[0] for a in ANCH]); cs=np.array([a[1] for a in ANCH]); t=np.linspace(0,1,n)
    return np.stack([np.interp(t,xs,cs[:,i]) for i in range(3)],axis=1)
LUT = lut()

# left-lateral cerebrum, frontal pole at LEFT, occipital at RIGHT, temporal lobe
# projecting forward-down under the Sylvian fissure.
CEREBRUM = [
 (0.065,0.450),(0.075,0.352),(0.128,0.262),(0.215,0.190),(0.318,0.140),
 (0.432,0.113),(0.548,0.113),(0.658,0.140),(0.752,0.190),(0.828,0.262),
 (0.876,0.348),(0.894,0.448),(0.888,0.548),(0.860,0.626),(0.812,0.678),
 (0.748,0.706),(0.672,0.716),(0.590,0.732),(0.506,0.756),(0.424,0.774),
 (0.344,0.778),(0.272,0.762),(0.216,0.726),(0.184,0.672),(0.178,0.612),
 (0.196,0.566),(0.162,0.548),(0.118,0.520),(0.082,0.492),
]
CEREB = [(0.690,0.660),(0.766,0.652),(0.826,0.676),(0.856,0.724),(0.846,0.778),
         (0.796,0.812),(0.730,0.814),(0.682,0.788),(0.662,0.740),(0.668,0.694)]
STEM  = [(0.598,0.700),(0.646,0.722),(0.668,0.782),(0.660,0.846),(0.630,0.884),
         (0.586,0.882),(0.566,0.840),(0.568,0.776),(0.578,0.724)]

def catmull(points, samples=30):
    p=np.array(points,dtype=float); n=len(p); out=[]
    for i in range(n):
        p0,p1,p2,p3=p[(i-1)%n],p[i%n],p[(i+1)%n],p[(i+2)%n]
        for s in range(samples):
            t=s/samples; t2,t3=t*t,t*t*t
            out.append(0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t2+(-p0+3*p1-3*p2+p3)*t3))
    return np.array(out)

def mask_of(ctrl):
    pts=catmull(ctrl); img=Image.new("L",(W,H),0)
    ImageDraw.Draw(img).polygon([(x*W,y*H) for x,y in pts], fill=255)
    return img

def curve_img(pts, width, samples=400):
    """Anti-aliased groove stroke along a catmull curve (open)."""
    p=np.array(pts,dtype=float); n=len(p); out=[]
    for i in range(n-1):
        p0,p1,p2,p3=p[max(i-1,0)],p[i],p[i+1],p[min(i+2,n-1)]
        for s in range(samples//n):
            t=s/(samples//n); t2,t3=t*t,t*t*t
            out.append(0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t2+(-p0+3*p1-3*p2+p3)*t3))
    img=Image.new("L",(W,H),0); d=ImageDraw.Draw(img)
    xy=[(x*W,y*H) for x,y in out]
    d.line(xy, fill=255, width=width, joint="curve")
    return np.asarray(img.filter(ImageFilter.GaussianBlur(width*0.42)),dtype=np.float32)/255.0

m_cx = np.asarray(mask_of(CEREBRUM),dtype=np.float32)/255.0
m_cb = np.asarray(mask_of(CEREB),dtype=np.float32)/255.0
m_st = np.asarray(mask_of(STEM),dtype=np.float32)/255.0
m_all = m_cx.copy()
print(f"mask coverage: cerebrum {m_cx.mean():.3f}  total {m_all.mean():.3f}")

yy,xx = np.mgrid[0:H,0:W].astype(np.float32); nx,ny = xx/W, yy/H

def height_of(img, r):
    return np.asarray(img.filter(ImageFilter.GaussianBlur(r)),dtype=np.float32)/255.0
h_cx=height_of(mask_of(CEREBRUM),44); h_cb=height_of(mask_of(CEREB),20); h_st=height_of(mask_of(STEM),16)
height=h_cx

# major named sulci -> deep grooves that make the lateral view legible
SYLVIAN = [(0.195,0.600),(0.285,0.618),(0.395,0.612),(0.500,0.588),(0.590,0.548),(0.652,0.498)]
CENTRAL = [(0.560,0.135),(0.534,0.246),(0.498,0.350),(0.452,0.440),(0.412,0.510)]
SUPTEMP = [(0.250,0.702),(0.350,0.716),(0.452,0.706),(0.548,0.676),(0.626,0.632)]
INTRAPAR= [(0.640,0.256),(0.676,0.336),(0.700,0.420),(0.712,0.500)]
grooves = (curve_img(SYLVIAN,40)*0.90 + curve_img(CENTRAL,30)*0.52
           + curve_img(SUPTEMP,26)*0.42 + curve_img(INTRAPAR,24)*0.34)
grooves = np.clip(grooves,0,1)*m_cx

def fbm(px,py,oct=5):
    v=np.zeros_like(px); amp=1.0; f=1.0; tot=0.0
    for o in range(oct):
        v += amp*(np.sin(px*f*13.0+1.7*o)*np.cos(py*f*15.0-2.3*o)+0.7*np.sin((px+py)*f*19.0+0.9*o))
        tot+=amp; amp*=0.52; f*=1.9
    return v/tot
warp=0.05*fbm(nx*1.3,ny*1.1,3)
gyri=fbm(nx+warp,ny-warp,5)
sulci=np.clip(1.0-np.abs(gyri)*1.5,0,1)**1.7

relief = height - 0.045*grooves + 0.030*gyri
gy,gx = np.gradient(relief)
sn=300.0; nz=np.ones_like(gx)
nl=np.sqrt((gx*sn)**2+(gy*sn)**2+nz**2)
Nx,Ny,Nz = -(gx*sn)/nl, -(gy*sn)/nl, nz/nl
L=np.array([-0.42,-0.64,0.64]); L/=np.linalg.norm(L)
lambert=np.clip(Nx*L[0]+Ny*L[1]+Nz*L[2],0,1)
rim=np.clip(1.0-height*1.85,0,1)**2.3

def focus(cx,cy,sx,sy,amp):
    return amp*np.exp(-(((nx-cx)/sx)**2+((ny-cy)/sy)**2))

STATES={
 "a":[(0.786,0.470,0.072,0.092,0.70),(0.700,0.390,0.062,0.070,0.34)],
 "b":[(0.786,0.468,0.082,0.104,0.96),(0.700,0.388,0.074,0.082,0.66),
      (0.560,0.270,0.078,0.062,0.42),(0.400,0.660,0.080,0.056,0.30)],
 "c":[(0.784,0.466,0.088,0.110,1.00),(0.698,0.386,0.080,0.090,0.84),
      (0.558,0.266,0.086,0.068,0.62),(0.398,0.658,0.090,0.062,0.52),
      (0.250,0.420,0.080,0.080,0.40),(0.430,0.200,0.070,0.050,0.34)],
}

# unlit cortex: neutral graphite tissue, not viridis purple
BASE = np.array([0.300,0.303,0.315],dtype=np.float32)
SUB  = np.array([0.232,0.235,0.245],dtype=np.float32)
THRESH = 0.18   # below this the surface stays grey, like a real thresholded stat map

for name,foci in STATES.items():
    act=np.zeros((H,W),dtype=np.float32)
    for f in foci: act+=focus(*f)
    act=np.clip(act*(1.0+0.07*gyri),0,1.0)

    idx=np.clip((act*255).astype(np.int32),0,255)
    hot=LUT[idx]
    # only supra-threshold vertices take colour; ramp in over a short band
    t=np.clip((act-THRESH)/0.14,0,1)[...,None]
    rgb=BASE*(1-t)+hot*t

    shade=0.52+0.62*lambert
    rgb=rgb*shade[...,None]
    rgb=rgb*(1.0-0.22*sulci[...,None])
    rgb=rgb*(1.0-0.30*grooves[...,None])
    rgb=rgb*(1.0-0.26*rim[...,None])

    rgb=np.clip(rgb,0,1)
    alpha=np.asarray(Image.fromarray((m_all*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9)),dtype=np.float32)/255.0
    rgb=rgb*(alpha[...,None]>0.003)

    Image.fromarray(np.dstack([(rgb*255).astype(np.uint8),(alpha*255).astype(np.uint8)]),mode="RGBA")\
         .save(f"{OUT}/brain-{name}.png",optimize=True)
    lum=(0.2126*rgb[...,0]+0.7152*rgb[...,1]+0.0722*rgb[...,2])[m_cx>0.5]
    print(f"brain-{name}.png  supra-thresh {(act>THRESH).mean()*100:5.2f}%  "
          f"cortex lum mean={lum.mean():.3f} p10={np.percentile(lum,10):.3f} p90={np.percentile(lum,90):.3f}")
