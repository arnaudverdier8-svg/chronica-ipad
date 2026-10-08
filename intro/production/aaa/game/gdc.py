import struct,sys,zstandard
sys.path.insert(0,'/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/game')
from variant import dec
T="""EMPTY ANNOTATION IDENTIFIER LITERAL < <= > >= == != and or not && || ! & | ~ ^ << >> + - * ** / % = += -= *= **= /= %= <<= >>= &= |= ^= if elif else for while break continue pass return match when as assert await breakpoint class class_name const enum extends func in is namespace preload self signal static super trait var void yield [ ] { } ( ) , ; . .. ... : $ -> _ NEWLINE INDENT DEDENT PI TAU INF NAN VCS ` ? ERROR EOF""".split()
def load(fn):
    b=open(fn,'rb').read()
    assert b[:4]==b'GDSC'
    ver,dsz=struct.unpack_from('<II',b,4)
    data=b[12:]
    if dsz: data=zstandard.ZstdDecompressor().decompress(data,max_output_size=dsz)
    i=0
    ic,cc,lc,tc=struct.unpack_from('<IIII',data,i); i+=16
    ids=[]
    for _ in range(ic):
        n=struct.unpack_from('<I',data,i)[0]; i+=4
        s=''.join(chr(struct.unpack_from('<I',bytes(x^0xb6 for x in data[i+4*k:i+4*k+4]))[0]) for k in range(n)); i+=4*n
        ids.append(s)
    consts=[]
    for _ in range(cc):
        v,i=dec(data,i); consts.append(v)
    lines={}
    for _ in range(lc):
        a,l=struct.unpack_from('<II',data,i); i+=8; lines[a]=l
    cols={}
    for _ in range(lc):
        a,c=struct.unpack_from('<II',data,i); i+=8; cols[a]=c
    toks=[]
    for _ in range(tc):
        t,ln=struct.unpack_from('<II',data,i); i+=8
        toks.append((t,ln))
    return ver,ids,consts,lines,cols,toks
def fmtc(v):
    if isinstance(v,str): return repr(v)
    if isinstance(v,float): return ('%g'%v)
    return str(v)
def recon(fn):
    ver,ids,consts,lines,cols,toks=load(fn)
    out=[];cur='';indent=0;line=None
    for k,(t,ln) in enumerate(toks):
        ty=t&0x7f; idx=t>>8
        name=T[ty] if ty<len(T) else 'T%d'%ty
        if name=='NEWLINE': out.append('    '*indent+cur); cur=''; continue
        if name=='INDENT': indent+=1; continue
        if name=='DEDENT': indent-=1; continue
        if name=='EOF': break
        if name=='IDENTIFIER': s=ids[idx]
        elif name=='LITERAL': s=fmtc(consts[idx])
        elif name=='ANNOTATION': s=ids[idx] if idx<len(ids) else '@?'
        else: s=name
        if cur and not cur.endswith(('(','[','.','$')) and s not in (')',']',',','.',':','(') : cur+=' '
        elif s=='(' and cur and cur[-1:].isalnum()==False and not cur.endswith(('(','[')): cur+=' '
        cur+=s
    out.append(cur)
    return ver,'\n'.join(out),ids,consts
if __name__=='__main__':
    ver,src,ids,consts=recon(sys.argv[1])
    print('# tokenizer version',ver)
    print(src)
