import pickle,struct,json,io,os,re,numpy as np
from PIL import Image
S='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad'
OUT=S+'/aaa/assets/tex'
W=S+'/aaa/assets/work'
e=pickle.load(open(S+'/ents.pkl','rb'))
m=json.load(open(W+'/import_map.json'))
f=open('/home/user/chronica-ipad/index.pck','rb')
DIRMAP={'assets/figures':'figures','assets/icons':'icons','assets/ui':'ui','assets/ui/embroidery_v2':'ui_embroidery_v2',
'assets/ui/linen':'ui_linen'}
def sub(d):
    if d in DIRMAP: return DIRMAP[d]
    return d.replace('assets/ui/table/','table_')
meta=[]
for p,o,s in e:
    if not p.endswith('.ctex'): continue
    src=m[p]; d,fn=src.rsplit('/',1); name=fn[:-4]
    f.seek(o); b=f.read(s)
    ver,w,h,flags,mml=struct.unpack('<IIIIi',b[4:24])
    df,iw,ih,mips,fmt=struct.unpack('<IHHII',b[36:52])
    os.makedirs(OUT+'/'+sub(d),exist_ok=True)
    dst=f'{OUT}/{sub(d)}/{name}.png'
    if df in (1,2):
        ln=struct.unpack('<I',b[52:56])[0]
        im=Image.open(io.BytesIO(b[56:56+ln])); im.load()
        codec='webp' if df==2 else 'png'
        lossless=None
        if df==2:
            lossless = b[56+12:56+16]==b'VP8L'
    elif df==3:
        meta_j=json.load(open(f'{W}/raw/{name}.json'))
        a=np.fromfile(f'{W}/raw/{name}.rgba',dtype=np.uint8).reshape(meta_j['h'],meta_j['w'],4)
        im=Image.fromarray(a,'RGBA'); codec='ktx2-uastc-zstd'; lossless=False
    else:
        raise Exception(p)
    if fmt==5 and im.mode!='RGBA': im=im.convert('RGBA')
    if fmt==4 and df==3: im=im.convert('RGB')
    im.save(dst,optimize=False,compress_level=6)
    meta.append(dict(src='res://'+src,ctex=p.split('/')[-1],out=dst,w=im.width,h=im.height,mode=im.mode,codec=codec,lossless=lossless,mips=mips,ctex_fmt=fmt,bytes=s))
# raw icon png
for p,o,s in e:
    if p=='assets/icons/icon.png':
        f.seek(o); b=f.read(s); im=Image.open(io.BytesIO(b)); im.load()
        os.makedirs(OUT+'/icons',exist_ok=True)
        dst=OUT+'/icons/icon_source.png'; im.save(dst)
        meta.append(dict(src='res://'+p,ctex=None,out=dst,w=im.width,h=im.height,mode=im.mode,codec='png',lossless=True,mips=0,ctex_fmt=None,bytes=s))
json.dump(meta,open(W+'/extract_meta.json','w'),indent=1)
print(len(meta))
