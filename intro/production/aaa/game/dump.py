import pickle,sys,os
S='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad'
e=pickle.load(open(S+'/ents.pkl','rb'))
f=open('/home/user/chronica-ipad/index.pck','rb')
out=S+'/aaa/game/raw'
for pat in sys.argv[1:]:
    for p,o,s in e:
        if pat in p:
            f.seek(o); d=f.read(s)
            fn=os.path.join(out,p.replace('/','__'))
            open(fn,'wb').write(d); print(fn,s)
