"""Recolour a CHRONICA embroidered figure card with a realm colour, exactly like
view/shaders/figure.gdshader does in-game:
    gray = mean(albedo.rgb) / g0 ;  col = mix(albedo, clamp(team*gray), mask.R)
mask.R = team livery zones (albedo is neutral grey there), mask.G = shield field
(in-game a procedural heraldic charge is stitched there), mask.B = thread sheen,
mask.A = brown outline cord. Masks are half resolution -> upsampled here.
Usage: python3 figure_tint.py knight strike '#2B4157' out.png
"""
import json,sys,os,numpy as np
from PIL import Image
D=os.path.dirname(os.path.abspath(__file__))
G0={'archer':0.6324,'catapult':0.7331,'engineer':0.6634,'goblin':0.8,'horse_archer':0.7612,'knight':0.6617,
    'legionary':0.682,'man_at_arms':0.7752,'mercenary':0.648,'scout':0.6478,'spearman':0.7784}
REALM={'red':'#843C1E','gold':'#C29632','green':'#3A4F1F','blue':'#2B4157'}  # Palettes.TAPISSERIE['border']
def hex2rgb(h): h=h.lstrip('#'); return np.array([int(h[i:i+2],16) for i in (0,2,4)],np.float32)/255
def tint(unit,pose,team,sat=1.3,val=0.92,shield=None):
    a=np.asarray(Image.open(f'{D}/tex/figures/{unit}_{pose}_albedo.png').convert('RGBA')).astype(np.float32)/255
    import cv2  # NB: never PIL-resize the mask as RGBA: PIL premultiplies by A (=cord) and wipes R/G/B
    m=np.asarray(Image.open(f'{D}/tex/figures/{unit}_{pose}_mask.png').convert('RGBA')).astype(np.float32)/255
    m=cv2.resize(m,(a.shape[1],a.shape[0]),interpolation=cv2.INTER_LINEAR)
    t=hex2rgb(team) if isinstance(team,str) else np.asarray(team,np.float32)
    # approximate Models.view_tone with fig_team_sat [1.3, 0.92]: saturate + darken slightly
    L=t.mean(); t=np.clip((L+(t-L)*sat)*val,0,1)
    gray=a[...,:3].mean(-1,keepdims=True)/G0[unit]
    col=a[...,:3]*(1-m[...,:1])+np.clip(t*gray,0,1)*m[...,:1]
    if shield is not None:  # flat-fill shield field (G) with a colour, keeping thread shading
        s=hex2rgb(shield) if isinstance(shield,str) else np.asarray(shield,np.float32)
        col=col*(1-m[...,1:2])+np.clip(s*gray,0,1)*m[...,1:2]
    out=np.dstack([col,a[...,3:]])
    return Image.fromarray((out*255+0.5).astype(np.uint8),'RGBA')
if __name__=='__main__':
    tint(sys.argv[1],sys.argv[2],sys.argv[3]).save(sys.argv[4])
