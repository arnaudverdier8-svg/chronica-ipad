import struct
def dec(b,i):
    h=struct.unpack_from('<I',b,i)[0]; i+=4; t=h&0xff; f64=bool(h&(1<<16))
    if t==0: return None,i
    if t==1: return bool(struct.unpack_from('<I',b,i)[0]),i+4
    if t==2:
        if f64: return struct.unpack_from('<q',b,i)[0],i+8
        return struct.unpack_from('<i',b,i)[0],i+4
    if t==3:
        if f64: return struct.unpack_from('<d',b,i)[0],i+8
        return struct.unpack_from('<f',b,i)[0],i+4
    if t in (4,21,):
        n=struct.unpack_from('<I',b,i)[0]; i+=4; s=b[i:i+n].decode('utf8','replace'); i+=n+((4-n%4)%4); return s,i
    fl='<d' if f64 else '<f'; fs=8 if f64 else 4
    cnt={5:2,7:4,9:3,12:4,14:4,15:4,16:6,17:9,18:12,19:16,20:4}
    if t in cnt:
        n=cnt[t]; fmt='<'+('d' if f64 and t!=20 else 'f')*n; sz=(8 if f64 and t!=20 else 4)*n
        v=struct.unpack_from(fmt,b,i); return (('Color' if t==20 else 'V%d'%t),tuple(round(x,4) for x in v)),i+sz
    if t in (6,8,10,13):
        n={6:2,8:4,10:3,13:4}[t]; return ('Vi',struct.unpack_from('<%di'%n,b,i)),i+4*n
    if t==27:
        n=struct.unpack_from('<I',b,i)[0]&0x7fffffff; i+=4; d={}
        for _ in range(n):
            k,i=dec(b,i); v,i=dec(b,i); d[k]=v
        return d,i
    if t==28:
        n=struct.unpack_from('<I',b,i)[0]&0x7fffffff; i+=4; a=[]
        for _ in range(n):
            v,i=dec(b,i); a.append(v)
        return a,i
    if t==34:
        n=struct.unpack_from('<I',b,i)[0]; i+=4; a=[]
        for _ in range(n):
            m=struct.unpack_from('<I',b,i)[0]; i+=4; a.append(b[i:i+m].decode()); i+=m+((4-m%4)%4)
        return a,i
    raise ValueError('type %d at %d'%(t,i))
