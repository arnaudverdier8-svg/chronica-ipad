import struct,sys,os
f=open('/home/user/chronica-ipad/index.pck','rb')
m,ver,maj,mi,pa,flags=struct.unpack('<4sIIIII',f.read(24))
print(m,ver,maj,mi,pa,flags)
file_base=struct.unpack('<Q',f.read(8))[0]
if ver>=2:
    dir_off=struct.unpack('<Q',f.read(8))[0]; f.seek(dir_off)
else:
    f.read(64)
n=struct.unpack('<I',f.read(4))[0]; print(n,file_base)
ents=[]
for _ in range(n):
    l=struct.unpack('<I',f.read(4))[0]; p=f.read(l).rstrip(b'\0').decode()
    off,size=struct.unpack('<QQ',f.read(16)); f.read(16); fl=struct.unpack('<I',f.read(4))[0]
    ents.append((p,off+(file_base if ver>=2 else 0),size))
import pickle;pickle.dump(ents,open('ents.pkl','wb'))
print(ents[:3])
