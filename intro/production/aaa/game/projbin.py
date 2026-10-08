import struct,sys
sys.path.insert(0,'.')
from variant import dec
b=open('raw/project.binary','rb').read()
assert b[:4]==b'ECFG'
n=struct.unpack_from('<I',b,4)[0]; i=8
for _ in range(n):
    l=struct.unpack_from('<I',b,i)[0]; i+=4; k=b[i:i+l].decode(); i+=l
    vl=struct.unpack_from('<I',b,i)[0]; i+=4
    try: v,_=dec(b,i)
    except Exception as e: v='ERR %s'%e
    i+=vl
    if isinstance(v,dict) and 'value' in v:
        val=v['value']
        if isinstance(val,tuple) and val[0].startswith('V') and len(val[1])==3:
            r,g,bb=val[1]; hx='#%02x%02x%02x'%tuple(int(round(max(0,min(1,c))*255)) for c in (r,g,bb))
            print(k,v['type'],val[1],hx,' srgb-if-linear:#%02x%02x%02x'%tuple(int(round((1.055*max(0,c)**(1/2.4)-0.055 if c>0.0031308 else 12.92*c)*255)) for c in (r,g,bb)))
            continue
    if isinstance(v,tuple) and v[0]=='Color':
        r,g,bb,a=v[1]; print(k,v,'#%02x%02x%02x'%tuple(int(round(c*255)) for c in (r,g,bb))); continue
    print(k,v)
