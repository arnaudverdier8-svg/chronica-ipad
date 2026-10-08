import pickle,struct,re,collections
S='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad'
e=pickle.load(open(S+'/ents.pkl','rb'))
f=open('/home/user/chronica-ipad/index.pck','rb')
rows=[]
for p,off,size in e:
    if not p.endswith('.ctex'): continue
    f.seek(off); d=f.read(min(size,64))
    magic=d[:4]
    ver,w,h,flags,mml=struct.unpack('<IIIIi',d[4:24])
    df,iw,ih,mips,fmt=struct.unpack('<IHHII',d[36:52])
    name=p.split('/')[-1]
    rows.append((name,magic,ver,w,h,flags,df,iw,ih,mips,fmt,size))
c=collections.Counter((r[1],r[6],r[10]) for r in rows)
print(c)
for r in rows:
    if r[6] not in (1,2): print(r)
