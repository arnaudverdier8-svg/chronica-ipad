import os,sys,glob,json,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from PIL import Image,ImageDraw,ImageFont
from groups import group_of
A='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/assets'
FONT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
FONTB=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',30)
BG=(128,128,128)
def sheet(items,out,title,SW=3000,H=260,maxW=900,pad=18,upscale=2.0):
    # items: list of (label, path)
    tiles=[]
    for lab,p in items:
        im=Image.open(p).convert('RGBA'); w,h=im.size
        s=min(H/h, maxW/w, upscale)
        tw,th=max(1,round(w*s)),max(1,round(h*s))
        im=im.resize((tw,th),Image.LANCZOS)
        lw=FONT.getlength(lab); tiles.append((lab,f'{w}x{h}',im,max(tw,int(lw)+4,int(FONT.getlength(f'{w}x{h}'))+4)))
    rows=[];cur=[];x=pad
    for t in tiles:
        if cur and x+t[3]+pad>SW: rows.append(cur);cur=[];x=pad
        cur.append(t);x+=t[3]+pad
    if cur: rows.append(cur)
    rowh=H+50
    canvas=Image.new('RGB',(SW,60+len(rows)*(rowh+pad)+pad),BG)
    d=ImageDraw.Draw(canvas); d.text((pad,12),title,font=FONTB,fill=(255,255,255))
    y=60
    for r in rows:
        x=pad
        for lab,dim,im,cw in r:
            ox=x+(cw-im.width)//2; oy=y+(H-im.height)//2
            canvas.paste(im,(ox,oy),im)
            d.rectangle([ox-1,oy-1,ox+im.width,oy+im.height],outline=(150,150,150))
            d.text((x,y+H+4),lab,font=FONT,fill=(255,255,255)); d.text((x,y+H+24),dim,font=FONT,fill=(215,215,215))
            x+=cw+pad
        y+=rowh+pad
    canvas.save(out,quality=88)
    print(out,canvas.size)
if __name__=='__main__':
    files=sorted(glob.glob(A+'/tex/*/*.png'))
    G={}
    for f in files:
        rel=os.path.relpath(f,A+'/tex'); G.setdefault(group_of(rel),[]).append((rel[:-4],f))
    json.dump({k:[r for r,_ in v] for k,v in G.items()},open(A+'/work/groups.json','w'),indent=1)
    cfg={'branding':dict(H=300,maxW=1100,title='BRANDING / TITLE ART / VIGNETTES (tex/)'),
         'heraldry':dict(H=230,title='HERALDRY: crests, shields, realm banners, lions'),
         'ornaments':dict(H=240,title='ORNAMENTS: carved wood, candles, lion statues, rules, pillars, frames'),
         'panels':dict(H=200,title='PANELS / PARCHMENT / LINEN / CARDS / MENU ITEMS'),
         'units':dict(H=300,title='UNITS: icons (256px) + embroidered figure cards idle/strike albedo'),
         'figure_maps':dict(H=220,title='FIGURE NORMAL (RGB recon. from RG) + MASK (R=team livery, G=shield field, B=thread sheen, A=cord) maps'),
         'icons':dict(H=150,title='ICONS: buildings, techs, resources, stats, jobs, levels, glyphs, phases'),
         'clouds':dict(H=260,title='CLOUDS: embroidered cloud edges, corners, puffs, fill, atlas'),
         'ui_widgets':dict(H=150,title='PURE UI WIDGETS (low cinematic value)')}
    for k,v in G.items():
        c=cfg.get(k,dict(H=200,title=k))
        items=v
        if k=='figure_maps':
            # show masks with alpha forced opaque so channels are visible
            import numpy as np
            tmp=A+'/work/maskvis'; os.makedirs(tmp,exist_ok=True); items=[]
            for lab,f in v:
                if f.endswith('_mask.png'):
                    a=np.array(Image.open(f).convert('RGBA')); rgb=a.copy(); rgb[...,3]=255
                    al=np.dstack([a[...,3]]*3+[np.full(a.shape[:2],255,np.uint8)])
                    p1=f'{tmp}/{os.path.basename(f)[:-4]}_rgb.png'; p2=f'{tmp}/{os.path.basename(f)[:-4]}_A.png'
                    Image.fromarray(rgb).save(p1); Image.fromarray(al).save(p2)
                    items+= [(lab+' RGB',p1),(lab+' A(cord)',p2)]
                else: items.append((lab,f))
        sheet(items,f'{A}/contact_{k}.jpg',c['title'],H=c['H'],maxW=c.get('maxW',900))
