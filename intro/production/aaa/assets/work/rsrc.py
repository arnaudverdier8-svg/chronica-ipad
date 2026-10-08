import struct,sys
sys.path.insert(0,'.')
from unrscc import unrscc
class R:
    def __init__(s,d): s.d=d; s.p=0
    def u32(s): v=struct.unpack_from('<I',s.d,s.p)[0]; s.p+=4; return v
    def i32(s): v=struct.unpack_from('<i',s.d,s.p)[0]; s.p+=4; return v
    def u64(s): v=struct.unpack_from('<Q',s.d,s.p)[0]; s.p+=8; return v
    def f32(s,n=1): v=struct.unpack_from('<%df'%n,s.d,s.p); s.p+=4*n; return v if n>1 else v[0]
    def ustr(s):
        n=s.u32(); b=s.d[s.p:s.p+n]; s.p+=n; return b.rstrip(b'\0').decode('utf8','replace')
    def pad(s,n):
        if n%4: s.p+=4-n%4
def parse(d):
    r=R(d)
    be,r64,vmaj,vmin,vfmt=[r.u32() for _ in range(5)]
    typ=r.ustr(); imo=r.u64(); flags=r.u32(); uid=r.u64()
    if flags&8: r.ustr()
    r.p+=11*4
    st=[r.ustr() for _ in range(r.u32())]
    ext=[]
    for _ in range(r.u32()):
        t=r.ustr(); pth=r.ustr(); u=r.u64() if flags&2 else 0; ext.append((t,pth))
    ints=[(r.ustr(),r.u64()) for _ in range(r.u32())]
    def var():
        t=r.u32()
        if t==1: return None
        if t==2: return bool(r.u32())
        if t==3: return r.i32()
        if t==40: v=struct.unpack_from('<q',r.d,r.p)[0]; r.p+=8; return v
        if t==4: return r.f32()
        if t==41: v=struct.unpack_from('<d',r.d,r.p)[0]; r.p+=8; return v
        if t in (5,44): return r.ustr()
        if t==22:
            nn=r.u32()&0x7fffffff; ns=r.u32(); fl=r.u32()
            names=[r.u32() for _ in range(nn+ns)]; return ('NodePath',[st[i] if i<len(st) else i for i in names])
        if t==10: return r.f32(2)
        if t==45: r.p+=8; return struct.unpack_from('<2i',r.d,r.p-8)
        if t==11: return r.f32(4)
        if t==12: return r.f32(3)
        if t==47: r.p+=12; return struct.unpack_from('<3i',r.d,r.p-12)
        if t==13: return r.f32(4)
        if t==14: return r.f32(4)
        if t==15: return ('AABB',r.f32(6))
        if t==16: return r.f32(9)
        if t==17: return ('T3D',r.f32(12))
        if t==18: return r.f32(6)
        if t==20: return ('Color',r.f32(4))
        if t==50: return r.f32(4)
        if t==52: return r.f32(16)
        if t==24:
            ot=r.u32()
            if ot==0: return None
            if ot==1: return ('ext',r.ustr(),r.ustr())
            if ot==2: return ('int',r.u32())
            if ot==3: return ('extidx',r.u32())
        if t==26:
            n=r.u32()&0x7fffffff; return {_k(var()):var() for _ in range(n)}
        if t==30:
            n=r.u32()&0x7fffffff; return [var() for _ in range(n)]
        if t==31:
            n=r.u32(); b=r.d[r.p:r.p+n]; r.p+=n; r.pad(n); return ('bytes',b)
        if t==32:
            n=r.u32(); v=struct.unpack_from('<%di'%n,r.d,r.p); r.p+=4*n; return ('i32',v)
        if t==33:
            n=r.u32(); v=struct.unpack_from('<%df'%n,r.d,r.p); r.p+=4*n; return ('f32',v)
        if t==34:
            n=r.u32(); return ('strs',[r.ustr() for _ in range(n)])
        if t==35:
            n=r.u32(); v=struct.unpack_from('<%df'%(3*n),r.d,r.p); r.p+=12*n; return ('v3',v)
        if t==37:
            n=r.u32(); v=struct.unpack_from('<%df'%(2*n),r.d,r.p); r.p+=8*n; return ('v2',v)
        if t==36:
            n=r.u32(); v=struct.unpack_from('<%df'%(4*n),r.d,r.p); r.p+=16*n; return ('col',v)
        raise Exception('variant type %d at %d'%(t,r.p))
    def _k(k): return k if isinstance(k,(str,int,float,bool)) else str(k)
    res=[]
    for path,off in ints:
        r.p=off; t=r.ustr(); props={}
        for _ in range(r.u32()):
            ni=r.u32(); name=st[ni] if ni<len(st) else ni
            props[name]=var()
        res.append((path,t,props))
    return dict(type=typ,ver=(vmaj,vmin,vfmt),ext=ext,res=res)
def short(v,depth=0):
    if isinstance(v,tuple) and v and v[0] in ('bytes','i32','f32','v3','v2','col','strs'):
        return f'<{v[0]} n={len(v[1])}>'
    if isinstance(v,dict): return '{'+', '.join(f'{k}: {short(x,depth+1)}' for k,x in v.items())+'}'
    if isinstance(v,list): return '['+', '.join(short(x,depth+1) for x in v[:6])+(' ...' if len(v)>6 else '')+']'
    return repr(v)[:200]
if __name__=='__main__':
    d=open(sys.argv[1],'rb').read()
    if d[:4]==b'RSCC': d=unrscc(d)
    else: d=d[4:]
    P=parse(d)
    print(P['type'],P['ver'],P['ext'])
    for path,t,props in P['res']:
        print('==',path,t)
        for k,v in props.items(): print('   ',k,':',short(v)[:600])
