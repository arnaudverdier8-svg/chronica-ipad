import sys,struct,json,os,glob,numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from rsrc import parse
from unrscc import unrscc
BASE=1<<35
def oct_dec(u):  # u: (N,2) in [-1,1]
    n=np.zeros((len(u),3),np.float32); n[:,0]=u[:,0]; n[:,1]=u[:,1]; n[:,2]=1-np.abs(u[:,0])-np.abs(u[:,1])
    t=np.clip(-n[:,2],0,None)
    n[:,0]+=np.where(n[:,0]>=0,-t,t); n[:,1]+=np.where(n[:,1]>=0,-t,t)
    return n/np.linalg.norm(n,axis=1,keepdims=True).clip(1e-9)
def decode_surface(s):
    fmt=s['format']; vc=s['vertex_count']; f=fmt & ((1<<35)-1)
    comp=bool(f&(1<<29)); hasN=bool(f&2); hasT=bool(f&4); hasC=bool(f&8); hasUV=bool(f&16); hasUV2=bool(f&32)
    vd=s['vertex_data'][1]; aabb=np.array(s['aabb'][1],np.float32)
    if comp:
        pb=np.frombuffer(vd[:8*vc],np.uint16).reshape(vc,4)
        pos=aabb[:3]+pb[:,:3].astype(np.float32)/65535.0*aabb[3:]
        nrm=None
        if hasN:
            q=np.frombuffer(vd[8*vc:8*vc+4*vc],np.uint16).reshape(vc,2).astype(np.float32)/65535.0*2-1
            nrm=oct_dec(q)
    else:
        pos=np.frombuffer(vd[:12*vc],np.float32).reshape(vc,3)
        nrm=None
        if hasN:
            ntst=4+(4 if hasT else 0)
            q=np.frombuffer(vd[12*vc:12*vc+ntst*vc],np.uint8).reshape(vc,ntst)[:,:4]
            q=np.frombuffer(q.tobytes(),np.uint16).reshape(vc,2).astype(np.float32)/65535.0*2-1
            nrm=oct_dec(q)
    uv=None
    if hasUV and 'attribute_data' in s:
        ad=s['attribute_data'][1]; astride=len(ad)//vc
        b=np.frombuffer(ad,np.uint8).reshape(vc,astride); o=4 if hasC else 0
        if comp: uv=np.frombuffer(b[:,o:o+4].tobytes(),np.uint16).reshape(vc,2).astype(np.float32)/65535.0
        else: uv=np.frombuffer(b[:,o:o+8].tobytes(),np.float32).reshape(vc,2)
    if 'index_data' in s:
        idd=s['index_data'][1]; ic=s['index_count']
        idx=np.frombuffer(idd,np.uint16 if vc<=65535 else np.uint32)[:ic].astype(np.int64)
    else: idx=np.arange(vc)
    tri=idx.reshape(-1,3)[:,[0,2,1]]  # godot CW -> CCW
    return pos,nrm,uv,tri
def T3D(t):
    b=np.array(t[:9],np.float32).reshape(3,3)  # godot Basis rows? stored as rows[0..2]
    m=np.eye(4,dtype=np.float32); m[:3,:3]=b; m[:3,3]=t[9:12]; return m
def load(fn):
    d=open(fn,'rb').read(); d=unrscc(d) if d[:4]==b'RSCC' else d[4:]
    P=parse(d); res=P['res']
    bund=[p for _,t,p in res if t=='PackedScene'][0]['_bundled']
    names=bund['names'][1]; var=bund['variants']; nd=list(bund['nodes'][1])
    nodes=[]; i=0
    for k in range(bund['node_count']):
        parent,owner,typ,name,inst=nd[i:i+5]; i+=5
        npr=nd[i]; i+=1; props={}
        for _ in range(npr): props[names[nd[i]]]=var[nd[i+1]]; i+=2
        ng=nd[i]; i+=1+ng
        nodes.append(dict(parent=parent,type=names[typ] if typ>=0 and typ<len(names) else typ,name=names[name&0xFFFFFF],props=props))
    return res,nodes
def world(nodes,k):
    m=np.eye(4,dtype=np.float32)
    while k>=0:
        t=nodes[k]['props'].get('transform')
        if t: m=T3D(t[1])@m
        k=nodes[k]['parent']
        if k>=len(nodes): break
    return m
def export(fn,out_dir):
    res,nodes=load(fn)
    base=os.path.basename(fn).replace('.glb.scn','')
    objp=f'{out_dir}/{base}.obj'; mtlp=f'{out_dir}/{base}.mtl'
    mats={}
    lines=[f'mtllib {base}.mtl']; vo=1; ntri=0; nvert=0; parts=[]
    allv=[]
    for k,n in enumerate(nodes):
        mesh=n['props'].get('mesh')
        if not mesh or mesh[0]!='int': continue
        _,t,mp=res[mesh[1]]
        M=world(nodes,k)
        lines.append(f'o {n["name"]}'); parts.append(n['name'])
        for si,s in enumerate(mp['_surfaces']):
            pos,nrm,uv,tri=decode_surface(s)
            mi=s.get('material'); mname=s.get('name','mat%d'%si)
            if mi and mi[0]=='int':
                mprops=res[mi[1]][2]; mname=mprops.get('resource_name',mname)
                col=mprops.get('albedo_color',('Color',(0.8,0.8,0.8,1)))[1]
                mats[mname]=col
            P=(np.c_[pos,np.ones(len(pos))]@M.T)[:,:3]
            allv.append(P)
            lines.append(f'g {n["name"]}_{mname}'); lines.append(f'usemtl {mname}')
            lines+= [f'v {x:.5f} {y:.5f} {z:.5f}' for x,y,z in P]
            if nrm is not None:
                N=nrm@M[:3,:3].T; N/=np.linalg.norm(N,axis=1,keepdims=True).clip(1e-9)
                lines+= [f'vn {x:.4f} {y:.4f} {z:.4f}' for x,y,z in N]
            for a,b,c in tri+vo:
                lines.append(f'f {a}//{a} {b}//{b} {c}//{c}' if nrm is not None else f'f {a} {b} {c}')
            vo+=len(P); ntri+=len(tri); nvert+=len(P)
    # NOTE: normals indices share vertex indices only when every surface has normals
    open(objp,'w').write('\n'.join(lines)+'\n')
    with open(mtlp,'w') as f:
        for m,c in mats.items(): f.write(f'newmtl {m}\nKd {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}\nd 1.0\n\n')
    V=np.concatenate(allv) if allv else np.zeros((1,3))
    return dict(name=base,obj=objp,parts=parts,materials={k:[round(x,3) for x in v[:3]] for k,v in mats.items()},verts=int(nvert),tris=int(ntri),
                bbox_min=V.min(0).round(3).tolist(),bbox_max=V.max(0).round(3).tolist())
if __name__=='__main__':
    out=sys.argv[2]; os.makedirs(out,exist_ok=True); info=[]
    for fn in sorted(glob.glob(sys.argv[1]+'/*.glb.scn')):
        try: r=export(fn,out); info.append(r); print(r['name'],r['verts'],r['tris'],r['parts'],list(r['materials'])[:12],r['bbox_min'],r['bbox_max'])
        except Exception as ex: print('FAIL',fn,repr(ex))
    json.dump(info,open(out+'/models.json','w'),indent=1)
