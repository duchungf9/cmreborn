import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..'))
DATA=os.path.join(ROOT,'work','poc','proxy_mesh_frames')
OUT=os.path.join(ROOT,'outputs','sf2_middle_hit_preview.gif')
FIRST=os.path.join(ROOT,'outputs','sf2_middle_hit_preview.png')
W,H=640,480
AA=2
SW,SH=W*AA,H*AA
WORLD_W=450.0
CX=-36.0
CZ=172.0
PX=W/WORLD_W
BG_TOP=(12,19,32)
BG_BOTTOM=(25,35,53)
PALETTE=np.array([
    (48,62,84),       # capsule surfaces
    (78,96,121),      # muscle details
    (106,124,151),    # edge / seam details
    (209,153,78),     # weapon accent
],dtype=np.float32)
LIGHT=np.array((-0.35,-0.80,0.48),dtype=np.float32)
LIGHT/=np.linalg.norm(LIGHT)

try:
    font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font_bold_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    title=ImageFont.truetype(font_bold_path, 16*AA)
    small=ImageFont.truetype(font_path, 10*AA)
except Exception:
    title=ImageFont.load_default(); small=ImageFont.load_default()

def px(x): return (x-CX)*PX*AA + SW/2
def py(z): return SH/2 - (z-CZ)*PX*AA

def make_background():
    top=np.array(BG_TOP,dtype=np.float32); bot=np.array(BG_BOTTOM,dtype=np.float32)
    y=np.linspace(0,1,SH,dtype=np.float32)[:,None,None]
    grad=(top[None,None,:]*(1-y)+bot[None,None,:]*y)
    arr=np.repeat(grad,SW,axis=1).astype(np.uint8)
    img=Image.fromarray(arr,'RGB').convert('RGBA')
    d=ImageDraw.Draw(img,'RGBA')
    # Fine technical grid, deliberately faint.
    for gx in range(0,SW,80*AA): d.line((gx,0,gx,SH),fill=(128,155,185,14),width=1)
    for gy in range(0,SH,80*AA): d.line((0,gy,SW,gy),fill=(128,155,185,14),width=1)
    # Floor / contact line at the proxy's feet.
    floor_y=py(62)
    d.line((0,floor_y,SW,floor_y),fill=(142,165,194,72),width=1*AA)
    for x in range(0,SW,20*AA):
        d.line((x,floor_y,x,floor_y+4*AA),fill=(142,165,194,55),width=1*AA)
    # Header.
    d.rounded_rectangle((22*AA,18*AA,SW-22*AA,61*AA),radius=8*AA,fill=(5,10,19,130),outline=(116,144,180,46),width=1*AA)
    d.text((34*AA,25*AA),'MIDDLE HIT',font=title,fill=(235,241,248,255))
    d.text((34*AA,46*AA),'SHADOW FIGHT 2  /  20 FPS',font=small,fill=(149,171,199,255))
    return img

def frame_image(frame_number):
    path=os.path.join(DATA,f'frame_{frame_number:02d}.npz')
    with np.load(path) as pack:
        verts=pack['vertices'].astype(np.float32)
        indices=pack['face_indices'].astype(np.int32)
        offsets=pack['face_offsets'].astype(np.int32)
        cats=pack['face_category'].astype(np.uint8)
        segments=pack['bone_segments'].astype(np.float32)
        bone_cats=pack['bone_category'].astype(np.uint8)
    img=make_background()
    # Ground shadow follows the moving proxy.
    d=ImageDraw.Draw(img,'RGBA')
    x_center=float((verts[:,0].min()+verts[:,0].max())/2)
    x0=px(x_center-55); x1=px(x_center+55)
    gy=py(float(verts[:,2].min())-1.5)
    shadow=Image.new('RGBA',(SW,SH),(0,0,0,0)); sd=ImageDraw.Draw(shadow)
    sd.ellipse((x0,gy-5*AA,x1,gy+6*AA),fill=(2,5,12,95))
    img=Image.alpha_composite(img,shadow.filter(ImageFilter.GaussianBlur(8*AA)))

    # Painter's algorithm from far to near; each mesh contributes only its visible proxy surface.
    polys=[]
    for i in range(len(cats)):
        a,b=offsets[i],offsets[i+1]
        face=indices[a:b]
        if len(face)<3: continue
        pts=verts[face]
        depth=float(pts[:,1].mean())
        polys.append((depth,i,face))
    polys.sort(key=lambda row:row[0],reverse=True)
    draw=ImageDraw.Draw(img,'RGBA')
    for depth,i,face in polys:
        pts3=verts[face]
        # Face normal for a soft, two-sided studio-light look.
        n=np.cross(pts3[1]-pts3[0],pts3[2]-pts3[0])
        length=float(np.linalg.norm(n))
        if length>1e-5:
            n/=length
            diffuse=max(0.0,float(np.dot(n,LIGHT)))
        else: diffuse=0.0
        shade=0.62+0.38*diffuse
        color=np.clip(PALETTE[cats[i]]*shade,0,255).astype(np.uint8)
        xy=[(px(float(v[0])),py(float(v[2]))) for v in pts3]
        # Ignore polygons fully outside the canvas.
        if max(q[0] for q in xy)<0 or min(q[0] for q in xy)>SW or max(q[1] for q in xy)<0 or min(q[1] for q in xy)>SH: continue
        draw.polygon(xy,fill=tuple(int(c) for c in color)+(255,))

    # Overlay the baked armature to make the mocap pose easy to read.
    bone_colors=[(104,221,210,255),(246,190,104,255),(240,143,82,255)]
    bone_rows=sorted(zip(segments,bone_cats),key=lambda row:float(row[0][:,1].mean()),reverse=True)
    rig=ImageDraw.Draw(img,'RGBA')
    for seg,cat in bone_rows:
        a=(px(float(seg[0,0])),py(float(seg[0,2])))
        b=(px(float(seg[1,0])),py(float(seg[1,2])))
        rig.line((a,b),fill=(3,9,16,240),width=5*AA)
        rig.line((a,b),fill=bone_colors[int(cat)],width=2*AA)
        for q in (a,b):
            r=2*AA
            rig.ellipse((q[0]-r,q[1]-r,q[0]+r,q[1]+r),fill=(229,238,246,255),outline=(7,16,26,255),width=1*AA)

    # Frame counter and progress indicator.
    overlay=ImageDraw.Draw(img,'RGBA')
    overlay.text((SW-88*AA,31*AA),f'{frame_number:02d} / 20',font=small,fill=(187,203,223,255))
    x1=SW-34*AA; x0=SW-86*AA; y=51*AA
    overlay.rounded_rectangle((x0,y,x1,y+3*AA),radius=2*AA,fill=(115,137,165,85))
    overlay.rounded_rectangle((x0,y,x0+(x1-x0)*frame_number/20,y+3*AA),radius=2*AA,fill=(230,169,93,255))
    # Downsample for antialiased final GIF.
    rgb=img.convert('RGB').resize((W,H),Image.Resampling.LANCZOS)
    return rgb

frames=[frame_image(i) for i in range(1,21)]
# Use one shared GIF palette to prevent color flicker between frames.
contact=Image.new('RGB',(W*4,H*3))
for i,im in enumerate(frames):
    contact.paste(im.resize((W//2,H//2)),((i%4)*(W//2),(i//4)*(H//2)))
palette_ref=contact.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
quantized=[im.quantize(palette=palette_ref,dither=Image.Dither.FLOYDSTEINBERG) for im in frames]
quantized[0].save(OUT,save_all=True,append_images=quantized[1:],duration=50,loop=0,optimize=True,disposal=2)
frames[7].save(FIRST)
print('GIF',OUT,os.path.getsize(OUT))
print('PNG',FIRST,os.path.getsize(FIRST))
