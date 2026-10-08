import numpy as np, cv2, sys
from PIL import Image
ex='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/ex/'
it='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/intro/'
def km(path,k=8,maxpx=200000):
    im=np.array(Image.open(path).convert('RGBA')).reshape(-1,4)
    px=im[im[:,3]>200][:,:3].astype(np.float32)
    if len(px)>maxpx: px=px[np.random.default_rng(0).choice(len(px),maxpx,replace=False)]
    lab=cv2.cvtColor(px.reshape(-1,1,3).astype(np.uint8),cv2.COLOR_RGB2LAB).reshape(-1,3).astype(np.float32)
    crit=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,50,0.5)
    _,lbl,c=cv2.kmeans(lab,k,None,crit,3,cv2.KMEANS_PP_CENTERS)
    out=[]
    for i in range(k):
        m=lbl.ravel()==i
        med=np.median(px[m],axis=0).astype(int)
        out.append((m.mean(),'#%02x%02x%02x'%tuple(med)))
    out.sort(reverse=True)
    return out
for name,k in [(ex+'logo_title.png.webp',8),(ex+'crest_builders.png.webp',6),(ex+'crest_legion.png.webp',6),(ex+'crest_merchants.png.webp',6),(ex+'crest_nomads.png.webp',7),(ex+'vignette_blue.png.webp',6),(ex+'vignette_red.png.webp',6),(ex+'unit_knight.png.webp',8),(ex+'unit_archer.png.webp',8),(ex+'unit_horse_archer.png.webp',8),(ex+'millefleurs.png.webp',7),(ex+'satin_or.png.webp',3),(ex+'menu_card.png.webp',5),(ex+'menu_veil.png.webp',4),(ex+'game_over_victory.png.webp',5),(ex+'shield_red.png.webp',5),(ex+'realm_banner_green.png.webp',4),(it+'p1_oath.png',10),(it+'p3_death.png',10),(it+'p6_ruin.png',10)]:
    r=km(name,k)
    print(name.split('/')[-1], ' '.join(f'{h}:{p*100:.0f}%' for p,h in r))
