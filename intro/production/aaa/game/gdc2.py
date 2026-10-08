import sys
sys.path.insert(0,'/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/game')
from gdc import load,T,fmtc
def recon(fn):
    ver,ids,consts,lines,cols,toks=load(fn)
    out={}; colof={}
    # cols map: token index -> column ; build per-token column by carrying
    for k,(t,ln) in enumerate(toks):
        ty=t&0x7f; idx=t>>8
        name=T[ty] if ty<len(T) else 'T%d'%ty
        if name in ('NEWLINE','INDENT','DEDENT'): continue
        if name=='EOF': break
        if name=='IDENTIFIER': s=ids[idx]
        elif name=='LITERAL': s=fmtc(consts[idx])
        elif name=='ANNOTATION': s=ids[idx]
        else: s=name
        cur=out.get(ln,'')
        if ln not in colof: colof[ln]=cols.get(k)
        if cur and not cur.endswith(('(','[','.','$','@')) and s not in (')',']',',','.',':','(','['): cur+=' '
        cur+=s
        out[ln]=cur
    res=[]
    for ln in sorted(out):
        c=colof[ln]
        ind=((c-1)//4) if c else 0
        res.append('%4d '%ln+'    '*ind+out[ln])
    return '\n'.join(res)
if __name__=='__main__':
    print(recon(sys.argv[1]))
