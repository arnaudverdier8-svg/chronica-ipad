import numpy as np, cv2
from PIL import Image
ex='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/ex/'
def load(n):
    a=np.array(Image.open(ex+n+'.png.webp').convert('RGBA')); return a[...,:3], a[...,3]>200
def hexs(c): return '#%02x%02x%02x'%tuple(int(round(x)) for x in c)
def sel(n, hlo,hhi,smin,vlo,vhi):
    rgb,a=load(n); hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV_FULL).astype(float)
    h=hsv[...,0]*360/256; s=hsv[...,1]/255; v=hsv[...,2]/255
    if hlo<=hhi: hm=(h>=hlo)&(h<=hhi)
    else: hm=(h>=hlo)|(h<=hhi)
    m=a&hm&(s>=smin)&(v>=vlo)&(v<=vhi)
    px=rgb[m].astype(float)
    if len(px)==0: return None
    L=px@[0.2126,0.7152,0.0722]
    q=np.percentile(L,[10,50,90])
    out=[]
    for lo,hi in [(0,q[0]+1),(q[0],q[2]),(q[2]-1,256)]:
        mm=(L>=lo)&(L<=hi); out.append(hexs(np.median(px[mm],0)))
    return dict(n=int(m.sum()),frac=round(m.sum()/a.sum(),3),shadow=out[0],mid=out[1],highlight=out[2])
tests={
 'navy(logo_title)':('logo_title',190,250,0.25,0.02,0.45),
 'gold(logo_title)':('logo_title',25,55,0.35,0.35,1),
 'gold(crest_legion eagle)':('crest_legion',30,55,0.3,0.45,1),
 'crimson(crest_legion)':('crest_legion',340,12,0.6,0.2,0.9),
 'royal_blue(crest_merchants)':('crest_merchants',200,235,0.5,0.15,0.9),
 'green(crest_nomads)':('crest_nomads',120,170,0.4,0.1,0.8),
 'orange(crest_builders)':('crest_builders',20,40,0.7,0.5,1),
 'ivory_horse(crest_nomads)':('crest_nomads',20,60,0.0,0.75,1),
 'linen(vignette_blue)':('vignette_blue',25,50,0.1,0.6,0.9),
 'blue_lion(vignette_blue)':('vignette_blue',180,240,0.15,0.1,0.6),
 'red_lion(vignette_red)':('vignette_red',0,25,0.4,0.2,0.7),
 'linen(millefleurs)':('millefleurs',25,50,0.1,0.65,0.95),
 'parchment(menu_card)':('menu_card',25,50,0.1,0.75,1),
 'dark_veil(menu_veil)':('menu_veil',0,60,0.0,0.0,0.2),
 'knight_navy(unit_knight)':('unit_knight',200,240,0.4,0.05,0.6),
 'knight_gold(unit_knight)':('unit_knight',25,50,0.5,0.5,1),
 'archer_green(unit_archer)':('unit_archer',50,110,0.3,0.1,0.6),
 'flesh(unit_archer)':('unit_archer',15,35,0.25,0.6,0.95),
 'red_shield(shield_red)':('shield_red',345,15,0.6,0.2,0.8),
 'banner_green(realm_banner_green)':('realm_banner_green',90,160,0.2,0.1,0.6),
}
import json
res={k:sel(*v) for k,v in tests.items()}
for k,v in res.items(): print(k,v)
json.dump(res,open('game_samples.json','w'),indent=1)
